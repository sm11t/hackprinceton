"""Parse outputs, draw per-call boxes, and score against small manual annotations."""
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
SAMPLE = OUT / "matterport_sample" / "paup35hdhemsueprdyas7xtub"
GT = {
    "skybox_face_1.jpg": [
        ("door", [0.315, 0.322, 0.462, 0.699]),
        ("door", [0.523, 0.333, 0.741, 0.682]),
        ("electrical", [0.833, 0.459, 0.912, 0.556]),
        ("light", [0.900, 0.040, 0.995, 0.140]),
    ],
    "skybox_face_2.jpg": [
        ("door", [0.380, 0.456, 0.510, 0.612]),
        ("partition", [0.375, 0.350, 0.800, 0.600]),
        ("circulation", [0.300, 0.390, 0.380, 0.610]),
        ("electrical", [0.010, 0.460, 0.060, 0.540]),
        ("light", [0.000, 0.060, 0.340, 0.150]),
        ("light", [0.390, 0.110, 0.750, 0.220]),
        ("light", [0.390, 0.280, 0.680, 0.330]),
    ],
    "skybox_face_3.jpg": [
        ("door", [0.690, 0.395, 0.775, 0.635]),
        ("door", [0.760, 0.350, 0.980, 0.700]),
        ("electrical", [0.240, 0.600, 0.650, 0.635]),
        ("light", [0.040, 0.040, 0.420, 0.170]),
        ("light", [0.880, 0.050, 1.000, 0.145]),
    ],
}


def parse_observations(content):
    if not content:
        return []
    match = re.search(r"\{\s*\"observations\"\s*:.*\}", content, re.S)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
        return data.get("observations", [])
    except json.JSONDecodeError:
        return []


def category(feature):
    s = feature.lower()
    if any(x in s for x in ("door", "doorway", "access opening")):
        return "door"
    if any(x in s for x in ("partition", "mezzanine")):
        return "partition"
    if any(x in s for x in ("stair", "circulation obstruction")):
        return "circulation"
    if "sprinkler" in s:
        return "sprinkler"
    if any(x in s for x in ("light fixture", "fluorescent light", "ceiling light")):
        return "light"
    if any(x in s for x in ("electrical panel", "electrical fixture", "outlet", "conduit")):
        return "electrical"
    return "other"


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2-x1) * max(0, y2-y1)
    area_a = max(0, a[2]-a[0]) * max(0, a[3]-a[1])
    area_b = max(0, b[2]-b[0]) * max(0, b[3]-b[1])
    return inter / (area_a + area_b - inter) if area_a + area_b > inter else 0


def main():
    run = json.loads((OUT / "vlm_benchmark.json").read_text())
    flat = []
    for rec in run.get("configuration_a", []):
        result = rec.get("result", {})
        observations = parse_observations(result.get("content"))
        preds = []
        for ob in observations:
            box = ob.get("bbox_xyxy_normalized")
            if ob.get("status") != "visible" or not isinstance(box, list) or len(box) != 4:
                continue
            # Both model outputs must comply with normalized [0,1] coordinates.
            if not all(isinstance(v, (float, int)) and 0 <= v <= 1 for v in box):
                continue
            preds.append({"feature": ob.get("feature", ""), "category": category(ob.get("feature", "")),
                          "bbox_xyxy_normalized": box, "evidence": ob.get("evidence", "")})
        gt = [{"category": c, "bbox_xyxy_normalized": b} for c, b in GT.get(rec["image"], [])]
        used = set()
        tp = fp = 0
        for pred in preds:
            candidates = [(iou(pred["bbox_xyxy_normalized"], item["bbox_xyxy_normalized"]), idx)
                          for idx, item in enumerate(gt) if item["category"] == pred["category"] and idx not in used]
            best = max(candidates, default=(0, -1))
            if best[0] >= 0.5:
                tp += 1
                used.add(best[1])
            else:
                fp += 1
        fn = len(gt) - len(used)
        # Render original image and each valid model box.
        im = Image.open(SAMPLE / rec["image"]).convert("RGB")
        draw = ImageDraw.Draw(im)
        w, h = im.size
        for pred in preds:
            x1, y1, x2, y2 = pred["bbox_xyxy_normalized"]
            box = (round(x1*w), round(y1*h), round(x2*w), round(y2*h))
            draw.rectangle(box, outline=(255, 58, 36), width=4)
            label = pred["feature"][:45]
            draw.text((box[0], max(0, box[1]-14)), label, fill=(255, 255, 0), stroke_width=1, stroke_fill=(0,0,0))
        slug = rec["model"].split("/")[-1]
        dest = SAMPLE / f"overlay_{slug}_{rec['image'].replace('.jpg','')}.jpg"
        im.save(dest, quality=92)
        manual = Image.open(SAMPLE / rec["image"]).convert("RGB")
        md = ImageDraw.Draw(manual)
        for cls, box in GT.get(rec["image"], []):
            x1, y1, x2, y2 = box
            coords = (round(x1*w), round(y1*h), round(x2*w), round(y2*h))
            md.rectangle(coords, outline=(42, 110, 255), width=4)
            md.text((coords[0], max(0, coords[1]-14)), cls, fill=(255,255,0), stroke_width=1, stroke_fill=(0,0,0))
        manual.save(SAMPLE / f"manual_annotated_{rec['image']}", quality=92)
        flat.append({"image": rec["image"], "model": rec["model"], "http_status": result.get("http_status"),
                     "latency_ms": result.get("latency_ms"), "usage": result.get("usage"),
                     "provider_reported_cost_usd": result.get("provider_reported_cost_usd"),
                     "finish_reason": result.get("finish_reason"), "json_observations_parsed": len(observations),
                     "visible_valid_boxes": len(preds), "manual_box_match_iou_0_5": {"tp":tp,"fp":fp,"fn":fn,
                     "precision": tp/(tp+fp) if tp+fp else None,
                     "recall": tp/(tp+fn) if tp+fn else None}, "overlay": dest.name,
                     "observations": observations})
    summary = {}
    for model in sorted({x["model"] for x in flat}):
        rows = [x for x in flat if x["model"] == model]
        tp = sum(x["manual_box_match_iou_0_5"]["tp"] for x in rows)
        fp = sum(x["manual_box_match_iou_0_5"]["fp"] for x in rows)
        fn = sum(x["manual_box_match_iou_0_5"]["fn"] for x in rows)
        costs = [x["provider_reported_cost_usd"] for x in rows if isinstance(x["provider_reported_cost_usd"], (float, int))]
        summary[model] = {"calls":len(rows), "mean_latency_ms":round(sum(x["latency_ms"] for x in rows)/len(rows)),
                          "total_cost_usd_reported":sum(costs), "mean_cost_usd":sum(costs)/len(costs) if costs else None,
                          "manual_box_match_iou_0_5":{"tp":tp,"fp":fp,"fn":fn,
                          "precision":tp/(tp+fp) if tp+fp else None,"recall":tp/(tp+fn) if tp+fn else None}}
    output = {"sample":"3 indoor panorama faces, 1024x1024 each, one CoStar-matched Matterport model",
              "method_limitations":["Single reviewer approximate boxes; exploratory, not statistically reliable.",
                 "Per-face greedy same-class IoU>=0.50 matching; no adjudication or confidence calibration.",
                 "Classes outside the visible manual labels are counted as false positives.",
                 "Panorama face views are not independent properties; no exterior imagery was available."],
              "manual_labels":GT,"configuration_a_results":flat,"per_model_summary":summary,
              "configuration_b":{"status":"not_run","reason":"No Perceptron credential; no fabricated localizations."}}
    (OUT / "evaluated_results.json").write_text(json.dumps(output, indent=2, ensure_ascii=False)+"\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
