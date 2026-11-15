"""Market-wide ranking: which listed spaces in a market best fit a use and a cash budget?

Screens every active for-lease space in the market with the same deterministic pieces the
single-property review uses, then returns a short, explained list:

  eligibility  CoStar property type must suit the use (alternatives.CATALOG); residential
               properties and dwelling tours are excluded
  fit          space_fit on CoStar facts only (no per-building Vexcel/Matterport calls), so many
               spaces come out "investigate" rather than "supported"
  rent         the listed asking rent for that space (deal.monthly_rent)
  cash         itemized planning cash to open incl. reserve (advisor_money.advisor_cash), the
               same editable allowances as /maximo; not quotes
  evidence     reconcile address and size conflicts are surfaced and ranked down, never hidden

Ranking (no synthetic score): physical-fit verdict, then within budget, then no evidence
conflict, then asking rent known, then lowest planning cash to open. One space per building.

Usage:
  python3 playground/market_rank.py --kit ~/Downloads/costar-hackathon-kit.zip --use "indoor pickleball" --capital 500000
"""
import argparse
import csv
import io
import json
import sys
from pathlib import Path
from zipfile import ZipFile

from advisor_money import advisor_cash
from alternatives import CATALOG
from deal import SERVICE, monthly_rent
from eligibility import DWELLING_CAPTION, DWELLING_TYPES, PROPERTY_TYPES
from reconcile import MARKETS, check_identity, check_size, costar_address, kit_password, unique_scans
from space_fit import space_fit

VERDICT_ORDER = {"supported": 0, "investigate": 1, "does_not_fit": 2}
TOP = 5
# Default smallest space worth ranking. Pickleball: 3 courts at the 30x60 ft minimum, because the cash
# scenario's revenue assumes 3 courts (3 x 12 h x 30 days); a 1-court suite can't earn that.
# Others are planning assumptions the user can override: a small boutique fitness studio, and a
# floor below which a space is an office cubicle rather than a business premises.
MIN_SF = {"indoor pickleball": 3 * 1800, "fitness studio": 1500}
DEFAULT_MIN_SF = 1000


def load_market(kit_path, market, password=None):
    """[(property, [listed lease spaces])] for every property in the market with an active lease listing.

    One pass over the listing summary and one over the properties, instead of one pass per building.
    Only properties the review page can open (commercial-properties.csv) are kept.
    """
    market_id = MARKETS[market]
    spaces = {}
    with ZipFile(kit_path) as kit:
        with kit.open("commercial-properties.csv", pwd=password) as stream:
            reviewable = {int(row["PropertyId"]) for row in csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"))
                          if row["PropertyId"].isdigit()}
        with kit.open("data/commercial-listing-summary.jsonl", pwd=password) as stream:
            for line in stream:
                listing = json.loads(line)
                if listing.get("listingStatus") != 1:  # active only
                    continue
                for space in (listing.get("forLeaseSummary") or {}).get("spaces") or []:
                    pid = space.get("propertyId")
                    if pid in reviewable:
                        spaces.setdefault(pid, []).append({
                            "listing_id": listing["id"], "suite": space.get("suite"),
                            "square_feet": space.get("squareFeetMax"),
                            "available_on": (space.get("availableOnDate") or "")[:10] or None,
                            "on_market": (space.get("dateOnMarket") or "")[:10] or None,
                            "raw": space,
                        })
        out = []
        with kit.open("data/commercial-property.jsonl", pwd=password) as stream:
            for line in stream:
                prop = json.loads(line)
                if prop["id"] in spaces and (prop.get("primaryAddress") or {}).get("researchMarketId") == market_id:
                    out.append((prop, spaces[prop["id"]]))
    return out


def space_value(space):
    """The suite value the review page's suite picker uses (maximo.space_option)."""
    suite = str(space["suite"] or "").strip()
    if suite:
        return suite
    return f"listing:{space['listing_id']}:{space['square_feet']:g}" if space["square_feet"] else None


def deciding_reason(fit):
    judged = [r for r in fit["records"] if r["source"] != "checklist"
              and (r["fact"].startswith(f"{fit['use']}_") or r["fact"].startswith("req_"))]
    row = (next((r for r in judged if r["status"] == "conflict"), None)
           or next((r for r in judged if r["status"] == "unknown"), None)
           or next(iter(judged), None))
    return row["note"] if row else "No use-specific threshold can be checked from CoStar data; see the review checklist."


def evidence_flags(prop):
    flags = []
    if any(r["status"] == "conflict" for r in check_identity(prop)):
        flags.append("A linked tour is captioned for a different address.")
    if any(r["status"] == "conflict" for r in check_size(prop)):
        flags.append("CoStar's own size fields don't add up.")
    return flags


LOW_RENT_PER_SF_YEAR = 3.0  # below this an asking rent is more likely a data-entry error than a bargain


def screen_space(prop, space, use, min_sf=None, max_sf=None):
    """Cheap screen for one space (eligibility, size, fit, rent), or None if the use is ruled out.

    Cash to open is added later, only for the best space per building (add_cash)."""
    spec = CATALOG[use]
    size = space["square_feet"] or 0
    if (min_sf and size < min_sf) or (max_sf and size > max_sf):
        return None
    kind = str(prop.get("propertyType", "")).strip()
    if kind.casefold() in DWELLING_TYPES or kind not in spec["types"]:
        return None
    if any(DWELLING_CAPTION.search(c) for scan in unique_scans(prop) for c in scan["captions"]):
        return None
    if not space["square_feet"] or not space_value(space):
        return None
    fit = space_fit(prop, spec["fit"], spaces=[space], suite=space["suite"],
                    requirements={"min_area_sf": 1} if spec["fit"] == "custom" else None)
    verdict = fit["verdict"]
    if verdict == "does_not_fit":
        return None
    if spec["fit"] == "custom" and verdict == "supported":
        verdict = "investigate"  # same rule as the single-property review: area alone doesn't prove a layout
    monthly, per_sf_year = monthly_rent(space["raw"])
    flags = []
    if per_sf_year is not None and per_sf_year < LOW_RENT_PER_SF_YEAR:
        flags.append(f"Asking rent of ${per_sf_year:.2f}/sq ft/year is implausibly low; confirm the rate and its "
                     "period with the broker.")
    basis = SERVICE.get(space["raw"].get("serviceType"), ("lease basis not recorded",))[0]
    return {
        "property_id": prop["id"], "address": costar_address(prop)["display"],
        "property_type": PROPERTY_TYPES.get(kind, kind), "suite": space_value(space),
        "suite_label": f"Suite {space['suite'].strip()}" if str(space["suite"] or "").strip()
        else f"{space['square_feet']:,.0f} sq ft (unnamed)",
        "square_feet": space["square_feet"], "available_on": space["available_on"],
        "monthly_rent": monthly, "rent_per_sf_year": per_sf_year, "lease_basis": basis,
        "rent_source": "CoStar asking rent" if monthly else "not listed; default assumption used",
        "verdict": verdict, "fit_reason": deciding_reason(fit), "evidence_flags": flags,
        "tour_count": len(unique_scans(prop)),
    }


def space_key(row):
    """Best space within one building. Planning cash to open rises with rent, so lowest rent = lowest cash."""
    return (VERDICT_ORDER[row["verdict"]], bool(row["evidence_flags"]), row["monthly_rent"] is None,
            row["monthly_rent"] or 0)


def add_cash(row, use, capital, reserve):
    inputs = {"starting_cash": capital, "reserve": reserve}
    if row["monthly_rent"] is not None:
        inputs["monthly_rent"] = row["monthly_rent"]
    cash = advisor_cash(inputs, use, "lease", area=row["square_feet"],
                        rent_source="CoStar asking rent" if row["monthly_rent"] else "Editable assumption")
    totals = cash["costs"]["totals"]["base"]
    gap = ((cash.get("money") or {}).get("conversion") or {}).get("extra_funding_needed") or 0
    row.update(cash_to_open=totals["cash_required"], shortfall=totals["shortfall"] or 0, reserve_gap=gap,
               within_budget=not totals["shortfall"] and not gap)
    return row


def rank_key(row):
    return (VERDICT_ORDER[row["verdict"]], not row["within_budget"], bool(row["evidence_flags"]),
            row["monthly_rent"] is None, row["cash_to_open"] if row["cash_to_open"] is not None else float("inf"))


def why(row):
    parts = [f"{row['square_feet']:,.0f} sq ft"]
    if row["monthly_rent"]:
        parts.append(f"${row['monthly_rent']:,}/mo asking ({row['lease_basis']})")
    else:
        parts.append("no asking rent listed")
    parts.append(f"~${row['cash_to_open']:,.0f} to open incl. reserve" if row["cash_to_open"] is not None
                 else "cash to open incomplete")
    parts.append("within budget" if row["within_budget"] else "over budget under planning allowances")
    return ", ".join(parts) + "."


def rank_market(candidates, use, capital, reserve, top=TOP, min_sf=None, max_sf=None):
    """Pure ranking over load_market() output."""
    if use not in CATALOG:
        raise ValueError(f"use must be one of {', '.join(CATALOG)}")
    min_sf = MIN_SF.get(use, DEFAULT_MIN_SF) if min_sf is None else min_sf
    best = {}
    screened = 0
    for prop, spaces in candidates:
        building_flags = None
        for space in spaces:
            screened += 1
            row = screen_space(prop, space, use, min_sf, max_sf)
            if not row:
                continue
            if building_flags is None:
                building_flags = evidence_flags(prop)
            row["evidence_flags"] = building_flags + row["evidence_flags"]
            if prop["id"] not in best or space_key(row) < space_key(best[prop["id"]]):
                best[prop["id"]] = row
    rows = sorted((add_cash(row, use, capital, reserve) for row in best.values()), key=rank_key)
    for row in rows:
        row["why"] = why(row)
    counts = {v: sum(r["verdict"] == v for r in rows) for v in ("supported", "investigate")}
    return {
        "use": use, "capital": capital, "reserve": reserve, "ownership": "lease", "min_sf": min_sf, "max_sf": max_sf,
        "spaces_screened": screened, "buildings_screened": len(candidates), "buildings_passing": len(rows),
        "by_verdict": counts, "within_budget": sum(r["within_budget"] for r in rows),
        "results": rows[:top],
        "ranking_basis": ("Physical-fit verdict from CoStar facts first, then within budget, then no evidence "
                          "conflict, then a listed asking rent, then the lowest planning cash to open. One space per "
                          "building. No numeric score."),
        "limits": ("CoStar data only: no per-building aerial or scan measurements, so most spaces are 'investigate'. "
                   "Cash to open uses the same unverified planning allowances as the full review, not quotes. "
                   "Lease only. Demand and permission are not screened. Open a result for the full review."),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--market", choices=sorted(MARKETS), default="Houston")
    parser.add_argument("--use", choices=sorted(CATALOG), default="indoor pickleball")
    parser.add_argument("--capital", type=float, default=320000)
    parser.add_argument("--reserve", type=float, default=50000)
    parser.add_argument("--top", type=int, default=TOP)
    parser.add_argument("--min-sf", type=float, help="Smallest space to rank (default: 3 courts for pickleball).")
    parser.add_argument("--max-sf", type=float)
    args = parser.parse_args()
    try:
        candidates = load_market(args.kit, args.market, kit_password())
        result = rank_market(candidates, args.use, args.capital, args.reserve, args.top, args.min_sf, args.max_sf)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    sys.exit(main())
