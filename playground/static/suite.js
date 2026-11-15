/* Venture Suite: "I have a budget" flow.
   My ventures -> budget -> scan -> opportunities -> shortlist -> investigate -> decide -> plan.
   Every number comes from /api/opportunities or /api/venture/review; this file only lays it out. */
(() => {
  "use strict";

  const USER = "demo";
  const STAGES = ["budget", "scan", "opportunities", "shortlist", "investigate", "decide", "plan"];
  const STAGE_NAMES = { budget: "Budget", scan: "Scan", opportunities: "Opportunities", shortlist: "Shortlist",
    investigate: "Investigate", decide: "Decide", plan: "Plan & track" };
  // Four starting points, one toolkit: the same stages and agents, in a different order (Jessenth's archetypes).
  const FLOWS = { budget: STAGES, idea: ["budget", "scan", "shortlist", "investigate", "decide", "plan"],
    space: ["budget", "scan", "opportunities", "investigate", "decide", "plan"], both: ["budget", "investigate", "decide", "plan"] };
  const KIND_LABEL = { budget: "I have a budget", idea: "I know what to open", space: "I have a space", both: "I know what and where" };
  const KIND_SHORT = { budget: "Budget", idea: "Business", space: "Space", both: "Business + space" };
  const KIND_STAGE = { idea: { budget: "Business & budget", scan: "Scan places" },
    space: { budget: "Your space", scan: "Building check", opportunities: "What fits here" }, both: { budget: "What & where" } };
  const kindOf = (v) => { v = v === undefined ? state.v : v; return v && FLOWS[v.kind] ? v.kind : "budget"; };
  const flow = (v) => FLOWS[kindOf(v)];
  const stageName = (s, v) => (KIND_STAGE[kindOf(v)] || {})[s] || STAGE_NAMES[s];
  const nextStage = (s) => { const f = flow(); return f[Math.min(f.length - 1, f.indexOf(s) + 1)]; };
  const STATUS_FOR = { budget: "exploring", scan: "exploring", opportunities: "exploring", shortlist: "shortlisted",
    investigate: "investigating", decide: "investigating", plan: "verifying" };
  const GROUPS = ["Sports & fitness", "Food & drink", "Health", "Personal services", "Children & education", "Retail",
    "Auto & storage"];
  const PLACES = [
    ["Downtown", 29.7604, -95.3698], ["The Heights", 29.798, -95.398], ["Galleria / Uptown", 29.739, -95.463],
    ["Energy Corridor", 29.783, -95.62], ["Katy", 29.7858, -95.8245], ["Cypress", 29.9691, -95.6972],
    ["Spring / Champions", 30.0, -95.53], ["The Woodlands", 30.1658, -95.4613], ["Sugar Land", 29.6197, -95.6349],
    ["Pearland", 29.5636, -95.286], ["Pasadena", 29.6911, -95.2091], ["Humble / Kingwood", 30.0, -95.25],
  ];
  const AGENT_JOBS = {
    planner: "Maps the request", site: "Finds the point", building: "Can the building host it?",
    residents: "Who lives here (ACS)", competitors: "Who already serves it", momentum: "Who is moving in",
    lookalike: "Looks like places that have it?", coordinator: "Combines neighborhood signals",
    money: "Cash to open", deal: "Is the rent known?", records: "Do the records agree?",
    permits: "What must be approved", verdict: "One call",
  };

  const state = { ventures: [], v: null, industries: null, opp: null, oppKey: "", reviews: {}, reviewErr: {},
    tab: null, traceOpen: null, filter: "all", savedAt: null, timers: [], ctrls: [] };
  const app = document.getElementById("app");

  // ---------- helpers ----------
  // The backend clips some long reasons at a fixed length; mark the cut instead of ending mid-word.
  const tidy = (t) => { t = String(t ?? ""); return t.length >= 150 && !/[.!?)]$/.test(t) ? t.replace(/\s+\S*$/, "") + "…" : t; };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const money = (n) => (n == null || isNaN(n) ? "—" : "$" + Math.round(n).toLocaleString("en-US"));
  const kmoney = (n) => {
    if (n == null || isNaN(n)) return "—";
    if (Math.abs(n) >= 1e6) return "$" + (n / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M";
    return "$" + Math.round(n / 1000).toLocaleString("en-US") + "k";
  };
  const num = (n) => (n == null ? "—" : Math.round(n).toLocaleString("en-US"));
  const src = (name) => `<span class="src" title="Source">${esc(name)}</span>`;
  const chip = (cls, text, title) => `<span class="chip ${cls}"${title ? ` title="${esc(title)}"` : ""}>${esc(text)}</span>`;
  const pairKey = (p) => `${p.business}|${p.property_id}|${p.suite ?? ""}`;
  const stageIdx = (s, v) => Math.max(0, flow(v).indexOf(s));
  const ago = (iso) => {
    const t = Date.parse(iso); if (!t) return "";
    const m = Math.round((Date.now() - t) / 60000);
    if (m < 1) return "just now"; if (m < 60) return `${m} min ago`;
    const h = Math.round(m / 60); return h < 24 ? `${h} h ago` : `${Math.round(h / 24)} d ago`;
  };
  async function api(path, opts) {
    const r = await fetch(path, opts);
    let body; try { body = await r.json(); } catch { body = { error: `Server answered ${r.status}` }; }
    if (!r.ok || (body && body.error)) throw new Error(body.error || r.statusText);
    return body;
  }
  const post = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  function toast(msg) {
    const t = document.getElementById("toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, 2600);
  }
  function clearTimers() {
    state.timers.forEach(clearTimeout); state.timers = [];
    state.ctrls.forEach((c) => { try { c && c.dispose && c.dispose(); } catch { /* ignore */ } }); state.ctrls = [];
  }
  const later = (fn, ms) => state.timers.push(setTimeout(fn, ms));
  const has3d = () => !!(window.Suite3D && window.Suite3D.ok && window.Suite3D.ok());
  function thumb(kind, opts) {
    try { return has3d() ? window.Suite3D.thumb(kind, opts || {}) : null; } catch { return null; }
  }
  function archetype(pair) {
    const r = ((pair.building && pair.building.reasons) || []).join(" ").toLowerCase();
    if (/apartment|multi-family|residential/.test(r)) return "apartments";
    if (/industrial|warehouse/.test(r)) return "warehouse";
    if (/flex/.test(r)) return "flex";
    if (/office/.test(r)) return "office";
    if (/retail|shopping|strip|storefront/.test(r)) return "retail";
    if (/hospitality|hotel|mixed/.test(r)) return "mixed";
    return "unknown";
  }
  const ARCH_LABEL = { warehouse: "Warehouse", flex: "Flex building", office: "Office building", retail: "Retail strip",
    mixed: "Mixed-use", apartments: "Apartments", unknown: "Building type unknown" };
  function buildingImg(pair, size) {
    const a = archetype(pair);
    const url = thumb(a, { size: size || 160 });
    return url ? `<img src="${url}" alt="${esc(ARCH_LABEL[a])}" title="${esc(ARCH_LABEL[a])}">` : `<span title="${esc(ARCH_LABEL[a])}">${ic("building", 22)}</span>`;
  }
  function propImg(group) {
    const url = thumb("prop:" + (GROUPS.includes(group) ? group : "other"), { size: 112 });
    return url ? `<img src="${url}" alt="">` : `<span>${esc((group || "?")[0])}</span>`;
  }
  function agentImg(name, px) {
    const url = thumb("agent:" + name, { size: 88 }), dim = px ? ` style="width:${px}px;height:${px}px"` : "";
    return url ? `<img src="${url}" alt=""${dim}>` : `<span class="fallback"${dim}>${esc(name.slice(0, 2).toUpperCase())}</span>`;
  }
  const ICONS = {
    plus: '<path d="M12 5v14M5 12h14"/>',
    right: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    left: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    wallet: '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18M16 14.5h2"/>',
    bulb: '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    building: '<rect x="5" y="3" width="14" height="18" rx="1"/><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2"/>',
    brief: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M3 13h18"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3M15 8l2 2"/>',
    shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    landmark: '<path d="M3 21h18M4 10h16M12 3l9 5H3zM6 10v8M10 10v8M14 10v8M18 10v8"/>',
    compass: '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
    spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
    ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    grid: '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
  };
  const ic = (n, s) => `<svg class="ic" width="${s || 16}" height="${s || 16}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[n] || ""}</svg>`;
  const ext = (url, text) => (url ? `<a class="ext" href="${esc(url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${esc(text || "Source")}${ic("ext", 12)}</a>` : "");
  const cap = (t) => (t ? t[0].toUpperCase() + t.slice(1) : "");
  function crumbs(list) {
    const el = document.getElementById("crumbs"); if (!el) return;
    el.innerHTML = list.map(([t, href], k) => (k ? `<span class="sep">/</span>` : "") + (href ? `<a href="${href}">${esc(t)}</a>` : `<span class="cur">${esc(t)}</span>`)).join("");
  }

  // ---------- status semantics ----------
  const FIT = { fits: ["green", "Fits"], check: ["amber", "Fits if checks pass"], no: ["red", "Can't host"] };
  const AFFORD = { within: ["green", "Within budget"], stretch: ["amber", "Low case only"],
    rent_unknown: ["grey", "Rent not listed"], over: ["red", "Over budget"] };
  const DEMAND = { supported: ["green", "Neighborhood supports"], mixed: ["amber", "Mixed neighborhood"],
    weak: ["red", "Weak neighborhood"], unknown: ["grey", "Neighborhood unknown"] };
  const VERDICT_CLS = { GO: "go", CONDITIONAL: "conditional", "NO-GO": "no-go" };
  const VERDICT_CHIP = { GO: "green", CONDITIONAL: "amber", "NO-GO": "red" };
  const VLABEL = { GO: "Go", CONDITIONAL: "Conditional", "NO-GO": "No-go" };
  const verdictBadge = (v, sm) => `<div class="verdict v-${VERDICT_CLS[v] || "unknown"}${sm ? " sm" : ""}"><span class="verdict-k">Verdict</span><span class="verdict-v"><i></i>${esc(VLABEL[v] || v || "Pending")}</span></div>`;
  const STATUS_CHIP = { exploring: "blue", shortlisted: "blue", investigating: "blue", verifying: "amber", ready: "green", paused: "grey", dropped: "red" };
  const look = (map, key) => map[key] || ["grey", key ? String(key) : "Unknown"];
  const costSrc = (basis) => (basis === "itemized" ? "FDD benchmark" : basis ? `FDD benchmark · ${basis}` : "FDD benchmark");
  const rentSrc = (rent) => (!rent || rent.monthly == null ? "not listed" : /model|comps|similar/i.test(rent.source || "") ? "rent model" : "CoStar");
  const demandSrc = (key) => (key === "childcare" ? "ACS · Texas HHSC · CoStar" : "ACS · OSM · CoStar");

  // ---------- data ----------
  async function industries() {
    if (!state.industries) {
      try { state.industries = await api("/api/neighborhood/industries"); } catch { state.industries = []; }
    }
    return state.industries;
  }
  function inputs() { return Object.assign({ budget: 500000, reserve: 50000, area: { mode: "anywhere", radius: 10 }, exclude: [], directions: [], reached: 0 }, (state.v && state.v.inputs) || {}); }
  async function opportunities() {
    const i = inputs(), list = await industries();
    const exclude = list.filter((x) => (i.exclude || []).includes(x.group)).map((x) => x.key);
    const q = new URLSearchParams({ budget: i.budget, reserve: i.reserve, top: 20 }), k = kindOf();
    if (k !== "space" && i.area && i.area.mode === "near" && i.area.lat) { q.set("lat", i.area.lat); q.set("lon", i.area.lon); q.set("radius", i.area.radius || 10); }
    if (k === "idea" && i.business) q.set("include", i.business);
    if (k === "space" && i.place) q.set("property_id", i.place.property_id);
    if (exclude.length) q.set("exclude", exclude.join(","));
    const key = q.toString();
    if (state.opp && state.oppKey === key) return state.opp;
    state.opp = await api("/api/opportunities?" + key); state.oppKey = key;
    return state.opp;
  }
  async function review(p, explain) {
    const i = inputs();
    const q = new URLSearchParams({ business: p.business, property_id: p.property_id, suite: p.suite || "", budget: i.budget, reserve: i.reserve, delay: 3 });
    if (explain) q.set("explain", "1");
    return api("/api/venture/review?" + q.toString());
  }
  function summaryLine(v) {
    const i = Object.assign({}, v.inputs || {});
    if (v.chosen) return `${v.chosen.label} at ${v.chosen.address}${v.chosen.verdict ? ` · ${v.chosen.verdict}` : ""}`;
    const parts = [];
    if (i.budget) parts.push(`${kmoney(i.budget)} budget, keep ${kmoney(i.reserve || 0)}`);
    if ((i.directionLabels || []).length) parts.push(i.directionLabels.join(", "));
    if ((v.shortlist || []).length) parts.push(`${v.shortlist.length} place${v.shortlist.length > 1 ? "s" : ""} shortlisted`);
    return parts.join(" · ") || "Not started: set a budget";
  }
  async function save(changes, quiet) {
    if (!state.v) return;
    try {
      const merged = Object.assign({}, state.v, changes);
      const prog = merged.summary && merged.summary.progress;
      changes.summary = Object.assign({}, merged.summary || {}, { line: summaryLine(merged), progress: prog || null });
      state.v = await post(`/api/ventures/${encodeURIComponent(state.v.id)}?user=${USER}`, changes);
      state.savedAt = new Date();
      const s = document.querySelector(".saved"); if (s) s.textContent = "Saved " + state.savedAt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    } catch (e) { if (!quiet) toast("Could not save: " + e.message); }
  }
  function setInputs(patch, quiet) { return save({ inputs: Object.assign({}, inputs(), patch) }, quiet); }
  async function goStage(stage) {
    const i = inputs(), idx = stageIdx(stage);
    const changes = { stage, inputs: Object.assign({}, i, { reached: Math.max(i.reached || 0, idx) }) };
    if (!state.v.chosen || idx < flow().length - 1) changes.status = STATUS_FOR[stage];
    if (state.v.status === "ready" && stage === "plan") delete changes.status;
    await save(changes);
    location.hash = `#/v/${state.v.id}/${stage}`;
  }

  // ---------- router ----------
  async function route() {
    clearTimers();
    const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
    try {
      if (parts[0] === "new") return renderNew();
      if (parts[0] === "v" && parts[1]) {
        if (!state.v || state.v.id !== parts[1]) {
          state.v = await api(`/api/ventures/${encodeURIComponent(parts[1])}?user=${USER}`);
          state.reviews = {}; state.reviewErr = {}; state.tab = null;
        }
        const stage = flow().includes(parts[2]) ? parts[2] : flow().includes(state.v.stage) ? state.v.stage : "budget";
        return renderVenture(stage);
      }
      return renderHome();
    } catch (e) {
      app.innerHTML = `<div class="error">${esc(e.message)}</div><p style="margin-top:12px"><a href="#/">Back to My ventures</a></p>`;
    }
  }
  window.addEventListener("hashchange", route);

  // ---------- My ventures ----------
  async function renderHome() {
    state.v = null;
    crumbs([["My ventures"]]);
    app.innerHTML = `<div class="loading"><span class="spinner"></span>Loading your ventures…</div>`;
    state.ventures = await api(`/api/ventures?user=${USER}`);
    const vs = state.ventures;
    const active = vs.filter((v) => !["ready", "paused", "dropped"].includes(v.status)).length;
    const committed = vs.filter((v) => v.chosen).length, ready = vs.filter((v) => v.status === "ready").length;
    const checks = vs.reduce((a, v) => { const g = v.summary && v.summary.progress; return g && g.total ? [a[0] + g.done, a[1] + g.total] : a; }, [0, 0]);
    const rows = vs.map((v) => {
      const f = flow(v), idx = stageIdx(v.stage, v), prog = v.summary && v.summary.progress;
      const seg = f.map((s, k) => `<span class="${k < idx ? "done" : k === idx ? "now" : ""}"></span>`).join("");
      return `<tr data-id="${esc(v.id)}" tabindex="0">
        <td><div class="vn">${esc(v.name)}</div><div class="vs">${esc(((v.summary && v.summary.line) || summaryLine(v)).replace(/· (GO|CONDITIONAL|NO-GO)$/, (m, x) => "· " + VLABEL[x]))}</div></td>
        <td class="hide-sm muted">${esc(KIND_SHORT[kindOf(v)])}</td>
        <td><div class="seg7" title="Step ${idx + 1} of ${f.length}">${seg}</div><div class="small muted">${esc(stageName(v.stage, v) || v.stage)}</div></td>
        <td>${chip(STATUS_CHIP[v.status] || "grey", cap(v.status))}</td>
        <td class="hide-sm">${prog && prog.total ? `<div class="meter"><div class="check-bar"><i style="width:${Math.round(100 * prog.done / prog.total)}%"></i></div><span class="small num">${prog.done}/${prog.total}</span></div>` : `<span class="faint">—</span>`}</td>
        <td class="hide-sm muted small" style="white-space:nowrap">${esc(ago(v.updated_at))}</td>
      </tr>`;
    }).join("");
    app.innerHTML = `
      <div class="page-head">
        <div><div class="eyebrow">Workspace</div><h1>My ventures</h1>
          <p class="lede">Each venture is one saved workflow, from a budget to a place you can sign for. Pick up where you left off.</p></div>
        <a class="btn primary" href="#/new">${ic("plus")}New venture</a>
      </div>
      <div class="kpis">
        <div class="glass kpi"><div class="k">Ventures</div><div class="v">${vs.length}</div><div class="s">${active} in progress</div></div>
        <div class="glass kpi"><div class="k">Committed to a place</div><div class="v">${committed}</div><div class="s">After a reviewed verdict</div></div>
        <div class="glass kpi"><div class="k">Checks answered</div><div class="v">${checks[1] ? `${checks[0]}<span class="faint" style="font-size:16px;font-weight:500"> / ${checks[1]}</span>` : "—"}</div><div class="s">Across committed ventures</div></div>
        <div class="glass kpi"><div class="k">Ready to sign</div><div class="v">${ready}</div><div class="s">Every check answered</div></div>
      </div>
      <div class="glass table-card">
        ${vs.length ? `<div class="table-scroll"><table class="vt">
          <thead><tr><th>Venture</th><th class="hide-sm">Type</th><th>Stage</th><th>Status</th><th class="hide-sm">Checks</th><th class="hide-sm">Updated</th></tr></thead>
          <tbody>${rows}</tbody></table></div>`
        : `<div class="empty"><div>No ventures yet. Start one; it saves at every step.</div><a class="btn primary" href="#/new">${ic("plus")}New venture</a></div>`}
      </div>`;
    app.querySelectorAll("tr[data-id]").forEach((tr) => {
      const go = () => { location.hash = `#/v/${tr.dataset.id}`; };
      tr.onclick = go; tr.onkeydown = (e) => { if (e.key === "Enter") go(); };
    });
  }

  function renderNew() {
    crumbs([["My ventures", "#/"], ["New venture"]]);
    app.innerHTML = `
      <div class="page-head"><div><div class="eyebrow">New venture</div><h1>What do you start with?</h1>
        <p class="lede">We start from what you already know and check everything else against CoStar listings and public data.</p></div>
        <a class="btn ghost" href="#/">${ic("left")}My ventures</a></div>
      <div class="grid chooser four">
        <button class="card clickable choice" data-kind="budget">
          <div class="icon">${ic("wallet", 20)}</div><h3>I have a budget</h3>
          <p>You know what you can put in, not what to open or where. We scan every listed Houston space against 26 kinds of business.</p>
          ${chip("blue", "Knows neither")}
        </button>
        <button class="card clickable choice" data-kind="idea">
          <div class="icon">${ic("bulb", 20)}</div><h3>I know what to open</h3>
          <p>You know the business, not where. We check every listed space for it: fit, cash, neighborhood and who permits it.</p>
          ${chip("blue", "Knows the business")}
        </button>
        <button class="card clickable choice" data-kind="space">
          <div class="icon">${ic("building", 20)}</div><h3>I have a space</h3>
          <p>You have a building in mind. We check the building first (who permits it, can it be commercial), then what fits and pays there.</p>
          ${chip("blue", "Knows the place")}
        </button>
        <button class="card clickable choice" data-kind="both">
          <div class="icon">${ic("check", 20)}</div><h3>I know what and where</h3>
          <p>One business in one space: straight to the 13-agent review and a Go, Conditional or No-go with every reason.</p>
          ${chip("blue", "Knows both")}
        </button>
      </div>
      <p class="muted small" style="margin-top:12px">Same agents and gates in every case; only the order changes with what you already know.</p>`;
    app.querySelectorAll(".choice[data-kind]").forEach((btn) => btn.onclick = async () => {
      const kind = btn.dataset.kind; btn.disabled = true;
      try {
        const n = (await api(`/api/ventures?user=${USER}`)).length + 1;
        state.v = await post("/api/ventures", { user: USER, kind, name: `${KIND_SHORT[kind]} venture ${n}` });
        state.reviews = {}; state.opp = null;
        location.hash = `#/v/${state.v.id}/budget`;
      } catch (e) { toast(e.message); btn.disabled = false; }
    });
  }

  // ---------- venture shell: header + stepper ----------
  function lockIns(i) {
    const v = state.v, o = state.opp;
    const reviewed = Object.values(state.reviews);
    return {
      budget: kindOf() === "space" && i.place ? esc(i.place.address.split(",")[0]) : kindOf() === "both" && i.place && i.businessLabel ? `${esc(i.businessLabel)} · ${esc(i.place.address.split(",")[0])}` : kindOf() === "idea" && i.businessLabel ? `${esc(i.businessLabel)} · <b>${kmoney(i.budget - i.reserve)}</b>` : i.budget ? `<b>${kmoney(i.budget - i.reserve)}</b> to open with` : "",
      scan: kindOf() === "space" ? (i.site ? (i.site.ok ? "Building checked" : "Stopped here") : "") : o ? `<b>${num(o.funnel.authority_identified ?? o.funnel.neighborhood_support)}</b> pass every gate` : (i.reached >= 1 ? "Scanned" : ""),
      opportunities: (i.directionLabels || []).length ? esc(i.directionLabels.join(", ")) : "",
      shortlist: (v.shortlist || []).length ? `<b>${v.shortlist.length}</b> place${v.shortlist.length > 1 ? "s" : ""}` : "",
      investigate: reviewed.length ? reviewed.map((r) => `<b>${esc(VLABEL[r.verdict] || r.verdict)}</b>`).join(" · ") : "",
      decide: v.chosen ? `${esc(v.chosen.label)} · ${esc(v.chosen.address.split(",")[0])}` : "",
      plan: v.summary && v.summary.progress && v.summary.progress.total ? `<b>${v.summary.progress.done}/${v.summary.progress.total}</b> checks answered` : "",
    };
  }
  const savedText = () => (state.savedAt ? "Saved " + state.savedAt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "Saved");
  function vtop(stage) {
    const i = inputs(), v = state.v, cur = stageIdx(stage), reached = Math.max(i.reached || 0, cur), lock = lockIns(i);
    const area = i.area && i.area.mode === "near" && i.area.place ? `${i.area.place} · ${i.area.radius} mi` : "All of Houston";
    const steps = flow().map((s, k) => {
      const cls = k === cur ? "now" : k <= reached ? "done" : "locked";
      return `<li class="step ${cls}"><button data-stage="${s}" ${k > reached ? "disabled" : ""} aria-current="${k === cur ? "step" : "false"}">
        <span class="idx">${k !== cur && k <= reached ? ic("check", 13) : k + 1}</span><span class="label">${esc(stageName(s))}</span>
        <span class="sub">${k === cur ? "In progress" : lock[s] || ""}</span></button></li>`;
    }).join("");
    return `<div class="glass vhead">
        <div class="vhead-main"><input id="vname" class="vname" value="${esc(v.name)}" aria-label="Venture name" maxlength="80">
          <div class="vhead-sub">${chip(STATUS_CHIP[v.status] || "grey", cap(v.status))}<span>${esc(KIND_LABEL[kindOf()])}</span><span class="saved">${savedText()}</span></div></div>
        <dl class="facts">
          <div><dt>Budget</dt><dd>${kmoney(i.budget)}</dd></div>
          <div><dt>Reserve</dt><dd>${kmoney(i.reserve)}</dd></div>
          <div><dt>To open with</dt><dd>${kmoney(i.budget - i.reserve)}</dd></div>
          ${i.businessLabel && kindOf() !== "budget" ? `<div><dt>Business</dt><dd>${esc(i.businessLabel)}</dd></div>` : ""}
          ${i.place && (kindOf() === "space" || kindOf() === "both") ? `<div><dt>Place</dt><dd>${esc(i.place.address.split(",")[0])}</dd></div>` : i.businessLabel && kindOf() === "idea" ? "" : `<div><dt>Area</dt><dd>${esc(area)}</dd></div>`}
        </dl>
      </div>
      <ol class="glass stepper" aria-label="Steps">${steps}</ol>`;
  }
  function bindTop(stage) {
    crumbs([["My ventures", "#/"], [state.v.name, `#/v/${state.v.id}`], [stageName(stage)]]);
    app.querySelectorAll(".step button[data-stage]").forEach((b) => { b.onclick = () => { if (!b.disabled) goStage(b.dataset.stage); }; });
    const name = document.getElementById("vname");
    name.onchange = () => { const n = name.value.trim(); if (n) save({ name: n }).then(() => crumbs([["My ventures", "#/"], [state.v.name, `#/v/${state.v.id}`], [stageName(stage)]])); };
  }
  async function renderVenture(stage) {
    app.innerHTML = `<div class="venture"><div id="vtop" class="venture">${vtop(stage)}</div><section id="stage"><div class="loading"><span class="spinner"></span>Loading…</div></section></div>`;
    bindTop(stage);
    const el = document.getElementById("stage");
    try {
      await ({ budget: stageBudget, scan: kindOf() === "space" ? stageSite : stageScan, opportunities: stageOpportunities, shortlist: stageShortlist,
        investigate: stageInvestigate, decide: stageDecide, plan: stagePlan })[stage](el);
    } catch (e) {
      el.innerHTML = `<div class="error">${esc(e.message)}</div>`;
    }
    if (state.v.stage !== stage) save({ stage }, true);
  }
  function refreshRail(stage) {
    const t = document.getElementById("vtop"); if (!t) return;
    t.innerHTML = vtop(stage); bindTop(stage);
  }
  const head = (stage, title, lede, right) => `<div class="stage-head"><div><div class="eyebrow">Step ${flow().indexOf(stage) + 1} of ${flow().length} · ${esc(stageName(stage))}</div>
    <h1>${title}</h1>${lede ? `<p class="lede">${lede}</p>` : ""}</div>${right ? `<div class="actions">${right}</div>` : ""}</div>`;

  // ---------- Stage 1: budget ----------
  async function stageBudget(el) {
    const i = inputs(), kind = kindOf(), list = await industries();
    const wantBiz = kind === "idea" || kind === "both", wantPlace = kind === "space" || kind === "both";
    const groups = [...new Set(list.map((x) => x.group))];
    const bizField = wantBiz ? `<div class="field"><label for="biz">What do you want to open?</label>
        <select class="select" id="biz"><option value="">Choose a business…</option>${groups.map((g) => `<optgroup label="${esc(g)}">${list.filter((x) => x.group === g).map((x) => `<option value="${esc(x.key)}" ${x.key === i.business ? "selected" : ""}>${esc(x.label)}</option>`).join("")}</optgroup>`).join("")}</select>
        <span class="hint">26 kinds of business, each with its own space needs, sourced opening costs and neighborhood signals.</span></div>` : "";
    const placeField = wantPlace ? `<div class="field"><label for="place-q">Which building?</label>
        <input id="place-q" class="text-input" autocomplete="off" placeholder="Street address, e.g. 11220 Louetta" value="${esc(i.place ? i.place.address : "")}">
        <div id="place-results" class="place-results"></div>
        ${kind === "both" ? `<select class="select hidden" id="suite" aria-label="Listed space"></select>` : ""}
        <span class="hint">Any Houston building in the CoStar kit. Buildings with space listed for lease come first.</span></div>` : "";
    let place = i.place || null;
    const area = Object.assign({ mode: "anywhere", radius: 10 }, i.area || {});
    const ex = new Set(i.exclude || []);
    const titles = { budget: ["What can you put in?", "Your total cash and what you want to keep in reserve. We'll find what that can open, and where."],
      idea: ["What do you want to open, and with how much?", "Pick the business and your cash. We'll check every listed Houston space for it."],
      space: ["Which building, and how much can you put in?", "Pick the building. We check it first (who permits it, can it be commercial), then what fits and pays there."],
      both: ["What, where, and how much?", "One business in one listed space. Thirteen agents review it and give a verdict with every reason."] }[kind];
    el.innerHTML = `${head("budget", titles[0], titles[1])}
      <div class="budget-layout">
        <div class="panel">
          ${bizField}${placeField}
          <div class="field"><label for="cash">Total cash you can put in</label>
            <div class="money-input"><span>$</span><input id="cash" inputmode="numeric" value="${num(i.budget)}"></div>
            <input type="range" id="cash-range" min="50000" max="2000000" step="10000" value="${i.budget}" aria-label="Total cash">
          </div>
          <div class="field"><label for="reserve">Reserve to keep untouched</label>
            <div class="money-input"><span>$</span><input id="reserve" inputmode="numeric" value="${num(i.reserve)}"></div>
            <span class="hint">Kept back for surprises. It is never spent on opening.</span>
          </div>
          <div class="field"><span class="label">Lease or buy</span>
            <div class="seg"><button class="on" type="button">Lease</button><button type="button" disabled title="Buying is not built yet">Buy</button></div>
            <span class="hint">Lease only for now. Buying is not built yet.</span>
          </div>
          <div class="field ${wantPlace ? "hidden" : ""}"><span class="label">Where</span>
            <div class="seg" id="area-mode"><button type="button" data-m="anywhere" class="${area.mode !== "near" ? "on" : ""}">Anywhere in Houston</button><button type="button" data-m="near" class="${area.mode === "near" ? "on" : ""}">Near a place</button></div>
            <div id="near" class="${area.mode === "near" ? "" : "hidden"}" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px">
              <select class="select" id="place" aria-label="Place">${PLACES.map(([n]) => `<option ${n === area.place ? "selected" : ""}>${esc(n)}</option>`).join("")}</select>
              <select class="select" id="radius" aria-label="Radius">${[3, 5, 10, 15, 25].map((r) => `<option value="${r}" ${+area.radius === r ? "selected" : ""}>within ${r} mi</option>`).join("")}</select>
            </div>
          </div>
          <div class="field ${wantBiz ? "hidden" : ""}"><span class="label">Leave out (optional)</span>
            <div class="toggle-chips" id="exclude">${GROUPS.map((g) => `<button type="button" data-g="${esc(g)}" class="${ex.has(g) ? "on" : ""}">${esc(g)}</button>`).join("")}</div>
            <span class="hint">Tap a group you'd never run. Everything else is considered: 26 kinds of business.</span>
          </div>
        </div>
        <div class="panel open-with">
          <div class="eyebrow">You can open with</div>
          <div class="big" id="open-with">${kmoney(i.budget - i.reserve)}</div>
          <div class="eq" id="open-eq">${money(i.budget)} cash − ${money(i.reserve)} reserve</div>
          <div class="note">Opening costs come from sourced franchise disclosure benchmarks, scaled to each space, plus the deposit and rent while you build. No revenue forecast: we show how many months of rent you'd have left.</div>
          <button class="btn primary block" id="go-scan">${{ budget: "Scan Houston", idea: "Scan Houston for it", space: "Check the building", both: "Review it" }[kind]}${ic("right")}</button>
          <div class="muted small" id="budget-err"></div>
        </div>
      </div>`;
    const cash = el.querySelector("#cash"), range = el.querySelector("#cash-range"), reserve = el.querySelector("#reserve");
    const parse = (s) => Number(String(s).replace(/[^0-9.]/g, "")) || 0;
    const sync = () => {
      const b = parse(cash.value), r = parse(reserve.value);
      el.querySelector("#open-with").textContent = kmoney(Math.max(0, b - r));
      el.querySelector("#open-eq").textContent = `${money(b)} cash − ${money(r)} reserve`;
      const bad = !(b > 0 && r >= 0 && r < b);
      el.querySelector("#go-scan").disabled = bad;
      el.querySelector("#budget-err").textContent = bad ? "The reserve has to be smaller than the cash." : "";
      return { b, r, bad };
    };
    let t;
    const persist = () => { clearTimeout(t); t = setTimeout(() => { const s = sync(); if (!s.bad) setInputs({ budget: s.b, reserve: s.r }, true).then(() => refreshRail("budget")); }, 500); };
    cash.oninput = () => { range.value = parse(cash.value); sync(); persist(); };
    cash.onblur = () => { cash.value = num(parse(cash.value)); };
    reserve.oninput = () => { sync(); persist(); };
    reserve.onblur = () => { reserve.value = num(parse(reserve.value)); };
    range.oninput = () => { cash.value = num(range.value); sync(); persist(); };
    el.querySelectorAll("#area-mode button").forEach((b) => b.onclick = () => {
      el.querySelectorAll("#area-mode button").forEach((x) => x.classList.toggle("on", x === b));
      el.querySelector("#near").classList.toggle("hidden", b.dataset.m !== "near");
    });
    el.querySelectorAll("#exclude button").forEach((b) => b.onclick = () => b.classList.toggle("on"));
    // Building search (I have a space / I know both): any Houston kit building; listed ones first.
    const loadSuites = async (pid) => {
      const sel = el.querySelector("#suite"); if (!sel) return;
      sel.innerHTML = `<option>Loading listed spaces…</option>`; sel.classList.remove("hidden");
      try {
        const pre = await api(`/api/site/preflight?property_id=${pid}`);
        sel.innerHTML = pre.spaces.length ? pre.spaces.map((x) => `<option value="${esc(x.value)}" ${x.value === i.suite ? "selected" : ""}>${esc(x.label)} · ${num(x.sf)} sq ft${x.monthly_rent ? ` · ${money(x.monthly_rent)}/mo` : " · rent not listed"}</option>`).join("")
          : `<option value="">Nothing listed for lease here</option>`;
        if (place) Object.assign(place, { lat: pre.lat, lon: pre.lon });
      } catch (e) { sel.innerHTML = `<option value="">${esc(e.message)}</option>`; }
    };
    const pq = el.querySelector("#place-q");
    if (pq) {
      let pt;
      pq.oninput = () => { clearTimeout(pt); place = null; pt = setTimeout(async () => {
        const box = el.querySelector("#place-results"), q = pq.value.trim();
        if (q.length < 3) { box.innerHTML = ""; return; }
        try {
          const r = await api(`/api/places?q=${encodeURIComponent(q)}`);
          box.innerHTML = r.places.length ? r.places.map((x) => `<button type="button" class="place-row" data-id="${x.property_id}" data-a="${esc(x.address)}"><span>${esc(x.address)}</span>${x.listed_spaces ? chip("green", `${x.listed_spaces} listed`) : chip("grey", "nothing listed")}</button>`).join("") : `<div class="faint small">No Houston building matches.</div>`;
          box.querySelectorAll(".place-row").forEach((b) => b.onclick = () => {
            place = { property_id: +b.dataset.id, address: b.dataset.a }; pq.value = b.dataset.a; box.innerHTML = "";
            loadSuites(place.property_id);
          });
        } catch (e) { box.innerHTML = `<div class="error">${esc(e.message)}</div>`; }
      }, 250); };
      if (place && kind === "both") loadSuites(place.property_id);
    }
    el.querySelector("#go-scan").onclick = async () => {
      const s = sync(); if (s.bad) return;
      const bizSel = el.querySelector("#biz"), biz = bizSel ? bizSel.value : null;
      if (wantBiz && !biz) { toast("Choose a business first"); return; }
      if (wantPlace && !place) { toast("Pick a building from the list"); return; }
      const suiteSel = el.querySelector("#suite"), suite = suiteSel ? suiteSel.value : null;
      if (kind === "both" && !suite) { toast("This building has no space listed for lease to review"); return; }
      const bizLabel = biz ? list.find((x) => x.key === biz).label : null;
      if (kind !== "budget") {
        const changedPick = biz !== (i.business || null) || (place && place.property_id) !== (i.place && i.place.property_id) || (suite || null) !== (i.suite || null);
        await setInputs(Object.assign({ budget: s.b, reserve: s.r, business: biz, businessLabel: bizLabel, place, suite },
          biz ? { directions: [biz], directionLabels: [bizLabel] } : {}));
        if (changedPick || s.b !== i.budget || s.r !== i.reserve) { state.reviews = {}; state.opp = null; await save({ shortlist: [], chosen: null }); }
        if (kind === "both") {
          const sel = suiteSel.options[suiteSel.selectedIndex], g = list.find((x) => x.key === biz).group;
          await save({ shortlist: [{ business: biz, label: bizLabel, group: g, property_id: place.property_id, suite,
            suite_label: sel.text.split(" · ")[0], address: place.address, lat: place.lat, lon: place.lon, building: { reasons: [] } }] });
        }
        goStage(nextStage("budget")); return;
      }
      const near = el.querySelector("#area-mode .on").dataset.m === "near";
      const placeName = el.querySelector("#place").value, p = PLACES.find(([n]) => n === placeName);
      const areaOut = near ? { mode: "near", place: placeName, lat: p[1], lon: p[2], radius: +el.querySelector("#radius").value } : { mode: "anywhere", radius: 10 };
      const exclude = [...el.querySelectorAll("#exclude .on")].map((b) => b.dataset.g);
      const before = JSON.stringify([i.budget, i.reserve, i.area, i.exclude]);
      const changed = before !== JSON.stringify([s.b, s.r, areaOut, exclude]);
      await setInputs(Object.assign({ budget: s.b, reserve: s.r, area: areaOut, exclude }, changed ? { directions: [], directionLabels: [] } : {}));
      if (changed && (state.v.shortlist || []).length) await save({ shortlist: [], chosen: null });
      if (changed) state.reviews = {};
      goStage("scan");
    };
  }

  // ---------- Stage 2 (I have a space): building check before any business ----------
  async function stageSite(el) {
    const i = inputs();
    if (!i.place) { el.innerHTML = `${head("scan", "Check the building first", "")}<div class="panel">Pick a building first. <button class="link-btn" id="back">${ic("left", 14)}Your space</button></div>`; el.querySelector("#back").onclick = () => goStage("budget"); return; }
    el.innerHTML = `${head("scan", "Check the building first", "Before any business: who permits this address, and can the building be used commercially? From the pin's official boundary, not the postal city. Nothing here is an approval.")}<div class="loading"><span class="spinner"></span>Checking ${esc(i.place.address)}…</div>`;
    const s = await api(`/api/site/preflight?property_id=${i.place.property_id}`);
    const j = s.jurisdiction || {}, f = s.facts || {};
    const state3 = s.stops.length ? ["red", "We stop here", "v-no-go"] : s.checks.length ? ["amber", "Continue, with checks", "v-conditional"] : ["green", "Clear to look at businesses", "v-go"];
    await setInputs({ place: Object.assign({}, i.place, { lat: s.lat, lon: s.lon }), site: { ok: s.can_continue, code: j.code } }, true);
    refreshRail("scan");
    el.innerHTML = `${head("scan", "Check the building first", "Before any business: who permits this address, and can the building be used commercially? From the pin's official boundary, not the postal city. Nothing here is an approval.")}
      <div class="inv"><div class="inv-main">
        <div class="panel verdict-panel"><div class="verdict-top"><div class="verdict ${state3[2]}"><span class="verdict-k">Building check</span><span class="verdict-v"><i></i>${esc(state3[1])}</span></div>
          <div class="verdict-id"><div class="eyebrow">${esc(f.property_type || "")} · CoStar ${s.property_id}</div><h2>${esc(s.address || i.place.address)}</h2></div></div>
          <ul class="verdict-reasons">${s.stops.map((x) => `<li class="blk">${esc(x)}</li>`).join("")}${s.checks.map((x) => `<li>${esc(x)}</li>`).join("")}${!s.stops.length && !s.checks.length ? `<li>Inside a jurisdiction we model, a commercial building, with space listed for lease.</li>` : ""}</ul>
          <div class="verdict-foot"><span class="faint small">${esc(s.computed_by)}</span></div></div>
        <div class="panel"><div class="ph">Who permits it</div><ul class="plain">
          ${li(j.verified ? "green" : "grey", j.verified ? "✓" : "?", `${esc(j.place || (j.county ? "Unincorporated " + j.county : "Not verified"))} ${srcChip({ name: "U.S. Census geocoder", url: j.evidence_url, retrieved_at: j.retrieved_at })}<br><span class="muted small">${esc(j.note || "")}</span>`)}
          ${s.authority ? li("grey", "→", `Permits go through <b>${esc(s.authority.name)}</b> ${ext(s.authority.url, "Official page")}`) : ""}
        </ul></div>
        <div class="panel"><div class="ph">Still to verify with the authority<span class="aside">none counted as cleared</span></div><ul class="plain">${(s.to_verify || []).map((x) => li("grey", "?", esc(x))).join("")}</ul></div>
      </div><aside class="inv-side">
        <div class="panel"><div class="ph">Building facts</div><dl class="figures">
          <div><dt>Property type</dt><dd>${esc(f.property_type || "—")}</dd><span class="sub">${src("CoStar")}</span></div>
          <div><dt>Building area</dt><dd>${f.area_sqft ? num(f.area_sqft) + " sq ft" : "—"}</dd><span class="sub">${src("CoStar")}</span></div>
          <div><dt>Floors</dt><dd>${f.floors ?? "—"}</dd><span class="sub">${src("CoStar")}</span></div>
          <div><dt>Parking</dt><dd>${f.parking_spaces ?? "not recorded"}</dd><span class="sub">${src("CoStar")}</span></div>
        </dl></div>
        <div class="panel"><div class="ph">Listed for lease<span class="aside">${s.spaces.length}</span></div>${s.spaces.length ? `<ul class="plain">${s.spaces.slice(0, 8).map((x) => li("grey", "·", `${esc(x.label)}${/sq ft/.test(x.label) ? "" : ` · ${num(x.sf)} sq ft`}${x.monthly_rent ? ` · ${money(x.monthly_rent)}/mo` : " · rent not listed"}`)).join("")}</ul>${s.spaces.length > 8 ? `<div class="faint small">+${s.spaces.length - 8} more</div>` : ""}` : `<div class="muted small">Nothing listed for lease in CoStar.</div>`}</div>
      </aside></div>
      <div class="sticky-bar"><span class="muted small">${s.can_continue ? "Next: every business this building can host, priced and checked against the neighborhood." : "No business is suggested for a building that fails this check."}</span>
        ${s.can_continue ? `<button class="btn primary" id="next">See what fits here${ic("right")}</button>` : `<button class="btn ghost" id="next">${ic("left")}Pick another building</button>`}</div>`;
    el.querySelector("#next").onclick = () => goStage(s.can_continue ? "opportunities" : "budget");
  }

  // ---------- Stage 2: scan ----------
  async function stageScan(el) {
    const i = inputs();
    const agents = ["site", "building", "money", "residents", "competitors", "momentum", "lookalike", "coordinator", "permits"];
    el.innerHTML = `${head("scan", kindOf() === "idea" ? `Where a ${esc((i.businessLabel || "").toLowerCase())} works` : "Our agents check every combination", `${kindOf() === "idea" ? `Every listed Houston space checked for a ${esc((i.businessLabel || "").toLowerCase())}` : "Every listed Houston space against every business"}, with ${kmoney(i.budget - i.reserve)} to open with. Four gates, in order: can the building host it, can you afford it, does the neighborhood support it, and who permits it.`,
      `<button class="btn ghost small" id="skip">Skip animation</button>`)}
      <div class="scan">
        <div class="panel"><div class="ph">Combinations left after each gate<span class="aside">Houston · lease</span></div><div class="funnel" id="funnel"><div class="loading"><span class="spinner"></span>Scanning…</div></div></div>
        <div class="panel scan-map"><div class="ph">Houston, gate by gate<span class="aside" id="map-count"></span></div><div class="map" id="scan-map"></div>
          <div class="map-legend"><span id="map-note">One dot per building with listed space</span><span>Green: passes every gate · amber: permitting authority not identified</span></div></div>
        <div class="panel scan-agents"><div class="ph">Agents<span class="aside">${agents.length} on this scan</span></div><div class="agents">${agents.map((a) => `<div class="agent" data-a="${a}">${agentImg(a)}<div class="name">${a[0].toUpperCase() + a.slice(1)}</div><div class="job">${esc(AGENT_JOBS[a])}</div></div>`).join("")}</div>
          <div class="note-line">${ic("info", 14)}<span>Every number and gate is computed in code. No AI decides who passes.</span></div></div>
      </div>
      <div class="sticky-bar hidden" id="next-bar"><span id="next-note" class="muted small"></span><button class="btn primary" id="next">${kindOf() === "idea" ? "Pick where" : `See what ${kmoney(i.budget - i.reserve)} can become`}${ic("right")}</button></div>`;
    let o;
    try { o = await opportunities(); } catch (e) { el.querySelector("#funnel").innerHTML = `<div class="error">${esc(e.message)}</div>`; return; }
    const f = o.funnel;
    const rows = [
      [f.spaces, "Listed Houston spaces", "CoStar listings with a space you can lease", "CoStar", ["site"]],
      [f.combinations, "Business × space combinations", o.businesses_considered === 1 ? `${num(f.spaces)} spaces × ${esc(i.businessLabel || "1 business")}` : `${num(f.spaces)} spaces × ${o.businesses_considered} businesses`, "26-business registry", ["site"]],
      [f.building_can_host, "The building can host it", "Property type, floor, size and ceiling vs each business's needs", "CoStar", ["building"]],
      [f.affordable, `Cash to open + reserve fits ${kmoney(i.budget)}`, "Sourced opening-cost benchmarks scaled to the space, plus deposit and rent while building", "FDD benchmark", ["money"]],
      [f.neighborhood_support, "The neighborhood supports it", "Residents, competitors, who's moving in, lookalike areas", "ACS · OSM · CoStar", ["residents", "competitors", "momentum", "lookalike", "coordinator"]],
      [f.authority_identified ?? f.neighborhood_support, "Compliance preflight: who permits it", "Official boundary from the pin, not the postal city: City of Houston or Harris County (Jayant's compliance engine)", "Census geocoder", ["permits"]],
    ];
    const max = Math.sqrt(f.combinations);
    // The map: buildings drop out gate by gate (real per-building results from the same scan).
    const M = o.map || { buildings: [], after_gate: [] };
    let mapCtl = null;
    if (has3d() && M.buildings.length) {
      try { mapCtl = window.Suite3D.map(el.querySelector("#scan-map"), { pins: [], plain: true }); } catch { mapCtl = null; }
      if (mapCtl) { state.ctrls.push(mapCtl); mapCtl.setDots(M.buildings); }
    }
    if (!mapCtl) el.querySelector(".scan-map").classList.add("hidden");
    const GATE_FOR_ROW = [0, 0, 1, 2, 3, 4], GATE_NAME = ["listed", "can host a business", "affordable for one", "neighborhood-supported", "with a known permitting authority"];
    const mapGate = (k) => {
      const g = GATE_FOR_ROW[k]; if (mapCtl) mapCtl.showGate(g);
      const n = M.after_gate[g];
      const c = el.querySelector("#map-count"); if (c && n != null) c.textContent = `${num(n)} of ${num(M.after_gate[0])} buildings ${GATE_NAME[g]}`;
    };
    el.querySelector("#funnel").innerHTML = rows.map(([n, title, what, s], k) => `
      <div class="funnel-row" data-k="${k}"><div class="top"><span><span class="t">${esc(title)}</span>${src(s)}</span><b data-n="${n}">0</b></div>
        <div class="bar"><i data-w="${Math.max(2, 100 * Math.sqrt(n) / max)}"></i></div><div class="what">${esc(what)}</div></div>`).join("") +
      `<div class="funnel-foot">${f.rent_not_listed ? chip("grey", `${num(f.rent_not_listed)} with no listed rent: judged on cost before rent`) : ""}
        ${f.cost_not_estimated ? chip("grey", `${num(f.cost_not_estimated)} pass but cost not estimated`, "No comparable opening-cost benchmark (e.g. car wash)") : ""}
        ${f.compliance && f.compliance.harris_unincorporated ? chip("amber", `${num(f.compliance.harris_unincorporated)} in unincorporated Harris County: county permits, not the city's`) : ""}
        ${f.compliance && f.compliance.other_city ? chip("amber", `${num(f.compliance.other_city)} inside another city: that city permits it`) : ""}
        ${f.compliance && f.compliance.unverified ? chip("grey", `${num(f.compliance.unverified)} jurisdiction not looked up`) : ""}
        <span class="muted small">Bar length on a square-root scale. Answered in ${o.elapsed_ms} ms.</span></div>`;
    const count = (b, n) => {
      const t0 = performance.now();
      const tick = () => { const p = Math.min(1, (performance.now() - t0) / 550); b.textContent = num(n * (1 - Math.pow(1 - p, 3))); if (p < 1 && b.isConnected) requestAnimationFrame(tick); };
      tick();
    };
    const light = (k, instant) => {
      const row = el.querySelector(`.funnel-row[data-k="${k}"]`); if (!row || row.classList.contains("lit")) return;
      row.classList.add("lit"); mapGate(k);
      const bar = row.querySelector("i"); bar.style.width = bar.dataset.w + "%";
      const b = row.querySelector("b[data-n]");
      if (instant) b.textContent = num(+b.dataset.n); else count(b, +b.dataset.n);
      el.querySelectorAll(".agent").forEach((a) => a.classList.remove("on"));
      rows[k][4].forEach((a) => { const x = el.querySelector(`.agent[data-a="${a}"]`); if (x) x.classList.add("on", "done"); });
    };
    const finish = () => {
      state.timers.forEach(clearTimeout); state.timers = []; // keep the map alive (clearTimers disposes 3D)
      rows.forEach((_, k) => light(k, true));
      el.querySelectorAll(".agent").forEach((a) => { a.classList.remove("on"); a.classList.add("done"); });
      el.querySelector("#next-bar").classList.remove("hidden");
      el.querySelector("#next-note").innerHTML = `<b class="num">${num(f.authority_identified ?? f.neighborhood_support)}</b> combinations pass every gate${o.businesses_considered > 1 ? `, across <b class="num">${o.directions.length}</b> kinds of business` : ""}.`;
      el.querySelector("#skip").classList.add("hidden");
      refreshRail("scan");
    };
    rows.forEach((_, k) => later(() => light(k), 250 + k * 600));
    later(finish, 250 + rows.length * 600 + 300);
    el.querySelector("#skip").onclick = finish;
    el.querySelector("#next").onclick = () => goStage(nextStage("scan"));
  }

  // ---------- Stage 3: opportunities ----------
  function directionPairs(o, keys) {
    const seen = new Set(), out = [];
    const add = (p) => { const k = pairKey(p); if (!seen.has(k) && (!keys || keys.includes(p.business))) { seen.add(k); out.push(p); } };
    o.pairs.forEach(add); o.directions.forEach((d) => d.pairs.forEach(add));
    return out;
  }
  function mapInto(holder, pins, onPick) {
    let ctrl = null;
    if (has3d()) { try { ctrl = window.Suite3D.map(holder, { pins, onPick }); } catch { ctrl = null; } }
    if (ctrl) { state.ctrls.push(ctrl); return ctrl; }
    // 2D fallback: equirectangular dots around downtown with I-610 and Beltway 8 rings
    holder.innerHTML = `<div class="map2d"></div>`;
    const box = holder.firstElementChild, W = holder.clientWidth || 400, H = holder.clientHeight || 400;
    const c = [29.7604, -95.3698], mi = Math.min(W, H) / 2 / 28;
    const xy = (lat, lon) => [W / 2 + (lon - c[1]) * 69 * Math.cos(c[0] * Math.PI / 180) * mi, H / 2 - (lat - c[0]) * 69 * mi];
    [5, 12].forEach((r) => { const d = document.createElement("div"); d.className = "ring"; Object.assign(d.style, { left: W / 2 - r * mi + "px", top: H / 2 - r * mi + "px", width: 2 * r * mi + "px", height: 2 * r * mi + "px" }); box.appendChild(d); });
    const els = {};
    const draw = (list) => {
      box.querySelectorAll(".pin").forEach((p) => p.remove());
      list.forEach((p) => {
        const [x, y] = xy(p.lat, p.lon), b = document.createElement("button");
        b.className = "pin"; b.title = p.label; b.style.left = x + "px"; b.style.top = y + "px"; b.style.background = p.color || "";
        b.onclick = () => onPick && onPick(p.id); box.appendChild(b); els[p.id] = b;
      });
    };
    draw(pins);
    return { setPins: draw, select: (id) => Object.entries(els).forEach(([k, b]) => b.classList.toggle("dim", !!id && k !== id)), dispose() {} };
  }
  async function stageOpportunities(el) {
    const i = inputs();
    el.innerHTML = `<div class="loading"><span class="spinner"></span>Loading opportunities…</div>`;
    const o = await opportunities();
    let picked = (i.directions || []).filter((k) => o.directions.some((d) => d.business === k));
    const cards = o.directions.map((d) => {
      const basis = d.cost_basis && d.cost_basis !== "itemized" ? chip("amber", d.excludes ? `excludes ${d.excludes}` : `${d.cost_basis} benchmark`, "The cost benchmark for this business is incomplete") : "";
      const best = d.pairs.map((p) => `<li><span class="mk ${look(AFFORD, p.cost.affordability)[0]}">•</span><span>${esc(p.address.split(",")[0])} · ${esc(p.suite_label)} · <span class="num">${kmoney(p.cost.cash_to_open.base)}</span></span></li>`).join("");
      return `<div class="card clickable direction ${picked.includes(d.business) ? "selected" : ""}" data-b="${esc(d.business)}" tabindex="0" role="button" aria-pressed="${picked.includes(d.business)}">
        <div class="head"><div class="prop">${propImg(d.group)}</div><div><h3>${esc(d.label)}</h3><div class="group">${esc(d.group)}</div></div></div>
        <div class="metrics">
          <div><span class="k">Places</span><span class="v">${d.places}</span></div>
          <div><span class="k">Within budget</span><span class="v">${d.within_budget || 0}</span></div>
          <div class="wide"><span class="k">Cash to open</span><span class="v">${d.cash_to_open_range[0] === d.cash_to_open_range[1] ? kmoney(d.cash_to_open_range[0]) : `${kmoney(d.cash_to_open_range[0])}–${kmoney(d.cash_to_open_range[1])}`}${src(costSrc(d.cost_basis))}</span></div>
        </div>
        <div class="chips">${d.supported ? chip("green", `${d.supported} neighborhood-supported`) : chip("amber", "Mixed neighborhoods, net positive")}
          ${d.only_low_case ? chip("amber", `${d.only_low_case} low case only`) : ""}${d.rent_not_listed ? chip("grey", `${d.rent_not_listed} rent not listed`) : ""}${basis}</div>
        <p class="why">${esc(d.why)}${src(demandSrc(d.business))}</p>
        <details onclick="event.stopPropagation()"><summary class="link-btn">Best places (${d.pairs.length})</summary><ul class="plain">${best}</ul></details>
      </div>`;
    }).join("");
    const cne = (o.cost_not_estimated || []).map((u) => `<div><b>${esc(u.label)}</b>: ${u.places} place${u.places > 1 ? "s" : ""} pass the building and neighborhood gates. ${esc(u.why)} We don't guess a number.</div>`).join("");
    const here = kindOf() === "space";
    const notHere = here ? (o.not_here || []).map((x) => `<div class="nh"><span class="mk ${x.stopped_at === "neighborhood" ? "amber" : "red"}">${x.stopped_at === "neighborhood" ? "!" : "✗"}</span><span><b>${esc(x.label)}</b> <span class="faint small">stopped at the ${esc(x.stopped_at)} gate</span><br><span class="muted small">${esc(tidy(x.why))}</span></span></div>`).join("") : "";
    el.innerHTML = `${head("opportunities", here ? `What ${esc(i.place.address.split(",")[0])} can become` : `Here's what ${kmoney(i.budget - i.reserve)} can become`, here ? `${o.directions.length} of 26 kinds of business fit this building, are affordable with ${kmoney(i.budget - i.reserve)} and have neighborhood support. Pick 1–3 to investigate; the rest show where they stopped.` : `${o.directions.length} kinds of business have at least one Houston space that fits, is affordable and has neighborhood support. Pick 1–3 directions to explore.`)}
      <div class="opps">
        <div>
          ${o.directions.length ? `<div class="grid directions">${cards}</div>` : `<div class="panel">Nothing passes every gate at this budget. Try more cash, a smaller reserve, or a wider area.</div>`}
          ${cne ? `<div class="panel not-estimated"><div class="ph">Cost not estimated</div><div class="muted" style="display:flex;flex-direction:column;gap:6px">${cne}</div></div>` : ""}
          ${notHere ? `<details class="panel not-here"><summary class="ph" style="cursor:pointer">Didn't make it here<span class="aside">${(o.not_here || []).length} businesses · why each one stopped</span></summary><div class="nh-list">${notHere}</div></details>` : ""}
        </div>
        <div class="glass map-wrap" style="border-radius:var(--r)"><div class="ph">Where they are<span class="aside">Best spaces per direction</span></div><div class="map" id="map"></div>
          <div class="map-legend"><span>Rings ≈ I-610 and Beltway 8</span><span>Drag to rotate · select a pin</span></div></div>
      </div>
      <div class="sticky-bar"><span class="muted" id="pick-note"></span><button class="btn primary" id="next">${here ? "Investigate" : "Pick where"}${ic("right")}</button></div>`;
    const pairs = directionPairs(o).filter((p) => o.directions.some((d) => d.business === p.business));
    const pinsFor = () => pairs.map((p) => ({ id: pairKey(p), lat: p.lat, lon: p.lon, label: `${p.label} · ${p.address}`,
      color: !picked.length || picked.includes(p.business) ? "#D9DCE1" : "#4A4F57" }));
    const map = mapInto(el.querySelector("#map"), pinsFor(), (id) => {
      const b = id.split("|")[0], card = el.querySelector(`.direction[data-b="${CSS.escape(b)}"]`);
      if (card) { card.scrollIntoView({ behavior: "smooth", block: "center" }); card.animate([{ borderColor: "#00B0E6" }, { borderColor: "rgba(255,255,255,.08)" }], { duration: 1400 }); }
      map.select && map.select(id);
    });
    const update = () => {
      el.querySelector("#pick-note").innerHTML = picked.length ? `<b class="num">${picked.length}</b> of 3 picked: ${esc(picked.map((k) => o.directions.find((d) => d.business === k).label).join(", "))}` : "Pick 1–3 directions";
      el.querySelector("#next").disabled = !picked.length;
      map.setPins && map.setPins(pinsFor());
    };
    el.querySelectorAll(".direction").forEach((c) => {
      const toggle = () => {
        const b = c.dataset.b;
        if (picked.includes(b)) picked = picked.filter((x) => x !== b);
        else if (picked.length >= 3) { toast("Pick up to 3 directions"); return; }
        else picked.push(b);
        c.classList.toggle("selected", picked.includes(b)); c.setAttribute("aria-pressed", picked.includes(b));
        update();
      };
      c.onclick = toggle; c.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } };
    });
    update();
    el.querySelector("#next").onclick = async () => {
      const labels = picked.map((k) => o.directions.find((d) => d.business === k).label);
      const keep = (state.v.shortlist || []).filter((s) => picked.includes(s.business));
      await setInputs({ directions: picked, directionLabels: labels });
      if (here) { // one building: each picked business goes straight to review at its best space here
        const list = picked.map((k) => o.directions.find((d) => d.business === k).pairs[0]).filter(Boolean).map((p) => ({
          business: p.business, label: p.label, group: p.group, property_id: p.property_id, suite: p.suite, suite_label: p.suite_label,
          address: p.address, sf: p.sf, lat: p.lat, lon: p.lon, building: { reasons: p.building.reasons } }));
        await save({ shortlist: list });
        goStage("investigate"); return;
      }
      if (keep.length !== (state.v.shortlist || []).length) await save({ shortlist: keep });
      goStage("shortlist");
    };
  }

  // ---------- Stage 4: shortlist ----------
  function gateChips(p) {
    const fit = look(FIT, p.building.status), aff = look(AFFORD, p.cost.affordability), dem = look(DEMAND, p.demand.verdict);
    const rec = p.evidence_flags && p.evidence_flags.length ? ["amber", "Records: check"] : ["green", "No record conflicts"];
    return `<div class="gates">${chip(fit[0], fit[1], (p.building.reasons || []).concat(p.building.unknowns || []).join(" · "))}
      ${chip(aff[0], aff[1], p.cost.note || "")}${chip(dem[0], dem[1], (p.demand.reasons || []).join(" · "))}
      ${chip(rec[0], rec[1], (p.evidence_flags || []).join(" · ") || "No conflicts found between CoStar's record and linked scans")}</div>`;
  }
  function decidingReason(p) {
    if (p.cost.affordability === "stretch") return `Only the low-cost case fits: ${kmoney(p.cost.required.low)} needed vs ${kmoney(inputs().budget)}.`;
    if (p.cost.affordability === "rent_unknown") return "Rent isn't listed, so cash to open excludes rent. Ask the broker.";
    if (p.building.status === "check") return (p.building.unknowns || [])[0] || "Fits if checks pass.";
    return p.demand.insight || (p.demand.reasons || [])[0] || "Passes every gate.";
  }
  async function stageShortlist(el) {
    const i = inputs();
    el.innerHTML = `<div class="loading"><span class="spinner"></span>Ranking places…</div>`;
    const o = await opportunities();
    const keys = (i.directions || []).filter((k) => o.directions.some((d) => d.business === k));
    if (!keys.length) { el.innerHTML = `${head("shortlist", "Pick where", "")}<div class="panel">Pick at least one direction first. <button class="link-btn" id="back">${ic("left", 14)}Opportunities</button></div>`; el.querySelector("#back").onclick = () => goStage(kindOf() === "idea" ? "budget" : "opportunities"); return; }
    const pairs = directionPairs(o, keys);
    let chosen = (state.v.shortlist || []).map(pairKey).filter((k) => pairs.some((p) => pairKey(p) === k));
    const filter = keys.includes(state.filter) ? state.filter : "all";
    const shown = pairs.filter((p) => filter === "all" || p.business === filter);
    const rows = shown.map((p, k) => {
      const key = pairKey(p), on = chosen.includes(key);
      const runway = p.cost.months_of_rent_after_opening;
      return `<div class="card clickable pair ${on ? "selected" : ""}" data-k="${esc(key)}" tabindex="0" role="button" aria-pressed="${on}">
        <div class="thumb">${buildingImg(p, 160)}</div>
        <div><div class="title"><span class="rank">#${k + 1}</span>${esc(p.label)}</div>
          <div class="addr">${esc(p.address)} · ${esc(p.suite_label)}${/sq ft/.test(p.suite_label || "") ? "" : ` · ${num(p.sf)} sq ft`}${p.rent && p.rent.monthly ? ` · ${money(p.rent.monthly)}/mo${src(rentSrc(p.rent))}` : ` · rent not listed`}</div>
          ${gateChips(p)}<div class="reason">${esc(decidingReason(p))}</div></div>
        <div class="cash"><b>${kmoney(p.cost.cash_to_open.base)}</b>
          <div>${kmoney(p.cost.cash_to_open.low)}–${kmoney(p.cost.cash_to_open.high)}${src(costSrc(p.cost.basis_quality))}</div>
          ${runway != null ? `<div title="Months of rent your remaining cash would cover after opening, with zero revenue">${runway} mo of rent in reserve</div>` : ""}</div>
      </div>`;
    }).join("");
    el.innerHTML = `${head("shortlist", "Pick where", "The best spaces for your directions, ranked: neighborhood support first, then cash. Four gates on each. Pick up to 3 to investigate.")}
      <div class="filter-row"><div class="seg" id="filter"><button data-f="all" class="${filter === "all" ? "on" : ""}">All (${pairs.length})</button>${keys.map((k) => { const d = o.directions.find((x) => x.business === k); return `<button data-f="${esc(k)}" class="${filter === k ? "on" : ""}">${esc(d.label)} (${pairs.filter((p) => p.business === k).length})</button>`; }).join("")}</div></div>
      <div class="pairs">${rows ? `<div class="pairs-head"><span></span><span>Place and gates</span><span>Cash to open</span></div>${rows}` : `<div class="panel">No ranked spaces for this direction.</div>`}</div>
      <div class="sticky-bar"><span class="muted" id="pick-note"></span><button class="btn primary" id="next">Investigate${ic("right")}</button></div>`;
    const update = () => {
      el.querySelector("#pick-note").innerHTML = chosen.length ? `<b class="num">${chosen.length}</b> of 3 places picked` : "Pick up to 3 places";
      el.querySelector("#next").disabled = !chosen.length;
    };
    el.querySelectorAll("#filter button").forEach((b) => b.onclick = () => { state.filter = b.dataset.f; persistShort().then(() => stageShortlist(el)); });
    const persistShort = () => {
      const list = chosen.map((k) => pairs.find((p) => pairKey(p) === k)).filter(Boolean).map((p) => ({
        business: p.business, label: p.label, group: p.group, property_id: p.property_id, suite: p.suite, suite_label: p.suite_label,
        address: p.address, sf: p.sf, lat: p.lat, lon: p.lon, building: { reasons: p.building.reasons } }));
      return save({ shortlist: list }, true);
    };
    el.querySelectorAll(".pair").forEach((c) => {
      const toggle = () => {
        const k = c.dataset.k;
        if (chosen.includes(k)) chosen = chosen.filter((x) => x !== k);
        else if (chosen.length >= 3) { toast("Pick up to 3 places"); return; }
        else chosen.push(k);
        c.classList.toggle("selected", chosen.includes(k)); c.setAttribute("aria-pressed", chosen.includes(k));
        update(); persistShort().then(() => refreshRail("shortlist"));
      };
      c.onclick = toggle; c.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } };
    });
    update();
    el.querySelector("#next").onclick = async () => { await persistShort(); goStage("investigate"); };
  }

  // ---------- Stage 5: investigate ----------
  function stanceMark(s) { return s > 0 ? ["green", "✓"] : s < 0 ? ["red", "✗"] : ["grey", "·"]; }
  function li(cls, mk, html) { return `<li><span class="mk ${cls}">${mk}</span><span>${html}</span></li>`; }
  function verdictCard(r, p) {
    const flips = r.flips && r.flips.length ? r.flips : [], blockers = r.blockers || [];
    const items = blockers.length ? blockers.map((b) => `<li class="blk">${esc(tidy(b))}</li>`).join("")
      : (r.reasons || []).slice(0, 3).map((x) => `<li>${esc(tidy(x))}</li>`).join("");
    const flipText = flips.length ? flips.map(esc).join(" · ") : r.verdict === "GO" ? "Nothing flagged. The checks below still need answers before you sign." : "";
    return `<div class="panel verdict-panel">
      <div class="verdict-top">${verdictBadge(r.verdict)}
        <div class="verdict-id"><div class="eyebrow">${esc(r.label)} · ${esc(p.suite_label || r.suite || "")}</div><h2>${esc(r.address)}</h2></div></div>
      ${items ? `<ul class="verdict-reasons">${items}</ul>` : ""}
      ${flipText ? `<div class="flip well"><span class="k">What would flip it</span><span>${flipText}</span></div>` : ""}
      <div class="verdict-foot"><span class="faint small">${esc(r.computed_by)}</span>
        <button class="btn ghost small" data-explain="1">${ic("spark", 14)}Explain the neighborhood in plain English</button></div>
      <div class="narr"></div>
    </div>`;
  }
  // ---------- "Why this verdict", the readable agent run, sources and the signal legend ----------
  // Everything here renders what the review returned (because[], trace[], evidence[]); no verdict logic in JS.
  const EFFECTS = [["blocks", "Blocks", "red"], ["check", "Needs a check", "amber"], ["supports", "Supports", "green"], ["unknown", "Unknown", "grey"]];
  const day = (d) => (d ? String(d).slice(0, 10) : "");
  function srcChip(s) {
    if (!s || !s.name) return "";
    const meta = [day(s.retrieved_at), s.confidence != null ? `conf ${s.confidence}` : ""].filter(Boolean).join(" · ");
    const inner = `<span class="sn">${esc(s.name)}</span>${meta ? `<span class="sm">${esc(meta)}</span>` : ""}`;
    return s.url ? `<a class="srcchip" href="${esc(s.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Open the source">${inner}${ic("ext", 11)}</a>`
      : `<span class="srcchip" title="Source">${inner}</span>`;
  }
  function whyHtml(r) {
    const rows = (r.because || []).map((x, i) => ({ ...x, i }));
    if (!rows.length) return "";
    const counts = EFFECTS.map(([e]) => rows.filter((x) => x.effect === e).length);
    // Wider columns where there are more reasons; empty columns stay narrow but visible ("None").
    const widths = counts.map((n) => `minmax(118px, ${n ? Math.min(n, 6) / 2 + 0.5 : 0.5}fr)`).join(" ");
    const cols = EFFECTS.map(([e, name, c]) => {
      const list = rows.filter((x) => x.effect === e);
      return `<div class="why-col"><div class="why-h"><span class="dot ${c}"></span>${name}<span class="n">${list.length}</span></div>
        <div class="why-list">${list.length ? list.map((x) => `<div class="why-row ${c}" role="button" tabindex="0" data-agent="${esc(x.agent)}" data-i="${x.i}" title="Open the ${esc(x.agent)} agent in the run">
          <div class="why-t">${esc(tidy(x.text))}</div>
          ${x.signal && x.signal.name && x.signal.value ? `<div class="why-sig"><span class="sk">${esc(x.signal.name)}</span> <b>${esc(x.signal.value)}</b>${x.signal.rule ? `<div class="rule">Rule: ${esc(x.signal.rule)}</div>` : ""}</div>` : ""}
          <div class="why-meta"><span class="wa">${esc(x.agent)} agent</span>${x.decides ? `<span class="dec" title="The verdict rule used this row">decides</span>` : `<span class="inf" title="Context: shown, but the verdict rule did not use it directly">informs</span>`}${srcChip(x.source)}</div>
        </div>`).join("") : `<div class="why-none">None</div>`}</div></div>`;
    }).join("");
    return `<div class="panel why" id="why"><div class="ph">Why this verdict<span class="aside">${rows.length} reasons · click one to open its agent · <button class="link-btn" data-legend>How to read the signals</button></span></div>
      <div class="why-grid" style="--cols:${widths}">${cols}</div></div>`;
  }
  const FSTATUS = { agrees: ["green", "confirmed"], conflict: ["amber", "conflict"], unknown: ["grey", "unknown"] };
  function fmtVal(v) {
    if (v == null) return "unknown";
    if (Array.isArray(v)) return v.length ? v.map(fmtVal).join(", ") : "none";
    if (typeof v === "object") return Object.entries(v).slice(0, 6).map(([k, x]) => `${k.replace(/_/g, " ")}: ${typeof x === "object" && x ? JSON.stringify(x) : fmtVal(x)}`).join(" · ");
    if (typeof v === "number") return Math.abs(v) >= 1000 ? Math.round(v).toLocaleString("en-US") : String(v);
    return String(v);
  }
  const factName = (f, key) => String(f || "").replace(key + ".", "").replace(/^compliance\./, "").replace(/[._]/g, " ");
  function arrow(sig) {
    if (!sig) return "";
    const s = sig.stance, [c, a, w] = s > 0 ? ["green", "↑", "supports"] : s < 0 ? ["amber", "↓", "against"] : s === 0 ? ["grey", "–", "neutral"] : ["grey", "?", "unknown"];
    return `<div class="sigline"><span class="arrow ${c}">${a}</span><span><b>${esc(sig.name)}</b> ${esc(w)}${sig.value != null ? ` · value ${esc(fmtVal(sig.value))}` : ""}${sig.validated === false && sig.name === "lookalike" ? " · not validated, does not vote" : ""}<br><span class="muted small">${esc(sig.reason || "")}</span></span></div>`;
  }
  function stepHtml(t, r, highlight) {
    const inputs = Object.entries(t.inputs || {}).filter(([, v]) => v != null && v !== "");
    const hl = new Set((highlight || []).map((i) => { const e = (r.evidence || [])[i]; return e ? e.fact + "|" + JSON.stringify(e.value) : ""; }));
    const rows = (t.findings || []).map((f) => {
      const [c, word] = FSTATUS[f.status] || FSTATUS.unknown;
      const s = { name: f.source ? String(f.source).replace(/^public:/, "") : "", url: f.evidence_url, retrieved_at: f.captured_at, confidence: f.confidence };
      return `<tr class="${hl.has(f.fact + "|" + JSON.stringify(f.value)) ? "hl" : ""}"><td><span class="dot ${c}" title="${word}"></span></td>
        <td><b>${esc(factName(f.fact, r.business))}</b>${f.needs_human ? `<span class="human">person must verify</span>` : ""}<div class="fv">${esc(tidy(fmtVal(f.value)))}</div>${f.note ? `<div class="fn">${esc(f.note)}</div>` : ""}${s.name || s.url ? `<div class="fs">${srcChip(s)}</div>` : ""}</td></tr>`;
    }).join("");
    const srcs = (t.sources || []).map((x) => srcChip({ name: x.name, url: x.url, retrieved_at: x.retrieved_at })).join("");
    return `<div class="step-head">${agentImg(t.agent, 22)}<div><b class="cap1">${esc(t.agent)}</b> <span class="faint small">${esc(t.computed_by === "llm" ? "LLM" : "code")}${t.ms != null ? ` · ${t.ms} ms` : ""}${t.confidence != null ? ` · confidence ${t.confidence}` : ""}</span>
        <div class="q">${esc(t.role || "")}</div></div></div>
      ${t.summary ? `<div class="step-sum">${esc(t.summary)}</div>` : ""}
      ${arrow(t.signal)}
      ${inputs.length ? `<div class="kv"><span class="k">Inputs</span>${inputs.map(([k, v]) => `<span class="pillk">${esc(k.replace(/_/g, " "))}: ${esc(tidy(fmtVal(v)))}</span>`).join("")}</div>` : ""}
      ${rows ? `<table class="findings"><tbody>${rows}</tbody></table>` : `<div class="faint small">No findings recorded by this step.</div>`}
      ${srcs ? `<div class="kv"><span class="k">Sources</span>${srcs}</div>` : ""}
      ${t.handoff ? `<div class="kv"><span class="k">Hands off</span><span class="small">${esc(t.handoff)}</span></div>` : ""}`;
  }
  function sourcesHtml(r) {
    const seen = new Map();
    const add = (name, url, when, agent) => {
      if (!name) return; const k = (name + "|" + (url || "")).toLowerCase();
      const cur = seen.get(k) || { name, url, when: "", agents: new Set() };
      if (when && (!cur.when || day(when) > cur.when)) cur.when = day(when);
      cur.agents.add(agent); seen.set(k, cur);
    };
    (r.trace || []).forEach((t) => (t.sources || []).forEach((x) => add(x.name, x.url, x.retrieved_at, t.agent)));
    (r.trace || []).forEach((t) => (t.findings || []).forEach((f) => { if (f.evidence_url && /^public:/.test(f.source || "")) add(String(f.source).replace(/^public:/, ""), f.evidence_url, f.captured_at, t.agent); }));
    const list = [...seen.values()];
    return `<details class="pillar" data-p="sources"><summary><span class="ptitle">Sources</span>${chip("grey", `${list.length} touched`)}<span class="pline">Every source this review used, with retrieval dates</span></summary>
      <div class="pillar-body"><table class="findings srcs"><tbody>${list.map((x) => `<tr><td><b>${esc(x.name)}</b><div class="fn">${[...x.agents].map(esc).join(", ")} agent${x.agents.size > 1 ? "s" : ""}</div></td><td class="small muted">${x.when ? "retrieved " + esc(x.when) : "cached kit / benchmark"}</td><td>${x.url ? ext(x.url, "Open") : ""}</td></tr>`).join("")}</tbody></table>
      <div class="muted small">Everything is read from local caches during the demo; nothing is fetched live.</div></div></details>`;
  }
  let guideCache = null;
  async function openLegend() {
    let dlg = document.getElementById("legend");
    if (!dlg) {
      dlg = document.createElement("dialog"); dlg.id = "legend"; dlg.className = "legend";
      document.body.appendChild(dlg);
      dlg.addEventListener("click", (e) => { if (e.target === dlg || e.target.closest("[data-close]")) dlg.close(); });
    }
    dlg.innerHTML = `<div class="legend-in"><div class="loading"><span class="spinner"></span>Loading the signal guide…</div></div>`;
    if (!dlg.open) dlg.showModal();
    try {
      const g = guideCache || (guideCache = await api("/api/signal-guide"));
      const look = (g.lookalike_accuracy || []).filter((x) => x.auc != null);
      const rent = g.rent_accuracy;
      dlg.innerHTML = `<div class="legend-in">
        <div class="legend-top"><h2>How to read the signals</h2><button class="btn ghost small" data-close>Close</button></div>
        <div class="chips" style="margin:6px 0 12px">${EFFECTS.map(([, n, c]) => chip(c, n)).join("")}</div>
        <ul class="plain">${(g.principles || []).map((x) => li("grey", "·", esc(x))).join("")}</ul>
        <div class="ph" style="margin-top:14px">Verdict rule</div>
        <dl class="vrule">${Object.entries(g.verdict || {}).map(([k, v]) => `<div><dt>${verdictBadgeSmall(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>
        <div class="ph" style="margin-top:14px">Signals<span class="aside">thresholds read from the code</span></div>
        <div class="sig-grid">${(g.signals || []).map((x) => `<div class="sig well"><div class="sig-h"><b>${esc(x.name)}</b><span class="faint small">${esc(x.agent)} agent · ${esc(x.pillar)}</span></div>
          <div class="small muted">${esc(x.measures)}</div>
          <div class="sig-r"><span class="arrow green">↑</span><span>${esc(x.supports)}</span></div>
          <div class="sig-r"><span class="arrow amber">↓</span><span>${esc(x.against)}</span></div>
          <div class="sig-r"><span class="arrow grey">?</span><span>${esc(x.unknown)}</span></div>
          <div class="small"><span class="faint">Source:</span> ${esc(x.source)}</div>
          <div class="small"><span class="faint">How accurate:</span> ${esc(x.accuracy)}</div></div>`).join("")}</div>
        ${look.length ? `<div class="ph" style="margin-top:14px">Lookalike accuracy by business<span class="aside">spatial hold-out AUC · 0.5 = chance · votes at ≥ ${g.thresholds.validated_auc}</span></div>
          <table class="findings acc"><tbody>${look.map((x) => `<tr><td>${esc(x.label)}</td><td class="num">${x.auc.toFixed(2)}</td><td><div class="bar"><span style="width:${Math.max(0, (x.auc - 0.5) / 0.5 * 100)}%"></span></div></td><td class="small ${x.votes ? "" : "faint"}">${esc(x.note)}</td></tr>`).join("")}</tbody></table>` : ""}
        ${rent ? `<div class="ph" style="margin-top:14px">Rent model vs recent comps<span class="aside">median error on ${num(rent.held_out)} held-out signed deals · trained on ${num(rent.deals_trained)}</span></div>
          <table class="findings acc"><thead><tr><th>Space use</th><th>Model</th><th>Comps</th><th>Range holds</th></tr></thead><tbody>${rent.by_use.map((x) => `<tr><td>${esc(x.use)} <span class="faint small">n=${x.n}</span></td><td class="num">${x.model_error_pct}%</td><td>${x.comps_error_pct}%</td><td>${x.range_coverage_pct ?? "—"}%${x.model_wins ? "" : ` <span class="faint small">comps better here</span>`}</td></tr>`).join("")}</tbody></table>` : ""}
      </div>`;
    } catch (e) { dlg.innerHTML = `<div class="legend-in"><div class="error">Signal guide unavailable: ${esc(e.message)}</div><button class="btn ghost small" data-close>Close</button></div>`; }
  }
  document.addEventListener("click", (e) => { if (e.target.closest("[data-legend]")) { e.preventDefault(); openLegend(); } });
  function verdictBadgeSmall(v) { return chip(VERDICT_CHIP[v] || "grey", VLABEL[v] || v); }

  function figures(r) {
    const m = r.pillars.money, rent = m.rent || {}, req = m.required || {}, months = m.months_of_rent_after_opening;
    const dem = look(DEMAND, r.pillars.demand.verdict)[1];
    return `<div class="panel"><div class="ph">Key figures</div><dl class="figures">
      <div><dt>Cash to open (base)</dt><dd>${kmoney(m.cash_to_open.base)}</dd><span class="sub">${kmoney(m.cash_to_open.low)}–${kmoney(m.cash_to_open.high)}${src(costSrc(m.basis_quality))}</span></div>
      <div><dt>Needed incl. reserve</dt><dd>${kmoney(req.base)}</dd><span class="sub">vs ${kmoney(inputs().budget)} budget · ${esc(look(AFFORD, m.affordability)[1])}</span></div>
      <div><dt>Months of rent left</dt><dd>${months ?? "—"}</dd><span class="sub">After opening, with zero revenue</span></div>
      <div><dt>Asking rent</dt><dd>${rent.monthly != null ? money(rent.monthly) + "/mo" : "Not listed"}</dd><span class="sub">${rent.monthly != null ? `$${rent.psf_year}/sq ft/yr${src(rentSrc(rent))}` : "Ask the broker"}</span></div>
      <div><dt>Neighborhood</dt><dd>${esc(cap(dem.replace(/^Neighborhood /, "")))}</dd><span class="sub">${src(demandSrc(r.business))}</span></div>
    </dl></div>`;
  }
  function pillarsHtml(r, p) {
    const P = r.pillars, m = P.money, sp = P.space, d = P.demand, i = inputs();
    const ind = (state.industries || []).find((x) => x.key === r.business) || {};
    const fit = look(FIT, sp.status), aff = look(AFFORD, m.affordability), dem = look(DEMAND, d.verdict);
    const recs = P.records || [], permits = P.permits || [], jur = r.jurisdiction || {}, tours = P.tours || [];
    const conflicts = recs.filter((x) => x.status !== "unknown");
    const rent = m.rent || {};
    const dw = m.delay_what_if || {};
    const ledger = (m.lines || []).map((l) => `<tr><td>${esc(l.label)}<span class="how">${esc(l.how || "")}${l.source ? ` · ${esc(l.source)}` : ""}</span></td><td>${money(l.low)}</td><td class="base">${money(l.base)}</td><td>${money(l.high)}</td></tr>`).join("");
    const req = m.required || {}, left = i.budget - (req.base || 0);
    const evidenceRow = (r.evidence || []).find((e) => e.fact === "building_facts");
    const ceiling = evidenceRow && evidenceRow.value ? evidenceRow.value.ceiling_ft : null;
    return `<div class="pillars">
      <details class="pillar" data-p="space"><summary><span class="ptitle">Space</span>${chip(fit[0], fit[1])}<span class="pline">${esc(sp.capacity || (sp.reasons || [])[0] || "")}</span></summary>
        <div class="pillar-body"><div class="space-view"><div class="space3d" data-sf="${p.sf || r.space.sf || 0}" data-ceiling="${ceiling || ""}"><span class="cap">${num(p.sf || r.space.sf)} sq ft drawn to scale · ${ceiling ? ceiling + " ft ceiling" : "ceiling not recorded (dashed)"}</span></div>
          <ul class="plain">${(sp.reasons || []).map((x) => li("green", "✓", esc(x))).join("")}${(sp.unknowns || []).map((x) => li("grey", "?", esc(x))).join("")}${(sp.verify || []).map((x) => li("amber", "!", "Verify: " + esc(x))).join("")}</ul></div>
          <div class="muted small">Building facts${src("CoStar")}. Sizes and fits are checked against each business's space needs; columns and layout are not.</div></div></details>
      <details class="pillar" data-p="money"><summary><span class="ptitle">Money</span>${chip(aff[0], aff[1])}<span class="pline">Cash to open <span class="num">${kmoney(m.cash_to_open.base)}</span> (${kmoney(m.cash_to_open.low)}–${kmoney(m.cash_to_open.high)})${m.months_of_rent_after_opening != null ? ` · ${m.months_of_rent_after_opening} months of rent left with zero revenue` : ""}</span></summary>
        <div class="pillar-body">
          <div class="stress">
            <div class="stat well"><div class="k">Needed incl. ${kmoney(r.reserve)} reserve (base)</div><div class="v">${kmoney(req.base)}</div><div class="k">${kmoney(req.low)}–${kmoney(req.high)}</div></div>
            <div class="stat well"><div class="k">Left of your ${kmoney(i.budget)} (base)</div><div class="v ${left < 0 ? "red" : "green"}">${left < 0 ? "−" : ""}${kmoney(Math.abs(left))}</div></div>
            <div class="stat well"><div class="k">Months of rent left after opening, zero revenue</div><div class="v ${m.months_of_rent_after_opening == null ? "" : m.months_of_rent_after_opening < 6 ? "red" : m.months_of_rent_after_opening < 12 ? "amber" : "green"}">${m.months_of_rent_after_opening ?? "—"}</div></div>
            ${dw.required ? `<div class="stat well"><div class="k">If opening slips 3 months (base)</div><div class="v ${dw.affordability === "within" ? "green" : dw.affordability === "stretch" ? "amber" : "red"}">${kmoney(dw.required.base)}</div><div class="k">${esc(look(AFFORD, dw.affordability)[1])} · ${dw.months_of_rent_after_opening ?? "—"} mo left</div></div>` : ""}
          </div>
          <div class="cash-one" data-cash="1"></div>
          <table class="ledger"><thead><tr><th>What you pay before opening</th><th>Low</th><th>Base</th><th>High</th></tr></thead>
            <tbody>${ledger}<tr class="total"><td>Cash to open</td><td>${money(m.cash_to_open.low)}</td><td>${money(m.cash_to_open.base)}</td><td>${money(m.cash_to_open.high)}</td></tr></tbody></table>
          ${m.excludes ? `<div>${chip("amber", "Excludes " + m.excludes)}</div>` : ""}${m.note ? `<div class="muted small">${esc(m.note)}</div>` : ""}
          ${dw.franchise_fee_excluded ? `<div class="muted small">Franchise fee left out (independent operator): ${kmoney(dw.franchise_fee_excluded[0])}–${kmoney(dw.franchise_fee_excluded[1])} if you franchise.</div>` : ""}
          <details><summary class="link-btn">Where these numbers come from (${(m.sources || []).length})</summary>
            <div class="sources" style="margin-top:8px">${(m.sources || []).map((s) => `<div class="source"><b>${esc(s.publisher_or_brand)}</b>, ${esc(s.document)} · ${ext(s.url, "Source")}<q>${esc(s.quote)}</q></div>`).join("")}
            <div class="muted small">Franchise disclosure document (Item 7) ranges, scaled to this space's size, plus the listing's 2-month deposit and rent while building. No revenue forecast.</div></div></details>
        </div></details>
      <details class="pillar" data-p="deal"><summary><span class="ptitle">Deal</span>${rent.monthly != null ? chip("green", "Rent listed") : chip("grey", "Rent not listed")}<span class="pline">${rent.monthly != null ? `${money(rent.monthly)}/month · $${rent.psf_year}/sq ft/yr` : "Ask the broker for the rent"}</span></summary>
        <div class="pillar-body"><ul class="plain">
          ${li(rent.monthly != null ? "green" : "grey", rent.monthly != null ? "✓" : "?", rent.monthly != null ? `Asking ${money(rent.monthly)}/month ($${rent.psf_year}/sq ft/yr)${src(rentSrc(rent))} <span class="muted">${esc(rent.source || "")}</span>` : "No asking rent listed: the broker has to quote it")}
          ${li(r.space.lease_basis && !/determined/i.test(r.space.lease_basis) ? "green" : "grey", r.space.lease_basis && !/determined/i.test(r.space.lease_basis) ? "✓" : "?", `Lease basis: ${esc(r.space.lease_basis || "unknown")}`)}
          ${li(r.space.available_on ? "green" : "grey", r.space.available_on ? "✓" : "?", `Available: ${esc(r.space.available_on || "date not listed")}`)}
          ${r.space.lease_pending ? li("amber", "!", "A lease is pending on this space") : ""}
        </ul></div></details>
      <details class="pillar" data-p="records"><summary><span class="ptitle">Records</span><span class="chips">${tours.length ? chip("grey", `${tours.length} tour${tours.length > 1 ? "s" : ""}`) : ""}${conflicts.length ? chip("amber", `${conflicts.length} to check`) : recs.length ? chip("grey", `${recs.length} unconfirmed`) : chip("green", "No conflicts")}</span><span class="pline">${recs.length ? esc(recs[0].note.split(".")[0]) : "CoStar's record and the linked scans agree on what we could check"}</span></summary>
        <div class="pillar-body">${tours.length ? `<div class="tours">${tours.map((t) => `<div class="tour well"><div><b>3D tour</b>${src("Matterport via CoStar")} ${t.caption ? `<span class="muted">· ${esc(t.caption)}</span>` : ""}<div class="small faint">${t.captured_at ? "Attached " + esc(day(t.captured_at)) + " · " : ""}${esc(t.note)}</div></div>${ext(t.url, "Open tour")}</div>`).join("")}</div>` : `<div class="muted small">No Matterport tour is linked to this building in CoStar.</div>`}<ul class="plain">${recs.length ? recs.map((x) => li(x.status === "unknown" ? "grey" : "amber", x.status === "unknown" ? "?" : "!", `<b>${esc(x.fact.replace(/_/g, " "))}</b>: ${esc(Array.isArray(x.value) ? x.value.join(", ") : typeof x.value === "object" ? JSON.stringify(x.value) : x.value)}<br><span class="muted small">${esc(x.note)}</span>${x.evidence_url ? " " + ext(x.evidence_url, "Open") : ""}${src(x.source)}`)).join("") : li("green", "✓", "No disagreements between CoStar and the linked tours")}</ul></div></details>
      <details class="pillar" data-p="permits"><summary><span class="ptitle">Permits</span><span class="chips">${jur.code === "houston" ? chip("green", "City of Houston") : jur.code === "harris_unincorporated" ? chip("amber", "Harris County") : jur.place ? chip("amber", jur.place) : chip("grey", "Jurisdiction unknown")}${chip("amber", `${permits.length} to verify`)}</span><span class="pline">${jur.code === "harris_unincorporated" ? "City of Houston permits don't apply; Harris County does." : `${esc((r.permit_authority || {}).name || "City")} change-of-use path + business licenses.`} None counted as cleared.</span></summary>
        <div class="pillar-body"><ul class="plain permits">${permits.map((x) => `<li><span class="mk amber">!</span><span><b>${esc(x.title)}</b> · <span class="muted">${esc(x.authority)}</span><br><span class="small">${esc(x.detail)}</span></span>${x.url ? ext(x.url, "Official page") : ""}</li>`).join("")}</ul>
          <div class="muted small">${jur.verified ? `Jurisdiction from the pin, not the postal city: ${esc(jur.note || "")}${src("Census geocoder")} ${ext(jur.evidence_url, "Boundary lookup")}` : jur.place ? esc(jur.note || "") : `Jurisdiction not verified (${esc(jur.note || "not looked up")}): City of Houston rules are shown as an assumption.`} No timelines are claimed; nothing here is an approval.</div></div></details>
      <details class="pillar" data-p="neighborhood"><summary><span class="ptitle">Neighborhood</span>${chip(dem[0], dem[1])}<span class="pline">${esc(d.headline || "")}</span></summary>
        <div class="pillar-body">${d.insight ? `<div><b>${esc(d.insight)}</b></div>` : ""}
          <ul class="plain">${(d.reasons || []).map((x) => { const [c, mk] = stanceMark(x.stance); return li(c, mk, `${esc(x.reason)} <span class="muted small">(${esc(x.signal)})</span>`); }).join("")}${(d.unknown || []).map((x) => li("grey", "?", esc(typeof x === "string" ? x : x.reason || JSON.stringify(x)))).join("")}</ul>
          <div class="muted small">Sources${src(demandSrc(r.business))}. ${ind.lookalike_auc ? `Lookalike accuracy for ${esc(ind.label)}: AUC ${ind.lookalike_auc} on held-out areas (0.5 = chance)${ind.validated ? "" : ", too weak to vote"}. Mostly an income signal; it finds gaps, not winners.` : "The lookalike score is not validated for this business."}</div></div></details>
    </div>`;
  }
  function mission(r) {
    return `<div class="panel"><div class="ph">Agent run<span class="aside">${(r.trace || []).length} steps</span></div>
      <div class="mission">${(r.trace || []).map((t, k) => `<div class="mstep" data-k="${k}" title="${esc(t.role)}">${agentImg(t.agent)}<div style="min-width:0"><div class="n">${esc(t.agent)}</div><div class="s">${esc(t.summary || "")}</div></div></div>`).join("")}</div>
      <div class="trace-detail well" id="trace-detail"></div></div>`;
  }
  async function stageInvestigate(el) {
    const list = state.v.shortlist || [];
    if (!list.length) { el.innerHTML = `${head("investigate", "Investigate", "")}<div class="panel">Shortlist at least one place first.</div>`; return; }
    const keys = list.map(pairKey);
    if (!keys.includes(state.tab)) state.tab = keys[0];
    await industries();
    const tabs = () => list.map((p) => { const k = pairKey(p), r = state.reviews[k]; return `<button data-k="${esc(k)}" class="${k === state.tab ? "on" : ""}">${r ? chip(VERDICT_CHIP[r.verdict] || "grey", VLABEL[r.verdict] || r.verdict) : state.reviewErr[k] ? chip("red", "error") : `<span class="spinner" style="width:12px;height:12px"></span>`}${esc(p.label)} · ${esc(p.address.split(",")[0])}</button>`; }).join("");
    el.innerHTML = `${head("investigate", "Investigate", "Thirteen agents review each place: the space, the money, the deal, the records, the permits and the neighborhood. Verdict first; open any section for the evidence.")}
      <div class="tabs" id="tabs">${tabs()}</div><div id="review"></div>
      <div class="sticky-bar"><span class="muted" id="rev-note"></span><button class="btn primary" id="next">Compare and decide${ic("right")}</button></div>`;
    const bindTabs = () => el.querySelectorAll("#tabs button").forEach((b) => b.onclick = () => { state.tab = b.dataset.k; el.querySelector("#tabs").innerHTML = tabs(); bindTabs(); show(true); });
    bindTabs();
    const note = () => { const n = Object.keys(state.reviews).filter((k) => keys.includes(k)).length; el.querySelector("#rev-note").innerHTML = `<b class="num">${n}</b> of ${keys.length} reviewed`; el.querySelector("#next").disabled = !n; };
    const show = (animate) => {
      clearTimers();
      const box = el.querySelector("#review"), k = state.tab, p = list.find((x) => pairKey(x) === k), r = state.reviews[k];
      if (state.reviewErr[k]) { box.innerHTML = `<div class="error">${esc(state.reviewErr[k])}</div>`; return; }
      if (!r) { box.innerHTML = `<div class="loading"><span class="spinner"></span>Agents are reviewing ${esc(p.label)} at ${esc(p.address)}…</div>`; return; }
      box.innerHTML = `<div class="inv"><div class="inv-main" id="vc" style="opacity:0">${verdictCard(r, p)}${whyHtml(r)}${pillarsHtml(r, p)}${sourcesHtml(r)}</div><aside class="inv-side">${figures(r)}${mission(r)}</aside></div>`;
      const steps = [...box.querySelectorAll(".mstep")];
      const reveal = () => { const vc = box.querySelector("#vc"); if (vc) vc.style.opacity = 1; };
      if (animate) { steps.forEach((s, j) => later(() => s.classList.add("lit"), 80 + j * 110)); later(reveal, 80 + steps.length * 110); }
      else { steps.forEach((s) => s.classList.add("lit")); reveal(); }
      const openStep = (s, highlight, force) => {
        const t = r.trace[+s.dataset.k], det = box.querySelector("#trace-detail");
        const open = s.classList.contains("active");
        steps.forEach((x) => x.classList.remove("active"));
        if (open && !force) { det.innerHTML = ""; return; }
        s.classList.add("active");
        det.innerHTML = stepHtml(t, r, highlight);
      };
      steps.forEach((s) => s.onclick = () => openStep(s));
      box.querySelectorAll(".why-row").forEach((row) => {
        const go = () => {
          const s = steps.find((x) => r.trace[+x.dataset.k].agent === row.dataset.agent);
          if (!s) { toast(`The ${row.dataset.agent} step is not in this run`); return; }
          const why = (r.because || [])[+row.dataset.i] || {};
          openStep(s, why.evidence || [], true);
          box.querySelectorAll(".why-row").forEach((x) => x.classList.toggle("on", x === row));
          const det = box.querySelector("#trace-detail");
          (det.querySelector("tr.hl") || s).scrollIntoView({ behavior: "smooth", block: "center" });
        };
        row.onclick = go; row.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } };
      });
      const one = box.querySelector("[data-cash]");
      if (one) { const items = [{ label: r.label.split(" / ")[0], c: r.pillars.money.cash_12m }]; const draw = () => { one.innerHTML = `<div class="ph" style="margin-bottom:6px">Next 12 months, zero revenue</div>` + cashChart(items); bindCash(one, items, draw); }; draw(); }
      const space = box.querySelector(".space3d");
      box.querySelector('details[data-p="space"]').addEventListener("toggle", function onT(ev) {
        if (!ev.target.open || space.dataset.drawn) return;
        space.dataset.drawn = 1;
        if (has3d()) {
          try {
            const c = window.Suite3D.space(space, { sf: +space.dataset.sf, ceiling_ft: +space.dataset.ceiling || null, business: r.business, label: r.label });
            if (c) {
              state.ctrls.push(c);
              // The drawing assumes a floor shape; say so, since area-only capacity (above) can differ.
              if (c.info && c.info.assumed) space.querySelector(".cap").textContent = `Drawn to scale. ${c.info.assumed}`;
            }
          } catch { /* 2D text stays */ }
        }
      });
      box.querySelector("[data-explain]").onclick = async (ev) => {
        const b = ev.currentTarget, out = box.querySelector(".narr"); b.disabled = true;
        out.innerHTML = `<div class="loading" style="padding:8px 0"><span class="spinner"></span>Writing a plain-English summary…</div>`;
        try {
          const x = await review(p, true);
          out.innerHTML = x.narration ? `<div class="narration"><span class="ai-label">${ic("spark", 12)}${esc(x.narration_label || "AI-written, numbers checked")}</span><div>${esc(x.narration)}</div></div>` : `<div class="muted small">No AI summary available (no LLM key on this server). The verdict above is computed in code.</div>`;
        } catch (e) { out.innerHTML = `<div class="muted small">AI summary unavailable: ${esc(e.message)}</div>`; }
      };
    };
    show(false); note();
    for (const p of list) {
      const k = pairKey(p);
      if (state.reviews[k]) continue;
      try { state.reviews[k] = await review(p); } catch (e) { state.reviewErr[k] = e.message; }
      if (!el.isConnected) return;
      el.querySelector("#tabs").innerHTML = tabs(); bindTabs(); note();
      if (k === state.tab) show(true);
      refreshRail("investigate");
    }
    el.querySelector("#next").onclick = () => goStage("decide");
  }

  // ---------- Stage 6: decide ----------
  // ---------- 12-month cash, zero revenue (Jayant's Nessie-pilot simulator on the real cost + rent) ----------
  const SERIES = ["#3987e5", "#d95926", "#199e70"]; // categorical slots 1-3, validated on this dark surface
  function cashSentence(c, label) {
    const k = c.cases[cashCase], open = k.opens, late = k.opens_if_delayed;
    if (k.first_month_below_zero) return `<b>${esc(label)}</b> ${k.first_month_below_reserve && k.first_month_below_reserve < k.first_month_below_zero ? `dips into your reserve in month ${k.first_month_below_reserve} and ` : ""}runs out of cash in month ${k.first_month_below_zero}${k.first_month_below_zero < open ? ", before it even opens" : ""}.`;
    if (k.first_month_below_reserve) {
      const after = k.first_month_below_reserve - open, afterLate = k.first_month_below_reserve - late;
      return `<b>${esc(label)}</b> dips into your reserve in month ${k.first_month_below_reserve}: ${after > 0 ? `${after} month${after > 1 ? "s" : ""} after opening` : "before opening"}${after > 0 ? `; ${afterLate > 0 ? `${afterLate}` : "0"} if opening slips ${c.delay} months` : ""}.`;
    }
    return `<b>${esc(label)}</b> stays above your reserve for all ${c.months} months with zero revenue (${kmoney(k.cash[c.months])} left).`;
  }
  let cashCase = "base";
  function cashChart(items) { // items: [{label, c}] with c = pillars.money.cash_12m
    items = items.filter((x) => x.c);
    if (!items.length) return `<div class="muted small">No 12-month view: the listing has no asking rent to bill.</div>`;
    const c0 = items[0].c, M = c0.months, W = 1100, H = 340, L = 64, R = 150, T = 16, B = 36;
    const axm = (v) => (Math.abs(v) < 1 ? "$0" : (v < 0 ? "−" : "") + kmoney(Math.abs(v)));
    const vals = items.flatMap((x) => x.c.cases[cashCase].cash).concat([0, c0.reserve, c0.budget]);
    let lo = Math.min(...vals), hi = Math.max(...vals);
    const pad = (hi - lo) * 0.06; lo -= pad; hi += pad;
    const x = (m) => L + (W - L - R) * m / M, y = (v) => T + (H - T - B) * (hi - v) / (hi - lo);
    const ticks = []; const step = Math.pow(10, Math.floor(Math.log10((hi - lo) / 4))) * ([1, 2, 5].find((f) => (hi - lo) / (Math.pow(10, Math.floor(Math.log10((hi - lo) / 4))) * f) <= 5) || 10);
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push(v);
    const k0 = c0.cases[cashCase];
    // nudge line-end labels apart so they never overlap (direct labels, <= 3 series)
    const ends = items.map((it, j) => ({ j, yy: y(it.c.cases[cashCase].cash[M]) })).sort((a, b) => a.yy - b.yy);
    const labelNudge = items.map(() => 0);
    ends.forEach((e, n) => { if (n && e.yy + labelNudge[e.j] - (ends[n - 1].yy + labelNudge[ends[n - 1].j]) < 15) labelNudge[e.j] = ends[n - 1].yy + labelNudge[ends[n - 1].j] + 15 - e.yy; });
    const lines = items.map((it, j) => {
      const k = it.c.cases[cashCase], pts = k.cash.map((v, m) => `${x(m).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
      const end = k.cash[M], dip = k.first_month_below_reserve;
      return `<polyline points="${pts}" fill="none" stroke="${SERIES[j]}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
        ${dip ? `<circle cx="${x(dip)}" cy="${y(k.cash[dip])}" r="5" fill="${SERIES[j]}" stroke="#141518" stroke-width="2"><title>${esc(it.label)}: below the reserve in month ${dip}</title></circle>` : ""}
        <text x="${x(M) + 8}" y="${y(end) + 4 + labelNudge[j]}" class="cc-lab">${esc(it.label.split(" · ")[0].slice(0, 20))}</text>`;
    }).join("");
    const svg = `<svg class="cc" viewBox="0 0 ${W} ${H}" role="img" aria-label="Cash balance over ${M} months with zero revenue">
      <rect x="${x(0)}" y="${T}" width="${x(k0.opens - 1) - x(0)}" height="${H - T - B}" class="cc-build"/>
      <text x="${x(0) + 6}" y="${T + 14}" class="cc-note">building out</text>
      ${ticks.map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="cc-grid"/><text x="${L - 8}" y="${y(v) + 4}" class="cc-ax" text-anchor="end">${axm(v)}</text>`).join("")}
      <line x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}" class="cc-zero"/><text x="${W - R - 4}" y="${y(0) + 14}" class="cc-note" text-anchor="end">out of cash</text>
      <line x1="${L}" x2="${W - R}" y1="${y(c0.reserve)}" y2="${y(c0.reserve)}" class="cc-res"/><text x="${W - R - 4}" y="${y(c0.reserve) + 14}" class="cc-note" text-anchor="end">your ${kmoney(c0.reserve)} reserve</text>
      <line x1="${x(k0.opens - 1)}" x2="${x(k0.opens - 1)}" y1="${T}" y2="${H - B}" class="cc-open"/><text x="${x(k0.opens - 1) + 4}" y="${H - B - 6}" class="cc-note">opens</text>
      <line x1="${x(k0.opens_if_delayed - 1)}" x2="${x(k0.opens_if_delayed - 1)}" y1="${T}" y2="${H - B}" class="cc-late"/><text x="${x(k0.opens_if_delayed - 1) + 4}" y="${H - B - 6}" class="cc-note">opens if ${c0.delay} mo late</text>
      ${Array.from({ length: M + 1 }, (_, m) => `<text x="${x(m)}" y="${H - 12}" class="cc-ax" text-anchor="middle">${m}</text>`).join("")}
      <text x="${(L + W - R) / 2}" y="${H}" class="cc-ax" text-anchor="middle">month</text>
      ${lines}
      <line class="cc-cross" x1="0" x2="0" y1="${T}" y2="${H - B}" visibility="hidden"/>
      <rect class="cc-hit" x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent"/>
    </svg>`;
    const legend = items.length > 1 ? `<div class="cc-legend">${items.map((it, j) => `<span><i style="background:${SERIES[j]}"></i>${esc(it.label)}</span>`).join("")}</div>` : "";
    const table = `<details class="cc-table"><summary class="link-btn">Table view</summary><div class="table-scroll"><table class="findings"><thead><tr><th>Month</th>${items.map((it) => `<th>${esc(it.label)}</th>`).join("")}</tr></thead><tbody>${Array.from({ length: M + 1 }, (_, m) => `<tr><td>${m}</td>${items.map((it) => `<td class="num">${money(it.c.cases[cashCase].cash[m])}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details>`;
    return `<div class="cc-wrap" data-n="${items.length}">
      <div class="cc-top"><div class="seg cc-case">${["low", "base", "high"].map((k) => `<button type="button" data-case="${k}" class="${k === cashCase ? "on" : ""}">${cap(k)} cost</button>`).join("")}</div>${legend}</div>
      <div class="cc-plot">${svg}<div class="cc-tip" hidden></div></div>
      <ul class="plain cc-says">${items.map((it, j) => `<li><span class="mk" style="color:${SERIES[j]}">●</span><span>${cashSentence(it.c, it.label)}</span></li>`).join("")}</ul>
      <div class="faint small">Starts from your ${kmoney(c0.budget)}; opening costs from the sourced ledger are paid up front, then the CoStar asking rent every month. <b>Zero revenue</b>, and no payroll or utilities, so real runway is shorter. Computed with Jayant's Nessie-pilot simulator. ${table}</div>
    </div>`;
  }
  function bindCash(root, items, rerender) {
    root.querySelectorAll(".cc-case button").forEach((b) => b.onclick = () => { cashCase = b.dataset.case; rerender(); });
    root.querySelectorAll(".cc-plot").forEach((plot) => {
      const svg = plot.querySelector("svg"), hit = plot.querySelector(".cc-hit"), tip = plot.querySelector(".cc-tip"), cross = plot.querySelector(".cc-cross");
      if (!svg || !hit) return;
      const its = items.filter((x) => x.c), M = its[0].c.months, vb = svg.viewBox.baseVal, L = 64, R = 150;
      hit.onmousemove = (ev) => {
        const r = svg.getBoundingClientRect(), sx = (ev.clientX - r.left) * vb.width / r.width;
        const m = Math.max(0, Math.min(M, Math.round((sx - L) / (vb.width - L - R) * M))), xx = L + (vb.width - L - R) * m / M;
        cross.setAttribute("x1", xx); cross.setAttribute("x2", xx); cross.setAttribute("visibility", "visible");
        tip.hidden = false; tip.style.left = Math.min(r.width - 190, (xx * r.width / vb.width) + 12) + "px";
        tip.innerHTML = `<b>Month ${m}</b>${its.map((it, j) => `<div><i style="background:${SERIES[j]}"></i>${esc(it.label)} <span class="num">${money(it.c.cases[cashCase].cash[m])}</span></div>`).join("")}`;
      };
      hit.onmouseleave = () => { tip.hidden = true; cross.setAttribute("visibility", "hidden"); };
    });
  }

  async function stageDecide(el) {
    const list = state.v.shortlist || [];
    el.innerHTML = `<div class="loading"><span class="spinner"></span>Gathering verdicts…</div>`;
    for (const p of list) { const k = pairKey(p); if (!state.reviews[k]) { try { state.reviews[k] = await review(p); } catch (e) { state.reviewErr[k] = e.message; } } }
    const order = { GO: 0, CONDITIONAL: 1, "NO-GO": 2 };
    const rows = list.map((p) => ({ p, r: state.reviews[pairKey(p)] })).filter((x) => x.r).sort((a, b) => (order[a.r.verdict] ?? 3) - (order[b.r.verdict] ?? 3));
    const ch = state.v.chosen ? pairKey(state.v.chosen) : null, budget = inputs().budget;
    const isCh = (p) => pairKey(p) === ch;
    const cell = (fn) => rows.map(({ p, r }) => `<td class="${isCh(p) ? "chosen" : ""}">${fn(p, r)}</td>`).join("");
    el.innerHTML = `${head("decide", "Decide", "Side by side: the deciding reason and what would flip each one. Commit to one and its open checks become your plan.")}
      ${rows.length ? `<div class="glass cmp-card"><div class="table-scroll"><table class="cmp">
        <thead><tr><th></th>${rows.map(({ p, r }) => `<th class="${isCh(p) ? "chosen" : ""}"><div class="eyebrow">${esc(r.label)}</div><div class="ct">${esc(r.address.split(",")[0])} · ${esc(p.suite_label)}</div>${verdictBadge(r.verdict, true)}</th>`).join("")}</tr></thead>
        <tbody>
          <tr><th>Deciding reason</th>${cell((p, r) => esc(tidy((r.blockers || [])[0] || (r.conditions || [])[0] || (r.reasons || [])[0] || "")))}</tr>
          <tr><th>What would flip it</th>${cell((p, r) => esc(tidy((r.flips || [])[0]) || (r.verdict === "GO" ? "Nothing flagged; checks still apply" : "—")))}</tr>
          <tr><th>Needed incl. reserve</th>${cell((p, r) => `<span class="num">${kmoney(r.pillars.money.required.base)}</span> <span class="faint">of ${kmoney(budget)}</span>${src(costSrc(r.pillars.money.basis_quality))}`)}</tr>
          <tr><th>Months of rent left</th>${cell((p, r) => `<span class="num">${r.pillars.money.months_of_rent_after_opening ?? "—"}</span> <span class="faint">with zero revenue</span>`)}</tr>
          <tr><th>Neighborhood</th>${cell((p, r) => { const d = look(DEMAND, r.pillars.demand.verdict); return chip(d[0], d[1]) + src(demandSrc(r.business)); })}</tr>
          <tr><th>Open checks</th>${cell((p, r) => `<span class="num">${(r.checks || []).length + (r.pillars.permits || []).length}</span>`)}</tr>
          <tr class="act"><th></th>${cell((p) => { const k = pairKey(p); return `<button class="btn ${isCh(p) ? "" : "primary"} block" data-k="${esc(k)}">${isCh(p) ? ic("check", 14) + "Committed" : "Commit to this one"}</button>`; })}</tr>
        </tbody></table></div></div>
        <div class="panel cash-panel"><div class="ph">The next 12 months with zero revenue<span class="aside">which pick dips into your reserve, and when</span></div><div id="cash12"></div></div>` : `<div class="panel">No reviews yet.</div>`}`;
    const cashItems = rows.map(({ p, r }) => ({ label: `${r.label.split(" / ")[0]} · ${r.address.split(",")[0]}`, c: r.pillars.money.cash_12m }));
    const drawCash = () => { const box = el.querySelector("#cash12"); if (!box) return; box.innerHTML = cashChart(cashItems); bindCash(box, cashItems, drawCash); };
    drawCash();
    el.querySelectorAll("button[data-k]").forEach((b) => b.onclick = async () => {
      const p = list.find((x) => pairKey(x) === b.dataset.k), r = state.reviews[b.dataset.k];
      if (r.verdict === "NO-GO" && !confirm("This one is NO-GO. Commit anyway and plan around the blocker?")) return;
      await save({ chosen: Object.assign({}, p, { verdict: r.verdict }), status: "verifying", checklist: {} });
      goStage("plan");
    });
  }

  // ---------- Stage 7: plan & track ----------
  const WHO = [
    ["broker", "Broker", "brief", /records disagree|caption|scan|survey|size field|asking|rent|lease basis|available|pending|suite/i],
    ["landlord", "Landlord", "key", /landlord|tenant-improvement|build-out|outdoor|fenced|plumb|ventilat|hvac|electric|power|ceiling|parking|loading|deed|grease|hood|drain|floor|consent|signage/i],
    ["inspector", "Inspector", "shield", /inspect|fire|accessib|occupancy|final|sprinkler|exit/i],
    ["city", "City & state", "landmark", /permit|license|certificate|registration|tax|city|county|state|health|tabc|tdlr|hhsc/i],
  ];
  function planItems(r) {
    const items = [], seen = new Set();
    const add = (text, who, extra) => { const t = String(text).trim(); const id = t.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 60); if (!t || seen.has(id)) return; seen.add(id); items.push(Object.assign({ id, text: t, who }, extra || {})); };
    const classify = (t) => (WHO.find(([, , , re]) => re.test(t)) || ["you"])[0];
    (r.blockers || []).forEach((t) => add(t, "you", { blocker: true }));
    (r.conditions || []).concat(r.checks || []).forEach((t) => add(t, classify(t)));
    (r.pillars.permits || []).forEach((x) => add(`${x.title} (${x.authority})`, /inspect|fire|final/i.test(x.title) ? "inspector" : x.authority === "City of Houston" && /deed|allowed use/i.test(x.title) ? "landlord" : "city", { url: x.url }));
    if (r.pillars.money && r.pillars.money.rent && r.pillars.money.rent.monthly == null) add("Get the asking rent quoted", "broker");
    return items;
  }
  async function stagePlan(el) {
    const c = state.v.chosen;
    if (!c) { el.innerHTML = `${head("plan", "Plan & track", "")}<div class="panel">Commit to one place in Decide first.</div>`; return; }
    el.innerHTML = `<div class="loading"><span class="spinner"></span>Building your plan…</div>`;
    const k = pairKey(c);
    if (!state.reviews[k]) state.reviews[k] = await review(c);
    const r = state.reviews[k], items = planItems(r), done = Object.assign({}, state.v.checklist || {});
    const groups = [["you", "You", "compass"]].concat(WHO.map(([id, name, icon]) => [id, name, icon]))
      .map(([id, name, icon]) => ({ id, name, icon, items: items.filter((x) => x.who === id) })).filter((g) => g.items.length);
    const render = () => {
      const n = items.filter((x) => done[x.id]).length;
      el.innerHTML = `${head("plan", "Plan & track", `Every open question for <b>${esc(c.label)}</b> at ${esc(c.address)}, grouped by who can answer it. Tick them off as answers come in; progress shows on your venture card.`)}
        <div class="panel plan-progress">${verdictBadge(r.verdict)}
          <div class="pp"><div style="display:flex;justify-content:space-between;gap:12px"><b>${n} of ${items.length} checks answered</b><span class="muted small">${n === items.length ? "Ready to sign" : `${items.length - n} open`}</span></div><div class="check-bar"><i style="width:${items.length ? Math.round(100 * n / items.length) : 0}%"></i></div></div></div>
        <div class="grid who">${groups.map((g) => `<div class="panel"><div class="ph">${ic(g.icon)}${esc(g.name)}<span class="count">${g.items.filter((x) => done[x.id]).length} / ${g.items.length}</span></div>
          ${g.items.map((x) => `<label class="check ${done[x.id] ? "done" : ""}"><input type="checkbox" data-id="${esc(x.id)}" ${done[x.id] ? "checked" : ""}><span>${x.blocker ? chip("red", "Blocks") + " " : ""}${esc(tidy(x.text))}${x.url ? " " + ext(x.url, "Official page") : ""}</span></label>`).join("")}</div>`).join("")}</div>`;
      el.querySelectorAll("input[data-id]").forEach((b) => b.onchange = async () => {
        if (b.checked) done[b.dataset.id] = true; else delete done[b.dataset.id];
        const n2 = items.filter((x) => done[x.id]).length;
        const status = n2 === items.length ? "ready" : "verifying";
        render();
        await save({ checklist: done, status, summary: Object.assign({}, state.v.summary || {}, { progress: { done: n2, total: items.length } }) }, true);
        refreshRail("plan");
      });
    };
    render();
    const n0 = items.filter((x) => done[x.id]).length;
    if (!state.v.summary || !state.v.summary.progress || state.v.summary.progress.total !== items.length) {
      await save({ summary: Object.assign({}, state.v.summary || {}, { progress: { done: n0, total: items.length } }) }, true);
      refreshRail("plan");
    }
  }

  route();
})();
