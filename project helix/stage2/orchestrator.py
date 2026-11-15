"""Stage 2 orchestration and dossier construction."""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

from .contracts import validate_handoff
from .providers import CoStarAdapter, MatterportAdapter, VexcelAdapter
from .property_preflight import run_property_preflight
from .reconciliation import reconcile_claims


def _asmit_reconciliation(costar_result, handoff):
    """Call Asmit/Jayant's shared deterministic reconciliation, without its network collectors."""
    prop=costar_result.get("raw_property_record")
    if not isinstance(prop,dict): return []
    try:
        import sys
        from pathlib import Path
        playground=Path(__file__).resolve().parents[2]/"playground"
        if str(playground) not in sys.path: sys.path.insert(0,str(playground))
        from reconcile import reconcile_evidence
        selected=handoff.get("selected_listing") or {}
        result=reconcile_evidence(prop,selected_suite=selected.get("suite"),tenancies=costar_result.get("tenancies"))
    except Exception:
        return []
    findings=[]
    for record in result.get("records",[]):
        status=record.get("status")
        if record.get("fact")=="suite_occupancy_at_scan":
            if status=="conflict": status="possible_conflict"  # attachment date is not camera capture
            elif status=="agrees" and ("moved in after the scan" in record.get("note","") or "had left before" in record.get("note","")):
                status="resolved_by_timeline"
        elif record.get("fact") in ("scan_address","scan_suite") and status=="conflict":
            status="possible_conflict"  # quarantine a likely wrong-building link; do not transfer its facts
        if status in ("conflict","possible_conflict","not_comparable","resolved_by_timeline"):
            findings.append({"fact":record.get("fact"),"status":status,"evidence_ids":[record.get("source_id")],
                "source":record.get("source"),"reason":record.get("note"),"needs_human":record.get("needs_human",True),
                "source_capture_semantics":"CoStar attachment originationDate is attachment provenance, not verified camera capture" if record.get("fact") in ("scan_attachment_date","suite_occupancy_at_scan") else None})
    return findings


def _status_summary(value):
    result={"status":value.get("status","unknown"),"reason":value.get("reason"),"error":value.get("error")}
    if value.get("operations"):
        result["operations"]={name:{k:op.get(k) for k in ("status","http_status","feature_count") if k in op}
                              for name,op in value["operations"].items()}
        ortho_dates=value["operations"].get("ortho_dates",{}).get("dates")
        if ortho_dates is not None:
            result["ortho_date_metadata"]=ortho_dates
        result["image_extraction"]=value.get("image_extraction")
        ops=value["operations"].get("property_extract",{})
        structures=ops.get("structures_at_pin") or []
        result["selected_structure_candidates"]=[{"structure_id":s.get("structure_id"),"capture_estimate":s.get("capture_estimate"),
            "identity_status":s.get("identity_status"),"footprint_area_sqft":s.get("footprint_area_sqft"),
            "roof_signals":s.get("roof_signals"),"rooftop_objects":s.get("rooftop_objects"),"roof_defect_signals":s.get("roof_defect_signals"),
            "interpretation_limit":s.get("interpretation_limit")} for s in structures]
    if value.get("visual_analysis"):
        result["visual_analysis"]={k:value["visual_analysis"].get(k) for k in ("status","reason","model","latency_ms") if k in value["visual_analysis"]}
    return result


def _unknowns(costar, matterport, vexcel, compliance):
    result=[]
    for source, item in (("CoStar",costar),("Matterport",matterport),("Vexcel",vexcel)):
        if item.get("status")!="available": result.append({"topic":source,"status":item.get("status","unknown"),"note":item.get("reason") or item.get("error") or "Evidence unavailable."})
    if not any(m.get("identity_status")=="matched" for m in matterport.get("models",[])):
        result.append({"topic":"Matterport identity","status":"unknown","note":"No exact-address model match is available; model measurements are excluded from reconciliation."})
    result.append({"topic":"Structure-level Vexcel identity","status":"unknown","note":"Parcel/collection geometry does not carry a CoStar building ID; no automatic building match is inferred."})
    result.append({"topic":"Visual evidence limitations","status":"unknown","note":"Visual descriptions are not inspections and cannot establish hidden systems, safety, structural condition or code compliance."})
    report=compliance.get("report") or {}
    for gate in report.get("gates",[]): result.append({"topic":"Property preflight","status":"unknown","note":gate})
    return result


def investigate(payload, *, costar_service=None, costar_adapter=None, matterport_adapter=None, vexcel_adapter=None,
                preflight_runner=run_property_preflight, visual_result=None):
    handoff=validate_handoff(payload)
    # Resolve source identity and collect independently; an adapter outage never aborts the dossier.
    costar=(costar_adapter or CoStarAdapter()).collect(handoff,costar_service)
    try: matterport=(matterport_adapter or MatterportAdapter()).collect({**handoff,"property_facts":costar.get("facts") or handoff.get("property_facts")})
    except Exception as error: matterport={"status":"temporarily_unavailable","error":type(error).__name__,"models":[],"claims":[]}
    try: vexcel=(vexcel_adapter or VexcelAdapter()).collect({**handoff,"property_facts":costar.get("facts") or handoff.get("property_facts")})
    except Exception as error: vexcel={"status":"temporarily_unavailable","error":type(error).__name__,"operations":{},"claims":[]}
    claims=list(costar.get("claims") or [])+list(matterport.get("claims") or [])+list(vexcel.get("claims") or [])
    asmit_findings=_asmit_reconciliation(costar,handoff)
    contradictions=reconcile_claims(claims)+asmit_findings
    # Building floor area and a ground footprint are different measurements.
    for area in [c for c in claims if c.get("fact")=="gross_building_area_sqft"]:
        for footprint in [c for c in claims if c.get("fact")=="vexcel_structure_footprint_area"]:
            contradictions.append({"fact":"gross_building_area_sqft_vs_vexcel_structure_footprint_area","status":"not_comparable",
                "evidence_ids":[area["claim_id"],footprint["claim_id"]],
                "reason":"CoStar gross floor area and Vexcel ground footprint area differ in measurement semantics. A parcel may also contain multiple structures; do not interpret the numeric difference as an area contradiction."})
    for model in matterport.get("models",[]):
        if model.get("identity_status")=="quarantined":
            contradictions.append({"fact":"matterport_model_identity","status":"possible_conflict",
                "evidence_ids":[model.get("model_id")],"identity_conflict":True,
                "reason":f"Matterport model label {model.get('name')!r} does not exactly match the selected CoStar address; its measurements are quarantined."})
    identity_conflict=any(v.get("identity_conflict") for v in contradictions)
    try: compliance=preflight_runner(handoff,costar.get("facts") or handoff.get("property_facts"),identity_conflict)
    except Exception as error: compliance={"status":"temporarily_unavailable","report":None,"business_specific_checks_invoked":False,"error":type(error).__name__}
    facts=costar.get("facts") or handoff.get("property_facts") or {}
    physical=[]
    for claim in claims:
        if claim.get("source")=="matterport" and claim.get("fact")=="room_area":
            physical.append({"kind":"reported_spatial_measurement","fact":claim["fact"],"value":claim["value"],"unit":claim["unit"],"scope":claim["scope_type"],"evidence_ids":[claim["claim_id"]],"note":"Matterport model estimate; not a verified usable area."})
        elif claim.get("source")=="vexcel":
            physical.append({"kind":"exterior_metadata","fact":claim["fact"],"value":claim["value"],"unit":claim["unit"],"scope":claim["scope_type"],"evidence_ids":[claim["claim_id"]],"note":("Vexcel imagery-derived signal; not an inspection or engineering assessment. " + ("The CoStar point lies inside this footprint." if claim.get("extra",{}).get("pin_within_footprint") else "Nearest footprint only; building identity is unconfirmed."))})
    if visual_result:
        for item in visual_result.get("observations",[]):
            physical.append({"kind":"direct_visual_observation",**item,"evidence_ids":[item.get("image_id")]})
    else:
        visual_result=matterport.get("visual_analysis") or {"status":"not_run","reason":"No authorized image-analysis result was supplied.","observations":[]}
        for item in visual_result.get("observations",[]):
            physical.append({"kind":"direct_visual_observation",**item,"evidence_ids":[item.get("image_id")]})
    retrieved=datetime.now(timezone.utc).isoformat()
    selected={"property_id":handoff["selected_listing"]["property_id"],"listing_id":handoff["selected_listing"].get("listing_id"),
              "space_id":handoff["selected_listing"].get("space_id"),"stable_id":handoff["selected_listing"].get("stable_id"),
              "address":handoff["selected_listing"]["address"],"city":facts.get("city"),"state":facts.get("state"),
              "latitude":facts.get("latitude"),"longitude":facts.get("longitude")}
    dossier={"schema_version":"helix.investigation.v1","investigation_id":uuid.uuid4().hex,
      "created_at":retrieved,"selected_property":selected,
      "source_status":{"costar":_status_summary(costar),"matterport":_status_summary(matterport),"vexcel":_status_summary(vexcel)},
      "identity_resolution":{"status":"conflict" if identity_conflict else "resolved_to_selected_costar_property","canonical_identity":f"costar-property:{selected['property_id']}",
          "matterport_models":[{"model_id":m.get("model_id"),"status":m.get("identity_status"),"name":m.get("name"),
              "floor_count":m.get("floor_count"),"room_count":m.get("room_count"),"panorama_count":m.get("panorama_count"),
              "available_panorama_count":m.get("available_panorama_count"),"images":m.get("images",[])} for m in matterport.get("models",[])],
          "vexcel_geometry_scope":"parcel candidate; no building-level identity established"},
      "reported_building_facts":{"costar":facts,"listing_context":costar.get("listing_context"),"evidence_claims":claims,
          "asmit_reconciliation_records":asmit_findings},
      "physical_observations":physical,"visual_analysis":visual_result,
      "contradictions":[v for v in contradictions if v.get("status") in ("conflict","possible_conflict","not_comparable")],
      "resolved_discrepancies":[v for v in contradictions if v.get("status")=="resolved_by_timeline"],
      "property_compliance_preflight":compliance,
      "unknowns":_unknowns(costar,matterport,vexcel,compliance),
      "verification_tasks":[{"task":"Confirm property/building identity for each parcel geometry and any non-matching Matterport scan.","evidence_ids":[]},
          {"task":"Verify occupancy, fire/life-safety, accessibility, parking and MEP records with the responsible authority and qualified professionals.","evidence_ids":[]}],
      "provenance":claims,"stage3_handoff":{"schema_version":"helix.stage3-input.v1","selected_property":selected,
          "stage1_context":{"intake":handoff.get("intake"),"selected_listing":handoff.get("selected_listing")},
          "physical_facts":physical,"contradictions":contradictions,"unknowns":_unknowns(costar,matterport,vexcel,compliance),
          "property_compliance_preflight":compliance,"source_status":{"costar":costar.get("status"),"matterport":matterport.get("status"),"vexcel":vexcel.get("status")},
          "business_recommendations":[],"financial_feasibility":None}}
    return {"status":"complete" if costar.get("status")=="available" else "partial","dossier":dossier}
