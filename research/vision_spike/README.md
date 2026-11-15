# Helix vision research spike

Isolated read-only experiments for Vexcel, Matterport, Perceptron Mk1, and image-capable VLMs. This directory is not imported by Helix. Generated source responses, imagery, and benchmark artifacts belong in the gitignored `output/` directory.

## Safety and provenance

- Credentials are read from `.env` and `project helix/.env`; values are never printed.
- Vexcel coverage/metadata and Matterport GraphQL queries are read-only. Do not call mutations, publish/share a model, or use paid/unlocked assets.
- The supplied Vexcel credential authorized the small read-only image sample in this spike. Do not expand extraction beyond the documented, low-volume sample without confirming permitted scope and any usage charges.
- Preserve provider IDs, retrieval time, dimensions, CRS/coordinate metadata, model visibility/permission, and attribution in local `output/` records.
- Perceptron Mk1 is available through the existing OpenRouter credential as `perceptron/perceptron-mk1`; this spike verifies the catalog route and makes actual image calls through it.
- Vision model APIs may incur token charges. The benchmark is deliberately small; actual usage and provider-reported cost are recorded for each call.

## Run

```sh
python3 research/vision_spike/provider_probe.py
python3 research/vision_spike/model_catalog.py
python3 research/vision_spike/acquire_matterport_sample.py
python3 research/vision_spike/acquire_vexcel_selected_sample.py
python3 research/vision_spike/vexcel_inventory_scan.py
python3 research/vision_spike/perceptron_probe.py
python3 research/vision_spike/perceptron_openrouter.py
python3 research/vision_spike/vlm_benchmark.py
python3 research/vision_spike/vlm_conditioned_benchmark.py
python3 research/vision_spike/evaluate_results.py
python3 research/vision_spike/evaluate_conditioned.py
```

Coverage scans are read-only; `acquire_vexcel_selected_sample.py` also retrieves one small ortho and four oblique views for the selected matched property. `vexcel_inventory_scan.py` samples 100 CoStar points per city and does not download imagery. `model_catalog.py` retrieves public model metadata. Perceptron Mk1 and the VLM comparisons use the existing OpenRouter key and make a deliberately small number of billed image calls. Generated source imagery and raw provider responses stay in the gitignored output directory.

## Results

See [report.md](report.md) for the research findings and blockers. Structured, sanitized benchmark outputs are in [results.json](results.json). Source images and annotated overlays are local-only under `output/matterport_sample/` and `output/vexcel_sample/`; third-party imagery is not committed.
