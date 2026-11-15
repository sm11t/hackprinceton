"use strict";

const byId = (id) => document.getElementById(id);
const form = byId("review");
const statusLine = byId("status");
const reportBox = byId("report");
const submit = form.querySelector("button");
const query = new URLSearchParams(location.search);
const dollars = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
let catalog = [];
let suiteRequest = 0;
let reportRevision = 0;
let financialRevision = 0;
// Opened from a market-ranking link: preselect its suite and run the review once.
let pendingSuite = query.get("suite");
let pendingRun = query.get("run") === "1";

function node(parent, tag, text, className) {
  const child = document.createElement(tag);
  if (text !== undefined) child.textContent = text;
  if (className) child.className = className;
  parent.append(child);
  return child;
}

async function json(url, payload) {
  const response = await fetch(url, payload ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  } : undefined);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
}

async function updateSuites() {
  reportRevision++;
  reportBox.replaceChildren();
  const request = ++suiteRequest;
  const id = byId("property").value;
  submit.disabled = true;
  byId("suite").replaceChildren(new Option("Building only", ""));
  if (!id) return;
  try {
    const options = await json(`/api/maximo/suites?id=${encodeURIComponent(id)}`);
    if (request !== suiteRequest) return;
    for (const option of options) byId("suite").add(new Option(option.label, option.value));
    if (options.length === 1) byId("suite").value = options[0].value;
    if (pendingSuite && options.some((option) => option.value === pendingSuite)) byId("suite").value = pendingSuite;
    pendingSuite = null;
    statusLine.textContent = options.length > 1 ? "Select a suite to tie its fit and asking rent together." : "";
  } catch (error) {
    if (request === suiteRequest) statusLine.textContent = error.message;
  } finally {
    if (request === suiteRequest) submit.disabled = false;
    if (request === suiteRequest && pendingRun) { pendingRun = false; form.requestSubmit(); }
  }
}

function updateProperties(preferred) {
  const needle = byId("filter").value.trim().toLowerCase();
  const matches = catalog.filter((record) => record.city === byId("city").value &&
    record.address.toLowerCase().includes(needle));
  const select = byId("property");
  select.replaceChildren(...matches.map((row) => new Option(row.address, row.id)));
  if (matches.some((row) => row.id === preferred)) select.value = preferred;
  statusLine.textContent = matches.length ? "Loading advertised suites…" : "No matching addresses.";
  void updateSuites();
}

function sourceLink(parent, url) {
  if (typeof url !== "string" || !url.startsWith("https://")) return;
  const link = node(parent, "a", " Open source ↗");
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
}

function showRecords(parent, records) {
  const list = node(parent, "ul");
  for (const record of records) {
    const item = node(list, "li", record.note || record.fact.replaceAll("_", " "));
    const date = record.captured_at ? ` · record date ${record.captured_at}` : record.attachment_date ? ` · attachment ${record.attachment_date}; capture date unknown` : " · date unknown";
    node(item, "small", ` ${record.source}${date}`);
    sourceLink(item, record.evidence_url);
  }
}

function showClaims(parent, claims, sources) {
  for (const claim of claims) {
    const item = node(parent, "article");
    node(item, "p", claim.statement);
    const matches = sources.filter((source) => claim.source_ids.includes(source.source_id));
    if (matches.length) {
      const details = node(item, "details");
      node(details, "summary", "Sources");
      showRecords(details, matches);
    }
  }
}

function panel(parent, title) {
  const section = node(parent, "section", undefined, "panel");
  node(section, "h2", title);
  return section;
}

function showCash(parent, cash, report) {
  const summary = node(parent, "div");
  const controls = node(parent, "form", undefined, "cash-form");
  const fields = [
    ["starting_cash", "Starting cash ($)"], ["reserve", "Minimum reserve ($)"],
    ["build_cost", "Build-out cost ($)"], ["bookings", "Paid bookings / month"], ["booking_price", "Price per booking ($)"],
    ["permit_months", "Approval allowance (months)"], ["build_months", "Build-out (months)"], ["delay", "Extra opening delay (months)"],
    ["monthly_rent", "Base rent / month ($)"], ["monthly_carry", "Other holding costs / month ($)"],
    ["monthly_operating_cost", "Other operations / month ($)"], ["monthly_nnn", "NNN / CAM / month ($)"],
    ["monthly_payroll", "Payroll / month ($)"], ["monthly_utilities", "Utilities / month ($)"],
    ["monthly_insurance", "Insurance / month ($)"], ["monthly_maintenance", "Maintenance / month ($)"],
    ["monthly_taxes", "Property taxes / month ($)"], ["monthly_income", "Non-booking revenue / month ($)"], ["baseline_income", "Current-use revenue / month ($)"],
    ["upfront_cost", "Acquisition cash for purchase ($)"], ["loan_amount", "Hypothetical loan ($)"], ["loan_apr", "Loan APR (%)"], ["loan_term", "Loan term (months)"],
  ];
  function renderCash(data) {
    summary.replaceChildren();
    const c = data.conversion;
    const money = (value) => dollars.format(value);
    if (report.ownership === "buy" && !data.inputs.upfront_cost) {
      node(summary, "p", "Add acquisition cash before using this purchase scenario.");
    }
    node(summary, "p", "Primary curve and option ranking are unfinanced. Any loan below is a separate hypothetical sensitivity.");
    if (data.financing.result) node(summary, "p", `Hypothetical financing: ${money(data.financing.monthly_payment)} monthly payment; ${money(data.financing.result.lowest_cash)} lowest cash after proceeds and payments. No loan offer or transaction.`);
    node(summary, "p", `Month ${data.timeline.opening_month} opening · ${money(c.lowest_cash)} low point in month ${c.lowest_month}.`);
    node(summary, "p", c.first_month_below_reserve === null
      ? "The conversion stays at or above reserve in this scenario."
      : `The conversion crosses reserve in month ${c.first_month_below_reserve}. It needs ${money(c.extra_funding_needed)} more cash to maintain reserve.`);
    node(summary, "p", `With three more months of delay: ${money(data.stress.extra_funding_needed)} reserve gap. Operating break-even: ${data.boundaries.break_even_monthly_bookings ?? "unavailable"} bookings per month.`);
    if (data.cash_at_opening !== undefined) {
      node(summary, "p", `${money(data.cash_at_opening)} immediately before opening · First negative cash month: ${data.runway_months ?? "none within horizon"}.`);
      node(summary, "p", data.revenue_basis);
      const sensitivity = node(summary, "details");
      node(sensitivity, "summary", "Low/base/high and downside sensitivities");
      for (const [name, series] of Object.entries({...data.cost_cases, ...data.sensitivities})) {
        node(sensitivity, "p", `${name.replaceAll("_", " ")}: ${money(series.lowest_cash)} lowest cash · ${money(series.extra_funding_needed)} reserve gap.`);
      }
    }
    node(summary, "p", `${data.buyer_source}. ${money(data.bank_monthly_bills)} per month in bank bills included. Count each rent or holding expense once.`);
    const openingCosts = node(summary, "details");
    node(openingCosts, "summary", "Where cash goes before opening");
    const costs = node(openingCosts, "ul");
    const values = data.inputs;
    node(costs, "li", `Build-out: ${money(values.build_cost)} (editable allowance; get itemized bids for design, building work and equipment).`);
    node(costs, "li", `Upfront deal cash: ${money(values.upfront_cost)} (editable allowance).`);
    for (const phase of data.timeline.phases) {
      node(costs, "li", `Months ${phase.start_month}–${phase.end_month}: ${phase.name}. Holding costs continue through both phases.`);
    }
    node(costs, "li", `Pre-opening outflow in the chart: ${money(values.upfront_cost + data.conversion.rows
      .filter((row) => row.month < data.timeline.opening_month).reduce((sum, row) => sum + row.outflow, 0))}.`);
    drawCash(summary, data);
  }
  renderCash(cash);
  if (report.ownership === "lease") node(parent, "p", `Starting rent input: ${cash.rent_source ?? "Editable assumption"}.`);
  for (const [name, label] of fields) {
    if (name === "monthly_rent" && report.ownership === "buy") continue;
    const input = node(node(controls, "label", label), "input");
    input.name = name;
    input.type = "number";
    input.min = "0";
    input.step = name.endsWith("months") || name === "delay" ? "1" : "any";
    input.required = true;
    input.value = (cash.planning_inputs ?? cash.inputs)[name];
    if (name === "build_cost" && Object.keys(report.costs?.overrides ?? {}).length) {
      input.disabled = true;
      input.title = "Individual cost overrides control the total; edit the itemized ledger.";
    }
    if (name === "starting_cash" && cash.buyer_source.startsWith("Nessie")) {
      input.value = cash.starting_cash;
      input.disabled = true;
    }
  }
  const run = node(controls, "button", "Update cash curve", "primary");
  const message = node(parent, "p", "");
  message.setAttribute("role", "status");
  controls.addEventListener("submit", async (event) => {
    event.preventDefault();
    run.disabled = true;
    message.textContent = "";
    try {
      const inputs = { ...(cash.planning_inputs ?? cash.inputs), ...Object.fromEntries([...new FormData(controls)].map(([k, v]) => [k, Number(v)])) };
      if (report.costs) await updateFinancials(report, inputs, report.costs.overrides);
      else renderCash(await json("/api/maximo/cash", { inputs, use: report.proposed_use, ownership: report.ownership, scenario_only: true }));
      message.textContent = "Cash curve and modeled opening updated.";
    } catch (error) {
      message.textContent = error.message;
    } finally {
      run.disabled = false;
    }
  });
}

async function updateFinancials(report, inputs, overrides) {
  const revision = reportRevision;
  const financialRequest = ++financialRevision;
  const result = await json("/api/maximo/estimate", {use: report.proposed_use, ownership: report.ownership,
    inputs, cost_overrides: overrides, compare_uses: report.alternatives.all_options.filter(o => !["excluded", "blocked"].includes(o.screen_status ?? o.status)).map(o => o.use)});
  if (revision !== reportRevision || financialRequest !== financialRevision) return;
  const priorInputs = report.money?.planning_inputs ?? report.planning_inputs;
  const priorRentSource = report.money?.rent_source;
  report.money = report.eligibility.physical_fit_blocked ? null : result.money;
  if (report.money) report.money.rent_source = inputs.monthly_rent === priorInputs?.monthly_rent && priorRentSource ? priorRentSource : "User-edited scenario base rent; not a new listing quote";
  report.costs = result.costs;
  report.planning_inputs = inputs;
  byId("budget").value = inputs.starting_cash;
  byId("reserve").value = inputs.reserve;
  report.finance_status = result.status;
  for (const option of report.alternatives.all_options) {
    const comparison = result.comparisons[option.use];
    if (!comparison) continue;
    Object.assign(option, comparison);
    option.status = comparison.cash_required === null ? "blocked" : comparison.shortfall ? "unaffordable" : "conditional";
    option.budget_fit = comparison.cash_required === null ? "unknown cost lines" : comparison.shortfall ? "shortfall under planning allowances" : "within budget under unverified allowances";
    option.key_blocker = option.status === "conditional" ? option.blockers[0] : "Budget or cost information prevents commitment.";
  }
  report.alternatives.options = report.alternatives.all_options.filter(o => o.status === "conditional")
    .sort((a,b) => (a.reserve_gap ?? 0)-(b.reserve_gap ?? 0) || a.cash_required-b.cash_required).slice(0,3);
  report.alternatives.recommendation = report.alternatives.options.length ? `Investigate ${report.alternatives.options[0].use} first under these assumptions; confirm scope, permission and demand.` : "Do not commit: no screened option fits the current planning budget.";
  reportBox.replaceChildren(); display(report);
  statusLine.textContent = "Recommendation, ledger, cash and opening assumptions recalculated. No new external research performed.";
}

function showCosts(parent, report) {
  const ledger = report.costs;
  const section = panel(parent, "Itemized cash to open");
  node(section, "p", ledger.basis);
  const totals = node(section, "div");
  function totalText(data) {
    totals.replaceChildren();
    for (const key of ["low", "base", "high"]) {
      const t = data.totals[key];
      node(totals, "p", `${key.toUpperCase()}: ${t.cash_required === null ? "Incomplete costs" : dollars.format(t.cash_required) + " including reserve"} · Shortfall: ${t.shortfall === null ? "unknown" : dollars.format(t.shortfall)}`);
    }
    node(totals, "p", `Monthly preopening burn: ${dollars.format(data.monthly_preopening_burn)}. Monthly operating outflow: ${dollars.format(data.monthly_operating_burn)} before revenue. Verify NNN/CAM and missing operating items.`);
  }
  totalText(ledger);
  const controls = node(section, "form", undefined, "ledger-form");
  const details = node(controls, "details");
  node(details, "summary", "Edit low / base / high allowances and responsibility");
  for (const line of ledger.lines) {
    const row = node(details, "fieldset");
    node(row, "legend", `${line.label} · ${line.classification}`);
    node(row, "small", `${line.quantity} ${line.unit} · ${line.source} · ${line.geography} · No verified quote date`);
    for (const key of ["low", "base", "high"]) {
      const input = node(node(row, "label", `${line.label} ${key} ($)`), "input");
      input.name = `${line.id}:${key}`; input.type = "number"; input.min = "0"; input.step = "any";
      input.value = line.amounts[key] ?? "";
    }
    const payer = node(node(row, "label", `${line.label} paid by`), "select");
    payer.name = `${line.id}:payer`;
    for (const name of ["tenant", "buyer", "landlord"]) payer.add(new Option(name, name));
    payer.value = line.payer;
  }
  const run = node(controls, "button", "Recalculate itemized costs", "secondary");
  const message = node(section, "p", "");
  controls.addEventListener("submit", async (event) => {
    event.preventDefault(); run.disabled = true;
    const overrides = {};
    for (const [name, value] of new FormData(controls)) {
      const [id, key] = name.split(":");
      (overrides[id] ??= {})[key] = key === "payer" ? value : value === "" ? null : Number(value);
    }
    try {
      await updateFinancials(report, report.planning_inputs ?? report.money.planning_inputs, overrides);
      message.textContent = "Cost ledger and cash updated. These remain unverified planning allowances.";
    } catch(error) { message.textContent = error.message; }
    finally { run.disabled = false; }
  });
}

function drawCash(parent, cash) {
  const lines = [
    [cash.baseline, "#55768a", "Current use"],
    [cash.conversion, "#148469", "Conversion"],
    [cash.stress, "#b75a2c", "+3 months"],
  ];
  const values = lines.flatMap(([series]) => [series.initial_cash, ...series.rows.map((row) => row.cash)]);
  const low = Math.min(cash.inputs.reserve, ...values), high = Math.max(cash.inputs.reserve, ...values);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 640 225");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Monthly cash for current use, conversion and a three-month delay, compared with minimum reserve");
  svg.classList.add("cash-chart");
  function shape(tag, attrs) {
    const child = document.createElementNS(svg.namespaceURI, tag);
    for (const [key, value] of Object.entries(attrs)) child.setAttribute(key, value);
    svg.append(child);
    return child;
  }
  const x = (month) => 20 + 600 * month / cash.inputs.months;
  const y = (value) => 195 - 170 * (value - low) / Math.max(1, high - low);
  shape("line", { x1: x(0), x2: x(cash.inputs.months), y1: y(cash.inputs.reserve), y2: y(cash.inputs.reserve), stroke: "#626b62", "stroke-dasharray": "6 4" });
  for (const [series, color] of lines) {
    const points = [[0, series.initial_cash], ...series.rows.map((row) => [row.month, row.cash])];
    shape("polyline", { points: points.map(([t, v]) => `${x(t)},${y(v)}`).join(" "), fill: "none", stroke: color, "stroke-width": 3 });
  }
  shape("text", { x: 20, y: 219 }).textContent = "Month 0";
  shape("text", { x: 620, y: 219, "text-anchor": "end" }).textContent = `Month ${cash.inputs.months}`;
  const legend = node(parent, "div", undefined, "cash-legend");
  for (const [, color, label] of lines) node(legend, "strong", label).style.color = color;
  node(legend, "span", `Dashed: reserve ${dollars.format(cash.inputs.reserve)}`);
  parent.append(svg);
}

function display(report) {
  const hero = panel(reportBox, report.address);
  node(hero, "p", `${report.scope_label} · ${report.proposed_use} · ${report.ownership}`);
  node(hero, "h3", report.eligibility.status === "conditional" ? report.headline : report.eligibility.headline);
  node(hero, "p", report.eligibility.reason);
  node(hero, "p", report.source_mode);
  node(hero, "h3", report.alternatives.recommendation);
  node(hero, "p", report.alternatives.reversal);
  const decisive = panel(reportBox, "Three decision-changing findings");
  const findings = report.eligibility.status !== "conditional" ? report.eligibility.records.slice(0,2).map(r => ({title:r.fact.replaceAll("_"," "),note:r.note})) : report.evidence_overview.slice(0, 2);
  if (report.costs) findings.push({title: "Budget under planning allowances", note: report.costs.totals.base.shortfall === null ? "Cost lines are incomplete." : `${dollars.format(report.costs.totals.base.shortfall)} shortfall to open and retain reserve. Costs and revenue remain unverified.`});
  else findings.push({title: "Eligibility", note: report.eligibility.reason});
  for (const finding of findings.slice(0,3)) { node(decisive, "h3", finding.title); node(decisive, "p", finding.note); }
  const alternativePanel = panel(reportBox, "Alternatives within your budget");
  node(alternativePanel, "p", report.alternatives.ranking_basis);
  for (const option of report.alternatives.options) {
    const card = node(alternativePanel, "article");
    node(card, "h3", option.use);
    node(card, "p", `${option.status} · Budget: ${option.budget_fit} · Physical fit: ${option.physical_fit}`);
    node(card, "p", `Key blocker: ${option.key_blocker}`);
    node(card, "p", `Cash to open incl. reserve: ${option.cash_required === null ? "unknown" : dollars.format(option.cash_required)} · Modeled opening month: ${option.opening_delay ?? "unknown"} · Reserve gap: ${option.reserve_gap == null ? "unknown" : dollars.format(option.reserve_gap)}.`);
    node(card, "p", option.cost_basis ?? "Unverified planning scenario");
    node(card, "p", `Permission: ${option.permission} · Demand: ${option.demand_confidence} · Evidence: ${option.evidence_quality}`);
    node(card, "p", `Next: ${option.next_check}`);
    const model = node(card, "button", "Model this use", "secondary");
    model.addEventListener("click", () => { byId("use").value = option.use; form.requestSubmit(); });
  }
  const excluded = node(alternativePanel, "details");
  node(excluded, "summary", "All screened uses and exclusions");
  for (const option of report.alternatives.all_options) node(excluded, "p", `${option.use}: ${option.status}. ${option.key_blocker}`);
  const nextChecks = document.createElement("section");
  nextChecks.className = "panel"; node(nextChecks, "h2", "Verify next");
  const list = node(nextChecks, "ol");
  for (const action of report.actions) {
    const item = node(list, "li");
    node(item, "strong", `${action.title} · ${action.owner}`);
    node(item, "p", action.request);
  }
  const media = node(hero, "details");
  node(media, "summary", "Open aerial and linked tour");
  media.addEventListener("toggle", () => {
    if (!media.open || media.querySelector(".property-views")) return;
    const views = node(media, "div", undefined, "property-views");
    const image = node(views, "img");
    image.alt = "Vexcel aerial at the building pin";
    image.src = `/aerial?id=${report.property_id}`;
    image.addEventListener("error", () => image.replaceWith(document.createTextNode("Aerial unavailable.")));
    if (report.tour?.startsWith("https://my.matterport.com/show/?m=")) {
      const tour = node(views, "iframe");
      tour.title = "Linked Matterport tour. Suite coverage requires verification.";
      tour.src = report.tour;
    }
  });
  const columns = node(reportBox, "div", undefined, "review-columns");
  const evidence = panel(columns, "Evidence and identity");
  const ranked = node(evidence, "ul");
  for (const issue of report.evidence_overview.slice(0, 3)) {
    const item = node(ranked, "li");
    node(item, "strong", issue.title);
    node(item, "p", issue.note);
  }
  if (!ranked.childElementCount) node(evidence, "p", "Available comparisons found no decision-changing discrepancies. Verify coverage before relying on them.");
  const all = node(evidence, "details");
  node(all, "summary", "Source records by issue");
  const issues = new Map();
  for (const record of report.identity.records) {
    if (!issues.has(record.fact)) issues.set(record.fact, []);
    issues.get(record.fact).push(record);
  }
  for (const [fact, rows] of issues) {
    const group = node(all, "details");
    node(group, "summary", `${fact.replaceAll("_", " ")} (${rows.length})`);
    showRecords(group, rows);
  }
  if (report.costs) showCosts(reportBox, report);
  if (!report.money) {
    const held = panel(reportBox, "Cash modeling paused");
    node(held, "p", report.finance_status === "incomplete_costs" ? "Complete missing cost lines in the ledger before projecting cash." : "Verify that the space is available and suitable before using cash estimates for this address.");
    const explore = node(held, "button", "Open a hypothetical cash scenario", "secondary");
    explore.addEventListener("click", async () => {
      explore.disabled = true;
      try {
        const cash = await json("/api/maximo/cash", {
          use: report.proposed_use, ownership: report.ownership, scenario_only: true, inputs: {},
        });
        explore.remove();
        node(held, "p", "Generic planning example. These assumptions do not establish costs, rent, demand or suitability for this property.");
        showCash(held, cash, {...report, costs: null, planning_inputs: null});
      } catch (error) {
        node(held, "p", error.message);
        explore.disabled = false;
      }
    });
  } else {
    const cash = panel(reportBox, "Conditional cash scenario");
    node(cash, "p", "Runway under editable assumptions. Build-out costs, bookings and approval durations need independent estimates; a surplus does not establish site feasibility.");
    showCash(cash, report.money, report);
  }
  if (!report.space) {
    reportBox.append(nextChecks);
    const raw = node(reportBox, "details"); node(raw, "summary", "Full identity evidence"); raw.append(columns);
    return;
  }
  const space = panel(columns, "Space and condition");
  const fitLabel = {
    supported: "Available measurements support initial screening. Verify the layout and overhead obstructions.",
    investigate: "Fit remains unverified. Ask for a measured plan and usable dimensions for the selected space.",
    does_not_fit: "Available measurements flag a fit problem. Review the limiting evidence before spending on this conversion.",
  };
  node(space, "p", fitLabel[report.space.verdict]);
  const decisions = report.space.records.filter((row) => row.status === "conflict" ||
    (row.status === "unknown" && ["footprint_vs_costar_floor", "roof_height_ft"].includes(row.fact)));
  showRecords(space, decisions.slice(0, 2));
  const keyFacts = new Set(["ceiling_height_ft", "listed_space_sf", "roof_defects"]);
  showRecords(space, [
    ...report.identity.records.filter((row) => row.fact === "ceiling_height_ft").slice(0, 3),
    ...report.space.records.filter((row) => keyFacts.has(row.fact)),
  ]);
  if (report.unavailable_sources.length) node(space, "p", `Unavailable evidence: ${report.unavailable_sources.join(", ")}.`);
  const fit = node(space, "details");
  node(fit, "summary", "Fit, building and inspection evidence");
  showRecords(fit, report.space.records);
  const deal = panel(columns, "Listing and deal facts");
  if (!report.deal.records.length) node(deal, "p", "The kit returned no listing or sale records.");
  if (report.deal.purchase_note) node(deal, "p", report.deal.purchase_note);
  const currentFacts = report.deal.records.filter((row) => row.fact.startsWith(report.ownership === "lease" ? "lease_" : "sale_"));
  if (!currentFacts.length) node(deal, "p", "Asking terms for this deal type are unverified.");
  showRecords(deal, currentFacts.slice(0, 4));
  const history = node(deal, "details");
  node(history, "summary", "All listing records and sale history");
  showRecords(history, report.deal.records);
  const approvals = panel(reportBox, "Approvals critical path");
  node(approvals, "p", report.approvals.summary);
  showClaims(approvals, report.approvals.findings, report.approvals.evidence);
  if (report.approvals.path) {
    const path = report.approvals.path;
    node(approvals, "p", `Parcel: ${JSON.stringify(path.parcel_ids)} · ${path.parcel_identity_status}. Jurisdiction ${path.jurisdiction_verified ? "boundary verified" : "unverified"}.`);
    node(approvals, "p", path.summary);
    const steps = node(approvals, "ol");
    for (const step of path.critical_path) {
      const item = node(steps, "li");
      node(item, "strong", step.title);
      node(item, "p", `${step.status} · ${step.authority}. Timing: ${step.time_provenance}.`);
      node(item, "p", step.next_action);
      sourceLink(item, step.official_source_url);
    }
  }
  const area = panel(reportBox, "Location and demand");
  if (report.location.status === "saved") node(area, "p", "Saved public research capture from the observation dates below; not refreshed for this run.");
  if (!["complete", "saved"].includes(report.location.status)) {
    node(area, "p", report.location.status === "offline" ? "Offline mode skipped live location research." : "Live location research was unavailable for this run.");
  }
  showClaims(area, report.location.findings, report.location.sources);
  if (report.location.sources.some((row) => row.source_id === "fema-effective-zone" &&
      Array.isArray(row.value) && row.value.some((zone) => /^(A|V)/.test(zone.FLD_ZONE ?? "")))) {
    node(area, "p", "The address point is in a FEMA A or V zone. Verify parcel coverage and ask an insurance broker for terms before adding a premium to cash costs.");
  }
  for (const [use, result] of Object.entries(report.demand_by_use ?? {})) {
    node(area, "h3", use);
    node(area, "p", result.status);
    node(area, "p", result.limitation);
    for (const competitor of result.competitors) {
      const card = node(area, "article");
      node(card, "strong", competitor.name);
      node(card, "p", competitor.address);
      node(card, "p", `Observed ${competitor.observed_at} · ${competitor.distance_miles === null ? "Distance unverified" : competitor.distance_miles + " miles straight-line"}. ${competitor.catchment}`);
      node(card, "p", `Published price: ${competitor.published_price ?? "unverified"}. Publication date: ${competitor.publication_date ?? "unknown"}.`);
      sourceLink(card, competitor.evidence_url);
    }
  }
  node(area, "p", "Paid demand at this site still needs a trial or direct customer evidence. ACS and FEMA are context, not willingness to pay.");
  reportBox.append(nextChecks);
  const raw = node(reportBox, "details"); node(raw, "summary", "Space, listing and full evidence"); raw.append(columns);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const suite = byId("suite").value;
  const inputs = {starting_cash: Number(byId("budget").value), reserve: Number(byId("reserve").value)};
  if (query.has("fitout") && Number.isFinite(Number(query.get("fitout")))) inputs.build_cost = Number(query.get("fitout"));
  const controls = [...form.elements];
  controls.forEach((control) => { control.disabled = true; });
  reportBox.replaceChildren();
  statusLine.textContent = "Checking property evidence, approvals, cash and local demand…";
  try {
    const report = await json("/api/maximo/run", {
      property_id: byId("property").value, suite, use: byId("use").value, ownership: byId("ownership").value, inputs,
    });
    display(report);
    statusLine.textContent = report.money ? "Review ready." : "Eligibility needs review.";
  } catch (error) {
    statusLine.textContent = error.message;
  } finally {
    controls.forEach((control) => { control.disabled = false; });
  }
});

byId("city").addEventListener("change", () => { byId("filter").value = ""; updateProperties(); });
byId("filter").addEventListener("input", () => updateProperties(byId("property").value));
byId("property").addEventListener("change", updateSuites);
json("/api/location/properties").then((rows) => {
  catalog = rows;
  if (query.has("capital")) byId("budget").value = query.get("capital");
  if (query.has("reserve")) byId("reserve").value = query.get("reserve");
  const id = query.get("property") ?? "23296";
  const initial = catalog.find((row) => row.id === id);
  if (initial) byId("city").value = initial.city;
  if (query.get("ownership") === "buy") byId("ownership").value = "buy";
  if ([...byId("use").options].some((option) => option.value === query.get("use"))) byId("use").value = query.get("use");
  updateProperties(id);
}).catch((error) => { statusLine.textContent = error.message; });
