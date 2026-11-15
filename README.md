# MAXIMUS: what could you open with your savings, and where?

**HackPrinceton Fall 2026.** A first-time founder has a budget and maybe an idea. MAXIMUS checks every space for lease in
Houston against 26 kinds of business and tells them which combinations survive the building, the money, the
neighborhood and the permits, with a source behind every number and an honest "unknown" where the data runs out.

Most new businesses pick a location by looking at a handful of listings. The expensive mistakes (a lease in a building
that can't legally host the use, a build-out that costs twice the estimate, an address that says "Houston" but sits
outside city limits) only show up after money is spent. MAXIMUS surfaces them before the lease is signed.

## The 2-minute demo

1. **Your bank, from Capital One Nessie.** The user's balance and recurring bills come from a Nessie sandbox account
   (simulated bank data, labelled as such). The balance becomes the budget.
2. **61,620 futures.** 2,370 listed Houston spaces × 26 business types. At a $500k budget with a $50k reserve:

   | Gate | Combinations left |
   |---|---|
   | Every space × every business | 61,620 |
   | The building can host it (size, ceiling, floors, building type) | 13,263 |
   | Cash to open fits the budget (sourced costs, deposit, rent while building, reserve) | 7,399 |
   | The neighborhood supports it (demand, competitors, who lives there) | 1,265 |
   | A permitting authority is known for the pin | 1,257 |

3. **Investigate one pick.** A team of agents (building, money, neighborhood, records, permits) each report what they
   found and where it came from, then the verdict (GO / CONDITIONAL / NO-GO) with every reason behind it, grouped as
   blocks, needs a check, supports and unknown, and what would flip it.
4. **Can it legally open here?** Jurisdiction comes from the pin, not the postal city:
   *9721 Cypresswood Dr* has a Houston address but is in unincorporated Harris County, and CoStar records it as
   residential, so it stops at the building check before any business research.
5. **12 months of cash, and borrowing.** Month-by-month balance with zero revenue, opening on time vs 3 months late,
   against the reserve. If a pick costs more than the budget, a Nessie business loan is sized for the gap and the year
   is rerun (assumed APR, labelled; not a credit offer). The loan and the `/flow` story view arrive with PR #26.

Demo picks, from real numbers: a salon at 11220 Louetta is **GO** ($297k to open); childcare at 9700 Tanner Rd at
$750k is **CONDITIONAL** (outdoor play space not recorded); indoor pickleball at 6855 Wynnwood Ln is **NO-GO**
($510k–$898k sourced cost to open against a $500k budget).

## Rules it follows

- **Every number has a source** (CoStar record, franchise disclosure table, official city page, Census boundary), and
  a date.
- **Unknown stays unknown.** Missing data is shown as unknown, never filled with a guess. Postal city is never used as
  jurisdiction.
- **Nothing is "approved".** Permit and license items stay "needs verification"; web results can't clear a gate.
- **No invented revenue.** Cash views show costs and bills only.
- **Works offline.** Every live lookup is cached, and the demo replays from the cache with no network.

## Run it

Needs **Python 3.10+** (macOS `/usr/bin/python3` is 3.9) and the standard library only.

```bash
git clone https://github.com/sm11t/hackprinceton.git && cd hackprinceton
cp .env.example .env    # fill in the values (team members: #env-keys)
```

Put the CoStar sponsor kit at `~/Downloads/costar-hackathon-kit.zip` (leave it zipped). Then:

```bash
python3 playground/with_env.py python3 playground/opportunity.py --kit ~/Downloads/costar-hackathon-kit.zip --build
```

That builds the scan index once per laptop. It does one neighborhood investigation per listed building, so it takes
several minutes the first time; afterwards a $500k scan takes about 150 ms.

```bash
python3 playground/with_env.py python3 playground/suite_nessie.py --seed     # once: create the Nessie demo account
python3 playground/with_env.py python3 playground/web.py --kit ~/Downloads/costar-hackathon-kit.zip
```

Open <http://127.0.0.1:8765/suite>. Before judging, warm everything and prove the demo path works with no network:

```bash
python3 playground/with_env.py python3 playground/suite_prep.py --kit ~/Downloads/costar-hackathon-kit.zip
python3 playground/with_env.py python3 playground/suite_prep.py --offline-only --warm-server http://127.0.0.1:8765
```

Tests: `python3 playground/with_env.py python3 playground/verify_suite.py` (311 tests; 7 real-kit cases are skipped
without the kit and cached sponsor responses).

`with_env.py` loads `.env` without printing any value. `.env`, the kit and everything under `playground/output/`
stay local and are gitignored.

## Sponsor technology

| Sponsor | Used for |
|---|---|
| **CoStar** (hackathon kit) | Every listed space, asking rents, building facts (size, ceiling, floors, type), tenants |
| **Capital One Nessie** | The user's balance and recurring bills; business loans stored as pending Nessie loan records (`nessie_loan.py`, PR #26) |
| **Vexcel** | Aerial imagery of the building |
| **Matterport** | Interior scans and 3D tours linked to the property |
| **NVIDIA Nemotron** (via OpenRouter, free route) | The optional LangChain neighborhood agent (`neighborhood_agent.py`) |
| **Tavily** | Searches restricted to official city and county domains for permit and license pages |
| U.S. Census geocoder (public) | Which city or county a pin is in |

## What's in the repo

| Path | What |
|---|---|
| `playground/web.py` | The server: `/suite` (the venture suite) and its APIs |
| `playground/opportunity.py`, `venture_costs.py`, `venture_review.py`, `ventures.py` | The scan, sourced cash to open, the per-pick agent review, saved ventures |
| `playground/neighborhood*.py` | Neighborhood demand for the 26 business types |
| `playground/jurisdiction.py`, `compliance_engine.py` | Who permits it (from the pin), the building check, the business-specific check |
| `playground/nessie_pilot.py`, `suite_nessie.py`, `money_runway.py` | Nessie bank data and the month-by-month cash simulation |
| `playground/market_rank.py`, `rent_model.py`, `space_fit.py`, `reconcile.py` | Ranking listed spaces, rent estimates, space fit, CoStar-vs-scan checks |
| `reports/` | Design notes, the compliance write-up and demo script, data pilots |

## Limits

- Houston only for the scan; jurisdiction lookup also covers Los Angeles and LA County.
- Opening costs are benchmarks (mostly franchise disclosure documents) scaled to the space, not contractor quotes.
- Permit research finds official process pages, not rules confirmed for a specific parcel.
- Loan terms (APR, term, down payment) are assumptions; Nessie is a sandbox, not a bank connection.

## Team

Built during HackPrinceton Fall 2026 by Asmit, Jessenth and Jayant.
