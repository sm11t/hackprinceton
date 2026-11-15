"""Bounded OpenRouter visual interpretation; never emits legal or engineering conclusions."""
from __future__ import annotations

import base64
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODEL = "qwen/qwen3.8-flash"  # Verified in the isolated research spike; one image / one call.
MAX_IMAGE_BYTES = 8 * 1024 * 1024
FORBIDDEN = re.compile(r"\b(compliant|code compliant|safe|structurally sound|electrical capacity|approved for|business fit)\b", re.I)
PROMPT = """Describe only directly visible building features in this single authorized image. Return JSON only: {\"observations\":[{\"feature\":string,\"evidence\":string,\"bbox_xyxy_normalized\":[number,number,number,number]|null,\"status\":\"visible\"|\"uncertain\"}]} . Look for doors/access doors, hallways/circulation, stairs, partitions, ceiling features, visible electrical panels/conduits, fixtures and obstructions. Do not infer hidden systems, structural condition, safety, code/legal compliance, or a business use. If evidence is insufficient, return no observation. Bboxes are normalized 0..1 in x1,y1,x2,y2 order."""


def validate_visual_observation(item, image_ref):
    if not isinstance(item, dict) or not image_ref or not image_ref.get("image_id"):
        return None
    feature, evidence = item.get("feature"), item.get("evidence")
    if not isinstance(feature, str) or not feature.strip() or not isinstance(evidence, str) or not evidence.strip():
        return None
    if FORBIDDEN.search(feature) or FORBIDDEN.search(evidence):
        return None
    box = item.get("bbox_xyxy_normalized")
    if box is not None:
        if (not isinstance(box, list) or len(box) != 4 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not 0 <= v <= 1 for v in box)
                or box[0] >= box[2] or box[1] >= box[3]):
            return None
    if item.get("status") not in ("visible", "uncertain"):
        return None
    return {"feature":feature.strip(),"evidence":evidence.strip(),"bbox_xyxy_normalized":box,
            "status":item["status"],"source":"visual_observation","image_id":image_ref["image_id"],
            "model_id":image_ref.get("model_id"),"location_id":image_ref.get("location_id"),
            "evidence_ref":image_ref.get("evidence_ref"),"captured_at":image_ref.get("captured_at"),
            "retrieved_at":image_ref.get("retrieved_at"),"interpretation":"visual description only; not a measurement or compliance finding"}


def analyze_one_image(image_bytes, content_type, image_ref, *, opener=urlopen):
    """One bounded image call; disabled unless explicitly enabled by server configuration."""
    key=os.environ.get("OPENROUTER_API_KEY")
    if os.environ.get("HELIX_STAGE2_VISION_ENABLED") != "1" or not key:
        return {"status":"not_run","reason":"Visual model calls are disabled; image evidence remains available for later review.","observations":[]}
    if not image_bytes or len(image_bytes)>MAX_IMAGE_BYTES or not content_type.startswith("image/"):
        return {"status":"unknown","reason":"Image is absent, too large or has an unsupported content type.","observations":[]}
    payload={"model":MODEL,"temperature":0,"max_tokens":450,"reasoning_effort":"none",
       "messages":[{"role":"user","content":[{"type":"text","text":PROMPT},{"type":"image_url","image_url":{"url":f"data:{content_type};base64,{base64.b64encode(image_bytes).decode()}"}}]}]}
    req=Request("https://openrouter.ai/api/v1/chat/completions",data=json.dumps(payload).encode(),
      headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","HTTP-Referer":"https://helix.local","X-Title":"Helix Stage 2"},method="POST")
    started=time.monotonic()
    try:
        with opener(req,timeout=45) as response: body=json.loads(response.read())
    except (HTTPError,URLError,TimeoutError,OSError,ValueError) as error:
        return {"status":"temporarily_unavailable","error":type(error).__name__,"latency_ms":round((time.monotonic()-started)*1000),"observations":[]}
    try:
        content=((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        parsed=json.loads(content)
        items=parsed.get("observations") or []
        out=[validated for item in items[:20] if (validated:=validate_visual_observation(item,image_ref))]
    except (ValueError,AttributeError,TypeError):
        return {"status":"unknown","reason":"Vision response did not match the required JSON evidence contract.","observations":[]}
    return {"status":"available","model":MODEL,"latency_ms":round((time.monotonic()-started)*1000),
            "usage":body.get("usage"),"observations":out}
