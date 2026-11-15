#!/usr/bin/env python3
"""Project Helix: Chat Server with CoStar Real Estate API Kit + Tavily Web Search.

Provides natural-language access to:
- CoStar commercial properties, listings, advertised suites, asking rents, tenancies, and sale comps
- Tavily live web search
- NVIDIA Nemotron 3 Ultra 550B (via OpenRouter free route) LLM tool orchestration
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
import urllib.error
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from costar_service import CoStarService

def load_env():
    """Load env vars from project helix/.env or root .env without overwriting existing."""
    paths = [
        BASE_DIR / ".env",
        BASE_DIR.parent / ".env",
    ]
    for p in paths:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip().removeprefix("export ")
                v = v.strip().strip("\"'")
                if k.isidentifier() and k not in os.environ:
                    os.environ[k] = v

load_env()

# Strictly enforced OpenRouter + NVIDIA Nemotron 3 Ultra (:free route only, zero paid fallback)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
MODEL = os.environ.get("OPENROUTER_MODEL", OPENROUTER_MODEL).strip()
if OPENROUTER_BASE_URL != "https://openrouter.ai/api/v1":
    raise RuntimeError("OPENROUTER_BASE_URL must be https://openrouter.ai/api/v1")
if MODEL != OPENROUTER_MODEL:
    raise RuntimeError(f"OPENROUTER_MODEL must be {OPENROUTER_MODEL}")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
COSTAR_KIT_PATH = os.environ.get("COSTAR_KIT_PATH", "/Users/jessenth/Downloads/costar-hackathon-kit.zip")
COSTAR_PASSWORD = os.environ.get("COSTAR_KIT_ZIP_PASSWORD") or os.environ.get("COSTAR_KIT_PASSWORD") or "princeton-h4ck4th0n-2026"

# Initialize CoStar service
try:
    costar = CoStarService(COSTAR_KIT_PATH, COSTAR_PASSWORD)
    has_costar = Path(COSTAR_KIT_PATH).exists()
except Exception as e:
    costar = None
    has_costar = False
    sys.stderr.write(f"[CoStar Init Warning] {e}\n")


def tavily_search(query: str, max_results: int = 5):
    """Perform a live web search using Tavily API."""
    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY not configured"}

    url = "https://api.tavily.com/search"
    payload = {
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
    }
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TAVILY_API_KEY}",
            "Content-Type": "application/json"
        },
        data=json.dumps(payload).encode("utf-8")
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", "")[:300]
                })
            return {"query": query, "results": results}
    except Exception as e:
        return {"error": f"Tavily search failed: {str(e)}"}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "costar_search_properties",
            "description": "Search CoStar commercial properties by address, street name, building keyword, or PropertyId in Houston.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Street name, address substring, or property number (e.g. '9800 Centre', 'Tanner Rd', 'Sam Houston')."
                    },
                    "city": {
                        "type": "string",
                        "description": "City filter, defaults to Houston."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "costar_get_property",
            "description": "Fetch verified commercial property facts from CoStar for a PropertyId: building size (RBA/GFA), property asset class (Office, Industrial, Flex, Retail), building class (A/B/C), stories, zoning, parking, and linked Matterport 3D twin model IDs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {
                        "type": "integer",
                        "description": "The exact integer CoStar PropertyId."
                    }
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "costar_get_listings_and_spaces",
            "description": "Fetch active commercial lease and sale listings from CoStar for a PropertyId: advertised suites/spaces, square footage, asking rents ($/SF/year or $/month), lease basis (Full Service Gross, NNN, Modified Gross), and availability dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {
                        "type": "integer",
                        "description": "The exact integer CoStar PropertyId."
                    }
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "costar_get_tenants",
            "description": "Fetch current and historical commercial occupants and tenants recorded in CoStar for a PropertyId, including tenant company names, move-in dates, and square feet occupied.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {
                        "type": "integer",
                        "description": "The exact integer CoStar PropertyId."
                    }
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "costar_get_sale_comps",
            "description": "Fetch historical commercial sales transactions and comps from CoStar for a PropertyId, including sale dates, recorded transaction prices, cap rates, and buyer/seller.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {
                        "type": "integer",
                        "description": "The exact integer CoStar PropertyId."
                    }
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "costar_filter_spaces",
            "description": "Screen and filter available commercial lease spaces across Houston and Los Angeles by minimum or maximum square footage, asking rent ($/SF/year), city, and sort order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City filter: 'Houston', 'Los Angeles', or omit to search both cities."
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["lowest_rent", "highest_rent", "largest_sf", "smallest_sf"],
                        "description": "Sorting criteria: 'highest_rent' (most expensive asking rate first), 'lowest_rent' (cheapest asking rate first), 'largest_sf', 'smallest_sf'."
                    },
                    "min_square_feet": {
                        "type": "number",
                        "description": "Minimum required square footage."
                    },
                    "max_square_feet": {
                        "type": "number",
                        "description": "Maximum square footage."
                    },
                    "min_asking_rate": {
                        "type": "number",
                        "description": "Minimum asking rent in $/SF/year."
                    },
                    "max_asking_rate": {
                        "type": "number",
                        "description": "Maximum asking rent in $/SF/year."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "costar_search_apartments",
            "description": "Search multifamily and apartment rental communities from CoStar/Apartments.com in Houston by building name or street address, returning unit counts, rent ranges, and management companies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Apartment community name or address."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "costar_search_residential",
            "description": "Search single-family home MLS listings from CoStar/Homes.com in Houston by street address, returning listing IDs and Matterport model IDs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Street name or address."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": "Search the live public web for independent verification, public broker listings, property records, asking rates, news, competitors, and external web evidence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The exact web search query."
                    }
                },
                "required": ["query"]
            }
        }
    }
]


class ChatHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            index_path = BASE_DIR / "index.html"
            if not index_path.exists():
                self.send_error(404, "index.html not found")
                return
            content = index_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if self.path == "/api/config":
            self.send_json({
                "model": MODEL,
                "has_openrouter": bool(OPENROUTER_API_KEY),
                "has_tavily": bool(TAVILY_API_KEY),
                "has_costar": has_costar
            })
            return

        self.send_error(404, "Not Found")

    def execute_tool(self, name: str, args: dict):
        """Dispatch tool calls to CoStar or Tavily."""
        if name == "costar_search_properties":
            if not costar: return {"error": "CoStar service unavailable"}
            return costar.search_properties(args.get("query", ""), city=args.get("city", "Houston"))
        
        elif name == "costar_get_property":
            if not costar: return {"error": "CoStar service unavailable"}
            return costar.get_property(args.get("property_id"))
        
        elif name == "costar_get_listings_and_spaces":
            if not costar: return {"error": "CoStar service unavailable"}
            return costar.get_listings_and_spaces(args.get("property_id"))
        
        elif name == "costar_get_tenants":
            if not costar: return {"error": "CoStar service unavailable"}
            return costar.get_tenants(args.get("property_id"))
        
        elif name == "costar_get_sale_comps":
            if not costar: return {"error": "CoStar service unavailable"}
            return costar.get_sale_comps(args.get("property_id"))
        
        elif name == "costar_filter_spaces":
            if not costar: return {"error": "CoStar service unavailable"}
            return costar.filter_spaces(
                min_square_feet=args.get("min_square_feet"),
                max_square_feet=args.get("max_square_feet"),
                min_asking_rate=args.get("min_asking_rate"),
                max_asking_rate=args.get("max_asking_rate"),
                city=args.get("city"),
                sort_by=args.get("sort_by", "lowest_rent")
            )

        elif name == "costar_search_apartments":
            if not costar: return {"error": "CoStar service unavailable"}
            return costar.search_apartments(args.get("query", ""))

        elif name == "costar_search_residential":
            if not costar: return {"error": "CoStar service unavailable"}
            return costar.search_residential(args.get("query", ""))

        elif name == "tavily_search":
            return tavily_search(args.get("query", ""))

        return {"error": f"Unknown tool: {name}"}

    def do_POST(self):
        if self.path == "/api/chat":
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len == 0:
                self.send_json({"error": "Empty request body"}, status=400)
                return

            raw_body = self.rfile.read(content_len)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception:
                self.send_json({"error": "Invalid JSON"}, status=400)
                return

            raw_messages = payload.get("messages", [])
            if not raw_messages:
                self.send_json({"error": "No messages provided"}, status=400)
                return

            if not OPENROUTER_API_KEY:
                self.send_json({"error": "OPENROUTER_API_KEY is missing from environment."}, status=500)
                return

            # Format messages for OpenRouter / Nemotron
            messages = []
            for m in raw_messages:
                role = m.get("role")
                content = m.get("content")
                if role in ("user", "assistant", "system"):
                    messages.append({"role": role, "content": content or ""})

            # System prompt to guide CoStar queries and Tavily web research
            sys_msg = {
                "role": "system",
                "content": (
                    "You are Project Helix, an evidence-grounded Commercial Real Estate AI advisor. "
                    "You have two authoritative information engines:\n\n"
                    "1. COSTAR COMMERCIAL REAL ESTATE KIT (Verified Internal Ground Truth):\n"
                    "- Commercial Properties: Use costar_search_properties and costar_get_property to inspect building class, RBA/GFA, zoning, parking, sprinklers, stories, and linked Matterport scans.\n"
                    "- Active Listings & Suites: Use costar_get_listings_and_spaces to extract exact suite numbers, square footages, asking rents, rate basis, and lease basis (Full Service Gross vs NNN).\n"
                    "- Market Screening: Use costar_filter_spaces to screen all available spaces in Houston and Los Angeles by minimum/maximum square footage, asking rents, and sort order (e.g. sort_by='highest_rent' or 'lowest_rent').\n"
                    "- Tenancies & Occupancy: Use costar_get_tenants for recorded occupant company names and lease sizes.\n"
                    "- Past Sales & Valuation: Use costar_get_sale_comps for transaction history, sale prices, and cap rates.\n"
                    "- Apartments & Homes: Use costar_search_apartments for multifamily communities and costar_search_residential for single-family MLS listings. NEVER use apartment tools to answer commercial lease questions.\n\n"
                    "2. TAVILY LIVE WEB SEARCH (External Intelligence & Public Verification):\n"
                    "- Use tavily_search for independent rate verification, finding public broker listings (LoopNet, Crexi, city deeds), municipal permitting processes, competitors, or external web facts.\n"
                    "- Whenever the user asks to verify evidence publicly, search online, or check public records, you MUST call tavily_search.\n\n"
                    "STRICT ANTI-HALLUCINATION & TOOL CALLING DIRECTIVES:\n"
                    "1. NATURAL LANGUAGE ROUTING: Users will ask natural commercial real estate questions (e.g. 'What are the highest rents?', 'Find spaces on Tanner Rd', 'What's at 9800 Centre?') WITHOUT mentioning the word 'CoStar'. You must ALWAYS automatically call the database tools (costar_*) for any property, suite, rent, square footage, building, or market query.\n"
                    "2. NEVER FAKE URLS OR PUBLIC DEEDS: You are strictly FORBIDDEN from inventing URLs (e.g. costar.com/..., searchlosangeles.org) or fake deed numbers. Only cite real URLs returned by tavily_search.\n"
                    "3. NEVER PROMISE IN TEXT THAT YOU ARE RUNNING A TOOL: You cannot say 'Let me check...' or 'Re-running data...' in prose without emitting the actual tool_calls payload. If you want data, you MUST emit the tool call.\n"
                    "4. NO UNGROUNDED NUMBERS: If you generate text without calling a tool, you are STRICTLY PROHIBITED from inventing property names (e.g., 'The Grand Palladium'), fake rents (e.g., '$6.00/SF'), fake suites, or fake square footages.\n"
                    "5. COMPARISONS ACROSS CITIES: When asked for highest/lowest rents in Houston or Los Angeles, call costar_filter_spaces(city='Houston', sort_by='highest_rent') and costar_filter_spaces(city='Los Angeles', sort_by='highest_rent').\n"
                    "6. LEASE BASIS CLARITY: Always specify whether asking rents are Full Service Gross (operating expenses included) or NNN (taxes/insurance/CAM on top).\n"
                    "7. ADMIT LIMITATIONS: If a requested calculation or metric is not supported by your tools, state clearly: 'I do not have a tool to compute that directly.' Never fabricate an answer."
                )
            }
            if not any(m["role"] == "system" for m in messages):
                messages.insert(0, sys_msg)

            # Determine if round 0 should require a tool call
            latest_user_text = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    latest_user_text = m.get("content", "").strip().lower()
                    break

            is_greeting = latest_user_text in {"hi", "hello", "hey", "greetings", "good morning", "thanks", "thank you", "clear"}

            # Agentic tool calling loop (up to 4 steps)
            executed_tools_summary = []
            final_reply = ""
            max_rounds = 4

            try:
                for round_idx in range(max_rounds):
                    # Force tool execution on round 0 for substantive queries so the model cannot fake lookups
                    tc_choice = "required" if (round_idx == 0 and not is_greeting and bool(TOOLS)) else "auto"

                    req_data = {
                        "model": MODEL,
                        "messages": messages,
                        "tools": TOOLS,
                        "tool_choice": tc_choice,
                        "stream": False,
                    }

                    url = f"{OPENROUTER_BASE_URL}/chat/completions"
                    req = urllib.request.Request(
                        url,
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://hackprinceton.com",
                            "X-Title": "Project Helix"
                        },
                        data=json.dumps(req_data).encode("utf-8"),
                        method="POST"
                    )

                    # Bounded retry with exponential backoff on 429 rate limit or capacity (Free model route only)
                    resp_json = None
                    max_retries = 2
                    for attempt in range(max_retries + 1):
                        try:
                            with urllib.request.urlopen(req, timeout=45) as resp:
                                resp_json = json.loads(resp.read().decode("utf-8"))
                            break
                        except urllib.error.HTTPError as http_err:
                            if http_err.code in (429, 503) and attempt < max_retries:
                                time.sleep(1.5 * (attempt + 1))
                                continue
                            raise

                    choice = resp_json.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    tool_calls = message.get("tool_calls") or []

                    messages.append(message)

                    if not tool_calls:
                        final_reply = message.get("content", "")
                        break

                    for tc in tool_calls:
                        fn_name = tc.get("function", {}).get("name")
                        fn_args_raw = tc.get("function", {}).get("arguments", "{}")
                        try:
                            fn_args = json.loads(fn_args_raw)
                        except Exception:
                            fn_args = {}

                        t_start = time.time()
                        tool_output = self.execute_tool(fn_name, fn_args)
                        duration_ms = max(1, int(round((time.time() - t_start) * 1000)))
                        status = "error" if (isinstance(tool_output, dict) and "error" in tool_output) else "success"

                        executed_tools_summary.append({
                            "tool": fn_name,
                            "args": fn_args,
                            "output": tool_output,
                            "status": status,
                            "duration_ms": duration_ms
                        })

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id"),
                            "name": fn_name,
                            "content": json.dumps(tool_output)
                        })

                self.send_json({
                    "reply": final_reply,
                    "tool_calls": executed_tools_summary
                })

            except urllib.error.HTTPError as e:
                err_text = e.read().decode("utf-8", errors="replace")
                try:
                    err_json = json.loads(err_text)
                    err_msg = err_json.get("error", {}).get("message", err_text)
                except Exception:
                    err_msg = err_text
                self.send_json({"error": f"OpenRouter API error ({e.code}): {err_msg}"}, status=502)
            except Exception as e:
                self.send_json({"error": f"Server error: {str(e)}"}, status=500)
            return

        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        sys.stderr.write(f"[Helix Chat] {self.address_string()} - {format % args}\n")


def main():
    parser = argparse.ArgumentParser(description="Run Project Helix Chat Server with CoStar + Tavily")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser")
    args = parser.parse_args()

    port = args.port
    url = f"http://localhost:{port}"
    server = ThreadingHTTPServer(("127.0.0.1", port), ChatHandler)
    print(f"Project Helix Chat running at: {url}")
    print(f"Using Model: {MODEL}")
    print(f"CoStar Kit: {'Connected (' + str(COSTAR_KIT_PATH) + ')' if has_costar else 'Disconnected'}")
    print(f"Tavily Search: {'Enabled' if TAVILY_API_KEY else 'Disabled'}")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    main()
