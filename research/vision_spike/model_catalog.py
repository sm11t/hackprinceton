"""Fetch current public OpenRouter catalog metadata for image-capable candidates."""
import json
from pathlib import Path
from urllib.request import Request, urlopen

OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(parents=True, exist_ok=True)
URL = "https://openrouter.ai/api/v1/models"
NEEDLES = ("deepseek/deepseek-v4.1-flash", "qwen/qwen3.8-flash", "perceptron/perceptron-mk1")


def main():
    req = Request(URL, headers={"Accept": "application/json", "User-Agent": "Helix research spike"})
    with urlopen(req, timeout=45) as response:
        catalog = json.load(response)
    chosen = []
    for item in catalog.get("data", []):
        model_id = item.get("id", "")
        if any(model_id == n or model_id.startswith(n + "-") for n in NEEDLES):
            chosen.append({"id": model_id, "name": item.get("name"), "description": item.get("description"),
                           "created": item.get("created"), "architecture": item.get("architecture"),
                           "pricing": item.get("pricing"), "context_length": item.get("context_length"),
                           "supported_parameters": item.get("supported_parameters")})
    result = {"source": URL, "catalog_retrieved": True, "candidates": chosen}
    (OUT / "model_catalog.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
