# Pre-Stage-2 vision intelligence research spike

**Status: research spike complete; Vexcel connectivity and a small matched-property exterior sample are confirmed.** This is an isolated research harness on `research/helix-vision-spike`, based on validated Stage 1 commit `06d95d5`. It does not change Helix production behavior and does not integrate legacy code.

## Selected property and sources

- CoStar property ID `236138`, 15603 W Hardy Rd, Houston, Texas; coordinates 29.944369, -95.385271.
- CoStar supplied Matterport model ID `NDMWnz1H9uV`; read-only GraphQL found the exact same address, model active and `public`, not a demo. Matterport documents the GraphQL endpoint and Model API access to images, panoramas, positions and model details ([Model API overview](https://developers.matterport.com/api/model/overview/)). No public setting, model, or asset was modified.
- Queried data reports 4 rooms, 1 floor, 36 locations/panoramas, all with available skyboxes. One room's API geometry reports about 5,002 sq ft. Position coordinates are Matterport-local; the response did not provide a CRS. Model created/modified timestamps (Nov 10/12, 2026) are API model timestamps, **not** asserted camera capture dates. No capture timestamp or creator attribution was returned.
- Downloaded six 1024×1024 skybox faces from one authorized indoor panorama. Manifest, retrieval timestamp, IDs, position, visibility, byte sizes, dimensions, hashes and caveats are in the local ignored sample dataset. Three indoor faces were used for the VLM run. No exterior view was present in this sample.

## Provider connectivity

### Vexcel

The official [Vexcel v2 API](https://api.vexcelgroup.com/v2/) and [v1-to-v2 operation mapping](https://vexcel.atlassian.net/wiki/spaces/APIDOCS/pages/3035136040/API%2BMigration%2BGuide+from+1.0+to+2.0) were inspected alongside the user-supplied Vexcel hackathon tutorial PDF and `vexcel_quickstart.py`. The first probe incorrectly sent the API key as a `token` query parameter, producing misleading 401s. The supplied helper showed the documented `X-API-KEY` header; after correcting the request, all tested read-only operations and the small selected-property image extracts returned HTTP 200. This was an integration bug in our probe, not evidence of missing Vexcel authorization.

For CoStar property `236138` (15603 W Hardy Rd, Houston; 29.944369, -95.385271), `property/extract` returned seven parcel candidates. The point-matching parcel selected collection `us-tx-cypress-2026`, with ortho estimate 2026-01-02. Oriented coverage and metadata returned 25 and 181 features respectively before parcel filtering; four matching source images were identified: north, east, south and west obliques, captured on 2026-01-02 between 17:25:42 and 18:29:39 UTC. The selected collection's orthomosaic date response reports capture range 17:43:12–18:06:35 UTC. Coverage, metadata and dates all returned HTTP 200. Five explicit, low-resolution extracts (one orthomosaic and four obliques) returned HTTP 200 as 800×800 JPEGs. Source IDs, image hashes, dimensions, capture/publish dates, WGS84 coordinates, provider attribution and retrieval time are recorded in the local ignored manifest under `output/vexcel_sample/costar-236138/manifest.json`. The sample contact sheet is local-only. No property/image result is presented as a CoStar field.

To gauge city inventory coverage, the CoStar kit's listing CSV (7,163 Houston and 5,984 Los Angeles rows) was joined with property detail records. Coordinates were present for 1,758 Houston and 1,581 Los Angeles properties; the primary listing CSV itself has no coordinates. A fixed-seed simple random sample of 100 coordinate-bearing properties in each city was checked against `oriented/collections` and `ortho/collections`, without downloading inventory imagery. All 100/100 points in each city had both types of Vexcel coverage. Of these samples, 99/100 in each city linked to at least one Matterport model, and all those linked samples had both types of Vexcel coverage. This is promising sampled evidence, not a complete inventory census or a guarantee for non-geocoded records. Full response rows are retained in the ignored `output/vexcel_inventory_sample.json`.

### Matterport

The documented read-only Model API succeeded (HTTP 200, no GraphQL errors) and matched the exact selected CoStar property; no unrelated-property sample was needed. Read-only requests fetched model metadata, rooms, floors, locations, panorama references, skybox availability, position data and one room's dimensions. The provider API did not expose a capture timestamp or geographic CRS in the queried fields. The local sample is a small permitted public-model sample; third-party source images were not added to git.

### Perceptron Mk1

The [official Perceptron SDK](https://github.com/perceptron-ai-inc/perceptron) was inspected. My initial check looked only for a separate `PERCEPTRON_API_KEY`, which was the wrong gate for this setup. [OpenRouter lists the exact `perceptron/perceptron-mk1` model](https://openrouter.ai/perceptron/perceptron-mk1), with image input, structured localization formats, and $0.15/M input and $1.50/M output pricing. Its listed May 12, 2026 release predates the VLM date cutoff, but Mk1 was explicitly exempt in the task. The existing OpenRouter key successfully routed image calls. The first three-call attempt exposed inconsistent coordinate scales and one malformed box, so it was not used. A strict JSON Schema retry returned valid localized detections on all three images, with integer coordinates on a 0–1000 grid.

On the same small manual label set and same-class IoU ≥ 0.50 scoring rule, Mk1 recorded 5 TP / 4 FP / 11 FN (precision 0.556, recall 0.313). Broad boxes sometimes included adjacent areas, explaining some low localization matches. This is exploratory only. Machine-readable detections and overlays are present locally; sanitized detections and measured usage are committed in `results.json`.

## Raw-image VLM comparison

Verified the exact model IDs against the live OpenRouter catalog and checked vendor release information and image support. DeepSeek V4.1 Flash released Sept 10, 2026 with native visual understanding and the tested `1017` snapshot was updated Oct 17 ([DeepSeek release](https://www.deepseek.com/en/news/deepseek-v4-1-flash/), [API changelog](https://api-docs.deepseek.com/updates/)). Qwen3.8 Flash released Aug 26, 2026, and its vendor documentation describes image understanding ([QwenCloud model changelog](https://docs.qwencloud.com/changelog/models)). Both meet the July 2026 cutoff. OpenRouter catalog entries reported `text+image` input for both; prices at catalog retrieval were approximately DeepSeek $0.038/M input and $0.50/M output tokens; Qwen $0.15/M and $0.47/M. Actual billed amounts below come from response usage, rather than catalog estimates.

Three identical 1024×1024 indoor faces × two exact model IDs were sent as raw image inputs with the same prompt, temperature 0, and reasoning disabled. All 6 final calls returned HTTP 200, valid/parseable JSON observations (Qwen fenced JSON was parsed), with finish reason `stop`. No VLM confidence value was used as ground truth.

| Model | Mean latency | Provider-reported cost, 3 calls | Mean cost/call | Manual box match precision | Manual box match recall |
|---|---:|---:|---:|---:|---:|
| `deepseek/deepseek-v4.1-flash-1017` | 2,453 ms | $0.000883 | $0.000294 | 10/19 = 0.526 | 10/16 = 0.625 |
| `qwen/qwen3.8-flash` | 7,830 ms | $0.001195 | $0.000398 | 7/14 = 0.500 | 7/16 = 0.438 |

### Configuration B — raw image + Perceptron localization → VLM

The same three images and base prompt were sent with the corresponding Mk1 detections appended as evidence. All six calls returned HTTP 200 with parseable output.

| Model | Mean latency | Reported cost, 3 calls | Manual box precision | Manual box recall |
|---|---:|---:|---:|---:|
| `deepseek/deepseek-v4.1-flash-1017` | 1,856 ms | $0.000751 | 7/14 = 0.500 | 7/16 = 0.438 |
| `qwen/qwen3.8-flash` | 6,431 ms | $0.001037 | 6/9 = 0.667 | 6/16 = 0.375 |

Conditioning improved Qwen's precision but reduced recall relative to its raw-image result; DeepSeek's precision and recall both declined. This one-property sample is too small for a general conclusion about Perceptron conditioning.

Box metric method: one reviewer manually labeled approximate visible-object boxes on three images (16 total); predictions greedily matched same broad class at IoU ≥ 0.50, per face. Unsupported or unmatched visible boxes count as false positives. This tiny hand-labeled sample is not an accuracy claim and has no second annotator/adjudication. The comparison highlights that doors and large electrical panels are localized consistently, while broad features (partitions, electrical devices) vary in box extent and a sprinkler-like interpretation is uncertain/possibly false positive. No systematic precision/recall conclusion should be drawn from one property.

The raw responses showed the importance of request settings: initial VLM calls using default reasoning returned no user-visible content before token limits; another iteration exposed coordinate-scale inconsistencies. An initial Mk1 attempt also returned mixed coordinate scales and malformed JSON. These were excluded from scoring. Across 30 billed image calls in the spike, reported total cost was approximately **$0.011330**. The final comparable A/B experiment (six raw-image VLM calls, three Mk1 calls, six conditioned VLM calls) cost approximately **$0.005276**. Per-call usage, latency, detections and overlays are in ignored output files; `results.json` contains sanitized observations and comparison metrics.

## Overlays and evidence

Original faces, provenance manifest, approximate manual labels, Perceptron overlays, and twelve VLM overlays are under the ignored local path `research/vision_spike/output/matterport_sample/paup35hdhemsueprdyas7xtub/`. Red rectangles show model boxes; manual label overlays use blue. Third-party source images remain uncommitted. The sanitized detections and metrics are in [results.json](results.json).

## Findings and recommended direction

1. **A two-part visual evidence chain is technically viable on the sampled property:** Vexcel exterior imagery plus the exact-property Matterport interior scan → Perceptron Mk1 localized candidates → a VLM constrained to interpret those regions and cite the image/evidence ID. Keep raw-image VLM as a control configuration. Confirm permitted scope/usage charges before expanding beyond this deliberately small sample.
2. Keep every generated visual claim tied to source image ID, face/panorama ID, normalized geometry, source coordinates, retrieval/acquisition timestamp and permission/attribution provenance. Preserve model observations separately from CoStar listing facts.
3. Gate abstention and structured-output correctness before using visual results downstream. Never infer engineering condition, code compliance, or unobserved geometry from these labels.
4. This spike does **not** justify selecting a winner: the evaluated vision-model sample is one property's three indoor views. DeepSeek was faster and slightly cheaper in this run. Qwen with Mk1 context had higher observed precision but lower recall than raw-image Qwen; the measurements are inconclusive beyond this sample. Vexcel connectivity is confirmed, but only one property's exterior imagery was extracted and city-wide coverage was tested at 100 points per city.

## Blockers and next steps

- There is no current Vexcel authentication blocker. Before scaling imagery extraction, confirm the credential's permitted volume and any usage charges; this probe's API responses do not report a charge amount.
- Perceptron Mk1 and configuration B are now confirmed working through OpenRouter; the separate Perceptron credential is unnecessary for this route.
- Extend the city coverage join only after obtaining coordinates for more of the CoStar inventory; current detail records cover 1,758/7,163 Houston and 1,581/5,984 Los Angeles rows. Keep coverage queries separate from image extraction and retain the sample/usage limits.
- Expand hand-labeled evaluation to several authorized properties/views with independent review before ranking architectures or reporting meaningful detection metrics.
- Do not integrate this research harness into Helix production or begin Stage 2 business analysis until the separate review/authorization.
