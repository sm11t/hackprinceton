(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const f = $("#f");
  const out = $("#out");
  const status = $("#status");
  const LA_DEMO = { market: "los_angeles", property_id: 4809147, budget: 900000, reserve: 50000, apr: 9, term_months: 60, business: "auto_repair" };
  let props = [];
  let lastRequest = null;

  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const money = (v) => (v == null || Number.isNaN(+v) ? "unknown" : (v < 0 ? "−$" : "$") + Math.abs(Math.round(v)).toLocaleString("en-US"));
  const tag = (kind) => `<span class="tag ${esc(kind)}">${esc({ listed: "CoStar", estimate: "estimate", user: "you", nessie: "Nessie", assumption: "assumption", unknown: "unknown", none: "none" }[kind] || kind)}</span>`;

  async function loadOptions(market, keep) {
    status.textContent = "Loading properties…";
    const r = await fetch(`/api/finance-lab/options?market=${encodeURIComponent(market)}`);
    const data = await r.json();
    if (data.error) { status.textContent = data.error; return; }
    props = data.properties;
    $("#props").innerHTML = props.map((p) => `<option value="${esc(p.address)} · ${p.property_id}">`).join("");
    const biz = f.business.value || keep?.business;
    const groups = {};
    data.businesses.forEach((b) => (groups[b.group || "Other"] ||= []).push(b));
    f.business.innerHTML = Object.entries(groups).map(([g, list]) => `<optgroup label="${esc(g)}">` +
      list.map((b) => `<option value="${esc(b.key)}">${esc(b.label)}${b.cost_benchmark ? "" : " (no cost benchmark)"}</option>`).join("") + "</optgroup>").join("");
    if (biz) f.business.value = biz;
    const want = keep?.property_id && props.find((p) => p.property_id === keep.property_id);
    selectProperty(want || props[0]);
    status.textContent = `${props.length} listed properties in ${data.label}.`;
  }

  function selectProperty(p) {
    if (!p) return;
    f.property_search.value = `${p.address} · ${p.property_id}`;
    f.property_search.dataset.id = p.property_id;
    f.suite.innerHTML = p.spaces.map((s) => `<option value="${esc(s.value)}">${esc(s.suite ? "Suite " + s.suite : "Space")} · ${Math.round(s.sf || 0).toLocaleString()} sq ft · ${s.monthly_rent ? money(s.monthly_rent) + "/mo " + (s.rent_kind === "estimate" ? "(estimate)" : "(listed)") : "rent unknown"}</option>`).join("");
  }

  f.property_search.addEventListener("change", () => {
    const id = Number((f.property_search.value.match(/(\d+)\s*$/) || [])[1]);
    const p = props.find((x) => x.property_id === id);
    if (p) selectProperty(p); else status.textContent = "Pick a property from the list (address · id).";
  });
  f.market.addEventListener("change", () => loadOptions(f.market.value));
  f.addEventListener("change", (e) => { if (e.target.name === "financing") $("#loanFields").hidden = f.financing.value !== "loan"; });

  function request() {
    const num = (n) => (f[n].value === "" ? null : Number(f[n].value));
    return {
      market: f.market.value, property_id: Number(f.property_search.dataset.id), suite: f.suite.value || null,
      business: f.business.value, budget: num("budget"), reserve: num("reserve"), monthly_rent: num("monthly_rent"),
      build_months: num("build_months"), delay: Number(f.delay.value), financing: f.financing.value,
      loan_amount: f.financing.value === "loan" ? num("loan_amount") : null, apr: num("apr"), term_months: num("term_months"),
      nessie_account: f.nessie_account.value.trim() || null, use_nessie_balance: f.use_nessie_balance.checked,
    };
  }

  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("#runBtn");
    lastRequest = request();
    if (!lastRequest.property_id) { status.textContent = "Pick a property first."; return; }
    btn.disabled = true; btn.textContent = "Running…"; status.textContent = "";
    try {
      const r = await fetch("/api/finance-lab/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(lastRequest) });
      const data = await r.json();
      if (data.error) { out.innerHTML = `<div class="panel"><div class="warn bad">${esc(data.error)}</div>${debug(lastRequest, data)}</div>`; return; }
      render(data);
    } catch (err) {
      out.innerHTML = `<div class="panel"><div class="warn bad">Request failed: ${esc(err.message)}</div></div>`;
    } finally { btn.disabled = false; btn.textContent = "Run Simulation"; }
  });

  $("#resetDemo").addEventListener("click", async () => {
    f.reset(); $("#loanFields").hidden = true;
    Object.entries(LA_DEMO).forEach(([k, v]) => { if (f[k] && k !== "business") f[k].value = v; });
    await loadOptions("los_angeles", LA_DEMO);
    f.business.value = LA_DEMO.business;
  });

  function debug(req, res) {
    return `<details><summary>Raw JSON / Debug</summary><p class="muted">POST /api/finance-lab/run</p><pre>${esc(JSON.stringify(req, null, 2))}</pre><p class="muted">Response</p><pre>${esc(JSON.stringify(res, null, 2))}</pre></details>`;
  }

  function chart(cashOnly, loan, reserve) {
    const series = [];
    if (cashOnly) series.push({ name: "Cash only (base)", color: "var(--accent)", data: cashOnly.cases.base.cash });
    if (cashOnly) series.push({ name: "Cash only (high cost)", color: "var(--warn)", data: cashOnly.cases.high.cash, dash: "4 3" });
    if (loan?.cases) series.push({ name: "With proposed loan (base)", color: "var(--good)", data: loan.cases.base.cash });
    if (!series.length) return "";
    const W = 720, H = 240, L = 70, R = 10, T = 10, B = 26;
    const all = series.flatMap((s) => s.data).concat([reserve || 0, 0]);
    const max = Math.max(...all), min = Math.min(...all);
    const x = (i) => L + (i / 12) * (W - L - R);
    const y = (v) => T + (1 - (v - min) / ((max - min) || 1)) * (H - T - B);
    const line = (d) => d.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
    const ticks = [min, (min + max) / 2, max];
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Cash balance over 12 months">
      ${ticks.map((t) => `<line x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}" stroke="var(--line)"/><text x="${L - 6}" y="${y(t) + 4}" text-anchor="end">${money(t)}</text>`).join("")}
      ${reserve ? `<line x1="${L}" x2="${W - R}" y1="${y(reserve)}" y2="${y(reserve)}" stroke="var(--bad)" stroke-dasharray="5 4"/><text x="${W - R}" y="${y(reserve) - 4}" text-anchor="end">reserve ${money(reserve)}</text>` : ""}
      ${min < 0 ? `<line x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}" stroke="var(--ink)" stroke-width=".6"/>` : ""}
      ${Array.from({ length: 13 }, (_, i) => `<text x="${x(i)}" y="${H - 8}" text-anchor="middle">${i}</text>`).join("")}
      ${series.map((s) => `<path d="${line(s.data)}" fill="none" stroke="${s.color}" stroke-width="2" ${s.dash ? `stroke-dasharray="${s.dash}"` : ""}/>`).join("")}
    </svg><div class="legend">${series.map((s) => `<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join("")}<span>month 0 = start, opening costs paid in month 1</span></div>`;
  }

  function render(d) {
    const c = d.capital, co = d.cash_only, loan = d.loan;
    const aff = { within: ["Within budget", "good"], stretch: ["Stretch", "bad"], over: ["Over budget", "bad"], rent_unknown: ["Rent unknown", "bad"], unknown: ["Unknown", "muted"] }[c.affordability] || [c.affordability, "muted"];
    const base = co?.cases.base;
    const html = [];
    html.push(`<div class="panel"><h2>${esc(d.business.label)} at ${esc(d.property.address)} <span class="muted">· CoStar ${d.property.property_id} · ${esc(d.property.type || "type not recorded")} · ${Math.round(d.property.space.sf || 0).toLocaleString()} sq ft</span></h2>
      ${d.warnings.map((w) => `<div class="warn">${esc(w)}</div>`).join("")}
      <div class="cards">
        <div class="card"><div class="k">Cash to open (base)</div><div class="v">${money(c.cash_to_open?.base)}</div><div class="s">low ${money(c.cash_to_open?.low)} · high ${money(c.cash_to_open?.high)}</div></div>
        <div class="card"><div class="k">Required incl. reserve</div><div class="v">${money(c.required_with_reserve?.base)}</div><div class="s">reserve ${money(c.reserve)}</div></div>
        <div class="card"><div class="k">Starting cash</div><div class="v">${money(c.budget)}</div><div class="s">${esc(d.provenance.budget.source)}</div></div>
        <div class="card"><div class="k">${c.funding_gap_base ? "Funding gap (base)" : "Headroom (base)"}</div><div class="v ${c.funding_gap_base ? "bad" : "good"}">${money(c.funding_gap_base || c.headroom_base)}</div><div class="s ${aff[1]}">${esc(aff[0])}</div></div>
        <div class="card"><div class="k">12-month cash, base</div><div class="v">${base ? money(base.cash[12]) : "unavailable"}</div><div class="s">${base ? (base.first_month_below_reserve ? `below reserve in month ${base.first_month_below_reserve}` : "stays above reserve") : esc(d.unavailable.join("; "))}</div></div>
        <div class="card"><div class="k">Opens</div><div class="v">${base ? "month " + base.opens : "—"}</div><div class="s">${base ? `delayed: month ${base.opens_if_delayed}` : ""}</div></div>
      </div>
      <div class="explain">${esc(c.explain)}${c.delayed_required ? ` · with the ${d.inputs.delay}-month delay, required(base) = ${money(c.delayed_required.base)}` : ""}${c.flip ? ` · ${esc(c.flip.text)}` : ""}</div></div>`);

    html.push(`<div class="panel"><h2>Not modeled</h2><div class="notmodeled">${d.not_modeled.map((x) => `<span>${esc(x)}: NOT MODELED</span>`).join("")}</div><p class="muted">${esc(d.reading)}</p></div>`);

    html.push(`<div class="panel"><h2>12-month cash balance</h2>${co ? chart(co, loan, c.reserve) : `<div class="warn">Unavailable: ${esc(d.unavailable.join("; "))}</div>`}
      ${co ? `<div class="scroll"><table><tr><th>Month</th>${base.cash.map((_, i) => `<th class="n">${i}</th>`).join("")}</tr>
        ${["low", "base", "high"].map((k) => `<tr><td>Cash only, ${k}</td>${co.cases[k].cash.map((v) => `<td class="n ${v < c.reserve ? "bad" : ""}">${money(v)}</td>`).join("")}</tr>`).join("")}
        ${loan?.cases ? `<tr><td>With loan, base</td>${loan.cases.base.cash.map((v) => `<td class="n ${v < c.reserve ? "bad" : ""}">${money(v)}</td>`).join("")}</tr>` : ""}
        <tr><td class="muted">Outflow, base</td><td></td>${base.outflows.map((v) => `<td class="n muted">${money(v)}</td>`).join("")}</tr></table></div>
        <p class="muted">Monthly bills charged: ${co.monthly_bills.map((b) => `${esc(b.payee)} ${money(b.monthly)}`).join(" · ")}${loan?.cases ? ` · loan payment ${money(loan.monthly_payment)}` : ""}. Upfront (month 1, base): ${money(base.upfront)}. Engine: ${esc(co.engine)}.</p>
        <p class="muted">${esc(co.note)}</p>` : ""}</div>`);

    if (loan) {
      html.push(`<div class="panel"><h2>Loan analysis <span class="tag">${esc(loan.status)}</span></h2>
        ${loan.note ? `<div class="warn">${esc(loan.note)}</div>` : ""}
        <div class="cards">
          <div class="card"><div class="k">Principal</div><div class="v">${money(loan.amount)}</div><div class="s">${esc(loan.amount_source)}</div></div>
          <div class="card"><div class="k">APR · term</div><div class="v">${loan.apr}% · ${loan.term_months} mo</div><div class="s">assumption</div></div>
          <div class="card"><div class="k">Monthly payment</div><div class="v">${money(loan.monthly_payment)}</div></div>
          <div class="card"><div class="k">Interest, first 12 months</div><div class="v">${money(loan.interest_12m)}</div><div class="s">principal repaid ${money(loan.principal_12m)}</div></div>
          <div class="card"><div class="k">Principal left after 12 months</div><div class="v">${money(loan.principal_remaining_12m)}</div></div>
          <div class="card"><div class="k">12-month cash with loan</div><div class="v">${loan.cases ? money(loan.cases.base.cash[12]) : "—"}</div><div class="s">${loan.cases ? (loan.cases.base.first_month_below_zero ? `below zero in month ${loan.cases.base.first_month_below_zero}` : loan.cases.base.first_month_below_reserve ? `below reserve in month ${loan.cases.base.first_month_below_reserve}` : "stays above reserve") : ""}</div></div>
        </div>
        <div class="explain">${esc(loan.explain)}</div><p class="muted">${esc(loan.label)}</p>
        ${d.inputs.nessie_account && loan.amount ? `<button type="button" id="createLoan">Create this loan in the Nessie sandbox…</button> <span class="muted" id="createStatus"></span>` : `<p class="muted">Enter a Nessie sandbox account to enable “Create this loan in the Nessie sandbox”. Running a scenario never creates one.</p>`}</div>`);
    }

    html.push(`<div class="panel"><h2>Where each input came from</h2><table><tr><th>Input</th><th>Value</th><th>Source</th></tr>
      ${Object.entries(d.provenance).map(([k, p]) => `<tr><td>${esc(k.replace(/_/g, " "))}</td><td class="n">${Array.isArray(p.value) ? (p.value.length ? p.value.map((b) => `${esc(b.payee)} ${money(b.monthly)}`).join("<br>") : "none") : (typeof p.value === "number" && k !== "build_months" ? money(p.value) : esc(p.value ?? "unknown"))}</td><td>${tag(p.kind)} ${esc(p.source)}</td></tr>`).join("")}
      <tr><td>building fit</td><td class="n">${esc(d.building_fit.status)}</td><td>${tag("listed")} CoStar facts vs the registry's space needs (neighborhood.building_fit)</td></tr></table></div>`);

    const ledger = d.ledger.lines || [];
    html.push(`<div class="panel"><h2>Startup cost ledger <span class="muted">(${esc(d.ledger.basis_quality || "none")})</span></h2>
      ${ledger.length ? `<div class="scroll"><table><tr><th>Line</th><th>How</th><th>Source</th><th class="n">Low</th><th class="n">Base</th><th class="n">High</th></tr>
      ${ledger.map((l) => `<tr><td>${esc(l.label)}</td><td class="muted">${esc(l.how)}</td><td>${esc(l.source)}</td><td class="n">${money(l.low)}</td><td class="n">${money(l.base)}</td><td class="n">${money(l.high)}</td></tr>`).join("")}
      <tr><th>Total</th><td></td><td></td><th class="n">${money(c.cash_to_open.low)}</th><th class="n">${money(c.cash_to_open.base)}</th><th class="n">${money(c.cash_to_open.high)}</th></tr></table></div>` : `<div class="warn">No itemized benchmark for this business.</div>`}
      ${d.ledger.note ? `<p class="muted">${esc(d.ledger.note)}</p>` : ""}
      <p class="muted">Sources: ${(d.ledger.sources || []).map((s) => s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.publisher_or_brand || s.url)}</a>` : esc(s.publisher_or_brand || "")).join(" · ") || "none"}</p></div>`);

    html.push(`<div class="panel">${debug(lastRequest, d)}</div>`);
    out.innerHTML = html.join("");

    const create = $("#createLoan");
    if (create) create.addEventListener("click", async () => {
      if (!confirm(`Create a PENDING sandbox loan of ${money(loan.amount)} at ${loan.apr}% for ${loan.term_months} months on Nessie account ${d.inputs.nessie_account}? This writes a record to the Nessie sandbox.`)) return;
      create.disabled = true;
      const r = await fetch("/api/finance-lab/create-loan", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: true, account_id: d.inputs.nessie_account, amount: loan.amount, apr: loan.apr, term_months: loan.term_months }) });
      const res = await r.json();
      $("#createStatus").textContent = res.error ? `Not created: ${res.error}` : `Created in Nessie sandbox: loan ${res.loan_id} (${res.status})${res.cached ? ", cached" : ""}`;
    });
  }

  $("#resetDemo").click();
})();
