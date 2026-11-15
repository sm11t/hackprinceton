# Pre-Stage-2 vision intelligence research spike

**Status: partial completion with provider blockers.** This is an isolated research harness on `research/helix-vision-spike`, based on validated Stage 1 commit `06d95d5`. It does not change Helix production behavior and does not integrate legacy code.

## Selected property and sources

- CoStar property ID `236138`, 15603 W Hardy Rd, Houston, Texas; coordinates 29.944369, -95.385271.
- CoStar supplied Matterport model ID `NDMWnz1H9uV`; read-only GraphQL found the exact same address, model active and `public`, not a demo. Matterport documents the GraphQL endpoint and Model API access to images, panoramas, positions and model details ([Model API overview](https://developers.matterport.com/api/model/overview/)). No public setting, model, or asset was modified.
- Queried data reports 4 rooms, 1 floor, 36 locations/panoramas, all with available skyboxes. One room's API geometry reports about 5,002 sq ft. Position coordinates are Matterport-local; the response did not provide a CRS. Model created/modified timestamps (Nov 10/12, 2026) are API model timestamps, **not** asserted camera capture dates. No capture timestamp or creator attribution was returned.
- Downloaded six 1024×1024 skybox faces from one authorized indoor panorama. Manifest, retrieval timestamp, IDs, position, visibility, byte sizes, dimensions, hashes and caveats are in the local ignored sample dataset. Three indoor faces were used for the VLM run. No exterior view was present in this sample.

## Provider connectivity

### Vexcel

The official [Vexcel v2 API](https://api.vexcelgroup.com/v2/) and [v1-to-v2 operation mapping](https://vexcel.atlassian.net/wiki/spaces/APIDOCS/pages/3035136040/API%2BMigration%2BGuide+from+1.0+to+2.0) were inspected. Relevant operations include oriented coverage/metadata/extract, orthomosaic dates/coverage and property extract generation. Read-only oriented coverage, oriented metadata, orthomosaic dates and orthomosaic coverage probes each returned HTTP 401 with a credential present. No extraction was attempted because authorization and licensed-asset entitlement/cost could not be verified. Consequently there is no Vexcel coverage result or imagery in this spike. The supplied credential needs Vexcel-side authorization/entitlement review.

### Matterport

The documented read-only Model API succeeded (HTTP 200, no GraphQL errors) and matched the exact selected CoStar property; no unrelated-property sample was needed. Read-only requests fetched model metadata, rooms, floors, locations, panorama references, skybox availability, position data and one room's dimensions. The provider API did not expose a capture timestamp or geographic CRS in the queried fields. The local sample is a small permitted public-model sample; third-party source images were not added to git.

### Perceptron Mk1

The [official Perceptron SDK](https://github.com/perceptron-ai-inc/perceptron) was inspected. Its own API credential is absent, and the SDK is not installed. The dry-run adapter records `blocked`, names the requested `perceptron-mk1`, and records target classes without invoking the service or inventing detections. Therefore configuration B (raw image + Perceptron localizations → VLM) was not run, and no Perceptron overlay/detection artifact exists. Provide an authorized Perceptron key to unblock.

## Raw-image VLM comparison

Verified the exact model IDs against the live OpenRouter catalog and checked vendor release information and image support. DeepSeek V4.1 Flash released Sept 10, 2026 with native visual understanding and the tested `1017` snapshot was updated Oct 17 ([DeepSeek release](https://www.deepseek.com/en/news/deepseek-v4-1-flash/), [API changelog](https://api-docs.deepseek.com/updates/)). Qwen3.8 Flash released Aug 26, 2026, and its vendor documentation describes image understanding ([QwenCloud model changelog](https://docs.qwencloud.com/changelog/models)). Both meet the July 2026 cutoff. OpenRouter catalog entries reported `text+image` input for both; prices at catalog retrieval were approximately DeepSeek $0.038/M input and $0.50/M output tokens; Qwen $0.15/M and $0.47/M. Actual billed amounts below come from response usage, rather than catalog estimates.

Three identical 1024×1024 indoor faces × two exact model IDs were sent as raw image inputs with the same prompt, temperature 0, and reasoning disabled. All 6 final calls returned HTTP 200, valid/parseable JSON observations (Qwen fenced JSON was parsed), with finish reason `stop`. No VLM confidence value was used as ground truth.

| Model | Mean latency | Provider-reported cost, 3 calls | Mean cost/call | Manual box match precision | Manual box match recall |
|---|---:|---:|---:|---:|---:|
| `deepseek/deepseek-v4.1-flash-1017` | 2,453 ms | $0.000883 | $0.000294 | 10/19 = 0.526 | 10/16 = 0.625 |
| `qwen/qwen3.8-flash` | 7,830 ms | $0.001195 | $0.000398 | 7/14 = 0.500 | 7/16 = 0.438 |

Box metric method: one reviewer manually labeled approximate visible-object boxes on three images (16 total); predictions greedily matched same broad class at IoU ≥ 0.50, per face. Unsupported or unmatched visible boxes count as false positives. This tiny hand-labeled sample is not an accuracy claim and has no second annotator/adjudication. The comparison highlights that doors and large electrical panels are localized consistently, while broad features (partitions, electrical devices) vary in box extent and a sprinkler-like interpretation is uncertain/possibly false positive. No systematic precision/recall conclusion should be drawn from one property.

The raw responses showed the importance of request settings: an initial six-call run used default reasoning and returned no user-visible content before token limits; another six-call iteration exposed coordinate-scale inconsistencies. Both iterations were discarded from model comparison. Their provider-reported billed cost plus the final run totaled approximately **$0.006736** over 18 calls; the final comparable six calls cost **$0.002078**. `evaluated_results.json` records the final call usage, latency, outputs, box counts and overlays. The earlier exploratory responses are retained only in the ignored raw output.

## Overlays and evidence

Original faces, exact source manifest, approximate manual labels, and six model overlays are under the ignored local path `research/vision_spike/output/matterport_sample/paup35hdhemsueprdyas7xtub/`. In each overlay, red rectangles and yellow labels show that model's returned visible-object boxes. Original imagery, annotated imagery and machine-readable results are all present locally; third-party imagery remains uncommitted. The committed sanitized comparison is [results.json](results.json).

## Findings and recommended direction

1. **Proceed with a two-part visual evidence chain only after entitlements are ready:** licensed Vexcel exterior imagery plus Matterport interior scan (when the exact-property match exists) → Perceptron Mk1 localized candidates → a VLM constrained to interpret those regions and cite the image/evidence ID. Keep raw-image VLM as a control configuration.
2. Keep every generated visual claim tied to source image ID, face/panorama ID, normalized geometry, source coordinates, retrieval/acquisition timestamp and permission/attribution provenance. Preserve model observations separately from CoStar listing facts.
3. Gate abstention and structured-output correctness before using visual results downstream. Never infer engineering condition, code compliance, or unobserved geometry from these labels.
4. This spike does **not** justify selecting a winner: the sample is one property and three views; Perceptron-conditioned comparison is blocked; Vexcel exterior coverage is blocked. The raw comparison suggests DeepSeek was faster and slightly cheaper in this run, while measured micro precision/recall is inconclusive.

## Blockers and next steps

- Have Vexcel enable the API credential for the required coverage/metadata products and confirm extraction entitlements and any cost before imagery download.
- Provide Perceptron Mk1 API access, then run configuration B on this same authorized sample with Perceptron box/point/polygon output preserved.
- If Vexcel confirms coverage at this property's coordinates, use only a permitted low-volume sample and record source IDs, image capture/acquisition time, dimensions, CRS, license and attribution.
- Expand hand-labeled evaluation to several authorized properties/views with independent review before ranking architectures or reporting meaningful detection metrics.
- Do not integrate this research harness into Helix production or begin Stage 2 business analysis until the separate review/authorization.
