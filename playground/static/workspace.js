"use strict";
const app = document.getElementById("app");
const cash = (n) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
const esc = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const uses = [
  ["pickleball", "◉", "Indoor pickleball"],
  ["gym", "◇", "Gym & fitness"],
  ["restaurant", "♧", "Restaurant"],
  ["daycare", "☼", "Daycare"],
  ["workshop", "▦", "Workshop & classes"],
];
const labels = Object.fromEntries(uses.map(([id, , name]) => [id, name]));
const defaults = {
  city: "Houston",
  mode: "known",
  uses: ["pickleball"],
  tenure: "lease",
  fitout: 250000,
  capital: 320000,
  reserve: 50000,
  propertyBudget: 12000,
  target: 6,
};
let state = {
  view: "login",
  name: "",
  prefs: { ...defaults, uses: [...defaults.uses] },
  property: null,
  chosenUse: null,
  agent: 0,
  completed: 0,
  running: false,
  checks: [],
  contradictions: false,
  money: null,
};
let runTimer = null,
  toastTimer = null;
// Intentionally small, synthetic catalog. No live availability or recommendation is asserted.
const properties = [
  {
    id: "tanner",
    city: "Houston",
    name: "9700 Tanner Road",
    district: "Northwest Houston",
    suite: "Advertised suite · number unconfirmed",
    area: 10000,
    rent: 8500,
    price: 1450000,
    fitout: 200000,
    months: 4,
    uses: ["pickleball", "gym", "workshop"],
    tenures: ["lease"],
    type: "Industrial",
    note: "Scan-to-suite match unresolved",
    real: true,
    costarId: 23296,
  },
  {
    id: "h-flex",
    city: "Houston",
    name: "Westside flex studio",
    district: "West Houston · illustrative property",
    suite: "Example suite A",
    area: 5200,
    rent: 6200,
    price: 780000,
    fitout: 140000,
    months: 4,
    uses: ["gym", "workshop", "daycare"],
    tenures: ["lease", "buy"],
    type: "Flex space",
    note: "Outdoor access and floor loads unverified",
  },
  {
    id: "h-retail",
    city: "Houston",
    name: "Neighborhood retail shell",
    district: "Central Houston · illustrative property",
    suite: "Example unit 02",
    area: 2800,
    rent: 4500,
    price: 520000,
    fitout: 180000,
    months: 6,
    uses: ["restaurant", "daycare", "workshop"],
    tenures: ["lease", "buy"],
    type: "Retail",
    note: "Ventilation and utility capacity unverified",
  },
  {
    id: "la-flex",
    city: "Los Angeles",
    name: "Valley flex building",
    district: "San Fernando Valley · illustrative property",
    suite: "Example suite 100",
    area: 11000,
    rent: 11500,
    price: 1950000,
    fitout: 235000,
    months: 6,
    uses: ["pickleball", "gym", "workshop"],
    tenures: ["lease", "buy"],
    type: "Industrial",
    note: "Parcel jurisdiction and scan coverage unverified",
  },
  {
    id: "la-studio",
    city: "Los Angeles",
    name: "Creative neighborhood studio",
    district: "Northeast LA · illustrative property",
    suite: "Example suite B",
    area: 4800,
    rent: 7800,
    price: 990000,
    fitout: 160000,
    months: 5,
    uses: ["gym", "workshop", "daycare"],
    tenures: ["lease", "buy"],
    type: "Flex space",
    note: "Change of use and parking allocation unverified",
  },
  {
    id: "la-retail",
    city: "Los Angeles",
    name: "Corner retail opportunity",
    district: "Central LA · illustrative property",
    suite: "Example storefront",
    area: 2600,
    rent: 6500,
    price: 850000,
    fitout: 210000,
    months: 7,
    uses: ["restaurant", "daycare", "workshop"],
    tenures: ["lease", "buy"],
    type: "Retail",
    note: "Kitchen exhaust and accessible entry unverified",
  },
];
const agents = [
  [
    "⌘",
    "Evidence & identity",
    "CoStar · Matterport · Vexcel",
    "Match the space before trusting the numbers.",
  ],
  [
    "▧",
    "Space & condition",
    "Layout · Jev · exterior",
    "Test physical fit and turn visible clues into inspection questions.",
  ],
  [
    "◎",
    "Location & demand",
    "People · competition · exposure",
    "Understand the area without mistaking context for demand.",
  ],
  [
    "◷",
    "Approvals & timeline",
    "Use · permits · build-out",
    "Explain the opening sequence and its dependencies.",
  ],
  [
    "↗",
    "Money & runway",
    "Cash · reserve · funding",
    "Find the assumptions that make the business work.",
  ],
  [
    "✓",
    "Decision & handoff",
    "Blockers · owners · evidence",
    "Turn unknowns into a focused next conversation.",
  ],
];
const badge = (text, kind = "") => `<span class="pill ${kind}">${text}</span>`;
function toast(text) {
  document.getElementById("toast").textContent = text;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(
    () => (document.getElementById("toast").textContent = ""),
    3500,
  );
}
function save() {
  try {
    localStorage.setItem(
      "reuse-mock-v1",
      JSON.stringify({ ...state, running: false }),
    );
    toast("Scenario saved in this browser.");
  } catch {
    toast("Browser storage is unavailable. Use Download handoff instead.");
  }
}
function hasSaved() {
  try {
    return !!localStorage.getItem("reuse-mock-v1");
  } catch {
    return false;
  }
}
function art(city = "Houston", variant = 0) {
  return `<svg viewBox="0 0 600 230" fill="none" aria-hidden="true"><path d="M0 195L600 60M0 225L600 90M70 0L400 230M190 0L520 230" stroke="${city === "Houston" ? "#c4d2bc" : "#d8c7b8"}" stroke-width="20"/><g transform="translate(${variant * 12} 0)"><path d="M120 105L300 45L470 120L290 185Z" fill="${city === "Houston" ? "#a9bc98" : "#c2aa92"}"/><path d="M120 105V150L290 220V185Z" fill="#8f9f7c"/><path d="M290 185L470 120V165L290 220Z" fill="#74896c"/><path d="M145 103L301 55L443 119L289 171Z" stroke="#e5ecd8"/><path d="M230 78L370 145M185 90L325 159" stroke="#e1e7d4" stroke-width="3"/><path d="M315 186V207M345 175V195M375 163V183M405 152V172M435 141V161" stroke="#d6e0c6" stroke-width="9"/></g><circle cx="90" cy="65" r="17" fill="#b5c99a"/><circle cx="500" cy="190" r="23" fill="#b5c99a"/></svg>`;
}
function field(
  name,
  label,
  value,
  type = "number",
  help = "",
  min = 0,
  max = 100000000,
) {
  return `<label class="form-field">${label}<input name="${name}" type="${type}" value="${esc(value)}" ${type === "number" ? `min="${min}" max="${max}" step="1"` : ""} required>${help ? `<small>${help}</small>` : ""}</label>`;
}
function shell(body) {
  const stage = { preferences: 0, shortlist: 1, workspace: 2 }[state.view];
  return `<header class="header"><a class="brand" href="/" aria-label="Reuse home"><b>↗</b>reuse</a><div class="header-right">${badge("INTERACTIVE PROTOTYPE", "amber")}<span class="small muted">${esc(state.name || "Demo workspace")}</span><span class="avatar">${esc((state.name || "D").slice(0, 1).toUpperCase())}</span><button class="text-button small" data-action="logout">Exit demo</button></div></header><div class="layout"><aside class="sidebar"><div class="eyebrow">YOUR NEXT BEGINNING</div>${["Your brief", "Find a property", "Property workspace"].map((s, i) => `<button class="nav-step ${stage === i ? "active" : ""}" data-action="nav" data-step="${i}" ${i > stage ? "disabled" : ""}><i>${i < stage ? "✓" : i + 1}</i>${s}</button>`).join("")}<div class="sidebar-bottom">A better use for<br>what’s already here.<div class="divider"></div><a href="/pilot">Tanner evidence pilot ↗</a><p class="mt">Demo data. No authentication, live search or agents connected.</p></div></aside><main class="main">${body}<div class="footer-note"><span>REUSE / REDEVELOPMENT WORKSPACE</span><span>Mock experience · illustrative outputs · nothing submitted externally</span></div></main></div>`;
}
function render() {
  renderPage();
  if (window.spaceFit) window.spaceFit.mount(app);
}
function renderPage() {
  app.innerHTML =
    state.view === "login"
      ? login()
      : shell(
          state.view === "preferences"
            ? preferences()
            : state.view === "shortlist"
              ? shortlist()
              : workspace(),
        );
}
function login() {
  return `<div class="login"><section class="login-story"><a class="brand" href="/">↗ reuse</a><div class="eyebrow mt">NEW BUSINESS. EXISTING SPACE.</div><h1>Find a place.<br>See what<br>it could <em>become.</em></h1><p>From an idea and a budget to a property worth investigating. Bring the evidence, the numbers and the next steps together.</p><div class="site-art">${art()}</div><div class="story-footer"><span>HOUSTON + LOS ANGELES</span><span>Built for the next use.</span></div></section><section class="login-form"><div class="login-box">${badge("UI PREVIEW", "amber")}<h2>Your next beginning<br>starts here.</h2><p>Explore the journey from business idea to property decision.</p><form id="login-form">${field("name", "What should we call you?", "Alex", "text", "Demo sign-in only. No account or password needed.")}<button class="primary wide" type="submit">Enter demo workspace <span>↗</span></button></form>${hasSaved() ? '<button class="secondary wide mt" data-action="resume">Resume saved scenario</button>' : ""}<div class="divider"></div><div class="row"><span class="avatar">1</span><p class="small">Tell us what you want to build</p></div><div class="row mt"><span class="avatar">2</span><p class="small">Explore properties that could fit</p></div><div class="row mt"><span class="avatar">3</span><p class="small">Watch each specialist investigate</p></div><p class="small mt">This prototype uses example listings and simulated agent outputs. Your inputs stay in this browser.</p></div></section></div>`;
}
function preferences() {
  const p = state.prefs;
  return `<div class="page-heading"><div><div class="eyebrow">01 / YOUR BRIEF</div><h1>What do you want to build, ${esc(state.name)}?</h1><p>A few preferences give your search a direction. You can change them as you learn.</p></div></div><div class="section-label"><h3>Start with a city</h3><span class="small muted">Two markets. One workflow.</span></div><div class="grid2">${["Houston", "Los Angeles"].map((c) => `<button class="city-card ${p.city === c ? "selected" : ""}" data-action="city" data-value="${c}" aria-pressed="${p.city === c}"><div class="city-art ${c === "Los Angeles" ? "la" : ""}">${art(c)}</div><div class="city-copy"><div class="row between"><h3>${c}</h3>${p.city === c ? badge("Selected") : "<span>↗</span>"}</div><p class="small">${c === "Houston" ? "Industrial spaces, retail shells and new possibilities." : "Neighborhood storefronts, studios and flexible spaces."}</p><div class="row">${badge("3 example properties", "neutral")}<span class="small muted">${c === "Houston" ? "Includes the Tanner pilot" : "Illustrative catalog"}</span></div></div></button>`).join("")}</div><div class="preference-layout"><form id="brief-form" class="stack"><section class="panel"><div class="section-label"><div><div class="eyebrow">THE BUSINESS</div><h3>Bring an idea. Or find one.</h3></div></div><div class="choice-row">${[
    ["known", "I know what I want", "Choose the business you have in mind"],
    [
      "open",
      "Open to suggestions",
      "Explore uses that fit the space and budget",
    ],
  ]
    .map(
      ([id, title, sub]) =>
        `<button type="button" class="choice ${p.mode === id ? "selected" : ""}" data-action="mode" data-value="${id}" aria-pressed="${p.mode === id}"><strong>${title}</strong><small>${sub}</small></button>`,
    )
    .join(
      "",
    )}</div><p class="small mt">${p.mode === "known" ? "Select one or more businesses." : "Optional interests. Leave all unselected to explore every use."}</p><div class="uses">${uses.map(([id, icon, name]) => `<button type="button" class="choice use-choice ${p.uses.includes(id) ? "selected" : ""}" data-action="use" data-value="${id}" aria-pressed="${p.uses.includes(id)}"><span class="use-icon">${icon}</span><strong>${name}</strong></button>`).join("")}</div><p id="brief-error" role="alert" class="small"></p></section><section class="panel"><div class="section-label"><div><div class="eyebrow">THE COMMITMENT</div><h3>How do you want to take the space?</h3></div></div><div class="choice-row">${[
    ["lease", "Lease", "Keep acquisition costs lower"],
    ["buy", "Buy", "Own the property and plan its next use"],
  ]
    .map(
      ([id, t, s]) =>
        `<button type="button" class="choice ${p.tenure === id ? "selected" : ""}" data-action="tenure" data-value="${id}" aria-pressed="${p.tenure === id}"><strong>${t}</strong><small>${s}</small></button>`,
    )
    .join(
      "",
    )}</div><div class="grid2 mt">${field("propertyBudget", p.tenure === "lease" ? "Maximum base rent / month ($)" : "Maximum purchase price ($)", p.propertyBudget, "number", p.tenure === "lease" ? "NNN charges and operating costs are separate." : "Acquisition is separate from the fit-out budget.")}${field("fitout", "Maximum fit-out budget ($)", p.fitout, "number", "Construction, finishes and equipment allowance.")}${field("capital", "Available starting capital ($)", p.capital, "number", "Cash available for acquisition, fit-out and opening.")}${field("reserve", "Minimum cash reserve ($)", p.reserve, "number", "The cash cushion you want to protect.")}${field("target", "Target opening (months from now)", p.target, "number", "A preference, not a promised approval date.", 1, 36)}</div></section><div class="actions"><span class="small muted">Illustrative matches; suitability still needs verification.</span><button class="primary" type="submit">Find suitable properties <span>→</span></button></div></form><aside class="panel brief"><div class="eyebrow">YOUR SEARCH BRIEF</div><h3>A place for your<br>next chapter.</h3><dl><div><dt>Market</dt><dd>${p.city}</dd></div><div><dt>Business</dt><dd>${p.uses.length ? p.uses.map((u) => labels[u]).join(", ") : "Open to suggestions"}</dd></div><div><dt>Approach</dt><dd>${p.tenure === "lease" ? "Lease a space" : "Buy a property"}</dd></div><div><dt>Fit-out ceiling</dt><dd id="brief-fitout">${cash(p.fitout)}</dd></div><div><dt>Capital available</dt><dd id="brief-capital">${cash(p.capital)}</dd></div></dl><div class="divider"></div><p class="small">We’ll look at the space, the location and the money—then show you what needs a closer look.</p>${badge("You stay in control", "dark")}</aside></div>`;
}
function eligible() {
  const p = state.prefs;
  return properties
    .filter(
      (x) =>
        x.city === p.city &&
        x.tenures.includes(p.tenure) &&
        x.fitout <= p.fitout &&
        (p.tenure === "lease" ? x.rent : x.price) <= p.propertyBudget &&
        (!p.uses.length || x.uses.some((u) => p.uses.includes(u))),
    )
    .sort((a, b) => {
      const score = (x) =>
        x.uses.filter((u) => p.uses.includes(u)).length * 10 +
        (x.months <= p.target ? 3 : 0);
      return score(b) - score(a) || a.fitout - b.fitout;
    });
}
function shortlist() {
  const p = state.prefs,
    items = eligible();
  return `<div class="page-heading"><div><div class="eyebrow">02 / FIND A PROPERTY</div><h1>Room for your idea.</h1><p>${items.length} example ${items.length === 1 ? "property matches" : "properties match"} your brief in ${p.city}. Choose one to see the specialist workflow.</p></div><button class="secondary" data-action="edit">Edit preferences</button></div><div class="filterbar">${badge(p.city)}${badge(p.tenure === "lease" ? "For lease" : "For purchase")}${badge(`Fit-out ≤ ${cash(p.fitout)}`)}${badge(p.tenure === "lease" ? `Base rent ≤ ${cash(p.propertyBudget)}/mo` : `Price ≤ ${cash(p.propertyBudget)}`)}${badge(`${p.target}-month target`)}${p.uses.map((u) => badge(labels[u], "neutral")).join("")}</div><div class="notice">Mock shortlist: filters work against six curated examples. Prices, availability and fit-out estimates are illustrative. Matches are not verified suitability or a live market search.</div><div class="row between mt"><h3>${items.length ? "Your potential spaces" : "No examples fit this brief"}</h3><span class="small muted">Ordered by interest overlap, then opening target</span></div><div class="grid3 mt">${items
    .map(
      (x, i) =>
        `<article class="panel property-card"><div class="property-art">${art(x.city, i)}${badge(x.type)}</div><div class="property-copy"><span class="eyebrow">${esc(x.district)}</span><h3>${x.name}</h3><p class="small">${x.suite}</p><div class="facts"><div><strong>${x.area.toLocaleString()} SF</strong><span>Example advertised area</span></div><div><strong>${cash(p.tenure === "lease" ? x.rent : x.price)}</strong><span>${p.tenure === "lease" ? "Base rent / month" : "Purchase price"}</span></div></div><div class="row wrap">${x.uses
          .filter((u) => !p.uses.length || p.uses.includes(u))
          .map((u) => badge(labels[u], "neutral"))
          .join(
            "",
          )}</div><ul><li>${cash(x.fitout)} example fit-out · within your ceiling</li><li>${x.months}-month example opening${x.months > p.target ? " · later than your target" : ""}</li><li>${cash(p.capital)} capital · ${Math.max(0, (p.tenure === "buy" ? x.price : 0) + x.fitout + p.reserve - p.capital) > 0 ? cash(Math.max(0, (p.tenure === "buy" ? x.price : 0) + x.fitout + p.reserve - p.capital)) + " upfront gap before runway" : "covers fit-out + reserve"}</li></ul><div class="notice">${x.note}</div><button class="primary wide" data-action="select" data-id="${x.id}">Investigate this property <span>↗</span></button></div></article>`,
    )
    .join(
      "",
    )}</div>${!items.length ? `<div class="empty mt"><h2>A small catalog, not a dead end.</h2><p>Try a higher fit-out or property budget, another business, or another city.</p><button class="primary" data-action="edit">Adjust my brief</button></div>` : ""}<div class="panel mt"><div class="row between wrap"><div><h3>What happens after you choose?</h3><p class="small mt">Six specialists investigate the same property. You can inspect every output, challenge the evidence and change the assumptions.</p></div>${badge("You’re choosing a review—not a purchase", "neutral")}</div></div>`;
}
function selected() {
  return properties.find((x) => x.id === state.property);
}
function currentUse() {
  const x = selected();
  if (x.uses.includes(state.chosenUse)) return state.chosenUse;
  return x.uses.find((u) => state.prefs.uses.includes(u)) || x.uses[0];
}
function startRun() {
  clearInterval(runTimer);
  state.completed = 0;
  state.running = true;
  state.agent = 0;
  state.contradictions = false;
  state.checks = [];
  state.money = { build: selected().fitout, bookings: 55, delay: 0, loan: 0 };
  render();
  runTimer = setInterval(() => {
    if (!state.running) return;
    state.completed = Math.min(6, state.completed + 1);
    if (state.completed === 6) {
      state.running = false;
      clearInterval(runTimer);
      toast("Demo review ready. Open each specialist’s findings.");
    }
    render();
  }, 1400);
}
function workspace() {
  const x = selected(),
    done = state.completed === 6;
  return `<div class="workspace-title"><div><div class="eyebrow">03 / PROPERTY WORKSPACE · ${x.city.toUpperCase()}</div><h1>${x.name}</h1><p>${x.suite} · ${state.prefs.tenure === "lease" ? "Lease scenario" : "Owner-operator purchase scenario"}</p><label class="form-field mt" style="max-width:300px;margin-bottom:0">Proposed business<select id="proposed-use">${x.uses.map((u) => `<option value="${u}" ${u === currentUse() ? "selected" : ""}>${labels[u]}</option>`).join("")}</select></label></div><div class="row"><button class="secondary" data-action="back">← Shortlist</button><button class="primary" data-action="save">Save scenario</button></div></div><div class="workspace-strip"><div><strong>${done ? "Your first review is ready." : state.running ? "Your specialists are on it." : "Review paused."}</strong><p>Simulated workflow · ${state.completed} of 6 outputs ready · no agents or provider calls are running</p></div><div class="progress-track" role="progressbar" aria-label="Simulated review progress" aria-valuenow="${state.completed}" aria-valuemin="0" aria-valuemax="6"><div class="progress-fill" style="width:${(state.completed / 6) * 100}%"></div></div><button class="secondary" data-action="${done ? "rerun" : "pause"}">${done ? "Run again" : state.running ? "Pause" : "Continue"}</button></div><div class="workspace-layout"><nav class="agents" aria-label="Specialist outputs">${agents.map(([icon, name, sub], i) => `<button class="agent ${state.agent === i ? "selected" : ""}" data-action="agent" data-index="${i}" aria-pressed="${state.agent === i}"><span class="agent-icon">${icon}</span><span><strong>${name}</strong><small class="${i === state.completed && state.running ? "running" : ""}">${i < state.completed ? "Output ready" : i === state.completed && state.running ? "Reviewing example evidence…" : "Queued"}</small></span><span class="dot ${i < state.completed ? "done" : i === state.completed && state.running ? "running" : ""}"></span></button>`).join("")}<div class="run-log">RUN / DEMO-${x.id.toUpperCase()}<br>INPUT / ${labels[currentUse()]}<br>SCOPE / ${state.prefs.tenure.toUpperCase()}<br>OUTPUT / ILLUSTRATIVE</div><a class="small muted" href="/pilot">Open original Tanner pilot ↗</a></nav><section class="panel agent-output"><div class="output-heading"><div><div class="eyebrow">SPECIALIST ${state.agent + 1} / ${agents[state.agent][2]}</div><h2>${agents[state.agent][1]}</h2><p>${agents[state.agent][3]}</p></div>${badge(state.agent < state.completed ? "Example output" : "Pending", state.agent < state.completed ? "amber" : "neutral")}</div>${state.agent < state.completed ? output() : `<div class="waiting"><span class="use-icon">${agents[state.agent][0]}</span><h3>${state.running ? "This specialist is queued." : "Continue the demo to see this output."}</h3><p>The simulated workflow reveals each specialist’s findings in sequence. Real orchestration will be connected later.</p><button class="secondary mt" data-action="finish">Show completed demo</button></div>`}</section></div>`;
}
function provenance(
  source,
  scope = "Subject suite",
  confidence = "Unverified",
) {
  return `<div class="provenance"><span>SOURCE / ${source}</span><span>SCOPE / ${scope}</span><span>DATE / not verified</span><span>STATUS / ${confidence}</span></div>`;
}
function finding(title, body, source, scope, flag = "Needs verification") {
  return `<article class="finding">${badge(flag, "amber")}<h3>${title}</h3><p>${body}</p>${provenance(source, scope)}</article>`;
}
function output() {
  switch (state.agent) {
    case 0:
      return evidenceOutput();
    case 1:
      return fitOutput();
    case 2:
      return locationOutput();
    case 3:
      return timelineOutput();
    case 4:
      return moneyOutput();
    case 5:
      return handoffOutput();
  }
}
function evidenceOutput() {
  const x = selected();
  return `<div class="notice">Illustrative report structure. ${x.real ? "Tanner identity and area notes are carried over from the earlier pilot; no fresh lookup has run." : "This example property is synthetic; no property evidence has been retrieved."}</div><div class="source-grid mt">${[
    [
      "CoStar",
      "Building & listing",
      x.real
        ? "69,500 SF building / 10,000 SF advertised suite"
        : "Building record, available suite and lease/sale terms",
    ],
    [
      "Matterport",
      "Interior & room",
      x.real
        ? "~6,383 SF warehouse room; scan named 9750 Tanner Rd"
        : "Scan address, room dimensions and original capture date",
    ],
    [
      "Vexcel",
      "Building exterior",
      "Correct footprint, roof, parking and capture date",
    ],
  ]
    .map(
      ([s, t, b]) =>
        `<div class="source-card"><span class="eyebrow">${s}</span><h3>${t}</h3><p>${b}</p><small>${x.real ? "Prior pilot context · dates not verified" : "Example source slot · not connected"}</small></div>`,
    )
    .join(
      "",
    )}</div><div class="mt">${finding(x.real ? "9700 ≠ 9750. Confirm the exact suite." : "Match the listing, scan and footprint.", x.real ? "The linked scan’s address differs from the building record. Asking rent and room measurements cannot yet be joined as one suite." : "A common street address is not enough. Confirm the building entrance, suite identifier and scan boundary before using measurements.", "CoStar + Matterport", "Building / advertised suite / scanned room")}${finding("Different dates can explain apparent contradictions.", "Check original scan provenance against listing and tenancy dates. An empty room in an old scan does not establish current vacancy.", "Attachment date + tenancy history", "Time-aware comparison")}</div><div class="actions"><p class="small">Request a focused cross-source audit.</p><button class="secondary" data-action="contradictions">${state.contradictions ? "Hide contradiction check" : "Run “lie detector” demo"}</button></div>${state.contradictions ? `<div class="notice mt"><strong>Illustrative contradiction audit</strong><ul><li>Identity: ${x.real ? "9700 / 9750 address mismatch needs broker confirmation." : "Suite match not established; request source IDs."}</li><li>Size: building area, suite area and room area are different scopes—not evidence of a false listing.</li><li>Occupancy: no dated tenancy/scan pair available; no conclusion.</li><li>Time: original capture date missing; comparison remains unresolved.</li></ul>No deception finding or automatic record correction.</div>` : ""}`;
}
const requirements = {
  pickleball: [
    "Unobstructed length, width and clear height",
    "Court run-off, circulation and support rooms",
    "Floor condition, lighting, ventilation and acoustics",
  ],
  gym: [
    "Floor load and vibration capacity",
    "Clear height, accessibility and changing rooms",
    "HVAC capacity and electrical service",
  ],
  restaurant: [
    "Kitchen hood, exhaust route and grease interceptor",
    "Gas, water, drainage and electrical capacity",
    "Restrooms, accessible seating and fire review",
  ],
  daycare: [
    "Outdoor space, secure access and circulation",
    "Occupant load, egress and accessible facilities",
    "Use licensing, restrooms and landlord consent",
  ],
  workshop: [
    "Room dimensions, occupant load and circulation",
    "Accessible entrance, toilets and after-hours access",
    "Power, ventilation and equipment-specific needs",
  ],
};
function fitOutput() {
  const u = currentUse();
  const x = selected();
  const live = x.costarId
    ? `<section class="live-fit panel" data-property="${x.costarId}" data-use="${u}"></section>`
    : "";
  return `${live}<div class="output-grid"><div><h3>${labels[u]} · fit questions</h3><ul class="list-plain">${requirements[u].map((r) => `<li>□ ${r}<span>Request measurements or plans before estimating capacity.</span></li>`).join("")}</ul>${finding("Area alone does not prove layout fit.", "An activity zone, circulation and support rooms must fit around columns and fixed services. Court count, seats or class capacity remains unverified.", "Matterport / measured plan", "Subject suite")}</div><div class="plan"><span class="eyebrow">CONCEPT ONLY · NOT TO SCALE</span><svg viewBox="0 0 330 200" role="img" aria-label="Illustrative space allocation: activity, circulation and support"><rect x="10" y="15" width="310" height="170" fill="white" stroke="#9cad8d" stroke-width="2"/><rect x="20" y="25" width="208" height="110" rx="3" fill="#d9e7bf"/><text x="124" y="84" text-anchor="middle" fill="#476044" font-size="13">Activity space</text><rect x="238" y="25" width="72" height="150" fill="#e5dfcf"/><text x="274" y="105" text-anchor="middle" fill="#746a53" font-size="11">Support</text><path d="M20 155H225" stroke="#bdccae" stroke-width="20"/><text x="124" y="159" text-anchor="middle" fill="#536c4a" font-size="11">Circulation</text></svg><p class="small">Illustrates what a future measured layout should account for. No geometry or capacity is inferred.</p></div></div><div class="grid2 mt">${finding("Exterior: roof, parking and loading", "Use the correct Vexcel footprint to inspect visible roof features, rooftop HVAC, docks and access. Verify allocated parking and vehicle turning access separately.", "Vexcel + CoStar", "Building / site")}${finding("Interior: visible condition clues", "Jev output will show room/photo references for water marks, damaged finishes, exits or equipment. Any apparent issue becomes an inspector question. No photo analysis ran.", "Jev + Matterport", "Room / photo")}</div><details class="mt"><summary>Additional inspection checklist</summary><ul class="list-plain"><li>Foundation, plumbing and sewer service<span>Request professional reports and utility records.</span></li><li>Pests, concealed moisture and electrical condition<span>Not established by an aerial or interior scan.</span></li><li>Three-phase power, HVAC and fire protection<span>Verify serving equipment, capacity and suite coverage.</span></li></ul></details>`;
}
function locationOutput() {
  const city = state.prefs.city;
  return `<div class="notice">No location datasets were queried. These are the questions and source slots the real workflow will populate for ${city}.</div><div class="grid2 mt">${finding("Who could use this business?", "Show catchment households, daytime population and relevant age/income distributions with dataset vintage and geographic scope. Validate demand through customer interviews and paid tests.", "Census ACS", "Catchment / tract")}${finding("What else is nearby?", "Map relevant businesses and complementary destinations. Verify whether a registered or mapped business is still operating; record hours and observed prices.", "Business registry / maps", "Trade area")}${finding(city === "Houston" ? "Flood and environmental context" : "Flood, wildfire and geological context", `Retrieve official mapped exposures for the exact parcel in ${city}. Nearby environmental records prompt further review; proximity alone does not establish contamination.`, "FEMA / EPA / local hazard maps", "Parcel / nearby area")}${finding("History and neighborhood context", "Review prior sales, permits and reported incident data with dates and limitations. No appreciation forecast or neighborhood “safe/unsafe” label.", "CoStar sales / public records", "Property / reporting area")}</div><div class="panel brief mt"><h3>Before calling this a good market</h3><p class="small">Test willingness to pay, peak-hour demand and competing capacity. Demographics describe an area; they do not prove bookings.</p></div>`;
}
function timelineOutput() {
  const x = selected(),
    u = currentUse();
  return `<div class="row between wrap"><div><h3>${x.months} months to opening · example planning case</h3><p class="small mt">${labels[u]} in ${x.city}. The future estimate should depend on use, location, existing condition and permit scope.</p></div>${badge(x.months <= state.prefs.target ? "Within your target" : "Later than your target", x.months <= state.prefs.target ? "" : "amber")}</div><div class="timeline">${[
    ["01", "Verify & scope", "Suite, plans, use"],
    ["02", "Design & approvals", "Landlord + authority"],
    ["03", "Build & equip", "Contractor schedule"],
    ["04", "Inspect & open", `Example: month ${x.months}`],
  ]
    .map(
      ([n, t, s]) =>
        `<div class="phase"><span>${n}</span><strong>${t}</strong><span>${s}</span></div>`,
    )
    .join(
      "",
    )}</div>${finding("Use and jurisdiction come first.", `Confirm the parcel authority, existing permitted use, proposed ${labels[u].toLowerCase()} use and approval path. ${x.city === "Houston" ? "Include deed restrictions, occupancy, parking and fire review." : "Include zoning/overlays, use classification and change-of-use review."}`, "Local planning / building authority", "Exact parcel and proposed use")}${finding("The schedule is a dependency chain, not a guarantee.", "A restaurant’s exhaust route, a daycare’s licensing, or a gym’s structural review can change scope and sequencing. The mock duration is a fixture—not an intelligent estimate or permit promise.", "Contractor quote + permit scope", "Project")}${finding("Insurance and landlord requirements", "Request requirements for the proposed occupancy, roof/exposure information, fire protection and operating hours. Cost and availability need a broker quote.", "Landlord + insurance broker", "Proposed operation")}<button class="primary mt" data-action="agent" data-index="4">Test a delayed opening →</button>`;
}
function finance(overrides = {}) {
  const p = state.prefs,
    x = selected(),
    m = { ...state.money, ...overrides },
    u = currentUse();
  const maxRevenue = {
    pickleball: 37800,
    gym: 40000,
    restaurant: 60000,
    daycare: 52000,
    workshop: 30000,
  }[u];
  const baseExpense = {
    pickleball: 7000,
    gym: 10000,
    restaurant: 24000,
    daycare: 23000,
    workshop: 6500,
  }[u];
  const monthlyProperty = p.tenure === "lease" ? x.rent + 2000 : 3500;
  const acquisition = p.tenure === "buy" ? x.price : 0;
  const debt = m.loan
    ? (m.loan * (0.1 / 12)) / (1 - Math.pow(1 + 0.1 / 12, -60))
    : 0;
  let balance = p.capital - acquisition + m.loan;
  const points = [balance],
    baseline = [p.capital - acquisition];
  const open = x.months + m.delay;
  for (let month = 1; month <= 24; month++) {
    balance -= monthlyProperty + debt + 2000;
    if (month > m.delay && month < open) balance -= m.build / (x.months - 1);
    if (month >= open)
      balance += (maxRevenue * m.bookings) / 100 - (baseExpense - 2000);
    points.push(Math.round(balance));
    baseline.push(Math.round(baseline.at(-1) - monthlyProperty + 18000 - 7000));
  }
  const low = Math.min(...points),
    breach = points.findIndex((v) => v < p.reserve),
    gap = Math.max(0, p.reserve - low);
  const breakeven = ((monthlyProperty + baseExpense + debt) / maxRevenue) * 100;
  return {
    points,
    baseline,
    low,
    breach,
    gap,
    open,
    breakeven,
    monthlyProperty,
    baseExpense,
    debt,
    maxRevenue,
  };
}
function chart(f) {
  const reserve = state.prefs.reserve,
    all = [...f.points, ...f.baseline, reserve, 0],
    lo = Math.min(...all),
    hi = Math.max(...all, 1),
    range = hi - lo || 1;
  const x = (i) => 65 + (i / 24) * 605,
    y = (v) => 245 - ((v - lo) / range) * 210;
  return `<svg class="cash-chart" viewBox="0 0 700 280" role="img" aria-label="Illustrative 24-month cash curve comparing current use and proposed use with minimum reserve">${[
    0, 1, 2, 3,
  ]
    .map((i) => {
      const v = lo + (range * i) / 3;
      return `<line x1="65" x2="670" y1="${y(v)}" y2="${y(v)}" stroke="#e5e9df"/><text x="57" y="${y(v) + 4}" text-anchor="end" font-size="10" fill="#8b9685">${cash(v)}</text>`;
    })
    .join(
      "",
    )}<line x1="65" x2="670" y1="${y(reserve)}" y2="${y(reserve)}" stroke="#b78b43" stroke-dasharray="5 5"/>${[f.baseline, f.points].map((s, i) => `<polyline points="${s.map((v, k) => `${x(k)},${y(v)}`).join(" ")}" fill="none" stroke="${i ? "#35694e" : "#a7b49b"}" stroke-width="3"/>`).join("")}${[0, 6, 12, 18, 24].map((i) => `<text x="${x(i)}" y="269" text-anchor="middle" font-size="10" fill="#8b9685">M${i}</text>`).join("")}</svg>`;
}
function affordability() {
  const feasible = finance({ build: 0 }).gap === 0;
  let low = 0,
    high = 10000000;
  if (feasible)
    for (let i = 0; i < 25; i++) {
      const mid = (low + high) / 2;
      if (finance({ build: mid }).gap === 0) low = mid;
      else high = mid;
    }
  const delays = Array.from({ length: 25 }, (_, delay) => delay).filter(
    (delay) => finance({ delay }).open <= 24 && finance({ delay }).gap === 0,
  );
  return {
    build: feasible ? Math.floor(low) : null,
    delay: delays.length ? Math.max(...delays) : null,
  };
}
function moneyOutput() {
  const f = finance(),
    m = state.money,
    p = state.prefs,
    a = affordability();
  return `<div class="notice">Illustrative frontend math—not the connected Nessie simulator. ${p.tenure === "buy" ? "Purchase price is paid in cash at month 0; no mortgage or closing costs are assumed." : "Tenant business revenue is compared against tenant costs."}</div><div class="grid3 mt"><div class="metric"><span>Lowest proposed cash</span><strong>${cash(f.low)}</strong><span>${f.breach < 0 ? "Reserve maintained" : `Below reserve in month ${f.breach}`}</span></div><div class="metric"><span>Funding gap vs reserve</span><strong>${cash(f.gap)}</strong><span>Reserve: ${cash(p.reserve)}</span></div><div class="metric"><span>Operating break-even</span><strong>${f.breakeven.toFixed(0)}%</strong><span>${currentUse() === "pickleball" ? "Paid court-hour occupancy" : "Of illustrative maximum revenue"}${f.breakeven > 100 ? " · exceeds capacity assumption" : ""}</span></div></div><div class="row wrap mt small muted"><span>━ Proposed use</span><span style="color:#a7b49b">━ Current-use placeholder</span><span style="color:#b78b43">┄ Reserve</span></div>${chart(f)}<form id="money-form" class="money-controls">${field("build", "Fit-out cost ($)", m.build, "number", "Example project cost; change to stress-test.", 0, 10000000)}${field("bookings", currentUse() === "pickleball" ? "Paid bookings (%)" : "Revenue utilization (%)", m.bookings, "number", "Percentage of illustrative maximum revenue.", 0, 100)}${field("delay", "Additional opening delay (months)", m.delay, "number", `Base opening: month ${selected().months}`, 0, 24)}<button class="primary" type="submit">Update cash comparison →</button></form><p class="small muted">Opening: month ${f.open}${f.open > 24 ? " (beyond chart)" : ""}. ${cash(f.monthlyProperty)}/mo property costs; ${cash(f.baseExpense - 2000)}/mo operations after opening + $2,000/mo carry throughout. Revenue at 100%: ${cash(f.maxRevenue)}/mo. ${currentUse() === "pickleball" ? "Assumes 3 courts × 12 h/day × 30 days × $35/h; court fit unverified." : ""}</p><details class="mt"><summary class="small">Baseline and financing assumptions</summary><p class="small mt">Current-use baseline: illustrative $18,000/month business revenue and $7,000 operations, starting in month 1, with the same property cost and acquisition. It is not a market rent estimate. Taxes beyond listed property costs, closing costs, exit value and appreciation are excluded.</p></details><div class="panel brief mt"><div class="row between wrap"><div><h3>${m.loan ? "Illustrative financing added" : "What would make it work?"}</h3><p class="small mt">Maximum affordable fit-out: <strong>${a.build === null ? "reserve fails even at $0" : cash(a.build)}</strong>. Maximum additional delay: <strong>${a.delay === null ? "none affordable" : a.delay + " months"}</strong>.</p><p class="small">One-variable sensitivity over the 24-month example, holding other inputs fixed; delay searched from 0–24 months, with opening inside the chart horizon.</p></div><button class="secondary" data-action="loan">${m.loan ? "Remove simulated loan" : "Illustrate loan for gap"}</button></div><p class="small mt">${m.loan ? `${cash(m.loan)} example loan · 10% APR · 60 months · ${cash(f.debt)}/month. Debt payments are included; a remaining gap may persist.` : "Example loan uses the current gap, 10% APR and a 60-month term. No lender offer, approval or Nessie transaction."}</p></div>`;
}
function checkItems() {
  return [
    [
      "Broker / landlord",
      "Identify the exact space",
      "Suite number, dated floor plan, scan boundary and current availability.",
      "Changes layout capacity and whether asking terms apply.",
    ],
    [
      "Architect / inspector",
      "Measure the fit and inspect condition",
      requirements[currentUse()].join("; ") +
        ". Include roof, services and visible condition follow-up.",
      "Changes usable capacity, build cost and insurance inputs.",
    ],
    [
      "Permitting authority",
      "Confirm the use and approval path",
      "Parcel jurisdiction, existing occupancy, required reviews and inspections.",
      "Changes design scope and opening sequence.",
    ],
    [
      "Contractor / utility",
      "Price the build and verify services",
      "Itemized quote, schedule dependencies, electrical/HVAC capacity and water/sewer records.",
      "Changes fit-out allowance and opening delay.",
    ],
    [
      "Operator / insurance broker",
      "Validate demand and monthly costs",
      "Paid-demand test, operating and insurance quotes, rent/NNN or purchase/financing terms.",
      "Changes revenue, recurring burn and reserve gap.",
    ],
  ];
}
function handoffOutput() {
  const f = finance();
  return `<div class="row between wrap"><div><h3>Investigate further. Resolve the fit first.</h3><p class="small mt">${labels[currentUse()]} is a hypothesis until the exact space and approval path are confirmed.</p></div>${badge("No investment recommendation", "neutral")}</div><div class="grid2 mt"><div class="metric"><span>Capital sensitivity</span><strong>${f.gap ? cash(f.gap) + " gap" : "Reserve holds"}</strong><span>Under the current illustrative inputs</span></div><div class="metric"><span>Priority one</span><strong>Confirm the suite</strong><span>Before estimating capacity or signing terms</span></div></div><div class="row between mt"><h3>Your next conversations</h3><span class="small muted">${state.checks.length} / 5 marked reviewed</span></div>${checkItems()
    .map(
      ([owner, title, request, impact], i) =>
        `<label class="check-item ${state.checks.includes(i) ? "done" : ""}"><input type="checkbox" data-check="${i}" ${state.checks.includes(i) ? "checked" : ""}><span><strong>${title}</strong><p>${request}</p><small>${owner} · ${impact}</small></span></label>`,
    )
    .join(
      "",
    )}<p class="small muted mt">Checkboxes track your review of this checklist; they do not verify a property fact.</p><div class="actions"><button class="secondary" data-action="save">Save inputs & checklist</button><button class="primary" data-action="download">Download handoff ↓</button></div><details class="mt"><summary class="small">Beyond this first workflow</summary><p class="small mt">Future applications: lender monitoring, insurance evidence packs, tax-appeal support, owner capital planning and records-freshness queues. These are roadmap concepts, not running features.</p></details>`;
}
function readBrief() {
  const f = document.getElementById("brief-form");
  if (!f) return;
  const d = new FormData(f);
  for (const k of [
    "fitout",
    "capital",
    "reserve",
    "propertyBudget",
    "target",
  ]) {
    const raw = d.get(k);
    if (raw !== null && raw !== "" && Number.isFinite(Number(raw)))
      state.prefs[k] = Number(raw);
  }
}
function navigate(view) {
  if (view === state.view) return;
  clearInterval(runTimer);
  state.running = false;
  state.view = view;
  render();
  window.scrollTo(0, 0);
}
app.addEventListener("submit", (e) => {
  e.preventDefault();
  if (e.target.id === "money-form") {
    for (const [k, v] of new FormData(e.target)) state.money[k] = Number(v);
    render();
    toast("Cash comparison updated.");
    return;
  }
  if (e.target.id === "login-form") {
    state.name =
      new FormData(e.target).get("name").trim().slice(0, 40) || "Alex";
    navigate("preferences");
  }
  if (e.target.id === "brief-form") {
    readBrief();
    if (state.prefs.mode === "known" && !state.prefs.uses.length) {
      document.getElementById("brief-error").textContent =
        "Choose at least one business, or switch to Open to suggestions.";
      return;
    }
    navigate("shortlist");
  }
});
app.addEventListener("input", (e) => {
  if (e.target.closest("#brief-form")) {
    readBrief();
    document.getElementById("brief-fitout").textContent = cash(
      state.prefs.fitout,
    );
    document.getElementById("brief-capital").textContent = cash(
      state.prefs.capital,
    );
  }
});
app.addEventListener("change", (e) => {
  if (e.target.id === "proposed-use") {
    state.chosenUse = e.target.value;
    startRun();
    toast("Started a new mock review for this business.");
    return;
  }
  if (e.target.matches("[data-check]")) {
    const i = Number(e.target.dataset.check);
    state.checks = e.target.checked
      ? [...new Set([...state.checks, i])]
      : state.checks.filter((x) => x !== i);
    render();
  }
});
app.addEventListener("click", (e) => {
  const b = e.target.closest("[data-action]");
  if (!b) return;
  const a = b.dataset.action;
  readBrief();
  if (a === "city") {
    state.prefs.city = b.dataset.value;
    render();
  }
  if (a === "mode") {
    state.prefs.mode = b.dataset.value;
    if (state.prefs.mode === "open") state.prefs.uses = [];
    render();
  }
  if (a === "use") {
    const u = b.dataset.value;
    state.prefs.uses = state.prefs.uses.includes(u)
      ? state.prefs.uses.filter((x) => x !== u)
      : [...state.prefs.uses, u];
    render();
  }
  if (a === "tenure") {
    if (state.prefs.tenure !== b.dataset.value) {
      state.prefs.tenure = b.dataset.value;
      state.prefs.propertyBudget =
        state.prefs.tenure === "buy" ? 2000000 : 12000;
    }
    render();
  }
  if (a === "edit") navigate("preferences");
  if (a === "back") navigate("shortlist");
  if (a === "nav")
    navigate(["preferences", "shortlist", "workspace"][Number(b.dataset.step)]);
  if (a === "select") {
    state.property = b.dataset.id;
    state.chosenUse = null;
    state.view = "workspace";
    window.scrollTo(0, 0);
    startRun();
  }
  if (a === "agent") {
    state.agent = Number(b.dataset.index);
    render();
  }
  if (a === "pause") {
    state.running = !state.running;
    render();
  }
  if (a === "finish") {
    clearInterval(runTimer);
    state.running = false;
    state.completed = 6;
    render();
  }
  if (a === "rerun") startRun();
  if (a === "contradictions") {
    state.contradictions = !state.contradictions;
    render();
  }
  if (a === "save") save();
  if (a === "loan") {
    const f = finance();
    if (!state.money.loan && !f.gap) {
      toast("There is no reserve gap in this example to finance.");
      return;
    }
    state.money.loan = state.money.loan ? 0 : Math.ceil(f.gap);
    render();
  }
  if (a === "logout") {
    navigate("login");
  }
  if (a === "resume") {
    try {
      const s = JSON.parse(localStorage.getItem("reuse-mock-v1"));
      if (!s || !properties.some((x) => x.id === s.property)) throw Error();
      state = { ...s, view: "workspace", running: false, completed: 6 };
      render();
    } catch {
      toast("Saved scenario could not be loaded. Start a new demo.");
    }
  }
  if (a === "download") {
    const text = [
      "REUSE — MOCK PROPERTY HANDOFF",
      selected().name,
      `Generated: ${new Date().toISOString()}`,
      `Business: ${labels[currentUse()]}`,
      `Brief: ${JSON.stringify(state.prefs, null, 2)}`,
      `Financial assumptions: ${JSON.stringify(state.money, null, 2)}`,
      `Illustrative results: ${JSON.stringify(finance(), null, 2)}`,
      "Sources: CoStar / Matterport / Vexcel / public records are planned source slots. Dates unverified. No fresh data retrieval or agent run.",
      ...checkItems().map(
        ([owner, title, request, impact], i) =>
          `${i + 1}. ${title}\nOwner: ${owner}\nRequest: ${request}\nImpact: ${impact}\nChecklist reviewed: ${state.checks.includes(i)}`,
      ),
      "All results are illustrative. No suitability, approval, financing or condition determination.",
    ].join("\n\n");
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `reuse-${state.property}-mock-handoff.txt`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("Mock handoff downloaded.");
  }
});
render();
