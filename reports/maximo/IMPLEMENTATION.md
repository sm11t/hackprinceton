# Maximo sequential implementation

## Stage 0 — baseline and additive contract

Baseline command: `python3 -m unittest discover -s playground -v`: 139 tests, 132 pass, 7 skip because COSTAR_KIT was unset. With kit path and password loaded from ignored environment: 133 pass, 6 skip. Missing cached Vexcel files: 9292792 (Grant), 237647 (Northgreen), 239686 (Willow), 13890701 (Wynnwood, three tests). These are not passes. Attempt with kit but no password failed and was corrected by loading environment.

Trace: browser POST /api/maximo/run -> local CoStar property/listed-space and deal readers -> eligibility -> gather cached/live Matterport + Vexcel -> reconciliation + physical fit -> approvals + optional location Deep Agents research -> money_runway -> Jayant's nessie_pilot.simulate. Blocked eligibility returns before gather, research and cash. Standalone cash endpoint requires explicit scenario_only opt-in. Nessie balances are sandbox data; without account configured all balance inputs are assumptions.

DecisionContext is an additive typed envelope preserving the existing evidence record shape. Scope includes unnamed listing tokens, not inferred suite names. Model output cannot modify eligibility. Provider errors remain partial evidence, unknown measurements remain unknown. CoStar attachment dates are not camera capture dates (corrected stale Slack spec). Older occupancy calculations use attachment timing as a proxy; their findings require human verification.

Real-kit HTTP baseline: Cypresswood 966604 blocked / no cash; Tanner 23296 Suite A conditional / $8,500 monthly base rent; Wynnwood 13890701 listing:37112018:9900 conditional / $7,920. Saved provider coverage is incomplete. Tanner address mismatch persists, Wynnwood listing scope does not imply verified tour identity. No parcel zoning or paid demand established.

## Stage 1 — budget-first alternatives

Catalog screens six uses with deterministic property-type applicability, separate per-use physical checks, listing scope, identity caveats, permission and demand unknowns. Up to three conditional candidates; exclusions remain inspectable. Initial budget screening is explicitly only reserve + one month base rent; total cash is unknown until Stage 2, never represented as affordable. Requested use breaks evidence ties. Browser assets now include cash/reserve inputs, next checks and options; changing properties clears prior results. Validation: 146 tests, 139 pass / 7 skip; JS syntax passes. Browser end-to-end will be repeated after the ledger is wired. No costs or approvals fabricated.
