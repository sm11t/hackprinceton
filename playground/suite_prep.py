"""Get a laptop demo-ready for /suite, then prove the demo path works with no network.

    ~/.local/bin/python3.12 playground/with_env.py ~/.local/bin/python3.12 playground/suite_prep.py \
        --kit ~/Downloads/costar-hackathon-kit.zip [--live-research] [--ventures]

1. Online (once): loads or builds the opportunity index, runs the $500k scan, and reviews every demo pair so the
   jurisdiction lookups (Census geocoder) are cached. --live-research also caches the compliance engine's official
   permit pages (Tavily, team key from .env) for those pairs.
2. Offline: sets NEIGHBORHOOD_OFFLINE=1 and JURISDICTION_OFFLINE=1 and reruns the scan and every review from the
   caches only, checking each verdict and that the jurisdiction is still verified. Prints PASS / FAIL per pair.
   Run suite_nessie.py --seed once online to create the Capital One Nessie sandbox persona the demo reads.
3. --ventures: (re)creates the "Demo:" ventures saved at each stage, so a reload or a crash recovers to any step.
4. --warm-server http://127.0.0.1:8765: requests the scan and every demo review from the running server, so the
   first click on stage is instant (the first read of the kit takes seconds).

Before judging, with the server running:
    ~/.local/bin/python3.12 playground/with_env.py ~/.local/bin/python3.12 playground/suite_prep.py \
        --offline-only --warm-server http://127.0.0.1:8765

Prints no keys or passwords. Writes only to playground/output/ (gitignored).
"""
import argparse
import importlib
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# (label, business, property_id, suite, budget, reserve, expected verdict)
DEMO = [
    ("Salon, 11220 Louetta Rd", "salon_barber", 6017645, "listing:40882536:1200", 500000, 50000, "GO"),
    ("Cafe, 11220 Louetta Rd", "cafe", 6017645, "listing:40882536:1200", 500000, 50000, "GO"),
    ("Physical therapy, 520 Post Oak Blvd", "physical_therapy", 239634, "625", 500000, 50000, "GO"),
    ("Vet, 3330 Audley St", "veterinary", 235044, "B", 500000, 50000, "GO"),
    ("Gym, 14405 Walters Rd (unincorporated Harris)", "fitness_gym", 237365, "140", 500000, 50000, "CONDITIONAL"),
    ("Childcare, 9700 Tanner Rd suite A ($750k)", "childcare", 23296, "A", 750000, 50000, "CONDITIONAL"),
    ("Pickleball, 6855 Wynnwood Ln", "indoor_pickleball", 13890701, None, 500000, 50000, "NO-GO"),
]
# "I have a space": the building check (Jayant's preflight) before any business
SITES = [("9721 Cypresswood Dr (residential, unincorporated Harris)", 966604, False, "harris_unincorporated"),
         ("11220 Louetta Rd", 6017645, True, "houston"), ("14405 Walters Rd", 237365, True, "harris_unincorporated")]
FUNNEL = {"combinations": 61620, "building_can_host": 13263, "affordable": 7399, "neighborhood_support": 1265}


def run(kit, offline):
    import neighborhood
    import opportunity
    import venture_review
    for module in (neighborhood, opportunity, venture_review):  # clear in-process caches between the two passes
        for name in dir(module):
            fn = getattr(module, name)
            if hasattr(fn, "cache_clear"):
                fn.cache_clear()
    ok = True
    started = time.perf_counter()
    scan = opportunity.scan(500000, 50000, kit, top=20)
    got = {k: scan["funnel"][k] for k in FUNNEL}
    same = got == FUNNEL
    ok &= same
    print(f"  {'PASS' if same else 'CHANGED'}  scan $500k/$50k: {got} ({time.perf_counter() - started:.1f}s)")
    reviews = {}
    for label, business, pid, suite, budget, reserve, want in DEMO:
        t = time.perf_counter()
        try:
            r = venture_review.review(business, pid, suite, budget, reserve, kit)
        except Exception as error:  # noqa: BLE001  report and keep checking the rest
            ok = False
            print(f"  FAIL  {label}: {type(error).__name__}: {error}")
            continue
        jur = r.get("jurisdiction") or {}
        good = r["verdict"] == want and jur.get("verified")
        ok &= bool(good)
        steps = {s["agent"]: s["status"] for s in r["trace"]}
        broken = [a for a, st in steps.items() if st != "ok"]
        print(f"  {'PASS' if good else 'FAIL'}  {label}: {r['verdict']} (want {want}), jurisdiction "
              f"{jur.get('code') or 'NOT VERIFIED'}, {len(r['because'])} reasons, "
              f"{sum(len(s.get('findings', [])) for s in r['trace'])} findings, {time.perf_counter() - t:.1f}s"
              + (f"; steps not ok: {broken}" if broken else ""))
        reviews[(business, pid)] = r
    for label, pid, cont, code in SITES:
        try:
            s = venture_review.site_preflight(pid, kit)
            good = s["can_continue"] == cont and s["jurisdiction"].get("code") == code
        except Exception as error:  # noqa: BLE001
            s, good = {"stops": [f"{type(error).__name__}: {error}"]}, False
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  building check {label}: "
              + ("continues" if s.get("can_continue") else "stops: " + "; ".join(s.get("stops", []))[:90]))
    for label, kwargs in (("one business (yoga)", {"include": ["yoga_pilates"]}),
                          ("one building (11220 Louetta)", {"property_ids": {6017645}})):
        o = opportunity.scan(500000, 50000, kit, top=20, **kwargs)
        good = o["funnel"]["neighborhood_support"] > 0
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  scan for {label}: {o['funnel']['authority_identified']} pass every gate")
    return ok, scan, reviews


def demo_ventures(scan, reviews):
    import ventures
    for v in ventures.all_for("demo"):
        if v["name"].startswith("Demo:"):
            ventures.delete("demo", v["id"])
    pairs = {(p["business"], p["property_id"]): p for d in scan["directions"] for p in d["pairs"]}
    pairs.update({(p["business"], p["property_id"]): p for p in scan["pairs"]})

    def entry(business, pid, suite, label):
        p = pairs.get((business, pid))
        if p:
            return {k: p[k] for k in ("business", "label", "group", "property_id", "suite", "suite_label", "address",
                                      "sf", "lat", "lon")} | {"building": {"reasons": p["building"]["reasons"]}}
        r = reviews[(business, pid)]  # not in the scan's top pairs (e.g. over budget): take it from the review
        sf = r["space"].get("sf")
        return {"business": business, "label": r["label"], "group": r["group"], "property_id": pid,
                "suite": r["suite"], "suite_label": (f"Suite {r['space']['suite']}" if r["space"].get("suite")
                                                     else f"{sf:,.0f} sq ft space" if sf else "listed space"),
                "address": r["address"], "sf": sf, "lat": r["lat"], "lon": r["lon"], "building": {"reasons": []}}
    short = [entry("salon_barber", 6017645, "listing:40882536:1200", ""),
             entry("physical_therapy", 239634, "625", ""),
             entry("indoor_pickleball", 13890701, None, "")]
    base = {"budget": 500000, "reserve": 50000, "area": {"mode": "anywhere", "radius": 10}, "exclude": [],
            "directions": ["salon_barber", "physical_therapy", "cafe"]}
    try:  # Capital One Nessie sandbox persona: its balance is the budget, its bills feed the 12-month view
        import suite_nessie
        a = suite_nessie.read()
        base["nessie"] = {k: a[k] for k in ("account_id", "balance", "monthly_bills", "retrieved_at", "cached")}
        print(f"  Nessie account …{a['account_id'][-6:]}: ${a['balance']:,.0f}, ${a['monthly_bills']:,.0f}/mo bills"
              + (" (cached)" if a["cached"] else ""))
    except Exception as error:  # noqa: BLE001
        print(f"  Nessie unavailable ({type(error).__name__}): ventures saved without it")
    stages = ["budget", "scan", "opportunities", "shortlist", "investigate", "decide"]
    made = []
    for i, stage in enumerate(stages):  # created oldest first so the list reads in demo order, newest on top
        v = ventures.create("demo", "budget", f"Demo: $500k, {stage}")
        ventures.update("demo", v["id"], {"stage": stage, "status": "investigating" if i >= 4 else "exploring",
                                          "inputs": base | {"reached": i},
                                          "shortlist": short if i >= 3 else []})
        made.append((stage, v["id"]))
    # the other three starting points (one toolkit, different order)
    salon = entry("salon_barber", 6017645, "listing:40882536:1200", "")
    louetta = {"property_id": 6017645, "address": salon["address"], "lat": salon.get("lat"), "lon": salon.get("lon")}
    extra = [
        ("idea", "Demo: I know what to open (yoga), scan", "scan",
         {**base, "business": "yoga_pilates", "businessLabel": "Yoga / pilates studio", "directions": ["yoga_pilates"],
          "directionLabels": ["Yoga / pilates studio"], "reached": 1}, []),
        ("space", "Demo: I have a space (11220 Louetta), building check", "scan",
         {**base, "place": louetta, "reached": 1}, []),
        ("space", "Demo: I have a space (Cypresswood), building check", "scan",
         {**base, "place": {"property_id": 966604, "address": "9721 Cypresswood Dr"}, "reached": 1}, []),
        ("both", "Demo: I know what and where (PT, 520 Post Oak), investigate", "investigate",
         {**base, "business": "physical_therapy", "businessLabel": "Physical therapy / chiropractic",
          "directions": ["physical_therapy"], "place": {"property_id": 239634, "address": "520 Post Oak Blvd"},
          "suite": "625", "reached": 1}, [entry("physical_therapy", 239634, "625", "")]),
    ]
    for kind, name, stage, inputs, short_list in extra:
        v = ventures.create("demo", kind, name)
        ventures.update("demo", v["id"], {"stage": stage, "status": "investigating" if stage == "investigate" else
                                          "exploring", "inputs": inputs, "shortlist": short_list})
        made.append((f"{stage} ({kind})", v["id"]))
    v = ventures.create("demo", "budget", "Demo: $750k childcare, investigate")
    ventures.update("demo", v["id"], {"stage": "investigate", "status": "investigating",
                                      "inputs": {**base, "budget": 750000, "directions": ["childcare"], "reached": 4},
                                      "shortlist": [entry("childcare", 23296, "A", "")]})
    made.append(("investigate $750k", v["id"]))
    for stage, vid in made:
        print(f"  /suite#/v/{vid}/{stage.split()[0]}  ({stage})")


def warm_server(base):
    import json
    from urllib.parse import urlencode
    from urllib.request import urlopen
    ok = True
    for path in ["/api/opportunities?" + urlencode({"budget": 500000, "reserve": 50000, "top": 20}),
                 "/api/signal-guide", "/api/neighborhood/industries",
                 "/api/opportunities?" + urlencode({"budget": 500000, "reserve": 50000, "top": 20, "include": "yoga_pilates"}),
                 "/api/opportunities?" + urlencode({"budget": 500000, "reserve": 50000, "top": 20, "property_id": 6017645})] + [
            f"/api/site/preflight?property_id={pid}" for _, pid, _, _ in SITES] + [
            "/api/venture/review?" + urlencode({k: v for k, v in (("business", b), ("property_id", pid),
                                                                  ("suite", suite or ""), ("budget", budget),
                                                                  ("reserve", reserve))})
            for _, b, pid, suite, budget, reserve, _ in DEMO]:
        t = time.perf_counter()
        try:
            with urlopen(base + path, timeout=120) as response:
                body = json.loads(response.read())
            note = body["verdict"] if isinstance(body, dict) and isinstance(body.get("verdict"), str) else "ok"
        except Exception as error:  # noqa: BLE001
            ok, note = False, f"FAIL {type(error).__name__}: {error}"
        print(f"  {time.perf_counter() - t:5.1f}s  {path.split('?')[0]} {note}")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kit", default=os.path.expanduser("~/Downloads/costar-hackathon-kit.zip"))
    parser.add_argument("--live-research", action="store_true", help="also cache official permit pages (Tavily)")
    parser.add_argument("--ventures", action="store_true", help="recreate the Demo: ventures at each stage")
    parser.add_argument("--offline-only", action="store_true", help="skip the online warm-up pass")
    parser.add_argument("--warm-server", metavar="URL", help="warm a running web.py (e.g. http://127.0.0.1:8765)")
    args = parser.parse_args()
    if not args.offline_only:
        print("1. Online warm-up (caches jurisdiction lookups" + (" and official permit pages" if args.live_research
                                                               else "") + ")")
        if args.live_research:
            os.environ["COMPLIANCE_LIVE"] = "1"
        run(args.kit, offline=False)
        os.environ.pop("COMPLIANCE_LIVE", None)
    print("2. Offline replay (NEIGHBORHOOD_OFFLINE=1, JURISDICTION_OFFLINE=1)")
    os.environ["NEIGHBORHOOD_OFFLINE"] = "1"
    os.environ["JURISDICTION_OFFLINE"] = "1"
    importlib.invalidate_caches()
    ok, scan, reviews = run(args.kit, offline=True)
    if args.ventures:
        print("3. Demo ventures (user 'demo')")
        demo_ventures(scan, reviews)
    if args.warm_server:
        print(f"4. Warming {args.warm_server}")
        ok &= warm_server(args.warm_server.rstrip("/"))
    print("READY: every demo pair replays offline." if ok else "NOT READY: see FAIL / CHANGED lines above.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
