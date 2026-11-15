"""Check whether the existing OpenRouter route exposes Perceptron Mk1."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILES = [ROOT.parents[1] / ".env", ROOT.parents[1] / "project helix" / ".env"]
KEY = "OPENROUTER_API_KEY"


def openrouter_key_present():
    found = bool(os.environ.get(KEY))
    for path in ENV_FILES:
        if not path.exists():
            continue
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if line.startswith(KEY + "="):
                found = found or bool(line.split("=", 1)[1].strip().strip("\"'"))
    return found


def main():
    catalog_file = ROOT / "output" / "model_catalog.json"
    catalog = json.loads(catalog_file.read_text()) if catalog_file.exists() else {}
    model = next((x for x in catalog.get("candidates", []) if x.get("id") == "perceptron/perceptron-mk1"), None)
    key_present = openrouter_key_present()
    state = {
        "provider": "Perceptron",
        "requested_model": "perceptron/perceptron-mk1",
        "route": "OpenRouter chat completions",
        "openrouter_key_present": key_present,
        "catalog_model_present": model is not None,
        "image_input_supported": "image" in ((model or {}).get("architecture") or {}).get("input_modalities", []),
        "catalog_only_probe": True,
        "live_calls_recorded_in": "output/perceptron_openrouter.json",
        "status": "ready_via_openrouter" if key_present and model else "blocked",
        "reason": "OpenRouter route and model catalog confirmed; use perceptron_openrouter.py for live detection calls." if key_present and model else "OpenRouter credential or exact model catalog entry missing.",
        "requested_categories": [
            "rooftop HVAC equipment", "loading docks and access doors", "parking areas",
            "roof obstructions", "interior doors", "partitions", "circulation obstacles",
            "visible sprinkler or electrical fixtures",
        ],
    }
    (ROOT / "output" / "perceptron_probe.json").write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
