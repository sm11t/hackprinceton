"""Finance lab: run the existing Stage 4 money engine on any listed space x any of the 26 businesses, with editable
inputs, and show exactly what it computed.

Nothing here is a new financial model. It calls the same functions /suite and /flow use:
  venture_review.find_space        which listed space (Houston or Los Angeles kit)
  venture_costs.rent_for           asking rent, else rent-model estimate, else unknown
  neighborhood.building_fit        can the building host the business (warnings only)
  venture_costs.cash_to_open       sourced opening-cost ledger, low/base/high, affordability
  venture_review.cash_months       12 months of cash, zero revenue (nessie_pilot.simulate)
  nessie_loan.payment / schedule / with_loan
The financed series repeats cash_months' scenario with the loan applied (test_finance_lab checks the cash-only path
matches cash_months exactly). Running a scenario never creates a Nessie loan; create_loan() needs confirm=True.
"""
from __future__ import annotations

import math

MARKETS = {"houston": "Houston, TX", "los_angeles": "Los Angeles, CA"}
NOT_MODELED = ["Revenue", "Payroll after opening", "Utilities", "Other operating expenses after opening", "Profit",
               "Break-even", "Taxes on income"]
DEFAULTS = {"market": "los_angeles", "property_id": 4809147, "budget": 900000.0, "reserve": 50000.0,
            "financing": "cash", "apr": 9.0, "term_months": 60, "delay": 0}
LIMITS = {"budget": (0, 50_000_000), "reserve": (0, 50_000_000), "monthly_rent": (0, 2_000_000),
          "build_months": (0, 36), "delay": (0, 24), "loan_amount": (0, 50_000_000), "apr": (0, 50),
          "term_months": (1, 360)}
INTEGERS = {"build_months", "delay", "term_months"}


def _number(name, raw):
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        raise ValueError(f"{name} must be a number")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number") from None
    low, high = LIMITS[name]
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be between {low:,} and {high:,}")
    if name in INTEGERS:
        if not value.is_integer():
            raise ValueError(f"{name} must be a whole number")
        return int(value)
    return value


def parse(params: dict) -> dict:
    """Validated inputs; anything not given falls back to DEFAULTS or to the engine's own value (None)."""
    if not isinstance(params, dict):
        raise ValueError("Send a JSON object of inputs")
    out = {**DEFAULTS}
    market = params.get("market", out["market"])
    if market not in MARKETS:
        raise ValueError("market must be houston or los_angeles")
    out["market"] = market
    pid = params.get("property_id", out["property_id"])
    if not str(pid).isdigit():
        raise ValueError("property_id must be a CoStar property id")
    out["property_id"] = int(pid)
    out["suite"] = params.get("suite") or None
    out["business"] = params.get("business")
    if not out["business"]:
        raise ValueError("Choose a business")
    for name in ("budget", "reserve", "monthly_rent", "build_months", "delay", "loan_amount", "apr", "term_months"):
        value = _number(name, params.get(name))
        if value is not None:
            out[name] = value
        elif name not in out:
            out[name] = None
    out["financing"] = params.get("financing", out["financing"])
    if out["financing"] not in ("cash", "loan"):
        raise ValueError("financing must be cash or loan")
    out["nessie_account"] = params.get("nessie_account") or None
    out["use_nessie_balance"] = params.get("use_nessie_balance") is True
    return out


def businesses():
    from neighborhood_industries import INDUSTRIES
    from venture_costs import costs
    data = costs()
    rows = []
    for key, spec in INDUSTRIES.items():
        c = data.get(key) or {}
        rows.append({"key": key, "label": spec["label"], "group": spec.get("group"),
                     "cost_benchmark": bool(c) and c.get("comparable", True),
                     "benchmark_source": ((c.get("sources") or [{}])[0]).get("publisher_or_brand"),
                     "typical_sf": c.get("typical_sf"), "build_months": c.get("build_months")})
    return rows


def options(market="houston", kit=None):
    """Listed properties in one market and the 26 businesses, straight from the kit and the registry."""
    from opportunity import load_market
    from venture_costs import rent_for
    if market not in MARKETS:
        raise ValueError("market must be houston or los_angeles")
    props = []
    for b in load_market(kit, market):
        spaces = []
        for s in b["spaces"]:
            rent = rent_for(s)
            spaces.append({"value": s["value"], "suite": s.get("suite"), "floor": s.get("floor"), "sf": s.get("sf"),
                           "monthly_rent": rent["monthly"], "rent_kind": rent["kind"], "rent_source": rent["source"]})
        props.append({"property_id": b["property_id"], "address": b.get("address"),
                      "type": (b.get("facts") or {}).get("type"), "spaces": spaces})
    props.sort(key=lambda p: p["address"] or "")
    return {"market": market, "label": MARKETS[market], "properties": props, "businesses": businesses()}


def _series(cost, buyer, start, reserve, delay):
    """cash_months' scenario (opening costs up front minus the build-rent line, rent billed monthly), any buyer."""
    from nessie_pilot import simulate
    lines = cost.get("lines") or []
    building = next((l for l in lines if l["label"].startswith("Rent while you build")), None)
    build_months = cost.get("build_months") or 3
    out = {}
    for case in ("low", "base", "high"):
        upfront = cost["cash_to_open"][case] - (building[case] if building else 0)
        scenario = {"name": case, "upfront_cost": upfront, "permit_months": build_months, "build_months": 0,
                    "build_cost": 0, "monthly_income": 0}
        run = simulate(scenario, buyer, 12, reserve)
        late = simulate(scenario, buyer, 12, reserve, permit_delay=delay)
        out[case] = {"cash": [round(start)] + [r["cash"] for r in run["rows"]],
                     "outflows": [r["outflow"] for r in run["rows"]],
                     "first_month_below_reserve": run["first_month_below_reserve"],
                     "first_month_below_zero": next((r["month"] for r in run["rows"] if r["cash"] < 0), None),
                     "opens": run["opening_month"], "opens_if_delayed": late["opening_month"],
                     "upfront": round(upfront)}
    return out


def run(params: dict, kit=None) -> dict:
    import neighborhood as nb
    import nessie_loan
    from neighborhood_industries import INDUSTRIES
    from venture_costs import cash_to_open, flip, rent_for
    from venture_review import cash_months, find_space

    p = parse(params)
    key = p["business"] if p["business"] in INDUSTRIES else nb.resolve(p["business"])[0]
    if not key:
        raise ValueError(f"Could not match '{p['business']}' to one of the 26 business types")
    building, space = find_space(p["property_id"], p["suite"], kit, key)
    if not building or not space:
        raise ValueError("This property has no active lease listing in the kit")
    facts = building.get("facts") or {}
    inputs, warnings = {}, []

    # Rent: listing, else model estimate, else unknown; a typed value overrides and is labelled as the user's.
    listed = rent_for(space)
    if p["monthly_rent"] is not None:
        rent = {"monthly": p["monthly_rent"], "kind": "user", "source": "Entered by you (overrides the listing)"}
    else:
        rent = listed
    inputs["monthly_rent"] = {"value": rent["monthly"], "source": rent["source"], "kind": rent["kind"]}
    if rent["monthly"] is None:
        warnings.append("No asking rent and no confident estimate: rent is unknown, so the 12-month view is "
                        "unavailable. Enter a rent to test one (it will be labelled as yours).")

    # Bank: Nessie bills are charged monthly; the balance is the budget only if explicitly chosen.
    bank, bills, cash_source = None, [], "Entered budget"
    if p["nessie_account"]:
        try:
            import suite_nessie
            bank = suite_nessie.read(p["nessie_account"])
            bills = bank.get("bills") or []
            if p["use_nessie_balance"]:
                p["budget"] = float(bank["balance"])
                cash_source = f"{bank['source']} balance"
        except Exception as error:  # noqa: BLE001 - Nessie trouble never blocks a run
            warnings.append(f"Nessie account unavailable ({type(error).__name__}); ran without its bills.")
            bank = None
    inputs["budget"] = {"value": p["budget"], "source": cash_source, "kind": "nessie" if "Nessie" in cash_source else "user"}
    inputs["reserve"] = {"value": p["reserve"], "source": "Entered by you", "kind": "user"}
    inputs["bills"] = {"value": bills, "source": (bank or {}).get("source") or "none", "kind": "nessie" if bills else "none"}

    fit = nb.building_fit(key, facts, space["value"])
    if fit["status"] == "no":
        warnings.append("Building fit: NO. " + "; ".join(fit.get("reasons") or []))
    elif fit["status"] == "check":
        warnings.append("Building fit: needs a check. " + "; ".join((fit.get("reasons") or fit.get("unknowns") or [])[:3]))
    if p["market"] != (building.get("market") or "houston"):
        warnings.append(f"Property {p['property_id']} is in {building.get('market')}, not {p['market']}.")

    btype = facts.get("type")
    cost = cash_to_open(key, space["sf"], rent["monthly"], budget=p["budget"], reserve=p["reserve"],
                        build_months=p["build_months"], building_type=btype)
    if not cost["lines"]:
        warnings.append(cost.get("note") or "No comparable opening-cost benchmark for this business.")
    inputs["build_months"] = {"value": cost.get("build_months"), "kind": "user" if p["build_months"] is not None else "assumption",
                              "source": "Entered by you" if p["build_months"] is not None else
                              "Benchmark build time (default 3 months), an assumption"}
    delayed = (cash_to_open(key, space["sf"], rent["monthly"], budget=p["budget"], reserve=p["reserve"],
                            build_months=(cost.get("build_months") or 3) + p["delay"], building_type=btype)
               if p["delay"] else None)

    base_need = (cost.get("required") or {}).get("base")
    capital = {"cash_to_open": cost.get("cash_to_open"), "required_with_reserve": cost.get("required"),
               "budget": p["budget"], "reserve": p["reserve"], "affordability": cost.get("affordability"),
               "headroom_base": cost.get("headroom"),
               "funding_gap_base": None if base_need is None else max(0, round(base_need - p["budget"])),
               "flip": flip(cost, p["budget"]),
               "delayed_required": (delayed or {}).get("required"),
               "explain": "required = sum of ledger lines (low/base/high) + reserve; gap = required(base) - budget"}

    # 12 months, cash only: the same function /suite and /flow use.
    twelve = cash_months(cost, rent, p["budget"], p["reserve"], delay=p["delay"] or 3, extra_bills=bills,
                         cash_source=cash_source)
    cash_only = None
    if twelve:
        buyer = {"starting_cash": p["budget"], "recurring_bills": [{"payee": "Base rent", "monthly": rent["monthly"]}]
                 + [{"payee": b["payee"], "monthly": b["monthly"]} for b in bills], "source": cash_source}
        cash_only = {"cases": _series(cost, buyer, p["budget"], p["reserve"], p["delay"] or 3),
                     "monthly_bills": buyer["recurring_bills"], "engine": twelve["engine"], "note": twelve["note"]}

    # Loan: a proposed scenario only. Default principal = the gap nessie_loan.plan would borrow.
    loan = None
    if p["financing"] == "loan" and cost.get("cash_to_open", {}).get("base") is not None:
        suggested = nessie_loan.plan(cost["cash_to_open"]["base"], p["budget"], p["reserve"], p["apr"], p["term_months"])
        amount = p["loan_amount"] if p["loan_amount"] is not None else suggested["amount"]
        pay = nessie_loan.payment(amount, p["apr"], p["term_months"])
        sched = nessie_loan.schedule(amount, p["apr"], p["term_months"])
        loan = {"status": "proposed (not created in Nessie)", "amount": amount,
                "amount_source": "Entered by you" if p["loan_amount"] is not None else
                "Suggested: the gap to cover base cash to open + reserve, rounded up to $5k (nessie_loan.plan)",
                "suggested_amount": suggested["amount"], "apr": p["apr"], "term_months": p["term_months"],
                "monthly_payment": round(pay, 2), "interest_12m": round(sum(r["interest"] for r in sched), 2),
                "principal_12m": round(sum(r["principal"] for r in sched), 2),
                "principal_remaining_12m": sched[-1]["balance_left"] if sched else amount, "schedule": sched,
                "label": nessie_loan.LABEL,
                "explain": "payment = P*r/(1-(1+r)^-n), r = APR/12; proceeds added to cash at month 0, payment billed monthly"}
        if amount and twelve:
            funded = nessie_loan.with_loan(buyer, {"amount": amount, "apr": p["apr"], "term_months": p["term_months"],
                                                   "monthly_payment": round(pay, 2)})
            loan["cases"] = _series(cost, funded, p["budget"] + amount, p["reserve"], p["delay"] or 3)
        elif amount == 0:
            loan["note"] = "No loan needed: cash covers base cost to open plus the reserve."

    return {"inputs": p, "business": {"key": key, "label": INDUSTRIES[key]["label"]},
            "property": {"property_id": building["property_id"], "address": building.get("address"),
                         "market": building.get("market") or "houston", "type": btype,
                         "space": {k: space.get(k) for k in ("value", "suite", "floor", "sf", "listing_id", "space_id")}},
            "provenance": inputs, "building_fit": {k: fit.get(k) for k in ("status", "reasons", "unknowns", "capacity")},
            "ledger": {"lines": cost.get("lines"), "sources": cost.get("sources"), "basis_quality": cost.get("basis_quality"),
                       "note": cost.get("note"), "franchise_fee_excluded": cost.get("franchise_fee_excluded")},
            "capital": capital, "cash_only": cash_only, "loan": loan,
            "unavailable": [] if cash_only else ["12-month cash view (rent unknown or no cost benchmark)"],
            "not_modeled": NOT_MODELED, "warnings": warnings,
            "reading": "Zero-revenue runway: how long cash lasts paying opening costs, rent and bills. "
                       "It is not a profitability forecast."}


def create_loan(body: dict) -> dict:
    """Store a proposed loan in the Nessie sandbox. Requires confirm=True; never called by run()."""
    import nessie_loan
    if not isinstance(body, dict) or body.get("confirm") is not True:
        raise ValueError("Creating a sandbox loan needs confirm: true")
    account = body.get("account_id")
    if not account or not str(account).replace("-", "").isalnum():
        raise ValueError("Give the Nessie sandbox account_id")
    amount = _number("loan_amount", body.get("amount"))
    apr = _number("apr", body.get("apr"))
    term = _number("term_months", body.get("term_months"))
    if not amount or apr is None or not term:
        raise ValueError("Give amount, apr and term_months")
    return nessie_loan.create(str(account), amount, apr, term)
