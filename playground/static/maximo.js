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
  const request = ++suiteRequest;
  const id = byId("property").value;
  submit.disabled = true;
  byId("suite").replaceChildren(new Option("Building only", ""));
  if (!id) return;
  try {
    const options = await json(`/api/maximo/suites?id=${encodeURIComponent(id)}`);
    if (request !== suiteRequest) return;
    for (const suite of options) byId("suite").add(new Option(suite, suite));
    if (options.length === 1) byId("suite").value = options[0];
    statusLine.textContent = options.length > 1 ? "Select a suite to tie its fit and asking rent together." : "";
  } catch (error) {
    if (request === suiteRequest) statusLine.textContent = error.message;
  } finally {
    if (request === suiteRequest) submit.disabled = false;
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
    const date = record.captured_at ? ` · ${record.captured_at}` : "";
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
    ["monthly_operating_cost", "Conversion operations / month ($)"], ["baseline_income", "Current-use revenue / month ($)"],
    ["upfront_cost", "Upfront deal cash ($)"],
  ];
  function renderCash(data) {
    summary.replaceChildren();
    const c = data.conversion;
    const money = (value) => dollars.format(value);
    if (report.ownership === "buy" && !data.inputs.upfront_cost) {
      node(summary, "p", "Add acquisition cash before using this purchase scenario.");
    }
    node(summary, "p", `Month ${data.timeline.opening_month} opening · ${money(c.lowest_cash)} low point in month ${c.lowest_month}.`);
    node(summary, "p", c.first_month_below_reserve === null
      ? "The conversion stays at or above reserve in this scenario."
      : `The conversion crosses reserve in month ${c.first_month_below_reserve}. It needs ${money(c.extra_funding_needed)} more cash to maintain reserve.`);
    node(summary, "p", `With three more months of delay: ${money(data.stress.extra_funding_needed)} reserve gap. Operating break-even: ${data.boundaries.break_even_monthly_bookings ?? "unavailable"} bookings per month.`);
    node(summary, "p", `${data.buyer_source}. ${money(data.bank_monthly_bills)} per month in bank bills included. Count each rent or holding expense once.`);
    drawCash(summary, data);
  }
  renderCash(cash);
  if (report.ownership === "lease") node(parent, "p", `Starting rent input: ${cash.rent_source}.`);
  for (const [name, label] of fields) {
    if (name === "monthly_rent" && report.ownership === "buy") continue;
    const input = node(node(controls, "label", label), "input");
    input.name = name;
    input.type = "number";
    input.min = "0";
    input.step = name.endsWith("months") || name === "delay" ? "1" : "any";
    input.required = true;
    input.value = cash.inputs[name];
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
      const inputs = { ...cash.inputs, ...Object.fromEntries([...new FormData(controls)].map(([k, v]) => [k, Number(v)])) };
      renderCash(await json("/api/maximo/cash", { inputs, use: report.proposed_use, ownership: report.ownership }));
      message.textContent = "Cash curve and modeled opening updated.";
    } catch (error) {
      message.textContent = error.message;
    } finally {
      run.disabled = false;
    }
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
  node(hero, "p", `${report.suite ? "Suite " + report.suite : "Building scope"} · ${report.proposed_use} · ${report.ownership}`);
  node(hero, "h3", report.headline);
  const list = node(hero, "ol");
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
  showCash(panel(reportBox, "Money and runway"), report.money, report);
  const columns = node(reportBox, "div", undefined, "review-columns");
  const evidence = panel(columns, "Evidence and identity");
  node(evidence, "p", `${report.identity.conflicts} evidence conflicts across linked records.`);
  const conflicts = report.identity.records.filter((row) => row.status === "conflict");
  showRecords(evidence, conflicts);
  const all = node(evidence, "details");
  node(all, "summary", "All identity, size and occupancy checks");
  showRecords(all, report.identity.records);
  const space = panel(columns, "Space and condition");
  node(space, "p", "Verify usable dimensions and obstructions on a measured plan before estimating layout.");
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
  showRecords(deal, report.deal.records);
  const approvals = panel(columns, "Approvals and timeline");
  node(approvals, "p", report.approvals.summary);
  showClaims(approvals, report.approvals.findings, report.approvals.evidence);
  const area = panel(reportBox, "Location and demand");
  if (report.location.status !== "complete") {
    node(area, "p", report.location.status === "offline" ? "Offline mode skipped live location research." : "Live location research was unavailable for this run.");
  }
  showClaims(area, report.location.findings, report.location.sources);
  node(area, "p", "Paid demand at this site still needs a trial or direct customer evidence.");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const suite = byId("suite").value;
  const inputs = {};
  for (const [parameter, field] of [["capital", "starting_cash"], ["fitout", "build_cost"], ["reserve", "reserve"]]) {
    if (query.has(parameter) && Number.isFinite(Number(query.get(parameter)))) inputs[field] = Number(query.get(parameter));
  }
  const controls = [...form.elements];
  controls.forEach((control) => { control.disabled = true; });
  reportBox.replaceChildren();
  statusLine.textContent = "Checking property evidence, approvals, cash and local demand…";
  try {
    const report = await json("/api/maximo/run", {
      property_id: byId("property").value, suite, use: byId("use").value, ownership: byId("ownership").value, inputs,
    });
    display(report);
    statusLine.textContent = "Review ready.";
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
  const id = query.get("property") ?? "23296";
  const initial = catalog.find((row) => row.id === id);
  if (initial) byId("city").value = initial.city;
  if (query.get("ownership") === "buy") byId("ownership").value = "buy";
  if (query.get("use") === "fitness studio") byId("use").value = "fitness studio";
  updateProperties(id);
}).catch((error) => { statusLine.textContent = error.message; });
