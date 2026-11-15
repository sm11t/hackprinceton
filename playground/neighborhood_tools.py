"""Framework-free tools over the neighborhood pipeline, for LLM agents (LangChain, OpenAI tools, MCP...).

Each tool is a plain function returning JSON-safe dicts, plus a JSON schema in TOOLS.
The tools compute nothing new: they call neighborhood.investigate and trim its
report, so every number an agent sees is code-computed and carries its evidence.
neighborhood_agent.py wraps these as LangChain tools.
"""
import time
from functools import lru_cache

import neighborhood as nb
from neighborhood_industries import INDUSTRIES, resolve

SITE_SCHEMA = {
    "property_id": {"type": "integer", "description": "CoStar property id (preferred when known)"},
    "address": {"type": "string", "description": "Street address in the Houston area"},
    "suite": {"type": "string", "description": "Listed suite to check the building against (optional)"},
}


@lru_cache(maxsize=64)
def _run(request, property_id=None, address=None, kit=None, suite=None):
    """One pipeline run per (request, site); agents often ask about the same site twice."""
    return nb.investigate(request, address=address, property_id=property_id, kit=kit, suite=suite)


def _site_args(property_id, address):
    if not property_id and not address:
        raise ValueError("Give property_id or address.")
    return (int(property_id) if property_id else None), (address or None)


def _building(b):
    return None if not b else {k: b[k] for k in ("status", "capacity", "reasons", "unknowns", "verify")}


def _decision(d, evidence_count=None):
    out = {k: d[k] for k in ("industry", "use", "verdict", "headline", "insight", "reasons", "unknown",
                             "lookalike_percentile", "lookalike_validated")}
    out["building"] = _building(d.get("building"))
    if evidence_count is not None:
        out["evidence_records"] = evidence_count
    return out


def list_industries():
    """Every industry the check covers, with how many facilities are mapped and the measured lookalike AUC."""
    return {"industries": nb.industry_catalog(), "area": nb.AREA_NAME}


def resolve_industry(description):
    """Map a business description (e.g. 'bouldering gym') to an industry key, in code. Unmatched stays None."""
    key, how, candidates = resolve(description)
    return {"industry": key, "label": INDUSTRIES[key]["label"] if key else None, "how": how,
            "candidates": [{"key": k, "label": INDUSTRIES[k]["label"]} for k in candidates]}


def check_neighborhood(industry, property_id=None, address=None, kit=None, suite=None):
    """Does the neighborhood support this business at this site, and can the building host it?
    Demand verdict with deciding reasons and unknowns, plus the building check for CoStar properties."""
    pid, addr = _site_args(property_id, address)
    started = time.perf_counter()
    report = _run(industry, pid, addr, kit, suite)
    out = {"site": report["site"], "request": industry, "unmatched": report["unmatched"],
           "candidates": report["candidates"], "not_modelled": report["not_modelled"],
           "decisions": [_decision(d, len(report["evidence"])) for d in report["decisions"]],
           "trace": [{"agent": s["agent"], "status": s["status"], "ms": s.get("ms"), "summary": s["summary"]}
                     for s in report["trace"]],
           "ms": round(1000 * (time.perf_counter() - started))}
    return out


def suggest_industries(property_id=None, address=None, top=5, kit=None, suite=None):
    """What should go here? Businesses the building can host, best supported first, plus demand gaps
    nearby that this building cannot host (so the person knows, without being steered to a misfit)."""
    pid, addr = _site_args(property_id, address)
    report = _run("suggest", pid, addr, kit, suite)

    def row(d):
        return {"industry": d["industry"], "use": d["use"], "verdict": d["verdict"],
                "lookalike_percentile": d["lookalike_percentile"], "insight": d["insight"],
                "top_reason": d["reasons"][0]["reason"] if d["reasons"] else None,
                "building": _building(d.get("building"))}
    status = lambda d: (d.get("building") or {}).get("status")  # noqa: E731
    hostable = [row(d) for d in report["decisions"] if status(d) != "no"]
    gaps = [row(d) for d in report["decisions"] if status(d) == "no"
            and (d["verdict"] == "supported" or (d["verdict"] == "mixed" and d.get("score", 0) > 0))]
    top = max(1, int(top))
    return {"site": report["site"], "building_checked": report.get("building_checked", False),
            "can_go_here": hostable[:top], "of": len(hostable),
            "demand_gaps_this_building_cannot_host": gaps[:top],
            "not_modelled": report["not_modelled"], "elapsed_ms": report["elapsed_ms"]}


def get_evidence(industry, fact=None, property_id=None, address=None, kit=None, suite=None):
    """The evidence records behind a check (optionally only facts containing `fact`), with sources."""
    pid, addr = _site_args(property_id, address)
    report = _run(industry, pid, addr, kit, suite)
    rows = [r for r in report["evidence"] if not fact or fact in r["fact"]]
    return {"records": rows[:40], "total": len(rows)}


TOOLS = {
    "list_industries": (list_industries, {"type": "object", "properties": {}}),
    "resolve_industry": (resolve_industry, {"type": "object", "properties": {
        "description": {"type": "string", "description": "What the person wants to open, in their words"}},
        "required": ["description"]}),
    "check_neighborhood": (check_neighborhood, {"type": "object", "properties": {
        "industry": {"type": "string", "description": "Industry key from list_industries/resolve_industry"},
        **SITE_SCHEMA}, "required": ["industry"]}),
    "suggest_industries": (suggest_industries, {"type": "object", "properties": {
        **SITE_SCHEMA, "top": {"type": "integer", "description": "How many to return (default 5)"}}}),
    "get_evidence": (get_evidence, {"type": "object", "properties": {
        "industry": {"type": "string"}, "fact": {"type": "string", "description": "Substring of the fact name"},
        **SITE_SCHEMA}, "required": ["industry"]}),
}


def openai_tool_specs():
    """The tools in OpenAI / OpenRouter function-calling format."""
    return [{"type": "function", "function": {"name": name, "description": fn.__doc__.strip(), "parameters": schema}}
            for name, (fn, schema) in TOOLS.items()]


def call(name, arguments):
    """Dispatch a tool call by name (for any agent loop)."""
    fn, schema = TOOLS[name]
    allowed = set(schema.get("properties", {}))
    return fn(**{k: v for k, v in (arguments or {}).items() if k in allowed})
