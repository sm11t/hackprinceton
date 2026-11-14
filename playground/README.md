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

## Evidence reconciliation (`reconcile.py`)

Cross-checks CoStar, Matterport and public data for one property and emits
facts in the shared evidence-record contract (Spec canvas → API contracts):
`fact, value, source, source_id, captured_at, confidence, evidence_url,
status (agrees|conflict|unknown), needs_human, note`.

```sh
set -a; source .env; set +a
python3 playground/reconcile.py --kit "$HOME/Downloads/costar-hackathon-kit.zip" --property-id 23296
python3 playground/reconcile.py --kit "$HOME/Downloads/costar-hackathon-kit.zip" --scan-identity Houston
```

Checks: scan caption address vs CoStar address, scan date (CoStar
`originationDate`, never Matterport `created`), ceiling height of the largest
scanned space vs CoStar, FEMA flood zone at the pin. `--offline` skips network
calls. Houston run: 7 of 1,731 scanned properties have a scan captioned with a
different address (most captions name no address, so only ~44 can be tested).

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

## Market rent check (trained model)

`rent_model.py` learns what spaces like this one were asking when they leased, from the kit's
signed lease deals, and writes a low / typical / high $/sq ft/year range for every listed space
(including "call for rate" spaces) to `playground/output/rent-estimates.json`. That folder is
gitignored because the file is derived from sponsor data. The deal panel shows it as
`market_rent_range` next to each asking rent. If the file is missing, the check is skipped.

```bash
python3 -m venv .venv && .venv/bin/pip install scikit-learn numpy   # training only; the server stays stdlib
.venv/bin/python playground/rent_model.py --kit ~/Downloads/costar-hackathon-kit.zip   # ~1 min on a laptop CPU
```

| Choice | Why |
| --- | --- |
| Target: asking rent on signed deals, normalized to $/sq ft/yr | 15,609 deals have it; contract rent is on only ~2,000 |
| Deals since 2012, one model for office-type space and one for the rest | 87% of deals are office; a single model, or all years, did worse on industrial and flex for held-out buildings |
| Inputs: use, lease basis (`serviceType`), size, year, building type/class/age/size/stories, submarket, location | Lease basis must be an input: full service and NNN rents are not comparable |
| Gradient-boosted trees, 10th/50th/90th percentile loss, widened by a conformal margin | Gives a range, and the margin makes it hold ~80% of rents in buildings the model never saw |
| Model served per space use only where it beat the baseline in every held-out test | Flex and medical currently show the middle 80% of similar recent deals instead, and say so |

Evaluation (5 folds grouped by building, so every test building is unseen; baseline = median of
the same city, use and lease basis):

| Test | Model median error | Baseline | Range holds the rent |
| --- | --- | --- | --- |
| 2,110 signed deals from the last 7 years | 16.2% | 22.7% | 86% |
| 2,085 current listings' asking rents | 15.4% | 21.7% | 84% |

Weak spots: office/retail and flex listings (few examples); industrial ranges held 68% of current
asking rents. Each record states its method, the number of similar deals behind it, and is marked
unknown when fewer than 30 recent deals share its use and lease basis. Examples: Tanner suite A asks
$10.20 vs $5.76–$15.00 for 79 similar Houston flex NNN deals; Wynnwood asks $9.60 vs a modeled
$9.38–$18.87.
