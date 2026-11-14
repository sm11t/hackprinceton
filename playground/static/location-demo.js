"use strict";
const byId = (id) => document.getElementById(id);
const city = byId("city");
const property = byId("property");
const filter = byId("filter");
const status = byId("status");
const results = byId("results");
const button = byId("run");
let catalog = [];
let running = false;

function displayProperties(preferredId) {
  const needle = filter.value.trim().toLowerCase();
  const matches = catalog.filter((row) => row.city === city.value &&
    row.address.toLowerCase().includes(needle));
  property.replaceChildren(...matches.map((row) => new Option(row.address, row.id)));
  if (matches.some((row) => row.id === preferredId)) property.value = preferredId;
  button.disabled = running || !matches.length;
  status.textContent = matches.length ? `${matches.length} properties` : "No properties match this filter.";
}

function addText(parent, tag, value) {
  const node = document.createElement(tag);
  node.textContent = value;
  parent.append(node);
  return node;
}

function displayReview(report) {
  const sources = new Map(report.sources.map((source) => [source.source_id, source]));
  addText(results, "h2", report.address);
  addText(results, "p", `Proposed use: ${report.proposed_use}`);
  const market = report.findings.filter((claim) =>
    claim.source_ids.some((id) => id.startsWith("market-page-")));
  const context = report.findings.filter((claim) => !market.includes(claim));

  addText(results, "h3", "Next decision: validate demand before committing");
  addText(results, "p", market.length
    ? "Use the comparable businesses below to benchmark your offer. You still need evidence that customers will pay for it at this location."
    : "This review found no verified local comparables. The household estimate describes the Census tract. It cannot tell you how many people would book or join.");
  const actions = addText(results, "ol", "");
  const activity = report.proposed_use === "fitness studio" ? "a trial class" : "a trial court session";
  addText(actions, "li", "Compare three nearby operators. Record travel time, prices, and availability at the times you plan to operate.");
  addText(actions, "li", `Offer ${activity} at your target price and track paid bookings. Compare that turnout with the bookings you need to cover costs.`);
  if (report.unknowns.some((note) => /scan-to-suite/i.test(note))) {
    addText(actions, "li", "Ask the broker to confirm which suite was scanned and send a dimensioned floor plan before estimating capacity.");
  }

  addText(results, "h3", "Local comparables");
  if (!market.length) addText(results, "p", "No comparable businesses could be verified in this run.");
  for (const claim of market) displayClaim(results, claim, sources);

  const details = addText(results, "details", "");
  addText(details, "summary", "Area and site evidence");
  for (const claim of context) displayClaim(details, claim, sources);
  if (!context.length) addText(details, "p", "No area or site evidence was available.");
}

function displayClaim(parent, claim, sources) {
  const card = document.createElement("article");
  addText(card, "p", claim.statement);
  for (const id of claim.source_ids) {
    const source = sources.get(id);
    if (!source) continue;
    const item = addText(card, "div", "");
    if (source.evidence_url?.startsWith("https://")) {
      const link = addText(item, "a", source.fact);
      link.href = source.evidence_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    } else {
      addText(item, "span", source.fact);
    }
    if (source.captured_at) addText(item, "small", ` · ${source.captured_at}`);
    if (source.note) addText(item, "p", source.note);
  }
  parent.append(card);
}

city.addEventListener("change", () => {
  filter.value = "";
  displayProperties();
});
filter.addEventListener("input", () => displayProperties(property.value));
byId("review").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (running || !property.value) return;
  const input = { property_id: property.value, use: byId("use").value };
  running = true;
  const controls = [...event.currentTarget.elements];
  controls.forEach((control) => { control.disabled = true; });
  results.replaceChildren();
  const start = Date.now();
  const update = () => {
    status.textContent = `Gathering evidence, researching the market, and validating findings… ${Math.floor((Date.now() - start) / 1000)}s`;
  };
  update();
  const timer = setInterval(update, 1000);
  try {
    const response = await fetch("/api/location/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    const report = await response.json();
    if (!response.ok) throw new Error(report.error);
    displayReview(report);
    status.textContent = "Review complete. See the next decision below.";
  } catch (error) {
    status.textContent = error.message || "Review failed. Try again.";
  } finally {
    clearInterval(timer);
    running = false;
    controls.forEach((control) => { control.disabled = false; });
  }
});

fetch("/api/location/properties")
  .then((response) => {
    if (!response.ok) throw new Error();
    return response.json();
  })
  .then((rows) => {
    catalog = rows;
    displayProperties("23296");
  })
  .catch(() => { status.textContent = "The property kit could not be loaded."; });
