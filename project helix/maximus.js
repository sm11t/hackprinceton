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
  let reclassifyTimer = null;
  let displayLimit = 40;

  async function post(path, body) {
    const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
    return data;
  }
  function setStage(stage) {
    intakeView.hidden = stage !== 0;
    discoveryView.hidden = stage !== 1;
    $("#stage-indicator").textContent = stage === 0 ? "STAGE 0 · YOUR STARTING POINT" : "STAGE 1 · PROPERTY DISCOVERY";
    $("#step-count").textContent = stage === 0 ? "01 / 03" : "02 / 03";
    $("#progress").style.width = stage === 0 ? "12%" : "44%";
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
      investigate.disabled = true; investigate.textContent = "Saving…";
      try {
        const saved = await post("/api/investigate", { discovery_id: currentDiscovery.discovery_id, stable_id: r.stable_id });
        $("#stage2").hidden = false; $("#stage2").scrollIntoView({ behavior: "smooth", block: "center" });
        text($("#stage2"), "p", `Handoff ${saved.handoff.handoff_id} saved. This is a placeholder; Stage 2 was not run.`);
      } catch (err) { text(card, "p", err.message, "caveat"); }
      finally { investigate.disabled = false; investigate.textContent = "Investigate this property"; }
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
    $("#stage2").hidden = true;
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
  $("#horizon").addEventListener("change", scheduleReclassify);
  $("#allocation").addEventListener("input", scheduleReclassify);
  $("#fitout-question").addEventListener("change", event => { $("#fitout-amount-wrap").hidden = event.target.value !== "yes"; });
  budget.addEventListener("blur", () => { const n = Number(budget.value.replace(/[,$\s]/g, "")); if (Number.isFinite(n) && n > 0) budget.value = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(n); });
  fillForm(JSON.parse(localStorage.getItem(intakeKey) || "null"));
})();
