# Compliance layer (building check, then business check)

Answers "who would permit this, what has to be checked, and is anything already a blocker?" for one
property and one business. It never says a permit is approved: every legal item stays
`needs_verification`, and nothing retrieved from the web can clear a gate.

Files (on `feat/compliance-engine`, PR #17):

| File | What it does |
|---|---|
| `playground/jurisdiction.py` | lat/lon → `houston`, `harris_unincorporated`, `los_angeles`, `la_unincorporated`, or none, from Census official boundaries |
| `playground/compliance_engine.py` | building check (`preflight`) and business check (`check_business`), Helix handoff adapter, kit adapter, cached official-source research. The business check resolves any of the 26 registry categories (`neighborhood_industries.resolve`) and runs the team's `neighborhood.building_fit` |
| `playground/test_jurisdiction.py`, `playground/test_compliance_engine.py` | 7 + 15 tests |

Needs **Python 3.10+** (the rest of `playground/` uses `X | None` types; macOS `/usr/bin/python3` is 3.9).

## How it works

1. **Jurisdiction.** If the context has no verified jurisdiction but has a pin, `resolve_jurisdiction(lat, lon)`
   asks the Census geocoder (geographies by coordinates, no key) which incorporated place and county contain
   the point. Another city inside a modeled county (Bellaire, Pico Rivera) gets **no** code, never the county.
   Postal city is never used: 9721 Cypresswood Dr has a "Houston" address but is in unincorporated Harris County.
2. **Building check (`preflight`).** Hard gates, in code:
   - `jurisdiction_unverified`: no supported authority found (research is deferred)
   - `identity_incomplete` / `identity_conflict`: property or scope unclear
   - `commercial_conversion_unestablished`: CoStar says residential / multifamily: **stops** before any business research
   It lists the building facts it was given (size, clear height, floors, parking, HVAC, fire) as evidence records,
   the jurisdiction with its source, any flagged tour (e.g. Tanner's scan captioned 9750), and a 6-item
   verification checklist (identity, occupancy, fire, accessibility, parking, MEP).
3. **Business check (`check_business`).** Only if the building check allows it:
   - requirements for the demo businesses come from the team's existing thresholds (`space_fit.USES`):
     pickleball 30x60 ft per court and 18 ft clear (marked as unofficial guidance, not code); childcare 30 sq ft
     indoor / 80 sq ft outdoor per child for Texas only (California childcare gets "verify CA licensing", not Texas
     numbers); restaurant checklist
   - building-level CoStar numbers are **not** treated as the suite's usable size or height
     (`measurements_match_scope` stays false unless a caller measured the suite)
   - two Tavily searches restricted to the authority's official domains, worded the way permit offices describe
     the business ("assembly occupancy", "child care center", "food service establishment"); park and cannabis
     pages and duplicates are dropped; each result is `applicability: unverified`

## Run it

```bash
set -a; source .env; set +a      # TAVILY_API_KEY for --live
python3 playground/compliance_engine.py --property-id 23296 --suite A --business indoor_pickleball --live
python3 playground/compliance_engine.py --property-id 13890701 --business childcare --live
python3 playground/compliance_engine.py --property-id 966604 --business indoor_pickleball        # stops: residential
python3 playground/compliance_engine.py --property-id 23296 --suite A --business indoor_pickleball --offline
python3 playground/jurisdiction.py 29.8540 -95.5317
```

- `--live` saves every search to `playground/output/compliance/research/` and every jurisdiction lookup to
  `playground/output/jurisdiction/` (both gitignored). `--offline` replays those with no network; anything not
  cached comes back as unknown, never guessed.
- A Helix Stage 1 handoff (`selected_listing` with `property_id`, `listing_id`, `space_id`, address, lat/lon) or a
  hand-written context JSON also works: `python3 playground/compliance_engine.py context.json --business childcare`.

## Results on real kit buildings (live, Nov 14)

| Property | Jurisdiction | Building check | Business check |
|---|---|---|---|
| 9700 Tanner Rd, suite A (23296) | City of Houston | passes; tour captioned 9750 flagged, not used | pickleball: Houston Permitting Center process page + "start a business" pages (some only loosely related, e.g. a BYOB occupancy memo) |
| 6855 Wynnwood Ln (13890701) | City of Houston | passes | childcare: Texas 30/80 sq ft per child; fire code + permit pages. Pickleball, restaurant: permit pages |
| 9721 Cypresswood Dr (966604) | **unincorporated Harris County** | **stopped**: residential | not run |
| 11040 W Pico Blvd, LA (1565338) | City of Los Angeles | passes | childcare: CA rules marked unverified; LADBS certificate-of-occupancy + license pages |

## Limits (say these, don't hide them)

- Search finds relevant official process pages, not rules confirmed for this parcel or suite.
- Census boundaries update yearly and can lag annexations; confirm edge parcels with the city's GIS.
- Only the four authorities above are modeled; other cities return "not modeled".
- All 26 registry categories get the team's building-fit screen (planning ranges, not code). Legal thresholds
  exist only for pickleball (sport guidance), Texas childcare (26 TAC 746) and the restaurant checklist.
- Research keeps official pages that mention permitting and lists pages naming the business first; some results
  are still general city process pages.
- No imagery-based checks (parking, HVAC, fire equipment) yet; those stay unknown.
- The Helix adapter follows Stage 1's `discovery.normalize_listing` fields (checked read-only against PR #18).
  Those listings carry no coordinates, so the adapter reads `latitude`/`longitude` from a nested `property` detail
  if present, else looks the pin up in the CoStar kit by `property_id` (cached in `output/compliance/pins.json`).
  Helix's investigate handoff is `{selected_listing, property_facts}`; the pin comes from `property_facts`.
  Tested on a real handoff generated with Helix's own Stage 1 code (PR #18, run read-only): Tanner → City of Houston,
  pickleball fits, childcare "check" (outdoor play space not recorded).

Official references (checked Nov 14, 2026):
- https://www.houstontx.gov/business/plan/permits-inspections.html (City of Houston)
- https://oce.harriscountytx.gov/Services/Permits/Permits-A-to-Z/Commercial-Building (Harris County)
- https://dbs.lacity.gov/services/search-online-building-records (City of LA)
- https://permits.lacounty.gov/permits/building-and-safety/ (LA County)
- https://geocoding.geo.census.gov/geocoder/ (jurisdiction lookup)
