# Houston property playground

Search Houston addresses in the CoStar sponsor kit and inspect their property
records, Vexcel aerial imagery, and linked Matterport scans. The playground
uses Python 3.10+ and the standard library.

## Setup

1. Check out the playground branch. From a fresh checkout:

   ```sh
   git clone --branch feature/pilot https://github.com/sm11t/hackprinceton.git
   cd hackprinceton
   ```

   If you already have the repo, run `git fetch origin` and
   `git switch feature/pilot` from its root.

2. Download `costar-hackathon-kit.zip` from the team's private Slack
   `#env-keys` channel and leave it zipped. The examples assume it is in
   `~/Downloads`; pass your actual path to `--kit` if it is elsewhere.

3. Run `cp .env.example .env` if you don't already have a local `.env`.
   Fill in the four values from `#env-keys`:

   | Variable | Value |
   | --- | --- |
   | `COSTAR_KIT_PASSWORD` | CoStar kit ZIP password |
   | `MATTERPORT_API_KEY` | Matterport GraphQL API key |
   | `MATTERPORT_API_TOKEN` | Matterport GraphQL API token |
   | `VEXCEL_API_KEY` | Vexcel API key |

   Keep `.env`, the ZIP, and generated sponsor data local. The sponsor
   credentials are available for the duration of the hackathon.

## Run the browser playground

From the repo root:

```sh
set -a
source .env
set +a
python3 playground/web.py --kit "$HOME/Downloads/costar-hackathon-kit.zip"
```

Open [localhost:8765](http://127.0.0.1:8765). Search for **9700 Tanner Rd**
to verify the CoStar record, Vexcel aerial, and Matterport room table. Select
a scan to see its rooms, or expand **View 3D tour** to open the Matterport player inline. Use
`--port 8766` and open port 8766 if port 8765 is already occupied.

## Run the command-line probe

With the same environment loaded:

```sh
python3 playground/probe.py --kit "$HOME/Downloads/costar-hackathon-kit.zip"
```

The default is CoStar property `23296` (9700 Tanner Rd). Use
`--property-id` to pick another property from the kit's
`commercial-properties.csv`, `--model-id` to select a specific linked scan,
or `--costar-only` to check the local join without network calls.

Results go to `playground/output/` as evidence JSON and, if Vexcel succeeds,
an aerial JPEG. Provider errors are recorded in the JSON and cause a nonzero
exit status. Matterport room fields can be blank for a valid scan. Scans can
cover only part of a building, and the aerial crop can include nearby parcels.

## Matterport photo for the Jev test

Use the sponsor's [Matterport Model Playground](https://beta-app.matterport.com/2026-princeton-hackathon/graphiql)
with the same GraphQL credentials. Select **Pano Locations** and run it for
`oNAvrNiXZS7`, the linked model for 9700 Tanner Rd. The query exposes
panorama image links for the scan. Use one of those images for the Jev
Choice + Box test. The local browser's aerial comes from Vexcel. Jev uses
its own API key.

- [Sponsor quickstart](https://beta-app.matterport.com/2026-princeton-hackathon/quickstart)
- [Matterport API](https://developers.matterport.com/api/)

## Tanner Road redevelopment pilot (`feature/pilot`)

The root URL now opens the UI-only onboarding and agent-workspace mock (see `MOCK_FLOW.md`). The Tanner Road evidence workspace remains at `/pilot`. The existing address search
is available at `/search` (and existing `/?q=...` links still work).

The pilot compares **two tenant operations in the advertised 10,000 SF suite**.
It uses `nessie_pilot.simulate` directly, preserving Jayant's simulator and its
CLI. The tenant pickleball scenario supplies starting cash, recurring bills,
build duration and operating costs. The warehouse baseline adds explicit demo
assumptions: $25,000 fit-out over one month, $18,000 monthly business revenue,
$5,000 monthly operating costs and $2,000 monthly carry. It is not a comparison
between landlord rental income and tenant business income. The chart extends
the tenant scenario to 24 months and includes starting cash at month 0.

- Edit pickleball build-out, paid bookings, additional delay, reserve and warehouse
  revenue to recalculate. Reset restores the demo assumptions.
- Three courts is an **unverified hypothesis**, not a capacity estimate. The
  advertised suite is not matched to the scan named 9750 Tanner Rd. Building
  area, scanned warehouse room area and advertised suite area remain separate.
- An 18 ft advertised height and $8,500 NNN base rent are carried forward from
  `scenarios/tanner_pickleball_tenant.json`; the current listing is not reverified.
- CoStar comes from the local kit. Matterport and Vexcel are live by default.
  Provider failures have explicit unavailable states; the simulator stays usable.
- To read an existing Nessie sandbox balance and recurring bills, add
  `--nessie-account ACCOUNT_ID` with `NESSIE_API_KEY` set. These are read once at
  startup; no bank records are created. Without this flag, the UI identifies
  scenario cash and bills as simulated.

For a reliable local evidence replay, run `probe.py` once while connected, then:

```sh
python3 playground/web.py --kit "$HOME/Downloads/costar-hackathon-kit.zip" --offline
```

`--offline` reads saved Matterport evidence and Vexcel imagery from the ignored
`playground/output/` directory. It still requires the CoStar kit, labels evidence
as a saved capture, and does **not** make the external Matterport tour offline.
Missing saved imagery/measurements display unavailable states. Never commit the
sponsor kit, generated captures or credentials.

Validation:

```sh
python3 -m unittest discover -s playground -p 'test_*.py'
node --check playground/static/pilot.js
```

Tanner demo path: open `/pilot` → inspect aerial/tour → compare the three evidence scopes →
change opening delay from 0 to 3 → observe the $5,000 reserve gap in month 6 →
review the suite identity and dimension check before estimating court count.

### Tanner Location & Demand

Load the sponsor keys along with `UPSTAGE_API_KEY`, `TAVILY_API_KEY` and the
activated `CENSUS_API_KEY` into your shell. From the repo root, run:

```sh
uv run playground/location_run.py --kit "$HOME/Downloads/costar-hackathon-kit.zip" \
  --output playground/output/location-tanner.json
```

CoStar archive joins, Matterport rooms and Vexcel structure data build the
property evidence packet. The Census geocoder, FEMA and ACS provide public
context. A Deep Agents supervisor calls three specialists for property
evidence, market research and independent claim review. Market research makes
at most one Tavily search and extracts up to three pages. Candidate web claims
must match an exact excerpt from a fetched page and pass the reviewer. Census
and FEMA summaries come directly from the API values. Demand remains unverified.

The kit run sends selected property evidence fields to Upstage. Use
`--public-only` for the public Tanner address and public sources. Add
`--skip-market` to omit Tavily retrieval. Individual source gaps are recorded
in the review. The saved report is local and gitignored.

Start the existing Python web server, choose Tanner Road and indoor pickleball,
then open the saved review in the Location & Demand panel. Re-run the CLI and
reload the review to refresh it. The endpoint serves accepted findings and
source references. Raw sponsor and search payloads stay in the local report.

### Live Location & Demand demo

Start the web server with the CoStar kit and the same credentials as the
Location & Demand CLI. Open `/location-demo`, pick Houston or Los Angeles,
filter the property dropdown by address, choose a proposed use, and click
**Run live review**. Houston starts with 9700 Tanner Rd selected. Allow a few
minutes for source retrieval and agent review. The page shows findings,
citations, and verification gaps. Each run uses its own temporary report and
does not overwrite the saved Tanner review.
## Evidence reconciliation (`reconcile.py`)

Cross-checks CoStar, Matterport and public data for one property and emits
facts in the shared evidence-record contract (Spec canvas → API contracts):
`fact, value, source, source_id, captured_at, confidence, evidence_url,
status (agrees|conflict|unknown), needs_human, note`.

```sh
set -a; source .env; set +a
python3 playground/reconcile.py --kit "$HOME/Downloads/costar-hackathon-kit.zip" --property-id 23296
python3 playground/reconcile.py --kit "$HOME/Downloads/costar-hackathon-kit.zip" --scan-identity Houston
python3 playground/reconcile.py --kit "$HOME/Downloads/costar-hackathon-kit.zip" --scan-occupancy Houston
```

**Occupancy at scan time** (from Asmit's data pilot, `attdates.py` + `hist.py`):
for a scan that names a suite, find the CoStar tenancy covering that suite on
the scan's `originationDate`. Suites are matched from both the space rows and
the tenant's company record, and spellings are normalised (`C-1A` = `C1A`).
- Lease running well past the scan → `conflict` (marketing scans are usually of
  empty space, so CoStar's record is stale or the scan shows the tenant's own space).
- Lease ending within a year, or move-in under 180 days before the scan date →
  `unknown`, needs a look at the tour photos (pre-marketing is normal).
- Tenant moved in after the scan, or left before it → `agrees` (the usual false alarm).
- Scan captioned for another building → not compared.

Houston: 356 suite-named scans: 135 agree, 33 conflict, 188 unknown (mostly no
tenancy recorded for the suite). Takes ~50 s.

**CoStar size math:** gross area vs typical floor × stories (±20%) and rentable
> gross. E.g. 1800 Sherwood Forest St: 24,567 sq ft gross vs 18,000 sq ft × 1
story = 1.36× → conflict. The aerial footprint vs floor-size check is in
`exterior.py` (physical fit), not duplicated here.

Checks: scan caption address vs CoStar address, scan date (CoStar
`originationDate`, never Matterport `created`), ceiling height of the largest
scanned space vs CoStar, FEMA flood zone at the pin. `--offline` skips network
calls. Houston run: 7 of 1,731 scanned properties have a scan captioned with a
different address (most captions name no address, so only ~44 can be tested).

## Market ranking (`market_rank.py`)

"Where should I do this?" Ranks every active for-lease space in a market for one use and
cash budget, then links each result into the full `/maximo` review (suite preselected, review
runs on open). On `/maximo`, use **Find the best matches** under the form.

```sh
set -a; source .env; set +a
python3 playground/market_rank.py --kit "$HOME/Downloads/costar-hackathon-kit.zip" --use "indoor pickleball" --capital 500000
```

API: `GET /api/maximo/rank?use=&capital=&reserve=&market=Houston[&min_sf=&max_sf=]`. The
server reads the market once at startup (~30 s, in the background), then each ranking takes
0.5–3 s.

Rules: property type must suit the use, residential properties and dwelling tours are out,
`space_fit` on CoStar facts must not rule it out, and the space must meet a minimum size
(pickleball: 3 courts = 5,400 sq ft, matching the cash scenario's 3-court revenue; fitness
1,500 sq ft; others 1,000 sq ft; override with `--min-sf`). Ranked by fit verdict, then
within budget, then no evidence flag (tour for another address, CoStar size math, asking rent
under $3/sq ft/yr), then a listed rent, then lowest planning cash to open. One space per
building, no numeric score. Limits: no per-building aerial/scan data, so most non-pickleball
uses are "investigate"; cash uses the same unverified allowances as the review; lease only.

Houston, pickleball, $500k: 2,431 spaces in 240 buildings → 37 pass, top 5 = 15603 W Hardy
Rd #350, 5829 W Sam Houston Pky #1009, 6855 Wynnwood Ln (9,900 sq ft), 1923 Kolfahl St,
5025 Jensen Dr.

## Physical fit (`space_fit.py`, `exterior.py`, `interior.py`)

Answers "can this building or listed space physically support the proposed use?"
for `pickleball`, `gym`, `restaurant`, `daycare` and `workshop`, with every fact in
the shared evidence-record contract. The browser shows it live in the
**Space & condition** specialist; the API is
`GET /api/space-fit?property_id=<CoStar id>&use=<use>[&suite=<suite>]`.

```sh
set -a; source .env; set +a
python3 playground/space_fit.py --kit "$HOME/Downloads/costar-hackathon-kit.zip" --property-id 13890701 --use pickleball
python3 playground/space_fit.py --kit <unzipped kit dir> --property-id 23296 --use daycare --offline
```

`--kit` takes the encrypted zip (with `COSTAR_KIT_PASSWORD`) or an unzipped folder.
Vexcel and Matterport responses are cached in `playground/output/` (gitignored), so
`--offline` replays them.

**Verdict:** `supported` (nothing in the data rules the use out), `investigate`
(something that decides fit is unknown), `does_not_fit` (the evidence rules it out).
Only use-specific checks drive the verdict; general building facts and the
ask-before-signing checklist are shown, not judged.

| Evidence | Source | Rule |
| --- | --- | --- |
| Size, stories, docks, drive-in doors, power (phases/amps/volts), parking, sprinklers, floor load | CoStar kit | Missing values are `unknown`, never assumed |
| Listed spaces in this building | CoStar listings (`forLeaseSummary.spaces` with this `propertyId`) | Park-wide listings are not counted against one building |
| Which space is judged | `--suite`, else a listed space that has a same-address scan, else the largest | Scans match a listing by suite, or by advertised size within 2% |
| Footprint, roof height, ground elevation, roof type and defects, rooftop AC, vehicles | Vexcel `property/extract` with `include=precomputed,calculated` | Only the footprint containing the CoStar pin is used; roof height under 8 ft per story is a data error; roof condition score is shown, not judged |
| Measured area and clear height | Matterport rooms | Scans captioned with another address are not measured; height 0 = unknown; a scan's height applies only to the listed space it names |
| Thresholds | USA Pickleball rule 3.A.3 (30x60 / 34x64 ft per court); Texas 26 TAC 746 (30 sq ft indoor, 80 sq ft outdoor per child) | 18 ft pickleball ceiling is unofficial guidance, low confidence |

**Your own requirements** (the "type and decide" path): `--use custom --label "Climbing gym"
--require min_clear_height_ft=20 --require min_area_sf=6000 --require three_phase=yes`, or the
same keys as query parameters on `/api/space-fit`. Keys: `min_clear_height_ft`,
`min_area_sf`, `max_area_sf`, `min_docks`, `min_drive_in_bays`, `min_parking_spaces`,
`min_amps`, `min_floor_load_psf`, `three_phase`, `sprinklers`. On a built-in use they add to
its own checks. Missing data is `unknown`, never a pass or a fail.

**Open to suggestions:** `--rank` (or `GET /api/space-fit/rank?property_id=`) judges every
built-in use for the space, best first, each with the deciding reason. Uses with no
data-checkable threshold (gym, restaurant, workshop) say so instead of getting a score.

**Known-answer checks** on the pilot's real buildings (Wynnwood, Willow Place, Northgreen,
Tanner, Grant Rd) run when the kit is available, using cached provider responses:

```sh
COSTAR_KIT="$HOME/Downloads/costar-hackathon-kit.zip" python3 -m unittest playground/test_known_cases.py
```

Good demo properties: **6855 Wynnwood Ln (13890701)**, a listed 9,900 sq ft
warehouse whose scan measures 96% of it with a 21.1 ft clear height (5 courts,
supported). **9700 Tanner Rd (23296)**: supported on CoStar's 18 ft and Vexcel's
33.8 ft roof, but its scan is captioned 9750 Tanner Rd and is not used.
**8203 Willow Place (239686)**: office suite 315 measured at 7.9 ft (does not fit).

## Deal facts for lease-or-buy (`deal.py`)

What a property actually asks and last sold for, as evidence records, for the money
step. Shown live in the **Money** panel; API `GET /api/deal?property_id=<id>[&capital=&suite=&square_feet=]`.

| Fact | From | Rule |
| --- | --- | --- |
| `lease_asking_rent` | Active `forLeaseSummary.spaces` in this building | Normalized to $/month and $/sq ft/year from `rateBasis`; lease basis explained (NNN = plus taxes, insurance, common-area costs); no rate = unknown |
| `sale_asking_price` | Active `forSaleSummary` on this property | Asking price, $/sq ft, owner/user vs investment, days on market; a bundle of properties is flagged |
| `last_sale_price` | Sale comps that include this property | Undisclosed Texas prices are unknown; bulk-portfolio and entity sales are not this building's value |
| `capital_vs_lease`, `capital_vs_purchase` | The above + the buyer's capital | States what each path needs up front; never recommends a path (the Nessie simulator compares cash flows) |

Examples: Tanner suite A asks $0.85/sq ft/month NNN = $8,500/month (the pilot's
scenario rent, now sourced). Wynnwood's 9,900 sq ft space asks $7,920/month NNN and the
property is also for sale at $7.93M with one other property, so leasing and buying can
both be compared there.

**Cash simulation uses the kit's rent.** `POST /api/pilot/simulate` replaces the scenario's
"Suite base rent" bill with the CoStar asking rent for the scenario's space (`costar_id` and
`suite_sqft` in `scenarios/tanner_pickleball_tenant.json`, via `deal.rent_for_simulation`).
The response says where the rent came from (`rent_source`, `bills`), and `/pilot` prints it.
If the kit can't be read or the space has no asking rent, the scenario's assumed rent stays
and `rent_source` is `scenario assumption`. Build cost, bookings and other dollars remain
editable assumptions.

### Combined redevelopment review

Open `/maximo` and choose a kit property, an advertised suite, and a proposed use.
The review brings together dated identity and occupancy checks, space and condition,
listing terms, location research, approvals to confirm, and a cash comparison.
Tanner's demo shortlist card also opens the combined review with your budget inputs.

Start the server using the kit and sponsor credentials above. Live location research
also needs `uv` and `UPSTAGE_API_KEY`; configure Tavily and Census for their findings.
With `--offline`, the review uses the kit and any cached property evidence and skips
live market research. `--nessie-account` reads sandbox starting cash and recurring
bills. Review the displayed monthly costs for overlap with those bills.

The same advertised suite must match one active listing before its base rent is
prefilled. Cash inputs remain editable, and the approval allowance, build-out, and
delay update the modeled opening month together. Before relying on court capacity,
confirm the scan covers the advertised suite and obtain a dimensioned plan. City
guidance identifies approvals to investigate. Parcel jurisdiction, approved use,
and paid demand still require verification.

A property review pauses when the kit cannot establish the commercial premises for
the selected deal. Cypresswood (966604) is the residential regression, Tanner Suite A
and Wynnwood's unnamed 9,900 sq ft listing are the commercial paths. A separately
requested hypothetical scenario uses editable placeholders. The property decision
shows evidence by issue and records behind expandable details.
