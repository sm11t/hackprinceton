"use strict";
// Neighborhood demand: does the area around the selected property support a business?
// Renders the coordinator's verdicts, then the agent trace with every source and evidence record.
(() => {
  const $ = (id) => document.getElementById(id);
  const panel = $("hood");
  if (!panel) return;
  const status = $("hood-status");
  const out = $("hood-results");
  const picker = $("hood-industry");

  function add(parent, tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined && text !== null) el.textContent = text;
    if (className) el.className = className;
    parent.append(el);
    return el;
  }

  function link(parent, text, href) {
    const a = add(parent, "a", text);
    a.href = href; a.target = "_blank"; a.rel = "noopener";
    return a;
  }

  const VERDICT = { supported: "Supported", mixed: "Mixed", weak: "Weak", unknown: "Unknown" };
  const AGENT = {
    planner: "Planner", site: "Site", residents: "Who lives here", competitors: "Who already serves it",
    momentum: "What is moving in", lookalike: "Lookalike check", coordinator: "Coordinator", narrator: "Narrator",
  };

  const pill = (parent, verdict) => add(parent, "span", VERDICT[verdict] || verdict, `hood-pill hood-${verdict}`);
  const sign = (stance) => (stance > 0 ? "▲" : stance < 0 ? "▼" : "●");
  const ms = (v) => (v < 1000 ? `${v} ms` : `${(v / 1000).toFixed(1)} s`);

  function value(v) {
    if (v === null || v === undefined) return "unknown";
    if (typeof v === "number") return Math.abs(v) < 1 && v !== 0 ? v.toFixed(3) : v.toLocaleString();
    if (typeof v === "object") return Object.entries(v).map(([k, x]) => `${k}: ${value(x)}`).join(" · ");
    return String(v);
  }

  async function loadIndustries() {
    try {
      const rows = await (await fetch("/api/neighborhood/industries")).json();
      const groups = {};
      for (const row of rows) (groups[row.group] ||= []).push(row);
      for (const [group, items] of Object.entries(groups)) {
        const og = add(picker, "optgroup");
        og.label = group;
        for (const row of items) {
          const opt = add(og, "option", row.label + (row.status === "too_few" ? " (too few mapped to score)"
            : row.lookalike_auc ? ` (accuracy AUC ${row.lookalike_auc})` : ""));
          opt.value = row.key;
        }
      }
    } catch { /* the free-text box still works */ }
  }

  function decisionCard(parent, d) {
    const card = add(parent, "article", undefined, "hood-card");
    const head = add(card, "div", undefined, "hood-card-head");
    pill(head, d.verdict);
    add(head, "strong", d.use);
    add(card, "p", d.headline);
    if (d.insight) add(card, "p", d.insight, "hood-insight");
    const list = add(card, "ul", undefined, "hood-reasons");
    for (const r of d.reasons) {
      const li = add(list, "li", undefined, r.stance > 0 ? "up" : r.stance < 0 ? "down" : "flat");
      add(li, "span", `${sign(r.stance)} `, "hood-sign");
      add(li, "span", r.reason);
    }
    for (const r of d.unknown) add(list, "li", `? ${r.reason}`, "unknown");
    return card;
  }

  function evaluationBox(parent, ev) {
    if (!ev || ev.status !== "ok") {
      if (ev?.note) add(parent, "aside", ev.note, "hood-eval");
      return;
    }
    const s = ev.splits.spatial;
    const box = add(parent, "aside", undefined, "hood-eval");
    add(box, "strong", `How accurate is the lookalike check for ${ev.label.toLowerCase()}?`);
    add(box, "p",
      `We hid ${s.held_out_facilities} real ${ev.label.toLowerCase()} locations area by area and scored them against `
      + `${s.held_out_background.toLocaleString()} Houston-area places. AUC ${s.auc} `
      + `(90% interval ${s.auc_90ci[0]}–${s.auc_90ci[1]}; 0.5 = coin flip). `
      + `${Math.round(s.hit_rate_top30 * 100)}% of the hidden locations landed in the top 30% of places (30% by chance).`);
    add(box, "p", `Same test with income alone: ${s.baseline_auc.income_only}; density alone: `
      + `${s.baseline_auc.density_only}; with the labels shuffled: ${s.baseline_auc.shuffled_labels} (should be ~0.5).`,
    "small muted");
    for (const c of ev.caveats || []) add(box, "p", `⚠ ${c}`, "small muted");
  }

  function findingsTable(parent, findings) {
    if (!findings.length) return;
    const table = add(parent, "table", undefined, "hood-table");
    const hr = add(add(table, "thead"), "tr");
    for (const h of ["Fact", "Value", "Source", "Confidence", "Status", "Note"]) add(hr, "th", h);
    const body = add(table, "tbody");
    for (const f of findings) {
      const tr = add(body, "tr");
      add(tr, "td", f.fact);
      add(tr, "td", value(f.value));
      const src = add(tr, "td");
      if (f.evidence_url) link(src, f.source, f.evidence_url); else add(src, "span", f.source);
      add(tr, "td", f.confidence);
      add(tr, "td", f.status + (f.needs_human ? " · check" : ""));
      add(tr, "td", f.note, "small");
    }
  }

  function perIndustryTable(parent, per) {
    const table = add(parent, "table", undefined, "hood-table");
    const hr = add(add(table, "thead"), "tr");
    for (const h of ["Industry", "Result", "Signal"]) add(hr, "th", h);
    const body = add(table, "tbody");
    for (const [key, v] of Object.entries(per)) {
      const tr = add(body, "tr");
      add(tr, "td", key.replaceAll("_", " "));
      add(tr, "td", v.summary || v.status);
      const s = v.signal;
      add(tr, "td", s ? `${s.stance === null ? "?" : sign(s.stance)} ${s.reason}` : "—");
    }
  }

  function trace(parent, report) {
    const wrap = add(parent, "details", undefined, "hood-trace");
    wrap.open = report.mode === "validate";
    add(wrap, "summary", `How the agents got there: ${report.trace.length} steps, `
      + `${report.evidence.length} evidence records, ${ms(report.elapsed_ms)}`
      + (report.offline ? " (offline: cached data only)" : ""));
    add(wrap, "p", report.computed_by, "small muted");
    const single = report.decisions.length === 1 ? report.decisions[0].industry : null;
    const ol = add(wrap, "ol", undefined, "hood-steps");
    for (const step of report.trace) {
      const li = add(ol, "li", undefined, `hood-step hood-step-${step.status}`);
      const head = add(li, "div", undefined, "hood-step-head");
      add(head, "strong", AGENT[step.agent] || step.agent);
      const llm = step.computed_by.startsWith("llm");
      add(head, "span", llm ? `LLM · ${step.computed_by.slice(5, -1)}` : "code", llm ? "hood-tag hood-llm" : "hood-tag hood-code");
      add(head, "span", step.status, `hood-tag hood-status-${step.status}`);
      if (step.confidence !== null && step.confidence !== undefined) add(head, "span", `confidence ${step.confidence}`, "hood-tag");
      add(head, "span", ms(step.ms ?? 0), "muted small");
      add(li, "p", step.role, "small muted");
      add(li, "p", step.summary);
      const more = add(li, "details");
      add(more, "summary", "Inputs, sources, findings, hand-off");
      const inputs = Object.entries(step.inputs || {}).filter(([, v]) => v !== null && v !== undefined);
      if (inputs.length) add(more, "p", `Inputs: ${inputs.map(([k, v]) => `${k}=${value(v)}`).join(", ")}`, "small");
      if (step.sources.length) {
        const ul = add(more, "ul", undefined, "small");
        for (const s of step.sources.slice(0, 12)) {
          const item = add(ul, "li");
          if (s.url) link(item, s.name, s.url); else add(item, "span", s.name);
          add(item, "span", ` · ${s.retrieved_at ? `retrieved ${s.retrieved_at.slice(0, 10)}` : "local"}`
            + `${s.cached ? " (cached)" : ""}${s.note ? ` · ${s.note}` : ""}`, "muted");
        }
        if (step.sources.length > 12) add(ul, "li", `…and ${step.sources.length - 12} more sources`, "muted");
      }
      const per = step.per_industry || {};
      if (!single && Object.keys(per).length > 1) perIndustryTable(more, per);
      findingsTable(more, single ? step.findings : step.findings.filter((f) => !f.fact.includes(".")));
      const mine = single ? per[single] : null;
      if (mine?.nearby?.length) {
        add(more, "p", "Nearest mapped locations:", "small");
        const ul = add(more, "ul", undefined, "small");
        for (const f of mine.nearby) {
          link(add(ul, "li"), `${f.name || "(unnamed)"} · ${f.miles} mi`
            + (f.capacity ? ` · ${f.capacity} licensed seats` : f.indoor ? " · indoor" : ""), f.url);
        }
      }
      if (mine?.examples?.length) {
        add(more, "p", "Recent arrivals in CoStar buildings nearby:", "small");
        const ul = add(more, "ul", undefined, "small");
        for (const e of mine.examples) add(ul, "li", `${e.name} · moved in ${e.arrived}${e.sqft ? ` · ${e.sqft.toLocaleString()} sq ft` : ""}`);
      }
      if (step.handoff) add(li, "p", `→ ${step.handoff}`, "small hood-handoff");
    }
  }

  function render(report) {
    out.replaceChildren();
    if (report.unmatched) {
      add(out, "p", `Couldn't match “${report.unmatched}” to a business type. Pick one from the list, or try other words.`);
    }
    if (report.mode === "validate") {
      for (const [use, why] of Object.entries(report.not_modelled || {})) add(out, "p", `${use}: not checked here. ${why}`);
    }
    if (!report.decisions.length) {
      if (!report.unmatched && !Object.keys(report.not_modelled || {}).length) {
        add(out, "p", report.trace.find((s) => s.agent === "site")?.summary || "No verdict: the site could not be placed.");
      }
      trace(out, report);
      return;
    }
    if (report.narration) {
      const n = add(out, "div", undefined, "hood-narration");
      add(n, "p", report.narration);
      add(n, "p", report.narration_label, "small muted");
    }
    const look = report.trace.find((s) => s.agent === "lookalike")?.per_industry || {};
    if (report.mode === "suggest") {
      const counts = {};
      for (const d of report.decisions) counts[d.verdict] = (counts[d.verdict] || 0) + 1;
      add(out, "h3", `${report.decisions.length} businesses checked around ${report.site.label}`);
      add(out, "p", Object.entries(counts).map(([v, k]) => `${k} ${VERDICT[v].toLowerCase()}`).join(" · "), "muted");
      const best = report.decisions.filter((d) => d.verdict === "supported" || (d.verdict === "mixed" && d.score > 0));
      const grid = add(out, "div", undefined, "hood-grid");
      for (const d of best) decisionCard(grid, d);
      const rest = report.decisions.filter((d) => !best.includes(d));
      if (rest.length) {
        const more = add(out, "details", undefined, "hood-rest");
        add(more, "summary", `Mixed with no net support, weak, or not enough evidence (${rest.length})`);
        const grid2 = add(more, "div", undefined, "hood-grid");
        for (const d of rest) decisionCard(grid2, d);
      }
      const nm = Object.keys(report.not_modelled || {});
      if (nm.length) add(out, "p", `Not checked (demand isn't driven by nearby residents): ${nm.join(", ")}.`, "small muted");
    } else {
      const d = report.decisions[0];
      decisionCard(out, d);
      evaluationBox(out, look[d.industry]?.evaluation);
    }
    const rules = add(out, "details", undefined, "small");
    add(rules, "summary", "Verdict rules");
    const ul = add(rules, "ul");
    for (const r of report.decisions[0].rules) add(ul, "li", r);
    trace(out, report);
  }

  async function run(mode) {
    const id = $("property")?.value;
    if (!id) { status.textContent = "Pick a property first."; return; }
    if ($("city")?.value !== "Houston") { status.textContent = "Neighborhood data covers the Houston area only."; return; }
    const use = mode === "suggest" ? "suggest" : ($("hood-text").value.trim() || picker.value || $("use").value);
    const params = new URLSearchParams({ property_id: id, use });
    if ($("hood-explain").checked) params.set("explain", "1");
    for (const b of panel.querySelectorAll("button")) b.disabled = true;
    out.replaceChildren();
    status.textContent = mode === "suggest"
      ? "Specialists are checking every business type around this property…"
      : `Specialists are checking whether the area supports “${use}”…`;
    try {
      const response = await fetch(`/api/neighborhood?${params}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "The neighborhood check failed.");
      status.textContent = "";
      render(data);
    } catch (error) {
      status.textContent = error.message;
    } finally {
      for (const b of panel.querySelectorAll("button")) b.disabled = false;
    }
  }

  $("hood-check").addEventListener("click", () => run("validate"));
  $("hood-suggest").addEventListener("click", () => run("suggest"));
  $("hood-text").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); run("validate"); } });
  loadIndustries();

  // Demo links: /maximo?property=13890701&use=indoor%20pickleball&hood=check (or hood=suggest; &business=bouldering%20gym)
  const query = new URLSearchParams(location.search);
  const auto = query.get("hood");
  if (query.get("business")) $("hood-text").value = query.get("business");
  if (auto === "check" || auto === "suggest") {
    const wanted = query.get("property");
    const started = Date.now();
    const timer = setInterval(() => {
      const ready = $("property")?.value && (!wanted || $("property").value === wanted);
      if (ready || Date.now() - started > 15000) {
        clearInterval(timer);
        if (ready) {
          panel.scrollIntoView();
          run(auto === "suggest" ? "suggest" : "validate");
        }
      }
    }, 200);
  }
})();
