"""Read-only Vexcel coverage + small ortho/oblique sample at the matched site."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT / "output"
SAMPLE = OUT / "vexcel_sample" / "costar-236138"
LAT, LON = 29.944369, -95.385271
POINT_WKT = f"POINT({LON} {LAT})"
LAYERS = "urban,urban-r,wide-area,urban-g"
BASE = "https://api.vexcelgroup.com/v2/"


def load_key():
    if os.environ.get("VEXCEL_API_KEY"):
        return os.environ["VEXCEL_API_KEY"]
    for path in (REPO / ".env", REPO / "project helix" / ".env"):
        if path.exists():
            for line in path.read_text(errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("VEXCEL_API_KEY="):
                    value = line.split("=", 1)[1].strip().strip("\"'")
                    if value:
                        return value
    return None


def get_json(key, path, params):
    req = Request(BASE + path + "?" + urlencode(params),
                  headers={"X-API-KEY": key, "Accept": "application/json"})
    start = time.monotonic()
    try:
        with urlopen(req, timeout=120) as response:
            status, content_type, data = response.status, response.headers.get("Content-Type", ""), response.read()
    except HTTPError as exc:
        status, content_type, data = exc.code, exc.headers.get("Content-Type", ""), exc.read()
    except (URLError, TimeoutError, OSError) as exc:
        return {"status": 0, "error_type": type(exc).__name__, "latency_s": round(time.monotonic()-start, 3)}
    try:
        body = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = data.decode("utf-8", "replace")[:1000]
    return {"status": status, "content_type": content_type, "latency_s": round(time.monotonic()-start, 3), "body": body}


def post_image(key, endpoint, body, filename):
    req = Request(BASE + endpoint, data=json.dumps(body).encode(),
                  headers={"X-API-KEY": key, "Accept": "image/jpeg,image/png,application/json", "Content-Type": "application/json"},
                  method="POST")
    start = time.monotonic()
    try:
        with urlopen(req, timeout=240) as response:
            status, ctype, payload = response.status, response.headers.get("Content-Type", ""), response.read()
    except HTTPError as exc:
        payload = exc.read()
        try: detail = json.loads(payload)
        except Exception: detail = payload.decode("utf-8", "replace")[:1200]
        return {"status": exc.code, "content_type": exc.headers.get("Content-Type", ""),
                "latency_s": round(time.monotonic()-start, 3), "error": detail}
    except (URLError, TimeoutError, OSError) as exc:
        return {"status": 0, "latency_s": round(time.monotonic()-start, 3), "error_type": type(exc).__name__}
    if not ctype.lower().startswith("image/"):
        try: detail = json.loads(payload)
        except Exception: detail = payload.decode("utf-8", "replace")[:1200]
        return {"status": status, "content_type": ctype, "latency_s": round(time.monotonic()-start, 3), "error": detail}
    SAMPLE.mkdir(parents=True, exist_ok=True)
    path = SAMPLE / filename
    path.write_bytes(payload)
    with Image.open(path) as im:
        width, height = im.size
        fmt = im.format
        im.verify()
    return {"status": status, "content_type": ctype, "latency_s": round(time.monotonic()-start, 3),
            "filename": filename, "width_px": width, "height_px": height, "format": fmt,
            "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def geo_to_wkt(geometry):
    kind, coords = geometry["type"], geometry["coordinates"]
    def ring(r): return "(" + ",".join(f"{x} {y}" for x,y in r) + ")"
    if kind == "Polygon":
        return "POLYGON(" + ",".join(ring(r) for r in coords) + ")"
    if kind == "MultiPolygon":
        return "MULTIPOLYGON(" + ",".join("(" + ",".join(ring(r) for r in poly) + ")" for poly in coords) + ")"
    raise ValueError(f"Unsupported parcel geometry: {kind}")


def point_in_ring(lon, lat, ring):
    inside = False
    for i in range(len(ring)-1):
        x1,y1=ring[i];x2,y2=ring[i+1]
        if ((y1>lat)!=(y2>lat)) and lon < (x2-x1)*(lat-y1)/(y2-y1+1e-30)+x1:
            inside=not inside
    return inside


def point_in_geometry(lon, lat, geometry):
    if not geometry: return False
    kind, coords=geometry.get("type"),geometry.get("coordinates")
    polys=[coords] if kind=="Polygon" else coords if kind=="MultiPolygon" else []
    for poly in polys:
        if poly and point_in_ring(lon,lat,poly[0]) and not any(point_in_ring(lon,lat,h) for h in poly[1:]):
            return True
    return False


def main():
    key = load_key()
    if not key:
        raise SystemExit("VEXCEL_API_KEY is not configured; no request made.")
    params = {"wkt": POINT_WKT, "srid": "4326", "layer": LAYERS,
              "latest": "true", "include": "precomputed", "unit-system": "imperial"}
    property_response = get_json(key, "property/extract", params)
    (OUT / "vexcel_property_extract.json").write_text(json.dumps(property_response, indent=2)+"\n")
    parcel_wkt = POINT_WKT
    property_data = property_response.get("body")
    feature = None
    if property_response.get("status") == 200 and isinstance(property_data, dict):
        features=property_data.get("features") or []
        covering=[f for f in features if point_in_geometry(LON,LAT,f.get("geometry"))]
        candidates=covering or features
        feature=max(candidates,key=lambda f:(f.get("properties") or {}).get("metadata.ortho-date-estimate", "")) if candidates else None
        if feature and feature.get("geometry"):
            parcel_wkt=geo_to_wkt(feature["geometry"])
    coverage_params={"wkt":parcel_wkt,"srid":"4326","layer":"urban",
                     "product-type":"oblique","include":"product-type,collection,last-capture-date"}
    oriented_coverage=get_json(key,"oriented/collections",coverage_params)
    metadata_params={"wkt":parcel_wkt,"srid":"4326","layer":"urban","product-type":"oblique",
                     "include":"image-name,geometry,capture-date,collection,product-type,first-publish-date,last-publish-date"}
    metadata=get_json(key,"oriented/query",metadata_params)
    ortho_dates=get_json(key,"ortho/dates",{"wkt":parcel_wkt,"srid":"4326","layer":LAYERS})
    # Choose only directions actually listed in the newest oriented collection.
    cov_features=(oriented_coverage.get("body") or {}).get("features",[]) if oriented_coverage.get("status")==200 else []
    newest=max((f.get("properties",{}).get("last-capture-date","") for f in cov_features),default="")
    directions=sorted({f.get("properties",{}).get("product-type") for f in cov_features
                       if f.get("properties",{}).get("last-capture-date")==newest and f.get("properties",{}).get("product-type")})
    meta_features=(metadata.get("body") or {}).get("features",[]) if metadata.get("status")==200 else []
    selected_ids=[]
    for direction in directions:
        matches=[f for f in meta_features if (f.get("properties") or {}).get("product-type")==direction
                 and point_in_geometry(LON,LAT,f.get("geometry"))]
        if matches:
            latest=max((f.get("properties",{}).get("capture-date","") for f in matches),default="")
            selected_ids.extend({"direction":direction,"image_name":(f.get("properties") or {}).get("image-name"),
                                 "capture_date":(f.get("properties") or {}).get("capture-date"),
                                 "collection":(f.get("properties") or {}).get("collection"),
                                 "first_publish_date":(f.get("properties") or {}).get("first-publish-date"),
                                 "last_publish_date":(f.get("properties") or {}).get("last-publish-date")}
                                for f in matches if (f.get("properties") or {}).get("capture-date")==latest)
    SAMPLE.mkdir(parents=True,exist_ok=True)
    image_results={}
    ortho_body={"wkt":parcel_wkt,"srid":4326,"layer":LAYERS,"buffer-meter":10,
                "crop":"bounding_box","destination-dimensions":"800,800","image-format":"jpeg"}
    image_results["ortho"]=post_image(key,"ortho/extract",ortho_body,"ortho_latest.jpg")
    for direction in directions:
        body={"wkt":parcel_wkt,"srid":4326,"layer":"urban","product-type":direction,
              "rotation":"natural","buffer-meter":10,"crop":"bbox",
              "destination-dimensions":"800,800","image-format":"jpeg/png"}
        image_results[direction]=post_image(key,"oriented/extract",body,f"{direction}_latest.jpg")
    manifest={"source_provider":"Vexcel API v2","attribution":"Imagery © Vexcel Imaging US, Inc. (per supplied Vexcel Hackathon Tutorial).",
      "costar_property_id":236138,"address":"15603 W Hardy Rd, Houston, TX","latitude":LAT,"longitude":LON,
      "coordinate_reference_system":"EPSG:4326 (WGS84)","auth_method":"X-API-KEY header; credential value not recorded",
      "property_extract_status":property_response.get("status"),"parcel_geometry_type":feature.get("geometry",{}).get("type") if feature else None,
      "property_extract_candidate_count":len((property_data or {}).get("features",[])) if isinstance(property_data,dict) else 0,
      "selected_property_extract_collection":(feature.get("properties") or {}).get("metadata.collection") if feature else None,
      "selected_property_extract_capture_estimate":(feature.get("properties") or {}).get("metadata.ortho-date-estimate") if feature else None,
      "parcel_geometry_wkt":parcel_wkt,"oriented_coverage_status":oriented_coverage.get("status"),
      "oriented_metadata_status":metadata.get("status"),"ortho_dates_status":ortho_dates.get("status"),
      "newest_oriented_coverage_date":newest or None,"newest_oriented_directions":directions,
      "matching_oriented_source_images":selected_ids,"ortho_dates":ortho_dates.get("body"),
      "retrieved_at":datetime.now(timezone.utc).isoformat(),
      "image_extractions":image_results,"permissions":"Existing Vexcel API key authorized read-only access and image retrieval; no model writes/shares/mutations performed."}
    (SAMPLE/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    summary={"property_extract_status":property_response.get("status"),"oriented_coverage_status":oriented_coverage.get("status"),
      "oriented_coverage_count":len(cov_features),"oriented_metadata_count":len(meta_features),
      "newest_oriented_coverage_date":newest or None,"directions":directions,"source_image_match_count":len(selected_ids),
      "ortho_dates":ortho_dates.get("body"),"image_results":image_results,"sample_dir":str(SAMPLE)}
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
