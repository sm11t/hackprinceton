"""Serve the Houston address playground on localhost."""
import argparse
import csv
from functools import lru_cache
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import re
from urllib.parse import parse_qs, urlencode, urlsplit
from zipfile import ZipFile

from probe import aerial_image, load_property, matterport_model
from pilot import ROOT, comparison, evidence
from nessie_pilot import buyer_from_nessie


def words(value):
    return re.findall(r"[a-z0-9]+", value.lower())


def lookup(rows, query):
    terms = words(query)
    return [
        row for row in rows
        if all(any(word.startswith(term) for word in words(
            f'{row["Address"]} {row["City"]} {row["State"]}'
        )) for term in terms)
    ]


def link(**params):
    return escape("/?" + urlencode(params), quote=True)


def value(item):
    return escape(str(item)) if item is not None and item != "" else "—"


def room_table(model):
    rows = []
    for floor in model.get("floors") or []:
        for room in floor.get("rooms") or []:
            classes = room.get("classifications") or []
            category = max(classes, key=lambda c: c.get("confidence") or 0)["label"] if classes else None
            area = (room.get("dimensionEstimates") or {}).get("area")
            rows.append("<tr>" + "".join(f"<td>{value(cell)}</td>" for cell in (
                floor.get("label"), room.get("label"), category,
                round(area, 1) if area is not None else None,
            )) + "</tr>")
    if not rows:
        return "<p>No room records for this scan.</p>"
    return (
        "<table><thead><tr><th>Floor</th><th>Room</th><th>Type</th><th>Area (m²)</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def page(query, content):
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Houston property search</title>
<style>
* {{ box-sizing: border-box }}
body {{ margin: 0 auto; max-width: 1120px; padding: 32px 24px; color: #202522;
  background: #fafaf8; font: 15px/1.5 "Instrument Sans", system-ui, sans-serif }}
h1 {{ font-size: 23px; margin: 0 0 16px }}
h2 {{ font-size: 19px; margin: 0 0 6px }}
h3 {{ font-size: 15px; margin: 0 0 10px }}
form {{ display:flex; gap:8px; margin-bottom: 22px }}
input, button {{ font: inherit; padding: 8px 12px; border: 1px solid #acb4ad; border-radius: 3px }}
input {{ width: min(100%, 460px); min-width: 0; background: white }}
button {{ background: #253e34; border-color: #253e34; color: white; cursor: pointer }}
a {{ color: #24543f }}
.meta {{ color: #515b54; margin: 0 0 20px }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 28px }}
img {{ width: 100%; height: auto; display: block; background: #e6e9e3 }}
details {{ margin: 12px 0 }}
summary {{ color: #24543f; cursor: pointer }}
iframe {{ display: block; width: 100%; aspect-ratio: 4 / 3; margin-top: 8px; border: 0;
  background: #e6e9e3 }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px }}
th, td {{ border-bottom: 1px solid #d9ded8; text-align: left; padding: 7px 6px }}
th:last-child, td:last-child {{ text-align: right }}
@media (max-width: 740px) {{ .grid {{ grid-template-columns: 1fr }} }}
</style>
<main>
<h1>Houston property search</h1>
<form action="/"><input name="q" aria-label="Houston address" placeholder="Search a Houston address"
  value="{escape(query, quote=True)}" required><button>Search</button></form>
{content}
</main>""".encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--offline", action="store_true", help="Use saved playground/output evidence and aerial; tour still requires internet")
    parser.add_argument("--nessie-account", help="Read starting cash and recurring bills from a Nessie sandbox account")
    args = parser.parse_args()
    buyer = buyer_from_nessie(args.nessie_account) if args.nessie_account else None
    password = os.environ.get("COSTAR_KIT_PASSWORD", "").encode() or None
    with ZipFile(args.kit) as kit, kit.open("commercial-properties.csv", pwd=password) as stream:
        properties = {}
        for row in csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig")):
            if row["City"].casefold() == "houston":
                properties.setdefault(row["PropertyId"], row)

    @lru_cache(maxsize=64)
    def property_data(property_id):
        return load_property(args.kit, int(property_id), password, require_model=False)

    @lru_cache(maxsize=32)
    def image_for(property_id):
        if args.offline:
            return (ROOT / "output" / f"{property_id}-aerial.jpg").read_bytes()
        prop, _ = property_data(property_id)
        address = prop["primaryAddress"]
        return aerial_image(address["latitude"], address["longitude"])

    @lru_cache(maxsize=64)
    def rooms_for(model_id):
        if args.offline:
            for path in (ROOT / "output").glob("*-evidence.json"):
                model = json.loads(path.read_text()).get("matterport") or {}
                if model.get("id") == model_id:
                    return model
            raise RuntimeError("No saved evidence for this scan. Run probe.py first.")
        return matterport_model(model_id)

    def detail(property_id, query, requested_model):
        row = properties[property_id]
        try:
            prop, matches = property_data(property_id)
        except (OSError, RuntimeError, ValueError) as error:
            return f"<p>{value(error)}</p>"
        models = [match["MatterportModelId"] for match in matches if match["MatterportModelId"]]
        scan = requested_model if requested_model in models else next(iter(models), "")
        area = prop.get("grossBuildingAreaSquareFeet")
        size = f" · {area:,.0f} sq ft" if area is not None else ""
        content = (
            f'<h2>{value(row["Address"])}</h2><p class="meta">Houston, TX · CoStar {property_id}{size}</p>'
        )
        interior = "<p>No Matterport scan is linked to this property.</p>"
        if scan:
            scan_links = " · ".join(
                f'<a href="{link(q=query, id=property_id, model=model)}">Scan {index}</a>'
                if model != scan else f"Scan {index}"
                for index, model in enumerate(models, 1)
            )
            try:
                rooms = room_table(rooms_for(scan))
            except (KeyError, OSError, RuntimeError, ValueError) as error:
                rooms = f"<p>{value(error)}</p>"
            tour_url = escape("https://my.matterport.com/show/?" + urlencode({"m": scan}), quote=True)
            interior = (
                f'<p>{scan_links}</p><details><summary>View 3D tour</summary>'
                f'<iframe src="{tour_url}" title="Matterport 3D tour" loading="lazy"'
                ' allow="fullscreen; xr-spatial-tracking"></iframe>'
                f'<p><a href="{tour_url}" target="_blank" rel="noreferrer">Open in a new tab</a></p>'
                f'</details>{rooms}'
            )
        try:
            image_for(property_id)
            aerial = f'<img src="/aerial?id={property_id}" alt="Vexcel aerial of {value(row["Address"])}">'
        except (KeyError, OSError, RuntimeError, ValueError) as error:
            aerial = f"<p>{value(error)}</p>"
        return (
            content + '<div class="grid"><section><h3>Vexcel aerial</h3>'
            + aerial + '</section><section><h3>Matterport rooms</h3>' + interior + '</section></div>'
        )

    class Handler(BaseHTTPRequestHandler):
        def send(self, body, content_type, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if urlsplit(self.path).path != "/api/pilot/simulate":
                self.send(b"Not found", "text/plain", 404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError("Invalid request size")
                inputs = json.loads(self.rfile.read(length))
                if not isinstance(inputs, dict):
                    raise ValueError("Expected an assumptions object")
                body = comparison(inputs, buyer)
                self.send(json.dumps(body).encode(), "application/json")
            except (ValueError, TypeError, OverflowError) as error:
                self.send(json.dumps({"error": str(error)}).encode(), "application/json", 400)

        def do_GET(self):
            route = urlsplit(self.path)
            params = parse_qs(route.query)
            if route.path in ("/", "/pilot") and not route.query:
                filename = "pilot.html" if route.path == "/pilot" else "index.html"
                self.send((ROOT / "static" / filename).read_bytes(), "text/html; charset=utf-8")
                return
            assets = {"/static/pilot.css": "text/css", "/static/pilot.js": "text/javascript",
                      "/static/workspace.css": "text/css", "/static/workspace.js": "text/javascript"}
            if route.path in assets:
                self.send((ROOT / "static" / route.path.rsplit("/", 1)[1]).read_bytes(), assets[route.path])
                return
            if route.path == "/api/pilot/evidence":
                try:
                    prop, matches = property_data("23296")
                    models = list(dict.fromkeys(m["MatterportModelId"] for m in matches if m["MatterportModelId"]))
                    model, error = None, None
                    try:
                        model = rooms_for(models[0]) if models else None
                    except (KeyError, OSError, RuntimeError, ValueError) as exc:
                        error = str(exc)
                    body = evidence(prop, models, model, error,
                                    "Saved local capture · not refreshed" if args.offline else "CoStar kit + live Matterport")
                    self.send(json.dumps(body).encode(), "application/json")
                except (KeyError, OSError, RuntimeError, ValueError) as exc:
                    self.send(json.dumps({"error": str(exc)}).encode(), "application/json", 502)
                return
            query = params.get("q", [""])[0].strip()
            property_id = params.get("id", [""])[0]
            model = params.get("model", [""])[0]
            if route.path == "/aerial" and property_id in properties:
                try:
                    self.send(image_for(property_id), "image/jpeg")
                except (KeyError, OSError, RuntimeError, ValueError):
                    self.send(b"Aerial image unavailable.", "text/plain", 502)
                return
            if route.path not in ("/", "/search"):
                self.send(b"Not found", "text/plain", 404)
                return

            content = ""
            if property_id in properties:
                content = detail(property_id, query, model)
            elif query:
                matches = lookup(properties.values(), query)
                if len(matches) == 1:
                    content = detail(matches[0]["PropertyId"], query, "")
                elif matches:
                    items = "".join(
                        f'<li><a href="{link(q=query, id=row["PropertyId"])}">{value(row["Address"])}</a></li>'
                        for row in matches[:50]
                    )
                    content = f"<ul>{items}</ul>"
                    if len(matches) > 50:
                        content += "<p>Showing the first 50. Add a street number to narrow the search.</p>"
                else:
                    content = "<p>No matching Houston address in the sponsor kit.</p>"
            else:
                content = f'<p>Try <a href="{link(q="9700 Tanner Rd")}">9700 Tanner Rd</a>.</p>'
            self.send(page(query, content), "text/html; charset=utf-8")

    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
