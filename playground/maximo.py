"""Join the team checks for one property and one explicitly selected suite."""
from approvals_timeline import analyze_approvals, build_timeline
from deal import deal_facts, load_deal_data, rent_for_simulation
from location_sources import record
from money_runway import analyze_money
from reconcile import load_tenancies, reconcile_evidence
from space_fit import gather, listed_spaces, space_fit

REVIEW_USES = {"indoor pickleball": "pickleball", "fitness studio": "gym"}


def suite_options(kit, property_id, password):
    return sorted({str(space["suite"]).strip() for space in listed_spaces(kit, property_id, password)
                   if space["suite"] and str(space["suite"]).strip()})


def project_cash(inputs, use, ownership, buyer=None):
    result = analyze_money(inputs, proposed_use=use, ownership=ownership, buyer=buyer)
    months = result["inputs"]
    result["timeline"] = build_timeline({
        "permit_months": months["permit_months"], "build_months": months["build_months"],
        "delay_months": months["delay"],
    })
    return result


def review_property(kit, entry, use, suite, ownership, inputs, *, password=None, offline=False,
                    buyer=None, research=None):
    property_id = int(entry["id"])
    prop, spaces, vexcel, rooms, errors = gather(kit, property_id, offline, password)
    region = "TX" if entry["city"] == "Houston" else "CA"
    address = f'{entry["address"]}, {entry["city"]}, {region}'
    tenancies = load_tenancies(kit, {property_id}, password).get(property_id, [])
    deals, offers, comps = load_deal_data(kit, property_id, password)
    selected = [space for space in spaces if suite and str(space["suite"]).strip() == suite]
    if suite and not selected:
        raise ValueError("Choose an advertised suite for this property.")
    unit = suite if len(selected) == 1 else None
    matched_deals = [space for space in deals if unit and str(space.get("suite")).strip() == unit
                     and space["listing_id"] == selected[0]["listing_id"]
                     and space.get("squareFeetMax") == selected[0]["square_feet"]]
    audit = reconcile_evidence(prop, rooms, selected_suite=unit, tenancies=tenancies)
    blocked_scans = {row["source_id"] for row in audit["records"]
                     if row["fact"] in {"scan_address", "scan_suite"} and row["status"] == "conflict"}
    fit = space_fit(prop, REVIEW_USES[use], spaces=selected if unit else [], suite=unit,
                    vexcel=vexcel, rooms_by_model={model: value for model, value in rooms.items()
                                                  if model not in blocked_scans})
    # An area calculation cannot determine court layout.
    fit["records"] = [row for row in fit["records"] if row["fact"] != "pickleball_courts_by_area"]
    if blocked_scans or not unit:
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
    cash = project_cash(cash_inputs, use, ownership, buyer)
    cash["rent_source"] = rent_source
    building = record("costar", f"property-{property_id}", "CoStar building record",
                      {"zoningDescription": prop.get("zoningDescription")})
    approvals = analyze_approvals(address, use, [building], {
        "permit_months": cash["inputs"]["permit_months"], "build_months": cash["inputs"]["build_months"],
        "delay_months": cash["inputs"]["delay"],
    })
    location = {"findings": [], "sources": [], "status": "offline" if offline else "unavailable"}
    if not offline and research:
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
        "requested_suite": suite, "ownership": ownership,
        "headline": "Confirm the suite before committing" if conflict or not unit else "Verify layout, approvals and demand before committing",
        "identity": audit, "space": fit, "deal": deal, "approvals": approvals,
        "location": location, "money": cash, "actions": actions,
        "unavailable_sources": list(errors),
        "tour": tour,
    }
