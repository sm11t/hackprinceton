"""Parcel/suite-scoped execution checklist; no inferred permit grants or dates."""
from approvals_timeline import REFERENCES


def approval_path(approvals, prop, scope, proposed_use, identity_records):
    parcel_ids=prop.get('parcelNumbers') or prop.get('parcelReferences') or []
    scope_conflict=any(r['fact'] in {'scan_suite','scan_address'} and r['status']=='conflict' for r in identity_records)
    market=approvals['guidance_market']
    municipal=approvals['jurisdiction_verified']
    authority={'Houston':'Houston Permitting Center / Planning (only if city jurisdiction confirmed)',
               'Los Angeles':'Los Angeles City Planning / LADBS (only if city jurisdiction confirmed)'}.get(market,'Local planning, building and fire authority — identify first')
    reference='houston-occupancy' if market=='Houston' else 'la-records' if market=='Los Angeles' else None
    url=REFERENCES[reference][1] if reference else None
    rows=[]
    def step(id,label,needs,action,ref=url):
        rows.append(dict(id=id,title=label,prerequisites=needs,authority=authority,official_source_url=ref,
                         status='conditionally_applicable' if municipal and parcel_ids and not scope_conflict else 'unknown_applicability',
                         duration_months=None,time_provenance='No agency estimate obtained',
                         blocker='Not cleared; written authority/landlord confirmation required',next_action=action))
    step('identity','Confirm parcel, municipal boundary and premises',[],
         f'Broker: reconcile recorded parcel identifiers {parcel_ids or "(missing)"} with official parcel map and {scope}. Obtain a municipal point-in-boundary result; postal city is not proof.',None)
    step('use','Allowed use, private restrictions and special-use review',['identity'],
         f'Ask planning and landlord whether {proposed_use} is permitted at this exact premises; obtain applicable zoning/overlays or deed restrictions, and whether discretionary/special-use review is needed.',
         REFERENCES['houston-deeds' if market=='Houston' else 'la-zimas'][1] if market else None)
    step('occupancy','Change of use and Certificate of Occupancy',['use'],
         'Retrieve current CO and approved plan; ask whether proposed occupancy changes classification or capacity.')
    step('design','Building, fire, accessibility, parking and signage',['occupancy'],
         'Architect: verify exits, ADA route/restrooms, fire protection, peak parking allocation, signage and MEP capacity. Ask authority for applicable plan reviews and trade permits.')
    step('permit','Permit review and corrections',['design'],
         'Obtain written submission checklist, fee calculation and agency timing; track resubmissions. Do not start regulated work without required permits.')
    step('build','Construction and trade inspections',['permit'],
         'Use contractor scope and approved plans; schedule required inspections and document corrections.')
    step('open','Final inspections and permission to occupy',['build'],
         'Obtain final signoffs and occupancy approval before opening. Confirm business-specific licenses.')
    return dict(parcel_ids=parcel_ids,parcel_identity_status='recorded; official match unverified' if parcel_ids else 'unknown',
                scope=scope,scope_conflict=scope_conflict,jurisdiction_verified=municipal,
                guidance_market=market,official_requirements_verified=[],
                critical_path=rows,critical_path_duration=None,
                summary='Complete identity and use checks first. This is a conditional review sequence; no site permission or agency completion date is established.')
