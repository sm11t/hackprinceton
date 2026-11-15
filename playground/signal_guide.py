"""How to read the venture review's signals: what each measures, its source, the exact vote thresholds, and how
accurate it is. Served at GET /api/signal-guide for the /suite legend.

Every threshold below is read from the constant the code itself uses (neighborhood.py, venture_costs.py), and
every accuracy number from the stored evaluation (lookalike evaluations, rent-estimates.json), so the legend
cannot drift from what the agents actually do. Nothing here is hand-copied from a run.
"""
import neighborhood as nb
from venture_costs import DEPOSIT_MONTHS, rent_estimates


def pct(x):
    return f"{x:.0%}" if x is not None else "?"


def lookalike_accuracy():
    """Measured spatial hold-out AUC per business, best first; businesses without a model listed as such."""
    rows = []
    for item in nb.industry_catalog():
        auc = item.get("lookalike_auc")
        rows.append({"business": item["key"], "label": item["label"], "auc": auc,
                     "votes": bool(item.get("validated")),
                     "note": ("votes" if item.get("validated") else
                              f"shown only (AUC below {nb.VALIDATED_AUC})" if auc is not None else
                              "no model: fewer than "
                              f"{nb.MIN_FACILITIES} mapped locations")})
    return sorted(rows, key=lambda r: -(r["auc"] or 0))


def rent_accuracy():
    """Rent model vs recent comps, median absolute % error on held-out signed deals, by space use."""
    ev = ((rent_estimates() or {}).get("evaluation") or {}).get("deals") or {}
    if not ev:
        return None
    by_use = [{"use": use, "n": v["n"], "model_error_pct": v["model_median_error_pct"],
               "comps_error_pct": v["baseline_median_error_pct"], "range_coverage_pct": v.get("range_coverage_pct"),
               "model_wins": v["model_median_error_pct"] < v["baseline_median_error_pct"]}
              for use, v in sorted((ev.get("by_space_use") or {}).items(), key=lambda kv: -kv[1]["n"])]
    est = rent_estimates() or {}
    return {"deals_trained": est.get("trained_on_deals"), "held_out": ev.get("n"),
            "model_error_pct": ev.get("model_median_error_pct"), "comps_error_pct": ev.get("baseline_median_error_pct"),
            "range_coverage_pct": ev.get("range_coverage_pct"), "by_use": by_use}


def guide():
    radius = f"{nb.RADIUS_MI:g} mi"
    signals = [
        {"name": "building fit", "agent": "building", "pillar": "space",
         "measures": "Whether this listed space can physically host the business.",
         "source": "CoStar kit: building type and subtype, listed suite size, floor, ceiling height",
         "supports": "Fits: building type commonly hosts it, the suite is inside the business's typical size range, "
                     "and street level / ceiling needs are met.",
         "against": "Blocks: residential building, an atypical building type, the suite is below the minimum size, "
                    "or the ceiling is below the stated need.",
         "unknown": "Needs a check: floor, ceiling or outdoor space not recorded, or the suite is larger than typical.",
         "accuracy": "Size ranges are planning assumptions for a typical small operator, not code. Building type, "
                     "size and ceiling are CoStar-recorded facts."},
        {"name": "population trend", "agent": "residents", "pillar": "demand",
         "measures": f"How fast the relevant residents within {radius} grew since 2015-19, compared with the "
                     "Houston area (childcare uses under-5s, tutoring ages 5-17).",
         "source": "U.S. Census ACS 5-year 2020-2024 vs 2015-2019, tract level",
         "supports": f"+1 when growth beats the Houston area by more than {nb.TREND_POINTS * 100:g} points AND the gap "
                     "is larger than the ACS 90% margin of error.",
         "against": f"-1 when it trails by more than {nb.TREND_POINTS * 100:g} points, beyond the margin of error.",
         "unknown": "0 inside the margin of error; unknown if the tracts are missing.",
         "accuracy": "A census count, not a model. Describes the area, not this business, so it cannot decide a "
                     "verdict on its own."},
        {"name": "local supply", "agent": "competitors", "pillar": "demand",
         "measures": f"How many of this business are within {radius} per resident, compared with the Houston-area "
                     "rate.",
         "source": "OpenStreetMap via Overpass (childcare: Texas HHSC licensed centers, with seats)",
         "supports": f"+1 (underserved) at {nb.SUPPLY_UNDER:g}x the Houston-area rate or less, only if that few is "
                     f"unlikely by chance (Poisson p < {nb.SUPPLY_P:g}).",
         "against": f"-1 (crowded) at {nb.SUPPLY_OVER:g}x or more, only if that many is unlikely by chance "
                    f"(p < {nb.SUPPLY_P:g}).",
         "unknown": f"Does not vote for restaurants, fast food, cafes and bars (they cluster on purpose). Unknown if "
                    f"fewer than {nb.MIN_FACILITIES} are mapped area-wide, or none mapped where 5+ are expected "
                    "(a mapping gap, not an empty market).",
         "accuracy": "OpenStreetMap is incomplete; Texas HHSC is the official license list. Straight-line "
                     "distance, not drive time."},
        {"name": "business arrivals", "agent": "momentum", "pillar": "demand",
         "measures": f"Net moves of this kind of business into nearby CoStar buildings (within "
                     f"{nb.MOMENTUM_RADIUS_MI:g} mi) over the last 3 years.",
         "source": "CoStar kit tenancies (arrivals and departures; renewals excluded)",
         "supports": "+1 when more arrived than left.",
         "against": "-1 when more left than arrived.",
         "unknown": "Needs 2+ moves; with fewer, falls back to the business's group (e.g. sports & fitness) and "
                    "says so; still fewer stays unknown.",
         "accuracy": "The kit is a sample of buildings, so counts are small. Group-level moves describe the area, "
                     "not this business."},
        {"name": "lookalike", "agent": "lookalike", "pillar": "demand",
         "measures": "Whether the residents here look like those near places that already have this business "
                     "(percentile among Houston-area neighborhoods).",
         "source": "Logistic model on ACS resident features; trained on mapped locations vs Houston tract points",
         "supports": f"+1 at the {nb.LOOKALIKE_PLUS}th percentile or above.",
         "against": f"-1 at the {nb.LOOKALIKE_MINUS}th percentile or below.",
         "unknown": f"Votes only if its held-out AUC (areas held out in 13-mile cells) is at least "
                    f"{nb.VALIDATED_AUC}; otherwise shown but does not vote. No model under "
                    f"{nb.MIN_FACILITIES} mapped locations.",
         "accuracy": "Better than chance and mostly an income signal. Near chance for need-based services "
                     "(childcare follows population), where it is shown but does not vote. Measured per business "
                     "below.",
         "measured": "lookalike"},
        {"name": "neighborhood verdict", "agent": "coordinator", "pillar": "demand",
         "measures": "Combines the four signals above into supported / mixed / weak / unknown.",
         "source": "The signals above (computed in code)",
         "supports": f"Supported: total of +{nb.VERDICT_TOTAL} or more, including a +1 from a business-specific "
                     "signal (lookalike or local supply), and no -1 from the lookalike.",
         "against": f"Weak: lookalike -1, or a total of -{nb.VERDICT_TOTAL} or less including a business-specific "
                    "-1.",
         "unknown": "Unknown: fewer than 2 known signals, or none business-specific. Everything else is mixed.",
         "accuracy": "These cut-offs are our rules, set relative to the Houston-area distribution; they are not "
                     "industry standards."},
        {"name": "cash to open", "agent": "money", "pillar": "money",
         "measures": "Cash needed to open in this space: equipment, build-out, opening inventory and fees, plus a "
                     f"{DEPOSIT_MONTHS}-month deposit and rent while building. Low / base / high.",
         "source": "Franchise disclosure documents (FDD Item 7 initial investment tables) and published "
                   "benchmarks, scaled to the space's size",
         "supports": "Within budget: cash to open (base case) + your reserve is at or under the budget.",
         "against": "Blocks: even the low case + reserve is over the budget.",
         "unknown": "Needs a check: affordable only in the low case (stretch), the listing has no asking rent, a "
                    "line is not priced (e.g. childcare build-out), or there is no benchmark (car wash).",
         "accuracy": "No revenue forecast. Fixed lines (signage, licenses) are not scaled down for small spaces, so "
                     "small sites can be overstated. Months of rent left after opening assume zero revenue."},
        {"name": "3-month delay", "agent": "money", "pillar": "money",
         "measures": "The same cash check if opening slips 3 months (3 more months of rent while building).",
         "source": "Computed from the cash-to-open ledger and the listing's rent",
         "supports": "Still within budget after the delay.",
         "against": "Needs a check: a delay pushes the base case over budget.",
         "unknown": "Unknown when the listing has no rent.",
         "accuracy": "Stress test, not a forecast."},
        {"name": "asking rent vs market", "agent": "deal", "pillar": "deal",
         "measures": "Whether the asking rent sits inside the 10-90% range that similar spaces signed at.",
         "source": "Rent model trained on CoStar signed lease deals (quantile model), or the comps range where "
                   "the model does not beat comps",
         "supports": "Inside the range.",
         "against": "Needs a check: above the range (negotiate) or below it (ask why).",
         "unknown": "No asking rent listed, or not enough similar deals for a confident range.",
         "accuracy": "Median error by space use below, on held-out deals, vs simply using recent comps.",
         "measured": "rent"},
        {"name": "records agree", "agent": "records", "pillar": "records",
         "measures": "Whether CoStar's record and the linked Matterport / Vexcel scans describe the same building, "
                     "suite and size.",
         "source": "CoStar kit property record, Matterport tour captions, Vexcel capture dates",
         "supports": "No conflicts between the records.",
         "against": "Needs a check: a conflict (e.g. the tour is captioned for another suite).",
         "unknown": "A record cannot be confirmed from the data.",
         "accuracy": "Captions are not surveyed joins; a conflict means 'confirm', not 'wrong'."},
        {"name": "jurisdiction", "agent": "permits", "pillar": "permits",
         "measures": "Which city or county permits this address, from the pin, never the postal city.",
         "source": "U.S. Census geocoder (incorporated places and counties)",
         "supports": "Verified inside the City of Houston: Houston's change-of-use path applies.",
         "against": "Needs a check: in unincorporated Harris County (Harris County permits, not the City of "
                    "Houston) or inside another city.",
         "unknown": "Not looked up (offline and not cached): Houston's path is shown as an assumption.",
         "accuracy": "Census boundaries update yearly and can lag an annexation; confirm edge parcels with the "
                     "city's GIS. Nothing here is an approval."},
    ]
    return {
        "principles": [
            "Green supports, amber needs a check, red blocks, grey is unknown. Unknown stays unknown: nothing is "
            "guessed to fill a gap.",
            "Every number is computed in code from cached sources. Only the optional summary is written by an LLM.",
            "No revenue forecast: survival is measured as months of rent left after opening with zero revenue.",
        ],
        "verdict": {
            "NO-GO": "Anything blocks: the space can't host it, cash is over budget even in the low case, or the "
                     "neighborhood looks weak.",
            "GO": "The space fits, cash is within budget in the base case, the neighborhood supports it, and no "
                  "check is open.",
            "CONDITIONAL": "Nothing blocks, but at least one check is open.",
        },
        "signals": signals,
        "lookalike_accuracy": lookalike_accuracy(),
        "rent_accuracy": rent_accuracy(),
        "thresholds": {"trend_points": nb.TREND_POINTS, "lookalike_plus": nb.LOOKALIKE_PLUS,
                       "lookalike_minus": nb.LOOKALIKE_MINUS, "validated_auc": nb.VALIDATED_AUC,
                       "supply_under": nb.SUPPLY_UNDER, "supply_over": nb.SUPPLY_OVER, "supply_p": nb.SUPPLY_P,
                       "verdict_total": nb.VERDICT_TOTAL, "min_facilities": nb.MIN_FACILITIES,
                       "radius_mi": nb.RADIUS_MI, "momentum_radius_mi": nb.MOMENTUM_RADIUS_MI,
                       "deposit_months": DEPOSIT_MONTHS},
    }


if __name__ == "__main__":
    import json
    print(json.dumps(guide(), indent=2))
