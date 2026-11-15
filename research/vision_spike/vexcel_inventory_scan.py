"""Sample Vexcel coverage at CoStar Houston/LA property coordinates (metadata only)."""
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
DATA_PATH = OUT / "costar_city_candidates.json"
URL = "https://api.vexcelgroup.com/v2/"
SAMPLE_PER_CITY = 100
SEED = 20261115


def get_key():
    if os.environ.get("VEXCEL_API_KEY"):
        return os.environ["VEXCEL_API_KEY"]
    for path in (ROOT.parents[1] / ".env", ROOT.parents[1] / "project helix" / ".env"):
        if path.exists():
            for line in path.read_text(errors="ignore").splitlines():
                line=line.strip()
                if line.startswith("VEXCEL_API_KEY="):
                    value=line.split("=",1)[1].strip().strip("\"'")
                    if value: return value
    return None


def request_json(key, path, params):
    last=None
    for attempt in range(6):
        req=Request(URL+path+"?"+urlencode(params),headers={"X-API-KEY":key,"Accept":"application/json"})
        started=time.monotonic()
        try:
            with urlopen(req,timeout=90) as response:
                status=response.status;body=response.read()
            latency=round(time.monotonic()-started,3)
        except HTTPError as exc:
            status=exc.code;body=exc.read();latency=round(time.monotonic()-started,3)
        except (URLError,TimeoutError,OSError) as exc:
            status=0;body=json.dumps({"error_type":type(exc).__name__}).encode();latency=round(time.monotonic()-started,3)
        if status!=429 or attempt==5:
            try: parsed=json.loads(body)
            except (UnicodeDecodeError,json.JSONDecodeError): parsed={"response_type":"non_json"}
            return {"status":status,"latency_s":latency,"body":parsed}
        time.sleep(min(2**attempt,30))
        last={"status":status,"latency_s":latency,"body":{"error":"rate_limit"}}
    return last


def summary(response, key):
    body=response.get("body") or {}
    features=body.get("features",[]) if isinstance(body,dict) else []
    records=[]
    for feature in features:
        p=feature.get("properties") or {}
        records.append({k:p.get(k) for k in key if p.get(k) is not None})
    return {"status":response.get("status"),"feature_count":len(features),"records":records}


def main():
    key=get_key()
    if not key: raise SystemExit("VEXCEL_API_KEY missing; no requests made.")
    candidates=json.loads(DATA_PATH.read_text())["rows"]
    rng=random.Random(SEED)
    selected={}
    for city,state in (("Houston","TX"),("Los Angeles","CA")):
        group=[r for r in candidates if r["city"].casefold()==city.casefold() and r["state"].casefold()==state.casefold()]
        if len(group)<SAMPLE_PER_CITY: raise SystemExit(f"Insufficient coordinate records for {city}.")
        selected[f"{city}, {state}"]=rng.sample(group,SAMPLE_PER_CITY)
    rows=[]
    for city_key,group in selected.items():
        city,state=city_key.split(", ")
        for index,row in enumerate(group,1):
            point=f"POINT({row['longitude']} {row['latitude']})"
            common={"wkt":point,"srid":"4326"}
            oriented=request_json(key,"oriented/collections",{**common,"layer":"urban","product-type":"oblique",
                         "include":"product-type,collection,last-capture-date"})
            time.sleep(0.1)
            ortho=request_json(key,"ortho/collections",{**common,"layer":"urban,urban-r,wide-area,urban-g",
                         "include":"collection,last-capture-date"})
            oriented_summary=summary(oriented,["product-type","collection","last-capture-date"])
            ortho_summary=summary(ortho,["collection","last-capture-date"])
            oblique=oriented_summary["status"]==200 and oriented_summary["feature_count"]>0
            nadir=ortho_summary["status"]==200 and ortho_summary["feature_count"]>0
            rows.append({"property_id":row["property_id"],"city":city,"state":state,
                         "latitude":row["latitude"],"longitude":row["longitude"],
                         "matterport_model_count":row["matterport_model_count"],
                         "oriented_coverage":oriented_summary,"ortho_coverage":ortho_summary,
                         "coverage_class":"both" if oblique and nadir else "oblique_only" if oblique else "ortho_only" if nadir else "neither",
                         "sample_order":index})
            if oriented.get("status")==401 or ortho.get("status")==401:
                raise SystemExit("Vexcel returned 401 during scan; stopped early. Credentials are not shown.")
            if oriented.get("status") not in (200,404) or ortho.get("status") not in (200,404):
                print(f"{city_key}: inspected {index}/{SAMPLE_PER_CITY} points (one non-coverage response; see output).")
    result={"source":"local CoStar Hackathon Kit commercial property records",
      "retrieved_at":datetime.now(timezone.utc).isoformat(),"sample_method":"simple random sample without replacement from coordinate-bearing properties in each city",
      "sample_per_city":SAMPLE_PER_CITY,"random_seed":SEED,"endpoints":["oriented/collections","ortho/collections"],
      "auth_method":"X-API-KEY header; secret excluded","imagery_extracted":False,"properties":rows}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"vexcel_inventory_sample.json").write_text(json.dumps(result,indent=2)+"\n")
    report={}
    for city_key in selected:
        group=[r for r in rows if f"{r['city']}, {r['state']}"==city_key]
        counts=Counter(r["coverage_class"] for r in group)
        linked=[r for r in group if r["matterport_model_count"]>0]
        linked_counts=Counter(r["coverage_class"] for r in linked)
        report[city_key]={"coordinate_bearing_universe":sum(1 for r in candidates
                              if r["city"].strip().casefold()==city.casefold() and r["state"].strip().casefold()==state.casefold()),
                          "sampled":len(group),"coverage_counts":dict(counts),
                          "any_vexcel_coverage":sum(v for k,v in counts.items() if k!="neither"),
                          "matterport_linked_in_sample":len(linked),"matterport_linked_coverage_counts":dict(linked_counts)}
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
