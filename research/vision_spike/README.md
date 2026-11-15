# Helix vision research spike

Isolated read-only experiments for Vexcel, Matterport, Perceptron Mk1, and image-capable VLMs. This directory is not imported by Helix. Generated source responses, imagery, and benchmark artifacts belong in the gitignored `output/` directory.

## Safety and provenance

- Credentials are read from `.env` and `project helix/.env`; values are never printed.
- Vexcel coverage/metadata and Matterport GraphQL queries are read-only. Do not call mutations, publish/share a model, or use paid/unlocked assets.
- Do not download Vexcel imagery until the credential's entitlement/cost is confirmed. Use only an already-entitled image or a clearly labeled official/demo sample.
- Preserve provider IDs, retrieval time, dimensions, CRS/coordinate metadata, model visibility/permission, and attribution in local `output/` records.
- `PERCEPTRON_API_KEY` is separate from the existing Vexcel/Matterport keys. Missing provider credentials must remain a blocker; SDK compile-only output is not a live result.
- Vision model APIs may incur token charges. The benchmark is deliberately small; actual usage and provider-reported cost are recorded for each call.

## Run

```sh
python3 research/vision_spike/provider_probe.py
python3 research/vision_spike/model_catalog.py
python3 research/vision_spike/acquire_matterport_sample.py
python3 research/vision_spike/perceptron_probe.py
python3 research/vision_spike/vlm_benchmark.py
python3 research/vision_spike/evaluate_results.py
```

The provider probes are read-only. `model_catalog.py` retrieves public model metadata. The VLM benchmark requires an existing OpenRouter key and makes a deliberately small number of billed image calls. Perceptron remains blocked until its own key is configured. Generated source imagery and raw provider responses stay in the gitignored output directory.

## Results

See [report.md](report.md) for the research findings and blockers. Structured, sanitized benchmark outputs are in [results.json](results.json). Source images and annotated overlays are local-only under `output/matterport_sample/`; they are not committed because they are third-party Matterport imagery.
