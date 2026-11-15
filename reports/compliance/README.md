# Standalone compliance triage v1

Functions: `preflight(context)` before recommendation; `check_business(context, business, search=None, requirements=None)` after a business is shortlisted. No UI or shared interfaces changed. Any of Asmit's registry labels can be passed; this version does NOT implement 26 sets of legal rules.

Context: `{property_id, scope, jurisdiction: {code, verified, evidence_url}, facts: {property_type, area_sqft, clear_height_ft, floors, parking_spaces, hvac_capacity, fire_inspection}, identity_conflict, measurements_match_scope}`. Use jurisdiction codes `houston`, `harris_unincorporated`, `los_angeles`, `la_unincorporated`. Caller must independently establish jurisdiction; an address/postal city is not a boundary lookup. Unknown jurisdiction stops legal research. `verified` is caller attestation, not this module's verification.

Output preserves the canvas evidence fields and adds gates, business handoff permission, trace, retrieval errors, and research excerpts. Residential/identity conflicts stop business research. Scope-matched numeric thresholds are screening constraints, not building codes. All legal checks remain needs_verification; no permit or inspection is asserted. Image evidence cannot certify HVAC, sprinklers, structural integrity or parking compliance.

CLI: `python3 playground/compliance_engine.py context.json --business 'indoor pickleball'`. Add `--live` to opt into Tavily with TAVILY_API_KEY. Two bounded searches are restricted to configured official authority domains; failure retains unknowns and hides exception details. Search excerpts are untrusted and cannot clear gates. Live authenticated Tavily has NOT been tested in this session.

Test: `python3 -m unittest discover -s playground -p test_compliance_engine.py -v` (8 passed). Tests cover all four authority configurations, residential and identity gates, unknown jurisdiction/height, scope mismatch, threshold failure, source spoofing and provider outage. Synthetic fixtures only; no claim of actual parcel compliance.

Official references checked Nov 14, 2026:
- https://permits.lacounty.gov/permits/building-and-safety/ — use service locator to establish responsible permitting office; county/city distinction.
- https://oce.harriscountytx.gov/Services/Permits/Permits-A-to-Z/Commercial-Building — county commercial-building review.
- https://www.houstontx.gov/business/plan/permits-inspections.html — existing team Houston process reference.
- https://dbs.lacity.gov/services/search-online-building-records — existing team LA City records reference.

Remaining: map actual Stage 2 intake and Asmit registry, authoritative parcel boundary lookup, business-specific official licensing rules, source freshness/cache policy, public GIS and Vexcel/Matterport adapters, and authenticated search validation. This is a working triage foundation, not the completed compliance engine.
