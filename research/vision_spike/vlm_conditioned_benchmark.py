"""Run configuration B: same image/prompt plus Perceptron Mk1 detections."""
from datetime import datetime, timezone
import base64
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from vlm_benchmark import MODELS, PROMPT, SAMPLE, get_key

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
PERCEPTRON_PATH = OUT / "perceptron_openrouter.json"


def get_detections():
    data = json.loads(PERCEPTRON_PATH.read_text())
    records = {}
    for call in data.get("calls", []):
        content = call.get("result", {}).get("content") or ""
        try:
            detections = json.loads(content).get("detections", [])
        except json.JSONDecodeError:
            detections = []
        normalized = []
        for item in detections:
            box = item.get("bbox_xyxy_1000")
            if isinstance(box, list) and len(box) == 4 and all(isinstance(v, int) and 0 <= v <= 1000 for v in box):
                normalized.append({"class": item.get("class"), "evidence": item.get("evidence"),
                                   "bbox_xyxy_1000": box, "status": item.get("status")})
        records[call["image"]] = normalized
    return records


def call(key, model_id, filename, detections):
    encoded = base64.b64encode((SAMPLE / filename).read_bytes()).decode("ascii")
    conditioned_text = "Perceptron Mk1 localization candidates for this same image (bbox coordinates on 0-1000 grid):\n" + json.dumps(detections, ensure_ascii=False)
    body = {"model": model_id, "temperature": 0, "max_tokens": 700, "reasoning_effort": "none",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "text", "text": conditioned_text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
            ]}]}
    req = Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                           "HTTP-Referer": "https://helix.local", "X-Title": "Helix isolated vision research"}, method="POST")
    start = time.perf_counter()
    try:
        with urlopen(req, timeout=150) as response:
            raw = json.loads(response.read())
            status = response.status
    except HTTPError as exc:
        try: error = json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception: error = "HTTP error body unavailable"
        return {"http_status": exc.code, "latency_ms": round((time.perf_counter()-start)*1000), "error": error}
    except (TimeoutError, URLError) as exc:
        return {"http_status": None, "latency_ms": round((time.perf_counter()-start)*1000), "error": str(exc)}
    choice = (raw.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    usage = raw.get("usage") or {}
    return {"http_status": status, "response_model": raw.get("model"),
            "latency_ms": round((time.perf_counter()-start)*1000), "finish_reason": choice.get("finish_reason"),
            "usage": usage, "provider_reported_cost_usd": usage.get("cost"),
            "response_id": raw.get("id"), "content": message.get("content", "")}


def main():
    key = get_key()
    if not key:
        result = {"status": "blocked", "reason": "OPENROUTER_API_KEY absent; no calls made."}
    else:
        detections = get_detections()
        records = []
        for filename in ["skybox_face_1.jpg", "skybox_face_2.jpg", "skybox_face_3.jpg"]:
            for model_id in MODELS:
                result_one = call(key, model_id, filename, detections.get(filename, []))
                record = {"image": filename, "model": model_id, "configuration": "B_raw_image_plus_perceptron_mk1_localizations_to_vlm",
                          "perceptron_model": "perceptron/perceptron-mk1", "perceptron_detection_count": len(detections.get(filename, [])),
                          "base_prompt_sha256": __import__("hashlib").sha256(PROMPT.encode()).hexdigest(),
                          "requested_at": datetime.now(timezone.utc).isoformat(), "result": result_one}
                records.append(record)
                print(json.dumps({"image": filename, "model": model_id, "http_status": result_one.get("http_status"),
                                  "latency_ms": result_one.get("latency_ms"), "usage": result_one.get("usage")}))
        result = {"status": "complete", "configuration": "B_raw_image_plus_perceptron_mk1_localizations_to_vlm",
                  "source_model_id": "NDMWnz1H9uV", "sample_property_costar_id": 236138,
                  "run_timestamp": datetime.now(timezone.utc).isoformat(), "configuration_b": records}
    (OUT / "vlm_conditioned_benchmark.json").write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n")


if __name__ == "__main__":
    main()
