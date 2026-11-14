"""Join a CoStar property to Matterport rooms and Vexcel imagery."""
import argparse
import base64
import csv
import io
import json
import math
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile

MATTERPORT = "https://api.matterport.com/api/models/graph"
VEXCEL = "https://api.vexcelgroup.com/v2"
LAYERS = "urban,urban-r,wide-area,urban-g"
ROOMS = """
query PropertyRooms($id: ID!) {
  model(id: $id) {
    id name
    floors {
      id label
      rooms {
        id label
        classifications { label confidence }
        dimensionEstimates(units: metric) { area areaIndoor height }
      }
    }
  }
}
"""


def load_property(kit_path, property_id, password, *, require_model=True):
    with ZipFile(kit_path) as kit:
        with kit.open("commercial-properties.csv", pwd=password) as stream:
            matches = [
                row for row in csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"))
                if row["PropertyId"] == str(property_id)
                and (row["MatterportModelId"] or not require_model)
            ]
        if not matches:
            raise ValueError(f"No Matterport mapping for CoStar property {property_id}.")
        with kit.open("data/commercial-property.jsonl", pwd=password) as stream:
            for line in stream:
                prop = json.loads(line)
                if prop["id"] == property_id:
                    return prop, matches
    raise ValueError(f"CoStar property {property_id} was absent from the property records.")


def request(url, headers, body=None):
    if body is not None:
        headers = {**headers, "Content-Type": "application/json"}
        body = json.dumps(body).encode()
    try:
        with urlopen(Request(url, data=body, headers=headers), timeout=30) as response:
            return response.read()
    except HTTPError as error:
        raise RuntimeError(f"HTTP {error.code} from {url.split('?')[0]}") from None
    except URLError as error:
        raise RuntimeError(f"Could not reach {url.split('?')[0]}: {error.reason}") from None


def matterport_model(model_id):
    credentials = f"{os.environ['MATTERPORT_API_KEY']}:{os.environ['MATTERPORT_API_TOKEN']}"
    auth = base64.b64encode(credentials.encode()).decode()
    payload = json.loads(request(
        MATTERPORT, {"Authorization": f"Basic {auth}"},
        {"query": ROOMS, "variables": {"id": model_id}},
    ))
    if payload.get("errors"):
        messages = "; ".join(error["message"] for error in payload["errors"])
        raise RuntimeError(f"Matterport GraphQL: {messages}")
    model = payload.get("data", {}).get("model")
    if not model:
        raise RuntimeError("Matterport returned no model for this ID.")
    return model


def aerial_image(latitude, longitude):
    # Request a small square centered on the CoStar address. WKT uses longitude first.
    dy = 90 / 111_320
    dx = dy / math.cos(math.radians(latitude))
    west, east = longitude - dx, longitude + dx
    south, north = latitude - dy, latitude + dy
    wkt = f"POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))"
    image = request(
        f"{VEXCEL}/ortho/extract", {"X-API-KEY": os.environ["VEXCEL_API_KEY"]},
        {"wkt": wkt, "srid": 4326, "layer": LAYERS, "crop": "bounding_box",
         "destination-dimensions": "800,800", "image-format": "jpeg"},
    )
    if not image.startswith(b"\xff\xd8"):
        raise RuntimeError("Vexcel did not return a JPEG.")
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--property-id", type=int, default=23296)
    parser.add_argument("--model-id", help="Choose a model when the property has multiple scans.")
    parser.add_argument("--output", type=Path, default=Path("playground/output"))
    parser.add_argument("--costar-only", action="store_true")
    args = parser.parse_args()

    password = os.environ.get("COSTAR_KIT_PASSWORD", "").encode() or None
    try:
        prop, matches = load_property(args.kit, args.property_id, password)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    models = [row["MatterportModelId"] for row in matches]
    model_id = args.model_id or models[0]
    if model_id not in models:
        parser.error(f"Model {model_id} is not linked to this property. Available: {', '.join(models)}")

    address = prop["primaryAddress"]
    report = {
        "costar": {
            "id": prop["id"],
            "address": matches[0]["Address"],
            "city": address["city"],
            "state": address["state"],
            "latitude": address["latitude"],
            "longitude": address["longitude"],
            "buildingName": prop.get("buildingName"),
            "buildingAreaSqFt": prop.get("grossBuildingAreaSquareFeet"),
        },
        "linkedMatterportModelIds": models,
        "errors": {},
    }
    args.output.mkdir(parents=True, exist_ok=True)
    if not args.costar_only:
        try:
            report["matterport"] = matterport_model(model_id)
        except (KeyError, RuntimeError, ValueError) as error:
            report["errors"]["matterport"] = str(error)
        try:
            image = aerial_image(address["latitude"], address["longitude"])
            image_path = args.output / f"{prop['id']}-aerial.jpg"
            image_path.write_bytes(image)
            report["vexcel"] = {"image": image_path.name, "view": "orthographic"}
        except (KeyError, RuntimeError, ValueError) as error:
            report["errors"]["vexcel"] = str(error)

    report_path = args.output / f"{prop['id']}-evidence.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report_path)
    for provider, error in report["errors"].items():
        print(f"{provider}: {error}")
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
