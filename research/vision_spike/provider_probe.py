"""Read-only Vexcel/Matterport capability probe; never logs credentials or signed URLs."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(parents=True, exist_ok=True)
PROPERTY_ID = 236138
MODEL_ID = "NDMWnz1H9uV"
LAT, LON = 29.944369, -95.385271


def load_env():
    for path in (ROOT / ".env", ROOT / "project helix" / ".env"):
        if not path.exists():
            continue
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def request(url, headers=None, timeout=60):
    req = Request(url, headers=headers or {}, method="GET")
    started = time.monotonic()
    try:
        with urlopen(req, timeout=timeout) as response:
            body = response.read()
            return response.status, response.headers.get("Content-Type", ""), body, round(time.monotonic()-started, 3)
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read(), round(time.monotonic()-started, 3)
    except (URLError, TimeoutError, OSError) as exc:
        return 0, "", json.dumps({"error_type": type(exc).__name__}).encode(), round(time.monotonic()-started, 3)


def save_private(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _count_records(value):
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for v in value.values():
            if isinstance(v, list):
                return len(v)
            n = _count_records(v)
            if n is not None:
                return n
    return None


def vexcel_probe(token):
    wkt = f"POINT({LON} {LAT})"
    # Vexcel accepts X-API-KEY (preferred) or `api_key`; it does not use a
    # `token` query parameter. Keep credentials out of URLs and logs.
    headers = {"X-API-KEY": token, "Accept": "application/json"}
    paths = {
        "oriented_coverage": ("oriented/collections", {"wkt": wkt, "srid": "4326", "layer": "urban",
                                "product-type": "oblique", "include": "product-type,collection,last-capture-date"}),
        "oriented_metadata": ("oriented/query", {"wkt": wkt, "srid": "4326", "layer": "urban",
                             "product-type": "oblique", "include": "image-name,geometry,capture-date,collection,product-type,first-publish-date,last-publish-date"}),
        "ortho_dates": ("ortho/dates", {"wkt": wkt, "srid": "4326", "layer": "urban,urban-r,wide-area,urban-g"}),
        "ortho_coverage": ("ortho/collections", {"wkt": wkt, "srid": "4326",
                            "layer": "urban,urban-r,wide-area,urban-g", "include": "collection,last-capture-date"}),
    }
    result, private = {}, {}
    for key, (path, params) in paths.items():
        status, content_type, body, latency = request("https://api.vexcelgroup.com/v2/" + path + "?" + urlencode(params), headers=headers)
        parsed = None
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        private[key] = {"status": status, "content_type": content_type,
                        "body": parsed if parsed is not None else body.decode("utf-8", "replace")[:20000]}
        result[key] = {"http_status": status, "content_type": content_type, "latency_seconds": latency,
                       "response_type": type(parsed).__name__ if parsed is not None else "non_json",
                       "has_error_field": isinstance(parsed, dict) and bool(parsed.get("error")),
                       "top_level_keys": sorted(parsed.keys())[:20] if isinstance(parsed, dict) else [],
                       "record_count": _count_records(parsed)}
    save_private("vexcel_raw.json", private)
    return {"credential_present": True, "auth_method": "X-API-KEY header", "operations": result,
            "imagery_extraction_attempted": False,
            "reason": "Read-only coverage/metadata checks only; no image extracts requested."}


def _post_graphql(url, headers, data):
    started = time.monotonic()
    req = Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
    try:
        with urlopen(req, timeout=90) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read(), round(time.monotonic()-started, 3)
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read(), round(time.monotonic()-started, 3)
    except (URLError, TimeoutError, OSError) as exc:
        return 0, "", json.dumps({"error_type": type(exc).__name__}).encode(), round(time.monotonic()-started, 3)


def matterport_probe(token_id, token_secret):
    endpoint = "https://api.matterport.com/api/models/graph"
    auth = base64.b64encode(f"{token_id}:{token_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json", "Accept": "application/json"}
    queries = {
        "authorized_models": {"query": "query { models(query: \"id:NDMWnz1H9uV\", pageSize: 10) { totalResults results { id name created modified visibility demo address { streetAddressLines locality administrativeArea postalCode countryCode } } } }"},
        "selected_model": {"query": "query($id: ID!) { model(id: $id) { id name state visibility created modified description } }", "variables": {"id": MODEL_ID}},
        "selected_model_spatial_assets": {"query": "query($id: ID!) { model(id: $id) { id name dimensions { areaFloor areaFloorIndoor volume height width depth units } floors { id label dimensions(units: imperial) { areaFloor areaFloorIndoor areaWall volume height width depth units } } rooms { id label tags dimensions { areaFloor areaFloorIndoor areaWall volume height width depth units } } locations { id label position { x y z } floor { id label } room { id label } panos { id skybox(resolution: \"high\") { id status format children } } } } }", "variables": {"id": MODEL_ID}},
    }
    private, report = {}, {}
    for key, body in queries.items():
        status, content_type, response, latency = _post_graphql(endpoint, headers, body)
        parsed = None
        try:
            parsed = json.loads(response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        private[key] = {"http_status": status, "content_type": content_type,
                        "response": parsed if parsed is not None else response.decode("utf-8", "replace")[:20000]}
        report[key] = {"http_status": status, "content_type": content_type, "latency_seconds": latency,
                       "graphql_error_count": len(parsed.get("errors", [])) if isinstance(parsed, dict) else None,
                       "data_keys": sorted((parsed.get("data") or {}).keys()) if isinstance(parsed, dict) and isinstance(parsed.get("data"), dict) else []}
        if key == "authorized_models" and isinstance(parsed, dict):
            models = ((parsed.get("data") or {}).get("models") or {}).get("results") or []
            report[key]["total_results"] = ((parsed.get("data") or {}).get("models") or {}).get("totalResults")
            report[key]["returned_count"] = len(models)
            report[key]["matches"] = [{"id": m.get("id"), "name": m.get("name"),
                "visibility": m.get("visibility"), "demo": m.get("demo")} for m in models]
        if key == "selected_model" and isinstance(parsed, dict):
            selected = (parsed.get("data") or {}).get("model")
            report[key]["found"] = selected is not None
            report[key]["selected"] = selected
        if key == "selected_model_spatial_assets" and isinstance(parsed, dict):
            selected = (parsed.get("data") or {}).get("model")
            if selected:
                locations = selected.get("locations") or []
                panoramas = [p for loc in locations for p in (loc.get("panos") or [])]
                report[key]["model_name"] = selected.get("name")
                report[key]["room_count"] = len(selected.get("rooms") or [])
                report[key]["floor_count"] = len(selected.get("floors") or [])
                report[key]["location_count"] = len(locations)
                report[key]["panorama_count"] = len(panoramas)
                report[key]["available_skybox_count"] = sum(1 for p in panoramas if (p.get("skybox") or {}).get("status") == "available")
                report[key]["first_room_dimensions"] = (selected.get("rooms") or [{}])[0].get("dimensions")
                report[key]["coordinate_sample"] = [{"location_id": loc.get("id"), "position": loc.get("position"),
                    "floor": loc.get("floor"), "room": loc.get("room"),
                    "skybox_statuses": [((p.get("skybox") or {}).get("status")) for p in (loc.get("panos") or [])]}
                    for loc in locations[:3]]
    save_private("matterport_raw.json", private)
    return {"credential_present": True, "endpoint": endpoint, "read_only_queries": report,
            "writes_or_shares_attempted": False}


def main():
    load_env()
    report = {"property": {"property_id": PROPERTY_ID, "latitude": LAT, "longitude": LON,
                            "matterport_model_id_from_costar": MODEL_ID}, "providers": {}}
    vkey = os.environ.get("VEXCEL_API_KEY")
    report["providers"]["vexcel"] = vexcel_probe(vkey) if vkey else {"credential_present": False, "status": "dry_run"}
    mp_id, mp_secret = os.environ.get("MATTERPORT_API_KEY"), os.environ.get("MATTERPORT_API_TOKEN")
    report["providers"]["matterport"] = matterport_probe(mp_id, mp_secret) if mp_id and mp_secret else {"credential_present": False, "status": "dry_run"}
    save_private("provider_probe.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
