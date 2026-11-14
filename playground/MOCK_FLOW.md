# Reuse mock product flow

This UI-only slice runs at `/` on `feature/pilot`. The earlier working provider /
Nessie pilot remains at `/pilot`; address search remains at `/search`.

## Run

Use the existing README environment + `web.py` command. The mock itself makes
no provider calls and requires no authentication. The existing server still
loads the local CoStar kit at startup. `--offline` applies to the separate pilot.

## Walkthrough

1. Enter a display name (demo login; no account, password or external request).
2. Pick Houston or Los Angeles; select a business or explore suggestions.
3. Choose buy/lease and enter property budget, fit-out ceiling, cash, reserve
   and desired opening horizon.
4. Browse examples filtered by city, transaction availability, use overlap,
   property budget and fit-out ceiling. Sort by use overlap and opening target.
   Capital is shown for later runway evaluation, not asserted as preapproval.
5. Select a property to start a six-stage **simulated** specialist review. Pause,
   resume, inspect individual outputs, or show the completed demo immediately.
6. Review contradictions, physical fit, location, approvals, money and handoff.
   Edit financial assumptions, illustrate a loan, mark checklist items reviewed,
   save in browser storage, or download a plain-text handoff.

The tiny catalog contains Tanner plus five synthetic examples. Every price,
availability, schedule and cost is illustrative. Tanner's source mismatch and
area context are carried over from the prior pilot, not fetched anew.

## Feature-dump coverage

| Requested family                                          | Mock surface                                                             |
| --------------------------------------------------------- | ------------------------------------------------------------------------ |
| Known business / open suggestions                         | Preferences; five business types; multi-select                           |
| Houston / Los Angeles; buy / lease; capital validation    | City + budget inputs, filtering, explicit tenant or owner-operator model |
| Visible outputs from each agent                           | Six selectable specialists with queued/running/ready state               |
| Source, date, scope, confidence; suite matching           | Evidence panel; dates explicitly unverified; source slots                |
| On-demand lie detector; occupancy, size, identity, time   | Contradiction check; no automatic fraud or vacancy finding               |
| Layout, clear height, parking, loading, power, HVAC       | Space panel; business-specific checklist and concept plan                |
| Roof / Jev photo checks / condition                       | Space panel; intended observations and inspection questions              |
| Foundation, plumbing, pests                               | Additional professional inspection checklist                             |
| Demographics, competitors, crime context, sales history   | Location panel; source slots, no fabricated statistics                   |
| Flood, environmental, LA hazard context                   | Location panel; unknowns, no invented mapped results                     |
| Use rules, approvals, insurance drivers                   | Approvals panel and named handoff owners                                 |
| Intelligent build timeline                                | Use/city context and dependency phases; duration remains a mock fixture  |
| Baseline, cash, delay, break-even, max fit-out/delay      | Financial panel; frontend deterministic example math                     |
| Funding gap / Nessie loan concept                         | Simulated amortizing loan; no account or transaction call                |
| Saved scenario, source context, rerun, inspection handoff | Local storage + download + review checklist + rerun                      |
| Lender / insurer / tax / owner / research applications    | Collapsed roadmap in handoff                                             |

## Financial mock limits

This is intentionally separate from `nessie_pilot.py`. The prototype demonstrates
interaction without pretending the backend has been connected. Lease scenarios
pay base rent + $2,000/month; purchase scenarios pay the example acquisition price
in cash at month 0 and $3,500/month carrying costs. Fit-out is spread before the
example opening month; additional delay postpones construction and revenue.
Business-type maximum revenue and operations are fixtures; utilization is editable.
The current-use comparison is a placeholder business with $18,000 revenue and
$7,000 operating cost from month 1. The example loan adds proceeds at month 0 and
payments at 10% APR over 60 months. Acquisition/financing paths do not imply a
mortgage offer or approval. Sensitivities hold other inputs fixed over 24 months.

## Next implementation boundaries

Replace demo session with authentication; catalog with scoped listings and
explainable matching; timer with real run events; report templates with dated,
source-linked claims; frontend money calculation with the existing simulator
adapter; browser save with versioned backend scenarios. Keep the distinction
between property facts, assumptions, inference and unresolved checks.
