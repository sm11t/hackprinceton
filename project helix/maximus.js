"use strict";
(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const intakeForm = $("#intake-form");
  const intakeView = $("#intake-view");
  const discoveryView = $("#discovery-view");
  const status = $("#status");
  const discoveryError = $("#discovery-error");
  const budget = $("#budget");
  const intakeKey = "maximus.stage0.intake.v1";
  const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
  let currentIntake = null;
  let currentDiscovery = null;
  let currentInvestigation = null;
  let currentStage3Output = null;
  let stage3InvestigationId = null;
  let reclassifyTimer = null;
  let displayLimit = 40;

  async function post(path, body) {
    const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
    return data;
  }
  async function get(path) {
    const response = await fetch(path, { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
    return data;
  }
  function setStage(stage) {
    intakeView.hidden = stage !== 0;
    discoveryView.hidden = stage !== 1;
    $("#stage2").hidden = stage !== 2;
    $("#stage3").hidden = stage !== 3;
    $("#stage-indicator").textContent = stage === 0 ? "STAGE 0 · YOUR STARTING POINT" : stage === 1 ? "STAGE 1 · PROPERTY DISCOVERY" : stage === 2 ? "STAGE 2 · BUILDING INVESTIGATION" : "STAGE 3 · BUSINESS OPTIONS";
    $("#step-count").textContent = stage === 0 ? "01 / 04" : stage === 1 ? "02 / 04" : stage === 2 ? "03 / 04" : "04 / 04";
    $("#progress").style.width = stage === 0 ? "12%" : stage === 1 ? "36%" : stage === 2 ? "62%" : "82%";
  }
  function readForm() {
    return {
      city: intakeForm.city.value,
      total_budget_usd: Number(budget.value.replace(/[,$\s]/g, "")),
      financing: intakeForm.financing.value,
      business_preferences: $("#preferences").value.trim(),
      open_to_ideas: $("#open-ideas").checked,
    };
  }
  function fillForm(value) {
    if (!value) return;
    const city = $(`input[name="city"][value="${CSS.escape(value.city || "")}"]`);
    const financing = $(`input[name="financing"][value="${CSS.escape(value.financing || "")}"]`);
    if (city) city.checked = true;
    if (financing) financing.checked = true;
    budget.value = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value.total_budget_usd || "");
    $("#preferences").value = value.business_preferences || "";
    $("#open-ideas").checked = value.open_to_ideas === true;
  }
  function text(parent, tag, value, className) {
    const node = document.createElement(tag);
    if (value !== undefined && value !== null) node.textContent = String(value);
    if (className) node.className = className;
    parent.append(node);
    return node;
  }
  function clear(node) { node.replaceChildren(); }
  function sectionMessage(node, message) { clear(node); text(node, "p", message, "investigation-empty"); }
  function humanize(value) {
    return String(value || "").replace(/^vexcel_/, "").replaceAll("_", " ").replace(/\b\w/g, x => x.toUpperCase());
  }
  function dateLabel(value) {
    if (!value) return "Capture date unavailable";
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? String(value).slice(0, 10) : new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(date);
  }
  function imageDialog(src, title) {
    let dialog = $("#evidence-image-dialog");
    if (!dialog) {
      dialog = document.createElement("dialog"); dialog.id = "evidence-image-dialog"; dialog.className = "evidence-image-dialog";
      const close = text(dialog, "button", "Close", "secondary"); close.type = "button"; close.addEventListener("click", () => dialog.close());
      text(dialog, "h3", "Evidence image", "evidence-dialog-title");
      const img = text(dialog, "img", undefined, "evidence-dialog-image"); img.alt = "Property evidence image";
      document.body.append(dialog);
    }
    $(".evidence-dialog-title", dialog).textContent = title;
    $("img", dialog).src = src; dialog.showModal();
  }
  function renderProgress(handoff) {
    const list = $("#investigation-progress"); clear(list);
    const events = handoff?.progress || [];
    const latest = new Map();
    for (const event of events) latest.set(event.stage, event);
    for (const event of [...latest.values()].slice(-7)) {
      const item = text(list, "li", undefined, "progress-step complete");
      text(item, "strong", event.message || humanize(event.stage));
      if (event.completed != null && event.total != null) text(item, "span", `${event.completed} of ${event.total}`);
    }
    if (handoff?.status === "stage2_running") {
      const item = text(list, "li", undefined, "progress-step active");
      text(item, "strong", "Working through the remaining evidence…");
    }
    $("#investigation-state").textContent = handoff?.status === "stage2_complete" ? "Complete" : handoff?.status === "stage2_running" ? "In progress" : handoff?.status === "stage2_failed" ? "Could not finish" : "Partially complete";
  }
  function renderInvestigation(handoff) {
    currentInvestigation = handoff;
    renderProgress(handoff);
    const d = handoff?.dossier;
    $("#stage3-start").disabled = !d || handoff?.status === "stage2_running";
    $("#stage3-transition-note").textContent = !d ? "Complete the investigation to explore business options." : handoff?.status === "stage2_partial" ? "Some property evidence is incomplete; you can still review conditional options." : "Review business options for this selected space.";
    if (!d) {
      $("#investigation-summary").textContent = handoff?.message || "Checking the selected property and gathering image evidence.";
      return;
    }
    const p = d.selected_property || {};
    const facts = d.reported_building_facts?.costar || {};
    $("#investigation-title").textContent = p.address || "Selected property";
    const listing = d.reported_building_facts?.listing_context || {};
    $("#investigation-summary").textContent = `${p.city || ""}${p.state ? `, ${p.state}` : ""}${listing.suite ? ` · Suite ${listing.suite}` : p.space_id ? ` · Selected space ${p.space_id}` : ""}. This is a source-backed physical review, not an inspection or approval.`;
    const overview = $("#investigation-overview"); clear(overview);
    const factsOverview = [
      ["Property type", facts.property_type || "Not recorded"],
      ["Selected suite", listing.suite || "Building-wide selection"],
      ["Available area", listing.area_min_sqft == null ? "Not recorded" : `${Number(listing.area_min_sqft).toLocaleString()} SF`],
      ["CoStar building area", facts.gross_building_area_sqft == null ? "Unknown" : `${Number(facts.gross_building_area_sqft).toLocaleString()} SF`],
      ["Stories reported", facts.stories ?? "Unknown"],
    ];
    for (const [label, value] of factsOverview) {
      const card = text(overview, "div", undefined, "overview-fact"); text(card, "small", label); text(card, "strong", value);
    }

    const models = d.identity_resolution?.matterport_models || [];
    const matched = models.find(m => m.status === "matched" && m.showcase_url);
    const viewerWrap = $("#matterport-viewer-wrap"), iframe = $("#matterport-frame");
    if (matched) {
      viewerWrap.hidden = false; $("#matterport-unavailable").hidden = true;
      iframe.src = matched.showcase_url; $("#matterport-open").href = matched.showcase_url;
      $("#matterport-open").setAttribute("aria-label", "Open full Matterport tour in a new tab");
    } else {
      viewerWrap.hidden = true; $("#matterport-unavailable").hidden = false;
      $("#matterport-unavailable").textContent = models.some(m => m.status === "quarantined")
        ? "A linked Matterport scan did not match this property's address, so it is not shown."
        : "No address-matched Matterport tour is available for this property.";
    }

    const gallery = $("#vexcel-gallery"); clear(gallery);
    text(gallery, "h4", "Exterior imagery", "gallery-heading");
    const vx = d.source_status?.vexcel || {}, views = vx.imagery?.views || [];
    if (!views.length) {
      text(gallery, "p", vx.imagery?.status === "unauthorized" ? "Vexcel image access needs authorization." : "No Vexcel aerial or oblique images were retrieved for this property.", "investigation-empty");
    } else {
      const grid = text(gallery, "div", undefined, "vexcel-image-grid");
      for (const view of views) {
        const card = text(grid, "article", undefined, "vexcel-image-card");
        const img = text(card, "img", undefined); img.src = view.image_url; img.alt = `${humanize(view.view)} exterior imagery of ${p.address || "the selected property"}`; img.loading = "lazy";
        img.addEventListener("click", () => imageDialog(view.image_url, `${humanize(view.view)} · ${dateLabel(view.capture_date)}`));
        text(card, "strong", view.view === "aerial" ? "Aerial view" : `${humanize(view.view)} view`);
        text(card, "small", dateLabel(view.capture_date));
        const detail = text(card, "details", undefined, "imagery-details"); text(detail, "summary", "Image details");
        text(detail, "small", `Collection ${view.collection || "not supplied"} · ${view.width && view.height ? `${view.width} × ${view.height}` : "dimensions unavailable"}`);
        const enlarge = text(card, "button", "Enlarge image", "secondary"); enlarge.type = "button"; enlarge.addEventListener("click", () => imageDialog(view.image_url, `${humanize(view.view)} · ${dateLabel(view.capture_date)}`));
      }
    }

    const physical = $("#investigation-physical"); clear(physical);
    const observations = d.physical_observations || [];
    const primary = observations.filter(item => {
      if (!(item.kind === "direct_visual_observation" || (item.kind === "provider_reported_physical_fact" && item.fact !== "structure_count" && item.value != null))) return false;
      const label = `${item.feature || ""} ${item.fact || ""}`.toLowerCase();
      if (label.includes("condition_score")) return false;
      const exterior = item.provider === "Vexcel" || item.source === "vexcel";
      return exterior
        ? /roof|footprint|structure|building|parking|vehicle|car|loading|dock|driveway|entrance|entry door|access door|roll.?up door|gate/.test(label)
        : /door|entrance|entry|access|roll.?up|shutter|opening|partition|circulation|hall|corridor|stair|column|ceiling|beam|duct|hvac|electrical|panel|pipe|sprinkler|fixture|light|conduit|floor drain|open space|open area|clear span/.test(label)
          && !/shelv|ladder|box|chair|desk|flag|workbench|stacked materials|monitor|filing cabinet|document|work table|workstation/.test(label);
    });
    if (!primary.length) text(physical, "p", "No physical features were confirmed in the retrieved imagery.", "investigation-empty");
    else {
      const groups = new Map();
      for (const item of primary) {
        const label = `${item.feature || item.fact || "Other"}`.toLowerCase();
        const exterior = item.provider === "Vexcel" || item.source === "vexcel";
        const key = exterior
          ? /parking|vehicle|car|drive|access|loading|dock|entrance|entry door|gate/.test(label) ? "Parking, loading and access" : "Roof and building form"
          : /door|entrance|entry|access|roll.?up|shutter/.test(label) ? "Doors and access" : /circulation|hall|corridor|stair|partition|room|column|opening/.test(label) ? "Layout and circulation" : "Ceiling and visible utilities";
        if (!groups.has(key)) groups.set(key, []); groups.get(key).push(item);
      }
      for (const [groupName, items] of groups) {
        const group = text(physical, "article", undefined, "finding-summary");
        text(group, "h4", groupName);
        const distinctFeatures = [...new Map(items.map(item => { const value=humanize(item.feature || item.fact || "Observation"); return [value.toLowerCase(),value]; })).values()];
        const locations = new Set(items.map(item => item.location_id || item.image_id).filter(Boolean));
        text(group, "p", `${items.length} evidence observations${locations.size ? ` across ${locations.size} image views` : ""}. ${distinctFeatures.slice(0, 3).join(" · ")}${distinctFeatures.length > 3 ? ` · +${distinctFeatures.length - 3} more` : ""}.`);
        const evidence = text(group, "details", undefined, "finding-evidence");
        text(evidence, "summary", `Review image evidence (${items.length})`);
        const list = text(evidence, "div", undefined, "finding-evidence-list");
        for (const item of items) {
          const row = text(list, "article", undefined, "finding-card");
          text(row, "strong", item.feature ? humanize(item.feature) : humanize(item.fact));
          text(row, "p", item.evidence || `${humanize(item.fact)} reported by ${item.source || item.provider || "source"}${item.value != null ? `: ${Number(item.value).toLocaleString()}${item.unit ? ` ${item.unit}` : ""}` : ""}.`);
          text(row, "small", `${item.provider || item.source || "Source"}${item.capture_date ? ` · ${dateLabel(item.capture_date)}` : item.captured_at ? ` · ${dateLabel(item.captured_at)}` : ""}${item.panorama_face ? ` · Camera view ${item.panorama_face}` : ""}`);
          const action = text(row, "button", item.image_url ? "View image" : "View inside tour", "text-action"); action.type = "button";
          action.addEventListener("click", () => {
            if (item.image_url) imageDialog(item.image_url, item.feature || "Exterior evidence");
            else if (matched && item.location_id) {
              const url = new URL(matched.showcase_url); url.searchParams.set("ss", item.location_id); iframe.src = url.toString();
              $("#investigation-explore").scrollIntoView({ behavior: "smooth", block: "start" });
            } else if (matched) { $("#investigation-explore").scrollIntoView({ behavior: "smooth", block: "start" }); }
          });
        }
      }
    }

    const contradictions = $("#investigation-contradictions"); clear(contradictions);
    const all = [...(d.contradictions || []), ...(d.resolved_discrepancies || [])];
    if (!all.length) text(contradictions, "p", "The available sources did not produce a direct disagreement.", "investigation-empty");
    else for (const item of all) {
      const row = text(contradictions, "article", undefined, `evidence-row verdict-${item.status}`);
      const label = item.status === "resolved_by_timeline" ? "Resolved by dates" : item.status === "possible_conflict" ? "Needs review" : "Conflicting evidence";
      text(row, "strong", `${label} · ${humanize(item.fact)}`); text(row, "p", item.reason || "The sources differ and should be reviewed.");
    }

    const compliance = $("#investigation-compliance"); clear(compliance);
    const report = d.property_compliance_preflight?.report || {};
    if (!report.jurisdiction) text(compliance, "p", "Property jurisdiction could not be confirmed from the available boundary lookup.", "investigation-empty");
    else {
      const j = report.jurisdiction; text(compliance, "p", `${j.place || j.code || "Jurisdiction pending"}${j.county ? ` · ${j.county}` : ""}`, "jurisdiction-result");
      if (j.evidence_url) { const a = text(compliance, "a", "View jurisdiction source"); a.href=j.evidence_url; a.target="_blank"; a.rel="noopener noreferrer"; }
      const records = (report.records || []).filter(x => x.value != null && x.fact !== "identity");
      for (const item of records) { const row=text(compliance,"p",undefined,"preflight-finding"); text(row,"strong",humanize(item.fact)); text(row,"span",String(item.value)); if(item.note) text(row,"small",item.note); }
      if (!records.length && report.status === "needs_verification") text(compliance,"p","The jurisdiction is identified; property-level legal approval has not been established.","preflight-finding");
    }

    const unknowns = $("#investigation-unknowns"); clear(unknowns);
    const todo = (d.verification_tasks || []).filter(x => x.task);
    if (!todo.length) text(unknowns, "p", "No property-specific verification blocker was identified in the evidence retrieved.", "investigation-empty");
    else for (const item of todo) text(unknowns, "p", item.task, "verification-question");
    $("#investigation-handoff").textContent = JSON.stringify({ physical_capabilities: d.stage3_handoff?.physical_capabilities, visual_evidence: d.stage3_handoff?.visual_evidence, physical_unknowns: d.stage3_handoff?.physical_unknowns, stage3_handoff: d.stage3_handoff }, null, 2);
  }
  function stage3List(parent, heading, values) {
    if (!values?.length) return;
    const box=text(parent,"div",undefined,"stage3-list"); text(box,"h4",heading);
    const list=text(box,"ul"); for(const value of values) text(list,"li",value);
  }
  function stage3Sources(parent, sources) {
    if (!sources?.length) return;
    const details=text(parent,"details",undefined,"stage3-sources"); text(details,"summary","View supporting sources");
    const list=text(details,"ul");
    for (const source of sources) {
      const item=text(list,"li");
      if (source.url && /^https?:\/\//i.test(source.url)) {
        const link=text(item,"a",source.name || "Source"); link.href=source.url; link.target="_blank"; link.rel="noopener noreferrer";
      } else text(item,"span",source.name || "Source");
      if(source.note) text(item,"small",source.note);
    }
  }
  function renderStage3(data) {
    currentStage3Output=data;
    $("#stage3-results").hidden=false;
    $("#stage3-count").textContent=`${data.shortlist?.length || 0} shortlisted · ${data.summary?.businesses ?? data.gates?.length ?? 0} evaluated`;
    $("#stage3-context").textContent=`${data.inputs?.address || "Selected property"} · ${Number(data.inputs?.space_sf || 0).toLocaleString()} SF · ${money.format(data.inputs?.budget || 0)} budget · Reserve ${data.inputs?.reserve === "unavailable" || data.inputs?.reserve == null ? "not provided" : money.format(data.inputs.reserve)}`;
    const target=$("#stage3-candidates"); clear(target);
    if (!data.shortlist?.length) text(target,"p","No business passed all screening gates with the available evidence.","stage3-empty");
    for (const candidate of data.shortlist || []) {
      const gate=(data.gates || []).find(x=>x.business===candidate.business) || {};
      const card=text(target,"article",undefined,"stage3-card");
      const head=text(card,"div",undefined,"stage3-card-head"), title=text(head,"div");
      text(title,"span",`#${candidate.rank} · ${candidate.group || "Business option"}`,"stage3-rank");
      text(title,"h3",candidate.label); text(head,"span","Needs verification","stage3-chip amber");
      const totals=candidate.stage4_inputs?.cash_to_open || {};
      const metrics=text(card,"div",undefined,"stage3-metrics");
      for(const [label,value] of [["Low",totals.low],["Base",totals.base],["High",totals.high]]) {
        const metric=text(metrics,"div"); text(metric,"small",`${label} startup`); text(metric,"strong",value == null ? "Unknown" : money.format(value));
      }
      const checks=text(card,"div",undefined,"stage3-check-grid");
      const building=text(checks,"div",undefined,"stage3-check"); text(building,"h4","Building fit");
      text(building,"p",(gate.building?.reasons || []).join(" · ") || gate.building?.rule || "Needs review.");
      const affordability=text(checks,"div",undefined,"stage3-check"); text(affordability,"h4","Affordability");
      text(affordability,"p",gate.affordability?.note || gate.affordability?.rule || "Needs review.");
      stage3List(card,"Conditions",candidate.conditions);
      stage3List(card,"Unknowns",candidate.unknowns);
      stage3List(card,"Verify before proceeding",candidate.verification_questions);
      const sources=[...(gate.building?.sources || []),...(gate.affordability?.sources || []),...(gate.compliance?.sources || [])];
      const seen=new Set(); stage3Sources(card,sources.filter(s=>{const k=`${s.name}|${s.url}`;if(seen.has(k))return false;seen.add(k);return true;}));
    }
    const gates=$("#stage3-gates"); clear(gates);
    $("#stage3-all-label").textContent=`Review all ${data.gates?.length || 0} business outcomes`;
    for (const g of data.gates || []) {
      const row=text(gates,"details",undefined,"stage3-gate"); const summary=text(row,"summary");
      text(summary,"strong",g.label); text(summary,"span",g.hard_pass ? "Passed screening · conditional" : `Stopped at ${humanize(g.stopped_at || "review")}`,g.hard_pass ? "stage3-chip" : "stage3-chip muted");
      for(const [label,key] of [["Building","building"],["Affordability","affordability"],["Compliance","compliance"]]) {
        const info=g[key] || {}; const line=text(row,"div",undefined,"stage3-gate-detail"); text(line,"strong",`${label}: ${humanize(info.status)}`);
        const reasons=info.reasons?.length ? info.reasons : info.note ? [info.note] : info.gates?.length ? info.gates.map(humanize) : info.rule ? [info.rule] : [];
        stage3List(line,"Reasons",reasons); stage3List(line,"Unknowns",info.unknowns);
      }
    }
    $("#stage3-json").textContent=JSON.stringify(data,null,2);
  }
  async function runStage3() {
    const handoff=currentInvestigation, entry=handoff?.selected_listing || {}, intake=handoff?.intake || {};
    if (!handoff?.dossier || !handoff.handoff_id) { $("#stage3-status").textContent="Complete the investigation first."; return; }
    if (entry.transaction_type !== "lease") { $("#stage3-status").textContent="Business options currently support selected lease spaces. Return to properties to select a lease."; return; }
    if (!entry.listing_id || !entry.space_id) { $("#stage3-status").textContent="The selected space cannot be verified because its listing or space ID is missing."; return; }
    const reserve=$("#stage3-reserve").value.trim();
    if (reserve!=="" && (!Number.isFinite(Number(reserve)) || Number(reserve)<0)) { $("#stage3-status").textContent="Enter a nonnegative reserve or leave it blank."; return; }
    currentStage3Output=null; $("#stage3-run").disabled=true; $("#stage3-results").hidden=true; $("#stage3-status").textContent="Matching your exact space and evaluating all 26 business types…";
    try {
      const query=new URLSearchParams({id:handoff.handoff_id,reserve});
      const result=await get(`/api/stage3/investigation?${query}`);
      if (String(result.inputs?.property_id)!==String(entry.property_id)) throw new Error("The Stage 3 property did not match the selected property.");
      renderStage3(result); $("#stage3-status").textContent="Screening complete. Review the conditions and evidence for each option.";
    } catch(error) { $("#stage3-status").textContent=`Could not complete business screening: ${error.message}`; }
    finally { $("#stage3-run").disabled=false; }
  }
  $("#stage3-start").addEventListener("click",()=>{
    const handoff=currentInvestigation; if (!handoff?.dossier) return;
    const intake=handoff.intake || {}, p=handoff.selected_listing || {};
    if (stage3InvestigationId === handoff.handoff_id && currentStage3Output) {
      setStage(3); window.scrollTo({top:0,behavior:"smooth"}); return;
    }
    stage3InvestigationId=handoff.handoff_id;
    $("#stage3-reserve").value=intake.reserve == null ? "" : String(intake.reserve);
    $("#stage3-context").textContent=`${p.address || "Selected property"} · ${p.area_min_sqft == null ? "Area unavailable" : `${Number(p.area_min_sqft).toLocaleString()} SF`} · ${money.format(intake.total_budget_usd || 0)} budget`;
    setStage(3); window.scrollTo({top:0,behavior:"smooth"}); runStage3();
  });
  $("#stage3-run").addEventListener("click",runStage3);
  $("#stage3-back").addEventListener("click",()=>{setStage(2);window.scrollTo({top:0,behavior:"smooth"});});
  function classificationLabel(value) {
    return ({ within_budget: "Within budget", stretch: "Stretch", over_budget: "Over budget", unknown: "Unknown" })[value] || "Unknown";
  }
  function propertyType(r) { return r.property_type || "Property type not recorded"; }
  function areaLabel(r) {
    if (r.area_min_sqft == null && r.area_max_sqft == null) return "Area unknown";
    if (r.area_min_sqft == null) return `Up to ${Number(r.area_max_sqft).toLocaleString()} SF`;
    if (r.area_max_sqft == null) return `At least ${Number(r.area_min_sqft).toLocaleString()} SF`;
    if (r.area_max_sqft != null && r.area_min_sqft !== r.area_max_sqft) return `${Number(r.area_min_sqft).toLocaleString()}–${Number(r.area_max_sqft).toLocaleString()} SF`;
    return `${Number(r.area_min_sqft).toLocaleString()} SF`;
  }
  function amountLabel(r) {
    if (r.transaction_type === "sale") return r.asking_price_usd == null ? "Asking price unknown" : `${money.format(r.asking_price_usd)} asking price`;
    const n = r.rent_normalization || {};
    if (n.status !== "normalized") {
      const raw = r.rent_raw || {};
      const rawText = raw.low != null || raw.high != null ? `Raw CoStar rate: ${raw.low ?? "?"}–${raw.high ?? "?"} (${n.raw_basis || "basis unknown"})` : "Asking rent unknown";
      return rawText;
    }
    const low = money.format(n.monthly_low_usd), high = money.format(n.monthly_high_usd);
    return `${low}${low === high ? "" : `–${high}`}/month base rent`;
  }
  function selectedLeaseClass(r) {
    const h = $("#horizon").value;
    return h ? r.lease_affordability?.[h]?.classification : r.budget_classification;
  }
  function appendFact(parent, label, value) {
    const fact = text(parent, "div", undefined, "fact");
    text(fact, "small", label);
    text(fact, "strong", value);
  }
  function renderConfidence(parent, confidence) {
    const details = text(parent, "details", undefined, "confidence");
    text(details, "summary", `Confidence · ${confidence.overall_confidence == null ? "incomplete evidence" : `${confidence.overall_confidence}/100`} (not a probability)`);
    const grid = text(details, "div", undefined, "confidence-grid");
    const labels = [
      ["Source reliability", confidence.source_reliability],
      ["Data completeness / consistency", confidence.data_completeness_consistency],
      ["Budget fit", confidence.budget_fit],
      ["Property-search fit", confidence.property_search_fit],
    ];
    for (const [label, factor] of labels) {
      const item = text(grid, "div", undefined, "confidence-item");
      text(item, "strong", `${label}: ${factor?.score == null ? "Unknown" : `${factor.score}/100`}`);
      text(item, "span", factor?.basis || "Insufficient supporting evidence.");
    }
  }
  function renderVerification(parent, verification) {
    const wrap = text(parent, "div", undefined, "verify-panel");
    if (verification.error) text(wrap, "p", verification.error, "caveat");
    const summary = text(wrap, "p", `Verification: ${verification.overall_status || "unavailable"}. Retrieved ${verification.retrieved_at || "time unavailable"}.`, "sub");
    for (const claim of verification.claims || []) {
      const item = text(wrap, "div", undefined, "claim");
      text(item, "strong", `${claim.claim_type}: ${claim.costar_value ?? "unknown"}${claim.unit ? ` ${claim.unit}` : ""} · ${claim.verdict}`);
      text(item, "small", claim.explanation || "No supported external comparison.");
      for (const source of claim.sources || []) {
        if (!source.url || !source.url.startsWith("https://")) continue;
        const a = text(item, "a", source.title || source.url);
        a.href = source.url; a.target = "_blank"; a.rel = "noopener noreferrer";
        text(item, "small", ` · ${source.source_date || "source date unavailable"}; retrieved ${source.retrieved_at || verification.retrieved_at}`);
      }
    }
    if (!verification.claims?.length) text(wrap, "small", "No claim-level source matches were available.");
    return summary;
  }
  function renderCard(r) {
    const card = text(document.createElement("div"), "article", undefined, "property-card");
    card.dataset.stableId = r.stable_id;
    const head = text(card, "div", undefined, "card-head");
    const title = text(head, "div", undefined);
    text(title, "h3", r.address || "Address not recorded");
    text(title, "div", `${r.city || "City unknown"}, ${r.state || "State unknown"} · ${propertyType(r)} · ${r.transaction_type === "sale" ? "For sale" : `For lease${r.suite ? ` · Suite ${r.suite}` : ""}`}`, "sub");
    const cls = r.transaction_type === "lease" ? selectedLeaseClass(r) : r.sale_classification;
    text(head, "span", classificationLabel(cls), `badge ${cls === "within_budget" ? "within" : cls === "stretch" ? "stretch" : cls === "over_budget" ? "over" : "unknown"}`);
    const facts = text(card, "div", undefined, "facts");
    appendFact(facts, "Area", areaLabel(r));
    appendFact(facts, r.transaction_type === "sale" ? "Asking price" : "Normalized base rent", amountLabel(r));
    appendFact(facts, "Listing ID", r.listing_id || "Not recorded");
    appendFact(facts, "CoStar property ID", r.property_id ?? "Not recorded");
    appendFact(facts, "Provider listing status", `${r.listing_status || "unknown"}${r.availability_status == null ? "" : ` · status ${r.availability_status}`}`);
    if (r.transaction_type === "lease") {
      const rent = r.rent_normalization || {};
      const raw = r.rent_raw || {};
      const rawRate = raw.low == null && raw.high == null ? "Not supplied" : `${raw.low ?? "?"}–${raw.high ?? "?"} ${rent.raw_basis || "unknown basis"}`;
      appendFact(facts, "Raw CoStar asking rate", rawRate);
      const caps = r.monthly_rent_caps_usd || {};
      const aff = r.lease_affordability || {};
      appendFact(facts, "3-year base-rent cap", `${money.format(caps["3"] || 0)} · ${classificationLabel(aff["3"]?.classification)}`);
      appendFact(facts, "5-year base-rent cap", `${money.format(caps["5"] || 0)} · ${classificationLabel(aff["5"]?.classification)}`);
      appendFact(facts, "10-year base-rent cap", `${money.format(caps["10"] || 0)} · ${classificationLabel(aff["10"]?.classification)}`);
    } else {
      const rawPrice = r.asking_price_raw || {};
      const saleRange = rawPrice.low == null && rawPrice.high == null ? "Not supplied" : `${rawPrice.low ?? "?"}–${rawPrice.high ?? "?"} USD`;
      appendFact(facts, "Recorded CoStar asking range", saleRange);
      appendFact(facts, "Maximum acquisition price", money.format(currentDiscovery?.policy?.maximum_sale_price_usd || 0));
      appendFact(facts, "Sale budget class", classificationLabel(r.sale_classification));
    }
    text(card, "p", r.explanation || "No generated explanation; canonical CoStar data is shown.", "grounded");
    if (r.total_occupancy_cost_status === "unknown" && r.transaction_type === "lease") {
      text(card, "p", "Base rent only. CAM, taxes, insurance, utilities, and total occupancy cost are not established by this record.", "caveat");
    }
    const source = text(card, "p", `CoStar source record ${r.source_reference || r.listing_id || "reference unavailable"}${r.source_updated_at ? ` · source date ${r.source_updated_at}` : " · source date unavailable"} · retrieved ${r.retrieved_at || "time unavailable"}.`, "sub");
    renderConfidence(card, r.confidence || {});
    const actions = text(card, "div", undefined, "card-actions");
    const verify = text(actions, "button", r.verification ? "Verification details" : "Verify listing", "secondary");
    verify.type = "button";
    const refresh = text(actions, "button", "Refresh verification", "secondary"); refresh.type = "button"; refresh.hidden = !r.verification;
    const investigate = text(actions, "button", "Investigate this property", "primary"); investigate.type = "button";
    const verificationBox = text(card, "div", undefined);
    verificationBox.hidden = !r.verification;
    if (r.verification) renderVerification(verificationBox, r.verification);
    async function verifyListing(force) {
      verify.disabled = true; refresh.disabled = true; verify.textContent = force ? "Refreshing…" : "Verifying…";
      try {
        const result = await post("/api/verify", { discovery_id: currentDiscovery.discovery_id, stable_id: r.stable_id, refresh: force });
        r.verification = result.verification;
        r.confidence = result.record?.confidence || r.confidence;
        renderResults();
        updateSummary();
      } catch (err) { verify.textContent = "Verification unavailable"; text(verificationBox, "p", err.message, "caveat"); verificationBox.hidden = false; }
      finally { verify.disabled = false; refresh.disabled = false; }
    }
    verify.addEventListener("click", () => r.verification ? (verificationBox.hidden = !verificationBox.hidden) : verifyListing(false));
    refresh.addEventListener("click", () => verifyListing(true));
    investigate.addEventListener("click", async () => {
      investigate.disabled = true; investigate.textContent = "Investigating…";
      setStage(2); window.scrollTo({ top: 0, behavior: "smooth" });
      const current = { status: "stage2_running", message: "Confirming the selected property, then gathering interior and exterior visual evidence.", progress: [{stage:"queued",message:"Investigation queued"}] };
      renderInvestigation(current);
      try {
        let saved = await post("/api/investigate", { discovery_id: currentDiscovery.discovery_id, stable_id: r.stable_id });
        let handoff = saved.handoff;
        renderInvestigation(handoff);
        while (handoff?.status === "stage2_running") {
          await new Promise(resolve => setTimeout(resolve, 1400));
          saved = await get(`/api/investigation?id=${encodeURIComponent(handoff.handoff_id)}`);
          handoff = saved.handoff; renderInvestigation(handoff);
        }
      } catch (err) { $("#investigation-state").textContent = "Request failed"; $("#investigation-summary").textContent = err.message; }
      finally { investigate.disabled = false; investigate.textContent = "Open investigation"; }
    });
    return card;
  }
  function renderResults() {
    const target = $("#results"); target.replaceChildren();
    if (!currentDiscovery?.results?.length) {
      text(target, "div", "No active commercial listing records were returned for this search. No properties have been fabricated.", "empty");
      return;
    }
    const groups = [
      ["Within budget", "within_budget"], ["Stretch", "stretch"], ["Unknown price or rent", "unknown"], ["Outside budget", "over_budget"],
    ];
    for (const [label, cls] of groups) {
      const rows = currentDiscovery.results.filter(r => (r.transaction_type === "lease" ? selectedLeaseClass(r) : r.sale_classification) === cls);
      if (!rows.length) continue;
      const section = text(target, "section", undefined, "result-group");
      text(section, "h3", `${label} · ${rows.length}`);
      const list = text(section, "div", undefined, "cards");
      rows.slice(0, displayLimit).forEach(r => list.append(renderCard(r)));
      if (rows.length > displayLimit) {
        const more = text(section, "button", `Show ${Math.min(displayLimit, rows.length - displayLimit)} more`, "secondary");
        more.type = "button";
        more.addEventListener("click", () => { displayLimit += 40; renderResults(); });
      }
    }
  }
  function updateSummary() {
    const s = currentDiscovery?.intake_summary;
    if (s) $("#intake-summary").textContent = `${s.city} · ${money.format(s.total_budget_usd)} total budget · ${s.financing === "cash" ? "Cash" : "Financing"} · Business preferences are saved for a later stage.`;
    const trace = currentDiscovery?.trace || {};
    const verifiedCount = currentDiscovery?.results?.filter(r => r.verification).length || 0;
    $("#result-meta").textContent = `${currentDiscovery?.qualifying_count ?? 0} qualifying opportunities · ${currentDiscovery?.excluded_count ?? 0} outside budget · ${trace.source_listing_count ?? 0} source records${trace.inventory_truncated ? " (bounded inventory; not exhaustive)" : ""} · CoStar ${trace.transaction_types_searched?.join(" + ") || "unavailable"}${trace.nemotron?.status === "deterministic_fallback" ? " · Deterministic explanation fallback" : ""} · ${verifiedCount ? `${verifiedCount} listing(s) verified on request` : "No Tavily requests yet"}.`;
  }
  function displayDiscovery(data) {
    currentDiscovery = data;
    displayLimit = 40;
    setStage(1);
    $("#discovery-error").textContent = "";
    $("#horizon").value = data.results?.[0]?.lease_horizon_years ? String(data.results[0].lease_horizon_years) : "";
    $("#allocation").value = String(data.policy?.acquisition_allocation_percent ?? 100);
    $("#allocation-value").textContent = `${$("#allocation").value}%`;
    updateSummary(); renderResults(); updateAllocationText();
  }
  function updateAllocationText() {
    const p = Number($("#allocation").value);
    $("#allocation-value").textContent = `${p}%`;
    const total = currentDiscovery?.policy?.total_budget_usd || currentIntake?.total_budget_usd || 0;
    const occupancy = total * p / 100;
    $("#allocation-note").textContent = `${money.format(occupancy)} currently available for acquisition/occupancy; total project budget remains ${money.format(total)}.`;
    $("#fitout-question").hidden = p !== 100;
  }
  async function reclassify() {
    if (!currentDiscovery) return;
    $("#allocation-value").textContent = `${$("#allocation").value}%`;
    try {
      const data = await post("/api/reclassify", {
        discovery_id: currentDiscovery.discovery_id,
        acquisition_allocation_percent: Number($("#allocation").value),
        lease_horizon_years: $("#horizon").value || null,
      });
      displayDiscovery(data);
    } catch (err) { $("#discovery-error").textContent = err.message; }
  }
  function scheduleReclassify() { updateAllocationText(); clearTimeout(reclassifyTimer); reclassifyTimer = setTimeout(reclassify, 180); }
  intakeForm.addEventListener("submit", async event => {
    event.preventDefault(); status.textContent = "";
    const intake = readForm();
    if (!intake.city || !intake.financing) { status.textContent = "Choose a city and funding method."; return; }
    if (!Number.isFinite(intake.total_budget_usd) || intake.total_budget_usd <= 0) { status.textContent = "Enter a budget greater than $0."; budget.focus(); return; }
    currentIntake = intake; localStorage.setItem(intakeKey, JSON.stringify(intake));
    const button = $("#find"); button.disabled = true; button.textContent = "Searching CoStar…";
    status.textContent = "Checking active CoStar commercial listings. No external web verification runs until you request it.";
    try {
      const result = await post("/api/discovery", { intake });
      localStorage.removeItem("maximus.discovery.v1");
      displayDiscovery(result);
    } catch (err) { status.textContent = `Discovery did not complete: ${err.message} Your intake is saved; retry when CoStar is available.`; }
    finally { button.disabled = false; button.innerHTML = 'Find Properties <span aria-hidden="true">→</span>'; }
  });
  $("#edit-intake").addEventListener("click", () => { setStage(0); fillForm(currentIntake); status.textContent = "Editing intake will require a fresh discovery search."; window.scrollTo({ top: 0, behavior: "smooth" }); });
  $("#investigation-back").addEventListener("click", () => { setStage(currentDiscovery ? 1 : 0); window.scrollTo({ top: 0, behavior: "smooth" }); });
  $("#horizon").addEventListener("change", scheduleReclassify);
  $("#allocation").addEventListener("input", scheduleReclassify);
  $("#fitout-question").addEventListener("change", event => { $("#fitout-amount-wrap").hidden = event.target.value !== "yes"; });
  budget.addEventListener("blur", () => { const n = Number(budget.value.replace(/[,$\s]/g, "")); if (Number.isFinite(n) && n > 0) budget.value = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(n); });
  fillForm(JSON.parse(localStorage.getItem(intakeKey) || "null"));
  const savedInvestigation = new URLSearchParams(window.location.search).get("investigation");
  if (savedInvestigation) {
    get(`/api/investigation?id=${encodeURIComponent(savedInvestigation)}`).then(({handoff}) => {
      if (!handoff?.dossier) throw new Error("Saved investigation is not available yet.");
      currentIntake=handoff.intake || null; fillForm(currentIntake);
      $("#investigation-back").textContent="← Back to intake";
      setStage(2); renderInvestigation(handoff);
    }).catch(error => { status.textContent=`Could not open investigation: ${error.message}`; });
  }
})();
