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
  };
  const unit = (fact) =>
    fact.endsWith("_sf") ? " sq ft" : fact.endsWith("_ft") || fact.endsWith("clear_height") || fact.endsWith("upper_bound")
      ? " ft" : fact.endsWith("_psf") ? " psf" : "";
  const show = (r) => {
    if (r.value === null || r.value === undefined) return "—";
    if (typeof r.value === "boolean") return r.value ? "Yes" : "No";
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
      if (el.isConnected) el.innerHTML = view(d);
    } catch (err) {
      cache.delete(key);
      el.dataset.loaded = "";
      if (el.isConnected) el.innerHTML = `<p class="small muted">Live evidence unavailable: ${esc(err.message)}</p>`;
    }
  }

  window.spaceFit = { mount: (root) => root.querySelectorAll(".live-fit[data-property]").forEach(load) };
})();
