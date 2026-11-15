"use strict";
// Market-wide ranking: "where should I do this?" for the use and cash already entered in the review form.
(() => {
  const $ = (id) => document.getElementById(id);
  const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  const button = $("rank-button");
  const status = $("rank-status");
  const list = $("rank-results");
  const note = $("rank-basis");

  function add(parent, tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    parent.append(el);
    return el;
  }

  function reviewLink(row, data) {
    const params = new URLSearchParams({
      property: String(row.property_id), suite: row.suite, use: data.use, ownership: "lease",
      capital: String(data.capital), reserve: String(data.reserve), fitout: String(row.build_cost), run: "1",
    });
    return `/maximo?${params}`;
  }

  async function rank() {
    if ($("ownership").value === "buy") {
      status.textContent = "Ranking covers leases only for now. Switch the deal type to Lease.";
      return;
    }
    const params = new URLSearchParams({
      market: $("city").value, use: $("use").value, capital: $("budget").value, reserve: $("reserve").value,
    });
    button.disabled = true;
    list.replaceChildren();
    note.textContent = "";
    status.textContent = `Screening every listed ${$("city").value} space for ${$("use").value}… (first run reads the kit, ~30 s)`;
    try {
      const response = await fetch(`/api/maximo/rank?${params}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Ranking failed.");
      const fit = data.by_verdict;
      status.textContent = `${data.spaces_screened.toLocaleString()} listed spaces in ${data.buildings_screened} buildings screened. `
        + `${data.buildings_passing} buildings pass (${fit.supported} supported by the data, ${fit.investigate} to investigate); `
        + `${data.within_budget} within ${money.format(data.capital)}`
        + (data.budget_unknown ? `, ${data.budget_unknown} with no listed rent.` : ".");
      if (!data.results.length) status.textContent += " No space passed this screen.";
      for (const row of data.results) {
        const item = add(list, "li");
        const head = add(item, "p");
        const link = add(head, "a", `${row.address} · ${row.suite_label}`);
        link.href = reviewLink(row, data);
        add(head, "span", ` · ${row.property_type}`, "muted");
        add(head, "strong", row.verdict === "supported" ? "  Fits on the data" : "  Investigate", row.verdict === "supported" ? "fit-ok" : "fit-check");
        add(item, "p", row.why);
        add(item, "p", row.fit_reason, "small muted");
        for (const flag of row.evidence_flags) add(item, "p", `⚠ ${flag}`, "small flag");
      }
      note.textContent = `How this is ranked: ${data.ranking_basis} Limits: ${data.limits}`;
    } catch (error) {
      status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }

  button.addEventListener("click", rank);
})();
