"""Run Perceptron Mk1 through the configured OpenRouter key on sample views."""
from datetime import datetime, timezone
import base64
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
SAMPLE = OUT / "matterport_sample" / "paup35hdhemsueprdyas7xtub"
MODEL = "perceptron/perceptron-mk1"
IMAGES = ["skybox_face_1.jpg", "skybox_face_2.jpg", "skybox_face_3.jpg"]
PROMPT = """Ground detections only in directly visible pixels in this Matterport indoor panorama face. Use the requested JSON schema exactly. Bounding boxes must use integer coordinates on a 0-to-1000 image grid in x1,y1,x2,y2 order. Look for rooftop HVAC, loading docks/access doors, parking, roof obstructions, interior doors, partitions, circulation obstacles, and visible sprinkler/electrical fixtures. Since this is an indoor view, use status not_in_view and null box for exterior-only classes. Do not infer engineering condition or code compliance. Be conservative: include only localized, directly visible objects."""
SCHEMA = {"type": "json_schema", "json_schema": {"name": "perceptron_mk1_detections", "strict": True,
          "schema": {"type": "object", "properties": {"detections": {"type": "array", "items": {
              "type": "object", "properties": {
                  "class": {"type": "string"}, "evidence": {"type": "string"},
                  "bbox_xyxy_1000": {"anyOf": [{"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 1000}, "minItems": 4, "maxItems": 4}, {"type": "null"}]},
                  "status": {"type": "string", "enum": ["visible", "uncertain", "not_in_view"]}},
              "required": ["class", "evidence", "bbox_xyxy_1000", "status"], "additionalProperties": False}}},
              "required": ["detections"], "additionalProperties": False}}}


def get_key():
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    for env_file in [ROOT.parents[1] / ".env", ROOT.parents[1] / "project helix" / ".env"]:
        if env_file.exists():
            for line in env_file.read_text(errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    value = line.split("=", 1)[1].strip().strip("\"'")
                    if value:
                        return value
    return None


def request_one(key, image):
    encoded = base64.b64encode(image.read_bytes()).decode("ascii")
    body = {"model": MODEL, "temperature": 0, "max_tokens": 750, "response_format": SCHEMA,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
            ]}]}
    req = Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                           "HTTP-Referer": "https://helix.local", "X-Title": "Helix isolated vision research"},
                  method="POST")
    start = time.perf_counter()
    try:
        with urlopen(req, timeout=150) as response:
            raw = json.loads(response.read())
            status = response.status
    except HTTPError as exc:
        try:
            error = json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception:
            error = "HTTP error body unavailable"
        return {"http_status": exc.code, "latency_ms": round((time.perf_counter()-start)*1000), "error": error}
    except (TimeoutError, URLError) as exc:
        return {"http_status": None, "latency_ms": round((time.perf_counter()-start)*1000), "error": str(exc)}
    choice = (raw.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return {"http_status": status, "response_model": raw.get("model"), "latency_ms": round((time.perf_counter()-start)*1000),
            "finish_reason": choice.get("finish_reason"), "usage": raw.get("usage"),
            "provider_reported_cost_usd": (raw.get("usage") or {}).get("cost"),
            "response_id": raw.get("id"), "content": message.get("content", "")}


def main():
    key = get_key()
    if not key:
        result = {"status": "blocked", "reason": "OPENROUTER_API_KEY absent; no requests made."}
    else:
        calls = []
        for filename in IMAGES:
            calls.append({"image": filename, "model": MODEL, "prompt": PROMPT,
                          "requested_at": datetime.now(timezone.utc).isoformat(),
                          "result": request_one(key, SAMPLE / filename)})
            r = calls[-1]["result"]
            print(json.dumps({"image": filename, "http_status": r.get("http_status"),
                              "latency_ms": r.get("latency_ms"), "usage": r.get("usage")}))
        result = {"status": "complete", "sample_property_costar_id": 236138,
                  "source_model_id": "NDMWnz1H9uV", "source_images": IMAGES,
                  "run_timestamp": datetime.now(timezone.utc).isoformat(), "calls": calls}
    (OUT / "perceptron_openrouter.json").write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n")
    if result.get("status") == "blocked":
        print(json.dumps(result))


if __name__ == "__main__":
    main()
