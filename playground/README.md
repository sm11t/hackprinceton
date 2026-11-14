# Sponsor data playground

Run from the repo root with Python 3.10 or later. Put the sponsor-issued values
in a local `.env` using `.env.example` as a template. Keep the original
`costar-hackathon-kit.zip` outside the repo.

```sh
set -a
source .env
set +a
python3 playground/probe.py --kit ~/Downloads/costar-hackathon-kit.zip
```

The default is Houston property 23296. Use `--property-id` to try another
property from the kit's `commercial-properties.csv` and `--model-id` to pick
a specific linked scan. `--costar-only` tests the local join without API calls.

The output directory contains an evidence JSON and, when Vexcel succeeds, an
aerial JPEG centered on the CoStar coordinates. The Matterport query returns
floors, room labels, classifiers, and dimension estimates in metric units.
Compare the scan in the sponsor's browser playground using the model ID in the
report. A property can have several scans, and each scan may cover only part of
the building. The aerial is a fixed-area crop, so it can include neighboring
parcels.

A provider failure is recorded in the JSON and causes a nonzero exit status.
Credentials and generated outputs are ignored by Git. Sponsor data access is
limited to the hackathon.

- [Sponsor quickstart](https://beta-app.matterport.com/2026-princeton-hackathon/quickstart)
- [Matterport Model Playground](https://beta-app.matterport.com/2026-princeton-hackathon/graphiql)
- [Matterport API](https://developers.matterport.com/api/)

## Browser view

Load the same environment as above, then run:

```sh
python3 playground/web.py --kit ~/Downloads/costar-hackathon-kit.zip
```

Open [localhost:8765](http://127.0.0.1:8765). Search the Houston addresses
in the kit by street number or words in the street name.
