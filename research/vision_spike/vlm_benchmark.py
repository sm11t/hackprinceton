"""Tiny same-prompt image benchmark over already-authorized Matterport images."""
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
MODELS = ["deepseek/deepseek-v4.1-flash-1017", "qwen/qwen3.8-flash"]
PROMPT = """Inspect this single Matterport indoor panorama face. Return JSON only with this schema: {\"observations\":[{\"feature\":string,\"evidence\":string,\"bbox_xyxy_normalized\":[number,number,number,number]|null,\"status\":\"visible\"|\"not_visible\"|\"uncertain\"}]} . bbox coordinates MUST be floating point values from 0.0 to 1.0, normalized by image width and height, in x1,y1,x2,y2 order. Assess visible doors/access doors, partitions, circulation obstructions, sprinkler fixtures, and electrical fixtures. Do not infer engineering condition, code compliance, unseen areas, or business suitability. Be conservative: report only directly visible evidence; use null bbox if localization is uncertain."""
IMAGES = ["skybox_face_1.jpg", "skybox_face_2.jpg", "skybox_face_3.jpg"]
CATALOG = json.loads((OUT / "model_catalog.json").read_text())


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


def catalog_price(model_id):
    item = next((x for x in CATALOG.get("candidates", []) if x.get("id") == model_id), {})
    price = item.get("pricing") or {}
    return float(price.get("prompt", 0)), float(price.get("completion", 0))


def one_call(key, model_id, image_path):
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    body = {"model": model_id, "temperature": 0, "max_tokens": 700,
            "reasoning_effort": "none",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
            ]}]}
    request = Request("https://openrouter.ai/api/v1/chat/completions",
                      data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}",
                      "Content-Type": "application/json", "HTTP-Referer": "https://helix.local",
                      "X-Title": "Helix isolated vision research"}, method="POST")
    start = time.perf_counter()
    try:
        with urlopen(request, timeout=120) as response:
            raw = json.loads(response.read())
            status = response.status
    except HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(payload)
        except Exception:
            detail = payload[:1000]
        return {"http_status": exc.code, "latency_ms": round((time.perf_counter() - start) * 1000),
                "error": detail}
    except (TimeoutError, URLError) as exc:
        return {"http_status": None, "latency_ms": round((time.perf_counter() - start) * 1000),
                "error": str(exc)}
    latency_ms = round((time.perf_counter() - start) * 1000)
    choice = (raw.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content", "")
    if content is None:
        content = ""
    usage = raw.get("usage") or {}
    prompt_price, completion_price = catalog_price(model_id)
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    estimated = None
    if prompt_tokens is not None and completion_tokens is not None:
        estimated = prompt_tokens * prompt_price + completion_tokens * completion_price
    return {"http_status": status, "response_model": raw.get("model"), "latency_ms": latency_ms,
            "finish_reason": choice.get("finish_reason"), "usage": usage,
            "catalog_price_per_token": {"prompt": prompt_price, "completion": completion_price},
            "estimated_cost_usd_from_token_usage": estimated,
            "provider_reported_cost_usd": usage.get("cost"), "content": content,
            "response_id": raw.get("id")}


def main():
    key = get_key()
    if not key:
        result = {"status": "blocked", "reason": "OPENROUTER_API_KEY absent; no model calls made."}
        (OUT / "vlm_benchmark.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return
    records = []
    for filename in IMAGES:
        image_path = SAMPLE / filename
        for model_id in MODELS:
            record = {"image": filename, "model": model_id, "configuration": "A_raw_image_to_VLM",
                      "prompt_sha256": __import__("hashlib").sha256(PROMPT.encode()).hexdigest(),
                      "requested_at": datetime.now(timezone.utc).isoformat(),
                      "result": one_call(key, model_id, image_path)}
            records.append(record)
            print(json.dumps({"image": filename, "model": model_id,
                              "http_status": record["result"].get("http_status"),
                              "latency_ms": record["result"].get("latency_ms"),
                              "usage": record["result"].get("usage")}, ensure_ascii=False))
    result = {"status": "complete", "sample": "authorized public Matterport model matching CoStar property 236138",
              "prompt": PROMPT, "configuration_a": records,
              "configuration_b": {"status": "not_run", "reason": "Perceptron Mk1 API key unavailable; no fabricated detections."},
              "run_timestamp": datetime.now(timezone.utc).isoformat()}
    (OUT / "vlm_benchmark.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
