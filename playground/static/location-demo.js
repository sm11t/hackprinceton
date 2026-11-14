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

  addText(results, "h3", "What we found");
  if (!report.findings.length) addText(results, "p", "This run returned no findings.");
  for (const claim of context) displayClaim(results, claim, sources);
  if (!market.length) {
    addText(results, "p", "This run did not verify any comparable businesses. It leaves local competition and customer demand unresolved.");
  }
  for (const claim of market) displayClaim(results, claim, sources);

  addText(results, "h3", "What this means for your decision");
  addText(results, "p", market.length
    ? "Use the businesses above to compare your offer. Paid demand at this address is still untested."
    : "The area figures alone are too limited to make a go/no-go decision. A household estimate describes the tract and gives no booking forecast.");
  const actions = addText(results, "ol", "");
  const activity = report.proposed_use === "fitness studio" ? "a trial class" : "a trial court session";
  addText(actions, "li", "Compare nearby operators on price, travel time, and availability.");
  addText(actions, "li", `Test ${activity} at your target price before committing to a build-out.`);
  if (report.unknowns.some((note) => /scan-to-suite/i.test(note))) {
    addText(actions, "li", "Ask the broker to confirm which suite was scanned and send a dimensioned floor plan before estimating capacity.");
  }
}

function displayClaim(parent, claim, sources) {
  const card = document.createElement("article");
  addText(card, "p", claim.statement);
  const references = claim.source_ids.map((id) => sources.get(id)).filter(Boolean);
  const details = references.length ? addText(card, "details", "") : null;
  if (details) addText(details, "summary", "Sources and context");
  for (const source of references) {
    const item = addText(details, "div", "");
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
    status.textContent = "Review complete. Findings are shown below.";
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
