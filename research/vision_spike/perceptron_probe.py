"""Perceptron Mk1 dry-run gate; never claims live detections without credentials."""
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILES = [ROOT.parents[1] / ".env", ROOT.parents[1] / "project helix" / ".env"]
KEY = "PERCEPTRON_API_KEY"


def load_env_presence():
    found = {KEY: bool(os.environ.get(KEY))}
    for path in ENV_FILES:
        if not path.exists():
            continue
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if line.startswith(KEY + "="):
                found[KEY] = found[KEY] or bool(line.split("=", 1)[1].strip().strip("\"'"))
    return found


def main():
    state = {
        "provider": "Perceptron",
        "requested_model": "perceptron-mk1",
        "sdk_installed": importlib.util.find_spec("perceptron") is not None,
        "credential_present": load_env_presence()[KEY],
        "live_test_run": False,
        "status": "blocked",
        "reason": "Perceptron API key is absent; no detections were simulated.",
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
