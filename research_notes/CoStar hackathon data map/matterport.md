# Matterport 3D Digital Twin Data & Developer Platform (as of Nov 2026)

Scope note: Researched 2026-11-13. Matterport's developer docs moved from matterport.github.io/showcase-sdk (now marked "no longer updated", site last generated Nov 12, 2026) and matterport.github.io/developer-docs to **developers.matterport.com** (301 redirects). Field names below come from the live developers.matterport.com pages unless flagged. Some AI-feature coverage is 2023-2024 trade press (flagged). **Hackathon caveat:** many of the richest data sources (Property Intelligence, webhooks, Account API) are **Enterprise-only**. Whether the CoStar sponsor credentials are Enterprise-tier is not known from public sources. Ask the sponsor on day 1.

## Q1. Developer tools: Showcase/Embed SDK, Bundle SDK, Model API (GraphQL), webhooks: endpoints, fields, auth, rate limits

### Takeaway
There are two main surfaces. (1) The **Model API**, a GraphQL endpoint at `https://api.matterport.com/api/models/graph`, authenticated with a Token ID/Secret. It returns model metadata, sweep locations with panorama skyboxes, Mattertags, notes, floor/room dimensions, floorplan image URLs, and purchasable asset bundles. (2) The browser **Embed SDK / Bundle SDK**, which needs an SDK application key. It drives the live 3D Showcase player: camera, sweeps, floors, rooms, tags, labels, measurements and sensors. The Bundle SDK also gives Three.js-level scene-graph access. Webhooks (10 model lifecycle events) are Enterprise-only. No public rate limits were found.

### Cited Findings
**Model API basics**
- GraphQL endpoint `https://api.matterport.com/api/models/graph`. There is a GraphiQL console at `https://api.matterport.com/model/graphiql` and a schema reference at `https://api.matterport.com/model/docs/reference`. — [Model API Overview](https://developers.matterport.com/api/model/overview/)
- Auth: an API Token ID plus Token Secret, generated in Matterport Cloud > Settings > Developer Tools > API Token Management. The Token ID acts as the username and the Secret as the password (HTTP Basic). OAuth exists separately for acting on other users' or private models. — [Matterport API docs index](https://matterport.github.io/developer-docs/api/); [Showcase SDK index (OAuth sections)](https://matterport.github.io/showcase-sdk/)
- The Model API is "available on all account levels". **Accounts start in Sandbox mode, where only demo models are accessible.** — [Model API Overview](https://developers.matterport.com/api/model/overview/); [API docs index](https://matterport.github.io/developer-docs/api/)
- Queryable per the overview: space name and address, sharing URLs, images and videos, panoramic imagery, position points, tags, and purchased assets (OBJ mesh and point cloud in a MatterPak once unlocked). — [Model API Overview](https://developers.matterport.com/api/model/overview/)
- Related APIs: Property Intelligence (via the Model API, Enterprise only), GeoCoordinate API, Import API (Enterprise beta: create models from E57 point clouds), Account API (Enterprise only), Webhooks, and "Views and Layers". — [Model API Overview](https://developers.matterport.com/api/model/overview/); [API docs index](https://matterport.github.io/developer-docs/api/)
- A Postman collection is published as the "model-api-snippets" workspace. — [API docs index](https://matterport.github.io/developer-docs/api/)

**Model API sample queries and fields (verbatim field names)**
- `models(query)` search returns `totalResults`, `nextOffset`, `results { id name description }`. Filters include `include: demo`, `include: inactive`, and floor-count filtering. — [Model API Samples](https://developers.matterport.com/api/model/samples/)
- `model(id)` details: `id name state visibility created modified description publication { description summary address contact { name email phoneNumber } externalUrl presentedBy published url }`. — [Samples](https://developers.matterport.com/api/model/samples/)
- **Sweeps and panoramas:** `model { locations { id label position floor room panos { id rotation{x y z w} position{x y z} skybox(resolution) { id status format children } } } }`. Skybox resolutions are `low` (512), `high` (1024), and `2k`. `4k` needs the Advanced Imagery add-on. `children` are the 6 cube-face image URLs. — [Samples](https://developers.matterport.com/api/model/samples/); [Ordering Add-ons](https://developers.matterport.com/api/model/ordering-addons/)
- **Defurnished panoramas** are queryable via `model { views(types) { model { locations { ... panos { skybox } } } } }`. This exposes Genesis-style defurnished imagery as a separate "view". — [Samples](https://developers.matterport.com/api/model/samples/)
- **Tags:** `mattertags(includeDisabled)` returns `id floor created modified enabled color label description icon keywords media mediaType position anchorPosition discPosition stemNormal stemLength stemEnabled`. — [Samples](https://developers.matterport.com/api/model/samples/)
- **Dimensions:** `model { dimensions floors { label dimensions(units) } rooms { id label tags dimensions } }`. The dimensions fragment is `areaCeiling areaFloor areaFloorIndoor areaWall volume depth height width units`. — [Samples](https://developers.matterport.com/api/model/samples/)
- **Floorplan images:** `assets { floorplans(provider, flags) { floor { label sequence } format flags url origin { x y } width height resolution } }`. Includes a "colored rooms" floorplan. `origin` and `resolution` let you map pixels to model coordinates. — [Samples](https://developers.matterport.com/api/model/samples/)
- **Notes and comments** (collaboration annotations): `notes(includeDisabled, resolutionStatus, ids)` returns `id label enabled createdBy resolution color position… firstCommentAt lastCommentAt totalComments comments{…}`. — [Samples](https://developers.matterport.com/api/model/samples/)
- **Mutations:** `updateModelAccessVisibility`, `updateModelState`, `patchModel` (name, description, options, mls, publication), `updateModelAddress`, `addMattertag(modelId, field, mattertag{floorId label description color icon keywords anchorPosition mediaType mediaUrl stem…})`, `patchMattertag`, and `unlockModelBundle(id, bundleId, bundleOptions)`. **Write-back is possible: an agent can create tags in the tour.** — [Samples](https://developers.matterport.com/api/model/samples/)

**Embed / Showcase SDK (browser JS)**
- The SDK key is created under Account Settings > Developer Tools > SDK Key Management. Add allowed domains such as `localhost` and `localhost:8080`. The key goes in both the iframe `applicationKey` URL param and the `connect()` call. Sample code requires a "sandboxed SDK key". — [Local environment tutorial](https://matterport.github.io/developer-docs/tutorials/local-environment/); [showcase-sdk-examples README](https://github.com/matterport/showcase-sdk-examples/blob/main/README.md)
- Embed SDK: "web apps run actions on the 3D Showcase (e.g., moving to a location) and listen to its events." Tutorials cover Scene, Tags/Mattertags (Tags 2.0 migration), Sensors (Sweep Control, Source Areas), Models, Observables, Collections, Pathfinding, and Pointer Reticle. — [Showcase SDK index](https://matterport.github.io/showcase-sdk/)
- Namespace examples: `mpSdk.Measurements.mode` (observable) plus experimental `add`/`remove`. `MeasurementModeData` includes a user-set `label`. `mpSdk.Sensor.createSensor` and `Sensor.createSource` take sphere, box or cylinder volumes, giving "is this region visible from the camera" triggers. `Room.current` reports which rooms the camera is in (empty unless in INSIDE mode). `Floor.getData` plus `Floor.Event.CHANGE_START/CHANGE_END`. `Label.data` is an observable map of 3D text labels. — [Measurements](https://matterport.github.io/showcase-sdk/docs/reference/current/modules/measurements.html); [Sensor](https://matterport.github.io/showcase-sdk/docs/reference/current/modules/sensor.html); [Room](https://matterport.github.io/showcase-sdk/docs/reference/current/modules/room.html); [Label](https://matterport.github.io/showcase-sdk/docs/reference/current/modules/label.html); [Floor](https://matterport.github.io/developer-docs/reference/floor/)
- **Bundle SDK:** extends the Embed SDK with "direct access to the 3D engine, renderer, and scene graph". Components include Ambient/Directional/Point Light, GLTF/DAE/FBX/OBJ loaders, Transform Controls, Input, Camera, and XR. A **WebComponent (Beta)** wraps the player in one DOM element. — [Showcase SDK index](https://matterport.github.io/showcase-sdk/); [Bundle SDK](https://matterport.github.io/developer-docs/bundle-sdk/)

**Webhooks (v2, Enterprise only)**
- Events: `activation_state_changed`, `bundle_updated` (requested/delivered/canceled/failed), `created`, `deleted`, `details_changed`, `processed` (succeeded/failed), `restored`, `transferred_in`, `transferred_out`, `visibility_changed`. Payload: `modelId version webhookId webhookCustomKey timestamp type body`. — [Webhooks](https://developers.matterport.com/webhooks/)
- Register via the GraphQL mutation `addModelEventWebhookCallback` (eventTypes, callback{scheme host port path cred…}, version: 2). Also `modelEventWebhookCallbacks`, `patch…`, `remove…`, and `pingModelEventWebhookCallback`. POST only. Requires an Enterprise subscription, a feature unlock and a developer license unlock. — [Webhooks](https://developers.matterport.com/webhooks/)

**Third-party MCP / agent tooling**
- Composio hosts a "Matterport MCP server" with managed auth, with guides for the Claude Agent SDK, OpenAI Agents SDK, Pydantic AI and Vercel AI SDK. The example is listing spaces and sharing a tour in natural language. — [Composio Matterport toolkit](https://composio.dev/toolkits/matterport); [Pydantic AI guide](https://composio.dev/toolkits/matterport/framework/pydantic-ai)
- Pipedream ([mcp.pipedream.com/app/matterport](https://mcp.pipedream.com/app/matterport)) and Metorial ([metorial.com](https://metorial.com/integrations/matterport/triggers)) also list Matterport MCP connectors. Runbear lists "no tools available". — [Runbear](https://runbear.io/solutions/integrations/slack/mcp/servers/matterport)

### Inferences
- The fastest hackathon path is to write your own thin MCP or tool layer over the GraphQL endpoint: `getSweeps`, `getDimensions`, `getVectorData`, `getTags`, `addMattertag`. That gives better coverage than third-party MCPs, which appear to wrap only account and model-management calls.
- Sweep `position` plus `rotation` plus cube-face skybox URLs are enough to project a vision-model detection back into 3D, then write it into the tour with `addMattertag`. That makes a closed perception-to-annotation loop.
- Floorplan `origin`, `resolution`, `width` and `height` support pixel-to-model coordinate conversion for overlay tasks.
- In the SDK, `Sensor` plus `Room.current` plus Camera/Sweep navigation make it possible to build an "agent-guided tour" that moves the camera and reacts to what is visible.

### Gaps
- **No public rate limits** for the Model API or SDK were found on any Matterport page retrieved. The developer-tools pricing support article was not retrieved.
- The full schema field list is only available in the live GraphiQL console or reference. Point cloud queries are not in the samples, so point clouds appear to come only via the `mp:matterpak` or `mp:e57` bundles.
- Exact Camera/Sweep/Mode SDK method signatures were not fetched. They are in the [SDK reference](https://matterport.github.io/showcase-sdk/docs/reference/current/index.html).
- No **official** Matterport- or CoStar-published MCP server was found.

## Q2. Extractable assets: panoramas, floor plans, E57, OBJ, MatterPak, dimensions, room labels, BIM/CAD, photos/video, measurements

### Takeaway
Free with any Model API access: cube-map panoramas up to 2K, sweep poses, floor/room dimensions and areas, floorplan image URLs, tags and notes, and model metadata. Paid "bundles" are unlocked through `unlockModelBundle`. These are MatterPak (OBJ/MTL + colorized point cloud + reflected ceiling plan + photogrammetry floorplan image), E57 (dense point cloud), schematic floorplans (JPG/PNG/SVG, delivered in about 2 days by humans), 4K imagery ($99), and BIM/CAD/TruePlan (query-only via API, not purchasable). Enterprise Property Intelligence adds wall vectors, openings and room classifications.

### Cited Findings
- Bundle IDs: `mp:matterpak` (high-res OBJ/MTL, colorized point cloud, reflected ceiling plan image, high-res photogrammetry floorplan); `floorplan:schematic` (JPG, PNG, SVG); `mp:e57` (point cloud); `bim:cad` (BIM); `standard:cad` (2D DWG, styles architecture/mep/furnished/mep_furnished/industrial); `trueplan:schematic` (for Xactimate insurance estimating); `mp:imagery` (4K panos on Business/Enterprise, 2K on Starter/Pro, $99). "BIM Files, CAD Files and Trueplans cannot be purchased via Model API at this time." — [Ordering Add-ons](https://developers.matterport.com/api/model/ordering-addons/)
- Schematic floorplan options: `color`, `furniture`, `delivery_time` (normal = 2 business days, fast = 1 day, urgent = 6 hours), `hide_dimensions`, `hide_internal_area`, `language` (en/de/fr/es/it), `unit_type`, `use_custom_showcase_labels`, `use_showcase_orientation`, `use_six_inch_wall_thickness`. Assets are not immediate. — [Ordering Add-ons](https://developers.matterport.com/api/model/ordering-addons/)
- Retrieval: `model { bundles { id availability availableOptions{key values} assets { id url validUntil format filename status } processing { status failureReason } } }`. Asset URLs are time-limited (`validUntil`). — [Ordering Add-ons](https://developers.matterport.com/api/model/ordering-addons/)
- The MatterPak OBJ comes with JPG texture maps. Multi-floor models have multiple JPG floorplan images and one PDF for all floors. — [Matterport MatterPak page](https://matterport.com/add-ons/matterpak)
- The MatterPak floorplan is an image, not the schematic floor plan (community and reseller sources, older). — [WGAN forum](https://www.wegetaroundnetwork.com/topic/8914/so-the-matterpak-includes-a-floor-plan/); [thefuture3d](https://www.thefuture3d.com/services/matterpak)
- E57 is a separate add-on. Matterport's blog claims it has "10x the detail" of a MatterPak, while a reseller says about 20x (conflicting). A reseller quotes $150 per E57 (unverified, likely dated). — [Introducing Matterport E57](https://matterport.com/blog/introducing-matterport-e57); [WGAN/reseller via search](https://forum.we-get-around.com/topic/6857/matterpak-bundle-example-and-case-study/)
- Free dimensional data: model, floor and room `areaCeiling areaFloor areaFloorIndoor areaWall volume depth height width units`. — [Samples](https://developers.matterport.com/api/model/samples/)
- **Property Intelligence (Enterprise only):** new `dimensionalEstimates`, `floors` and `rooms` objects. Use cases: square footage for billing, floor and room dimensions for listings, detected room names, and vector data for redrawing floorplans. Owners can edit detected rooms and labels, and the edits flow through the API. — [Property Intelligence](https://developers.matterport.com/api/property-intelligence/)
- **Vector data:** `rooms { id label classifications{id label} boundary{edges{ id type(wall|invisible) centerLineBias thickness openings{ id height width lowerElevation relativeCenter type(doorway|opening) } vertices{ id position{x y} } }} holes{…} }`. Vertex coordinates are 2D relative to the model center. — [PI Vector Data](https://developers.matterport.com/api/property-intelligence/vector-data/)
- **Room classifications (21):** Balcony, Basement, Bathroom, Bedroom, Closet, Dining Room, Entrance, Exercise Room, Family Room, Game Room, Garage, Hallway, Kitchen, Living Room, Loft, Office, Pantry, Patio, Staircase, Utility Room, Other. Multi-label combos are allowed (e.g., Kitchen+Living+Dining, Bathroom+Laundry). Fields: `classifications { id label defaultKeywords confidence }`, `keywords`, `floor{id}`. — [PI Room Names](https://matterport.github.io/showcase-sdk/modelapi_pi_room_names.html)
- The Import API (Enterprise beta) creates Matterport models from E57 point clouds. — [API docs index](https://matterport.github.io/developer-docs/api/)
- Images, videos and sharing URLs are listed as queryable model data. — [Model API Overview](https://developers.matterport.com/api/model/overview/)

### Inferences
- The room classification taxonomy is **residential-centric**: no "conference room", "lobby", "retail floor" or "server room". For CoStar commercial buildings in Houston and LA, expect many "Office"/"Other" labels. A vision-LLM reclassifier for commercial space types is a natural project.
- In a 36-hour window, schematic floorplans (2-day human turnaround), BIM and CAD are effectively unavailable unless the sponsor pre-unlocked them. Plan around panoramas, dimensions, vector data, and pre-unlocked MatterPak or E57 files.
- Openings typed only as `doorway` or `opening`, plus wall `thickness` and opening `width`, give a cheap accessibility heuristic (for example, ADA 32-inch clear door width).

### Gaps
- MatterPak point cloud format (likely .xyz) and E57 density/size were not confirmed from a 2026 official page.
- Whether the hackathon models already have MatterPak, E57 or PI unlocked is unknown.
- The `dimensionalEstimates` sub-fields and PI mutations sub-pages were not retrieved.

## Q3. Matterport AI features 2023-2026 and post-CoStar announcements; MCP / agent tooling

### Takeaway
Matterport's AI stack is branded **Cortex AI** (reconstruction, auto-measurement, object recognition, privacy blurring). It includes **Property Intelligence** (auto measurements and layouts, Sept 2023 to Feb 2024; 20+ room types) and **Project Genesis** (generative defurnish, declutter and erase, previewed early 2024 and rolled out 2024). AI property descriptions rolled out around Oct 2024. After CoStar closed the acquisition in 2025, Matterport data was folded into CoStar's consumer AI: **Homes AI** (Feb 2026, Azure OpenAI), **Apartments.com AI** (June 2026), and in-tour conversational AI on Matterport tours (reported July 2026). No official Matterport MCP server was found.

### Cited Findings
- Cortex AI: computer vision, image processing and deep learning for 3D reconstruction, HDR and color correction, automated measurements (square footage, ceiling height, wall dimensions, exportable to MLS), 2D photos, privacy protection, and "object location and identification" (no detail given). Project Genesis can "defurnish", "declutter" and "erase" objects individually. — [Matterport Cortex AI](https://matterport.com/cortex-ai)
- The "Automated Measurements and Layouts Now Available" blog is dated Sept 26, 2023. A Property Intelligence article is dated Dec 13, 2023. — [Cortex AI page](https://matterport.com/cortex-ai)
- Property Intelligence launched Feb 2024 as "a collection of AI-powered features providing automated measurements, layouts, editing, and reporting." It identifies 20+ space types. — [RISMedia, Feb 2024](https://www.rismedia.com/2024/02/20/matterport-launches-property-intelligence/)
- Genesis defurnish removes anything "not bolted down" in one click. AI-generated property descriptions use Matterport spatial data (2024 coverage, older). — [HousingWire](https://www.housingwire.com/articles/matterport-ai-defurnish-photos-property-descriptions/); [Geo Week News](https://www.geoweeknews.com/news/matterport-genesis); [WGAN 2024 Fall Release](https://www.wegetaroundnetwork.com/topic/20398/wgan-tv-podcast-matterport-2024-fall-release/)
- Defurnished panoramas are exposed in the Model API via `views(types)`. — [Samples](https://developers.matterport.com/api/model/samples/)
- CoStar completed its about $1.6B Matterport acquisition in 2025. — [Virginia Business](https://virginiabusiness.com/costar-completes-1-6b-acquisition-of-matterport/); [Matterport blog: Next Chapter](https://matterport.com/blog/matterports-next-chapter-as-part-of-costar-group)
- Homes AI on Homes.com launched Feb 17, 2026, powered by Microsoft Azure OpenAI and drawing on Matterport 3D digital twin technology. — [BusinessWire](https://www.businesswire.com/news/home/20260217810823/en/CoStar-Group-Launches-Transformative-AI-Experience-on-Homes.com-Redefining-the-Future-of-Home-Shopping); [CoStar press room](https://www.costargroup.com/press-room/2026/costar-group-launches-transformative-ai-experience-homescom-redefining-future-home)
- On the Q1 2026 earnings call, management said Matterport is a key component of Homes AI and will support AI development across CoStar. — [VectorShift transcript summary](https://vectorshift.ai/research/companies/costar-group/earnings/2026-q1)
- Apartments.com AI (June 16, 2026) offers conversational rental search built on listings plus Matterport tours. Apartments.com began offering professionally produced Matterport "Exterior-to-Interior" tours on June 15, 2026. — [Let's Data Science](https://letsdatascience.com/news/costar-launches-apartmentscom-ai-conversational-search-38921227); [Apartments.com NAA 2026](https://www.apartments.com/grow/learning-center/naa-apartmentalize-highlights-2026)
- July 2026: CoStar embedded LLM conversations into Matterport 3D tours on Homes.com and Apartments.com. Users can ask about room dimensions, window views, features and nearby amenities during a tour. Note: only one or two trade sources were found, and the primary article returned 403. — [AIM Group](https://aimgroup.com/2026/07/15/costar-embeds-ai-conversations-into-matterport-3d-tours-on-homes-com-apartments-com/); [Online Marketplaces roundup](https://www.onlinemarketplaces.com/articles/product-and-services-roundup-costar-group-entegral-zoopla-and-fotocasa/)
- MCP: only third-party connectors were found (Composio, Pipedream, Metorial). — [Composio](https://composio.dev/toolkits/matterport); [Pipedream](https://mcp.pipedream.com/app/matterport)

### Inferences
- CoStar's own "AI in the tour" is a consumer Q&A chatbot. Differentiated hackathon ideas should go beyond Q&A: commercial underwriting, compliance or accessibility audits, cross-referencing CoStar comps and Vexcel roof or exterior imagery, or agentic tour authoring with `addMattertag`.
- Judges from CoStar will already know Homes AI. Pitch against it explicitly (for example, "Homes AI answers questions; we produce an auditable report").

### Gaps
- No Matterport developer-API changelog entries for 2025-2026 (new AI fields after the acquisition) were retrieved. Check the [SDK changelog](https://matterport.github.io/showcase-sdk/sdk_changelog.html) and the Model API changelog.
- Whether the Genesis "redesign/restyle" (beyond defurnish) shipped by 2026 is unconfirmed.
- No accuracy figures for auto-measurements or room classification were found on official pages.

## Q4. What is NOT available (build-on-top opportunities with vision models)

### Takeaway
The API exposes geometry (dimensions, wall vectors, openings, sweeps) and coarse room types. It does **not** expose a semantic object inventory, materials or finishes, condition or damage, fixture counts, windows as a distinct type, commercial room types, or text/OCR. These are all reachable by running a VLM or segmentation model on the 2K skybox faces and back-projecting with sweep poses.

### Cited Findings
- Openings are typed only `doorway` or `opening`. Windows are not a separate type. — [PI Vector Data](https://developers.matterport.com/api/property-intelligence/vector-data/)
- The room taxonomy has 21 mostly residential classes plus "Other". — [PI Room Names](https://matterport.github.io/showcase-sdk/modelapi_pi_room_names.html)
- Cortex AI mentions "object recognition" but publishes no object list, and no object-list query appears in the Model API samples. — [Cortex AI](https://matterport.com/cortex-ai); [Samples](https://developers.matterport.com/api/model/samples/)
- Point cloud and mesh data are available only via paid bundles (MatterPak or E57), not a free query. — [Ordering Add-ons](https://developers.matterport.com/api/model/ordering-addons/)

### Inferences
- Candidate build-ons:
  - Object and fixture inventory with 3D positions (for facilities management or insurance contents lists)
  - Material and finish detection (flooring type, countertops) feeding valuation against CoStar comps
  - Condition and damage detection (water stains, cracks)
  - ADA and accessibility audit (door widths from `openings.width`, thresholds, stairs, grab bars via VLM)
  - Fire and life-safety checks (exit signs, extinguishers, sprinklers in panoramas)
  - Commercial space re-classification and rentable-vs-usable area
  - Window detection and view or daylight scoring, combined with Vexcel aerials and orientation
  - Natural-language spatial search ("show me every room with exposed brick") that jumps the Showcase camera to the matching sweep
- Back-projection recipe: skybox cube face plus sweep `position` and `rotation` (quaternion) give a ray. Intersect it with wall vectors or room bounds (or a MatterPak mesh, if unlocked) for 3D placement, then call `addMattertag`.

### Gaps
- No official statement was found that enumerates what Matterport's internal object recognition detects or whether it will be exposed.

## Q5. Known creative uses and research with Matterport data

### Takeaway
Matterport scans underpin the main embodied-AI benchmarks. Matterport3D (2017) has 90 buildings and 10,800 panoramas. HM3D (2021) has 1,000 buildings, is Habitat-ready, and is free for academic non-commercial use. These power navigation, vision-language navigation and object-goal research. Commercially, the API exposes insurance (TruePlan for Xactimate), facilities, MLS/listings and BIM/CAD workflows.

### Cited Findings
- Matterport3D (Chang et al. 2017): 90 buildings, 194,400 RGB-D images, 10,800 panoramas captured about 2.5 m apart. — [arXiv 1709.06158](https://arxiv.org/pdf/1709.06158)
- HM3D (Ramakrishnan et al., NeurIPS 2021 Datasets): 1,000 building-scale reconstructions scanned with the Matterport Pro2, Habitat-simulator ready, 1.8x more scans than prior sets (Gibson has 571). Free for academic, non-commercial research. — [arXiv 2109.08238](https://arxiv.org/abs/2109.08238); [NeurIPS paper](https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/file/34173cb38f07f89ddbebc2ac9128303f-Paper-round2.pdf)
- `trueplan:schematic` is a floorplan for Xactimate (insurance claims estimating). CAD styles include MEP and industrial (facilities and AEC). — [Ordering Add-ons](https://developers.matterport.com/api/model/ordering-addons/)
- PI use cases: square footage for billing, listing dimensions, floorplan redraw. Measurements export to MLS. — [Property Intelligence](https://developers.matterport.com/api/property-intelligence/); [Cortex AI](https://matterport.com/cortex-ai)
- Matterport's E57 is positioned for AEC/BIM workflows. — [Introducing Matterport E57](https://matterport.com/blog/introducing-matterport-e57)

### Inferences
- Habitat-style ideas, such as "point-goal" or "object-goal" agents walking the sweep graph, can be prototyped directly. Sweep `locations` act as a navigation graph (Matterport3D panoramas were about 2.5 m apart), and the SDK has a Pathfinding tutorial ([Showcase SDK index](https://matterport.github.io/showcase-sdk/)). A VLN-style agent ("take me to the server room") over real CoStar buildings is very demo-able.
- HM3D licensing is non-commercial. For a hackathon, the CoStar-provided scans are the relevant data, and HM3D/MP3D pretrained models (e.g., Habitat baselines) could be reused.

### Gaps
- No recent (2025-2026) sources were retrieved on accessibility-audit, construction-progress or insurance products built on Matterport. These use cases are plausible but uncited here.
