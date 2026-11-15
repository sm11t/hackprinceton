"use strict";
// Neighborhood demand: does the area around the selected property support the use?
// Renders the coordinator's verdict, then the full agent trace with every source and evidence record.
(() => {
  const $ = (id) => document.getElementById(id);
  const panel = $("hood");
  if (!panel) return;
  const status = $("hood-status");
  const out = $("hood-results");

  function add(parent, tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined && text !== null) el.textContent = text;
    if (className) el.className = className;
    parent.append(el);
    return el;
  }

  const VERDICT = { supported: "Supported", mixed: "Mixed", weak: "Weak", unknown: "Unknown" };
  const AGENT = {
    planner: "Planner", site: "Site", residents: "Who lives here", competitors: "Who already serves it",
    momentum: "What is moving in", lookalike: "Lookalike check", coordinator: "Coordinator", narrator: "Narrator",
  };

  function pill(parent, verdict) {
    return add(parent, "span", VERDICT[verdict] || verdict, `hood-pill hood-${verdict}`);
  }

  function value(v) {
    if (v === null || v === undefined) return "unknown";
    if (typeof v === "number") return Math.abs(v) < 1 && v !== 0 ? v.toFixed(3) : v.toLocaleString();
    if (typeof v === "object") return Object.entries(v).map(([k, x]) => `${k}: ${value(x)}`).join(" · ");
    return String(v);
  }

  function sign(stance) {
    return stance > 0 ? "▲" : stance < 0 ? "▼" : "●";
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
    if (!ev) return;
    const s = ev.splits.spatial;
    const box = add(parent, "aside", undefined, "hood-eval");
    add(box, "strong", `How accurate is the lookalike check (${ev.use})?`);
    add(box, "p",
      `We hid ${s.held_out_facilities} real facilities area by area and scored them against `
      + `${s.held_out_background.toLocaleString()} Houston-area places. AUC ${s.auc} `
      + `(90% interval ${s.auc_90ci[0]}–${s.auc_90ci[1]}; 0.5 = coin flip). `
      + `${Math.round(s.hit_rate_top30 * 100)}% of the hidden facilities landed in the top 30% of places (30% by chance).`);
    add(box, "p", `Same test with income alone: AUC ${s.baseline_auc.income_only}; density alone: `
      + `${s.baseline_auc.density_only}. Better than chance, and mostly an income signal.`, "small muted");
    for (const c of ev.caveats || []) add(box, "p", `⚠ ${c}`, "small muted");
  }

  function trace(parent, report) {
    const wrap = add(parent, "details", undefined, "hood-trace");
    wrap.open = report.mode === "validate";
    add(wrap, "summary", `How the agents got there: ${report.trace.length} steps, `
      + `${report.evidence.length} evidence records, `
      + (report.elapsed_ms < 1000 ? `${report.elapsed_ms} ms` : `${(report.elapsed_ms / 1000).toFixed(1)} s`)
      + (report.offline ? " (offline: cached data only)" : ""));
    add(wrap, "p", report.computed_by, "small muted");
    const ol = add(wrap, "ol", undefined, "hood-steps");
    for (const step of report.trace) {
      const li = add(ol, "li", undefined, `hood-step hood-step-${step.status}`);
      const head = add(li, "div", undefined, "hood-step-head");
      add(head, "strong", AGENT[step.agent] || step.agent);
      if (step.use) add(head, "span", step.use, "hood-tag");
      add(head, "span", step.computed_by.startsWith("llm") ? `LLM · ${step.computed_by.slice(5, -1)}` : "code",
        step.computed_by.startsWith("llm") ? "hood-tag hood-llm" : "hood-tag hood-code");
      add(head, "span", step.status, `hood-tag hood-status-${step.status}`);
      if (step.confidence !== null && step.confidence !== undefined) add(head, "span", `confidence ${step.confidence}`, "hood-tag");
      add(head, "span", `${step.ms ?? 0} ms`, "muted small");
      add(li, "p", step.role, "small muted");
      add(li, "p", step.summary);
      const more = add(li, "details");
      add(more, "summary", "Inputs, sources, findings, hand-off");
      const inputs = Object.entries(step.inputs || {}).filter(([, v]) => v !== null && v !== undefined);
      if (inputs.length) add(more, "p", `Inputs: ${inputs.map(([k, v]) => `${k}=${value(v)}`).join(", ")}`, "small");
      if (step.sources.length) {
        const ul = add(more, "ul", undefined, "small");
        for (const s of step.sources) {
          const item = add(ul, "li");
          if (s.url) {
            const a = add(item, "a", s.name);
            a.href = s.url; a.target = "_blank"; a.rel = "noopener";
          } else add(item, "span", s.name);
          add(item, "span", ` · ${s.retrieved_at ? `retrieved ${s.retrieved_at.slice(0, 10)}` : "local"}`
            + `${s.cached ? " (cached)" : ""}${s.note ? ` · ${s.note}` : ""}`, "muted");
        }
      }
      if (step.findings.length) {
        const table = add(more, "table", undefined, "hood-table");
        const hr = add(add(table, "thead"), "tr");
        for (const h of ["Fact", "Value", "Source", "Confidence", "Status", "Note"]) add(hr, "th", h);
        const body = add(table, "tbody");
        for (const f of step.findings) {
          const tr = add(body, "tr");
          add(tr, "td", f.fact);
          add(tr, "td", value(f.value));
          const src = add(tr, "td");
          if (f.evidence_url) {
            const a = add(src, "a", f.source);
            a.href = f.evidence_url; a.target = "_blank"; a.rel = "noopener";
          } else add(src, "span", f.source);
          add(tr, "td", f.confidence);
          add(tr, "td", f.status + (f.needs_human ? " · check" : ""));
          add(tr, "td", f.note, "small");
        }
      }
      if (step.nearby?.length) {
        add(more, "p", "Nearest mapped facilities:", "small");
        const ul = add(more, "ul", undefined, "small");
        for (const f of step.nearby) {
          const a = add(add(ul, "li"), "a", `${f.name || "(unnamed)"} · ${f.miles} mi${f.indoor ? " · indoor" : ""}`);
          a.href = f.url; a.target = "_blank"; a.rel = "noopener";
        }
      }
      if (step.examples?.length) {
        add(more, "p", "Recent arrivals in CoStar buildings nearby:", "small");
        const ul = add(more, "ul", undefined, "small");
        for (const e of step.examples) add(ul, "li", `${e.name} · moved in ${e.arrived}${e.sqft ? ` · ${e.sqft.toLocaleString()} sq ft` : ""}`);
      }
      if (step.handoff) add(li, "p", `→ ${step.handoff}`, "small hood-handoff");
    }
  }

  function render(report) {
    out.replaceChildren();
    if (!report.decisions.length) {
      add(out, "p", report.trace.find((s) => s.agent === "site")?.summary || "No verdict: the site could not be placed.");
      trace(out, report);
      return;
    }
    if (report.narration) {
      const n = add(out, "div", undefined, "hood-narration");
      add(n, "p", report.narration);
      add(n, "p", report.narration_label, "small muted");
    }
    if (report.mode === "suggest") {
      add(out, "h3", `Uses ranked for ${report.site.label}`);
      const grid = add(out, "div", undefined, "hood-grid");
      for (const d of report.decisions) decisionCard(grid, d);
    } else {
      decisionCard(out, report.decisions[0]);
    }
    const look = report.trace.find((s) => s.agent === "lookalike" && s.evaluation
      && (report.mode === "suggest" || s.use === report.decisions[0].use));
    evaluationBox(out, look?.evaluation);
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
    const use = mode === "suggest" ? "suggest" : $("use").value;
    const params = new URLSearchParams({ property_id: id, use });
    if ($("hood-explain").checked) params.set("explain", "1");
    for (const b of panel.querySelectorAll("button")) b.disabled = true;
    out.replaceChildren();
    status.textContent = mode === "suggest"
      ? "Specialists are checking every use around this property…"
      : `Specialists are checking whether the area supports ${use}…`;
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

  // Demo links: /maximo?property=13890701&use=indoor%20pickleball&hood=check (or hood=suggest)
  const auto = new URLSearchParams(location.search).get("hood");
  if (auto === "check" || auto === "suggest") {
    const wanted = new URLSearchParams(location.search).get("property");
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
