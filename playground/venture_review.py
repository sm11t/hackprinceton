"""Deep review of one business in one listed space, for any of the 26 businesses (venture Stage 5).

A traced team of agents, the same trace shape as the neighborhood check:

  building      can this space host it? (neighborhood.building_fit)
  neighborhood  does the area support it? (neighborhood.investigate, all demand specialists)
  money         itemized cash to open from sourced benchmarks, scaled to this space; reserve; months of rent
                left after opening with zero revenue; what-if: opening delay
  deal          asking rent vs the rent model's range for this space; lease basis
  records       do CoStar and the linked scans agree? (address, suite, size, scan dates)
  permits       Houston's change-of-use path plus the business-specific licenses (official sources)
  verdict       GO / CONDITIONAL / NO-GO with the deciding reason, conditions and what would flip it

Everything is computed in code from cached data; the review never forecasts revenue.
"""
import json
import time
from functools import lru_cache
from pathlib import Path

import neighborhood as nb
from neighborhood_industries import INDUSTRIES
from reconcile import record

HOUSTON_STEPS = [  # Houston process (approvals_timeline.REFERENCES), applied to every business
    ("Allowed use and deed restrictions", "Houston has no conventional zoning, but recorded deed restrictions and "
     "development rules (parking, access) can limit a use. Ask the landlord and check the deed restrictions.",
     "houston-deeds"),
    ("Certificate of Occupancy (change of use)", "Houston requires a Certificate of Occupancy for a commercial lease "
     "space and for a change in occupancy classification. Retrieve the current CO and ask whether this use changes it.",
     "houston-occupancy"),
    ("Building, fire and accessibility review", "Plans for build-out, exits, accessible route and restrooms, fire "
     "protection and signage go through permit review; trade permits follow.", "houston-occupancy"),
    ("Final inspections and occupancy", "Final sign-offs before opening.", "houston-occupancy"),
]


def licenses_for(key):
    try:
        from venture_license_data import LICENSES
    except ImportError:
        return []
    return LICENSES.get(key, [])


@lru_cache(maxsize=256)
def property_record(property_id, kit=""):
    """The full CoStar property record (cached on disk: reading the encrypted zip is slow)."""
    path = nb.CACHE / "property-records" / f"{property_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    from space_fit import load_property
    kit_file = Path(kit) if kit else nb.kit_path()
    import os
    prop = load_property(kit_file, int(property_id), os.environ.get("COSTAR_KIT_PASSWORD", "").encode() or None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prop))
    return prop


def step(trace, agent, role, fn):
    """Run one review agent and record it in the trace (inputs are the review's)."""
    started = time.perf_counter()
    entry = {"agent": agent, "role": role, "computed_by": "code", "inputs": {}, "sources": [], "findings": [],
             "summary": "", "confidence": None, "handoff": "", "signal": None, "per_industry": {}, "status": "ok"}
    try:
        entry.update(fn() or {})
    except nb.Offline as error:
        entry.update(status="unknown", summary=f"Offline and not cached: {error}")
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        entry.update(status="error", summary=f"{type(error).__name__}: {error}")
    entry["ms"] = round(1000 * (time.perf_counter() - started))
    trace.append(entry)
    return entry


def find_space(property_id, suite, kit, key=None):
    """The building and the listed space to review: the chosen suite, else the listed space that best suits the
    business's typical size (not the biggest one: costs scale with floor area)."""
    from opportunity import load_market
    building = next((b for b in load_market(kit) if b["property_id"] == int(property_id)), None)
    if not building:
        return None, None
    space = next((s for s in building["spaces"] if s["value"] == suite), None)
    if space is None and building["spaces"]:
        pool = [s for s in building["spaces"] if not s.get("executive_suite")] or building["spaces"]
        need = INDUSTRIES[key]["space"] if key else {}
        lo, hi = need.get("min_sf", 0), need.get("max_sf") or need.get("min_sf", 0) * 3 or 1e12
        target = (lo + hi) / 2
        inside = [s for s in pool if lo <= (s["sf"] or 0) <= hi]
        above = [s for s in pool if (s["sf"] or 0) > hi]
        space = (min(inside, key=lambda s: abs(s["sf"] - target)) if inside else
                 min(above, key=lambda s: s["sf"]) if above else max(pool, key=lambda s: s["sf"] or 0))
    return building, space


def review(business, property_id, suite=None, budget=None, reserve=0.0, kit=None, delay_months=0, explain=False):
    """Full review of `business` (registry key or description) in a listed space."""
    from venture_costs import cash_to_open, flip, rent_estimates, rent_for
    started = time.perf_counter()
    key = business if business in INDUSTRIES else nb.resolve(business)[0]
    if not key:
        raise ValueError(f"Could not match '{business}' to a business type.")
    spec = INDUSTRIES[key]
    building, space = find_space(property_id, suite, kit, key)
    if not building or not space:
        raise ValueError("This property has no active lease listing in the kit.")
    suite = space["value"]
    trace, conditions, blockers = [], [], []

    hood = nb.investigate(key, property_id=int(property_id), kit=kit, suite=suite, explain=explain)
    decision = hood["decisions"][0] if hood["decisions"] else None
    fit = (decision or {}).get("building") or nb.building_fit(key, building["facts"], suite)
    trace.extend(s for s in hood["trace"] if s["agent"] in ("planner", "site", "building"))

    rent = rent_for(space)
    money_holder = {}

    def money():
        btype = building["facts"].get("type")
        cost = cash_to_open(key, space["sf"], rent["monthly"], budget=budget, reserve=reserve, building_type=btype)
        delayed = (cash_to_open(key, space["sf"], rent["monthly"], budget=budget, reserve=reserve, building_type=btype,
                                build_months=cost["build_months"] + delay_months) if delay_months else None)
        stress = cash_to_open(key, space["sf"], rent["monthly"], budget=budget, reserve=reserve, building_type=btype,
                              build_months=cost.get("build_months", 3) + 3)
        money_holder.update(cost=cost, delayed=delayed, stress=stress, flip=flip(cost, budget))
        total = cost["cash_to_open"]
        findings = [record(f"{key}.cash_to_open", total, "computed", "venture_costs", None,
                           0.5 if cost["basis_quality"] == "itemized" else 0.3, None,
                           "agrees" if total["base"] else "unknown",
                           note=f"Low/base/high from {cost['sources'][0]['publisher_or_brand'] if cost['sources'] else 'no source'}"
                                f", scaled to {space['sf']:,.0f} sq ft. {cost['note']}".strip())]
        if budget is not None and cost["required"]["base"] is not None:
            findings.append(record(f"{key}.budget_check", cost["affordability"], "computed", "venture_costs", None,
                                   0.5, None, "agrees" if cost["affordability"] != "unknown" else "unknown",
                                   note=f"Cash to open ${total['base']:,.0f} + reserve ${reserve:,.0f} = "
                                        f"${cost['required']['base']:,.0f} vs budget ${budget:,.0f}."))
        if stress["required"]["base"] is not None and budget is not None:
            findings.append(record(f"{key}.three_month_delay", stress["required"]["base"], "computed", "venture_costs",
                                   None, 0.4, None, "agrees",
                                   note=f"If opening slips 3 months, rent while building adds "
                                        f"${stress['cash_to_open']['base'] - total['base']:,.0f}; affordability "
                                        f"becomes '{stress['affordability']}'."))
        summary = (f"Cash to open ${total['base']:,.0f} (range ${total['low']:,.0f}-${total['high']:,.0f}); "
                   f"{cost['affordability']} for a ${budget:,.0f} budget with ${reserve:,.0f} reserve"
                   + (f"; about {cost['months_of_rent_after_opening']} months of rent left after opening"
                      if cost["months_of_rent_after_opening"] else "")
                   if total["base"] is not None and budget is not None else cost["note"])
        return {"summary": summary, "findings": findings, "confidence": 0.5,
                "sources": [{"name": s["publisher_or_brand"] + " · " + s["document"], "url": s["url"],
                             "retrieved_at": None, "cached": True, "note": s.get("quote", "")} for s in cost["sources"]],
                "handoff": "Cash verdict and the 3-month delay stress to the verdict."}
    step(trace, "money", "What it costs to open here, from sourced opening-cost benchmarks scaled to this space",
         money)

    def deal():
        est = ((rent_estimates() or {}).get("spaces") or {}).get(str(space.get("space_id")))
        findings, summary = [], rent["source"]
        if rent["kind"] == "listed" and est and not est.get("low_confidence"):
            psf = rent["psf_year"]
            where = "inside" if est["low"] <= psf <= est["high"] else "above" if psf > est["high"] else "below"
            findings.append(record("asking_rent_vs_market", psf, "costar", space.get("listing_id"), None, 0.6, None,
                                   "agrees" if where == "inside" else "conflict",
                                   note=f"Asking ${psf:.2f}/sq ft/yr vs ${est['low']:.2f}-${est['high']:.2f} that "
                                        f"similar spaces were asking when they leased ({est['method']})."))
            summary = f"Asking ${psf:.2f}/sq ft/yr ({space['lease_basis']}) is {where} the market range"
        findings.append(record("monthly_base_rent", rent["monthly"], "costar" if rent["kind"] == "listed" else "computed",
                               space.get("listing_id"), space.get("available_on"), 0.6 if rent["kind"] == "listed" else 0.4,
                               None, "agrees" if rent["monthly"] else "unknown",
                               note=rent["source"] + (". A lease is pending on this space." if space.get("lease_pending") else "")
                               + (" NNN: taxes, insurance and common-area costs come on top." if "NNN" in str(space.get("lease_basis")) else "")))
        if space.get("lease_pending"):
            conditions.append("A lease is pending on this space: confirm it is still available.")
        return {"summary": summary, "findings": findings, "confidence": 0.6,
                "handoff": "Rent feeds the money agent; a pending lease becomes a condition."}
    step(trace, "deal", "Is the asking rent fair for this space?", deal)

    def records():
        from reconcile import check_identity, check_scan_dates, check_size, check_suite_identity
        prop = property_record(int(property_id), str(kit or ""))
        rows = check_identity(prop) + check_suite_identity(prop, space.get("suite")) + check_size(prop) + check_scan_dates(prop)
        conflicts = [r for r in rows if r["status"] == "conflict"]
        for r in conflicts[:3]:
            conditions.append(f"Records disagree: {r['note'][:160]}")
        return {"findings": rows, "confidence": 0.7,
                "summary": (f"{len(conflicts)} conflict(s) between CoStar and the linked scans" if conflicts
                            else f"No conflicts in {len(rows)} checks") + f"; {building['tours']} linked tour(s).",
                "handoff": "Conflicts become conditions on the verdict."}
    step(trace, "records", "Do CoStar's record and the linked scans agree?", records)

    def permits():
        from approvals_timeline import REFERENCES
        steps = [{"title": t, "detail": d, "authority": "City of Houston", "url": REFERENCES[ref][1],
                  "status": "to verify"} for t, d, ref in HOUSTON_STEPS]
        licenses = licenses_for(key)
        for lic in licenses:
            steps.insert(-1, {"title": lic["name"], "detail": lic.get("applies_when") or "", "authority": lic["authority"],
                              "url": lic["url"], "status": "to verify"})
        findings = [record(f"{key}.license.{i}", lic["name"], "public:" + lic["authority"], lic["url"], None, 0.7,
                           lic["url"], "agrees", note=f"{lic.get('applies_when') or 'Required'}: \"{lic.get('quote', '')}\"")
                    for i, lic in enumerate(licenses)]
        return {"findings": findings, "steps": steps, "confidence": 0.6,
                "summary": f"{len(steps)} steps: Houston change-of-use path + {len(licenses)} business-specific "
                           "license(s). No timelines are claimed.",
                "sources": [{"name": lic["authority"], "url": lic["url"], "retrieved_at": None, "cached": True,
                             "note": lic["name"]} for lic in licenses],
                "handoff": "Steps go to the plan; none are counted as cleared."}
    permits_step = step(trace, "permits", "What must be approved before opening (Houston + business licenses)?",
                        permits)

    # --- Verdict -------------------------------------------------------------------------
    cost = money_holder.get("cost") or {}
    demand = decision["verdict"] if decision else "unknown"
    afford = cost.get("affordability", "unknown")
    reasons = []
    if fit["status"] == "no":
        blockers.append("The space can't host it: " + "; ".join(r for r in fit["reasons"] if any(
            w in r for w in ("below", "Not a typical", "Residential"))))
    elif fit["status"] == "check":
        conditions.extend(fit["unknowns"])
    if afford == "over":
        blockers.append(f"Cash to open plus reserve (${cost['required']['low']:,.0f} even in the low case) exceeds "
                        f"the ${budget:,.0f} budget")
    elif afford == "stretch":
        conditions.append(f"Only affordable in the low-cost case: base case needs ${cost['required']['base']:,.0f}")
    elif afford == "unknown":
        conditions.append("Cash to open is unknown (no comparable cost benchmark for this business): get quotes")
    elif afford == "rent_unknown":
        conditions.append("The listing has no asking rent: cash excludes the deposit and rent while building; ask the broker")
    for gap in cost.get("unpriced") or []:
        conditions.append(gap)
    if demand == "weak":
        blockers.append("The neighborhood does not look like it supports this business: "
                        + (decision["reasons"][0]["reason"] if decision and decision["reasons"] else ""))
    elif demand in ("mixed", "unknown"):
        conditions.append(f"Neighborhood demand is {demand}: "
                          + (decision["headline"] if decision else "no verdict"))
    verdict = "NO-GO" if blockers else ("GO" if not conditions and demand == "supported" and afford == "within"
                                        and fit["status"] == "fits" else "CONDITIONAL")
    if verdict == "NO-GO":
        reasons = blockers
    elif verdict == "GO":
        reasons = [f"Fits ({fit.get('capacity') or 'size and type'}), affordable with "
                   f"{cost.get('months_of_rent_after_opening')} months of rent to spare, and the neighborhood supports it"]
    else:
        reasons = conditions[:3]
    flips = []
    if money_holder.get("flip"):
        flips.append(money_holder["flip"]["text"])
    if fit["status"] != "fits" and fit.get("unknowns"):
        flips.append("Confirm: " + fit["unknowns"][0])
    if demand == "mixed" and decision:
        unknown = [u["signal"] for u in decision["unknown"]]
        if unknown:
            flips.append("More evidence on " + ", ".join(unknown[:2]) + " could settle demand")
    trace.append({"agent": "verdict", "role": "Combines space, money, demand, records and permits into one call",
                  "computed_by": "code", "inputs": {}, "sources": [], "findings": [], "signal": None,
                  "per_industry": {}, "status": "ok", "confidence": None, "ms": 0,
                  "summary": f"{verdict}: " + (reasons[0] if reasons else ""),
                  "handoff": "Verdict, conditions and next checks to the person."})
    neighborhood_steps = [s for s in hood["trace"] if s["agent"] in ("residents", "competitors", "momentum", "lookalike",
                                                                     "coordinator", "narrator")]
    order = ["planner", "site", "building", "residents", "competitors", "momentum", "lookalike", "coordinator",
             "money", "deal", "records", "permits", "narrator", "verdict"]
    trace = sorted(trace + neighborhood_steps, key=lambda s: order.index(s["agent"]) if s["agent"] in order else 99)
    checks = list(dict.fromkeys(fit.get("unknowns", []) + fit.get("verify", []) + conditions))
    return {
        "business": key, "label": spec["label"], "group": spec["group"],
        "property_id": int(property_id), "address": building["address"], "lat": building["lat"], "lon": building["lon"],
        "suite": suite, "space": {k: space.get(k) for k in ("suite", "sf", "available_on", "lease_basis", "lease_pending")},
        "budget": budget, "reserve": reserve,
        "verdict": verdict, "reasons": reasons, "blockers": blockers, "conditions": conditions, "flips": flips,
        "pillars": {
            "space": {"status": fit["status"], "capacity": fit.get("capacity"), "reasons": fit["reasons"],
                      "unknowns": fit.get("unknowns", []), "verify": fit.get("verify", [])},
            "money": {"affordability": afford, "cash_to_open": cost.get("cash_to_open"), "required": cost.get("required"),
                      "months_of_rent_after_opening": cost.get("months_of_rent_after_opening"),
                      "lines": cost.get("lines"), "sources": cost.get("sources"), "rent": rent,
                      "delay_what_if": money_holder.get("delayed"), "three_month_delay": (money_holder.get("stress") or {}).get("required")},
            "demand": decision,
            "permits": permits_step.get("steps", []),
            "records": [r for r in next((s for s in trace if s["agent"] == "records"), {}).get("findings", [])
                        if r["status"] != "agrees"],
        },
        "checks": checks, "narration": hood.get("narration"), "narration_label": hood.get("narration_label"),
        "trace": trace, "evidence": [r for s in trace for r in s.get("findings", [])],
        "elapsed_ms": round(1000 * (time.perf_counter() - started)),
        "computed_by": "All numbers and verdicts are computed in code. Only the optional summary is LLM-written.",
    }
