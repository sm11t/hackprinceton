"""Physical fit: can this building (or listed suite) physically support the proposed use?

Every fact is an evidence record in the shared contract (see reconcile.record):

    {fact, value, source, source_id, captured_at, confidence, evidence_url,
     status: agrees|conflict|unknown, needs_human, note}

For fit checks, status means: "agrees" = the evidence supports the use, "conflict" =
the evidence rules the use out, "unknown" = the data cannot settle it (a question for
the broker or inspector, never a guess).

Sources used here:
  CoStar kit   building size, clear height, docks, parking, sprinklers, power, listed suites
  Vexcel       footprint of the building under the CoStar pin, roof, rooftop units, vehicles
  Matterport   measured area and height of scanned spaces, real scan dates (via CoStar)

Usage:
  python3 playground/space_fit.py --kit ~/Downloads/costar-hackathon-kit.zip --property-id 23296 --use pickleball
  python3 playground/space_fit.py --kit <unzipped kit dir> --property-id 23296 --use daycare --offline
"""
import argparse
import io
import json
import math
import os
import sys
from pathlib import Path
from zipfile import ZipFile

from exterior import exterior_records, fetch_property, roof_height_ft
from reconcile import costar_address, costar_ceiling_ft, record

# --- Use requirements ------------------------------------------------------------
# Thresholds are only stated where a source supports them. Everything else is a
# checklist item that the data cannot answer and must be verified.

SOURCES = {
    "usa-pickleball-rule-3a3": "https://www.mypickleballconnect.com/guides/pickleball-court-dimensions/",
    "pickleball-ceiling-guidance": "https://millersports.com/pickleball-court-size/",
    "tx-746-indoor": "https://regulations.justia.com/states/texas/title-26/part-1/chapter-746/subchapter-t/division-1",
    "tx-746-4301-outdoor": "https://regulations.justia.com/states/texas/title-26/part-1/chapter-746/subchapter-t/division-2/section-746-4301",
    "houston-26-492": "https://houstontx.gov/planning/Off-Street-Parking-Ordinance.html",
}

USES = {
    "pickleball": {
        "label": "Indoor pickleball",
        "unit": "court",
        # USA Pickleball rule 3.A.3 total playing area per court: 30x60 ft minimum, 34x64 ft preferred.
        "area_per_unit_sf": 30 * 60,
        "preferred_area_per_unit_sf": 34 * 64,
        "area_source": "usa-pickleball-rule-3a3",
        # No official USA Pickleball ceiling figure was found; 18 ft is the commonly cited
        # recreational minimum and 20+ ft is preferred. Treated as guidance, low confidence.
        "min_clear_height_ft": 18,
        "preferred_clear_height_ft": 20,
        "height_source": "pickleball-ceiling-guidance",
        "height_is_official": False,
        "checks": [
            "Columns or posts inside the court + run-off area (needs a measured plan)",
            "Floor flatness and surface (sealed concrete or sport tile)",
            "Lighting, ventilation and acoustics for a hard-court sport",
            "Parking for peak sessions (Houston Sec. 26-492 ratio for the use classification)",
        ],
    },
    "gym": {
        "label": "Gym & fitness",
        "checks": [
            "Floor load for free weights and equipment (CoStar floorLoad if recorded)",
            "Clear height for overhead lifts or rigs",
            "HVAC capacity and electrical service",
            "Changing rooms and showers (plumbing)",
            "Parking for peak classes (Houston Sec. 26-492)",
        ],
    },
    "restaurant": {
        "label": "Restaurant",
        "checks": [
            "Kitchen hood and exhaust route through roof or wall",
            "Grease interceptor and sewer connection",
            "Gas service, water and electrical capacity (3-phase)",
            "Restrooms, accessible seating and fire review",
            "Parking for the restaurant classification (Houston Sec. 26-492)",
        ],
    },
    "daycare": {
        "label": "Daycare",
        "unit": "child",
        # 26 TAC ch. 746 subch. T: 30 sq ft indoor activity space per licensed child;
        # §746.4301: 80 sq ft outdoor activity space per child using the area at one time.
        "indoor_sf_per_child": 30,
        "outdoor_sf_per_child": 80,
        "indoor_source": "tx-746-indoor",
        "outdoor_source": "tx-746-4301-outdoor",
        "checks": [
            "Indoor activity space excludes restrooms, kitchens, halls and offices (needs a measured plan)",
            "Fenced outdoor play area on or next to the site (HHSC approval if not connected)",
            "Child-height restrooms, egress, fire alarm and sprinkler review",
            "Licensing inspection and landlord consent for a childcare use",
        ],
    },
    "workshop": {
        "label": "Workshop & classes",
        "checks": [
            "Room dimensions, occupant load and circulation",
            "Accessible entrance, toilets and after-hours access",
            "Power, ventilation and equipment-specific needs",
        ],
    },
}

# --- Kit access (zip from Slack, or an unzipped folder) -------------------------------


def kit_password():
    return os.environ.get("COSTAR_KIT_PASSWORD", "").encode() or None


def kit_lines(kit_path, member, password=None):
    """Yield lines of a kit file from either the encrypted zip or an unzipped folder."""
    kit_path = Path(kit_path)
    if kit_path.is_dir():
        with open(kit_path / member, encoding="utf-8") as fh:
            yield from fh
        return
    with ZipFile(kit_path) as kit, kit.open(member, pwd=password) as stream:
        yield from io.TextIOWrapper(stream, encoding="utf-8")


def load_property(kit_path, property_id, password=None):
    needle = str(property_id)
    for line in kit_lines(kit_path, "data/commercial-property.jsonl", password):
        if needle not in line:  # cheap prefilter before parsing a large record
            continue
        prop = json.loads(line)
        if prop["id"] == property_id:
            return prop
    raise ValueError(f"CoStar property {property_id} is not in the kit.")


def listed_spaces(kit_path, property_id, password=None):
    """Active for-lease spaces in THIS building (not the whole park listing)."""
    out = []
    for line in kit_lines(kit_path, "data/commercial-listing-summary.jsonl", password):
        if str(property_id) not in line:
            continue
        listing = json.loads(line)
        lease = listing.get("forLeaseSummary")
        if not lease or listing.get("listingStatus") != 1:  # 1 = Active
            continue
        for space in lease.get("spaces") or []:
            if space.get("propertyId") == property_id:
                out.append({
                    "listing_id": listing["id"], "suite": space.get("suite"),
                    "square_feet": space.get("squareFeetMax"),
                    "available_on": (space.get("availableOnDate") or "")[:10] or None,
                    "on_market": (space.get("dateOnMarket") or "")[:10] or None,
                })
    return out


# --- CoStar building facts -----------------------------------------------------------


def subtype_block(prop):
    for key in ("propertyIndustrial", "propertyFlex", "propertyOffice", "propertyRetail"):
        if prop.get(key):
            return key, prop[key]
    return None, {}


def costar_facts(prop):
    """Physical facts CoStar's researchers recorded for the building."""
    pid = prop["id"]
    key, sub = subtype_block(prop)
    parking = sum((p.get("totalSpaces") or 0) for p in prop.get("parking") or [])
    docks = (sub.get("numExternalLoadingDocks") or 0) + (sub.get("numInternalLoadingDocks") or 0)
    bays = sub.get("driveInBays") or {}
    drive_in = bays.get("numDriveInBays")
    bay_size = (f" Doors {bays['numFeetWide']:g} ft wide x {bays['numFeetHigh']:g} ft high."
                if bays.get("numFeetWide") and bays.get("numFeetHigh") else "")
    floor_load = (sub.get("structural") or {}).get("floorLoadPoundsPerSquareFoot")
    electric = sub.get("electric") or {}
    phases = electric.get("numElectricCurrentPhases")
    amps = electric.get("ampsHigh") or electric.get("ampsLow")
    volts = "-".join(str(v) for v in dict.fromkeys(x for x in (electric.get("voltsLow"), electric.get("voltsHigh")) if x))
    power_note = ", ".join(x for x in (f"{phases}-phase" if phases else "", f"{amps} A" if amps else "",
                                         f"{volts} V" if volts else "",
                                         "heavy power (800 A+)" if electric.get("hasHeavyPower") else "") if x)
    rec = lambda fact, value, note, confidence=0.6: record(  # noqa: E731
        fact, value, "costar", pid, None, confidence if value not in (None, 0) else 0.2,
        status="agrees" if value not in (None, 0) else "unknown", note=note)
    return [
        rec("building_area_sf", prop.get("grossBuildingAreaSquareFeet"),
            "CoStar gross building area (GBA), the whole building to the outside walls."),
        rec("rentable_area_sf", prop.get("rentableBuildingAreaSquareFeet"), "CoStar rentable building area (RBA)."),
        rec("typical_floor_sf", prop.get("grossTypicalFloorSquareFeet"), "CoStar typical floor size."),
        rec("stories", prop.get("numStoriesAboveGrade"), "CoStar stories above grade."),
        rec("loading_docks", docks or None, f"CoStar {key or 'property'} external + internal docks."
            if docks else "CoStar records no loading docks (unknown, not necessarily none)."),
        rec("drive_in_bays", drive_in, "CoStar drive-in (grade-level) bays." + bay_size),
        rec("electrical_service", power_note or None,
            f"CoStar electrical service: {power_note}. Capacity serving a specific suite needs an electrician."
            if power_note else "CoStar records no electrical service details."),
        rec("parking_spaces", parking or None, "CoStar total parking spaces for the property (shared across tenants)."),
        rec("sprinklers", prop.get("hasSprinklers"), "CoStar sprinkler flag; type and coverage need verification."),
        rec("floor_load_psf", floor_load, "CoStar floor load capacity, upper end of the recorded range."),
    ]


# --- Fit evaluation ------------------------------------------------------------------


def best_area(candidates):
    """Pick the most specific trustworthy area: a listed suite beats the whole building."""
    for label, value, source, source_id in candidates:
        if value:
            return label, float(value), source, source_id
    return None, None, None, None


def evaluate_use(use_id, area, ceiling_ft, ceiling_source, roof_ft=None):
    """Return evidence records judging fit for one use from the best area + clear height.

    roof_ft (Vexcel roof height above ground) is a hard upper bound: no interior is taller than its roof."""
    use = USES[use_id]
    area_label, area_sf, area_src, area_id = area
    out = []
    need_ft = use.get("min_clear_height_ft")
    if need_ft and roof_ft:
        ok = roof_ft >= need_ft
        out.append(record(
            f"{use_id}_roof_upper_bound", roof_ft, "vexcel", None, confidence=0.6,
            status="agrees" if ok else "conflict", needs_human=not ok,
            note=(f"The roof is {roof_ft:g} ft above ground, so the inside cannot exceed that; "
                  + (f"it leaves room for the {need_ft} ft clear height {use['label'].lower()} needs, but the usable "
                     "height under the roof structure still has to be measured."
                     if ok else f"that is below the {need_ft} ft clear height {use['label'].lower()} needs."))))
    if use_id == "pickleball":
        if area_sf:
            courts = math.floor(area_sf / use["area_per_unit_sf"])
            preferred = math.floor(area_sf / use["preferred_area_per_unit_sf"])
            out.append(record(
                "pickleball_courts_by_area", courts, area_src, area_id, confidence=0.5,
                evidence_url=SOURCES[use["area_source"]],
                status="agrees" if courts >= 1 else "conflict", needs_human=True,
                note=(f"{area_label} of {area_sf:,.0f} sq ft holds at most {courts} court(s) at the 30x60 ft minimum "
                      f"playing area ({preferred} at the preferred 34x64 ft). Upper bound: columns, support rooms "
                      "and circulation reduce it; needs a measured plan.")))
        else:
            out.append(record("pickleball_courts_by_area", None, "costar", None, confidence=0.1, status="unknown",
                              needs_human=True, note="No usable area recorded for the building or a listed suite."))
        need = use["min_clear_height_ft"]
        if ceiling_ft is None:
            out.append(record("pickleball_clear_height", None, ceiling_source or "costar", None, confidence=0.1,
                              evidence_url=SOURCES[use["height_source"]], status="unknown", needs_human=True,
                              note=f"Clear height is not recorded or measured; indoor play is commonly planned at "
                                   f"{need}+ ft (unofficial guidance). Ask for a measured clear height."))
        else:
            ok = ceiling_ft >= need
            pref = ceiling_ft >= use["preferred_clear_height_ft"]
            out.append(record(
                "pickleball_clear_height", ceiling_ft, ceiling_source, None, confidence=0.4,
                evidence_url=SOURCES[use["height_source"]], status="agrees" if ok else "conflict", needs_human=True,
                note=(f"Recorded clear height {ceiling_ft:g} ft vs a commonly cited {need} ft minimum "
                      f"({use['preferred_clear_height_ft']}+ ft preferred); "
                      + ("meets the minimum" if ok else "below the minimum")
                      + ("" if pref else ", below the preferred height")
                      + ". Guidance is not an official USA Pickleball rule; lights, beams and sprinklers lower the "
                        "usable height.")))
    elif use_id == "daycare":
        if area_sf:
            kids = math.floor(area_sf / use["indoor_sf_per_child"])
            outdoor_needed = use["outdoor_sf_per_child"] * max(1, math.ceil(kids * 0.25))
            out.append(record(
                "daycare_capacity_by_indoor_area", kids, area_src, area_id, confidence=0.4,
                evidence_url=SOURCES[use["indoor_source"]], status="agrees" if kids >= 1 else "conflict",
                needs_human=True,
                note=(f"At 30 sq ft of indoor activity space per child (Texas 26 TAC ch. 746), {area_label} of "
                      f"{area_sf:,.0f} sq ft is an upper bound of {kids} children; restrooms, kitchens, halls and "
                      "offices do not count, so the licensed number is lower.")))
            out.append(record(
                "daycare_outdoor_space_needed_sf", outdoor_needed, "public:tx-746-4301", None, confidence=0.5,
                evidence_url=SOURCES[use["outdoor_source"]], status="unknown", needs_human=True,
                note=(f"Outdoor play area must give 80 sq ft per child outside at one time and cover at least 25% of "
                      f"licensed capacity: about {outdoor_needed:,} sq ft for {kids} children. No fenced play area is "
                      "recorded; check the site plan or a nearby approved space.")))
        else:
            out.append(record("daycare_capacity_by_indoor_area", None, "costar", None, confidence=0.1,
                              status="unknown", needs_human=True, note="No usable area recorded."))
    for item in use["checks"]:
        out.append(record("verify", item, "checklist", None, confidence=0.0, status="unknown", needs_human=True,
                          note=f"{use['label']}: not answerable from CoStar, Matterport or Vexcel data; ask the "
                               "broker, landlord or inspector."))
    return out


def verdict(fit_records):
    """Summarise the use-specific judgements (not general building facts or checklist items):
    a hard conflict rules the use out, an unknown means 'investigate', otherwise the data supports it.
    'supported' still carries the checklist: it means nothing in the data rules the use out."""
    judged = [r for r in fit_records if r["source"] != "checklist"]
    if not judged:
        return "investigate"
    if any(r["status"] == "conflict" for r in judged):
        return "does_not_fit"
    if any(r["status"] == "unknown" for r in judged):
        return "investigate"
    return "supported"


def space_fit(prop, use_id, spaces=None, suite=None, vexcel=None):
    """Fit report for one property and proposed use.

    vexcel: a Vexcel property/extract response for the CoStar pin (see exterior.fetch_property), or None."""
    if use_id not in USES:
        raise ValueError(f"Unknown use {use_id!r}; choose one of {', '.join(USES)}")
    spaces = spaces or []
    chosen = next((s for s in spaces if suite and str(s["suite"]).lower() == str(suite).lower()), None) \
        or max(spaces, key=lambda s: s["square_feet"] or 0, default=None)
    records = costar_facts(prop)
    for space in spaces:
        records.append(record(
            "listed_space_sf", space["square_feet"], "costar", space["listing_id"], space["on_market"],
            confidence=0.7, status="agrees" if space["square_feet"] else "unknown",
            note=(f"Active listing: suite {space['suite'] or '(unnamed)'}, available "
                  f"{space['available_on'] or 'date not given'}. Advertised size can be rounded.")))
    area = best_area([
        (f"listed suite {chosen['suite'] or '(unnamed)'}", (chosen or {}).get("square_feet"), "costar",
         (chosen or {}).get("listing_id")),
        ("the building (RBA)", prop.get("rentableBuildingAreaSquareFeet"), "costar", prop["id"]),
        ("the building (GBA)", prop.get("grossBuildingAreaSquareFeet"), "costar", prop["id"]),
    ]) if chosen else best_area([
        ("the building (RBA)", prop.get("rentableBuildingAreaSquareFeet"), "costar", prop["id"]),
        ("the building (GBA)", prop.get("grossBuildingAreaSquareFeet"), "costar", prop["id"]),
    ])
    floor_sf = prop.get("grossTypicalFloorSquareFeet") or (
        (prop.get("grossBuildingAreaSquareFeet") or 0) / (prop.get("numStoriesAboveGrade") or 1)) or None
    ext = exterior_records(prop, vexcel, floor_sf)[0] if vexcel else []
    records += ext
    ceiling_ft, _ = costar_ceiling_ft(prop)
    fit = evaluate_use(use_id, area, ceiling_ft, "costar" if ceiling_ft else None, roof_height_ft(ext))
    return {
        "property_id": prop["id"], "address": costar_address(prop)["display"], "use": use_id,
        "use_label": USES[use_id]["label"], "suite": (chosen or {}).get("suite"),
        "area_basis": area[0], "verdict": verdict(fit), "records": records + fit, "errors": {},
        "sources": SOURCES,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kit", type=Path, required=True, help="Kit zip (with COSTAR_KIT_PASSWORD) or unzipped folder")
    parser.add_argument("--property-id", type=int, required=True)
    parser.add_argument("--use", choices=sorted(USES), required=True)
    parser.add_argument("--suite", help="Evaluate this listed suite instead of the largest one")
    parser.add_argument("--offline", action="store_true", help="Skip network calls; use cached provider responses.")
    args = parser.parse_args()
    password = kit_password()
    try:
        prop = load_property(args.kit, args.property_id, password)
        spaces = listed_spaces(args.kit, args.property_id, password)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")
    errors, vexcel = {}, None
    address = prop.get("primaryAddress") or {}
    try:
        vexcel = fetch_property(address.get("latitude"), address.get("longitude"), prop["id"], args.offline)
    except (OSError, RuntimeError, ValueError) as error:  # provider errors are reported, never fatal
        errors["vexcel"] = str(error)
    result = space_fit(prop, args.use, spaces, args.suite, vexcel)
    result["errors"].update(errors)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    sys.exit(main())
