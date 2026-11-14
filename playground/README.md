# Houston property playground

Search Houston addresses in the CoStar sponsor kit and inspect their property
records, Vexcel aerial imagery, and linked Matterport scans. The playground
uses Python 3.10+ and the standard library.

## Setup

1. Check out the playground branch. From a fresh checkout:

   ```sh
   git clone --branch feature/playground https://github.com/sm11t/hackprinceton.git
   cd hackprinceton
   ```

   If you already have the repo, run `git fetch origin` and
   `git switch feature/playground` from its root.

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
