"""Download one public Matterport skybox from the CoStar-matched model."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
RAW = OUT / "matterport_raw.json"
MODEL_ID = "NDMWnz1H9uV"


def main():
    raw = json.loads(RAW.read_text())
    spatial = raw["selected_model_spatial_assets"]["response"]["data"]["model"]
    metadata = raw["selected_model"]["response"]["data"]["model"]
    location = next((loc for loc in spatial.get("locations", [])
                     if any((p.get("skybox") or {}).get("status") == "available" for p in loc.get("panos", []))), None)
    if not location:
        raise SystemExit("No available public skybox was returned; no image downloaded.")
    pano = next(p for p in location["panos"] if (p.get("skybox") or {}).get("status") == "available")
    skybox = pano["skybox"]
    face_urls = skybox.get("children") or []
    if len(face_urls) != 6:
        raise SystemExit(f"Expected six skybox faces, got {len(face_urls)}; no image downloaded.")
    target = OUT / "matterport_sample" / location["id"]
    target.mkdir(parents=True, exist_ok=True)
    faces = []
    for index, url in enumerate(face_urls):
        req = Request(url, headers={"User-Agent": "Helix isolated research spike"})
        with urlopen(req, timeout=90) as response:
            content_type = response.headers.get("Content-Type", "")
            blob = response.read()
        path = target / f"skybox_face_{index}.jpg"
        path.write_bytes(blob)
        with Image.open(path) as image:
            width, height = image.size
            image.verify()
        faces.append({"image_id": skybox.get("id"), "child_face_index": index, "filename": path.name,
                      "width_px": width, "height_px": height, "content_type": content_type,
                      "bytes": len(blob), "sha256": __import__("hashlib").sha256(blob).hexdigest()})
    manifest = {
        "source_provider": "Matterport Model API",
        "attribution": "Matterport public model; model creator attribution was not returned by this API query.",
        "model_id": MODEL_ID, "model_name": metadata.get("name"),
        "model_visibility": metadata.get("visibility"), "model_state": metadata.get("state"),
        "model_created": metadata.get("created"),
        "model_created_interpretation": "Model API creation timestamp; not asserted to be the camera capture date.",
        "model_modified": metadata.get("modified"),
        "property_id_costar": 236138,
        "selected_location_id": location.get("id"), "position": location.get("position"),
        "position_coordinate_system": "Matterport local model coordinates; source API does not specify CRS in this response.",
        "floor": location.get("floor"), "room": location.get("room"),
        "panorama_id": pano.get("id"), "skybox_id": skybox.get("id"),
        "skybox_resolution": "high (documented 1024px face tier)", "skybox_format": skybox.get("format"),
        "skybox_status": skybox.get("status"),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "capture_timestamp": None, "coordinate_reference_system": None,
        "permission_basis": "Model API query confirms active, public model; no access/share settings were changed.",
        "faces": faces,
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"model_id": MODEL_ID, "model_name": metadata.get("name"), "visibility": metadata.get("visibility"),
                      "location_id": location.get("id"), "panorama_id": pano.get("id"),
                      "images": [{k: f[k] for k in ("filename", "width_px", "height_px", "bytes", "sha256")} for f in faces]}, indent=2))


if __name__ == "__main__":
    main()
