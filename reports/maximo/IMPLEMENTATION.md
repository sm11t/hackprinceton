# Maximo sequential implementation

## Stage 0 — baseline and additive contract

Baseline command: `python3 -m unittest discover -s playground -v`: 139 tests, 132 pass, 7 skip because COSTAR_KIT was unset. With kit path and password loaded from ignored environment: 133 pass, 6 skip. Missing cached Vexcel files: 9292792 (Grant), 237647 (Northgreen), 239686 (Willow), 13890701 (Wynnwood, three tests). These are not passes. Attempt with kit but no password failed and was corrected by loading environment.

Trace: browser POST /api/maximo/run -> local CoStar property/listed-space and deal readers -> eligibility -> gather cached/live Matterport + Vexcel -> reconciliation + physical fit -> approvals + optional location Deep Agents research -> money_runway -> Jayant's nessie_pilot.simulate. Blocked eligibility returns before gather, research and cash. Standalone cash endpoint requires explicit scenario_only opt-in. Nessie balances are sandbox data; without account configured all balance inputs are assumptions.

DecisionContext is an additive typed envelope preserving the existing evidence record shape. Scope includes unnamed listing tokens, not inferred suite names. Model output cannot modify eligibility. Provider errors remain partial evidence, unknown measurements remain unknown. CoStar attachment dates are not camera capture dates (corrected stale Slack spec). Older occupancy calculations use attachment timing as a proxy; their findings require human verification.

Real-kit HTTP baseline: Cypresswood 966604 blocked / no cash; Tanner 23296 Suite A conditional / $8,500 monthly base rent; Wynnwood 13890701 listing:37112018:9900 conditional / $7,920. Saved provider coverage is incomplete. Tanner address mismatch persists, Wynnwood listing scope does not imply verified tour identity. No parcel zoning or paid demand established.

## Stage 1 — budget-first alternatives

Catalog screens six uses with deterministic property-type applicability, separate per-use physical checks, listing scope, identity caveats, permission and demand unknowns. Up to three conditional candidates; exclusions remain inspectable. Initial budget screening is explicitly only reserve + one month base rent; total cash is unknown until Stage 2, never represented as affordable. Requested use breaks evidence ties. Browser assets now include cash/reserve inputs, next checks and options; changing properties clears prior results. Validation: 146 tests, 139 pass / 7 skip; JS syntax passes. Browser end-to-end will be repeated after the ledger is wired. No costs or approvals fabricated.

## Stage 2 — editable ledger

Cost ledger includes construction allocations, deposit, acquisition, insurance/legal, preopening marketing/payroll, contingency and retained reserve. Low/base/high quantities/rates/amounts, payer, classification, geography, assumption date, confidence and source fields are explicit. Default allocation of the user-entered build allowance is **not** a market price estimate; no quote date is invented. Null line costs make totals unknown. Landlord-paid work is excluded; deposits are separate from rent; purchase has no lease deposit/rent. UI exposes line edits and recalculates totals/shortfall. All options initially share the user's envelope until separate bids establish differences. Stage 5 will reconcile the ledger into the chart (current chart remains labeled standalone assumption). Tests: 152 total / 145 pass / 7 skip, JS syntax and diff check pass.

## Stage 3 — parcel/suite approval path

Added recorded parcel IDs (not official matching), exact selected scope, conflict gate and seven-step prerequisite sequence. Each step includes authority, official reference where available, applicability, null agency duration, blocker and human action. Houston/LA use distinct references; other jurisdictions remain generic. No municipal boundary lookup or parcel-specific permission has yet been verified; therefore no rules are asserted as applicable to a site. Live-read Houston permit/CO page and current LADBS property records page; LA zoning page timed out, so it remains a lookup destination, not fetched parcel evidence. Tests: 158 total / 151 pass / 7 skip. Existing jurisdiction proof contract remains unchanged. Full browser path verification in Stage 6.

## Stage 4 — validated local competitors

Extended existing sequential Deep Agents property/market/validator harness with structured operator extraction and independent accepted operator IDs. Server then checks copied name/address/category against the cited original extract, category match, city, observation freshness, duplicates and copied price. Census geocoding computes a 10-mile straight-line screening radius; missing coordinates remain distance-unverified, not a drive-time assertion. Research runs separately for shortlisted uses. Search errors yield demand unverified, never zero competition. ACS/flood remain context. Live first pass completed Solar/Tavily/validator but rejected all three candidates (two nonmatching category descriptions and one source mismatch); this is reported as unverified, not a success finding. Search narrowed away from equipment retailers/directories; retry in progress. Deterministic suite: 165 tests, 158 pass / 7 skip, JS syntax pass. Live evidence outputs stay ignored, not Git.
