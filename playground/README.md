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
