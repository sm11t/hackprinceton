"""Evaluate Mk1 localizations and configuration B against the same tiny labels."""
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw
from evaluate_results import GT, category, iou, parse_observations, ROOT, OUT, SAMPLE


def detections_from_perceptron():
    source = json.loads((OUT / "perceptron_openrouter.json").read_text())
    pred_by_image, rows = {}, []
    for call in source.get("calls", []):
        result = call.get("result", {})
        try: data = json.loads(result.get("content") or "{}")
        except json.JSONDecodeError: data = {}
        dets=[]
        for item in data.get("detections", []):
            box=item.get("bbox_xyxy_1000")
            if item.get("status")!="visible" or not isinstance(box,list) or len(box)!=4: continue
            if not all(isinstance(v,(int,float)) and 0<=v<=1000 for v in box): continue
            norm=[v/1000 for v in box]
            dets.append({"feature":item.get("class",""),"evidence":item.get("evidence",""),
                         "category":category(item.get("class","")+" "+item.get("evidence","")),
                         "bbox_xyxy_normalized":norm})
        pred_by_image[call["image"]]=dets
        rows.append({"image":call["image"],"latency_ms":result.get("latency_ms"),"usage":result.get("usage"),
                     "provider_reported_cost_usd":result.get("provider_reported_cost_usd"),"detections":dets})
    return pred_by_image, rows


def score(preds, image):
    gt=[{"category":c,"bbox_xyxy_normalized":b} for c,b in GT.get(image,[])]
    used=set();tp=fp=0
    for pred in preds:
        options=[(iou(pred["bbox_xyxy_normalized"],g["bbox_xyxy_normalized"]),idx)
                 for idx,g in enumerate(gt) if g["category"]==pred["category"] and idx not in used]
        best=max(options,default=(0,-1))
        if best[0]>=.5: tp+=1;used.add(best[1])
        else: fp+=1
    fn=len(gt)-len(used)
    return {"tp":tp,"fp":fp,"fn":fn,"precision":tp/(tp+fp) if tp+fp else None,
            "recall":tp/(tp+fn) if tp+fn else None}


def draw_overlay(image, preds, filename):
    im=Image.open(SAMPLE/image).convert("RGB");d=ImageDraw.Draw(im);w,h=im.size
    for p in preds:
        x1,y1,x2,y2=p["bbox_xyxy_normalized"]
        b=(round(x1*w),round(y1*h),round(x2*w),round(y2*h))
        d.rectangle(b,outline=(255,58,36),width=4)
        d.text((b[0],max(0,b[1]-14)),p["feature"][:45],fill=(255,255,0),stroke_width=1,stroke_fill=(0,0,0))
    im.save(SAMPLE/filename,quality=92)


def main():
    p_by_image,p_rows=detections_from_perceptron()
    for row in p_rows:
        row["manual_box_match_iou_0_5"]=score(p_by_image.get(row["image"],[]),row["image"])
        row["overlay"]="overlay_perceptron-mk1_"+row["image"].replace(".jpg","")+".jpg"
        draw_overlay(row["image"],p_by_image.get(row["image"],[]),row["overlay"])
    total_p={k:sum(r["manual_box_match_iou_0_5"][k] for r in p_rows) for k in ["tp","fp","fn"]}
    total_p["precision"]=total_p["tp"]/(total_p["tp"]+total_p["fp"]) if total_p["tp"]+total_p["fp"] else None
    total_p["recall"]=total_p["tp"]/(total_p["tp"]+total_p["fn"]) if total_p["tp"]+total_p["fn"] else None
    conditioned=json.loads((OUT/"vlm_conditioned_benchmark.json").read_text())
    b_rows=[]
    for rec in conditioned.get("configuration_b",[]):
        result=rec.get("result",{});obs=parse_observations(result.get("content"))
        preds=[]
        for ob in obs:
            box=ob.get("bbox_xyxy_normalized")
            if ob.get("status")!="visible" or not isinstance(box,list) or len(box)!=4:continue
            if not all(isinstance(v,(int,float)) and v>=0 for v in box):continue
            if max(box)>1: box=[v/1000 for v in box]
            if not all(0<=v<=1 for v in box):continue
            preds.append({"feature":ob.get("feature",""),"evidence":ob.get("evidence",""),
                          "category":category(ob.get("feature","")+" "+ob.get("evidence","")),
                          "bbox_xyxy_normalized":box})
        metric=score(preds,rec["image"])
        slug=rec["model"].split("/")[-1]
        overlay=f"overlay_conditioned_{slug}_{rec['image'].replace('.jpg','')}.jpg"
        draw_overlay(rec["image"],preds,overlay)
        b_rows.append({"image":rec["image"],"model":rec["model"],"http_status":result.get("http_status"),
                       "latency_ms":result.get("latency_ms"),"usage":result.get("usage"),
                       "provider_reported_cost_usd":result.get("provider_reported_cost_usd"),
                       "finish_reason":result.get("finish_reason"),"json_observations_parsed":len(obs),
                       "visible_valid_boxes":len(preds),"manual_box_match_iou_0_5":metric,
                       "overlay":overlay,"observations":obs})
    b_summary={}
    for model in sorted({r["model"] for r in b_rows}):
        rs=[r for r in b_rows if r["model"]==model]
        tp=sum(r["manual_box_match_iou_0_5"]["tp"] for r in rs)
        fp=sum(r["manual_box_match_iou_0_5"]["fp"] for r in rs)
        fn=sum(r["manual_box_match_iou_0_5"]["fn"] for r in rs)
        costs=[r["provider_reported_cost_usd"] for r in rs if isinstance(r["provider_reported_cost_usd"],(float,int))]
        b_summary[model]={"calls":len(rs),"mean_latency_ms":round(sum(r["latency_ms"] for r in rs)/len(rs)),
            "total_cost_usd_reported":sum(costs),"mean_cost_usd":sum(costs)/len(costs) if costs else None,
            "manual_box_match_iou_0_5":{"tp":tp,"fp":fp,"fn":fn,
            "precision":tp/(tp+fp) if tp+fp else None,"recall":tp/(tp+fn) if tp+fn else None}}
    output={"method":"Same reviewer labels/classes and greedy per-image IoU>=0.50 matching as raw-image evaluation; exploratory only.",
            "perceptron_model":"perceptron/perceptron-mk1","perceptron_calls":p_rows,
            "perceptron_summary":{"calls":len(p_rows),"mean_latency_ms":round(sum(r["latency_ms"] for r in p_rows)/len(p_rows)),
                "total_cost_usd_reported":sum(r["provider_reported_cost_usd"] for r in p_rows),"manual_box_match_iou_0_5":total_p},
            "configuration_b_results":b_rows,"configuration_b_summary":b_summary,
            "limitations":["Single property and three selected views, one approximate reviewer; not reliable general accuracy.",
                "Greedy same-category IoU>=0.50; large or differently grouped boxes can score poorly despite object presence.",
                "No engineering-condition or code-compliance inference."]}
    (OUT/"conditioned_evaluation.json").write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n")
    final=json.loads((ROOT/"results.json").read_text())
    final["perceptron_mk1"]=output["perceptron_summary"]
    final["perceptron_mk1_detections"]=output["perceptron_calls"]
    final["configuration_b_summary"]=b_summary
    final["configuration_b_results"]=b_rows
    (ROOT/"results.json").write_text(json.dumps(final,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"perceptron":output["perceptron_summary"],"configuration_b":b_summary},indent=2))


if __name__=="__main__":main()
