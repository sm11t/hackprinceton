/* Venture Suite: "I have a budget" flow.
   My ventures -> budget -> scan -> opportunities -> shortlist -> investigate -> decide -> plan.
   Every number comes from /api/opportunities or /api/venture/review; this file only lays it out. */
(() => {
  "use strict";

  const USER = "demo";
  const STAGES = ["budget", "scan", "opportunities", "shortlist", "investigate", "decide", "plan"];
  const STAGE_NAMES = { budget: "Budget", scan: "Scan", opportunities: "Opportunities", shortlist: "Shortlist",
    investigate: "Investigate", decide: "Decide", plan: "Plan & track" };
  const STATUS_FOR = { budget: "exploring", scan: "exploring", opportunities: "exploring", shortlist: "shortlisted",
    investigate: "investigating", decide: "investigating", plan: "verifying" };
  const GROUPS = ["Sports & fitness", "Food & drink", "Health", "Personal services", "Children & education", "Retail",
    "Auto & storage"];
  const GROUP_ICON = { "Sports & fitness": "🏓", "Food & drink": "☕", Health: "✚", "Personal services": "✂",
    "Children & education": "▣", Retail: "🛍", "Auto & storage": "🔧" };
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
  const stageIdx = (s) => Math.max(0, STAGES.indexOf(s));
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
    return url ? `<img src="${url}" alt="${esc(ARCH_LABEL[a])}" title="${esc(ARCH_LABEL[a])}">` : `<span title="${esc(ARCH_LABEL[a])}">▦</span>`;
  }
  function propImg(group) {
    const url = thumb("prop:" + (GROUPS.includes(group) ? group : "other"), { size: 112 });
    return url ? `<img src="${url}" alt="">` : `<span>${GROUP_ICON[group] || "◆"}</span>`;
  }
  function agentImg(name) {
    const url = thumb("agent:" + name, { size: 88 });
    return url ? `<img src="${url}" alt="">` : `<span class="fallback">${esc(name.slice(0, 2).toUpperCase())}</span>`;
  }

  // ---------- status semantics ----------
  const FIT = { fits: ["green", "Fits"], check: ["amber", "Fits if checks pass"], no: ["red", "Can't host"] };
  const AFFORD = { within: ["green", "Within budget"], stretch: ["amber", "Low case only"],
    rent_unknown: ["grey", "Rent not listed"], over: ["red", "Over budget"] };
  const DEMAND = { supported: ["green", "Neighborhood supports"], mixed: ["amber", "Mixed neighborhood"],
    weak: ["red", "Weak neighborhood"], unknown: ["grey", "Neighborhood unknown"] };
  const VERDICT_CLS = { GO: "go", CONDITIONAL: "conditional", "NO-GO": "no-go" };
  const VERDICT_CHIP = { GO: "green", CONDITIONAL: "amber", "NO-GO": "red" };
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
    const q = new URLSearchParams({ budget: i.budget, reserve: i.reserve, top: 20 });
    if (i.area && i.area.mode === "near" && i.area.lat) { q.set("lat", i.area.lat); q.set("lon", i.area.lon); q.set("radius", i.area.radius || 10); }
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
    if (!state.v.chosen || idx < 6) changes.status = STATUS_FOR[stage];
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
        const stage = STAGES.includes(parts[2]) ? parts[2] : state.v.stage || "budget";
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
    app.innerHTML = `<div class="loading"><span class="spinner"></span>Loading your ventures…</div>`;
    state.ventures = await api(`/api/ventures?user=${USER}`);
    const cards = state.ventures.map((v) => {
      const idx = stageIdx(v.stage);
      const dots = STAGES.map((s, k) => `<span class="${k < idx ? "done" : k === idx ? "now" : ""}"></span>`).join("");
      const prog = v.summary && v.summary.progress;
      const status = { exploring: "blue", shortlisted: "blue", investigating: "blue", verifying: "amber", ready: "green", paused: "grey", dropped: "red" }[v.status] || "grey";
      return `<a class="card clickable venture-card" href="#/v/${esc(v.id)}" style="color:inherit;text-decoration:none">
        <div class="kind">${esc(v.kind === "budget" ? "I have a budget" : v.kind)}</div>
        <h3>${esc(v.name)}</h3>
        <div class="summary">${esc((v.summary && v.summary.line) || summaryLine(v))}</div>
        ${prog && prog.total ? `<div><div class="venture-meta" style="margin-bottom:6px"><span>Checks answered</span><span class="num">${prog.done} / ${prog.total}</span></div><div class="check-bar"><i style="width:${Math.round(100 * prog.done / prog.total)}%"></i></div></div>` : ""}
        <div class="progress-dots" title="Stage ${idx + 1} of 7">${dots}</div>
        <div class="venture-meta"><span>${esc(STAGE_NAMES[v.stage] || v.stage)} · ${esc(ago(v.updated_at))}</span>${chip(status, v.status)}</div>
      </a>`;
    }).join("");
    app.innerHTML = `
      <div class="home-head">
        <div><div class="eyebrow">My ventures</div><h1>What are we opening?</h1>
          <p class="empty-hint">${state.ventures.length ? "Each venture is one saved workflow. Pick up where you left off." : "No ventures yet. Start one: it saves at every step."}</p></div>
        <a class="btn primary" href="#/new">+ New venture</a>
      </div>
      <div class="grid ventures">
        <a class="card clickable new-card" href="#/new" style="text-decoration:none"><div><div class="plus">+</div><div style="font-weight:600;margin-top:6px">New venture</div><div class="muted small">Start from a budget</div></div></a>
        ${cards}
      </div>`;
  }

  function renderNew() {
    app.innerHTML = `
      <div><a class="link-btn" href="#/">← My ventures</a></div>
      <div style="margin-top:14px"><div class="eyebrow">New venture</div><h1>What do you have?</h1>
        <p class="muted" style="margin-top:6px">We'll start from what you already know and check everything else.</p></div>
      <div class="grid chooser">
        <button class="card clickable choice" id="kind-budget" style="text-align:left">
          <div class="icon">💵</div><h3>I have a budget</h3>
          <p class="muted small">You know what you can put in, not what to open or where. We scan every listed Houston space against 26 kinds of business.</p>
          <span class="chip blue nodot" style="align-self:flex-start">Start here</span>
        </button>
        <div class="card choice soon" aria-disabled="true"><div class="icon">💡</div><h3>I have an idea</h3>
          <p class="muted small">You know the business. We find where it works.</p>${chip("grey nodot", "Coming soon")}</div>
        <div class="card choice soon" aria-disabled="true"><div class="icon">🏢</div><h3>I have a space</h3>
          <p class="muted small">You have a building. We find what it can become.</p>${chip("grey nodot", "Coming soon")}</div>
      </div>`;
    document.getElementById("kind-budget").onclick = async (ev) => {
      ev.currentTarget.disabled = true;
      try {
        const n = (await api(`/api/ventures?user=${USER}`)).length + 1;
        state.v = await post("/api/ventures", { user: USER, kind: "budget", name: `Budget venture ${n}` });
        state.reviews = {}; state.opp = null;
        location.hash = `#/v/${state.v.id}/budget`;
      } catch (e) { toast(e.message); ev.currentTarget.disabled = false; }
    };
  }

  // ---------- venture shell + rail ----------
  function lockIns(i) {
    const v = state.v, o = state.opp;
    const area = i.area && i.area.mode === "near" && i.area.place ? `within ${i.area.radius} mi of ${i.area.place}` : "anywhere in Houston";
    const reviewed = Object.values(state.reviews);
    return {
      budget: i.budget ? `<b>${kmoney(i.budget - i.reserve)}</b> to open with · ${esc(area)}` : "",
      scan: o ? `<b>${num(o.funnel.neighborhood_support)}</b> combinations pass every gate` : (i.reached >= 1 ? "Scanned" : ""),
      opportunities: (i.directionLabels || []).length ? esc(i.directionLabels.join(", ")) : "",
      shortlist: (v.shortlist || []).length ? `<b>${v.shortlist.length}</b> place${v.shortlist.length > 1 ? "s" : ""}` : "",
      investigate: reviewed.length ? reviewed.map((r) => `<b>${esc(r.verdict)}</b>`).join(" · ") : "",
      decide: v.chosen ? `${esc(v.chosen.label)} · ${esc(v.chosen.address.split(",")[0])}` : "",
      plan: v.summary && v.summary.progress && v.summary.progress.total ? `<b>${v.summary.progress.done} / ${v.summary.progress.total}</b> checks answered` : "",
    };
  }
  function rail(stage) {
    const i = inputs(), cur = stageIdx(stage), reached = Math.max(i.reached || 0, cur), lock = lockIns(i);
    const steps = STAGES.map((s, k) => {
      const cls = k === cur ? "now" : k <= reached ? "done" : "locked";
      return `<li class="step ${cls}"><button data-stage="${s}" ${k > reached ? "disabled" : ""} aria-current="${k === cur ? "step" : "false"}">
        <span class="dot">${k < cur || (k <= reached && k !== cur) ? "✓" : k + 1}</span><span class="label">${STAGE_NAMES[s]}</span></button>
        ${lock[s] && k !== cur ? `<div class="lock-in">${lock[s]}</div>` : ""}</li>`;
    }).join("");
    return `<aside class="rail">
      <div class="rail-title"><a class="link-btn" href="#/">← My ventures</a>
        <input id="vname" value="${esc(state.v.name)}" aria-label="Venture name" maxlength="80"></div>
      <ol class="steps">${steps}</ol>
      <div class="saved">${state.savedAt ? "Saved " + state.savedAt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "Saved"}</div>
    </aside>`;
  }
  async function renderVenture(stage) {
    app.innerHTML = `<div class="venture">${rail(stage)}<section id="stage"><div class="loading"><span class="spinner"></span>Loading…</div></section></div>`;
    app.querySelectorAll(".step button[data-stage]").forEach((b) => { b.onclick = () => { if (!b.disabled) goStage(b.dataset.stage); }; });
    const name = document.getElementById("vname");
    name.onchange = () => { const n = name.value.trim(); if (n) save({ name: n }); };
    const el = document.getElementById("stage");
    try {
      await ({ budget: stageBudget, scan: stageScan, opportunities: stageOpportunities, shortlist: stageShortlist,
        investigate: stageInvestigate, decide: stageDecide, plan: stagePlan })[stage](el);
    } catch (e) {
      el.innerHTML = `<div class="error">${esc(e.message)}</div>`;
    }
    if (state.v.stage !== stage) save({ stage }, true);
  }
  function refreshRail(stage) {
    const r = app.querySelector(".rail"); if (!r) return;
    const tmp = document.createElement("div"); tmp.innerHTML = rail(stage);
    r.replaceWith(tmp.firstElementChild);
    app.querySelectorAll(".step button[data-stage]").forEach((b) => { b.onclick = () => { if (!b.disabled) goStage(b.dataset.stage); }; });
    const name = document.getElementById("vname");
    name.onchange = () => { const n = name.value.trim(); if (n) save({ name: n }); };
  }
  const head = (n, title, lede, right) => `<div class="stage-head"><div><div class="eyebrow">Stage ${n} of 7 · ${STAGE_NAMES[STAGES[n - 1]]}</div>
    <h1>${title}</h1>${lede ? `<p class="lede">${lede}</p>` : ""}</div>${right ? `<div class="actions">${right}</div>` : ""}</div>`;

  // ---------- Stage 1: budget ----------
  async function stageBudget(el) {
    const i = inputs();
    const area = Object.assign({ mode: "anywhere", radius: 10 }, i.area || {});
    const ex = new Set(i.exclude || []);
    el.innerHTML = `${head(1, "What can you put in?", "Your total cash and what you want to keep in reserve. We'll find what that can open, and where.")}
      <div class="budget-layout">
        <div class="panel">
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
          <div class="field"><span class="label">Where</span>
            <div class="seg" id="area-mode"><button type="button" data-m="anywhere" class="${area.mode !== "near" ? "on" : ""}">Anywhere in Houston</button><button type="button" data-m="near" class="${area.mode === "near" ? "on" : ""}">Near a place</button></div>
            <div id="near" class="${area.mode === "near" ? "" : "hidden"}" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px">
              <select class="select" id="place" aria-label="Place">${PLACES.map(([n]) => `<option ${n === area.place ? "selected" : ""}>${esc(n)}</option>`).join("")}</select>
              <select class="select" id="radius" aria-label="Radius">${[3, 5, 10, 15, 25].map((r) => `<option value="${r}" ${+area.radius === r ? "selected" : ""}>within ${r} mi</option>`).join("")}</select>
            </div>
          </div>
          <div class="field" style="margin-bottom:0"><span class="label">Leave out (optional)</span>
            <div class="toggle-chips" id="exclude">${GROUPS.map((g) => `<button type="button" data-g="${esc(g)}" class="${ex.has(g) ? "on" : ""}">${esc(g)}</button>`).join("")}</div>
            <span class="hint">Tap a group you'd never run. Everything else is considered: 26 kinds of business.</span>
          </div>
        </div>
        <div class="panel open-with">
          <div class="eyebrow">You can open with</div>
          <div class="big" id="open-with">${kmoney(i.budget - i.reserve)}</div>
          <div class="eq" id="open-eq">${money(i.budget)} cash − ${money(i.reserve)} reserve</div>
          <div class="note">Opening costs come from sourced franchise disclosure benchmarks, scaled to each space, plus the deposit and rent while you build. No revenue forecast: we show how many months of rent you'd have left.</div>
          <button class="btn primary" id="go-scan" style="justify-content:center">Scan Houston →</button>
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
    const persist = () => { clearTimeout(t); t = setTimeout(() => { const s = sync(); if (!s.bad) setInputs({ budget: s.b, reserve: s.r }, true); }, 500); };
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
    el.querySelector("#go-scan").onclick = async () => {
      const s = sync(); if (s.bad) return;
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

  // ---------- Stage 2: scan ----------
  async function stageScan(el) {
    const i = inputs();
    const agents = ["site", "building", "money", "residents", "competitors", "momentum", "lookalike", "coordinator"];
    el.innerHTML = `${head(2, "Our agents check every combination", `Every listed Houston space against every business, with ${kmoney(i.budget - i.reserve)} to open with. Three gates, in order: can the building host it, can you afford it, does the neighborhood support it.`,
      `<button class="btn ghost small" id="skip">Skip animation</button>`)}
      <div class="scan">
        <div class="panel"><div class="funnel" id="funnel"><div class="loading"><span class="spinner"></span>Scanning…</div></div></div>
        <div class="panel"><h3 style="margin-bottom:12px">The agents</h3><div class="agents">${agents.map((a) => `<div class="agent" data-a="${a}">${agentImg(a)}<div class="name">${a[0].toUpperCase() + a.slice(1)}</div><div class="job">${esc(AGENT_JOBS[a])}</div></div>`).join("")}</div>
          <p class="muted small" style="margin-top:12px">Every number and gate is computed in code. No AI decides who passes.</p></div>
      </div>
      <div class="sticky-bar hidden" id="next-bar"><span id="next-note" class="muted small"></span><button class="btn primary" id="next">See what ${kmoney(i.budget - i.reserve)} can become →</button></div>`;
    let o;
    try { o = await opportunities(); } catch (e) { el.querySelector("#funnel").innerHTML = `<div class="error">${esc(e.message)}</div>`; return; }
    const f = o.funnel;
    const rows = [
      [f.spaces, "Listed Houston spaces", "CoStar listings with a space you can lease", "CoStar", ["site"]],
      [f.combinations, "Business × space combinations", `${num(f.spaces)} spaces × ${o.businesses_considered} businesses`, "26-business registry", ["site"]],
      [f.building_can_host, "The building can host it", "Property type, floor, size and ceiling vs each business's needs", "CoStar", ["building"]],
      [f.affordable, `Cash to open + reserve fits ${kmoney(i.budget)}`, "Sourced opening-cost benchmarks scaled to the space, plus deposit and rent while building", "FDD benchmark", ["money"]],
      [f.neighborhood_support, "The neighborhood supports it", "Residents, competitors, who's moving in, lookalike areas", "ACS · OSM · CoStar", ["residents", "competitors", "momentum", "lookalike", "coordinator"]],
    ];
    const max = Math.sqrt(f.combinations);
    el.querySelector("#funnel").innerHTML = rows.map(([n, title, what, s], k) => `
      <div class="funnel-row" data-k="${k}"><div class="top"><span><span style="font-weight:600">${esc(title)}</span>${src(s)}</span><b data-n="${n}">0</b></div>
        <div class="bar"><i data-w="${Math.max(2, 100 * Math.sqrt(n) / max)}"></i></div><div class="what">${esc(what)}</div></div>`).join("") +
      `<div class="funnel-foot">${f.rent_not_listed ? chip("grey", `${num(f.rent_not_listed)} with no listed rent: judged on cost before rent`) : ""}
        ${f.cost_not_estimated ? chip("grey", `${num(f.cost_not_estimated)} pass but cost not estimated`, "No comparable opening-cost benchmark (e.g. car wash)") : ""}
        <span class="muted small">Bar length on a square-root scale. Answered in ${o.elapsed_ms} ms.</span></div>`;
    const count = (b, n) => {
      const t0 = performance.now();
      const tick = () => { const p = Math.min(1, (performance.now() - t0) / 550); b.textContent = num(n * (1 - Math.pow(1 - p, 3))); if (p < 1 && b.isConnected) requestAnimationFrame(tick); };
      tick();
    };
    const light = (k, instant) => {
      const row = el.querySelector(`.funnel-row[data-k="${k}"]`); if (!row || row.classList.contains("lit")) return;
      row.classList.add("lit");
      const bar = row.querySelector("i"); bar.style.width = bar.dataset.w + "%";
      const b = row.querySelector("b[data-n]");
      if (instant) b.textContent = num(+b.dataset.n); else count(b, +b.dataset.n);
      el.querySelectorAll(".agent").forEach((a) => a.classList.remove("on"));
      rows[k][4].forEach((a) => { const x = el.querySelector(`.agent[data-a="${a}"]`); if (x) x.classList.add("on", "done"); });
    };
    const finish = () => {
      clearTimers(); rows.forEach((_, k) => light(k, true));
      el.querySelectorAll(".agent").forEach((a) => a.classList.add("done"));
      el.querySelector("#next-bar").classList.remove("hidden");
      el.querySelector("#next-note").innerHTML = `<b class="num">${num(f.neighborhood_support)}</b> combinations pass every gate, across <b class="num">${o.directions.length}</b> kinds of business.`;
      el.querySelector("#skip").classList.add("hidden");
      refreshRail("scan");
    };
    rows.forEach((_, k) => later(() => light(k), 250 + k * 600));
    later(finish, 250 + rows.length * 600 + 300);
    el.querySelector("#skip").onclick = finish;
    el.querySelector("#next").onclick = () => goStage("opportunities");
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
        <div class="headline">${d.places} <small>place${d.places > 1 ? "s" : ""} pass every gate</small></div>
        <div class="chips">${d.supported ? chip("green", `${d.supported} neighborhood-supported`) : chip("amber", "Mixed neighborhoods, net positive")}
          ${d.within_budget ? chip("green", `${d.within_budget} within budget`) : ""}${d.only_low_case ? chip("amber", `${d.only_low_case} low case only`) : ""}${d.rent_not_listed ? chip("grey", `${d.rent_not_listed} rent not listed`) : ""}</div>
        <div class="range">Cash to open <span class="num">${kmoney(d.cash_to_open_range[0])}–${kmoney(d.cash_to_open_range[1])}</span>${src(costSrc(d.cost_basis))} ${basis}</div>
        <div class="why">${esc(d.why)}${src(demandSrc(d.business))}</div>
        <details onclick="event.stopPropagation()"><summary class="link-btn">Best places (${d.pairs.length})</summary><ul class="plain" style="margin-top:8px;font-size:13px">${best}</ul></details>
      </div>`;
    }).join("");
    const cne = (o.cost_not_estimated || []).map((u) => `<div><b>${esc(u.label)}</b>: ${u.places} place${u.places > 1 ? "s" : ""} pass the building and neighborhood gates. ${esc(u.why)} We don't guess a number.</div>`).join("");
    el.innerHTML = `${head(3, `Here's what ${kmoney(i.budget - i.reserve)} can become`, `${o.directions.length} kinds of business have at least one Houston space that fits, is affordable and has neighborhood support. Pick 1–3 directions to explore.`)}
      <div class="opps">
        <div>
          ${o.directions.length ? `<div class="grid directions">${cards}</div>` : `<div class="panel">Nothing passes every gate at this budget. Try more cash, a smaller reserve, or a wider area.</div>`}
          ${cne ? `<div class="panel not-estimated"><div class="eyebrow" style="color:#B4BCC6">Cost not estimated</div><div style="margin-top:8px;display:flex;flex-direction:column;gap:6px">${cne}</div></div>` : ""}
        </div>
        <div class="map-wrap"><div class="map" id="map"></div>
          <div class="map-legend"><span>● best spaces for each direction</span><span>rings ≈ I-610 and Beltway 8</span><span>drag to rotate · tap a pin</span></div></div>
      </div>
      <div class="sticky-bar"><span class="muted" id="pick-note"></span><button class="btn primary" id="next">Pick where →</button></div>`;
    const pairs = directionPairs(o).filter((p) => o.directions.some((d) => d.business === p.business));
    const pinsFor = () => pairs.map((p) => ({ id: pairKey(p), lat: p.lat, lon: p.lon, label: `${p.label} · ${p.address}`,
      color: !picked.length || picked.includes(p.business) ? "#00B0E6" : "#2B4A6F" }));
    const map = mapInto(el.querySelector("#map"), pinsFor(), (id) => {
      const b = id.split("|")[0], card = el.querySelector(`.direction[data-b="${CSS.escape(b)}"]`);
      if (card) { card.scrollIntoView({ behavior: "smooth", block: "center" }); card.animate([{ boxShadow: "0 0 0 2px #00B0E6" }, { boxShadow: "none" }], { duration: 1200 }); }
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
    if (!keys.length) { el.innerHTML = `${head(4, "Pick where", "")}<div class="panel">Pick at least one direction first. <button class="link-btn" id="back">← Opportunities</button></div>`; el.querySelector("#back").onclick = () => goStage("opportunities"); return; }
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
        <div class="cash"><div>Cash to open${src(costSrc(p.cost.basis_quality))}</div><b>${kmoney(p.cost.cash_to_open.base)}</b>
          <div>${kmoney(p.cost.cash_to_open.low)}–${kmoney(p.cost.cash_to_open.high)}</div>
          ${runway != null ? `<div title="Months of rent your remaining cash would cover with zero revenue">${runway} mo of rent left after opening</div>` : ""}</div>
      </div>`;
    }).join("");
    el.innerHTML = `${head(4, "Pick where", "The best spaces for your directions, ranked: neighborhood support first, then cash. Four gates on each. Pick up to 3 to investigate.")}
      <div class="filter-row"><div class="seg" id="filter"><button data-f="all" class="${filter === "all" ? "on" : ""}">All (${pairs.length})</button>${keys.map((k) => { const d = o.directions.find((x) => x.business === k); return `<button data-f="${esc(k)}" class="${filter === k ? "on" : ""}">${esc(d.label)} (${pairs.filter((p) => p.business === k).length})</button>`; }).join("")}</div></div>
      <div class="pairs">${rows || `<div class="panel">No ranked spaces for this direction.</div>`}</div>
      <div class="sticky-bar"><span class="muted" id="pick-note"></span><button class="btn primary" id="next">Investigate →</button></div>`;
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
    const cls = VERDICT_CLS[r.verdict] || "conditional";
    const flips = r.flips && r.flips.length ? r.flips : [];
    return `<div class="panel verdict-card">
      <div class="stamp ${cls}">${esc(r.verdict)}</div>
      <div class="verdict-body"><div class="eyebrow">${esc(r.label)} · ${esc(p.suite_label || r.suite || "")}</div>
        <h2>${esc(r.address)}</h2>
        <ul>${(r.blockers || []).map((b) => `<li style="color:#F3B4B0">${esc(tidy(b))}</li>`).join("")}${(r.blockers || []).length ? "" : (r.reasons || []).slice(0, 3).map((x) => `<li>${esc(tidy(x))}</li>`).join("")}</ul>
        ${flips.length ? `<div class="flip"><b>What would flip it:</b> ${flips.map(esc).join(" · ")}</div>` : r.verdict === "GO" ? `<div class="flip"><b>What would flip it:</b> nothing flagged. The checks below still need answers before you sign.</div>` : ""}
        <div class="actions" style="margin-top:12px"><span class="muted small">${esc(r.computed_by)}</span>
          <button class="link-btn" data-explain="1">AI summary</button></div>
        <div class="narr"></div>
      </div></div>`;
  }
  function pillarsHtml(r, p) {
    const P = r.pillars, m = P.money, sp = P.space, d = P.demand, i = inputs();
    const ind = (state.industries || []).find((x) => x.key === r.business) || {};
    const fit = look(FIT, sp.status), aff = look(AFFORD, m.affordability), dem = look(DEMAND, d.verdict);
    const recs = P.records || [], permits = P.permits || [];
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
            <div class="stat"><div class="k">Needed incl. ${kmoney(r.reserve)} reserve (base)</div><div class="v">${kmoney(req.base)}</div><div class="k">${kmoney(req.low)}–${kmoney(req.high)}</div></div>
            <div class="stat"><div class="k">Left of your ${kmoney(i.budget)} (base)</div><div class="v ${left < 0 ? "red" : "green"}">${left < 0 ? "−" : ""}${kmoney(Math.abs(left))}</div></div>
            <div class="stat"><div class="k">Months of rent left after opening, zero revenue</div><div class="v ${m.months_of_rent_after_opening == null ? "" : m.months_of_rent_after_opening < 6 ? "red" : m.months_of_rent_after_opening < 12 ? "amber" : "green"}">${m.months_of_rent_after_opening ?? "—"}</div></div>
            ${dw.required ? `<div class="stat"><div class="k">If opening slips 3 months (base)</div><div class="v ${dw.affordability === "within" ? "green" : dw.affordability === "stretch" ? "amber" : "red"}">${kmoney(dw.required.base)}</div><div class="k">${esc(look(AFFORD, dw.affordability)[1])} · ${dw.months_of_rent_after_opening ?? "—"} mo left</div></div>` : ""}
          </div>
          <table class="ledger"><thead><tr><th>What you pay before opening</th><th>Low</th><th>Base</th><th>High</th></tr></thead>
            <tbody>${ledger}<tr class="total"><td>Cash to open</td><td>${money(m.cash_to_open.low)}</td><td>${money(m.cash_to_open.base)}</td><td>${money(m.cash_to_open.high)}</td></tr></tbody></table>
          ${m.excludes ? `<div>${chip("amber", "Excludes " + m.excludes)}</div>` : ""}${m.note ? `<div class="muted small">${esc(m.note)}</div>` : ""}
          ${dw.franchise_fee_excluded ? `<div class="muted small">Franchise fee left out (independent operator): ${kmoney(dw.franchise_fee_excluded[0])}–${kmoney(dw.franchise_fee_excluded[1])} if you franchise.</div>` : ""}
          <details><summary class="link-btn">ⓘ Where these numbers come from (${(m.sources || []).length})</summary>
            <div class="sources" style="margin-top:8px">${(m.sources || []).map((s) => `<div class="source"><b>${esc(s.publisher_or_brand)}</b>, ${esc(s.document)} · <a href="${esc(s.url)}" target="_blank" rel="noopener">source ↗</a><q>${esc(s.quote)}</q></div>`).join("")}
            <div class="muted small">Franchise disclosure document (Item 7) ranges, scaled to this space's size, plus the listing's 2-month deposit and rent while building. No revenue forecast.</div></div></details>
        </div></details>
      <details class="pillar" data-p="deal"><summary><span class="ptitle">Deal</span>${rent.monthly != null ? chip("green", "Rent listed") : chip("grey", "Rent not listed")}<span class="pline">${rent.monthly != null ? `${money(rent.monthly)}/month · $${rent.psf_year}/sq ft/yr` : "Ask the broker for the rent"}</span></summary>
        <div class="pillar-body"><ul class="plain">
          ${li(rent.monthly != null ? "green" : "grey", rent.monthly != null ? "✓" : "?", rent.monthly != null ? `Asking ${money(rent.monthly)}/month ($${rent.psf_year}/sq ft/yr)${src(rentSrc(rent))} <span class="muted">${esc(rent.source || "")}</span>` : "No asking rent listed: the broker has to quote it")}
          ${li(r.space.lease_basis && !/determined/i.test(r.space.lease_basis) ? "green" : "grey", r.space.lease_basis && !/determined/i.test(r.space.lease_basis) ? "✓" : "?", `Lease basis: ${esc(r.space.lease_basis || "unknown")}`)}
          ${li(r.space.available_on ? "green" : "grey", r.space.available_on ? "✓" : "?", `Available: ${esc(r.space.available_on || "date not listed")}`)}
          ${r.space.lease_pending ? li("amber", "!", "A lease is pending on this space") : ""}
        </ul></div></details>
      <details class="pillar" data-p="records"><summary><span class="ptitle">Records</span>${conflicts.length ? chip("amber", `${conflicts.length} to check`) : recs.length ? chip("grey", `${recs.length} unconfirmed`) : chip("green", "No conflicts")}<span class="pline">${recs.length ? esc(recs[0].note.split(".")[0]) : "CoStar's record and the linked scans agree on what we could check"}</span></summary>
        <div class="pillar-body"><ul class="plain">${recs.length ? recs.map((x) => li(x.status === "unknown" ? "grey" : "amber", x.status === "unknown" ? "?" : "!", `<b>${esc(x.fact.replace(/_/g, " "))}</b>: ${esc(Array.isArray(x.value) ? x.value.join(", ") : typeof x.value === "object" ? JSON.stringify(x.value) : x.value)}<br><span class="muted small">${esc(x.note)}</span>${x.evidence_url ? ` <a href="${esc(x.evidence_url)}" target="_blank" rel="noopener">open ↗</a>` : ""}${src(x.source)}`)).join("") : li("green", "✓", "No disagreements between CoStar and the linked tours")}</ul></div></details>
      <details class="pillar" data-p="permits"><summary><span class="ptitle">Permits</span>${chip("amber", `${permits.length} to verify`)}<span class="pline">City change-of-use path + business licenses. None counted as cleared.</span></summary>
        <div class="pillar-body"><ul class="plain permits">${permits.map((x) => `<li><span class="mk amber">!</span><span><b>${esc(x.title)}</b> · <span class="muted">${esc(x.authority)}</span><br><span class="small">${esc(x.detail)}</span></span>${x.url ? `<a class="small" href="${esc(x.url)}" target="_blank" rel="noopener">official page ↗</a>` : ""}</li>`).join("")}</ul>
          <div class="muted small">Assumes City of Houston rules. Some "Houston" addresses are in unincorporated Harris County; confirm the jurisdiction for this pin. No timelines are claimed.</div></div></details>
      <details class="pillar" data-p="neighborhood"><summary><span class="ptitle">Neighborhood</span>${chip(dem[0], dem[1])}<span class="pline">${esc(d.headline || "")}</span></summary>
        <div class="pillar-body">${d.insight ? `<div><b>${esc(d.insight)}</b></div>` : ""}
          <ul class="plain">${(d.reasons || []).map((x) => { const [c, mk] = stanceMark(x.stance); return li(c, mk, `${esc(x.reason)} <span class="muted small">(${esc(x.signal)})</span>`); }).join("")}${(d.unknown || []).map((x) => li("grey", "?", esc(typeof x === "string" ? x : x.reason || JSON.stringify(x)))).join("")}</ul>
          <div class="muted small">Sources${src(demandSrc(r.business))}. ${ind.lookalike_auc ? `Lookalike accuracy for ${esc(ind.label)}: AUC ${ind.lookalike_auc} on held-out areas (0.5 = chance)${ind.validated ? "" : ", too weak to vote"}. Mostly an income signal; it finds gaps, not winners.` : "The lookalike score is not validated for this business."}</div></div></details>
    </div>`;
  }
  function mission(r) {
    return `<div class="mission">${(r.trace || []).map((t, k) => `<div class="mstep" data-k="${k}" title="${esc(t.role)}">${agentImg(t.agent)}<div><div class="n">${esc(t.agent)}</div><div class="s">${esc(t.summary || "")}</div></div></div>`).join("")}</div>
      <div class="trace-detail" id="trace-detail"></div>`;
  }
  async function stageInvestigate(el) {
    const list = state.v.shortlist || [];
    if (!list.length) { el.innerHTML = `${head(5, "Investigate", "")}<div class="panel">Shortlist at least one place first.</div>`; return; }
    const keys = list.map(pairKey);
    if (!keys.includes(state.tab)) state.tab = keys[0];
    await industries();
    const tabs = () => list.map((p) => { const k = pairKey(p), r = state.reviews[k]; return `<button data-k="${esc(k)}" class="${k === state.tab ? "on" : ""}">${r ? chip(VERDICT_CHIP[r.verdict] || "grey", r.verdict) : state.reviewErr[k] ? chip("red", "error") : `<span class="spinner" style="width:12px;height:12px"></span>`}${esc(p.label)} · ${esc(p.address.split(",")[0])}</button>`; }).join("");
    el.innerHTML = `${head(5, "Investigate", "Thirteen agents review each place: the space, the money, the deal, the records, the permits and the neighborhood. Verdict first; open any section for the evidence.")}
      <div class="tabs" id="tabs">${tabs()}</div><div id="review"></div>
      <div class="sticky-bar"><span class="muted" id="rev-note"></span><button class="btn primary" id="next">Compare and decide →</button></div>`;
    const bindTabs = () => el.querySelectorAll("#tabs button").forEach((b) => b.onclick = () => { state.tab = b.dataset.k; el.querySelector("#tabs").innerHTML = tabs(); bindTabs(); show(true); });
    bindTabs();
    const note = () => { const n = Object.keys(state.reviews).filter((k) => keys.includes(k)).length; el.querySelector("#rev-note").innerHTML = `<b class="num">${n}</b> of ${keys.length} reviewed`; el.querySelector("#next").disabled = !n; };
    const show = (animate) => {
      clearTimers();
      const box = el.querySelector("#review"), k = state.tab, p = list.find((x) => pairKey(x) === k), r = state.reviews[k];
      if (state.reviewErr[k]) { box.innerHTML = `<div class="error">${esc(state.reviewErr[k])}</div>`; return; }
      if (!r) { box.innerHTML = `<div class="loading"><span class="spinner"></span>Agents are reviewing ${esc(p.label)} at ${esc(p.address)}…</div>`; return; }
      box.innerHTML = `${mission(r)}<div id="vc" style="opacity:0;transition:opacity .4s">${verdictCard(r, p)}${pillarsHtml(r, p)}</div>`;
      const steps = [...box.querySelectorAll(".mstep")];
      const reveal = () => { const vc = box.querySelector("#vc"); if (vc) vc.style.opacity = 1; };
      if (animate) { steps.forEach((s, j) => later(() => s.classList.add("lit"), 80 + j * 110)); later(reveal, 80 + steps.length * 110); }
      else { steps.forEach((s) => s.classList.add("lit")); reveal(); }
      steps.forEach((s) => s.onclick = () => {
        const t = r.trace[+s.dataset.k], det = box.querySelector("#trace-detail");
        const open = s.classList.contains("active");
        steps.forEach((x) => x.classList.remove("active"));
        if (open) { det.innerHTML = ""; return; }
        s.classList.add("active");
        det.innerHTML = `<div class="panel"><b style="text-transform:capitalize">${esc(t.agent)}</b> · <span class="muted">${esc(t.role)}</span>
          <div style="margin-top:6px">${esc(t.summary || "")}</div>
          <div class="muted small" style="margin-top:6px">Computed by ${esc(t.computed_by)}${t.confidence != null ? ` · confidence ${t.confidence}` : ""}${t.ms != null ? ` · ${t.ms} ms` : ""} · hands off: ${esc(t.handoff || "")}</div>
          ${(t.findings || []).length ? `<details><summary class="link-btn">Findings (${t.findings.length})</summary><pre>${esc(JSON.stringify(t.findings, null, 1).slice(0, 4000))}</pre></details>` : ""}</div>`;
      });
      const space = box.querySelector(".space3d");
      box.querySelector('details[data-p="space"]').addEventListener("toggle", function onT(ev) {
        if (!ev.target.open || space.dataset.drawn) return;
        space.dataset.drawn = 1;
        if (has3d()) { try { const c = window.Suite3D.space(space, { sf: +space.dataset.sf, ceiling_ft: +space.dataset.ceiling || null, business: r.business, label: r.label }); if (c) state.ctrls.push(c); } catch { /* 2D text stays */ } }
      });
      box.querySelector("[data-explain]").onclick = async (ev) => {
        const b = ev.currentTarget, out = box.querySelector(".narr"); b.disabled = true;
        out.innerHTML = `<div class="loading" style="padding:8px 0"><span class="spinner"></span>Writing a plain-English summary…</div>`;
        try {
          const x = await review(p, true);
          out.innerHTML = x.narration ? `<div class="narration"><span class="ai-label">✦ ${esc(x.narration_label || "AI-written, numbers checked")}</span><div>${esc(x.narration)}</div></div>` : `<div class="muted small">No AI summary available (no LLM key on this server). The verdict above is computed in code.</div>`;
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
  async function stageDecide(el) {
    const list = state.v.shortlist || [];
    el.innerHTML = `<div class="loading"><span class="spinner"></span>Gathering verdicts…</div>`;
    for (const p of list) { const k = pairKey(p); if (!state.reviews[k]) { try { state.reviews[k] = await review(p); } catch (e) { state.reviewErr[k] = e.message; } } }
    const order = { GO: 0, CONDITIONAL: 1, "NO-GO": 2 };
    const rows = list.map((p) => ({ p, r: state.reviews[pairKey(p)] })).filter((x) => x.r).sort((a, b) => (order[a.r.verdict] ?? 3) - (order[b.r.verdict] ?? 3));
    const ch = state.v.chosen ? pairKey(state.v.chosen) : null, budget = inputs().budget;
    el.innerHTML = `${head(6, "Decide", "Side by side. The deciding reason and what would flip each one. Commit to one and we'll turn its open checks into a plan.")}
      <div class="compare">${rows.map(({ p, r }) => {
        const m = r.pillars.money, k = pairKey(p);
        return `<div class="card col ${k === ch ? "chosen" : ""}">
          <div class="eyebrow">${esc(r.label)}</div><h3>${esc(r.address.split(",")[0])} · ${esc(p.suite_label)}</h3>
          <div class="stamp small ${VERDICT_CLS[r.verdict]}">${esc(r.verdict)}</div>
          <div class="row"><div class="k">Deciding reason</div>${esc(tidy((r.blockers || [])[0] || (r.conditions || [])[0] || (r.reasons || [])[0] || ""))}</div>
          <div class="row"><div class="k">What would flip it</div>${esc(tidy((r.flips || [])[0]) || (r.verdict === "GO" ? "Nothing flagged; checks still apply" : "—"))}</div>
          <div class="row"><div class="k">Needed incl. reserve (base) vs ${kmoney(budget)}${src(costSrc(m.basis_quality))}</div><span class="num">${kmoney(m.required.base)}</span> · ${m.months_of_rent_after_opening ?? "—"} months of rent left</div>
          <div class="row"><div class="k">Neighborhood${src(demandSrc(r.business))}</div>${esc(look(DEMAND, r.pillars.demand.verdict)[1])}</div>
          <div class="row"><div class="k">Open checks</div>${(r.checks || []).length + (r.pillars.permits || []).length}</div>
          <button class="btn ${k === ch ? "" : "primary"}" data-k="${esc(k)}" style="align-self:stretch;justify-content:center">${k === ch ? "✓ Committed" : "Commit to this one"}</button>
        </div>`;
      }).join("") || `<div class="panel">No reviews yet.</div>`}</div>`;
    el.querySelectorAll("button[data-k]").forEach((b) => b.onclick = async () => {
      const p = list.find((x) => pairKey(x) === b.dataset.k), r = state.reviews[b.dataset.k];
      if (r.verdict === "NO-GO" && !confirm("This one is NO-GO. Commit anyway and plan around the blocker?")) return;
      await save({ chosen: Object.assign({}, p, { verdict: r.verdict }), status: "verifying", checklist: {} });
      goStage("plan");
    });
  }

  // ---------- Stage 7: plan & track ----------
  const WHO = [
    ["broker", "Broker", "📇", /records disagree|caption|scan|survey|size field|asking|rent|lease basis|available|pending|suite/i],
    ["landlord", "Landlord", "🔑", /landlord|tenant-improvement|build-out|outdoor|fenced|plumb|ventilat|hvac|electric|power|ceiling|parking|loading|deed|grease|hood|drain|floor|consent|signage/i],
    ["inspector", "Inspector", "🦺", /inspect|fire|accessib|occupancy|final|sprinkler|exit/i],
    ["city", "City & state", "🏛", /permit|license|certificate|registration|tax|city|county|state|health|tabc|tdlr|hhsc/i],
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
    if (!c) { el.innerHTML = `${head(7, "Plan & track", "")}<div class="panel">Commit to one place in Decide first.</div>`; return; }
    el.innerHTML = `<div class="loading"><span class="spinner"></span>Building your plan…</div>`;
    const k = pairKey(c);
    if (!state.reviews[k]) state.reviews[k] = await review(c);
    const r = state.reviews[k], items = planItems(r), done = Object.assign({}, state.v.checklist || {});
    const groups = [["you", "You", "🧭"]].concat(WHO.map(([id, name, icon]) => [id, name, icon]))
      .map(([id, name, icon]) => ({ id, name, icon, items: items.filter((x) => x.who === id) })).filter((g) => g.items.length);
    const render = () => {
      const n = items.filter((x) => done[x.id]).length;
      el.innerHTML = `${head(7, "Plan & track", `Every open question for <b>${esc(c.label)}</b> at ${esc(c.address)}, grouped by who can answer it. Tick them off as answers come in; progress shows on your venture card.`)}
        <div class="panel plan-progress"><div class="stamp small ${VERDICT_CLS[r.verdict]}" style="width:84px;height:84px;font-size:13px">${esc(r.verdict)}</div>
          <div style="flex:1"><div style="display:flex;justify-content:space-between;margin-bottom:8px"><b>${n} of ${items.length} answered</b><span class="muted small">${n === items.length ? "Ready to sign" : "Keep going"}</span></div><div class="check-bar"><i style="width:${items.length ? Math.round(100 * n / items.length) : 0}%"></i></div></div></div>
        <div class="grid who">${groups.map((g) => `<div class="panel"><h3><span>${g.icon}</span>${esc(g.name)}<span class="count">${g.items.filter((x) => done[x.id]).length} / ${g.items.length}</span></h3>
          ${g.items.map((x) => `<label class="check ${done[x.id] ? "done" : ""}"><input type="checkbox" data-id="${esc(x.id)}" ${done[x.id] ? "checked" : ""}><span>${x.blocker ? chip("red", "Blocks") + " " : ""}${esc(tidy(x.text))}${x.url ? ` <a href="${esc(x.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">↗</a>` : ""}</span></label>`).join("")}</div>`).join("")}</div>`;
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
