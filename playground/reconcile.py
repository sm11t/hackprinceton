"""Evidence reconciliation: cross-check what CoStar, Matterport and public data say.

Every check returns evidence records in the shared contract (Spec canvas →
API contracts):

    {fact, value, source, source_id, captured_at, confidence, evidence_url,
     status: agrees|conflict|unknown, needs_human, note}

status: "conflict" when two sources disagree, "unknown" when a fact cannot be
established, and "agrees" when sources match or a single-source fact raised no
conflict.

Checks so far:
  identity     scan caption address vs CoStar address (e.g. 9750 vs 9700 Tanner Rd)
  scan_dates   CoStar's originationDate per scan (latest date the scan can show;
               Matterport's own `created` is the re-hosting date and must not be used)
  clear_height CoStar ceiling height vs Matterport measured room heights
  flood        FEMA National Flood Hazard Layer zone at the CoStar pin
  occupancy    suite-named scan vs the CoStar tenancy covering that suite on the scan date
               (empty marketing scan + active lease = conflict; tenant moved in after = fine)
  size         CoStar internal size math: GBA vs typical floor x stories, rentable vs gross
               (aerial footprint vs floor size lives in exterior.py, from physical fit)

Usage:
  python3 playground/reconcile.py --kit ~/Downloads/costar-hackathon-kit.zip --property-id 23296
  python3 playground/reconcile.py --kit ... --scan-identity Houston   # identity check across a market
  python3 playground/reconcile.py --kit ... --scan-occupancy Houston  # occupancy check across a market
Add --offline to skip Matterport and FEMA network calls.
"""
import argparse
import base64
import io
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile

MATTERPORT_TYPES = {36, 234}  # MatterportScan, MatterportStreamingKey (kit docs)
MARKETS = {"Houston": 14, "Los Angeles": 20}
FEMA_NFHL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
MATTERPORT_GRAPH = "https://api.matterport.com/api/models/graph"
STREET_WORDS = {
    "rd": "road", "st": "street", "ave": "avenue", "av": "avenue", "blvd": "boulevard",
    "dr": "drive", "ln": "lane", "pkwy": "parkway", "pky": "parkway", "hwy": "highway",
    "fwy": "freeway", "ct": "court", "pl": "place", "cir": "circle", "trl": "trail",
    "n": "north", "s": "south", "e": "east", "w": "west", "ste": "suite",
}
SUFFIXES = ("road|rd|street|st|avenue|ave|av|boulevard|blvd|drive|dr|lane|ln|parkway|pkwy|pky|highway|hwy|"
            "freeway|fwy|court|ct|place|pl|circle|cir|trail|trl|way|loop|plaza|plz|expressway|expy|terrace|ter")
# A street address needs a street-type word, so "7457 Suite 250" or "2603 Club" are not read as addresses.
ADDRESS_RE = re.compile(
    rf"(?<![#\w])(\d{{1,6}}(?:\s*-\s*\d{{1,6}})?)\s+((?:[NSEW]\.?\s+)?(?:[A-Za-z0-9.']+\s+){{0,4}}?(?:{SUFFIXES}))\b\.?",
    re.I)
UNIT_BEFORE_RE = re.compile(r"(?:suite|ste\.?|unit|#|floor|fl\.?|bldg\.?|building)\s*$", re.I)
SUITE_RE = re.compile(r"\b(?:suite|ste\.?|unit|#)\s*([A-Za-z0-9-]+)", re.I)
M2_TO_FT = 3.28084


# --- Evidence record --------------------------------------------------------

def record(fact, value, source, source_id=None, captured_at=None, confidence=0.5,
           evidence_url=None, status="unknown", needs_human=False, note=""):
    """One fact in the shared evidence contract. Keep every check on this shape."""
    if status not in {"agrees", "conflict", "unknown"}:
        raise ValueError(f"bad status {status!r}")
    return {
        "fact": fact, "value": value, "source": source,
        "source_id": None if source_id is None else str(source_id),
        "captured_at": captured_at, "confidence": round(float(confidence), 2),
        "evidence_url": evidence_url, "status": status,
        "needs_human": bool(needs_human), "note": note,
    }


# --- Kit access ---------------------------------------------------------------

def kit_password():
    return os.environ.get("COSTAR_KIT_PASSWORD", "").encode() or None


def iter_properties(kit_path, password=None):
    with ZipFile(kit_path) as kit, kit.open("data/commercial-property.jsonl", pwd=password) as stream:
        for line in stream:
            yield json.loads(line)


def load_property(kit_path, property_id, password=None):
    for prop in iter_properties(kit_path, password):
        if prop["id"] == property_id:
            return prop
    raise ValueError(f"CoStar property {property_id} is not in the kit.")


def scans_of(prop):
    """Matterport scan attachments, with the capture date CoStar recorded."""
    return [
        {"model_id": a.get("videoKey"), "caption": a.get("caption") or "",
         "captured_at": (a.get("originationDate") or "")[:10] or None,
         "attachment_id": a.get("attachmentMasterId"), "thumbnail": a.get("attachmentUri")}
        for a in prop.get("attachments") or []
        if a.get("videoExternalReferenceType") in MATTERPORT_TYPES and a.get("videoKey")
    ]


def unique_scans(prop):
    """One entry per model id (CoStar can attach the same scan twice), earliest date kept."""
    best = {}
    for scan in scans_of(prop):
        seen = best.get(scan["model_id"])
        if not seen or (scan["captured_at"] or "9") < (seen["captured_at"] or "9"):
            best[scan["model_id"]] = scan
    return list(best.values())


def tour_url(model_id):
    return f"https://my.matterport.com/show/?m={model_id}"


# --- Address parsing ----------------------------------------------------------

def normalize_street(name):
    words = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower()).split()
    return " ".join(STREET_WORDS.get(w, w) for w in words)


def parse_caption(caption, home_street=None):
    """Pull a street address and suite out of a scan caption, if it names one.

    An address must end in a street-type word, or name the CoStar street itself (``home_street``,
    normalized), and must not be a suite/unit number.
    """
    caption = caption or ""
    found = None
    for match in ADDRESS_RE.finditer(caption):
        if not UNIT_BEFORE_RE.search(caption[:match.start()]):
            found = (match.group(1), match.group(2))
            break
    if not found and home_street:
        core = home_street.split()[0]  # e.g. "tanner" from "tanner road"
        m = re.search(rf"(?<![#\w])(\d{{1,6}}(?:\s*-\s*\d{{1,6}})?)\s+({re.escape(core)})\b", caption, re.I)
        if m and not UNIT_BEFORE_RE.search(caption[:m.start()]):
            found = (m.group(1), m.group(2))
    suite = SUITE_RE.search(caption)
    return {
        "street_number": re.sub(r"\s+", "", found[0]) if found else None,
        "street": normalize_street(found[1]) if found else None,
        "suite": suite.group(1) if suite else None,
    }


def number_matches(caption_number, costar_number):
    """Equal, or one side is a range (8303-8317) containing the other."""
    if not caption_number or not costar_number:
        return None
    if caption_number == costar_number:
        return True
    def span(n):
        parts = [int(p) for p in re.findall(r"\d+", n)]
        return (min(parts), max(parts)) if parts else None
    a, b = span(caption_number), span(costar_number)
    return bool(a and b and a[0] <= b[1] and b[0] <= a[1])


def costar_address(prop):
    a = prop.get("primaryAddress") or {}
    street = " ".join(str(x) for x in (a.get("streetName"), a.get("streetType")) if x)
    if a.get("streetDirection"):
        street = f"{a['streetDirection']} {street}"
    return {"street_number": str(a.get("streetNumber") or "") or None, "street": normalize_street(street),
            "display": f"{a.get('streetNumber', '')} {street}".strip(),
            "latitude": a.get("latitude"), "longitude": a.get("longitude")}


GENERIC_STREET_WORDS = set(STREET_WORDS.values()) | {"freeway", "highway", "loop", "way", "interstate"}


def same_street(a, b):
    """True if the names match or share a distinctive word ("world houston parkway" ~ "world parkway");
    None if they could still be aliases (highways: "n i 45" vs "north freeway"); False otherwise."""
    if not a or not b:
        return None
    if a == b or a in b or b in a:
        return True
    words_a, words_b = set(a.split()) - GENERIC_STREET_WORDS, set(b.split()) - GENERIC_STREET_WORDS
    if words_a & words_b:
        return True
    highway = re.compile(r"\b(i|ih|us|sh|fm|freeway|highway|interstate)\b|\bi ?\d+\b")
    if highway.search(a) or highway.search(b):
        return None
    return False


# --- Checks ---------------------------------------------------------------------

def check_identity(prop):
    """Does each scan's caption name the same address as the CoStar record?"""
    home = costar_address(prop)
    out = []
    for scan in unique_scans(prop):
        parsed = parse_caption(scan["caption"], home["street"])
        common = dict(fact="scan_address", value=scan["caption"], source="matterport",
                      source_id=scan["model_id"], captured_at=scan["captured_at"],
                      evidence_url=tour_url(scan["model_id"]))
        if not parsed["street_number"]:
            out.append(record(**common, confidence=0.3, status="unknown",
                              note=f"Scan caption names no street address; cannot confirm it is {home['display']}."))
            continue
        number_ok = number_matches(parsed["street_number"], home["street_number"])
        street_ok = same_street(parsed["street"], home["street"])
        if number_ok and street_ok is None:
            out.append(record(**common, confidence=0.5, status="unknown", needs_human=True,
                              note=(f"Same street number as CoStar ({home['display']}) but the street is written as "
                                    f"'{parsed['street'].title()}', likely a highway alias. Confirm it is the same "
                                    "building.")))
            continue
        if number_ok and street_ok:
            out.append(record(**common, confidence=0.9, status="agrees",
                              note=f"Caption address matches CoStar ({home['display']})."
                                   + (f" Scan covers suite {parsed['suite']}." if parsed["suite"] else "")))
        else:
            what = "street number" if street_ok else "street number and street"
            out.append(record(
                **common, confidence=0.85 if street_ok else 0.6, status="conflict", needs_human=True,
                note=(f"Scan is captioned {parsed['street_number']} {parsed['street'].title()} but CoStar's address is "
                      f"{home['display']} (different {what}). It may be a sibling building in the same park or a "
                      "mislinked scan. Confirm which building was scanned before using its rooms or measurements.")))
    return out


def check_scan_dates(prop):
    """Real capture date per scan, from CoStar's attachment record."""
    out = []
    for scan in unique_scans(prop):
        out.append(record(
            fact="scan_captured_at", value=scan["captured_at"], source="costar",
            source_id=scan["attachment_id"], captured_at=scan["captured_at"],
            confidence=0.8 if scan["captured_at"] else 0.2, evidence_url=tour_url(scan["model_id"]),
            status="agrees" if scan["captured_at"] else "unknown", needs_human=not scan["captured_at"],
            note=("CoStar's originationDate for this scan attachment (when CoStar added it; the scan itself can be "
                  "older). Use it, not Matterport's 'created' (the re-hosting date), as the latest date the scan can "
                  "describe when comparing with tenancy or listing dates.")))
    return out


def matterport_rooms(model_id):
    key, token = os.environ.get("MATTERPORT_API_KEY"), os.environ.get("MATTERPORT_API_TOKEN")
    if not key or not token:
        raise RuntimeError("MATTERPORT_API_KEY / MATTERPORT_API_TOKEN not set")
    query = ("query R($id: ID!) { model(id: $id) { id name floors { rooms { id label "
             "dimensionEstimates(units: metric) { area height } } } } }")
    auth = base64.b64encode(f"{key}:{token}".encode()).decode()
    req = Request(MATTERPORT_GRAPH, data=json.dumps({"query": query, "variables": {"id": model_id}}).encode(),
                  headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"})
    with urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())
    if payload.get("errors"):
        raise RuntimeError("; ".join(e["message"] for e in payload["errors"]))
    model = (payload.get("data") or {}).get("model") or {}
    return [r for f in model.get("floors") or [] for r in f.get("rooms") or []]


def costar_ceiling_ft(prop):
    for key in ("propertyFlex", "propertyIndustrial", "propertyOffice", "propertyRetail"):
        height = ((prop.get(key) or {}).get("structural") or {}).get("ceilingHeightFeet")
        if height:
            return height, key
    return None, None


def check_clear_height(prop, rooms_by_model):
    """CoStar ceiling height vs Matterport measured heights (0 means not measured)."""
    costar_ft, where = costar_ceiling_ft(prop)
    out = [record(fact="ceiling_height_ft", value=costar_ft, source="costar", source_id=prop["id"],
                  confidence=0.6 if costar_ft else 0.2, status="unknown" if not costar_ft else "agrees",
                  needs_human=True,
                  note=(f"CoStar {where}.structural.ceilingHeightFeet. Researched value, not a site measurement; "
                        "usable clear height under beams, sprinklers and lights must be verified on site.")
                       if costar_ft else "CoStar has no ceiling height for this property.")]
    for model_id, rooms in rooms_by_model.items():
        # Compare the main space only: building ceiling height describes the big open area, and
        # smaller measured rooms (offices with dropped ceilings) would raise false conflicts.
        dims = [(r, r.get("dimensionEstimates") or {}) for r in rooms]
        main_room, main = max(dims, key=lambda rd: rd[1].get("area") or 0, default=(None, {}))
        label = (main_room or {}).get("label") or "unlabeled room"
        area_ft2 = round((main.get("area") or 0) * M2_TO_FT ** 2)
        height_m = main.get("height") or 0
        if not main_room or height_m <= 0:
            out.append(record(
                fact="ceiling_height_ft", value=None, source="matterport", source_id=model_id,
                confidence=0.1, evidence_url=tour_url(model_id), status="unknown", needs_human=True,
                note=(f"Largest scanned space ({label}, ~{area_ft2:,} sq ft) has no measured height (Matterport "
                      "reports 0, common in large open spaces). Clear height stays unverified; smaller rooms' "
                      "heights are not used because they do not describe the main space.")))
            continue
        main_ft = round(height_m * M2_TO_FT, 1)
        agrees = costar_ft is not None and abs(main_ft - costar_ft) <= max(2.0, 0.15 * costar_ft)
        out.append(record(fact="ceiling_height_ft", value=main_ft, source="matterport", source_id=model_id,
                          confidence=0.7, evidence_url=tour_url(model_id),
                          status="unknown" if costar_ft is None else ("agrees" if agrees else "conflict"),
                          needs_human=not agrees,
                          note=f"Measured height of the largest scanned space ({label}, ~{area_ft2:,} sq ft)."
                               + (f" CoStar says {costar_ft} ft." if costar_ft else "")))
    return out


def check_flood(prop):
    home = costar_address(prop)
    lat, lon = home["latitude"], home["longitude"]
    params = urlencode({"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326,
                        "spatialRel": "esriSpatialRelIntersects", "outFields": "FLD_ZONE,ZONE_SUBTY,SFHA_TF",
                        "returnGeometry": "false", "f": "json"})
    url = f"{FEMA_NFHL}?{params}"
    with urlopen(Request(url, headers={"User-Agent": "property-evidence-check"}), timeout=30) as resp:
        data = json.loads(resp.read())
    zones = [f["attributes"] for f in data.get("features") or []]
    today = date.today().isoformat()
    if not zones:
        return [record(fact="flood_zone", value=None, source="public:fema-nfhl", captured_at=today,
                       confidence=0.3, evidence_url=url, status="unknown", needs_human=True,
                       note="No mapped FEMA flood zone at the CoStar pin (unmapped area or service gap).")]
    zone = zones[0]
    special = zone.get("SFHA_TF") == "T"
    return [record(fact="flood_zone", value=zone.get("FLD_ZONE"), source="public:fema-nfhl", captured_at=today,
                   confidence=0.8, evidence_url=url, status="agrees", needs_human=special,
                   note=f"{zone.get('ZONE_SUBTY') or 'Zone ' + str(zone.get('FLD_ZONE'))}. "
                        + ("Special Flood Hazard Area: flood insurance is typically required for financed purchases."
                           if special else "Outside the Special Flood Hazard Area.")
                        + " Point lookup at the CoStar pin; the building footprint can cross zones.")]


# --- Time-aware occupancy -------------------------------------------------------

RECENT_MOVE_IN_DAYS = 180  # the scan can predate CoStar's attachment date by this much
ENDING_SOON_DAYS = 365  # landlords market a suite this far ahead of a lease ending


def suite_key(suite):
    """'C-1A', 'C1A ', 'c 1a' -> 'C1A'."""
    return re.sub(r"[^A-Z0-9]", "", str(suite or "").upper())


def load_tenancies(kit_path, property_ids=None, password=None):
    """{property_id: [tenancy]} from CoStar's location-occupancy, deduplicated, with tenant names.

    A tenancy is {tenant, suites, start, end, square_feet, id}; end None = still in place.
    Suites come from the space rows and from the tenant's company record, since CoStar
    often fills only one of them.
    """
    want = set(property_ids) if property_ids is not None else None
    rows = {}
    with ZipFile(kit_path) as kit:
        with kit.open("data/location-occupancy.jsonl", pwd=password) as stream:
            for line in stream:
                row = json.loads(line)
                if want is None or row["propertyId"] in want:
                    rows.setdefault(row["propertyId"], []).append(row)
        locations = {r.get("tenantLocationId") for rs in rows.values() for r in rs} - {None}
        companies = {}
        with kit.open("data/company-detail.jsonl", pwd=password) as stream:
            for line in stream:
                company = json.loads(line)
                if company["id"] in locations:
                    companies[company["id"]] = company
    out = {}
    for pid, raw in rows.items():
        seen, tenancies = set(), []
        for row in raw:
            company = companies.get(row.get("tenantLocationId")) or {}
            spaces = row.get("spaces") or []
            suites = {suite_key(sp.get("suite")) for sp in spaces} | {suite_key(company.get("suite"))}
            start = (row.get("moveInDate") or row.get("fromDate") or "")[:10] or None
            end = (row.get("toDate") or "")[:10] or None
            sqft = sum(sp.get("squareFeetOccupied") or 0 for sp in spaces) or None
            key = (row.get("tenantLocationId"), start, end, frozenset(suites), sqft)
            if key in seen or not start:
                continue
            seen.add(key)
            tenancies.append({"id": row["id"], "tenant": company.get("name"), "suites": suites - {""},
                              "start": start, "end": end, "square_feet": sqft})
        out[pid] = tenancies
    return out


def describe(t):
    name = t["tenant"] or "an unnamed tenant"
    size = f", {t['square_feet']:,.0f} sq ft" if t["square_feet"] else ""
    return f"{name} ({t['start']} to {t['end'] or 'present'}{size})"


def check_occupancy(prop, tenancies):
    """For each scan that names a suite: who did CoStar have in that suite on the scan date?

    Most scans market vacant space, so an active lease on the scan date is a conflict
    (CoStar's tenant data is stale, or the scan shows someone's occupied space). Leases
    that start after the scan or end before it are the usual false alarms and agree.
    """
    home = costar_address(prop)
    out = []
    for scan in unique_scans(prop):
        parsed = parse_caption(scan["caption"], home["street"])
        if not parsed["suite"]:
            continue
        common = dict(fact="suite_occupancy_at_scan", source="costar", captured_at=scan["captured_at"],
                      evidence_url=tour_url(scan["model_id"]))
        suite = parsed["suite"]
        elsewhere = parsed["street_number"] and not number_matches(parsed["street_number"], home["street_number"])
        if elsewhere:
            out.append(record(**common, value=None, source_id=scan["model_id"], confidence=0.2, status="unknown",
                              note=(f"Scan is captioned for suite {suite} at {parsed['street_number']}, not "
                                    f"{home['display']}, so this building's tenancies were not compared.")))
            continue
        when = scan["captured_at"]
        if not when:
            out.append(record(**common, value=None, source_id=scan["model_id"], confidence=0.1, status="unknown",
                              needs_human=True, note=f"Scan of suite {suite} has no CoStar date to compare with."))
            continue
        matches = [t for t in tenancies if suite_key(suite) in t["suites"]]
        active = [t for t in matches if t["start"] <= when and (t["end"] is None or when <= t["end"])]
        settled = [t for t in active
                   if (date.fromisoformat(when) - date.fromisoformat(t["start"])).days > RECENT_MOVE_IN_DAYS]
        ids = ",".join(str(t["id"]) for t in (active or matches)) or scan["model_id"]
        ending = [t for t in settled
                  if t["end"] and (date.fromisoformat(t["end"]) - date.fromisoformat(when)).days <= ENDING_SOON_DAYS]
        settled = [t for t in settled if t not in ending]
        if settled:
            out.append(record(
                **common, value="; ".join(t["tenant"] or "unnamed tenant" for t in settled), source_id=ids,
                confidence=0.6, status="conflict", needs_human=True,
                note=(f"Suite {suite} was scanned by {when} (\"{scan['caption'].strip()}\"), but CoStar lists "
                      + "; ".join(describe(t) for t in settled) + " in that suite on that date. Marketing scans are "
                      "usually of empty space: check the tour's photos, then ask the broker whether the tenant "
                      "has left (CoStar's record is stale) or the scan shows the tenant's own space, e.g. a sublease "
                      "or coworking operator.")))
        elif ending:
            out.append(record(
                **common, value="; ".join(t["tenant"] or "unnamed tenant" for t in ending), source_id=ids,
                confidence=0.5, status="unknown", needs_human=True,
                note=(f"Suite {suite} was scanned by {when} (\"{scan['caption'].strip()}\") while CoStar lists "
                      + "; ".join(describe(t) for t in ending) + f" in it, with the lease ending within a year. "
                      "Landlords often market space before a tenant leaves. If the tour shows the suite empty, "
                      "CoStar's move-out date is late; if it shows the tenant's furniture, the space isn't free "
                      "until the lease ends.")))
        elif active:
            out.append(record(
                **common, value="; ".join(t["tenant"] or "unnamed tenant" for t in active), source_id=ids,
                confidence=0.4, status="unknown", needs_human=True,
                note=(f"CoStar lists " + "; ".join(describe(t) for t in active) + f" in suite {suite}, moving in "
                      f"within {RECENT_MOVE_IN_DAYS} days before the scan's CoStar date ({when}). The scan can be "
                      "older than that date, so it may show the suite before move-in. Check the photos.")))
        elif matches:
            later = sorted((t for t in matches if t["start"] > when), key=lambda t: t["start"])
            earlier = sorted((t for t in matches if t["end"] and t["end"] < when), key=lambda t: t["end"])
            parts = []
            if earlier:
                parts.append(f"the previous tenant, {describe(earlier[-1])}, had left before the scan")
            if later:
                parts.append(f"{describe(later[0])} moved in after the scan")
            out.append(record(
                **common, value="vacant at scan", source_id=ids, confidence=0.7, status="agrees",
                note=(f"No CoStar tenant in suite {suite} on the scan date ({when}): " + " and ".join(parts)
                      + ". An empty suite in the tour is expected, not a contradiction.")))
        else:
            out.append(record(
                **common, value=None, source_id=scan["model_id"], confidence=0.3, status="unknown",
                note=f"CoStar has no tenancy recorded for suite {suite}, so occupancy at the scan date can't be checked."))
    return out


# --- CoStar size consistency ------------------------------------------------------

SIZE_TOLERANCE = 0.2


def check_size(prop):
    """Do CoStar's own size fields add up? (GBA vs typical floor x stories, rentable vs gross.)"""
    gba = prop.get("grossBuildingAreaSquareFeet")
    typical = prop.get("grossTypicalFloorSquareFeet")
    rba = prop.get("rentableBuildingAreaSquareFeet")
    stories = prop.get("numStoriesAboveGrade")
    common = dict(source="costar", source_id=prop["id"])
    out = []
    if gba and typical and stories:
        implied = typical * stories
        ratio = gba / implied
        ok = abs(ratio - 1) <= SIZE_TOLERANCE
        out.append(record(
            fact="gross_area_vs_floors", value=round(ratio, 2), **common, confidence=0.7,
            status="agrees" if ok else "conflict", needs_human=not ok,
            note=(f"CoStar gross building area {gba:,.0f} sq ft vs typical floor {typical:,.0f} sq ft x {stories} "
                  f"stor{'y' if stories == 1 else 'ies'} = {implied:,.0f} sq ft ({ratio:.2f}x). "
                  + ("Consistent." if ok else "These can't all be right: one of the size, floor or story count is "
                                              "wrong (or a mezzanine/basement is counted). Ask for a measured plan "
                                              "before pricing per sq ft."))))
    else:
        out.append(record(fact="gross_area_vs_floors", value=None, **common, confidence=0.1, status="unknown",
                          note="CoStar is missing gross area, typical floor or story count."))
    if gba and rba and rba > gba * 1.02:
        out.append(record(
            fact="rentable_vs_gross_area", value=round(rba / gba, 2), **common, confidence=0.7, status="conflict",
            needs_human=True,
            note=f"Rentable area {rba:,.0f} sq ft is larger than gross area {gba:,.0f} sq ft, which can't be true."))
    return out


def reconcile(prop, offline=False, tenancies=None):
    """All checks for one property. Pass tenancies (from load_tenancies) to add the occupancy check."""
    results = {"property_id": prop["id"], "address": costar_address(prop)["display"],
               "records": check_identity(prop) + check_scan_dates(prop) + check_size(prop), "errors": {}}
    if tenancies is not None:
        results["records"] += check_occupancy(prop, tenancies)
    rooms_by_model = {}
    if not offline:
        for scan in unique_scans(prop):
            try:
                rooms_by_model[scan["model_id"]] = matterport_rooms(scan["model_id"])
            except Exception as error:  # provider errors are reported, never fatal
                results["errors"][f"matterport:{scan['model_id']}"] = str(error)
    results["records"] += check_clear_height(prop, rooms_by_model)
    if not offline:
        try:
            results["records"] += check_flood(prop)
        except Exception as error:
            results["errors"]["fema"] = str(error)
    results["conflicts"] = sum(r["status"] == "conflict" for r in results["records"])
    return results


def scan_identity_market(kit_path, market, password=None):
    """Identity check across every scanned property in a market (offline, captions only)."""
    market_id = MARKETS[market]
    checked = conflicts = no_address = 0
    examples = []
    for prop in iter_properties(kit_path, password):
        if (prop.get("primaryAddress") or {}).get("researchMarketId") != market_id or not scans_of(prop):
            continue
        records = check_identity(prop)
        checked += 1
        bad = [r for r in records if r["status"] == "conflict"]
        no_address += all(r["status"] == "unknown" for r in records)
        if bad:
            conflicts += 1
            if len(examples) < 15:
                examples.append({"property_id": prop["id"], "costar": costar_address(prop)["display"],
                                 "scan_caption": bad[0]["value"], "model_id": bad[0]["source_id"]})
    return {"market": market, "properties_checked": checked, "with_address_conflict": conflicts,
            "captions_without_address": no_address, "examples": examples}


def scan_occupancy_market(kit_path, market, password=None):
    """Occupancy check for every suite-named scan in a market (offline, kit only)."""
    market_id = MARKETS[market]
    props = [p for p in iter_properties(kit_path, password)
             if (p.get("primaryAddress") or {}).get("researchMarketId") == market_id and scans_of(p)]
    tenancies = load_tenancies(kit_path, {p["id"] for p in props}, password)
    counts = {"agrees": 0, "conflict": 0, "unknown": 0}
    examples = []
    for prop in props:
        for r in check_occupancy(prop, tenancies.get(prop["id"], [])):
            counts[r["status"]] += 1
            if r["status"] == "conflict" and len(examples) < 15:
                examples.append({"property_id": prop["id"], "costar": costar_address(prop)["display"],
                                 "scan_date": r["captured_at"], "tenant": r["value"], "tour": r["evidence_url"]})
    return {"market": market, "suite_scans_checked": sum(counts.values()), "by_status": counts,
            "examples": examples}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--property-id", type=int)
    parser.add_argument("--scan-identity", choices=sorted(MARKETS))
    parser.add_argument("--scan-occupancy", choices=sorted(MARKETS))
    parser.add_argument("--offline", action="store_true", help="Skip Matterport and FEMA network calls.")
    parser.add_argument("--json", type=Path, help="Write results to this file.")
    args = parser.parse_args()
    if not (args.property_id or args.scan_identity or args.scan_occupancy):
        parser.error("pass --property-id, --scan-identity or --scan-occupancy")
    password = kit_password()
    try:
        if args.scan_identity:
            result = scan_identity_market(args.kit, args.scan_identity, password)
        elif args.scan_occupancy:
            result = scan_occupancy_market(args.kit, args.scan_occupancy, password)
        else:
            tenancies = load_tenancies(args.kit, {args.property_id}, password).get(args.property_id, [])
            result = reconcile(load_property(args.kit, args.property_id, password), offline=args.offline,
                               tenancies=tenancies)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")
    text = json.dumps(result, indent=2)
    if args.json:
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    sys.exit(main())
