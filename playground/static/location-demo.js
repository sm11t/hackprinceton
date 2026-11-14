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
  addText(results, "p", `Proposed use: ${report.proposed_use}. Paid demand remains unverified.`);
  addText(results, "h3", "Findings");
  if (!report.findings.length) addText(results, "p", "No findings cleared review.");
  for (const claim of report.findings) {
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
    results.append(card);
  }
  const gaps = [...report.unknowns, ...report.validation_issues];
  if (gaps.length) {
    addText(results, "h3", "What to verify");
    const list = addText(results, "ul", "");
    for (const gap of gaps) addText(list, "li", gap);
  }
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
    status.textContent = "Review complete.";
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
