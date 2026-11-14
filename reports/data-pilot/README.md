# Data pilot: cross-checking CoStar, Matterport and Vexcel

Scripts behind the "building lie detector" pilot (29 Houston buildings). Results and caveats are in [findings.md](findings.md). Standard library only, except `sheet.py`, which needs Pillow.

## Setup

1. Unzip the sponsor kit (password in `#env-keys`) somewhere outside Git, e.g. `costar-hackathon-kit/` at the repo root (gitignored).
2. Export the paths and keys (never commit them):

   ```sh
   export COSTAR_KIT_DIR=/path/to/costar-hackathon-kit
   export MATTERPORT_API_KEY=...  MATTERPORT_API_TOKEN=...  VEXCEL_API_KEY=...
   ```

3. Run from the repo root. Outputs (`*.pkl`, `raw/`, `img/`, `sheets/`) land next to the scripts and are gitignored.

## Run order

| Step | Script | What it does | Needs |
| --- | --- | --- | --- |
| 1 | `profile.py` | Loads all commercial properties into `props.pkl`; prints field coverage for Houston non-apartment buildings | kit |
| 2 | `pilot.py` | Picks a stratified sample of 29 Houston buildings; adds CoStar tenancies and listings; fetches Vexcel `property/extract` and Matterport rooms/panos into `raw/` | kit, both APIs |
| 3 | `analyze.py` | Per-building table: CoStar size/stories/tenants vs. Vexcel structures vs. Matterport scans | step 2 |
| 4 | `pin.py` | **Size check, done right:** uses the Vexcel structure whose footprint contains the CoStar pin (parcels can hold several buildings) | step 2 |
| 5 | `refine.py`, `suites.py`, `suites2.py` | Available spaces per building, tenants by suite, alternate addresses | steps 1–2 |
| 6 | `attdates.py` | **Real scan date** = CoStar attachment `originationDate` (Matterport `created` is the re-hosting date) | kit |
| 7 | `hist.py` | Tenancy history by suite, to line up against scan dates (the time-aware occupancy check) | kit |
| 8 | `panos.py` → `sheet.py` | Downloads 360° faces for chosen scans and makes contact sheets for visual review | Matterport, Pillow |
| 9 | `ortho.py` | Annotated Vexcel aerial: parcel, every footprint with area, CoStar pin | Vexcel |
| 10 | `scale.py` | Kit-wide: scans whose caption names a different street number than the property | kit |

`api.py` is a tiny stdlib client (Vexcel GET/POST with 429 backoff; Matterport GraphQL with Basic auth).

## Checks worth porting into `playground/reconcile.py`

- **Size:** CoStar typical floor (or GBA ÷ stories) vs. the footprint of the Vexcel structure under the pin (`pin.py`). In the pilot, 16 of 29 were within ±20%. Towers often include a podium or garage in the footprint.
- **Time-aware occupancy:** for a suite-named scan, take its `originationDate` and find the CoStar tenancy covering that suite on that date (`attdates.py` + `hist.py`). Empty photo + active tenancy = conflict. Scan before move-in = consistent.
- Hard-coded property IDs in `suites2.py`, `hist.py`, `panos.py` and `ortho.py` are the pilot's cases (Suite 155 = property 237647, Grant Rd = 9292792).
