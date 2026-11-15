"""Neighborhood demand and trends: does the area around an address support a business?

A small team of specialist agents investigates, and every step is recorded in a
trace (inputs -> sources -> findings with confidence -> hand-off):

  planner      picks the signals that apply to the use (rule table, code)
  site         resolves the address or CoStar property to a point and Census tract
  residents    "Who lives here": ACS 2020-2024 vs 2015-2019 around the site
  competitors  "Who already serves it": OpenStreetMap facilities within the radius
  momentum     "What is moving in": CoStar kit tenancy move-ins / move-outs by category
  lookalike    "Does it look like places that already have this business?"
               (logistic model, measured on held-out real facilities)
  coordinator  verdict per use from the signals, with the deciding reasons
  narrator     optional plain-English summary written by an LLM from the records

Numbers are computed in code. The LLM only writes the optional summary, and that
text is labelled as LLM-written. Missing data stays "unknown"; nothing is guessed.

Every external response is cached under playground/output/neighborhood/ (gitignored).
Set NEIGHBORHOOD_OFFLINE=1 (or pass --offline) to use only the cache.

Usage:
  python3.12 playground/with_env.py python3.12 playground/neighborhood.py \
      --kit costar-hackathon-kit --property-id 13890701 --use "indoor pickleball"
  ... --address "9700 Tanner Rd, Houston, TX 77041" --use suggest
  ... --evaluate "indoor pickleball"     # held-out evaluation of the lookalike score
"""
import argparse
import hashlib
import json
import math
import os
import random
import re
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from reconcile import record

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "output" / "neighborhood"
USER_AGENT = "hackprinceton-neighborhood-demand/0.1 (research prototype)"

# Houston area = the five core Houston-metro counties (Census FIPS, Texas = 48).
STATE = "48"
COUNTIES = {"201": "Harris", "157": "Fort Bend", "339": "Montgomery", "039": "Brazoria", "167": "Galveston"}
AREA_NAME = "Houston area (Harris, Fort Bend, Montgomery, Brazoria, Galveston counties)"
BBOX = (28.9, -96.1, 30.65, -94.35)  # south, west, north, east around those counties
RADIUS_MI = 3.0

ACS = "https://api.census.gov/data/{year}/acs/acs5"
ACS_PAGE = "https://www.census.gov/programs-surveys/acs"
GAZETTEER = {  # tract internal points; ACS 2015-2019 uses 2010 tracts, 2020-2024 uses 2020 tracts
    2024: "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_gaz_tracts_48.txt",
    2019: "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2019_Gazetteer/2019_gaz_tracts_48.txt",
}
GEOCODER = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
OVERPASS = "https://overpass-api.de/api/interpreter"

# B01001 sex-by-age cells (male 003-025, female 027-049, same order) grouped into bands.
AGE_BANDS = {
    "under_5": [3], "age_5_17": [4, 5, 6], "age_18_24": [7, 8, 9, 10], "age_25_34": [11, 12],
    "age_35_54": [13, 14, 15, 16], "age_55_64": [17, 18, 19], "age_65_plus": [20, 21, 22, 23, 24, 25],
}
AGE_VARS = [f"B01001_{n + offset:03d}E" for band in AGE_BANDS.values() for n in band for offset in (0, 24)]
BASE_VARS = ["B01003_001E", "B01003_001M", "B11001_001E", "B19013_001E"]


class Offline(RuntimeError):
    """Raised when a response is needed but offline mode allows only the cache."""


def offline():
    return os.environ.get("NEIGHBORHOOD_OFFLINE", "") not in ("", "0", "false")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --- Cached fetching -----------------------------------------------------------

def public_url(url, params=None):
    """The URL a person can open as evidence: never includes an API key."""
    shown = {k: v for k, v in (params or {}).items() if k != "key"}
    return url + ("?" + urlencode(shown) if shown else "")


def fetch(url, params=None, form=None, kind="json", timeout=90):
    """GET/POST with a disk cache. Returns (payload, meta). The key never enters the cache key."""
    shown = public_url(url, params)
    digest = hashlib.sha1((shown + "|" + json.dumps(form, sort_keys=True)).encode()).hexdigest()[:20]
    path = CACHE / "http" / f"{digest}.json"
    if path.exists():
        saved = json.loads(path.read_text())
        return saved["payload"], {"url": shown, "retrieved_at": saved["retrieved_at"], "cached": True}
    if offline():
        raise Offline(f"Offline mode and no cached response for {shown}")
    full = url + ("?" + urlencode(params) if params else "")
    body = urlencode(form).encode() if form else None
    last = None
    for attempt in range(3):
        try:
            with urlopen(Request(full, data=body, headers={"User-Agent": USER_AGENT}), timeout=timeout) as response:
                raw = response.read().decode("utf-8", "replace")
            break
        except HTTPError as error:
            last = RuntimeError(f"HTTP {error.code} from {url}")
            if error.code not in (429, 502, 503, 504):
                raise last from None
        except (URLError, TimeoutError) as error:
            last = RuntimeError(f"Could not reach {url}: {getattr(error, 'reason', error)}")
        time.sleep(2 * (attempt + 1))
    else:
        raise last
    payload = json.loads(raw) if kind == "json" else raw
    retrieved = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"url": shown, "retrieved_at": retrieved, "payload": payload}))
    return payload, {"url": shown, "retrieved_at": retrieved, "cached": False}


def source(name, meta, note=""):
    return {"name": name, "url": meta["url"], "retrieved_at": meta["retrieved_at"],
            "cached": meta["cached"], "note": note}


# --- Geometry ------------------------------------------------------------------

def miles(lat1, lon1, lat2, lon2):
    """Great-circle distance in miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 3958.8 * 2 * math.asin(math.sqrt(a))


def near(rows, lat, lon, radius):
    """Rows (with lat/lon) within radius miles; cheap box prefilter before the exact distance."""
    dlat = radius / 69.0
    dlon = radius / (69.0 * math.cos(math.radians(lat)))
    out = []
    for row in rows:
        if abs(row["lat"] - lat) <= dlat and abs(row["lon"] - lon) <= dlon:
            d = miles(lat, lon, row["lat"], row["lon"])
            if d <= radius:
                out.append((d, row))
    return out


# --- Census tables -------------------------------------------------------------

@lru_cache(maxsize=None)
def tracts(year):
    """{GEOID: {lat, lon, land_sqmi}} for the Houston-area counties, from the Census Gazetteer."""
    text, meta = fetch(GAZETTEER[year], kind="text")
    out = {}
    for line in text.splitlines()[1:]:
        cells = [c.strip() for c in line.split("\t")]
        if len(cells) < 8 or cells[1][2:5] not in COUNTIES:
            continue
        out[cells[1]] = {"geoid": cells[1], "lat": float(cells[6]), "lon": float(cells[7]),
                         "land_sqmi": float(cells[4])}
    return out, meta


def number(value):
    """ACS uses large negative sentinels for 'not available'; those become None."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


@lru_cache(maxsize=None)
def acs(year):
    """{GEOID: {variable: value}} for every Houston-area tract in the ACS 5-year release ending `year`."""
    key = os.environ.get("CENSUS_API_KEY")
    table, metas = {}, []
    for variables in (BASE_VARS, AGE_VARS):
        query = {"get": ",".join(variables), "for": "tract:*", "in": f"state:{STATE} county:{','.join(COUNTIES)}"}
        if key:
            query["key"] = key
        rows, meta = fetch(ACS.format(year=year), query)
        metas.append(meta)
        header = rows[0]
        for row in rows[1:]:
            cells = dict(zip(header, row))
            geoid = cells["state"] + cells["county"] + cells["tract"]
            table.setdefault(geoid, {}).update({v: number(cells[v]) for v in variables})
    return table, metas


def tract_rows(year):
    """Tracts joined to their ACS values, ready for radius queries."""
    points, gaz_meta = tracts(year)
    values, acs_metas = acs(year)
    rows = []
    for geoid, point in points.items():
        v = values.get(geoid)
        if not v or v.get("B01003_001E") is None:
            continue
        bands = {band: sum((v.get(f"B01001_{n:03d}E") or 0) + (v.get(f"B01001_{n + 24:03d}E") or 0) for n in cells)
                 for band, cells in AGE_BANDS.items()}
        rows.append({**point, "pop": v["B01003_001E"], "pop_moe": v.get("B01003_001M"),
                     "households": v.get("B11001_001E"), "income": v.get("B19013_001E"), **bands})
    return rows, [gaz_meta, *acs_metas]


@lru_cache(maxsize=None)
def tract_table(year):
    rows, metas = tract_rows(year)
    return tuple(rows), tuple(tuple(sorted(m.items())) for m in metas)


def census_sources(year):
    _, metas = tract_table(year)
    names = ["Census Gazetteer tract points", f"ACS {year - 4}-{year} 5-year (population, households, income)",
             f"ACS {year - 4}-{year} 5-year (sex by age, B01001)"]
    return [source(n, dict(m)) for n, m in zip(names, metas)]


def area_profile(lat, lon, radius=RADIUS_MI):
    """Residents of the Census tracts whose internal point lies within `radius` miles.

    Tracts are the unit, so the area is approximate at its edge. Median household
    income is the household-weighted mean of tract medians (medians do not add up
    exactly), and is labelled that way wherever it is shown.
    """
    rows, _ = tract_table(2024)
    hits = [row for _, row in near(rows, lat, lon, radius)]
    if not hits:
        return None
    pop = sum(r["pop"] for r in hits)
    land = sum(r["land_sqmi"] for r in hits)
    weighted = [(r["income"], r["households"] or 0) for r in hits if r["income"] is not None]
    hh_weight = sum(w for _, w in weighted)
    out = {
        "tracts": len(hits), "population": pop,
        "population_moe": round(math.sqrt(sum((r["pop_moe"] or 0) ** 2 for r in hits))),
        "households": sum(r["households"] or 0 for r in hits),
        "land_sqmi": round(land, 2), "density_per_sqmi": round(pop / land) if land else None,
        "median_income_approx": round(sum(i * w for i, w in weighted) / hh_weight) if hh_weight else None,
    }
    for band in AGE_BANDS:
        out[f"share_{band}"] = round(sum(r[band] for r in hits) / pop, 4) if pop else None
    old_rows, _ = tract_table(2019)
    old = [row for _, row in near(old_rows, lat, lon, radius)]
    old_pop = sum(r["pop"] for r in old)
    out["population_2019"] = old_pop or None
    out["growth"] = round(pop / old_pop - 1, 4) if old_pop else None
    old_under5 = sum(r["under_5"] for r in old)
    out["under_5"] = sum(r["under_5"] for r in hits)
    out["under_5_growth"] = round(out["under_5"] / old_under5 - 1, 4) if old_under5 else None
    return out


@lru_cache(maxsize=None)
def area_totals():
    """Whole Houston-area totals (county sums are comparable across tract vintages)."""
    new, _ = tract_table(2024)
    old, _ = tract_table(2019)
    pop, old_pop = sum(r["pop"] for r in new), sum(r["pop"] for r in old)
    under5, old_under5 = sum(r["under_5"] for r in new), sum(r["under_5"] for r in old)
    return {"population": pop, "population_2019": old_pop, "growth": round(pop / old_pop - 1, 4),
            "under_5": under5, "under_5_growth": round(under5 / old_under5 - 1, 4)}


@lru_cache(maxsize=None)
def reference_profiles(radius=RADIUS_MI):
    """The same profile around every Houston-area tract point: the distribution a site is compared to."""
    path = CACHE / f"reference-profiles-{radius}.json"
    if path.exists():
        return json.loads(path.read_text())
    rows, _ = tract_table(2024)
    out = [{"geoid": r["geoid"], "lat": r["lat"], "lon": r["lon"], **(area_profile(r["lat"], r["lon"], radius) or {})}
           for r in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    return out


def percentile(value, population):
    """Share of the reference values strictly below `value`, plus half the ties (0-100)."""
    values = [v for v in population if v is not None]
    if value is None or not values:
        return None
    below = sum(v < value for v in values)
    ties = sum(v == value for v in values)
    return round(100 * (below + ties / 2) / len(values))


def houston_percentile(field, value, radius=RADIUS_MI):
    return percentile(value, [p.get(field) for p in reference_profiles(radius)])


# --- Uses and signal plans ------------------------------------------------------

USES = {
    "indoor pickleball": {
        "osm": ['nwr["sport"~"pickleball"]'],
        "facility_word": "pickleball facilities",
        "kit_category": "fitness_recreation",
        "participation": {
            "fact": "US pickleball players, 2025 (ages 6+)", "value": 24_300_000, "core_players": 7_500_000,
            "source": "public:sfia", "url": "https://www.sfia.org/u-s-pickleball-participation",
            "note": ("SFIA Topline Participation: 24.3M players in 2025 (+479% since 2020), 7.5M core (8+ times a "
                     "year), 42.9% female; ages 13-24 have the highest participation rate. SFIA does not publish "
                     "age-specific rates on this page, so no age weighting is applied."),
        },
        "age_focus": None,
    },
    "fitness studio": {
        "osm": ['nwr["leisure"="fitness_centre"]', 'nwr["sport"~"^(fitness|yoga|crossfit|pilates|boxing|martial_arts)$"]["leisure"]'],
        "facility_word": "gyms and fitness studios",
        "kit_category": "fitness_recreation",
        "participation": None,
        "age_focus": None,
    },
    "childcare": {
        "osm": ['nwr["amenity"~"^(childcare|kindergarten)$"]'],
        "facility_word": "childcare centres",
        "kit_category": "childcare",
        "participation": None,
        "age_focus": "under_5",
    },
}
# Catalog uses (alternatives.CATALOG) whose demand is not driven by nearby residents.
NO_NEIGHBORHOOD_MODEL = {
    "warehouse / storage": "Business-to-business demand (logistics, contractors); residents nearby do not drive it.",
    "flex workspace": "Business-to-business demand; residents nearby do not drive it.",
    "office / service": "Demand depends on firms and workers, which ACS residence data does not measure.",
    "retail / showroom": "Too broad to model as one use; it depends on the specific store type.",
}


def plan(use):
    """Planner agent: which specialists run for this use, and why (a rule table, not an LLM)."""
    if use in USES:
        steps = ["site", "residents", "competitors", "momentum", "lookalike", "coordinator"]
        why = "Consumer-facing use: residents, local supply, business arrivals and a lookalike check all apply."
    else:
        steps = ["site", "residents", "coordinator"]
        why = NO_NEIGHBORHOOD_MODEL.get(use, "No neighborhood model for this use.")
    return steps, why


# --- Trace ---------------------------------------------------------------------

def run_agent(trace, agent, role, fn, inputs):
    """Run one specialist and record its step: inputs, sources, findings, confidence, hand-off."""
    started = time.perf_counter()
    step = {"agent": agent, "role": role, "computed_by": "code", "inputs": inputs,
            "sources": [], "findings": [], "summary": "", "confidence": None,
            "handoff": "", "signal": None, "status": "ok"}
    try:
        step.update(fn(**inputs) or {})
    except Offline as error:
        step.update(status="unknown", summary=f"Offline and not cached: {error}",
                    handoff="Signal stays unknown; nothing was guessed.")
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        step.update(status="error", summary=f"{type(error).__name__}: {error}",
                    handoff="Signal stays unknown; nothing was guessed.")
    step["ms"] = round(1000 * (time.perf_counter() - started))
    trace.append(step)
    return step


def stance(value, *, plus, minus, higher_is_better=True):
    """+1 / -1 / 0 from a percentile-style value; None stays unknown."""
    if value is None:
        return None
    if not higher_is_better:
        value = -value
        plus, minus = -plus, -minus
    return 1 if value >= plus else -1 if value <= minus else 0


# --- Agents --------------------------------------------------------------------

def residents_agent(lat, lon, use, radius=RADIUS_MI):
    """Who lives here: size, age mix, income and growth around the site vs the Houston area."""
    profile = area_profile(lat, lon, radius)
    sources = census_sources(2024) + census_sources(2019)
    if not profile:
        return {"sources": sources, "status": "unknown",
                "summary": "No Census tract point lies inside the radius; residents are unknown.",
                "findings": [record("residents_population", None, "public:acs", note="No tracts in radius.")]}
    totals = area_totals()
    acs_url = sources[1]["url"]
    note_area = (f"Sum of the {profile['tracts']} Census tracts whose internal point is within {radius:g} miles. "
                 "Tract edges make the area approximate.")
    pct = {f: houston_percentile(f, profile.get(f), radius) for f in
           ("population", "density_per_sqmi", "median_income_approx", "growth",
            "share_age_25_34", "share_age_35_54", "share_age_55_64", "share_age_65_plus", "share_under_5")}
    findings = [
        record("residents_population", profile["population"], "public:acs", "acs-2020-2024-tracts",
               "2020-2024", 0.9, acs_url, "agrees",
               note=f"{note_area} Margin of error about ±{profile['population_moe']:,} (90%). "
                    f"Houston-area percentile of 3-mile areas: {pct['population']}."),
        record("residents_density_per_sqmi", profile["density_per_sqmi"], "public:acs", "acs-2020-2024-tracts",
               "2020-2024", 0.85, acs_url, "agrees", note=f"Houston-area percentile: {pct['density_per_sqmi']}."),
        record("residents_median_income_approx", profile["median_income_approx"], "public:acs",
               "acs-2020-2024-B19013", "2020-2024", 0.7, acs_url, "agrees",
               note="Household-weighted mean of tract median household incomes (2024 dollars); an approximation, "
                    f"since medians do not add. Houston-area percentile: {pct['median_income_approx']}."),
        record("residents_growth_2019_to_2024", profile["growth"], "public:acs", "acs-2015-2019-vs-2020-2024",
               "2015-2019 vs 2020-2024", 0.6, acs_url, "agrees" if profile["growth"] is not None else "unknown",
               note=(f"Population {profile['population_2019']:,.0f} -> {profile['population']:,.0f} using each "
                     f"vintage's own tracts (2010 vs 2020 boundaries) within the same radius. Houston area overall: "
                     f"{totals['growth']:+.1%}. Overlapping 5-year samples, so this is a trend, not a yearly rate."
                     if profile["population_2019"] else "No 2015-2019 tracts in radius.")),
        record("residents_age_mix", {k[6:]: profile[k] for k in profile if k.startswith("share_")},
               "public:acs", "acs-2020-2024-B01001", "2020-2024", 0.85, sources[2]["url"], "agrees",
               note="Shares of residents by age band (ACS sex-by-age table B01001). Houston-area percentiles: "
                    + ", ".join(f"{k.removeprefix('share_')} {v}" for k, v in pct.items() if k.startswith("share_"))),
    ]
    spec = USES.get(use) or {}
    if spec.get("age_focus") == "under_5":
        findings.append(record(
            "residents_under_5", profile["under_5"], "public:acs", "acs-B01001-under-5", "2020-2024", 0.8, acs_url,
            "agrees", note=f"Children under 5 (ACS B01001) within {radius:g} miles; change since 2015-2019: "
                           f"{fmt_pct(profile['under_5_growth'])} (Houston area {totals['under_5_growth']:+.1%})."))
    participation = spec.get("participation")
    if participation:
        us_meta, us_6_plus = us_population_6_plus_record()
        sources.append(source("ACS 2020-2024 national population by age", us_meta))
        rate = participation["value"] / us_6_plus
        findings.append(record(
            "expected_players_at_national_rate", round(profile["population"] * rate), participation["source"],
            "sfia-2025-topline", "2025", 0.4, participation["url"], "agrees",
            note=(f"Residents x the national rate ({participation['value'] / 1e6:.1f}M players / "
                  f"{us_6_plus / 1e6:.0f}M Americans aged 6+ = {rate:.1%}). Assumes this area plays at "
                  "the national average; local rates are unknown. " + participation["note"])))
    growth_vs_area = None if profile["growth"] is None else profile["growth"] - totals["growth"]
    signal_value = profile["under_5_growth"] - totals["under_5_growth"] if (
        spec.get("age_focus") == "under_5" and profile["under_5_growth"] is not None) else growth_vs_area
    signal = {"name": "population trend", "stance": stance(signal_value, plus=0.02, minus=-0.02),
              "value": signal_value,
              "reason": (f"{'Under-5' if spec.get('age_focus') == 'under_5' else 'Population'} change since 2015-2019 "
                         f"is {fmt_pct(signal_value, signed=True, points=True)} vs the Houston area"
                         if signal_value is not None else "Trend unknown")}
    summary = (f"{profile['population']:,.0f} residents within {radius:g} mi "
               f"({pct['population']}th pct of Houston-area 3-mile areas), income ≈ ${profile['median_income_approx']:,} "
               f"({pct['median_income_approx']}th pct), growth {fmt_pct(profile['growth'], signed=True)} since 2015-19 "
               f"vs {totals['growth']:+.1%} area-wide.") if profile["median_income_approx"] else \
        f"{profile['population']:,.0f} residents within {radius:g} mi."
    return {"sources": sources, "findings": findings, "summary": summary, "confidence": 0.8,
            "profile": profile, "percentiles": pct, "signal": signal,
            "handoff": "Residents profile and trend to the lookalike agent (features) and coordinator (trend signal)."}


# --- OpenStreetMap facilities ----------------------------------------------------

def overpass_query(selectors):
    s, w, n_, e = BBOX
    body = "".join(f"{sel}({s},{w},{n_},{e});" for sel in selectors)
    return f"[out:json][timeout:120];({body});out center tags;"


def element_point(element):
    if "lat" in element:
        return element["lat"], element["lon"]
    center = element.get("center") or {}
    return center.get("lat"), center.get("lon")


def is_indoor(tags):
    return (tags.get("indoor") == "yes" or tags.get("leisure") in ("sports_centre", "sports_hall", "fitness_centre")
            or tags.get("building") not in (None, "no", "roof"))


def is_commercial(tags):
    return tags.get("fee") == "yes" or tags.get("access") == "customers" or tags.get("leisure") == "sports_centre"


def cluster(points, radius_mi):
    """Merge OSM features into facilities: courts in one park become one facility.

    Two features merge when they are within `radius_mi` and their names do not
    conflict (same name, or one is unnamed).
    """
    facilities = []
    for p in sorted(points, key=lambda p: (p["name"] is None, p["name"] or "")):
        for f in facilities:
            if miles(p["lat"], p["lon"], f["lat"], f["lon"]) <= radius_mi and (
                    p["name"] is None or f["name"] is None or p["name"].casefold() == f["name"].casefold()):
                f["features"] += 1
                f["osm_ids"].append(p["osm_id"])
                f["indoor"] = f["indoor"] or p["indoor"]
                f["commercial"] = f["commercial"] or p["commercial"]
                f["name"] = f["name"] or p["name"]
                break
        else:
            facilities.append({**p, "features": 1, "osm_ids": [p["osm_id"]]})
    return facilities


CLUSTER_MI = {"indoor pickleball": 0.15, "fitness studio": 0.03, "childcare": 0.03}


@lru_cache(maxsize=None)
def osm_facilities(use):
    """All facilities for a use across the Houston area, clustered. Returns (facilities, meta)."""
    query = overpass_query(USES[use]["osm"])
    payload, meta = fetch(OVERPASS, form={"data": query})
    points = []
    for e in payload.get("elements", []):
        lat, lon = element_point(e)
        if lat is None:
            continue
        tags = e.get("tags") or {}
        points.append({"lat": lat, "lon": lon, "name": tags.get("name"), "osm_id": f"{e['type']}/{e['id']}",
                       "indoor": is_indoor(tags), "commercial": is_commercial(tags)})
    facilities = cluster(points, CLUSTER_MI.get(use, 0.03))
    # Keep facilities inside the Houston area: within 2 miles of a Houston-area tract point.
    rows, _ = tract_table(2024)
    facilities = [f for f in facilities if near(rows, f["lat"], f["lon"], 2.0)]
    meta = {**meta, "url": OVERPASS + "?data=" + query}
    return facilities, tuple(sorted(meta.items()))


def osm_link(osm_id):
    return f"https://www.openstreetmap.org/{osm_id}"


def competitors_agent(lat, lon, use, radius=RADIUS_MI):
    """Who already serves it: facilities near the site and supply per 10k residents vs the Houston area."""
    facilities, meta = osm_facilities(use)
    meta = dict(meta)
    word = USES[use]["facility_word"]
    sources = [source(f"OpenStreetMap via Overpass ({word})", meta,
                      "Volunteer-mapped; coverage is incomplete, so absence on the map is not proof of absence.")]
    local = sorted(near(facilities, lat, lon, radius), key=lambda x: x[0])
    wider = near(facilities, lat, lon, 5.0)
    profile = area_profile(lat, lon, radius)
    totals = area_totals()
    area_rate = len(facilities) / totals["population"] * 10_000
    local_rate = len(local) / profile["population"] * 10_000 if profile and profile["population"] else None
    ratio = local_rate / area_rate if local_rate is not None and area_rate else None
    nearest = min(((miles(lat, lon, f["lat"], f["lon"]), f) for f in facilities), key=lambda x: x[0], default=None)
    when = meta["retrieved_at"][:10]
    findings = [
        record("competitors_within_radius", len(local), "public:osm", f"overpass-{use}", when, 0.6,
               meta["url"], "agrees",
               note=f"{word.capitalize()} within {radius:g} miles ({sum(f['indoor'] for _, f in local)} indoor or in a "
                    f"building, {sum(f['commercial'] for _, f in local)} fee/customer-only). Courts in one place count "
                    "as one facility. OpenStreetMap is incomplete."),
        record("competitors_within_5mi", len(wider), "public:osm", f"overpass-{use}", when, 0.6, meta["url"], "agrees",
               note="Same count at 5 miles."),
        record("supply_per_10k_residents", None if local_rate is None else round(local_rate, 2), "computed",
               "osm-count / acs-population", when, 0.5, meta["url"], "agrees" if local_rate is not None else "unknown",
               note=f"Houston area: {area_rate:.2f} per 10k ({len(facilities)} facilities / "
                    f"{totals['population']:,.0f} residents). Ratio here vs area: "
                    f"{'unknown' if ratio is None else f'{ratio:.2f}x'}."),
    ]
    if nearest:
        d, f = nearest
        findings.append(record("nearest_competitor", {"name": f["name"] or "(unnamed on the map)",
                                                      "miles": round(d, 2), "indoor": f["indoor"]},
                               "public:osm", f["osm_ids"][0], when, 0.6, osm_link(f["osm_ids"][0]), "agrees",
                               note="Straight-line distance, not drive time."))
    signal = {"name": "local supply", "value": None if ratio is None else round(ratio, 2),
              "stance": None if ratio is None else (1 if ratio <= 0.5 else -1 if ratio >= 2 else 0),
              "reason": ("Supply unknown" if ratio is None else
                         f"{len(local)} {word} within {radius:g} mi = {ratio:.1f}x the Houston-area rate per resident"
                         + (" (underserved)" if ratio <= 0.5 else " (crowded)" if ratio >= 2 else ""))}
    nearest_text = (f"; nearest {nearest[1]['name'] or 'unnamed'} at {nearest[0]:.1f} mi" if nearest else "")
    return {"sources": sources, "findings": findings, "signal": signal, "confidence": 0.5,
            "summary": f"{len(local)} {word} within {radius:g} mi, {len(wider)} within 5 mi{nearest_text}.",
            "handoff": "Supply ratio to the coordinator; facility locations are the lookalike agent's training data.",
            "nearby": [{"name": f["name"], "miles": round(d, 2), "indoor": f["indoor"], "commercial": f["commercial"],
                        "lat": f["lat"], "lon": f["lon"], "url": osm_link(f["osm_ids"][0])} for d, f in local[:15]]}


# --- CoStar kit tenancies --------------------------------------------------------

# Business category from the tenant's company name. CoStar's own industry code is too
# coarse here (gyms sit under Education, Personal Services or Arts & Recreation), so
# names decide, and the CoStar code is kept next to each tenant for audit.
CATEGORIES = {
    "fitness_recreation": re.compile(
        r"\b(gym|gyms|fitness|crossfit|yoga|pilates|barre|martial arts?|karate|taekwondo|tae kwon do|jiu[- ]?jitsu|"
        r"boxing|kickboxing|gymnastics?|cheer|dance (studio|academy|center)|pickleball|tennis|golf|climbing|"
        r"swim(ming)? (school|club|academy)|athletic club|sports (club|academy|center|complex)|orangetheory|"
        r"curves|f45|cyclebar|soulcycle|bootcamp|personal training|health club|rec(reation)? center)\b", re.I),
    "childcare": re.compile(
        r"\b(day ?care|child ?care|childcare|preschool|pre-school|montessori|kindercare|kiddie academy|"
        r"primrose school|goddard school|la petite|tutor time|learning (center|academy|tree)|early (learning|childhood)|"
        r"children'?s (center|academy|learning)|kids'? (academy|club|zone|world)|nursery school)\b", re.I),
    "food": re.compile(
        r"\b(restaurant|cafe|café|coffee|pizza|taco|tacos|taqueria|burger|grill|kitchen|bakery|bbq|bar-b-q|sushi|"
        r"donut|doughnut|deli|bistro|cantina|eatery|starbucks|subway|chick-fil-a|mcdonald'?s|wingstop|smoothie|"
        r"tea house|boba|ice cream|yogurt)\b", re.I),
    "medical": re.compile(
        r"\b(md|m\.d\.|dds|dmd|clinic|dental|dentist|medical|physician|physicians|pediatric|urgent care|"
        r"orthodont|chiropract|physical therapy|dermatology|cardiology|imaging|hospice|health ?care|surgery|"
        r"surgical|optometr|eye (care|associates)|pharmacy|counseling|therapy)\b", re.I),
}
CATEGORY_LABEL = {"fitness_recreation": "fitness & recreation", "childcare": "childcare", "food": "food & drink",
                  "medical": "medical", "other": "other businesses"}
# Suppliers and consultants to an industry are not the industry ("Golf Design", "Fitness Wholesalers").
NOT_A_VENUE = re.compile(r"\b(design|contractors?|wholesal\w*|consult\w*|equipment|suppl(y|ies)|network|"
                         r"services group|tour|council|apartments)\b", re.I)
NOT_A_DEPARTURE = {7: "Renewal", 12: "MovingIntoSameBuilding", 14: "OccupancySplit"}


def categorize(name):
    if name and NOT_A_VENUE.search(name):
        return "other"
    for category, pattern in CATEGORIES.items():
        if name and pattern.search(name):
            return category
    return "other"


def kit_path():
    for candidate in (os.environ.get("COSTAR_KIT"), os.environ.get("COSTAR_KIT_DIR"),
                      ROOT.parent / "costar-hackathon-kit", Path.home() / "Downloads" / "costar-hackathon-kit.zip"):
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None


def day(value):
    return (value or "")[:10] or None


@lru_cache(maxsize=4)
def kit_tenancies(kit=None):
    """Houston tenancies with location, category, arrival and departure dates.

    An arrival is the first occupancy of a tenant in a property (renewals and
    expansions are not new arrivals). A departure is an ended occupancy whose
    reason is not a renewal, a move within the building or a split.
    """
    from space_fit import kit_lines  # local import: the kit is optional for the rest of the pipeline
    kit = Path(kit) if kit else kit_path()
    if not kit:
        raise ValueError("CoStar kit not found. Set COSTAR_KIT to the unzipped kit folder or the zip.")
    password = os.environ.get("COSTAR_KIT_PASSWORD", "").encode() or None
    derived = CACHE / f"kit-tenancies-{hashlib.sha1(str(kit.resolve()).encode()).hexdigest()[:8]}.json"
    if derived.exists():
        return tuple(json.loads(derived.read_text()))
    places = {}
    for line in kit_lines(kit, "data/commercial-property.jsonl", password):
        prop = json.loads(line)
        a = prop.get("primaryAddress") or {}
        if a.get("state") == "TX" and a.get("latitude"):
            places[prop["id"]] = (a["latitude"], a["longitude"])
    companies = {}
    for line in kit_lines(kit, "data/company-detail.jsonl", password):
        c = json.loads(line)
        companies[c["id"]] = (c.get("name"), (c.get("profile") or {}).get("industryType"))
    rows = []
    for line in kit_lines(kit, "data/location-occupancy.jsonl", password):
        r = json.loads(line)
        if r.get("propertyId") in places:
            rows.append(r)
    first = {}
    for r in rows:
        k = (r.get("tenantLocationId"), r["propertyId"])
        start = day(r.get("moveInDate") or r.get("fromDate"))
        if r.get("tenantLocationId") and start and (k not in first or start < first[k]):
            first[k] = start
    out = []
    for r in rows:
        tenant = r.get("tenantLocationId")
        name, industry = companies.get(tenant, (None, None))
        start = day(r.get("moveInDate") or r.get("fromDate"))
        end = day(r.get("toDate"))
        reason = r.get("expirationReason")
        lat, lon = places[r["propertyId"]]
        out.append({
            "id": r["id"], "property_id": r["propertyId"], "lat": lat, "lon": lon, "name": name,
            "costar_industry": industry, "category": categorize(name) if name else "unknown",
            "arrival": start if tenant and first.get((tenant, r["propertyId"])) == start else None,
            "departure": end if end and reason not in NOT_A_DEPARTURE else None,
            "sqft": sum((sp.get("squareFeetOccupied") or 0) for sp in r.get("spaces") or []) or None,
        })
    derived.parent.mkdir(parents=True, exist_ok=True)
    derived.write_text(json.dumps(out))
    return tuple(out)


MOMENTUM_RADIUS_MI = 5.0  # wider than the residents radius: the kit is a sample of buildings


def momentum_agent(lat, lon, use, radius=MOMENTUM_RADIUS_MI, kit=None, today=None):
    """What is moving in: arrivals and departures of this kind of business near the site (CoStar kit)."""
    rows = kit_tenancies(kit)
    category = USES[use]["kit_category"]
    label = CATEGORY_LABEL[category]
    today = today or datetime.now(timezone.utc).date().isoformat()
    since = f"{int(today[:4]) - 3}{today[4:]}"
    local = [r for _, r in near(rows, lat, lon, radius)]
    buildings = len({r["property_id"] for r in local})
    years = list(range(int(today[:4]) - 7, int(today[:4]) + 1))

    def by_year(items, field):
        return {y: sum(1 for r in items if r[field] and r[field][:4] == str(y) and r[field] <= today) for y in years}

    mine = [r for r in local if r["category"] == category]
    arrivals = by_year(mine, "arrival")
    departures = by_year(mine, "departure")
    recent_in = [r for r in mine if r["arrival"] and since < r["arrival"] <= today]
    recent_out = [r for r in mine if r["departure"] and since < r["departure"] <= today]
    all_in = sum(1 for r in local if r["arrival"] and since < r["arrival"] <= today)
    all_out = sum(1 for r in local if r["departure"] and since < r["departure"] <= today)
    houston_in = [r for r in rows if r["arrival"] and since < r["arrival"] <= today]
    houston_share = sum(r["category"] == category for r in houston_in) / len(houston_in) if houston_in else None
    local_share = len(recent_in) / all_in if all_in else None
    net = len(recent_in) - len(recent_out)
    enough = len(recent_in) + len(recent_out) >= 2
    source_id = "costar-kit:location-occupancy+company-detail+commercial-property"
    caveat = ("The kit covers only CoStar's Matterport-scanned properties (about 1,758 in Houston), so this is a "
              "sample of buildings, not every business. Categories come from tenant names (keyword rules).")
    findings = [
        record(f"kit_{category}_arrivals_by_year", arrivals, "costar", source_id, today, 0.5, None, "agrees",
               note=f"{label.capitalize()} tenants arriving in {buildings} kit buildings within {radius:g} mi. "
                    "First occupancy of a tenant in a building; renewals excluded. " + caveat),
        record(f"kit_{category}_departures_by_year", departures, "costar", source_id, today, 0.5, None, "agrees",
               note="Ended occupancies, excluding renewals, moves within the building and splits."),
        record(f"kit_{category}_net_last_3_years", net if enough else None, "costar", source_id, today, 0.4, None,
               "agrees" if enough else "unknown",
               note=(f"{len(recent_in)} arrived, {len(recent_out)} left since {since}." if enough else
                     f"Only {len(recent_in) + len(recent_out)} {label} moves since {since} in the sample: too few "
                     "to call a trend.")),
        record("kit_all_business_net_last_3_years", all_in - all_out, "costar", source_id, today, 0.5, None, "agrees",
               note=f"All tenants within {radius:g} mi: {all_in} arrived, {all_out} left since {since}."),
        record(f"kit_{category}_share_of_arrivals", None if local_share is None else round(local_share, 3), "costar",
               source_id, today, 0.4, None, "agrees" if local_share is not None else "unknown",
               note=f"Share of arrivals here that are {label}, vs {fmt_pct(houston_share)} across all Houston kit "
                    "buildings in the same period."),
    ]
    signal = {"name": "business arrivals", "value": net if enough else None,
              "stance": None if not enough else (1 if net > 0 else -1 if net < 0 else 0),
              "reason": (f"{len(recent_in)} {label} businesses moved into nearby CoStar buildings since {since[:4]}, "
                         f"{len(recent_out)} left" if enough else
                         f"Too few {label} moves in the CoStar sample nearby to call a trend")}
    examples = sorted(recent_in, key=lambda r: r["arrival"], reverse=True)[:6]
    return {"sources": [{"name": "CoStar hackathon kit: tenancies, companies, properties", "url": None,
                         "retrieved_at": None, "cached": True, "note": caveat}],
            "findings": findings, "signal": signal, "confidence": 0.4,
            "summary": (f"{len(local)} tenancies in {buildings} kit buildings within {radius:g} mi. {label.capitalize()}: "
                        f"{len(recent_in)} arrived, {len(recent_out)} left since {since[:4]}; all businesses: "
                        f"{all_in} arrived, {all_out} left."),
            "handoff": "Category momentum to the coordinator (counts only with 2+ moves). All-business moves are "
                       "context, not a vote: they are not specific to this use.",
            "examples": [{"name": r["name"], "arrived": r["arrival"], "sqft": r["sqft"],
                          "costar_property_id": r["property_id"]} for r in examples]}


@lru_cache(maxsize=None)
def us_population_6_plus_record():
    """US residents aged 6+ from the ACS 2020-2024 national table (SFIA surveys ages 6+)."""
    key = os.environ.get("CENSUS_API_KEY")
    query = {"get": "B01003_001E,B01001_003E,B01001_027E,B01001_004E,B01001_028E", "for": "us:1"}
    if key:
        query["key"] = key
    rows, meta = fetch(ACS.format(year=2024), query)
    cells = dict(zip(rows[0], rows[1]))
    total = float(cells["B01003_001E"])
    under5 = float(cells["B01001_003E"]) + float(cells["B01001_027E"])
    age5to9 = float(cells["B01001_004E"]) + float(cells["B01001_028E"])
    # Age 5 is one fifth of the 5-9 band (assumes even ages within the band).
    return meta, total - under5 - age5to9 / 5


def fmt_pct(value, signed=False, points=False):
    if value is None:
        return "unknown"
    if points:
        return f"{value * 100:+.1f} pts"
    return f"{value:+.1%}" if signed else f"{value:.1%}"
