# /// script
# requires-python = ">=3.12"
# dependencies = ["langchain-core==1.8.0", "langchain-openai==1.8.0"]
# ///
"""LangChain front end for the neighborhood check: the LLM routes and explains, the tools compute.

The model gets the deterministic tools from neighborhood_tools.py (resolve an industry,
check a site, suggest industries, fetch evidence). It never computes a number: its
final answer is rejected if it contains a number that no tool returned. Every tool call
is recorded in the trace with its arguments, timing and result summary.

The model is any OpenAI-compatible endpoint, read from the team contract:
  LLM_BASE_URL, LLM_MODEL, LLM_API_KEY      (OpenRouter: https://openrouter.ai/api/v1)
falling back to Upstage Solar Mini (UPSTAGE_API_KEY) until the OpenRouter key exists.

  uv run playground/with_env.py uv run playground/neighborhood_agent.py \
      --property-id 13890701 "I want to open a bouldering gym. Does this area work, and what else would?"
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage  # noqa: E402
from langchain_core.tools import StructuredTool  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

import neighborhood as nb  # noqa: E402
import neighborhood_tools as tools  # noqa: E402

SYSTEM = (
    "You help a small-business owner decide whether a neighborhood in the Houston area supports their business. "
    "Always use the tools: resolve the business to an industry, check the site, and if asked for alternatives, "
    "suggest industries. Never compute or estimate numbers yourself; quote only numbers that tools returned. "
    "Report unknowns as unknown. Answer in at most 5 short sentences."
)


def langchain_tools(site, kit=None):
    """Wrap the plain tools as LangChain StructuredTools, with the site bound so the model cannot change it."""
    bound = {"property_id": site.get("property_id"), "address": site.get("address"), "kit": kit}
    out = []
    for name, (fn, schema) in tools.TOOLS.items():
        properties = {k: v for k, v in schema.get("properties", {}).items() if k not in ("property_id", "address")}
        args_schema = {"type": "object", "properties": properties,
                       "required": [r for r in schema.get("required", []) if r in properties]}
        takes_site = "property_id" in schema.get("properties", {})

        def run(_fn=fn, _takes_site=takes_site, **kwargs):
            return json.dumps(_fn(**kwargs, **(bound if _takes_site else {})), default=str)
        out.append(StructuredTool.from_function(func=run, name=name, description=fn.__doc__.strip(),
                                                args_schema=args_schema))
    return out


def model():
    cfg = nb.llm_config()
    if not cfg["key"]:
        raise SystemExit("Set LLM_API_KEY (OpenRouter) or UPSTAGE_API_KEY.")
    extra = {"default_headers": {"X-Title": "Neighborhood demand check"}} if "openrouter.ai" in cfg["base_url"] else {}
    return ChatOpenAI(base_url=cfg["base_url"], model=cfg["model"], api_key=cfg["key"], temperature=0,
                      timeout=40, max_retries=1, **extra), cfg


def ask(question, site, kit=None, max_rounds=5, llm=None):
    """Run the tool-calling loop. Returns {answer, accepted, trace, ms}."""
    started = time.perf_counter()
    llm, cfg = (llm, {"model": "injected"}) if llm else model()
    available = langchain_tools(site, kit)
    by_name = {t.name: t for t in available}
    chat = llm.bind_tools(available)
    messages = [SystemMessage(SYSTEM), HumanMessage(question)]
    trace, tool_text = [], ""
    for _ in range(max_rounds):
        t = time.perf_counter()
        reply = chat.invoke(messages)
        trace.append({"agent": "llm", "computed_by": f"llm ({cfg['model']})", "ms": round(1000 * (time.perf_counter() - t)),
                      "summary": f"asked for {[c['name'] for c in reply.tool_calls]}" if reply.tool_calls
                      else "final answer"})
        messages.append(reply)
        if not reply.tool_calls:
            break
        for call in reply.tool_calls:
            t = time.perf_counter()
            try:
                result = by_name[call["name"]].invoke(call["args"])
            except (KeyError, ValueError, TypeError) as error:
                result = json.dumps({"error": f"{type(error).__name__}: {error}"})
            tool_text += result
            trace.append({"agent": f"tool:{call['name']}", "computed_by": "code", "inputs": call["args"],
                          "ms": round(1000 * (time.perf_counter() - t)), "summary": result[:200]})
            messages.append(ToolMessage(result, tool_call_id=call["id"]))
    answer = reply.content if isinstance(reply.content, str) else json.dumps(reply.content)
    invented = sorted(nb.numbers_in(answer) - nb.numbers_in(tool_text) - nb.numbers_in(question))
    return {"answer": answer if not invented else None, "accepted": not invented,
            "rejected_numbers": invented[:5], "trace": trace, "ms": round(1000 * (time.perf_counter() - started))}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question")
    parser.add_argument("--property-id", type=int)
    parser.add_argument("--address")
    parser.add_argument("--kit", type=Path)
    args = parser.parse_args()
    result = ask(args.question, {"property_id": args.property_id, "address": args.address}, args.kit)
    for step in result["trace"]:
        print(f"  [{step['agent']}] {step['ms']} ms: {step['summary']}")
    print("\n" + (result["answer"] if result["accepted"] else
                  f"(answer rejected: numbers not returned by any tool {result['rejected_numbers']})"))
    print(f"\n{result['ms']} ms total")


if __name__ == "__main__":
    main()
