"use strict";
// Live physical-fit evidence for the "Space & condition" specialist.
// Mounts into any <section class="live-fit" data-property="<CoStar id>" data-use="<use id>">.
(() => {
  const cache = new Map();
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const VERDICT = {
    supported: ["Nothing in the data rules this use out", "good"],
    investigate: ["Investigate before committing", "amber"],
    does_not_fit: ["The evidence rules this use out", "bad"],
  };
  const STATUS = { agrees: "Supported", conflict: "Conflict", unknown: "Unknown" };
  const GROUPS = [
    ["fit", "Fit for the proposed use"],
    ["matterport", "Inside · Matterport scans"],
    ["vexcel", "Outside · Vexcel aerial"],
    ["costar", "Building record · CoStar"],
    ["verify", "Ask before signing"],
  ];
  const LABELS = {
    building_area_sf: "Building area (GBA)", rentable_area_sf: "Rentable area (RBA)", typical_floor_sf: "Typical floor",
    stories: "Stories", loading_docks: "Loading docks", drive_in_bays: "Drive-in bays", electrical_service: "Power",
    parking_spaces: "Parking spaces", sprinklers: "Sprinklers", floor_load_psf: "Floor load", listed_space_sf: "Listed space",
    footprint_sf: "Footprint under the pin", footprint_vs_costar_floor: "Footprint vs CoStar floor",
    roof_height_ft: "Roof height", ground_elevation_ft: "Ground elevation", roof_type: "Roof",
    roof_defects: "Roof defects", roof_condition_score: "Roof condition score", rooftop_ac_units: "Rooftop AC units",
    vehicles_on_parcel: "Vehicles on parcel", scan_used_for_measurements: "Scan used", scan_measured_area_sf: "Scanned area",
    measured_clear_height_ft: "Measured clear height", pickleball_courts_by_area: "Courts by area",
    pickleball_clear_height: "Clear height for play", pickleball_roof_upper_bound: "Roof leaves room?",
    daycare_capacity_by_indoor_area: "Children by indoor area", daycare_outdoor_space_needed_sf: "Outdoor play area needed",
    req_min_clear_height_ft: "Clear height you need", req_min_area_sf: "Minimum space you need",
    req_max_area_sf: "Maximum space you want", req_min_docks: "Loading docks you need",
    req_min_drive_in_bays: "Drive-in doors you need", req_min_parking_spaces: "Parking you need",
    req_min_amps: "Power you need", req_min_floor_load_psf: "Floor load you need",
    req_three_phase: "Three-phase power", req_sprinklers: "Sprinklers",
    lease_asking_rent: "Asking rent", market_rent_range: "Similar leased spaces asked", sale_asking_price: "Asking price", last_sale_price: "Sold",
    capital_vs_lease: "Your capital vs leasing", capital_vs_purchase: "Your capital vs buying",
  };
  const unit = (fact) =>
    fact === "req_min_amps" ? " A" : fact.endsWith("_sf") ? " sq ft" : fact.endsWith("_ft") || fact.endsWith("clear_height") || fact.endsWith("upper_bound")
      ? " ft" : fact.endsWith("_psf") ? " psf" : "";
  const show = (r) => {
    if (r.value === null || r.value === undefined) return "—";
    if (typeof r.value === "boolean") return r.value ? "Yes" : "No";
    if (typeof r.value === "number" && /rent|price|capital_vs/.test(r.fact))
      return "$" + r.value.toLocaleString("en-US") + (r.fact === "lease_asking_rent" ? "/mo" : r.fact === "market_rent_range" ? "/sq ft/yr typical" : r.fact === "capital_vs_lease" ? " yr 1" : "");
    if (typeof r.value === "number")
      return r.fact === "footprint_vs_costar_floor" ? `${r.value}×` : r.value.toLocaleString("en-US") + unit(r.fact);
    return r.value;
  };
  const group = (r, use) =>
    r.source === "checklist" ? "verify" : r.fact.startsWith(`${use}_`) ? "fit" : r.source.startsWith("public:") ? "fit" : r.source;

  function row(r) {
    const src = r.evidence_url
      ? `<a href="${esc(r.evidence_url)}" target="_blank" rel="noopener">${esc(r.source)}</a>`
      : esc(r.source);
    return `<li class="lf-row lf-${esc(r.status)}"><span class="lf-dot" title="${esc(STATUS[r.status])}"></span><div><div class="lf-head"><strong>${esc(LABELS[r.fact] || r.fact.replace(/_/g, " "))}</strong><span class="lf-value">${esc(show(r))}</span></div><p>${esc(r.note)}</p><small>${src}${r.captured_at ? " · " + esc(r.captured_at) : ""} · ${esc(STATUS[r.status])}${r.needs_human ? " · needs a person" : ""}</small></div></li>`;
  }

  function checklist(rows) {
    return `<ul class="lf-checks">${rows.map((r) => `<li>□ ${esc(r.value)}</li>`).join("")}</ul>`;
  }

  function view(d) {
    const [title, tone] = VERDICT[d.verdict] || ["", "amber"];
    const byGroup = Object.fromEntries(GROUPS.map(([k]) => [k, []]));
    d.records.forEach((r) => (byGroup[group(r, d.use)] || byGroup.costar).push(r));
    const fitConflicts = byGroup.fit.filter((r) => r.status === "conflict").length;
    const sourceConflicts = d.records.filter((r) => r.status === "conflict" && !byGroup.fit.includes(r)).length;
    const conflictText = [
      fitConflicts ? `${fitConflicts} fit conflict${fitConflicts === 1 ? "" : "s"}` : "",
      sourceConflicts ? `${sourceConflicts} source conflict${sourceConflicts === 1 ? "" : "s"} to resolve` : "",
    ].filter(Boolean).join(", ") || "No conflicts";
    const errors = Object.keys(d.errors || {});
    return `<div class="lf-top"><div><div class="eyebrow">LIVE EVIDENCE · ${esc(d.address)}</div><h3>${esc(d.use_label)} · ${esc(title)}</h3><p class="small">Judged on ${esc(d.area_basis || "no recorded area")}. ${esc(conflictText)}. Every row shows its source and date.</p></div><span class="lf-verdict lf-${tone}">${esc(d.verdict.replace(/_/g, " "))}</span></div>${GROUPS.filter(([k]) => byGroup[k].length)
      .map(([k, name]) => {
        const body = k === "verify" ? checklist(byGroup[k]) : `<ul class="lf-list">${byGroup[k].map(row).join("")}</ul>`;
        return k === "costar"
          ? `<details class="lf-more"><summary class="lf-group">${name} (${byGroup[k].length})</summary>${body}</details>`
          : `<h4 class="lf-group">${name}</h4>${body}`;
      })
      .join("")}${errors.length ? `<p class="small muted">Provider gaps: ${esc(errors.join(", "))}</p>` : ""}`;
  }

  const REQ_FIELDS = [
    ["label", "Your business", "text", "e.g. Climbing gym"],
    ["min_clear_height_ft", "Min clear height (ft)", "number", "20"],
    ["min_area_sf", "Min space (sq ft)", "number", "6000"],
    ["max_area_sf", "Max space (sq ft)", "number", ""],
    ["min_docks", "Min loading docks", "number", ""],
    ["min_parking_spaces", "Min parking spaces", "number", ""],
    ["three_phase", "Three-phase power", "checkbox", ""],
    ["sprinklers", "Sprinklers", "checkbox", ""],
  ];

  function rankView(d) {
    return `<h4 class="lf-group">What else fits this space?</h4><ul class="lf-rank">${d.uses
      .map((u) => {
        const [, tone] = VERDICT[u.verdict] || ["", "amber"];
        return `<li><span class="lf-verdict lf-${tone}">${esc(u.verdict.replace(/_/g, " "))}</span><div><strong>${esc(u.use_label)}</strong><p>${esc(u.reason)}</p></div></li>`;
      })
      .join("")}</ul>`;
  }

  function reqForm(el) {
    return `<details class="lf-more lf-req"><summary class="lf-group">Check your own requirements</summary><form class="lf-form">${REQ_FIELDS.map(
      ([k, label, type, ph]) =>
        type === "checkbox"
          ? `<label class="lf-check"><input type="checkbox" name="${k}"> ${esc(label)}</label>`
          : `<label>${esc(label)}<input name="${k}" type="${type}" min="0" placeholder="${esc(ph)}"></label>`,
    ).join("")}<button class="secondary" type="submit">Check this space</button></form><div class="lf-req-out"></div></details>`;
  }

  async function runRequirements(form, el) {
    const out = form.parentElement.querySelector(".lf-req-out");
    const q = new URLSearchParams({ property_id: el.dataset.property, use: "custom" });
    new FormData(form).forEach((v, k) => {
      if (v !== "" && v !== null) q.set(k, k === "three_phase" || k === "sprinklers" ? "yes" : v);
    });
    if ([...q.keys()].filter((k) => !["property_id", "use", "label"].includes(k)).length === 0) {
      out.innerHTML = `<p class="small muted">Add at least one requirement.</p>`;
      return;
    }
    out.innerHTML = `<p class="small muted">Checking…</p>`;
    try {
      const d = await fetch(`/api/space-fit?${q}`).then((r) => r.json());
      if (d.error) throw new Error(d.error);
      const reqs = d.records.filter((r) => r.fact.startsWith("req_"));
      const [title, tone] = VERDICT[d.verdict] || ["", "amber"];
      out.innerHTML = `<div class="lf-top"><h3>${esc(d.use_label)} · ${esc(title)}</h3><span class="lf-verdict lf-${tone}">${esc(d.verdict.replace(/_/g, " "))}</span></div><ul class="lf-list">${reqs.map(row).join("")}</ul>`;
    } catch (err) {
      out.innerHTML = `<p class="small muted">Could not check: ${esc(err.message)}</p>`;
    }
  }

  async function loadExtras(el) {
    const slot = el.querySelector(".lf-extras");
    if (!slot) return;
    slot.innerHTML = reqForm(el);
    slot.querySelector(".lf-form").addEventListener("submit", (e) => {
      e.preventDefault();
      runRequirements(e.target, el);
    });
    const key = `rank:${el.dataset.property}`;
    if (!cache.has(key))
      cache.set(key, fetch(`/api/space-fit/rank?property_id=${encodeURIComponent(el.dataset.property)}`).then((r) => r.json()));
    try {
      const d = await cache.get(key);
      if (d.error) throw new Error(d.error);
      if (slot.isConnected) slot.insertAdjacentHTML("afterbegin", rankView(d));
    } catch (err) {
      cache.delete(key);
    }
  }

  async function load(el) {
    const key = `${el.dataset.property}:${el.dataset.use}`;
    if (el.dataset.loaded === key) return;
    el.dataset.loaded = key;
    el.innerHTML = `<p class="small muted">Checking CoStar, Matterport and Vexcel for this space…</p>`;
    if (!cache.has(key))
      cache.set(key, fetch(`/api/space-fit?property_id=${encodeURIComponent(el.dataset.property)}&use=${encodeURIComponent(el.dataset.use)}`)
        .then((r) => r.json()));
    try {
      const d = await cache.get(key);
      if (d.error) throw new Error(d.error);
      if (el.isConnected) {
        el.innerHTML = view(d) + `<div class="lf-extras"></div>`;
        loadExtras(el);
      }
    } catch (err) {
      cache.delete(key);
      el.dataset.loaded = "";
      if (el.isConnected) el.innerHTML = `<p class="small muted">Live evidence unavailable: ${esc(err.message)}</p>`;
    }
  }

  const DEAL_GROUPS = [
    ["capital", "Your capital", (r) => r.fact.startsWith("capital_")],
    ["lease", "Lease: asking rents in this building", (r) => r.fact === "lease_asking_rent"],
    ["market", "Market check: what similar spaces that leased were asking", (r) => r.fact === "market_rent_range"],
    ["buy", "Buy: for-sale listing", (r) => r.fact === "sale_asking_price"],
    ["sold", "Sale history", (r) => r.fact === "last_sale_price"],
  ];

  function dealView(d) {
    const paths = d.paths.length ? d.paths.map((p) => `<span class="lf-verdict lf-good">${esc(p)}</span>`).join(" ")
      : `<span class="lf-verdict lf-amber">not on the market</span>`;
    return `<div class="lf-top"><div><div class="eyebrow">LIVE DEAL FACTS · ${esc(d.address)}</div><h3>What this property asks, and what it last sold for</h3><p class="small">From CoStar listings and sale comps. Asking figures, not signed or sold prices. The capital check states gaps; it does not choose lease or buy.</p></div><div>${paths}</div></div>${DEAL_GROUPS.map(([k, name, test]) => {
      const rows = d.records.filter(test);
      if (!rows.length) return "";
      const shown = rows.slice(0, 4), rest = rows.slice(4);
      return `<h4 class="lf-group">${name}</h4><ul class="lf-list">${shown.map(row).join("")}</ul>${rest.length ? `<details class="lf-more"><summary class="small">${rest.length} more</summary><ul class="lf-list">${rest.map(row).join("")}</ul></details>` : ""}`;
    }).join("")}`;
  }

  async function loadDeal(el) {
    const fit = [...cache.entries()].find(([k]) => k.startsWith(`${el.dataset.property}:`));
    const fitResult = fit ? await fit[1].catch(() => null) : null;
    const q = new URLSearchParams({ property_id: el.dataset.property });
    if (el.dataset.capital) q.set("capital", el.dataset.capital);
    if (fitResult && fitResult.suite) q.set("suite", fitResult.suite);
    const key = `deal:${q}`;
    if (el.dataset.loaded === key) return;
    el.dataset.loaded = key;
    el.innerHTML = `<p class="small muted">Reading CoStar listings and sale comps…</p>`;
    if (!cache.has(key)) cache.set(key, fetch(`/api/deal?${q}`).then((r) => r.json()));
    try {
      const d = await cache.get(key);
      if (d.error) throw new Error(d.error);
      if (el.isConnected) el.innerHTML = dealView(d);
    } catch (err) {
      cache.delete(key);
      el.dataset.loaded = "";
      if (el.isConnected) el.innerHTML = `<p class="small muted">Deal facts unavailable: ${esc(err.message)}</p>`;
    }
  }

  window.spaceFit = {
    mount: (root) => {
      root.querySelectorAll(".live-fit[data-property]").forEach(load);
      root.querySelectorAll(".live-deal[data-property]").forEach(loadDeal);
    },
  };
})();
