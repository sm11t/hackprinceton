"""Two-stage compliance triage. No output constitutes a permit or inspection.

Caller supplies normalized facts and confirmed jurisdiction; postal city is insufficient.
Optional search callback: search(query, domains) -> list of {url, title, content}.
Only official-domain search results survive; retrieved text never clears a gate.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

AUTHORITIES = {
    'houston': ('Houston Permitting Center', 'https://www.houstontx.gov/business/plan/permits-inspections.html', ['houstontx.gov']),
    'harris_unincorporated': ('Harris County Office of the County Engineer', 'https://oce.harriscountytx.gov/Services/Permits/Permits-A-to-Z/Commercial-Building', ['harriscountytx.gov', 'hctx.net']),
    'los_angeles': ('City of Los Angeles Building and Safety / Planning', 'https://dbs.lacity.gov/services/search-online-building-records', ['lacity.gov', 'ladbs.org']),
    'la_unincorporated': ('LA County Public Works / Planning', 'https://permits.lacounty.gov/permits/building-and-safety/', ['lacounty.gov']),
}
TOPICS = {
    'identity': 'Confirm parcel, building and selected suite against official records',
    'occupancy': 'Retrieve approved occupancy/use and proposed change-of-use requirements',
    'fire': 'Obtain fire review: exits, occupant load, alarms and suppression',
    'accessibility': 'Verify accessible route, entrances and restrooms with qualified review',
    'parking': 'Confirm allocated parking, access and applicable local requirements',
    'mep': 'Verify electrical, HVAC, plumbing capacity and required trade permits',
}

def record(fact, value=None, source='public:compliance-triage', url=None, note='', conflict=False):
    return dict(fact=fact, value=value, source=source, source_id=fact, captured_at=None,
                confidence=None, evidence_url=url, status='conflict' if conflict else 'unknown',
                needs_human=True, note=note)


def official(url, domains):
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    return parsed.scheme == 'https' and not parsed.username and not parsed.password and any(host == d or host.endswith('.' + d) for d in domains)


def tavily_search(query, domains):
    """Opt-in live search. API key is read only when called; never returned."""
    key = os.environ.get('TAVILY_API_KEY')
    if not key:
        raise RuntimeError('TAVILY_API_KEY unavailable')
    data = json.dumps(dict(query=query, include_domains=domains, max_results=3)).encode()
    req = Request('https://api.tavily.com/search', data=data, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urlopen(req, timeout=20) as response:
        return json.load(response).get('results', [])


def preflight(context):
    """Building stage; returns normalized scope, deterministic gates and handoff."""
    if not isinstance(context, dict):
        raise ValueError('context must be an object')
    facts = context.get('facts') or {}
    records = []
    gates = []
    jurisdiction = context.get('jurisdiction') or {}
    code = jurisdiction.get('code')
    verified = jurisdiction.get('verified') is True and bool(jurisdiction.get('evidence_url'))
    if code not in AUTHORITIES or not verified:
        gates.append('jurisdiction_unverified')
    if not context.get('property_id') or not context.get('scope'):
        gates.append('identity_incomplete')
    if context.get('identity_conflict') is True:
        gates.append('identity_conflict')
    if facts.get('property_type', '').lower() in {'residential', 'multifamily', 'apartment'}:
        gates.append('commercial_conversion_unestablished')
    for name in ('area_sqft', 'clear_height_ft', 'floors', 'parking_spaces', 'hvac_capacity', 'fire_inspection'):
        value = facts.get(name)
        # Zero height/area and booleans cannot establish usable geometry.
        if name in ('area_sqft', 'clear_height_ft', 'floors') and (isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0):
            value = None
        records.append(record(name, value, source='costar' if name in ('area_sqft', 'floors') else 'public:caller-evidence', note='Caller-provided; verify source, suite scope and date. Not an inspection.'))
    for topic, action in TOPICS.items():
        records.append(record(topic, note=action))
    return dict(schema_version='compliance.v1', stage='building', property_id=context.get('property_id'), scope=context.get('scope'),
                jurisdiction=jurisdiction, gates=gates, status='blocked' if any(g in gates for g in ('identity_conflict', 'commercial_conversion_unestablished')) else 'needs_verification',
                records=records, business_handoff_allowed=not any(g in gates for g in ('identity_conflict', 'commercial_conversion_unestablished')), legal_approval=False)


def check_business(context, business, search=None, requirements=None):
    """Business stage accepts ANY registry key, avoiding a divergent 26-use catalog.

    requirements may contain numeric min_area_sqft/min_clear_height_ft plus source_url.
    These are explicit screening thresholds, never assumed code requirements.
    """
    if not isinstance(business, str) or not business.strip():
        raise ValueError('business must be a nonempty registry key or label')
    report = preflight(context)
    report.update(stage='business', business=business, research=[], errors=[], trace=[])
    if not report['business_handoff_allowed']:
        report['trace'].append('Stopped before business research: unresolved building gate')
        return report
    facts = context.get('facts') or {}
    for key, fact in [('min_area_sqft', 'area_sqft'), ('min_clear_height_ft', 'clear_height_ft')]:
        threshold = (requirements or {}).get(key)
        actual = facts.get(fact)
        if threshold is not None:
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 < threshold < 1e9:
                raise ValueError('invalid screening threshold')
            comparable = isinstance(actual, (int, float)) and not isinstance(actual, bool) and actual > 0 and context.get('measurements_match_scope') is True
            failed = comparable and actual < threshold
            report['records'].append(record(key, threshold, url=(requirements or {}).get('source_url'), conflict=failed,
                note='User/registry screening threshold; scope-matched measurement required; not legal capacity.'))
            if failed:
                report['gates'].append(fact + '_below_requested_threshold')
                report['status'] = 'blocked'
    code = (context.get('jurisdiction') or {}).get('code')
    if 'jurisdiction_unverified' in report['gates'] or report['status'] == 'blocked':
        report['trace'].append('Research deferred until jurisdiction and screening gates are resolved')
        return report
    authority, url, domains = AUTHORITIES[code]
    report['authority'] = authority
    report['records'].append(record('official_process', url, url=url, note='General process reference, not parcel approval'))
    # Two bounded calls, not 26 independent loops. Evidence cannot execute instructions.
    for topic in ('change of use occupancy permits', 'parking HVAC fire accessibility business licensing'):
        query = f'{authority} {business} {topic}'
        if search is None:
            report['trace'].append(dict(query=query, status='not_run'))
            continue
        try:
            results = search(query, domains)
            accepted = [dict(url=r['url'], title=str(r.get('title', ''))[:300], excerpt=str(r.get('content', ''))[:2000], retrieved_at=datetime.now(timezone.utc).isoformat(), applicability='unverified') for r in results if official(r.get('url', ''), domains)]
            report['research'].extend(accepted)
            report['trace'].append(dict(query=query, status='retrieved', accepted=len(accepted)))
        except Exception:
            report['errors'].append('Official-source research unavailable; retry or contact authority')
            report['trace'].append(dict(query=query, status='unavailable'))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('context', help='Normalized JSON context file')
    parser.add_argument('--business')
    parser.add_argument('--live', action='store_true', help='Opt-in Tavily official-source retrieval')
    args = parser.parse_args()
    with open(args.context) as stream:
        context = json.load(stream)
    print(json.dumps(check_business(context, args.business, tavily_search if args.live else None) if args.business else preflight(context), indent=2))
