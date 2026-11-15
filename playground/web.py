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
import subprocess
from tempfile import TemporaryDirectory
from threading import Lock, Thread
from urllib.parse import parse_qs, urlencode, urlsplit
from zipfile import ZipFile

from probe import aerial_image, load_property, matterport_model
from pilot import CONFIG, ROOT, comparison, evidence
from nessie_pilot import buyer_from_nessie
from advisor_money import advisor_cash, comparison_inputs
from cost_ledger import estimate_costs
from maximo import REVIEW_USES, project_cash, review_property, suite_options
from market_rank import load_market, rank_market
from deal import load_deal_data, load_rent_estimates, rent_for_simulation, run_deal
import neighborhood
import opportunity
import venture_review
import ventures
from space_fit import REQUIREMENTS, USES, run as space_fit_run, run_rank as space_fit_rank


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
    parser.add_argument("--research-replay", type=Path, help="Replay one saved public research report only for its exact address and use; visibly labeled")
    parser.add_argument("--nessie-account", help="Read starting cash and recurring bills from a Nessie sandbox account")
    args = parser.parse_args()
    if args.offline:  # the neighborhood check then reads only its cached public data
        os.environ.setdefault("NEIGHBORHOOD_OFFLINE", "1")
    Thread(target=neighborhood.warm, args=(args.kit,), daemon=True).start()
    Thread(target=opportunity.warm, args=(args.kit,), daemon=True).start()
    buyer = buyer_from_nessie(args.nessie_account) if args.nessie_account else None
    password = os.environ.get("COSTAR_KIT_PASSWORD", "").encode() or None
    location_properties = {}
    location_lock = Lock()
    with ZipFile(args.kit) as kit, kit.open("commercial-properties.csv", pwd=password) as stream:
        properties = {}
        for row in csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig")):
            if row["City"].casefold() == "houston":
                properties.setdefault(row["PropertyId"], row)
            city = {"houston": "Houston", "los angeles": "Los Angeles"}.get(row["City"].strip().casefold())
            if city and row["PropertyId"].isdigit() and row["Address"].strip():
                location_properties.setdefault(row["PropertyId"], {
                    "id": row["PropertyId"], "address": row["Address"], "city": city,
                })

    market_lock = Lock()

    @lru_cache(maxsize=2)
    def load_market_once(market):
        return load_market(args.kit, market, password)

    def market_candidates(market):
        """Listed spaces for a whole market; ~30 s to read once, then cached for every ranking.
        The lock makes a request that arrives during the startup warm-up wait instead of reading twice."""
        with market_lock:
            return load_market_once(market)

    Thread(target=market_candidates, args=("Houston",), daemon=True).start()  # warm before the first click

    @lru_cache(maxsize=64)
    def property_data(property_id):
        return load_property(args.kit, int(property_id), password, require_model=False)

    @lru_cache(maxsize=128)
    def fit_for(property_id, use, suite, requirements=(), label=""):
        return space_fit_run(args.kit, property_id, use, suite or None, args.offline, password,
                             dict(requirements), label or None)

    @lru_cache(maxsize=128)
    def deal_for(property_id, capital, suite, square_feet):
        return run_deal(args.kit, property_id, capital, password, suite or None, square_feet)

    @lru_cache(maxsize=1)
    def pilot_rent():
        """The kit's asking rent for the pilot scenario's space; None keeps the scenario's assumed rent."""
        scenario = CONFIG["property"]
        try:
            spaces, _, _ = load_deal_data(args.kit, scenario["costar_id"], password)
        except (KeyError, OSError, RuntimeError, ValueError):
            return None
        return rent_for_simulation(spaces, square_feet=scenario.get("suite_sqft"))

    @lru_cache(maxsize=64)
    def rank_for(property_id, suite):
        return space_fit_rank(args.kit, property_id, suite or None, args.offline, password)

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

    def market_review(property_id, use):
        if args.research_replay:
            saved=json.loads(args.research_replay.read_text())
            entry=location_properties[str(property_id)]
            expected=f"{entry['address']}, {entry['city']},".casefold()
            if not saved.get('address','').casefold().startswith(expected) or saved.get('proposed_use') != use:
                raise RuntimeError('No saved research for this address and use')
            saved['replayed']=True
            return saved
        if not os.environ.get("UPSTAGE_API_KEY"):
            raise RuntimeError("Research provider is not configured")
        if not location_lock.acquire(blocking=False):
            raise RuntimeError("Research already running")
        try:
            with TemporaryDirectory(prefix="reuse-location-") as directory:
                output = Path(directory) / "report.json"
                try:
                    subprocess.run(
                        ["uv", "run", str(ROOT / "location_run.py"), "--kit", str(args.kit.resolve()),
                         "--property-id", str(property_id), "--use", use, "--output", str(output)],
                        check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                except subprocess.SubprocessError as error:
                    raise RuntimeError("Research provider did not finish") from error
                return json.loads(output.read_text())
        finally:
            location_lock.release()

    class Handler(BaseHTTPRequestHandler):
        def send(self, body, content_type, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def location_run(self):
            def respond(body, status=200):
                self.send(json.dumps(body).encode(), "application/json", status)

            if self.headers.get_content_type() != "application/json":
                respond({"error": "Send an application/json request."}, 415)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024:
                    raise ValueError()
                payload = json.loads(self.rfile.read(length))
                property_id = payload["property_id"]
                use = payload["use"]
                if property_id not in location_properties or use not in ("indoor pickleball", "fitness studio"):
                    raise ValueError()
            except (KeyError, TypeError, ValueError, UnicodeError):
                respond({"error": "Choose a property and use from the demo."}, 400)
                return
            if not os.environ.get("UPSTAGE_API_KEY"):
                respond({"error": "Set UPSTAGE_API_KEY in the server environment to run agents."}, 503)
                return
            if not location_lock.acquire(blocking=False):
                respond({"error": "A review is already running. Try again when it finishes."}, 409)
                return
            try:
                with TemporaryDirectory(prefix="reuse-location-") as directory:
                    output = Path(directory) / "report.json"
                    subprocess.run(
                        ["uv", "run", str(ROOT / "location_run.py"), "--kit", str(args.kit.resolve()),
                         "--property-id", property_id, "--use", use, "--output", str(output)],
                        check=True, timeout=240, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    report = json.loads(output.read_text())
                respond({key: report[key] for key in
                         ("address", "proposed_use", "demand_verified", "findings", "unknowns", "validation_issues")}
                        | {"sources": [{key: source.get(key) for key in
                                       ("source_id", "fact", "evidence_url", "captured_at", "note")}
                                       for source in report["evidence"]]})
            except subprocess.TimeoutExpired:
                respond({"error": "The review timed out. Try again."}, 504)
            except FileNotFoundError:
                respond({"error": "The review runner is unavailable. Install uv on the server."}, 503)
            except (subprocess.CalledProcessError, OSError, ValueError, KeyError):
                respond({"error": "The review could not finish. Check the server keys and provider availability."}, 502)
            finally:
                location_lock.release()

        def maximo_request(self, route):
            if self.headers.get_content_type() != "application/json":
                self.send(b'{"error":"Expected JSON."}', "application/json", 415)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError("Invalid request size.")
                payload = json.loads(self.rfile.read(length))
                use, ownership = payload["use"], payload["ownership"]
                inputs = payload.get("inputs", {})
                if use not in REVIEW_USES or ownership not in ("lease", "buy") or not isinstance(inputs, dict):
                    raise ValueError("Choose a supported use and lease or buy.")
                if route.endswith('/estimate'):
                    report = advisor_cash(inputs,use,ownership,overrides=payload.get('cost_overrides'),buyer=buyer)
                    report['comparisons'] = {}
                    for candidate in payload.get('compare_uses', []):
                        if candidate not in REVIEW_USES: raise ValueError('Unknown comparison use.')
                        candidate_inputs = comparison_inputs(inputs,use,candidate)
                        modeled = report if candidate == use else advisor_cash(candidate_inputs,candidate,ownership,buyer=buyer)
                        report['comparisons'][candidate] = {
                            'cash_required': modeled['costs']['totals']['base']['cash_required'],
                            'shortfall': modeled['costs']['totals']['base']['shortfall'],
                            'reserve_gap': (modeled['money'] or {}).get('conversion',{}).get('extra_funding_needed'),
                            'opening_delay': modeled['costs']['opening_month'],
                            'runway': (modeled['money'] or {}).get('runway_months')}
                elif route.endswith("/cash"):
                    if payload.get("scenario_only") is not True:
                        raise ValueError("Confirm that you want a hypothetical cash scenario.")
                    report = advisor_cash(inputs,use,ownership,overrides=payload.get('cost_overrides'),buyer=buyer) if payload.get('itemized') else project_cash(inputs, use, ownership, buyer)
                else:
                    entry = location_properties[str(payload["property_id"])]
                    suite = payload.get("suite") or None
                    if suite is not None and not isinstance(suite, str):
                        raise ValueError("Invalid suite.")
                    report = review_property(args.kit, entry, use, suite, ownership, inputs,
                                             password=password, offline=args.offline, buyer=buyer,
                                             research=market_review, replay_research=bool(args.research_replay), cost_overrides=payload.get("cost_overrides"))
                self.send(json.dumps(report).encode(), "application/json")
            except ValueError as error:
                self.send(json.dumps({"error": str(error)}).encode(), "application/json", 400)
            except (TypeError, KeyError, AttributeError):
                self.send(b'{"error":"Choose a property and review inputs from the workspace."}', "application/json", 400)
            except (OSError, RuntimeError):
                self.send(b'{"error":"Property review unavailable. Check local kit and provider settings."}', "application/json", 502)

        def ventures_request(self, method):
            """GET /api/ventures?user= | POST /api/ventures {user, kind, name} |
            GET /api/ventures/<id>?user= | POST /api/ventures/<id>?user= {changes}"""
            route = urlsplit(self.path)
            params = parse_qs(route.query)
            parts = route.path.strip("/").split("/")
            try:
                body = {}
                if method == "POST":
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= ventures.MAX_BYTES:
                        raise ValueError("Invalid request size.")
                    body = json.loads(self.rfile.read(length))
                    if not isinstance(body, dict):
                        raise ValueError("Expected a JSON object.")
                user = params.get("user", [body.get("user", "demo")])[0] or "demo"
                if len(parts) == 2 and method == "GET":
                    result = ventures.all_for(user)
                elif len(parts) == 2:
                    result = ventures.create(user, body.get("kind", "budget"), body.get("name"))
                elif method == "GET":
                    result = ventures.get(user, parts[2])
                else:
                    result = ventures.update(user, parts[2], {k: v for k, v in body.items() if k != "user"})
                self.send(json.dumps(result).encode(), "application/json")
            except KeyError:
                self.send(b'{"error":"Venture not found."}', "application/json", 404)
            except ValueError as error:
                self.send(json.dumps({"error": str(error)}).encode(), "application/json", 400)

        def do_POST(self):
            route = urlsplit(self.path).path
            if route == "/api/ventures" or route.startswith("/api/ventures/"):
                self.ventures_request("POST")
                return
            if route in ("/api/maximo/run", "/api/maximo/cash", "/api/maximo/estimate"):
                self.maximo_request(route)
                return
            if urlsplit(self.path).path == "/api/location/run":
                self.location_run()
                return
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
                body = comparison(inputs, buyer, pilot_rent())
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
            if route.path == "/maximo":
                self.send((ROOT / "static/maximo.html").read_bytes(), "text/html; charset=utf-8")
                return
            if route.path == "/flow":
                self.send((ROOT / "static/flow.html").read_bytes(), "text/html; charset=utf-8")
                return
            if route.path == "/suite":
                self.send((ROOT / "static/suite.html").read_bytes(), "text/html; charset=utf-8")
                return
            if route.path == "/api/maximo/rank":
                try:
                    market = params.get("market", ["Houston"])[0]
                    if market not in ("Houston", "Los Angeles"):
                        raise ValueError("Choose Houston or Los Angeles.")
                    number = lambda name, default=None: float(params[name][0]) if params.get(name, [""])[0] else default  # noqa: E731
                    capital, reserve = number("capital", 320000), number("reserve", 50000)
                    if not (0 <= capital <= 1e9 and 0 <= reserve <= 1e9):
                        raise ValueError("Cash and reserve must be between 0 and 1,000,000,000.")
                    body = rank_market(market_candidates(market), params.get("use", [""])[0], capital, reserve,
                                       min_sf=number("min_sf"), max_sf=number("max_sf"),
                                       rent_estimates=load_rent_estimates())
                    self.send(json.dumps(body).encode(), "application/json")
                except ValueError as error:
                    self.send(json.dumps({"error": str(error)}).encode(), "application/json", 400)
                except (OSError, RuntimeError, KeyError):
                    self.send(b'{"error":"Market ranking unavailable. Check the local kit."}', "application/json", 502)
                return
            if route.path == "/api/ventures" or route.path.startswith("/api/ventures/"):
                self.ventures_request("GET")
                return
            if route.path in ("/api/opportunities", "/api/venture/review"):
                try:
                    number = lambda name, default=None: float(params[name][0]) if params.get(name, [""])[0] else default  # noqa: E731
                    budget, reserve = number("budget"), number("reserve", 0)
                    if budget is None or not (0 < budget <= 1e9 and 0 <= reserve <= budget):
                        raise ValueError("Give a budget between 0 and 1,000,000,000 and a reserve below it.")
                    if route.path == "/api/opportunities":
                        lat, lon, radius = number("lat"), number("lon"), number("radius")
                        exclude = [k for k in params.get("exclude", [""])[0].split(",") if k]
                        include = [k for k in params.get("include", [""])[0].split(",") if k] or None
                        pids = {int(x) for x in params.get("property_id", [""])[0].split(",") if x.isdigit()} or None
                        body = opportunity.scan(budget, reserve, args.kit, center=(lat, lon) if lat and lon else None,
                                                radius_mi=radius, exclude=exclude, top=int(number("top", 8)),
                                                include=include, property_ids=pids)
                    else:
                        property_id = params.get("property_id", [""])[0]
                        if not property_id.isdigit():
                            raise ValueError("Give a CoStar property_id.")
                        bank = None
                        if params.get("nessie", [""])[0]:  # the user's other bills, from the Nessie sandbox account
                            try:
                                import suite_nessie
                                bank = suite_nessie.read(params["nessie"][0] if params["nessie"][0] != "1" else None)
                            except (RuntimeError, OSError, ValueError, KeyError):
                                bank = None
                        body = venture_review.review(params.get("business", [""])[0], int(property_id),
                                                     params.get("suite", [""])[0] or None, budget, reserve, args.kit,
                                                     delay_months=int(number("delay", 0)),
                                                     explain=params.get("explain", ["0"])[0] == "1", bank=bank)
                    self.send(json.dumps(body, default=str).encode(), "application/json")
                except ValueError as error:
                    self.send(json.dumps({"error": str(error)}).encode(), "application/json", 400)
                except (OSError, RuntimeError, KeyError):
                    self.send(b'{"error":"Opportunity data unavailable. Run opportunity.py --build once."}',
                              "application/json", 502)
                return
            if route.path == "/api/site/preflight":
                try:
                    property_id = params.get("property_id", [""])[0]
                    if not property_id.isdigit():
                        raise ValueError("Give a CoStar property_id.")
                    body = venture_review.site_preflight(int(property_id), args.kit)
                    self.send(json.dumps(body, default=str).encode(), "application/json")
                except ValueError as error:
                    self.send(json.dumps({"error": str(error)}).encode(), "application/json", 400)
                except (OSError, RuntimeError, KeyError):
                    self.send(b'{"error":"Building check unavailable. Check the kit."}', "application/json", 502)
                return
            if route.path == "/api/places":
                q = params.get("q", [""])[0].strip()[:80]
                listed = {b["property_id"]: b for b in opportunity.load_market(args.kit)}
                rows = lookup(properties.values(), q) if len(q) >= 2 else []
                out = []
                for row in rows[:40]:
                    pid = int(row["PropertyId"]) if row["PropertyId"].isdigit() else None
                    b = listed.get(pid)
                    out.append({"property_id": pid, "address": row["Address"], "listed_spaces": len(b["spaces"]) if b else 0})
                out.sort(key=lambda r: -r["listed_spaces"])
                self.send(json.dumps({"query": q, "places": out[:12], "matches": len(rows)}).encode(), "application/json")
                return
            if route.path == "/api/nessie/account":
                try:
                    import suite_nessie
                    self.send(json.dumps(suite_nessie.read(params.get("id", [""])[0] or None)).encode(), "application/json")
                except (RuntimeError, OSError, ValueError, KeyError) as error:
                    self.send(json.dumps({"error": f"Nessie unavailable: {error}"}).encode(), "application/json", 502)
                return
            if route.path == "/api/signal-guide":
                import signal_guide
                self.send(json.dumps(signal_guide.guide(), default=str).encode(), "application/json")
                return
            if route.path == "/api/neighborhood/industries":
                self.send(json.dumps(neighborhood.industry_catalog()).encode(), "application/json")
                return
            if route.path == "/api/neighborhood":
                try:
                    use = params.get("use", ["indoor pickleball"])[0].strip()
                    if not 2 <= len(use) <= 80:
                        raise ValueError("Describe the business in 2-80 characters, or use 'suggest'.")
                    property_id = params.get("property_id", [""])[0]
                    address = params.get("address", [""])[0].strip()
                    if not (property_id.isdigit() or 5 <= len(address) <= 200):
                        raise ValueError("Give a CoStar property_id or a street address.")
                    suite = params.get("suite", [""])[0].strip()[:80] or None
                    body = neighborhood.investigate(use, address or None, int(property_id) if property_id else None,
                                                    kit=args.kit, explain=params.get("explain", ["0"])[0] == "1",
                                                    suite=suite)
                    self.send(json.dumps(body, default=str).encode(), "application/json")
                except ValueError as error:
                    self.send(json.dumps({"error": str(error)}).encode(), "application/json", 400)
                except (OSError, RuntimeError, KeyError):
                    self.send(b'{"error":"Neighborhood check unavailable. Check the kit and the cache."}',
                              "application/json", 502)
                return
            if route.path == "/api/maximo/suites":
                try:
                    entry = location_properties[params.get("id", [""])[0]]
                    suites = suite_options(args.kit, int(entry["id"]), password)
                    self.send(json.dumps(suites).encode(), "application/json")
                except KeyError:
                    self.send(b'{"error":"Unknown property."}', "application/json", 404)
                except (OSError, RuntimeError, ValueError):
                    self.send(b'{"error":"Suite lookup unavailable."}', "application/json", 502)
                return
            if route.path == "/location-demo":
                self.send((ROOT / "static/location-demo.html").read_bytes(), "text/html; charset=utf-8")
                return
            if route.path == "/api/location/properties":
                rows = sorted(location_properties.values(), key=lambda row: (row["city"], row["address"]))
                self.send(json.dumps(rows).encode(), "application/json")
                return
            assets = {"/static/location-demo.js": "text/javascript","/static/pilot.css": "text/css", "/static/pilot.js": "text/javascript",
                      "/static/workspace.css": "text/css", "/static/workspace.js": "text/javascript", "/static/space-fit.js": "text/javascript", "/static/maximo.js": "text/javascript",
                      "/static/maximo.css": "text/css", "/static/market-rank.js": "text/javascript",
                      "/static/neighborhood.js": "text/javascript", "/static/neighborhood.css": "text/css",
                      "/static/suite.css": "text/css", "/static/suite.js": "text/javascript",
                      "/static/suite3d.js": "text/javascript",
                      "/static/flow.css": "text/css", "/static/flow.js": "text/javascript",
                      "/static/vendor/gsap.min.js": "text/javascript", "/static/vendor/ScrollTrigger.min.js": "text/javascript",
                      "/static/vendor/lenis.min.js": "text/javascript", "/static/vendor/three.min.js": "text/javascript"}
            if route.path in assets:
                self.send((ROOT / route.path.lstrip("/")).read_bytes(), assets[route.path])  # whitelisted paths only
                return
            if route.path == "/api/location/tanner":
                try:
                    path = ROOT / "output" / "location-tanner.json"
                    report = json.loads(path.read_text())
                    if report.get("property_id") != 23296 or report.get("proposed_use") != "indoor pickleball":
                        raise ValueError("Report belongs to another scenario")
                    # Return only accepted claims, gaps, and evidence references.
                    body = {key: report[key] for key in ("findings", "unknowns", "validation_issues")}
                    body["sources"] = [
                        {key: item.get(key) for key in
                         ("source_id", "fact", "evidence_url", "captured_at", "note")}
                        for item in report["evidence"]
                    ]
                    self.send(json.dumps(body).encode(), "application/json")
                except (OSError, ValueError, KeyError, TypeError):
                    self.send(b'{"error":"No saved Location & Demand review for this scenario."}',
                              "application/json", 404)
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
            if route.path == "/api/deal":
                try:
                    number = lambda name: float(params[name][0]) if params.get(name, [""])[0] else None  # noqa: E731
                    capital, square_feet = number("capital"), number("square_feet")
                    if capital is not None and not 0 <= capital <= 1e10:
                        raise ValueError("capital must be between 0 and 10,000,000,000")
                    body = deal_for(int(params.get("property_id", [""])[0]), capital,
                                    params.get("suite", [""])[0], square_feet)
                    self.send(json.dumps(body).encode(), "application/json")
                except ValueError as exc:
                    self.send(json.dumps({"error": str(exc)}).encode(), "application/json", 400)
                except (KeyError, OSError, RuntimeError) as exc:
                    self.send(json.dumps({"error": str(exc)}).encode(), "application/json", 502)
                return
            if route.path == "/api/space-fit/rank":
                try:
                    body = rank_for(int(params.get("property_id", [""])[0]), params.get("suite", [""])[0])
                    self.send(json.dumps(body).encode(), "application/json")
                except ValueError as exc:
                    self.send(json.dumps({"error": str(exc)}).encode(), "application/json", 400)
                except (KeyError, OSError, RuntimeError) as exc:
                    self.send(json.dumps({"error": str(exc)}).encode(), "application/json", 502)
                return
            if route.path == "/api/space-fit":
                try:
                    property_id = int(params.get("property_id", [""])[0])
                    use = params.get("use", [""])[0]
                    if use not in USES:
                        raise ValueError(f"use must be one of {', '.join(USES)}")
                    requirements = tuple(sorted((k, v[0]) for k, v in params.items() if k in REQUIREMENTS))
                    body = fit_for(property_id, use, params.get("suite", [""])[0], requirements,
                                   params.get("label", [""])[0])
                    self.send(json.dumps(body).encode(), "application/json")
                except ValueError as exc:
                    self.send(json.dumps({"error": str(exc)}).encode(), "application/json", 400)
                except (KeyError, OSError, RuntimeError) as exc:
                    self.send(json.dumps({"error": str(exc)}).encode(), "application/json", 502)
                return
            query = params.get("q", [""])[0].strip()
            property_id = params.get("id", [""])[0]
            model = params.get("model", [""])[0]
            if route.path == "/aerial" and property_id in location_properties:
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
