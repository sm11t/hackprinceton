"""Join the team checks for one property and one explicitly selected suite."""
from cost_ledger import estimate_costs
from alternatives import CATALOG, rank_alternatives
from decision_context import attach_context
from approvals_timeline import analyze_approvals, build_timeline
from eligibility import evidence_overview, review_eligibility
from deal import deal_facts, load_deal_data, rent_for_simulation
from location_sources import record
from money_runway import analyze_money
from reconcile import load_tenancies, reconcile_evidence
from space_fit import gather, listed_spaces, load_property, space_fit

REVIEW_USES = {name: spec["fit"] for name, spec in CATALOG.items()}


def space_option(space):
    suite = str(space["suite"] or "").strip()
    if suite:
        return {"value": suite, "label": f"Suite {suite}"}
    size = space["square_feet"]
    if size:
        return {"value": f"listing:{space['listing_id']}:{size:g}", "label": f"{size:,.0f} sq ft (unnamed)"}
    return None


def suite_options(kit, property_id, password):
    options = [option for space in listed_spaces(kit, property_id, password)
               if (option := space_option(space))]
    return list({option["value"]: option for option in options}.values())


def project_cash(inputs, use, ownership, buyer=None):
    result = analyze_money(inputs, proposed_use=use, ownership=ownership, buyer=buyer)
    months = result["inputs"]
    result["timeline"] = build_timeline({
        "permit_months": months["permit_months"], "build_months": months["build_months"],
        "delay_months": months["delay"],
    })
    return result


def _review_property(kit, entry, use, suite, ownership, inputs, *, password=None, offline=False,
                    buyer=None, research=None):
    property_id = int(entry["id"])
    prop = load_property(kit, property_id, password)
    spaces = listed_spaces(kit, property_id, password)
    region = "TX" if entry["city"] == "Houston" else "CA"
    address = f'{entry["address"]}, {entry["city"]}, {region}'
    selected = [space for space in spaces if suite and (option := space_option(space))
                and option["value"] == suite]
    if suite and not selected:
        raise ValueError("Choose an advertised suite for this property.")
    listing = selected[0] if len(selected) == 1 else None
    unit = str(listing["suite"]).strip() if listing and listing["suite"] else None
    scope_label = space_option(listing)["label"] if listing else "Building scope"
    # A building-only lease cannot select a specific commercial space.
    deals, offers, comps = load_deal_data(kit, property_id, password) if listing or ownership == "buy" else ([], [], [])
    matched_deals = [space for space in deals if listing and str(space.get("suite") or "").strip() == (unit or "")
                     and space["listing_id"] == listing["listing_id"]
                     and space.get("squareFeetMax") == listing["square_feet"]]
    eligibility = review_eligibility(prop, suite, selected, matched_deals, offers, ownership)
    if eligibility["status"] != "conditional":
        audit = reconcile_evidence(prop, selected_suite=unit)
        audit["records"].extend(eligibility["records"])
        return {
            "property_id": property_id, "address": address, "proposed_use": use, "suite": unit,
            "requested_suite": suite, "scope_label": scope_label, "ownership": ownership, "headline": eligibility["headline"],
            "eligibility": eligibility, "identity": audit, "evidence_overview": evidence_overview(audit["records"]),
            "money": None, "space": None, "approvals": None, "location": None,
            "tour": next((row["evidence_url"] for row in eligibility["records"] if row["evidence_url"]), None),
            "actions": [{"title": "Verify an available commercial space or pick another property",
                         "owner": "Broker or property manager",
                         "request": "Ask for the current listing, the premises on a floor plan and the allowed use. Verify that any tour covers those premises."}],
            "unavailable_sources": [],
        }

    prop, _, vexcel, rooms, errors = gather(kit, property_id, offline, password, property_data=(prop, spaces))
    tenancies = load_tenancies(kit, {property_id}, password).get(property_id, [])
    audit = reconcile_evidence(prop, rooms, selected_suite=unit, tenancies=tenancies)
    blocked_scans = {row["source_id"] for row in audit["records"]
                     if row["fact"] in {"scan_address", "scan_suite"} and row["status"] == "conflict"}
    fit = space_fit(prop, REVIEW_USES[use], spaces=selected if listing else [], suite=unit,
                    requirements={"min_area_sf": 1} if REVIEW_USES[use] == "custom" else None,
                    vexcel=vexcel, rooms_by_model={model: value for model, value in rooms.items()
                                                  if model not in blocked_scans})
    alternatives_fit = {}
    for candidate, spec in CATALOG.items():
        alternatives_fit[candidate] = space_fit(
            prop, spec['fit'], spaces=selected if listing else [], suite=unit, vexcel=vexcel,
            rooms_by_model={m: r for m, r in rooms.items() if m not in blocked_scans},
            requirements={'min_area_sf': 1} if spec['fit'] == 'custom' else None)
    # An area calculation cannot determine court layout.
    fit["records"] = [row for row in fit["records"] if row["fact"] != "pickleball_courts_by_area"]
    if (blocked_scans or not listing) and fit["verdict"] == "supported":
        fit["verdict"] = "investigate"
    deal = deal_facts(property_id, deals, offers, comps, prop.get("grossBuildingAreaSquareFeet"),
                      suite=unit)
    if ownership == "buy" and "upfront_cost" not in inputs:
        purchase_cost = next((row for row in deal["records"] if row["fact"] == "sale_asking_price"), None)
        if purchase_cost:
            deal["purchase_note"] = "Enter your expected acquisition cash in the scenario before interpreting cash runway."
        else:
            deal["purchase_note"] = "No asking price was found. Enter your own expected acquisition cash."
    rent = rent_for_simulation(matched_deals) if len(matched_deals) == 1 and ownership == "lease" else None
    cash_inputs = dict(inputs)
    rent_source = "Editable assumption"
    bank_has_rent = buyer and any(
        str(bill.get("payee", "")).casefold().startswith("suite base rent")
        for bill in buyer["recurring_bills"]
    )
    if bank_has_rent and ownership == "lease" and "monthly_rent" not in cash_inputs:
        cash_inputs["monthly_rent"] = 0
        rent_source = "Base rent already included in the Nessie bills"
    elif rent and "monthly_rent" not in cash_inputs:
        cash_inputs["monthly_rent"] = rent["monthly"]
        rent_source = rent["source"]
    if property_id == 23296 and unit == "A" and ownership == "lease" and not buyer:
        # Match the pilot: $2k in assumed NNN charges plus $2k in pre-opening overhead.
        cash_inputs.setdefault("monthly_carry", 4000)
    cash = None
    if fit["verdict"] == "does_not_fit":
        eligibility["headline"] = "Fit check failed under the available measurements"
        eligibility["reason"] = "Review the physical fit findings before modeling this conversion."
        eligibility["status"] = "blocked"
    else:
        cash = project_cash(cash_inputs, use, ownership, buyer)
        cash["rent_source"] = rent_source
    building = record("costar", f"property-{property_id}", "CoStar building record",
                      {"zoningDescription": prop.get("zoningDescription")})
    approvals = analyze_approvals(address, use, [building], {
        "permit_months": cash["inputs"]["permit_months"], "build_months": cash["inputs"]["build_months"],
        "delay_months": cash["inputs"]["delay"],
    } if cash else None)
    location = {"findings": [], "sources": [], "status": "offline" if offline else "unavailable"}
    if not offline and research and cash:
        try:
            report = research(property_id, use)
            location.update(status="complete", findings=report["findings"], sources=report["evidence"])
            audit["records"].extend(row for row in report["evidence"] if row["source"] == "public:fema")
        except (OSError, RuntimeError, ValueError, KeyError):
            pass
    conflict = any(row["fact"] in {"scan_address", "scan_suite"} and row["status"] == "conflict"
                   for row in audit["records"])
    tour = next((row["evidence_url"] for row in audit["records"]
                 if row["fact"] == "scan_address" and row["evidence_url"]), None)
    actions = [
        {"title": "Confirm the advertised suite and request a dimensioned plan",
         "request": "Match the suite to the tour. Verify clear width, length, overhead obstructions and usable height before pricing a layout.",
         "owner": "Broker and architect"},
        *approvals["actions"][:2],
        {"title": "Test willingness to book", "request": "Run a paid trial and compare nearby offers before relying on the booking assumption.",
         "owner": "Operator"},
    ]
    return {
        "property_id": property_id, "address": address, "proposed_use": use, "suite": unit,
        "requested_suite": suite, "scope_label": scope_label, "ownership": ownership,
        "headline": "Confirm the suite before committing" if conflict or not listing else "Verify layout, approvals and demand before committing",
        "eligibility": eligibility, "evidence_overview": evidence_overview(audit["records"]),
        "identity": audit, "space": fit, "deal": deal, "approvals": approvals,
        "location": location, "money": cash, "actions": actions,
        "unavailable_sources": list(errors),
        "tour": tour, "_fits": alternatives_fit, "_prop": prop, "_listing": listing,
    }


def review_property(kit, entry, use, suite, ownership, inputs, **kwargs):
    # Validate before providers; contract is additive to preserve existing callers.
    from money_runway import assumptions
    assumptions(inputs)
    overrides = kwargs.pop("cost_overrides", None)
    report = _review_property(kit, entry, use, suite, ownership, inputs, **kwargs)
    report['source_mode'] = 'Saved sponsor evidence; live research disabled' if kwargs.get('offline') else 'Sponsor kit and provider research (may be partial)'
    attach_context(report, inputs)
    report['alternatives'] = rank_alternatives(report, report.pop('_prop', {}), report.pop('_fits', {}),
        report.pop('_listing', None), report['decision_context']['cash_budget'], float(inputs.get('reserve', 50000)))
    if report['money']:
        listing = next((r for r in report['space']['records'] if r['fact']=='listed_space_sf'), {})
        report['costs'] = estimate_costs(report['money']['inputs'], area=listing.get('value'), tenure=ownership,
            geography=entry['city'], rent_source=report['money']['rent_source'], overrides=overrides)
        for option in report['alternatives']['all_options']:
            option['cash_required'] = report['costs']['totals']['base']['cash_required']
            option['budget_fit'] = ('unknown: incomplete cost lines' if option['cash_required'] is None else
                'shortfall under planning allowances' if report['costs']['totals']['base']['shortfall'] else 'within budget under unverified planning allowances')
            if option['status']=='conditional' and report['costs']['totals']['base']['shortfall']:
                option['status']='unaffordable'
                option['key_blocker']='Planning cash required exceeds available cash; reduce scope or increase cash before proceeding.'
        report['alternatives']['options'] = [o for o in report['alternatives']['all_options'] if o['status']=='conditional'][:3]
        if not report['alternatives']['options']:
            report['alternatives']['recommendation']='Do not commit: no screened option fits the current planning budget.'
        report['alternatives']['ranking_basis']='Deterministic eligibility and physical fit first, then budget. All uses share your editable cost envelope until use-specific bids exist; requested use breaks ties. No claim that one use is cheaper without evidence.'
    return report
