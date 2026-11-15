# Pre-Stage-2 vision intelligence research spike

**Status: research spike complete with Vexcel access blocker.** This is an isolated research harness on `research/helix-vision-spike`, based on validated Stage 1 commit `06d95d5`. It does not change Helix production behavior and does not integrate legacy code.

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

1. **Proceed with a two-part visual evidence chain only after entitlements are ready:** licensed Vexcel exterior imagery plus Matterport interior scan (when the exact-property match exists) → Perceptron Mk1 localized candidates → a VLM constrained to interpret those regions and cite the image/evidence ID. Keep raw-image VLM as a control configuration.
2. Keep every generated visual claim tied to source image ID, face/panorama ID, normalized geometry, source coordinates, retrieval/acquisition timestamp and permission/attribution provenance. Preserve model observations separately from CoStar listing facts.
3. Gate abstention and structured-output correctness before using visual results downstream. Never infer engineering condition, code compliance, or unobserved geometry from these labels.
4. This spike does **not** justify selecting a winner: the sample is one property and three views; Vexcel exterior coverage is blocked. DeepSeek was faster and slightly cheaper in this run. Qwen with Mk1 context had higher observed precision but lower recall than raw-image Qwen; the measurements are inconclusive beyond this sample.

## Blockers and next steps

- Have Vexcel enable the API credential for the required coverage/metadata products and confirm extraction entitlements and any cost before imagery download.
- Perceptron Mk1 and configuration B are now confirmed working through OpenRouter; the separate Perceptron credential is unnecessary for this route.
- If Vexcel confirms coverage at this property's coordinates, use only a permitted low-volume sample and record source IDs, image capture/acquisition time, dimensions, CRS, license and attribution.
- Expand hand-labeled evaluation to several authorized properties/views with independent review before ranking architectures or reporting meaningful detection metrics.
- Do not integrate this research harness into Helix production or begin Stage 2 business analysis until the separate review/authorization.
