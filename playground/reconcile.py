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

Usage:
  python3 playground/reconcile.py --kit ~/Downloads/costar-hackathon-kit.zip --property-id 23296
  python3 playground/reconcile.py --kit ... --scan-identity Houston   # identity check across a market
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


def reconcile(prop, offline=False):
    results = {"property_id": prop["id"], "address": costar_address(prop)["display"],
               "records": check_identity(prop) + check_scan_dates(prop), "errors": {}}
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--property-id", type=int)
    parser.add_argument("--scan-identity", choices=sorted(MARKETS))
    parser.add_argument("--offline", action="store_true", help="Skip Matterport and FEMA network calls.")
    parser.add_argument("--json", type=Path, help="Write results to this file.")
    args = parser.parse_args()
    if not args.property_id and not args.scan_identity:
        parser.error("pass --property-id or --scan-identity")
    password = kit_password()
    try:
        if args.scan_identity:
            result = scan_identity_market(args.kit, args.scan_identity, password)
        else:
            result = reconcile(load_property(args.kit, args.property_id, password), offline=args.offline)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")
    text = json.dumps(result, indent=2)
    if args.json:
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    sys.exit(main())
