/* Venture Suite · Flow: the whole reasoning as one scroll.
   Stages follow the team's Helix map (0 intake, 1 discovery, 2 building preflight, 3 business options and
   use-specific compliance, 4 feasibility and decision, 5 report). Every number comes from the same APIs as /suite;
   this file only lays them out, in the order the agents worked, with each source beside its finding. */
(() => {
  "use strict";
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const money = (n) => (n == null || isNaN(n) ? "—" : (n < 0 ? "−$" : "$") + Math.round(Math.abs(n)).toLocaleString("en-US"));
  const kmoney = (n) => { if (n == null || isNaN(n)) return "—"; const a = Math.abs(n), s = n < 0 ? "−$" : "$"; return a >= 1e6 ? s + (a / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M" : s + Math.round(a / 1000).toLocaleString("en-US") + "k"; };
  const num = (n) => (n == null ? "—" : Math.round(n).toLocaleString("en-US"));
  const cap = (s) => String(s || "").charAt(0).toUpperCase() + String(s || "").slice(1);
  const day = (d) => (d ? String(d).slice(0, 10) : "");
  const tidy = (t) => { t = String(t ?? ""); return t.length > 240 ? t.slice(0, 236).replace(/\s+\S*$/, "") + "…" : t; };
  const chip = (cls, text, title) => `<span class="chip ${cls}"${title ? ` title="${esc(title)}"` : ""}>${esc(text)}</span>`;
  const STATIC = document.documentElement.classList.contains("static");
  const TOUCH = matchMedia("(hover: none)").matches;
  function srcChip(s) {
    if (!s || !(s.name || s.url)) return "";
    const meta = [day(s.retrieved_at), s.confidence != null ? `conf ${s.confidence}` : ""].filter(Boolean).join(" · ");
    const inner = `<span class="sn">${esc(s.name || "source")}</span>${meta ? `<span>${esc(meta)}</span>` : ""}`;
    return s.url ? `<a class="srcchip" href="${esc(s.url)}" target="_blank" rel="noopener">${inner} ↗</a>` : `<span class="srcchip">${inner}</span>`;
  }
  async function api(path) {
    const r = await fetch(path); let b; try { b = await r.json(); } catch { b = { error: `Server answered ${r.status}` }; }
    if (!r.ok || (b && b.error)) throw new Error(b.error || r.statusText); return b;
  }
  function toast(m) { const t = $("#toast"); t.textContent = m; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, 2600); }

  // ---------- what the user starts from (Jessenth's four archetypes) ----------
  const QS = new URLSearchParams(location.search);
  const PATHS = {
    budget: { label: "I have a budget", short: "Knows neither", chapters: ["cash", "scan", "directions", "shortlist", "investigate", "verdict", "decide", "plan"] },
    idea: { label: "I know what to open", short: "Knows the business", chapters: ["cash", "scan", "shortlist", "investigate", "verdict", "decide", "plan"] },
    space: { label: "I have a space", short: "Knows the place", chapters: ["cash", "site", "fits", "investigate", "verdict", "decide", "plan"] },
    both: { label: "I know what and where", short: "Knows both", chapters: ["cash", "site", "investigate", "verdict", "decide", "plan"] },
  };
  const DEMO = { idea: { business: "yoga_pilates" }, space: { place: 6017645 }, both: { business: "physical_therapy", place: 239634, suite: "625" } };
  const S = { kind: "budget", budget: 500000, reserve: 50000, nessie: null, opp: null, pre: null, picks: [], reviews: [], lead: 0, guide: null, industries: [], business: null, place: null, suite: null, map: null };

  const EFFECT = { blocks: ["red", "Blocks"], check: ["amber", "Needs a check"], supports: ["green", "Supports"], unknown: ["grey", "Unknown"] };
  const VLABEL = { GO: "Go", CONDITIONAL: "Conditional", "NO-GO": "No-go" };
  const GROUPS = [
    { id: "g-building", stage: "Helix stage 2 · Building preflight", title: "Is the building what it claims?", lede: "Where it is, what CoStar says it is, and whether the scans agree.", agents: ["planner", "site", "building", "records"] },
    { id: "g-hood", stage: "Helix stage 3 · Business options", title: "Does the neighborhood want it?", lede: "Four independent signals, each with a stated rule, then a coordinator that combines them.", agents: ["residents", "competitors", "momentum", "lookalike", "coordinator"] },
    { id: "g-legal", stage: "Helix stage 3 · Use-specific compliance", title: "Can it legally open here?", lede: "Who permits this pin, what this business needs, and what a person must still confirm. Nothing here is an approval.", agents: ["permits"] },
    { id: "g-money", stage: "Helix stage 4 · Feasibility", title: "What does it cost, and is the rent fair?", lede: "Sourced opening costs scaled to this space, the asking rent against signed deals, and a 3-month delay.", agents: ["money", "deal"] },
  ];
  const AGENT_Q = {
    planner: "What exactly are we checking?", site: "Where is it, exactly?", building: "Can this space host the business?",
    residents: "Who lives within 3 miles, and is that group growing?", competitors: "Who already serves it nearby?",
    momentum: "Are businesses like it moving in or out?", lookalike: "Does it look like places that already have it?",
    coordinator: "What do the four signals add up to?", money: "What does it cost to open here?", deal: "Is the asking rent fair?",
    records: "Do CoStar and the scans agree?", permits: "Who permits it, and what must be approved?",
  };

  // ---------- load ----------
  async function load() {
    const meta = $("#heroMeta");
    try {
      const [nessie, industries, guide] = await Promise.all([api("/api/nessie/account").catch(() => null), api("/api/neighborhood/industries").catch(() => []), api("/api/signal-guide").catch(() => null)]);
      Object.assign(S, { nessie, industries, guide });
      let v = null;
      if (QS.get("v")) { try { v = await api(`/api/ventures/${encodeURIComponent(QS.get("v"))}?user=demo`); } catch { v = null; } }
      S.kind = PATHS[QS.get("path")] ? QS.get("path") : v && PATHS[v.kind] ? v.kind : "budget";
      const vi = (v && v.inputs) || {}, d = DEMO[S.kind] || {};
      S.budget = +QS.get("budget") || vi.budget || (nessie && nessie.balance) || 500000;
      S.reserve = QS.get("reserve") != null ? +QS.get("reserve") : vi.reserve != null ? vi.reserve : 50000;
      S.business = QS.get("business") || vi.business || d.business || null;
      S.place = +QS.get("place") || (vi.place && vi.place.property_id) || d.place || null;
      S.suite = QS.get("suite") || vi.suite || d.suite || null;
      $("#navPath").textContent = PATHS[S.kind].label;
      meta.innerHTML = `<span class="spinner"></span> Scanning every listed space…`;
      const q = new URLSearchParams({ budget: S.budget, reserve: S.reserve, top: 20 });
      if (S.kind === "idea" && S.business) q.set("include", S.business);
      if (S.kind === "space" && S.place) q.set("property_id", S.place);
      if (S.kind !== "both") S.opp = await api("/api/opportunities?" + q);
      if (S.kind === "space" || S.kind === "both") S.pre = await api(`/api/site/preflight?property_id=${S.place}`);
      S.picks = pickPairs(v);
      meta.innerHTML = `<span class="spinner"></span> Thirteen agents are reviewing ${S.picks.length} place${S.picks.length === 1 ? "" : "s"}…`;
      S.reviews = await Promise.all(S.picks.map((p) => review(p).catch((e) => ({ error: e.message, label: p.label, address: p.address }))));
      const ok = S.reviews.map((r, i) => [r, i]).filter(([r]) => !r.error);
      S.lead = (ok.find(([r]) => r.verdict === "GO") || ok[0] || [null, 0])[1];
      render();
    } catch (e) {
      meta.innerHTML = `<div class="error">${esc(e.message)}</div>`;
    }
  }
  function pickPairs(v) {
    if (v && (v.shortlist || []).length) return v.shortlist.slice(0, 3);
    if (S.kind === "both") {
      const sp = ((S.pre && S.pre.spaces) || []).find((x) => x.value === S.suite) || ((S.pre && S.pre.spaces) || [])[0];
      const ind = S.industries.find((x) => x.key === S.business) || {};
      return S.pre && S.pre.can_continue && sp ? [{ business: S.business, label: ind.label || S.business, group: ind.group, property_id: S.place, suite: sp.value, suite_label: sp.label, address: S.pre.address }] : [];
    }
    if (S.kind === "space" && S.pre && !S.pre.can_continue) return [];
    const o = S.opp || { directions: [], pairs: [] };
    if (S.kind === "idea") return (o.directions[0] ? o.directions[0].pairs : o.pairs).slice(0, 3);
    return o.directions.slice(0, 3).map((d) => d.pairs[0]).filter(Boolean);
  }
  function review(p) {
    const q = new URLSearchParams({ business: p.business, property_id: p.property_id, suite: p.suite || "", budget: S.budget, reserve: S.reserve, delay: 3 });
    if (S.nessie && S.nessie.account_id) q.set("nessie", S.nessie.account_id);
    return api("/api/venture/review?" + q);
  }

  // ---------- chapters ----------
  const CH = {
    cash: { rail: "Your cash", stage: "Helix stage 0 · Intake", head: () => "Start with the money you have.", lede: () => "Your balance and recurring bills come from your bank. What you keep in reserve is never spent on opening.", tools: ["Capital One Nessie API (sandbox)", "Your reserve"] },
    scan: { rail: "Every lease", stage: "Helix stage 1 · Discovery", head: () => S.kind === "idea" ? `Where a ${esc(lbl(S.business).toLowerCase())} works.` : `${num(S.opp.funnel.combinations)} possible businesses.`, lede: () => S.kind === "idea" ? `Every listed Houston space, checked for one business through the same four gates.` : `Every listed Houston space against 26 kinds of business. Four gates in order. Most die on the building, the cash or the neighborhood.`, tools: ["CoStar kit: 2,370 listed spaces", "Building fit (space needs)", "FDD Item 7 cost benchmarks", "Neighborhood index", "Census jurisdiction"] },
    directions: { rail: "What it can become", stage: "Helix stage 1 · Discovery", head: () => `What ${kmoney(S.budget - S.reserve)} can become.`, lede: () => `${S.opp.directions.length} kinds of business have at least one space that fits, is affordable and has neighborhood support.`, tools: ["Cost ledger", "Neighborhood verdicts", "Lookalike accuracy (AUC)"] },
    shortlist: { rail: "Three places", stage: "Helix stage 1 · Selection", head: () => "Three places worth a closer look.", lede: () => "The best space for each direction. Pick one to follow through the agents; the others come back when you compare.", tools: ["Gate results per space"] },
    site: { rail: "Building check", stage: "Helix stage 2 · Building preflight", head: () => "Check the building before any business.", lede: () => "Who permits this address, from the pin's official boundary, and can it be used commercially at all.", tools: ["Jayant's compliance engine: preflight", "U.S. Census geocoder", "CoStar property record"] },
    fits: { rail: "What fits here", stage: "Helix stage 3 · Business options", head: () => `What ${esc((S.pre && S.pre.address) || "this space")} can become.`, lede: () => isLA() ? "Each of the 26 businesses is checked for fit and cash here. The neighborhood model is calibrated for Houston, so in Los Angeles demand stays unknown instead of borrowing Houston's thresholds." : "Each of the 26 businesses either passes every gate here or stops at one. Both are shown.", tools: ["Building fit", "Cost ledger", "Neighborhood index"] },
    investigate: { rail: "Investigate", stage: "Helix stages 2–4 · Investigation", head: () => { const r = lead(); return r ? `Thirteen agents examine ${esc(r.label.split(" / ")[0].toLowerCase())} at ${esc(r.address.split(",")[0])}.` : "Nothing to investigate."; }, lede: () => "Each agent answers one question in code, shows what it found and where it came from, and hands off to the next. The verdict stays hidden until the evidence is in.", tools: ["13 agents · computed in code", "Evidence records with sources", "LLM writes only the optional summary"] },
    verdict: { rail: "Verdict", stage: "Helix stage 4 · Decision", head: () => "What the evidence adds up to.", lede: () => "Every reason in one place, ranked by what decided it, then the call and what would change it.", tools: ["Verdict rule (code)", "because[] from the review"] },
    decide: { rail: "Decide", stage: "Helix stage 4 · Feasibility", head: () => "The next twelve months, with zero revenue.", lede: () => "Side by side, then month by month: which pick dips into your reserve, and when. Your bank's bills are included. If cash falls short, a Nessie loan shows what borrowing the gap would do.", tools: ["Jayant's Nessie-pilot simulator", "Nessie loan plan (sandbox)", "CoStar asking rent"] },
    plan: { rail: "Next checks", stage: "Helix stage 5 · Report", head: () => "What to verify before you sign.", lede: () => "Every open check, grouped by who can answer it, and every source this report touched.", tools: ["Plan grouped by who answers", "Source register"] },
  };
  const lbl = (key) => (S.industries.find((x) => x.key === key) || {}).label || key || "business";
  const lead = () => { const r = S.reviews[S.lead]; return r && !r.error ? r : null; };
  const isLA = () => (S.opp && S.opp.market === "los_angeles") || /Los Angeles/.test((S.pre && S.pre.address) || "") || S.reviews.some((r) => r && /Los Angeles/.test(r.address || ""));

  function render() {
    // A building that fails the preflight ends the flow there: no business is suggested for it.
    const chapters = S.pre && !S.pre.can_continue ? ["cash", "site"] : PATHS[S.kind].chapters;
    $("#heroMeta").innerHTML = heroMeta();
    if (isLA()) { $(".hero .eyebrow").textContent = "Venture Suite · Los Angeles"; $(".hero .display").innerHTML = "One budget.<br>One Los Angeles lease."; }
    $("#chapters").innerHTML = chapters.map((id, i) => `<section class="ch" id="ch-${id}" data-ch="${id}">
        <div class="ch-intro"><div class="fields" aria-hidden="true"><i class="f1"></i><i class="f2"></i><i class="f3"></i></div>
          <div class="ch-intro-inner"><p class="stage-no"><b>${String(i + 1).padStart(2, "0")}</b> / ${String(chapters.length).padStart(2, "0")} · ${esc(CH[id].stage)}</p>
            <h2 class="headline">${CH[id].head()}</h2><p class="lede">${CH[id].lede()}</p>
            <div class="ch-tools">${CH[id].tools.map((t) => `<span class="tool"><i></i>${esc(t)}</span>`).join("")}</div></div>
          <div class="dim"></div></div>
        <div class="ch-body"><div class="wrap" id="body-${id}">${BODY[id]()}</div></div></section>`).join("");
    $("#railList").innerHTML = chapters.map((id, i) => `<li data-ch="${id}"><a href="#ch-${id}"><span class="dot">${i + 1}</span><span class="lbl">${esc(CH[id].rail)}${id === "investigate" && lead() ? `<span class="sub">${esc(lead().label.split(" / ")[0])}</span>` : ""}</span></a>
      ${id === "investigate" ? `<ol class="agents">${GROUPS.map((g) => `<li data-g="${g.id}"><i></i>${esc(g.title.replace(/\?$/, ""))}</li>`).join("")}</ol>` : ""}</li>`).join("");
    if (!chapters.includes("verdict")) $("#navSkip").classList.add("hidden");
    bindAll();
  }
  function heroMeta() {
    const r = S.reviews.filter((x) => !x.error);
    return `${chip("blue", PATHS[S.kind].short)} ${S.nessie ? chip("blue", "Capital One Nessie · sandbox") : ""}${isLA() ? chip("amber", "Los Angeles: neighborhood model not calibrated, demand stays unknown") : ""}
      <span>${kmoney(S.budget)} cash · keep ${kmoney(S.reserve)}</span>${S.opp ? `<span>· ${num(S.opp.funnel.combinations)} combinations checked in ${S.opp.elapsed_ms} ms</span>` : ""}
      <span>· ${r.length} place${r.length === 1 ? "" : "s"} reviewed by 13 agents</span>`;
  }

  const BODY = {
    cash() {
      const n = S.nessie;
      const bank = n ? `<div class="bank glass reveal"><div><div class="who"><b>Capital One Nessie</b>${chip("blue", "sandbox · simulated bank data")}</div>
          <div class="muted small" style="margin-top:6px">${esc(n.nickname || "Checking")} · account …${esc(String(n.account_id).slice(-6))}</div>
          <div class="bal" style="margin-top:10px">${money(n.balance)}</div></div>
          <ul>${(n.bills || []).map((b) => `<li>↻ ${esc(b.payee)} <b class="num">${money(b.monthly)}</b>/mo</li>`).join("") || "<li>No recurring bills</li>"}</ul>
          <div class="meta">${esc(n.source)} · ${n.cached ? "cached (offline replay)" : "read"} ${esc(new Date(n.retrieved_at).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }))}. Not a live bank connection.</div></div>`
        : `<div class="error">Nessie unavailable: using the typed budget.</div>`;
      return `<div class="sec-head"><h3 class="title">Your bank says ${kmoney(S.budget)}.</h3></div>${bank}
        <div class="eq reveal"><div><div class="t">Cash</div><div class="n">${kmoney(S.budget)}</div></div><div class="op">−</div>
          <div><div class="t">Reserve, never spent</div><div class="n">${kmoney(S.reserve)}</div></div><div class="op">=</div>
          <div><div class="t">To open with</div><div class="n">${kmoney(S.budget - S.reserve)}</div></div></div>
        <div class="block reveal"><div class="sec-head"><h3 class="title">Start from what you know.</h3><span class="note">The same agents run in every case; only the order changes.</span></div>
          <div class="start glass">${startControls()}</div></div>`;
    },
    scan() {
      const f = S.opp.funnel, m = S.opp.map || { after_gate: [] };
      const one = S.opp.businesses_considered === 1;
      const g = (S.guide && S.guide.thresholds) || {};
      const steps = [
        { gate: 0, k: "Listed spaces", n: f.spaces, h: `${num(f.spaces)} spaces listed for lease in Houston`, p: "Every active lease listing in the CoStar kit, with its size, floor, rent and building type.", s: { name: "CoStar hackathon kit" } },
        { gate: 0, k: "Combinations", n: f.combinations, h: one ? `${num(f.combinations)} spaces to check for one business` : `× ${S.opp.businesses_considered} businesses = ${num(f.combinations)} possible futures`, p: "Each one is a “what if you opened this business in this space”. Nobody can check them by hand.", s: { name: "26-business registry" } },
        { gate: 1, k: "Gate 1 · Building", n: f.building_can_host, h: `${num(f.building_can_host)} spaces can physically host it`, p: "Building type, floor, size and ceiling against each business's space needs. Residential buildings stop here.", s: { name: "CoStar property facts" } },
        { gate: 2, k: "Gate 2 · Cash", n: f.affordable, h: `${num(f.affordable)} are affordable with ${kmoney(S.budget)}`, p: `Sourced cash to open (FDD Item 7, scaled to the space) + a ${g.deposit_months || 2}-month deposit + rent while building + your reserve must fit the budget.`, s: { name: "FDD Item 7 benchmarks" } },
        { gate: 3, k: "Gate 3 · Neighborhood", n: f.neighborhood_support, h: `${num(f.neighborhood_support)} have neighborhood support`, p: `Residents, competitors, business arrivals and a lookalike model (votes only if its held-out AUC ≥ ${g.validated_auc || 0.6}).`, s: { name: "ACS · OSM · CoStar tenancies" } },
        { gate: 4, k: "Gate 4 · Compliance preflight", n: f.authority_identified ?? f.neighborhood_support, h: `${num(f.authority_identified ?? f.neighborhood_support)} with a known permitting authority`, p: `From the pin's Census boundary, not the postal city: ${num((f.compliance || {}).houston)} City of Houston, ${num((f.compliance || {}).harris_unincorporated)} unincorporated Harris County${(f.compliance || {}).other_city ? `, ${num(f.compliance.other_city)} inside another city (flagged, not dropped)` : ""}.`, s: { name: "Census geocoder · Jayant's compliance engine" } },
      ];
      return `<div class="split"><div class="graphic"><div class="map" id="scanMap"></div>
          <div class="map-cap"><span id="mapCount"><b>${num(m.after_gate[0])}</b> buildings with listed space</span><span>Green: passes every gate · amber: authority not identified</span></div>
          <div class="gate-bars glass" style="padding:14px">${steps.slice(1).map((s, i) => `<div class="gate-bar" data-bar="${i + 1}"><span>${esc(s.k)}</span><span class="t"><i data-w="${Math.max(1, 100 * Math.sqrt(s.n) / Math.sqrt(f.combinations))}"></i></span><b>${num(s.n)}</b></div>`).join("")}</div></div>
        <div class="steps">${steps.map((s, i) => `<div class="step glass" data-step="scan" data-gate="${s.gate}" data-bar="${i}"><div class="k">${esc(s.k)}</div><div class="big">${num(s.n)}</div><h3>${esc(s.h)}</h3><p>${esc(s.p)}</p><div style="margin-top:10px">${srcChip(s.s)}</div></div>`).join("")}
          <div class="step glass" data-step="scan" data-gate="4" data-bar="5"><div class="k">Answered in ${S.opp.elapsed_ms} ms</div><h3>Every gate is computed in code.</h3><p>No model decides who passes. ${f.rent_not_listed ? `${num(f.rent_not_listed)} listings have no asking rent, so they're judged on cost before rent and labelled.` : ""}</p></div></div></div>`;
    },
    directions() {
      const ds = S.opp.directions.slice(0, 9);
      return `<div class="cards">${ds.map((d) => `<div class="card glass reveal"><div class="k">${esc(d.group)}</div><h4>${esc(d.label)}</h4>
          <div class="v">${d.cash_to_open_range ? (d.cash_to_open_range[0] === d.cash_to_open_range[1] ? kmoney(d.cash_to_open_range[0]) : `${kmoney(d.cash_to_open_range[0])}–${kmoney(d.cash_to_open_range[1])}`) : "—"}</div><div class="k">cash to open ${srcChip({ name: "FDD benchmark" })}</div>
          <div class="chips">${chip(d.supported ? "green" : "amber", d.supported ? `${d.supported} supported` : "mixed, net positive")}${chip("grey", `${d.places} place${d.places > 1 ? "s" : ""}`)}${d.within_budget ? chip("green", `${d.within_budget} within budget`) : ""}</div>
          <p>${esc(tidy(d.why))} ${srcChip({ name: "ACS · OSM · CoStar" })}</p></div>`).join("")}</div>
        ${(S.opp.cost_not_estimated || []).length ? `<p class="note block">Not estimated: ${S.opp.cost_not_estimated.map((u) => `${esc(u.label)} (${u.places} places; ${esc(u.why)})`).join("; ")}. We don't guess a number.</p>` : ""}`;
    },
    shortlist() { return picksHtml(); },
    site() {
      const s = S.pre; if (!s) return "";
      const j = s.jurisdiction || {}, f = s.facts || {};
      const state = s.stops.length ? ["red", "We stop here"] : s.checks.length ? ["amber", "Continue, with checks"] : ["green", "Clear to look at businesses"];
      return `<div class="sec-head"><h3 class="title">${esc(s.address)}</h3>${chip(state[0], state[1])}</div>
        <div class="cards">
          <div class="card glass reveal"><div class="k">Who permits it</div><h4>${esc(j.place || (j.county ? "Unincorporated " + j.county : "Not verified"))}</h4><p>${esc(tidy(j.note || ""))}</p>${srcChip({ name: "U.S. Census geocoder", url: j.evidence_url, retrieved_at: j.retrieved_at })}</div>
          <div class="card glass reveal"><div class="k">Authority</div><h4>${esc((s.authority || {}).name || "—")}</h4>${s.authority ? srcChip({ name: "Official page", url: s.authority.url }) : ""}</div>
          <div class="card glass reveal"><div class="k">Building</div><h4>${esc(f.property_type || "—")}</h4><p>${f.area_sqft ? num(f.area_sqft) + " sq ft · " : ""}${f.floors ?? "?"} floor(s) · parking ${f.parking_spaces ?? "not recorded"}</p>${srcChip({ name: "CoStar property record" })}</div>
          <div class="card glass reveal"><div class="k">Listed for lease</div><h4>${s.spaces.length} space${s.spaces.length === 1 ? "" : "s"}</h4><p>${s.spaces.slice(0, 4).map((x) => esc(x.label)).join(" · ") || "Nothing listed"}</p></div>
        </div>
        ${s.stops.length || s.checks.length ? `<ul class="reasons block">${s.stops.concat(s.checks).map((x) => `<li><div>${esc(x)}</div></li>`).join("")}</ul>` : ""}
        ${s.stops.length ? `<div class="flip glass block"><b>We stop here.</b> No business is suggested for a building that fails this check. <a href="#ch-cash">Pick another building</a> or start from a budget instead.</div>` : ""}
        <div class="block"><div class="kicker">Still to verify with the authority · none counted as cleared</div><ul class="reasons" style="margin-top:10px">${(s.to_verify || []).map((x) => `<li><div class="muted">${esc(x)}</div></li>`).join("")}</ul></div>`;
    },
    fits() {
      const o = S.opp; if (!o) return "";
      const nh = o.not_here || [];
      return `${picksHtml()}<div class="block"><div class="sec-head"><h3 class="title">Fits here: ${o.directions.length} of 26.</h3></div>
          <div class="cards">${o.directions.map((d) => `<div class="card glass reveal"><div class="k">${esc(d.group)}</div><h4>${esc(d.label)}</h4><div class="v">${kmoney((d.pairs[0] || {}).cost ? d.pairs[0].cost.cash_to_open.base : null)}</div><p>${esc(tidy(d.why))}</p></div>`).join("")}</div></div>
        ${nh.length ? `<div class="block"><div class="sec-head"><h3 class="title">Didn't make it: ${nh.length}.</h3><span class="note">Every business stopped at one gate. Here's which, and why.</span></div>
          <table class="ledger">${nh.map((x) => `<tr><td><span class="sd ${x.stopped_at === "neighborhood" ? "amber" : "red"}"></span></td><td><div class="f">${esc(x.label)} <span class="faint">· ${esc(x.stopped_at)} gate</span></div><div class="n">${esc(tidy(x.why))}</div></td></tr>`).join("")}</table></div>` : ""}`;
    },
    investigate() {
      const r = lead(); if (!r) return `<div class="error">No review to show.${S.pre && S.pre.stops.length ? " The building check stopped this path." : ""}</div>`;
      const trace = (r.trace || []).filter((t) => t.agent !== "verdict" && t.agent !== "narrator");
      const maxMs = Math.max(1, ...trace.map((t) => t.ms || 0));
      let off = 0;
      const water = trace.map((t) => { const w = Math.max(2, 100 * (t.ms || 0) / (trace.reduce((a, x) => a + (x.ms || 0), 0) || 1)); const row = `<div class="wrow" data-agent="${esc(t.agent)}"><span class="nm">${esc(t.agent)}</span><span class="bar"><i style="left:${off}%;width:${Math.min(100 - off, w)}%"></i></span><span class="ms">${t.ms ?? 0} ms</span></div>`; off = Math.min(98, off + w); return row; }).join("");
      const segs = (r.because || []).map((b) => `<i class="${EFFECT[b.effect][0]}" data-agent="${esc(b.agent)}" style="visibility:hidden"></i>`).join("");
      const tabs = S.reviews.length > 1 ? `<div class="seg" id="leadTabs" style="margin-bottom:22px">${S.reviews.map((x, i) => x.error ? "" : `<button type="button" data-i="${i}" class="${i === S.lead ? "on" : ""}">${esc(x.label.split(" / ")[0])} · ${esc(x.address.split(",")[0])}</button>`).join("")}</div>` : "";
      const cards = GROUPS.map((g) => {
        const ts = g.agents.map((a) => trace.find((t) => t.agent === a)).filter(Boolean);
        if (!ts.length) return "";
        return `<div class="group-h" id="${g.id}" data-group="${g.id}"><div class="eyebrow">${esc(g.stage)}</div><h3 class="title">${esc(g.title)}</h3><p>${esc(g.lede)}</p></div>${ts.map((t) => agentCard(t, r)).join("")}`;
      }).join("");
      return `${tabs}<div class="split"><div class="graphic"><div class="run glass"><div class="run-head"><span class="kicker">Agent run</span><span class="faint small">${trace.length} agents report · the verdict is the 13th · ${trace.reduce((a, t) => a + (t.ms || 0), 0)} ms</span></div>
            <div class="water">${water}</div>
            <div class="tally"><div class="kicker">Signals so far</div><div class="tally-bar" id="tallyBar">${segs}</div><div class="tally-legend" id="tallyLegend"></div></div>
            <div class="verdict-hidden">The verdict stays hidden until every agent has reported. <a href="#ch-verdict">Skip to it</a></div></div></div>
          <div class="steps">${cards}</div></div>`;
    },
    verdict() {
      const r = lead(); if (!r) return "";
      const rows = (r.because || []).map((x, i) => ({ ...x, i }));
      const counts = Object.fromEntries(Object.keys(EFFECT).map((k) => [k, rows.filter((x) => x.effect === k).length]));
      const ranked = rows.filter((x) => x.decides).sort((a, b) => ["blocks", "check", "supports", "unknown"].indexOf(a.effect) - ["blocks", "check", "supports", "unknown"].indexOf(b.effect)).slice(0, 4);
      const col = (k) => `<div class="why-col"><h5><span class="sd ${EFFECT[k][0]}" style="margin:0"></span>${EFFECT[k][1]}<span class="n">${counts[k]}</span></h5>${rows.filter((x) => x.effect === k).map((x) => `<div class="why-row ${EFFECT[k][0]}">${esc(tidy(x.text))}${x.signal && x.signal.value ? `<div class="sg">${esc(x.signal.name)} <b>${esc(x.signal.value)}</b>${x.signal.rule ? ` · rule: ${esc(x.signal.rule)}` : ""}</div>` : ""}<div class="ft"><span>${esc(x.agent)} agent</span>${x.decides ? "<span>· decides</span>" : ""}${srcChip(x.source)}</div></div>`).join("") || `<div class="faint small">None</div>`}</div>`;
      return `<div class="verdict-wrap">
        <div class="sec-head"><h3 class="title">${esc(r.label)} at ${esc(r.address.split(",")[0])}${r.space && r.space.suite ? ` · Suite ${esc(r.space.suite)}` : r.space && r.space.sf ? ` · ${num(r.space.sf)} sq ft` : ""}</h3><span class="note">${rows.length} reasons from ${new Set(rows.map((x) => x.agent)).size} agents</span></div>
        <div class="why-grid reveal" style="grid-template-columns:${["blocks", "check", "supports", "unknown"].map((k) => `minmax(130px, ${counts[k] ? Math.min(counts[k], 6) / 2 + .5 : .5}fr)`).join(" ")}">${["blocks", "check", "supports", "unknown"].map(col).join("")}</div>
        <div class="reveal"><div class="kicker" style="margin-bottom:12px">What decided it, ranked</div><ol class="reasons">${ranked.map((x) => `<li><div>${esc(tidy(x.text))}<div class="meta">${esc(EFFECT[x.effect][1])} · ${esc(x.agent)} agent ${srcChip(x.source)}</div></div></li>`).join("")}</ol></div>
        <div class="reveal verdict-reveal"><div class="kicker" style="margin-bottom:10px">The call</div><div class="vword ${esc(r.verdict)}"><i></i>${esc(VLABEL[r.verdict] || r.verdict)}</div>
          <p class="lede" style="margin-top:14px">${esc(tidy((r.reasons || [])[0] || ""))}</p></div>
        <div class="flip glass reveal"><b>What would change it:</b> ${(r.flips || []).length ? r.flips.map(esc).join(" · ") : r.verdict === "GO" ? "Nothing flagged. The checks in the last chapter still need answers before you sign." : "—"}
          <div class="faint small" style="margin-top:6px">${counts.unknown} thing${counts.unknown === 1 ? "" : "s"} unknown, shown in grey and never guessed. ${esc(r.computed_by || "")}</div></div></div>`;
    },
    decide() {
      const rows = S.reviews.map((r, i) => ({ r, i })).filter((x) => !x.r.error);
      if (!rows.length) return "";
      const cell = (fn) => rows.map(({ r }) => `<td>${fn(r)}</td>`).join("");
      const loanPick = rows.find(({ r }) => r.pillars.money.cash_12m && r.pillars.money.cash_12m.loan);
      return `<div class="glass table-scroll reveal"><table class="cmp"><thead><tr><th></th>${rows.map(({ r }) => `<th>${esc(r.label.split(" / ")[0])}<div class="faint small">${esc(r.address.split(",")[0])}</div><div style="margin-top:6px">${chip(r.verdict === "GO" ? "green" : r.verdict === "NO-GO" ? "red" : "amber", VLABEL[r.verdict] || r.verdict)}</div></th>`).join("")}</tr></thead><tbody>
          <tr><th>Deciding reason</th>${cell((r) => esc(tidy((r.blockers || [])[0] || (r.conditions || [])[0] || (r.reasons || [])[0] || "")))}</tr>
          <tr><th>Needed incl. reserve</th>${cell((r) => `<span class="num">${kmoney(r.pillars.money.required.base)}</span> <span class="faint">of ${kmoney(S.budget)}</span> ${srcChip({ name: "FDD benchmark" })}`)}</tr>
          <tr><th>Neighborhood</th>${cell((r) => esc(cap((r.pillars.demand || {}).verdict || "unknown")))}</tr>
          <tr><th>Who permits it</th>${cell((r) => esc(((r.jurisdiction || {}).place) || ((r.jurisdiction || {}).county ? "Unincorporated " + r.jurisdiction.county : "not verified")))}</tr></tbody></table></div>
        <div class="block"><div class="sec-head"><h3 class="title">Month by month, with zero revenue.</h3><span class="note">Which pick dips into your reserve, and when.</span></div><div class="glass" id="cash12"></div></div>
        ${loanPick ? `<div class="block"><div class="sec-head"><h3 class="title">Or borrow the gap.</h3><span class="note">A Nessie business loan, sized to what cash alone can't cover.</span></div><div id="loanBox"></div></div>` : ""}`;
    },
    plan() {
      const r = lead(); if (!r) return "";
      const items = planItems(r);
      const cols = WHO.concat([["you", "You", ""]]).map(([k, name]) => [k, name, items.filter((x) => x.who === k)]).filter(([, , xs]) => xs.length);
      return `<div class="plan-grid">${cols.map(([, name, xs]) => `<div class="plan-col glass reveal"><h4>${esc(name)}<span class="faint small">${xs.length}</span></h4><ul>${xs.map((x) => `<li class="${x.blocker ? "blk" : ""}"><span>${esc(tidy(x.text))}${x.url ? ` <a class="srcchip" href="${esc(x.url)}" target="_blank" rel="noopener">official ↗</a>` : ""}</span></li>`).join("")}</ul></div>`).join("")}</div>
        <div class="block reveal"><div class="sec-head"><h3 class="title">Every source this report touched.</h3><button class="btn ghost" type="button" data-legend>How to read the signals</button></div>${sourcesTable(r)}</div>
        <p class="note block">All numbers and verdicts are computed in code from cached sources. Nessie data is a sandbox persona. Nothing here is a permit, an approval or a revenue forecast. <a href="/suite">Open the workspace view</a>.</p>`;
    },
  };

  function picksHtml() {
    const rows = S.reviews.map((r, i) => ({ r, i, p: S.picks[i] }));
    return `<div class="cards">${rows.map(({ r, i, p }) => r.error ? `<div class="card glass error">${esc(p.label)}: ${esc(r.error)}</div>` : `<button type="button" class="card glass pick reveal ${i === S.lead ? "on" : ""}" data-pick="${i}">
        <div class="k">${esc(r.group || "")}</div><h4>${esc(r.label)}</h4><p>${esc(r.address)} · ${esc(p.suite_label || "")}</p>
        <div class="v">${kmoney(r.pillars.money.cash_to_open.base)}</div><div class="k">cash to open (${kmoney(r.pillars.money.cash_to_open.low)}–${kmoney(r.pillars.money.cash_to_open.high)}) ${srcChip({ name: "FDD benchmark" })}</div>
        <div class="chips">${chip(r.pillars.space.status === "fits" ? "green" : r.pillars.space.status === "no" ? "red" : "amber", "Building: " + r.pillars.space.status)}${chip(r.pillars.money.affordability === "within" ? "green" : r.pillars.money.affordability === "over" ? "red" : "amber", "Cash: " + r.pillars.money.affordability.replace("_", " "))}${chip((r.pillars.demand || {}).verdict === "supported" ? "green" : "amber", "Neighborhood: " + ((r.pillars.demand || {}).verdict || "unknown"))}</div>
        <div class="faint small">${i === S.lead ? "Following this one through the agents" : "Follow this one instead"}</div></button>`).join("")}</div>`;
  }

  // ---------- one agent ----------
  const FSTAT = { agrees: ["green", "confirmed"], conflict: ["amber", "conflict"], unknown: ["grey", "unknown"] };
  function fmtVal(v) {
    if (v == null) return "unknown";
    if (Array.isArray(v)) return v.length ? v.map(fmtVal).join(", ") : "none";
    if (typeof v === "object") return Object.entries(v).slice(0, 5).map(([k, x]) => `${k.replace(/_/g, " ")}: ${typeof x === "object" && x ? JSON.stringify(x) : fmtVal(x)}`).join(" · ");
    if (typeof v === "number") return Math.abs(v) >= 1000 ? num(v) : String(v);
    return String(v);
  }
  function sigVal(sig) { // same wording as the review's signal values
    const v = sig.value; if (v == null) return "unknown";
    return { lookalike: `${v}th percentile`, "local supply": `${v}x the Houston-area rate`, "population trend": `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)} pts vs the Houston area`, "business arrivals": `${v >= 0 ? "+" : ""}${v} net arrivals` }[sig.name] || fmtVal(v);
  }
  function stanceOf(sig) { const s = sig && sig.stance; return s > 0 ? ["green", "↑", "supports"] : s < 0 ? ["amber", "↓", "counts against"] : s === 0 ? ["grey", "–", "neutral"] : ["grey", "?", "unknown"]; }
  function thresholdBar(sig) {
    const g = (S.guide && S.guide.thresholds) || {};
    if (!sig || sig.value == null) return "";
    if (sig.name === "lookalike") { const lo = g.lookalike_minus || 30, hi = g.lookalike_plus || 70; return `<div class="thresh" title="0–100th percentile; votes at ≤${lo} and ≥${hi}"><span class="ln"></span><span class="tk" style="left:${lo}%"></span><span class="tk" style="left:${hi}%"></span><span class="val" style="left:${Math.max(0, Math.min(100, sig.value))}%"></span></div>`; }
    if (sig.name === "local supply") { const x = (v) => Math.max(0, Math.min(100, 50 + 25 * Math.log2(v))); return `<div class="thresh" title="supply vs Houston rate, log scale; votes at ≤${g.supply_under}x and ≥${g.supply_over}x"><span class="ln"></span><span class="tk" style="left:${x(g.supply_under || .5)}%"></span><span class="tk" style="left:${x(g.supply_over || 2)}%"></span><span class="val" style="left:${x(Math.max(.05, sig.value))}%"></span></div>`; }
    return "";
  }
  function agentCard(t, r) {
    const sig = t.signal, [sc, sa, sw] = stanceOf(sig);
    const mine = (r.because || []).filter((b) => b.agent === t.agent);
    const rows = (t.findings || []).map((f) => {
      const [c, word] = FSTAT[f.status] || FSTAT.unknown;
      return `<tr><td><span class="sd ${c}" title="${word}"></span></td><td><div class="f">${esc(String(f.fact).replace(r.business + ".", "").replace(/^compliance\./, "").replace(/[._]/g, " "))}${f.needs_human ? `<span class="verify">person must verify</span>` : ""}</div>
        <div class="v">${esc(tidy(fmtVal(f.value)))}</div>${f.note ? `<div class="n">${esc(tidy(f.note))}</div>` : ""}<div class="s">${srcChip({ name: f.source ? String(f.source).replace(/^public:/, "") : "", url: f.evidence_url, retrieved_at: f.captured_at, confidence: f.confidence })}</div></td></tr>`;
    });
    const inputs = Object.entries(t.inputs || {}).filter(([, v]) => v != null && v !== "");
    return `<article class="agent step glass" data-step="agent" data-agent="${esc(t.agent)}">
      <div class="agent-top"><span class="nm">${esc(t.agent)} agent</span><span class="meta">${t.computed_by === "llm" ? "LLM" : "code"} · ${t.ms ?? 0} ms${t.confidence != null ? ` · confidence ${t.confidence}` : ""}</span></div>
      <div class="q">${esc(AGENT_Q[t.agent] || t.role || "")}</div>
      <div class="sum">${esc(tidy(t.summary || "No summary."))}</div>
      ${sig ? `<div class="signal"><span class="arrow ${sc}">${sa}</span><div><div class="w"><b>${esc(sig.name)}</b> ${esc(sw)}${sig.value != null ? ` · ${esc(sigVal(sig))}` : ""}${sig.name === "lookalike" && sig.validated === false ? " · not validated, does not vote" : ""}</div><div class="r">${esc(sig.reason || "")}</div>${thresholdBar(sig)}</div></div>` : ""}
      ${mine.length ? `<div class="chips">${mine.map((b) => chip(EFFECT[b.effect][0], `${EFFECT[b.effect][1]}${b.decides ? " · decides" : ""}`, b.text)).join("")}</div>` : ""}
      ${rows.length ? `<table class="ledger">${rows.slice(0, 5).join("")}</table>${rows.length > 5 ? `<details class="more"><summary>${rows.length - 5} more finding${rows.length - 5 > 1 ? "s" : ""}</summary><table class="ledger">${rows.slice(5).join("")}</table></details>` : ""}` : ""}
      ${inputs.length ? `<div class="kv"><span>Inputs</span>${inputs.map(([k, v]) => `<span class="pill">${esc(k.replace(/_/g, " "))}: ${esc(tidy(fmtVal(v)).slice(0, 60))}</span>`).join("")}</div>` : ""}
      ${(t.sources || []).length ? `<div class="kv"><span>Sources</span>${t.sources.slice(0, 4).map((s) => srcChip({ name: s.name, url: s.url, retrieved_at: s.retrieved_at })).join("")}</div>` : ""}
      ${t.handoff ? `<div class="handoff"><b>Hands off:</b> ${esc(t.handoff)}</div>` : ""}</article>`;
  }

  // ---------- 12-month cash (zero revenue) and the Nessie loan ----------
  const SERIES = ["#3987e5", "#d95926", "#199e70"];
  let cashCase = "base";
  function cashSentence(c, label, which) {
    const k = which || c.cases[cashCase], open = k.opens;
    if (k.first_month_below_zero) return `<b>${esc(label)}</b> ${k.first_month_below_reserve && k.first_month_below_reserve < k.first_month_below_zero ? `dips into your reserve in month ${k.first_month_below_reserve} and ` : ""}runs out of cash in month ${k.first_month_below_zero}${k.first_month_below_zero < open ? ", before it even opens" : ""}.`;
    if (k.first_month_below_reserve) { const after = k.first_month_below_reserve - open; return `<b>${esc(label)}</b> dips into your reserve in month ${k.first_month_below_reserve}${after > 0 ? `, ${after} month${after > 1 ? "s" : ""} after opening` : ", before opening"}.`; }
    return `<b>${esc(label)}</b> stays above your reserve for all ${c.months} months with zero revenue (${kmoney(k.cash[c.months])} left).`;
  }
  function cashChart(items) {
    items = items.filter((x) => x.c);
    if (!items.length) return `<div class="faint small" style="padding:18px">No 12-month view: no asking rent to bill.</div>`;
    const c0 = items[0].c, M = c0.months, W = 1100, H = 340, L = 64, R = 150, T = 16, B = 36;
    const axm = (v) => (Math.abs(v) < 1 ? "$0" : kmoney(v));
    const vals = items.flatMap((x) => x.c.cases[cashCase].cash).concat([0, c0.reserve, c0.budget]);
    let lo = Math.min(...vals), hi = Math.max(...vals); const pad = (hi - lo) * .06; lo -= pad; hi += pad;
    const x = (m) => L + (W - L - R) * m / M, y = (v) => T + (H - T - B) * (hi - v) / (hi - lo);
    const mag = Math.pow(10, Math.floor(Math.log10((hi - lo) / 4))), step = mag * ([1, 2, 5].find((f) => (hi - lo) / (mag * f) <= 5) || 10);
    const ticks = []; for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push(v);
    const k0 = c0.cases[cashCase];
    const ends = items.map((it, j) => ({ j, yy: y(it.c.cases[cashCase].cash[M]) })).sort((a, b) => a.yy - b.yy), nudge = items.map(() => 0);
    ends.forEach((e, n) => { if (n && e.yy + nudge[e.j] - (ends[n - 1].yy + nudge[ends[n - 1].j]) < 15) nudge[e.j] = ends[n - 1].yy + nudge[ends[n - 1].j] + 15 - e.yy; });
    const lines = items.map((it, j) => { const k = it.c.cases[cashCase], dip = k.first_month_below_reserve;
      return `<polyline class="cc-line" points="${k.cash.map((v, m) => `${x(m).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}" fill="none" stroke="${SERIES[j]}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
        ${dip ? `<circle cx="${x(dip)}" cy="${y(k.cash[dip])}" r="5" fill="${SERIES[j]}" stroke="#0B0E14" stroke-width="2"/>` : ""}
        <text x="${x(M) + 8}" y="${y(k.cash[M]) + 4 + nudge[j]}" class="cc-lab">${esc(it.label.split(" · ")[0].slice(0, 20))}</text>`; }).join("");
    return `<div class="cc-wrap"><div class="cc-top"><div class="seg cc-case">${["low", "base", "high"].map((k) => `<button type="button" data-case="${k}" class="${k === cashCase ? "on" : ""}">${cap(k)} cost</button>`).join("")}</div>
        ${items.length > 1 ? `<div class="cc-legend">${items.map((it, j) => `<span><i style="background:${SERIES[j]}"></i>${esc(it.label)}</span>`).join("")}</div>` : ""}</div>
      <div class="cc-plot"><svg class="cc" viewBox="0 0 ${W} ${H}" role="img" aria-label="Cash balance over ${M} months with zero revenue">
        <rect x="${x(0)}" y="${T}" width="${x(k0.opens - 1) - x(0)}" height="${H - T - B}" class="cc-build"/><text x="${x(0) + 6}" y="${T + 14}" class="cc-note">building out</text>
        ${ticks.map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="cc-grid"/><text x="${L - 8}" y="${y(v) + 4}" class="cc-ax" text-anchor="end">${axm(v)}</text>`).join("")}
        <line x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}" class="cc-zero"/><text x="${W - R - 4}" y="${y(0) + 14}" class="cc-note" text-anchor="end">out of cash</text>
        <line x1="${L}" x2="${W - R}" y1="${y(c0.reserve)}" y2="${y(c0.reserve)}" class="cc-res"/><text x="${W - R - 4}" y="${y(c0.reserve) + 14}" class="cc-note" text-anchor="end">your ${kmoney(c0.reserve)} reserve</text>
        <line x1="${x(k0.opens - 1)}" x2="${x(k0.opens - 1)}" y1="${T}" y2="${H - B}" class="cc-open"/><text x="${x(k0.opens - 1) + 4}" y="${H - B - 6}" class="cc-note">opens</text>
        <line x1="${x(k0.opens_if_delayed - 1)}" x2="${x(k0.opens_if_delayed - 1)}" y1="${T}" y2="${H - B}" class="cc-late"/><text x="${x(k0.opens_if_delayed - 1) + 4}" y="${H - B - 6}" class="cc-note">opens if ${c0.delay} mo late</text>
        ${Array.from({ length: M + 1 }, (_, m) => `<text x="${x(m)}" y="${H - 12}" class="cc-ax" text-anchor="middle">${m}</text>`).join("")}
        ${lines}<line class="cc-cross" x1="0" x2="0" y1="${T}" y2="${H - B}" visibility="hidden"/><rect class="cc-hit" x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent"/></svg><div class="cc-tip" hidden></div></div>
      <ul class="says">${items.map((it, j) => `<li><span style="color:${SERIES[j]}">●</span><span>${cashSentence(it.c, it.label)}</span></li>`).join("")}</ul>
      <div class="faint small">Starts from your ${kmoney(c0.budget)}${/Nessie/.test(c0.cash_source || "") ? " (Capital One Nessie sandbox balance)" : ""}; sourced opening costs paid up front, then the CoStar asking rent every month${(c0.other_bills || []).length ? ` plus ${c0.other_bills.map((b) => `${esc(b.payee.toLowerCase())} (${money(b.monthly)}/mo)`).join(", ")} from Nessie` : ""}. Zero revenue, no payroll or utilities, so real runway is shorter. Engine: Jayant's Nessie-pilot simulator.</div></div>`;
  }
  function drawCash() {
    const box = $("#cash12"); if (!box) return;
    const items = S.reviews.filter((r) => !r.error).map((r) => ({ label: `${r.label.split(" / ")[0]} · ${r.address.split(",")[0]}`, c: r.pillars.money.cash_12m }));
    box.innerHTML = cashChart(items);
    $$(".cc-case button", box).forEach((b) => b.onclick = () => { cashCase = b.dataset.case; drawCash(); drawLoan(); });
    const svg = $("svg", box), hit = $(".cc-hit", box), tip = $(".cc-tip", box), cross = $(".cc-cross", box);
    if (svg && hit) {
      const its = items.filter((x) => x.c), M = its[0].c.months, vb = svg.viewBox.baseVal;
      hit.onmousemove = (ev) => { const r = svg.getBoundingClientRect(), sx = (ev.clientX - r.left) * vb.width / r.width, m = Math.max(0, Math.min(M, Math.round((sx - 64) / (vb.width - 214) * M))), xx = 64 + (vb.width - 214) * m / M;
        cross.setAttribute("x1", xx); cross.setAttribute("x2", xx); cross.setAttribute("visibility", "visible"); tip.hidden = false; tip.style.left = Math.min(r.width - 210, xx * r.width / vb.width + 12) + "px";
        tip.innerHTML = `<b>Month ${m}</b>${its.map((it, j) => `<div><i style="background:${SERIES[j]}"></i>${esc(it.label.split(" · ")[0])} <span class="num">${money(it.c.cases[cashCase].cash[m])}</span></div>`).join("")}`; };
      hit.onmouseleave = () => { tip.hidden = true; cross.setAttribute("visibility", "hidden"); };
    }
    if (!STATIC && window.gsap) $$(".cc-line", box).forEach((l) => { const len = l.getTotalLength(); gsap.fromTo(l, { strokeDasharray: len, strokeDashoffset: len }, { strokeDashoffset: 0, duration: 1.2, ease: "power2.out", scrollTrigger: { trigger: box, start: "top 75%" } }); });
  }
  function drawLoan() {
    const box = $("#loanBox"); if (!box) return;
    const r = S.reviews.find((x) => !x.error && x.pillars.money.cash_12m && x.pillars.money.cash_12m.loan);
    if (!r) return;
    const c = r.pillars.money.cash_12m, L = c.loan, label = `${r.label.split(" / ")[0]} · ${r.address.split(",")[0]}`;
    const withLoan = { ...c, cases: Object.fromEntries(Object.entries(L.cases).map(([k, v]) => [k, { ...v, opens_if_delayed: c.cases[k].opens_if_delayed }])) };
    box.innerHTML = `<div class="loan glass"><div><div class="k faint small">${esc(label)} needs ${kmoney(r.pillars.money.cash_to_open.base)} to open + your ${kmoney(c.reserve)} reserve, with ${kmoney(c.budget)} in the bank</div>
        <div class="v" style="margin-top:6px">Borrow ${kmoney(L.amount)} · ${money(L.monthly_payment)}/mo</div>
        <div class="muted small">${L.apr}% APR assumed, ${L.term_months} months; about ${money(L.first_year_interest)} interest in year one.</div></div>${chip("blue", "Nessie loan · sandbox")}
        <div style="grid-column:1/-1" class="faint small">${esc(L.label)}. Payment charged every month below; still zero revenue. Engine: Jayant's nessie_loan.plan + with_loan.</div></div>
      <div class="glass" style="margin-top:12px">${cashChart([{ label: "Cash only · " + label, c }, { label: "With the loan · " + label, c: withLoan }])}</div>`;
    $$(".cc-case button", box).forEach((b) => b.onclick = () => { cashCase = b.dataset.case; drawCash(); drawLoan(); });
  }

  // ---------- plan + sources ----------
  const WHO = [
    ["broker", "Broker", /records disagree|caption|scan|survey|size field|asking|rent|lease basis|available|pending|suite/i],
    ["landlord", "Landlord", /landlord|tenant-improvement|build-out|outdoor|fenced|plumb|ventilat|hvac|electric|power|ceiling|parking|loading|deed|grease|hood|drain|floor|consent|signage|water|visibility/i],
    ["inspector", "Inspector", /inspect|fire|accessib|occupancy|final|sprinkler|exit/i],
    ["city", "City, county & state", /permit|license|certificate|registration|tax|city|county|state|health|tabc|tdlr|hhsc/i],
  ];
  function planItems(r) {
    const out = [], seen = new Set();
    const add = (text, who, extra) => { const t = String(text).trim(), id = t.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 60); if (!t || seen.has(id)) return; seen.add(id); out.push(Object.assign({ text: t, who }, extra || {})); };
    const classify = (t) => (WHO.find(([, , re]) => re.test(t)) || ["you"])[0];
    (r.blockers || []).forEach((t) => add(t, "you", { blocker: true }));
    (r.conditions || []).concat(r.checks || []).forEach((t) => add(t, classify(t)));
    (r.pillars.permits || []).forEach((x) => add(`${x.title} (${x.authority})`, /inspect|fire|final/i.test(x.title) ? "inspector" : /deed|allowed use/i.test(x.title) ? "landlord" : "city", { url: x.url }));
    return out;
  }
  function sourcesTable(r) {
    const seen = new Map();
    const add = (name, url, when, agent) => { if (!name) return; const k = (name + "|" + (url || "")).toLowerCase(); const cur = seen.get(k) || { name, url, when: "", agents: new Set() }; if (when && day(when) > cur.when) cur.when = day(when); cur.agents.add(agent); seen.set(k, cur); };
    if (S.nessie) add(S.nessie.source, null, S.nessie.retrieved_at, "intake");
    (r.trace || []).forEach((t) => (t.sources || []).forEach((x) => add(x.name, x.url, x.retrieved_at, t.agent)));
    (r.trace || []).forEach((t) => (t.findings || []).forEach((f) => { if (f.evidence_url && /^public:/.test(f.source || "")) add(String(f.source).replace(/^public:/, ""), f.evidence_url, f.captured_at, t.agent); }));
    return `<table class="src-table">${[...seen.values()].map((x) => `<tr><td>${esc(x.name)}</td><td class="faint">${[...x.agents].map(esc).join(", ")}</td><td class="faint">${x.when ? "retrieved " + esc(x.when) : "cached kit / benchmark"}</td><td>${x.url ? `<a class="srcchip" href="${esc(x.url)}" target="_blank" rel="noopener">open ↗</a>` : ""}</td></tr>`).join("")}</table>`;
  }

  // ---------- start controls ----------
  function startControls() {
    const groups = [...new Set(S.industries.map((x) => x.group))];
    const biz = `<div class="field"><label for="bizSel">Business</label><select class="select" id="bizSel"><option value="">Choose…</option>${groups.map((g) => `<optgroup label="${esc(g)}">${S.industries.filter((x) => x.group === g).map((x) => `<option value="${esc(x.key)}" ${x.key === S.business ? "selected" : ""}>${esc(x.label)}</option>`).join("")}</optgroup>`).join("")}</select></div>`;
    const place = `<div class="field" style="flex:1;min-width:240px"><label for="placeQ">Building</label><input class="input" id="placeQ" autocomplete="off" placeholder="Street address, e.g. 11220 Louetta" value="${esc((S.pre && S.pre.address) || "")}" data-id="${S.place || ""}"><div class="places" id="placeRes"></div></div>`;
    return `<div class="seg" id="pathSeg">${Object.entries(PATHS).map(([k, p]) => `<button type="button" data-path="${k}" class="${k === S.kind ? "on" : ""}">${esc(p.label)}</button>`).join("")}</div>
      <div class="row" id="pathFields">${S.kind === "idea" || S.kind === "both" ? biz : ""}${S.kind === "space" || S.kind === "both" ? place : ""}
        <div class="field"><label for="resIn">Reserve to keep</label><input class="input" id="resIn" inputmode="numeric" value="${num(S.reserve)}"></div>
        <div class="field"><label>&nbsp;</label><button class="btn" type="button" id="runBtn">Run the agents</button></div></div>`;
  }
  function bindStart() {
    $$("#pathSeg button").forEach((b) => b.onclick = () => { const q = new URLSearchParams({ path: b.dataset.path }); location.search = q.toString(); });
    const pq = $("#placeQ");
    if (pq) { let t; pq.oninput = () => { clearTimeout(t); t = setTimeout(async () => { const box = $("#placeRes"), q = pq.value.trim(); if (q.length < 3) { box.innerHTML = ""; return; }
      try { const r = await api(`/api/places?q=${encodeURIComponent(q)}`); box.innerHTML = r.places.map((x) => `<button type="button" data-id="${x.property_id}" data-a="${esc(x.address)}"><span>${esc(x.address)}</span>${chip(x.listed_spaces ? "green" : "grey", x.listed_spaces ? `${x.listed_spaces} listed` : "nothing listed")}</button>`).join("");
        $$("button", box).forEach((b) => b.onclick = () => { pq.value = b.dataset.a; pq.dataset.id = b.dataset.id; box.innerHTML = ""; }); } catch (e) { box.innerHTML = `<div class="error">${esc(e.message)}</div>`; } }, 250); }; }
    const run = $("#runBtn");
    if (run) run.onclick = () => {
      const q = new URLSearchParams({ path: S.kind, reserve: String($("#resIn").value).replace(/[^0-9]/g, "") || "0" });
      const b = $("#bizSel"); if (b) { if (!b.value) return toast("Choose a business first"); q.set("business", b.value); }
      if (pq) { if (!pq.dataset.id) return toast("Pick a building from the list"); q.set("place", pq.dataset.id); }
      location.search = q.toString();
    };
  }

  // ---------- legend ----------
  async function openLegend() {
    const dlg = $("#legend"), g = S.guide;
    if (!g) { toast("Signal guide unavailable"); return; }
    dlg.innerHTML = `<div class="legend-in"><div class="sec-head"><h3 class="title">How to read the signals</h3><button class="btn ghost" type="button" data-close>Close</button></div>
      <div class="chips">${Object.values(EFFECT).map(([c, n]) => chip(c, n)).join("")}</div>
      <div class="sig-grid">${g.signals.map((x) => `<div class="sig"><b>${esc(x.name)}</b><span class="faint">${esc(x.agent)} agent · ${esc(x.source)}</span><span class="muted">${esc(x.measures)}</span>
        <span class="r"><span class="arrow green">↑</span><span>${esc(x.supports)}</span></span><span class="r"><span class="arrow amber">↓</span><span>${esc(x.against)}</span></span><span class="r"><span class="arrow grey">?</span><span>${esc(x.unknown)}</span></span><span class="faint">How accurate: ${esc(x.accuracy)}</span></div>`).join("")}</div>
      <table class="src-table">${(g.lookalike_accuracy || []).filter((x) => x.auc != null).map((x) => `<tr><td>${esc(x.label)}</td><td class="num">AUC ${x.auc.toFixed(2)}</td><td class="faint">${esc(x.note)}</td></tr>`).join("")}</table></div>`;
    dlg.showModal();
  }

  // ---------- scroll: rail, steps, sheets ----------
  let lenis = null;
  function go(target) { const el = typeof target === "string" ? $(target) : target; if (!el) return; if (lenis) lenis.scrollTo(el, { offset: 0, duration: 1.1 }); else el.scrollIntoView({ behavior: STATIC ? "auto" : "smooth" }); }
  function bindAll() {
    if (window.gsap && window.ScrollTrigger) gsap.registerPlugin(ScrollTrigger);
    bindStart();
    document.onclick = (e) => {
      const a = e.target.closest('a[href^="#"]'); if (a && a.getAttribute("href").length > 1) { e.preventDefault(); go(a.getAttribute("href")); return; }
      if (e.target.closest("[data-legend]")) { openLegend(); return; }
      if (e.target.closest("[data-close]")) { $("#legend").close(); return; }
      const pick = e.target.closest("[data-pick]"); if (pick) { setLead(+pick.dataset.pick); return; }
      const tab = e.target.closest("#leadTabs button"); if (tab) setLead(+tab.dataset.i);
    };
    // map
    const mapEl = $("#scanMap");
    if (mapEl && S.opp && S.opp.map && window.Suite3D && Suite3D.ok()) {
      try { S.map = Suite3D.map(mapEl, { pins: [], plain: true }); if (S.map) S.map.setDots(S.opp.map.buildings); } catch { S.map = null; }
    }
    if (mapEl && !S.map) mapEl.innerHTML = `<div class="faint small" style="padding:18px">3D map unavailable here; the counts on the right are the same.</div>`;
    drawCash(); drawLoan();
    observeSteps(); revealOnScroll(); sheets(); railTick(); updateTally(-1);
    addEventListener("scroll", railTick, { passive: true }); addEventListener("resize", railTick);
  }
  function setLead(i) {
    if (i === S.lead || !S.reviews[i] || S.reviews[i].error) return;
    S.lead = i;
    ["investigate", "verdict", "plan", "shortlist", "fits"].forEach((id) => { const b = $(`#body-${id}`); if (b) b.innerHTML = BODY[id](); const h = $(`#ch-${id} .headline`); if (h) h.innerHTML = CH[id].head(); });
    const sub = $('#railList li[data-ch="investigate"] .sub'); if (sub && lead()) sub.textContent = lead().label.split(" / ")[0];
    observeSteps(); revealOnScroll(); updateTally(-1);
    if (window.ScrollTrigger) ScrollTrigger.refresh();
    toast(`Following ${lead().label.split(" / ")[0]} at ${lead().address.split(",")[0]}`);
  }
  let io = null;
  function observeSteps() {
    if (io) io.disconnect();
    io = new IntersectionObserver((entries) => entries.forEach((en) => { if (en.isIntersecting) activate(en.target); }), { rootMargin: "-42% 0px -42% 0px" });
    $$(".step").forEach((s) => io.observe(s));
  }
  function activate(step) {
    const box = step.closest(".steps"); $$(".step", box).forEach((s) => s.classList.toggle("on", s === step));
    if (step.dataset.step === "scan") {
      const g = +step.dataset.gate, bar = +step.dataset.bar;
      if (S.map) S.map.showGate(g);
      const m = S.opp.map.after_gate[g]; const names = ["with listed space", "that can host a business", "affordable for one", "with neighborhood support", "with a known permitting authority"];
      const c = $("#mapCount"); if (c && m != null) c.innerHTML = `<b>${num(m)}</b> of ${num(S.opp.map.after_gate[0])} buildings ${names[g]}`;
      $$(".gate-bar").forEach((b) => { const k = +b.dataset.bar; b.classList.toggle("on", k <= bar); const i = $("i", b); i.style.width = k <= bar ? i.dataset.w + "%" : "0"; });
    }
    if (step.dataset.step === "agent") {
      const a = step.dataset.agent, order = $$('.agent[data-step="agent"]').map((x) => x.dataset.agent), idx = order.indexOf(a);
      $$(".wrow").forEach((w) => { const k = order.indexOf(w.dataset.agent); w.classList.toggle("on", w.dataset.agent === a); w.classList.toggle("seen", k >= 0 && k <= idx); });
      updateTally(idx, order);
      const g = GROUPS.find((x) => x.agents.includes(a));
      $$("#railList .agents li").forEach((li) => { const gi = GROUPS.findIndex((x) => x.id === li.dataset.g), cur = GROUPS.indexOf(g); li.classList.toggle("seen", gi <= cur); li.classList.toggle("on", gi === cur); });
    }
  }
  function updateTally(idx, order) {
    order = order || $$('.agent[data-step="agent"]').map((x) => x.dataset.agent);
    const seen = new Set(order.slice(0, idx + 1));
    const segs = $$("#tallyBar i"); const counts = { green: 0, amber: 0, red: 0, grey: 0 };
    segs.forEach((s) => { const on = seen.has(s.dataset.agent) || (s.dataset.agent === "verdict" && idx >= order.length - 1); s.style.visibility = on ? "visible" : "hidden"; if (on) counts[s.className]++; });
    const lg = $("#tallyLegend"); if (lg) lg.innerHTML = `<span><b>${counts.green}</b> support</span><span><b>${counts.amber}</b> need a check</span><span><b>${counts.red}</b> block</span><span><b>${counts.grey}</b> unknown</span>`;
  }
  function revealOnScroll() {
    if (STATIC) { $$(".reveal").forEach((r) => r.classList.add("in")); return; }
    const ro = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); ro.unobserve(e.target); } }), { rootMargin: "0px 0px -12% 0px" });
    $$(".reveal:not(.in)").forEach((r) => ro.observe(r));
  }
  function sheets() {
    if (STATIC || !window.gsap || !window.ScrollTrigger) return;
    $$(".ch").forEach((ch) => {
      const inner = $(".ch-intro-inner", ch), dim = $(".dim", ch), body = $(".ch-body", ch);
      gsap.fromTo(inner, { scale: 1, yPercent: 0 }, { scale: .9, yPercent: -4, ease: "none", scrollTrigger: { trigger: body, start: "top bottom", end: "top top", scrub: true } });
      gsap.fromTo(dim, { opacity: 0 }, { opacity: .82, ease: "none", scrollTrigger: { trigger: body, start: "top bottom", end: "top top", scrub: true } });
      gsap.from($$(".headline, .lede, .ch-tools, .stage-no", inner), { y: 26, opacity: 0, stagger: .08, duration: .9, ease: "power3.out", scrollTrigger: { trigger: ch, start: "top 70%" } });
    });
    gsap.to(".hero .hero-inner", { y: -80, opacity: 0, ease: "none", scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true } });
    gsap.to(".hero .f1", { yPercent: -20, scale: 1.2, ease: "none", scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true } });
    if (!TOUCH && window.Lenis) {
      lenis = new Lenis({ lerp: .1, wheelMultiplier: .95, smoothWheel: true });
      lenis.on("scroll", () => { ScrollTrigger.update(); railTick(); });
      gsap.ticker.add((t) => lenis.raf(t * 1000)); gsap.ticker.lagSmoothing(0);
    }
    const vr = $(".verdict-reveal .vword");
    if (vr) gsap.from(vr, { scale: .92, opacity: 0, duration: 1, ease: "power3.out", scrollTrigger: { trigger: vr, start: "top 80%" } });
  }
  function railTick() {
    const items = $$("#railList > li"); if (!items.length) return;
    const mid = scrollY + innerHeight * .45;
    const tops = items.map((li) => { const s = $("#ch-" + li.dataset.ch); return s ? s.getBoundingClientRect().top + scrollY : Infinity; });
    let cur = -1; tops.forEach((t, i) => { if (mid >= t) cur = i; });
    items.forEach((li, i) => { li.classList.toggle("done", i <= cur); li.classList.toggle("now", i === cur); const a = $("a", li); if (i === cur) a.setAttribute("aria-current", "step"); else a.removeAttribute("aria-current"); });
    const dots = items.map((li) => $(".dot", li)), rail = $("#rail").getBoundingClientRect();
    const cy = (d) => { const r = d.getBoundingClientRect(); return r.top + r.height / 2 - rail.top; };
    const track = $(".rail-track"), first = cy(dots[0]), last = cy(dots[dots.length - 1]);
    track.style.top = first + "px"; track.style.height = Math.max(0, last - first) + "px";
    let fill = 0;
    if (cur >= 0) {
      const next = Math.min(cur + 1, dots.length - 1), span = (tops[next] - tops[cur]) || 1, frac = cur === dots.length - 1 ? 0 : Math.max(0, Math.min(1, (mid - tops[cur]) / span));
      fill = cy(dots[cur]) - first + frac * (cy(dots[next]) - cy(dots[cur]));
    }
    $("#railFill").style.height = Math.max(0, fill) + "px";
  }

  load();
})();
