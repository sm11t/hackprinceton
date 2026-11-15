"""Market-rent range for a commercial space, learned from the kit's signed lease deals.

Trains gradient-boosted trees (scikit-learn, quantile loss) on the asking rent of signed lease deals
in location-occupancy since 2012, one model for office-type space and one for everything else, then
predicts a low / typical / high $/sq ft/yr range for every
listed space in the kit, including "call for rate" spaces. Inputs: space use, lease basis
(serviceType), size, year, and the building's type, class, age, size, stories, submarket and
location. The served model is trained on every deal, so a building's own past signed deals inform its
range; the evaluation holds whole buildings out, so its figures are for buildings the model never saw.

Evaluated with 5 folds grouped by building, on recent signed deals and on current listings' asking rents,
against a simple baseline (median of the same city, use and lease basis). The 10th-90th percentile
range is widened by a conformal margin so it holds about 80% of rents in buildings the model never saw.
For a space use where the model did not beat the baseline in every held-out test (flex, today), the
served range is the 10th-90th percentile of similar recent deals instead, and the output says which.

Training needs scikit-learn and numpy; the web server only reads the output file, so the app stays
standard-library only. The output is derived from sponsor data, so it lives in the gitignored
playground/output/:

    python3 rent_model.py --kit ~/Downloads/costar-hackathon-kit.zip
"""
import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from space_fit import kit_lines, kit_password

OUTPUT = Path(__file__).parent / "output" / "rent-estimates.json"
QUANTILES = (0.1, 0.5, 0.9)
TARGET_COVERAGE = 0.8
TRAIN_SINCE = 2012
MIN_SEGMENT_ROWS = 50
OFFICE_USES = {1, 2, 4}  # office, office/medical, medical
MIN_SUPPORT = 30  # fewer similar recent deals than this and the range is shown as low confidence
RECENT_YEARS = 7
SPACE_USE = {1: "office", 2: "office/medical", 3: "office/retail", 4: "medical", 5: "retail", 6: "flex",
             7: "industrial"}
NUMERIC = ("log_sf", "year", "year_built", "log_gba", "stories", "lat", "lon")
CATEGORICAL = ("space_use", "service_type", "space_type", "property_type", "building_class", "submarket")


# --- Rows (standard library) ----------------------------------------------------------------------

def per_sf_year(low, high, basis):
    """Midpoint asking rent in $/sq ft/yr; None if missing, an unknown basis, or not plausible."""
    rates = [r for r in (low, high) if r]
    if not rates or basis not in (1, 2):
        return None
    value = sum(rates) / len(rates) * (12 if basis == 1 else 1)
    return round(value, 2) if 1 <= value <= 300 else None


def year_of(*stamps):
    for s in stamps:
        if s and s[:4].isdigit():
            return int(s[:4]) + (int(s[5:7]) - 1) / 12 if len(s) >= 7 and s[5:7].isdigit() else int(s[:4])
    return None


def building_features(prop):
    a = prop.get("primaryAddress") or {}
    built = [e.get("year") for e in prop.get("constructionEvents") or [] if e.get("eventType") == 2 and e.get("year")]
    gba = prop.get("grossBuildingAreaSquareFeet")
    return {
        "property_type": prop.get("propertyType"), "building_class": prop.get("buildingClass") or None,
        "year_built": min(built) if built else None, "log_gba": math.log(gba) if gba else None,
        "stories": prop.get("numStoriesAboveGrade"), "lat": a.get("latitude"), "lon": a.get("longitude"),
        "submarket": prop.get("primarySubmarketId"), "city": (a.get("city") or "").strip().casefold(),
    }


def space_features(space_use, service_type, space_type, square_feet, year):
    return {"space_use": space_use or None, "service_type": service_type or None, "space_type": space_type or None,
            "log_sf": math.log(square_feet) if square_feet else None, "year": year}


def load_buildings(kit, password=None):
    return {p["id"]: building_features(p) for p in map(json.loads, kit_lines(kit, "data/commercial-property.jsonl", password))}


def deal_rows(kit, buildings, password=None):
    """One row per signed lease deal with an asking rent: features, target and building id."""
    rows = []
    for occ in map(json.loads, kit_lines(kit, "data/location-occupancy.jsonl", password)):
        deal = occ.get("leaseDeal") or {}
        ask = deal.get("askingRate") or {}
        rent = per_sf_year(ask.get("rateLow"), ask.get("rateHigh"), ask.get("rateBasis"))
        building = buildings.get(occ.get("propertyId"))
        if rent is None or building is None or deal.get("monetaryUnit") not in (None, 1):
            continue
        sf = sum((s or {}).get("squareFeetOccupied") or 0 for s in occ.get("spaces") or [])
        year = year_of(deal.get("signDate"), deal.get("commencementDate"), occ.get("moveInDate"))
        if year is None:
            continue
        rows.append({**building, **space_features(deal.get("spaceUse"), deal.get("serviceType"),
                                                  deal.get("spaceType"), sf, year),
                     "rent": rent, "group": occ["propertyId"]})
    return rows


def listing_rows(kit, buildings, password=None):
    """One row per space on an active lease listing, priced or not."""
    rows = []
    for listing in map(json.loads, kit_lines(kit, "data/commercial-listing-summary.jsonl", password)):
        if listing.get("listingStatus") != 1:
            continue
        for s in (listing.get("forLeaseSummary") or {}).get("spaces") or []:
            building = buildings.get(s.get("propertyId"))
            if building is None or s.get("monetaryUnit") not in (None, 1):
                continue
            year = year_of(s.get("dateOnMarket")) or date.today().year
            rows.append({**building, **space_features(s.get("spaceUse"), s.get("serviceType"), s.get("spaceType"),
                                                      s.get("squareFeetMax"), year),
                         "rent": per_sf_year(s.get("rateLow"), s.get("rateHigh"), s.get("rateBasis")),
                         "group": s.get("propertyId"), "space_id": s.get("id"), "suite": s.get("suite")})
    return rows


def peer_key(row):
    return row["city"], row["space_use"], row["service_type"]


def support(deals, now_year):
    """Recent deals per (city, space use, lease basis): how much evidence backs a range."""
    return Counter(peer_key(r) for r in deals if r["year"] >= now_year - RECENT_YEARS)


def baseline(train):
    """Median rent of the same city, use and lease basis (falling back to city, then everything)."""
    by_key, by_city = defaultdict(list), defaultdict(list)
    for r in train:
        by_key[peer_key(r)].append(r["rent"])
        by_city[r["city"]].append(r["rent"])
    overall = statistics.median(r["rent"] for r in train)

    def predict(row):
        pool = by_key.get(peer_key(row)) or by_city.get(row["city"])
        return statistics.median(pool) if pool else overall
    return predict


# --- Model (scikit-learn) -------------------------------------------------------------------------

class Encoder:
    """Categorical codes for HistGradientBoosting; rare submarkets share one code."""

    def __init__(self, rows, max_codes=200):
        self.codes = {}
        for name in CATEGORICAL:
            counts = Counter(r[name] for r in rows if r[name] is not None)
            keep = [v for v, _ in counts.most_common(max_codes)]
            self.codes[name] = {v: i for i, v in enumerate(keep)}

    def matrix(self, rows):
        import numpy as np
        out = np.full((len(rows), len(NUMERIC) + len(CATEGORICAL)), np.nan)
        for i, r in enumerate(rows):
            for j, name in enumerate(NUMERIC):
                if r[name] is not None:
                    out[i, j] = r[name]
            for j, name in enumerate(CATEGORICAL, len(NUMERIC)):
                code = self.codes[name].get(r[name])
                if code is not None:
                    out[i, j] = code
        return out

    def categorical_mask(self):
        return [False] * len(NUMERIC) + [True] * len(CATEGORICAL)


def segment(row):
    """Office-type and other space are trained separately: 87% of deals are office, and one shared model
    learned office patterns at the expense of industrial, flex and retail (checked on held-out buildings)."""
    return "office" if row["space_use"] in OFFICE_USES else "other"


def fit_one(rows, seed=0):
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingRegressor
    enc = Encoder(rows)
    x, y = enc.matrix(rows), np.log([r["rent"] for r in rows])
    models = []
    for q in QUANTILES:
        m = HistGradientBoostingRegressor(loss="quantile", quantile=q, learning_rate=0.05, max_iter=400,
                                          max_leaf_nodes=31, min_samples_leaf=20, l2_regularization=1.0,
                                          categorical_features=enc.categorical_mask(), random_state=seed)
        models.append(m.fit(x, y))
    return enc, models


def fit(rows, seed=0):
    """One quantile model per segment, trained on deals signed since TRAIN_SINCE (older rents hurt on
    held-out buildings)."""
    rows = [r for r in rows if r["year"] >= TRAIN_SINCE]
    parts = {name: [r for r in rows if segment(r) == name] for name in ("office", "other")}
    return {name: fit_one(part, seed) for name, part in parts.items() if len(part) >= MIN_SEGMENT_ROWS}


def predict(model, rows):
    import numpy as np
    out = np.zeros((len(rows), len(QUANTILES)))
    for name, (enc, models) in model.items():
        # a segment too small to train borrows the other segment's model
        idx = [i for i, r in enumerate(rows) if segment(r) == name or segment(r) not in model]
        if idx:
            x = enc.matrix([rows[i] for i in idx])
            out[idx] = np.exp(np.column_stack([m.predict(x) for m in models]))
    out.sort(axis=1)  # quantile models trained separately can cross; keep low <= typical <= high
    return out


def scores(rows, preds, base):
    """Median absolute % error for the model and the baseline, and how often the 10–90% range holds the rent."""
    def ape(pred, actual):
        return abs(pred - actual) / actual * 100

    model_err = [ape(p[1], r["rent"]) for r, p in zip(rows, preds)]
    base_err = [ape(base(r), r["rent"]) for r in rows]
    covered = [p[0] <= r["rent"] <= p[2] for r, p in zip(rows, preds)]
    by_use = {}
    for use, label in SPACE_USE.items():
        idx = [i for i, r in enumerate(rows) if r["space_use"] == use]
        if len(idx) >= 20:
            by_use[label] = {"n": len(idx), "model_median_error_pct": round(statistics.median(model_err[i] for i in idx), 1),
                             "baseline_median_error_pct": round(statistics.median(base_err[i] for i in idx), 1),
                             "range_coverage_pct": round(100 * sum(covered[i] for i in idx) / len(idx))}
    return {"n": len(rows), "model_median_error_pct": round(statistics.median(model_err), 1),
            "baseline_median_error_pct": round(statistics.median(base_err), 1),
            "range_coverage_pct": round(100 * sum(covered) / len(rows)), "by_space_use": by_use}


def out_of_fold(deals, listings, since, folds=5):
    """Predict recent deals and priced listings with models that never saw their building.

    Folds are by building id, so a listing's building is held out together with its own past deals."""
    fold = lambda r: r["group"] % folds  # noqa: E731
    result = {"deals": ([], [], []), "listings": ([], [], [])}
    for k in range(folds):
        train = [r for r in deals if fold(r) != k]
        tests = {"deals": [r for r in deals if fold(r) == k and r["year"] >= since],
                 "listings": [r for r in listings if fold(r) == k and r["rent"] is not None]}
        model, base = fit(train), baseline(train)
        for name, rows in tests.items():
            if rows:
                result[name][0].extend(rows)
                result[name][1].extend(predict(model, rows))
                result[name][2].extend(base(r) for r in rows)
    return result


def conformity(row, pred):
    """How far (in log rent) the actual rent falls outside the predicted range; negative when inside."""
    y = math.log(row["rent"])
    return max(math.log(pred[0]) - y, y - math.log(pred[2]))


def widen(pred, width):
    return [pred[0] * math.exp(-width), pred[1], pred[2] * math.exp(width)]


def calibrate(rows, preds, target=TARGET_COVERAGE):
    """Conformal width: widening every range by this (log) amount covers `target` of held-out rents."""
    e = sorted(conformity(r, p) for r, p in zip(rows, preds))
    k = min(len(e) - 1, math.ceil((len(e) + 1) * target) - 1)
    return e[k]


def choose_methods(report):
    """Serve the model for a space use only where it beat the baseline on held-out buildings in every test
    with at least 20 rows; otherwise serve the range of similar recent deals."""
    methods = {}
    for use in SPACE_USE.values():
        tests = [report[name]["by_space_use"][use] for name in ("deals", "listings")
                 if use in report[name]["by_space_use"]]
        wins = [t["model_median_error_pct"] < t["baseline_median_error_pct"] for t in tests]
        methods[use] = "model" if wins and all(wins) else "similar_deals"
    return methods


def peer_ranges(deals, now_year):
    """10th / 50th / 90th percentile rent of recent deals per (city, space use, lease basis)."""
    pools = defaultdict(list)
    for r in deals:
        if r["year"] >= now_year - RECENT_YEARS:
            pools[peer_key(r)].append(r["rent"])
    out = {}
    for key, rents in pools.items():
        if len(rents) >= MIN_SUPPORT:
            q = statistics.quantiles(rents, n=10)
            out[key] = (q[0], statistics.median(rents), q[-1])
    return out


def evaluate(deals, listings, now_year):
    """Out-of-fold scores on unseen buildings. The range width is calibrated on half the buildings and its
    coverage reported on the other half, so the coverage figure is not graded on its own homework."""
    oof = out_of_fold(deals, listings, now_year - RECENT_YEARS)
    rows, preds, base = oof["deals"]
    half = lambda r: (r["group"] // 5) % 2  # noqa: E731
    cal = [i for i, r in enumerate(rows) if half(r) == 0]
    width_half = calibrate([rows[i] for i in cal], [preds[i] for i in cal])
    report = {}
    for name, (rs, ps, bs) in oof.items():
        held = [i for i, r in enumerate(rs) if name == "listings" or half(r) == 1]
        lookup = {id(rs[i]): bs[i] for i in held}
        report[name] = scores([rs[i] for i in held], [widen(ps[i], width_half) for i in held], lambda r: lookup[id(r)])
    report["range_width"] = round(calibrate(rows, preds), 4)  # final width, from all held-out deals
    report["method_by_space_use"] = choose_methods(report)
    report["note"] = ("Every figure is on buildings the model never saw. 'deals' = signed deals from the last "
                      f"{RECENT_YEARS} years; 'listings' = current asking rents. Range = 10th-90th percentile "
                      f"widened to cover {int(TARGET_COVERAGE * 100)}% of held-out rents.")
    return report


def estimates(model, deals, listings, now_year, width=0.0, methods=None):
    preds = [widen(p, width) for p in predict(model, listings)]
    peers, ranges = support(deals, now_year), peer_ranges(deals, now_year)
    out = {}
    for r, pred in zip(listings, preds):
        n = peers.get(peer_key(r), 0)
        use = SPACE_USE.get(r["space_use"])
        method = (methods or {}).get(use, "model")
        if method == "similar_deals" and peer_key(r) in ranges:
            low, mid, high = ranges[peer_key(r)]
        else:
            method, (low, mid, high) = "model", pred
        out[str(r["space_id"])] = {
            "property_id": r["group"], "suite": r["suite"], "space_use": use, "service_type": r["service_type"],
            "low": round(float(low), 2), "typical": round(float(mid), 2), "high": round(float(high), 2),
            "asking": r["rent"], "method": method, "similar_recent_deals": n, "low_confidence": n < MIN_SUPPORT,
        }
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kit", required=True)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--skip-eval", action="store_true", help="Train and write estimates without cross-validation.")
    args = parser.parse_args()
    password = kit_password()
    buildings = load_buildings(args.kit, password)
    deals = deal_rows(args.kit, buildings, password)
    listings = listing_rows(args.kit, buildings, password)
    now_year = date.today().year
    print(f"{len(deals):,} signed deals with an asking rent; {len(listings):,} listed spaces "
          f"({sum(r['rent'] is not None for r in listings):,} with an asking rent)", file=sys.stderr)

    report = evaluate(deals, listings, now_year) if not args.skip_eval else {}
    if report:
        for name in ("deals", "listings"):
            print(f"unseen buildings, {name}:", json.dumps(report[name]), file=sys.stderr)
    model = fit(deals)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "generated": date.today().isoformat(), "trained_on_deals": sum(r["year"] >= TRAIN_SINCE for r in deals),
        "train_since": TRAIN_SINCE, "quantiles": QUANTILES,
        "min_support": MIN_SUPPORT, "recent_years": RECENT_YEARS, "evaluation": report,
        "spaces": estimates(model, deals, listings, now_year, report.get("range_width", 0.0),
                            report.get("method_by_space_use")),
    }))
    print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
