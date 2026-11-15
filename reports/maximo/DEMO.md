# Maximo demo and validation

Run from repository root. `.env` stays ignored; the helper loads literal values without executing shell content. Do not commit sponsor kit, caches or credentials.

## Start

```sh
python3 playground/with_env.py python3 playground/web.py --kit "$HOME/Downloads/costar-hackathon-kit.zip" --port 8783 --offline --research-replay playground/output/maximo-live-verified.json
```

That replay file is a local, ignored live research capture created during acceptance testing. For another checkout, first run:

```sh
python3 playground/with_env.py uv run playground/location_run.py --public-only --use 'indoor pickleball' --output playground/output/maximo-live-verified.json
```

The replay is address/use matched. It cannot become Wynnwood or fitness evidence. Source observation dates stay visible. `--offline` uses saved sponsor responses; this is not a claim of refreshed data. Remove both offline/replay flags for live provider/model research. Live results can be partial or unavailable. Inline Matterport still needs network access.

## Two-minute walkthrough

Warm the three property reviews before presenting; initial encrypted-kit reads and provider requests take longer than cash edits. The server caches tenancy parsing only, invalidated by kit modification time.

1. **0:00–0:25:** `/maximo?property=966604` — Cypresswood. Run review: multifamily + 2-bedroom tour + no commercial premises. No actionable fit, demand or cash. Hypothetical calculator requires an explicit click and stays labeled.
2. **0:25–1:10:** `/maximo?property=23296&capital=500000` — Tanner Suite A. Run review. Show three conditional options, 9700/9750 tour mismatch and transparent planning-cost basis. $8,500 is base rent; assumed $2,000 NNN is separate. Costs are NOT contractor estimates. Drop cash to $320k in the cash controls and add three months: opening moves to month 7 and the current itemized scenario has a $60k reserve gap. (The older lump-sum pilot's $5k gap is a different scenario.)
3. **1:10–1:35:** Show the cost ledger, permit prerequisites and saved competitor capture. Casa Pickle — Galleria was source-validated at 8.24 straight-line miles in the tested capture. It does not verify paid demand, prices, driving time or booking assumptions. The farther Space City location was excluded.
4. **1:35–2:00:** Wynnwood 13890701: explicitly choose **9,900 sq ft (unnamed)**, not building-only or 27,750 SF. Show conditional scope and $7,920 listed rent, then the concrete next checks. No saved Tanner research is reused here.

## Verification commands

```sh
python3 playground/verify_suite.py
COSTAR_KIT="$HOME/Downloads/costar-hackathon-kit.zip" python3 playground/with_env.py python3 playground/verify_suite.py
node --check playground/static/maximo.js
python3 -m py_compile playground/*.py
git diff --check
```

`verify_suite.py` runs Git-tracked tests only. Ordinary unittest discovery also picks up seven pre-existing, untracked teammate space-condition tests; these pass locally but are not part of this PR. Seven known-case tests require the kit/password and cached provider responses; missing inputs cause explicit skips. During acceptance, all missing caches were fetched and all seven executed successfully.

## Boundaries

- Construction quantities/rates are allocations of editable allowances, with no verified quote dates. Get use-specific bids. Warehouse uses the baseline allowance; this is not evidence that conversion is actually cheaper.
- Parcel IDs are recorded CoStar context. Municipal boundary, suite approval, private restrictions and agency durations remain unverified; checklist applicability is conditional.
- Solar/Tavily can fail, reach recursion limits or return irrelevant pages. Unsupported names, addresses, categories and prices are rejected. The accepted live capture proves one successful pathway, not comprehensive competition coverage.
- Revenue remains an assumption. Primary cash/ranking are unfinanced; the optional loan is a separate hypothetical sensitivity. Nessie is a sandbox, not a real balance or credit offer.
- Attachment date is not camera capture date; missing clear height and implausible roof heights remain unknown. Building, advertised suite and scan scopes remain distinct.
