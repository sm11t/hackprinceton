# Make CoStar's Three Data Layers Disagree

The strongest play for the "Inside and Out" track is an agent that treats CoStar records, Matterport interiors and Vexcel aerials as **three independent witnesses about the same building**, and then shows where they disagree or where one predicts what the others haven't recorded yet. Examples are "CoStar says 92% leased; the parking lot and the floors say 41%," or "this tenant stores lithium batteries behind a stairwell the fire department has never seen." That framing earns the 30% data-combination score by design. Two of the three layers are well documented in public. Matterport has a GraphQL Model API plus a browser SDK. Vexcel has a REST v2 API and, since July 2026, an MCP server. **CoStar has no public API at all**, so the CoStar fields in the hackathon toolkit are the biggest unknown and must be confirmed on site before you commit to an idea. TypeSafe's Jev fits as the fast perception layer: an LLM plans, Jev makes thousands of cheap, calibrated yes/no and multiple-choice judgments over scan frames and aerial crops, and plain code does all the counting and math. The three best directions are a "shadow vacancy" detector, a tenant-aware fire pre-incident planner, and a vacant-space film-location finder. Skip roof, solar and peril scoring, parking-lot counts on their own, "agent ranks sites on a map," and tour chatbots. Incumbents and last year's HackPrinceton winners already own those. CoStar's 2026 announcements show one consistent motive. It wants to use AI to turn cheap capture (aerials, scans, lease documents) into proprietary, verified fields at lower cost. It wants to defend that data against public-data AI agents, to grow its profit margin under investor pressure, and to push data into lender workflows. So the most aligned build is an "AI researcher" agent that proposes CoStar fields from imagery and scans, with confidence-gated human review, and feeds a Shadow Vacancy watchlist for lenders.

## Matterport and Vexcel are documented; CoStar's layer is a black box

A note on sources: the track details (the name, the Houston and LA buildings, SDK/MCP/OpenAPI access, the judging weights) come from the team's brief. The public HackPrinceton site lists CoStar as a sponsor but does not describe the track or its toolkit ([HackPrinceton](https://www.hackprinceton.com/)). Everything below is therefore "what each platform can do in public," not "what the toolkit exposes." The verification table at the end of this section separates the two.

### CoStar: rich in principle, unconfirmed in the toolkit

As of November 2026, **no public API, developer portal, SDK or official MCP server** exists for CoStar Suite, COMPS, Market Analytics or LoopNet. One API report card gives CoStar an "F" and notes that CoStar enforces its no-scraping terms with account suspensions and federal lawsuits ([Supergood](https://supergood.ai/api-report-card/costar)). So the hackathon's SDKs, MCP servers and OpenAPI services are a purpose-built, event-only exposure with no public schema, and anything built on them is new by default. Don't plan to fill gaps by scraping LoopNet or CoStar.

What CoStar tracks in its products is public, even if the toolkit subset isn't:

- **Building attributes:** RBA (rentable building area; retail uses GLA), Typical Floor SF, Parking Ratio (spaces per 1,000 SF), Building Class (A/B/C), and a separate 1–5 **Star Rating** ([CoStar Glossary](https://www.costar.com/resources/costar-glossary); [Introduction to Properties](https://www.costar.com/sites/costar.com.na/files/2023-02/introduction-to-properties.pdf)).
- **Lease comps:** asking vs. achieved rent, time on market, expirations and incentives ([CoStar Lease Comps](https://costar.co.uk/products/lease-comps)).
- **Sale comps:** price, date, an "Assessment at Sale" section and a "Market at Sale" section ([Introduction to Sale Comps](https://costar.com/sites/costar.com.na/files/2023-02/introduction-to-sale-comps.pdf)).
- **Debt and loan risk:** the COMPASS default model joins CMBS bond data to collateral properties ([CoStar Risk Analytics](https://costar.com/ja-jp/node/1586)).

The likely entity graph is Property → Spaces/Availabilities → Lease comps → Sale comps → Contacts/Owners → Tenants → Market time series. That is an inference from the product pages, not a published schema.

CoStar's stated strategy is the best guide to what its judges care about:

- On its Q3 2026 earnings call, CoStar said **about 75% of its content is not visible on the open internet**, and that in head-to-head tests **an AI agent using only public data had a 75% error rate**, against CoStar's single-digit rate ([Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)).
- On the same call it described an AI research process meant to refresh all **6.7M CoStar Tenant locations every year** (same source).
- It agreed on October 27, 2026 to buy Vexcel for about **$730M**, explicitly to have AI extract **"hundreds of data fields per property"** from aerial imagery. Closing is expected in Q1 2027, and product enhancements using the aerials are a late-2027 initiative ([SEC 8-K Ex. 99.2](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm)).

A team that demonstrates imagery- and scan-derived fields being checked against researcher-verified records this weekend is prototyping CoStar's 2027 roadmap.

### Matterport: deep geometry, with the best parts behind tiers and paywalls

The **Model API** is a GraphQL endpoint at `https://api.matterport.com/api/models/graph`. It authenticates with HTTP Basic, using an API Token ID and Secret. It is "available on all account levels," but **new accounts start in Sandbox mode, where only demo models are visible** ([Model API Overview](https://developers.matterport.com/api/model/overview/)). The useful fields, quoted verbatim from Matterport's samples ([Model API Samples](https://developers.matterport.com/api/model/samples/)):

- **Sweeps (scan positions):** `locations` gives each sweep's position, floor and room. Each sweep has `panos` with a quaternion rotation and six cube-face `skybox` image URLs at `low` (512), `high` (1024) or `2k` resolution. 4K needs a paid add-on ([Ordering Add-ons](https://developers.matterport.com/api/model/ordering-addons/)).
- **Defurnished panoramas:** served as a separate `views(types)` layer.
- **Dimensions** for the model, each floor and each room: `areaCeiling areaFloor areaFloorIndoor areaWall volume depth height width`.
- **Floorplan images** with `origin` and `resolution`, so you can convert pixels to model coordinates.
- **Notes and comments.**
- **Mattertags (annotations), with write mutations:** `addMattertag` and `patchMattertag`. **An agent can write its findings back into the 3D tour.**
- **Model metadata,** including `created` and `modified` dates, which give you a scan date.

The browser **Embed SDK** drives the live 3D viewer:

- `Sensor.createSensor` raises visibility triggers when a region comes into view.
- `Room.current` reports which room the camera is in.
- It also controls measurements, floors and the camera.

The **Bundle SDK** adds Three.js-level scene-graph access ([Showcase SDK](https://matterport.github.io/showcase-sdk/)). One gotcha: the Model API and the SDK use **different coordinate conventions** ([developer docs overview](https://matterport.github.io/developer-docs/overview/)).

Three things are **Enterprise-only**:

- **Property Intelligence.** This gives wall vectors with thickness, plus openings with `width`, `height` and type. Openings are typed only as `doorway` or `opening`; there is no window type ([PI Vector Data](https://developers.matterport.com/api/property-intelligence/vector-data/)). It also gives a **21-class room taxonomy that is almost entirely residential**: Bedroom, Kitchen, Garage and so on, with no conference room, lobby or retail floor ([PI Room Names](https://matterport.github.io/showcase-sdk/modelapi_pi_room_names.html)).
- **Webhooks** ([Webhooks](https://developers.matterport.com/webhooks/)).
- **The Account API.**

Point clouds and meshes come only as **paid bundles**: MatterPak (OBJ plus colorized point cloud) and E57. Their download URLs expire. Schematic floorplans take a **2-business-day human turnaround**, and BIM/CAD files **cannot be bought through the API** ([Ordering Add-ons](https://developers.matterport.com/api/model/ordering-addons/)). In a 36-hour event, plan on panoramas, dimensions and tags, plus whatever the sponsor has already unlocked.

The API exposes no object inventory, materials, condition, windows or commercial room types. That gap is where a vision model, or Jev, adds value.

### Vexcel: the most agent-ready layer, with an MCP server built for this

Vexcel flies its own UltraCam cameras. It captures:

- four-direction **45° obliques** and nadir images at **7.5 cm**;
- a **TrueOrtho** with no building lean, pixel-matched to a DSM;
- near-infrared, delivered as color-infrared;
- **DSM/DTM** elevation (surface vs. bare earth).

([Vexcel High Resolution](https://vexceldata.com/?p=3475)). Major US metros are refreshed **up to 3 times a year** ([SEC 8-K](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm)). A reseller listing puts the archive back to 2012 ([UP42](https://docs.up42.com/data/vexcel-aerial)), which makes multi-date change detection on real buildings possible.

On top of the imagery, **Elements** precomputes more than 40 attributes per property ([Elements: Property Attributes](https://vexceldata.com/products/elements/property-attributes/)):

- footprint polygon and area;
- ground and **entrance elevation**;
- **number of stories** and volume below eave;
- roof condition, material, max and eave height, and rooftop objects (AC units, panels, skylights);
- roof defects such as tarps, rust and water pooling;
- **vehicles detected, type and count**;
- hardscape;
- defensible-space buffers at 5, 30, 100 and 200 ft.

Each attribute is tied to timestamped imagery.

Two newer capabilities matter most for a hackathon:

- **Custom Elements** (launched August 19, 2026) does text-prompted, zero-training object detection that returns segmentation polygons. It is Vexcel's first detection on **oblique** imagery, so it can find facade and vertical features ([Custom Elements launch](https://vexceldata.com/?p=29613)).
- **Semantic search** runs over **more than 3 billion embeddings** ([Insurance Edge](https://insurance-edge.net/2026/09/30/vexcel-intelligence-offers-aerial-imagery-searchable-using-everyday-language/)).

The **Vexcel MCP server** sits at `https://api.vexcelgroup.com/v2/mcp` ([Get Started with Vexcel MCP](https://vexceldata.com/?p=28421)):

- Auth is an API key, passed as `X-API-KEY` or `?api_key=`.
- Locations are WKT `POINT`/`POLYGON` in EPSG:4326, and date ranges are supported.
- Tools cover ortho and oblique imagery (including the Gray Sky disaster layer), DSM/DTM, property metadata, damage assessment, embedding search and custom elements.
- Products may need separate entitlements, and no rate limits are published.

Gray Sky disaster coverage is **confirmed** for the January 2025 LA wildfires, with flights on January 10–13, January 20 and February 2 ([Gray Sky: California Wildfires](https://vexceldata.com/?p=17177)), and for the **December 28, 2024 Houston-area EF2 tornadoes** ([Gray Sky: Houston Tornadoes](https://vexceldata.com/stories/gray-sky-houston-area-tornadoes/)). It is **not confirmed for Hurricane Beryl**: the only post-Beryl Houston imagery found came from competitor Nearmap ([Nearmap](https://nearmap.com/white-papers/hurricane-beryl-government)).

### What is verified and what is assumed

| Layer | Capability | Access method | Status |
|---|---|---|---|
| CoStar | Property attributes (RBA, typical floor, parking ratio, class, star rating) | Hackathon SDK/MCP/OpenAPI only | Fields exist in CoStar's products; **which ones the toolkit exposes is unverified** |
| CoStar | Lease comps, expirations, tenants, sale comps, owners, loans, market forecasts | Same | Exist in products; **toolkit inclusion unverified, and the most important thing to confirm** |
| CoStar | Join key to Matterport and Vexcel | Same | **Unknown.** Probably property ID plus lat/long or footprint (speculation) |
| Matterport | Sweeps, 512–2K skybox faces, dimensions, floorplan images, tags, notes, scan dates | Model API (GraphQL, Token ID/Secret) | **Verified, all tiers** (Sandbox sees only demo models) |
| Matterport | Write-back via `addMattertag` / `patchMattertag` | Model API mutations | **Verified in docs**; whether the toolkit token has write scope is unverified |
| Matterport | Live 3D viewer control, sensors, current room | Embed/Bundle SDK (SDK key plus domain allowlist) | **Verified** |
| Matterport | Wall vectors, opening widths, room classification | Property Intelligence | **Enterprise-only**; toolkit tier unverified |
| Matterport | Mesh / point cloud / schematic floorplan / BIM | Paid bundles | **Paid, slow, or not available via the API**; usable only if pre-unlocked |
| Vexcel | Obliques, TrueOrtho, CIR, DSM/DTM | REST v2, WMTS, MCP | **Verified in public docs** |
| Vexcel | Elements attributes (stories, vehicles, entrance elevation, roof objects) | MCP / API | **Verified as a product; entitlement unverified** |
| Vexcel | Custom Elements, semantic embeddings search | MCP / API | **Verified as a product (2026); entitlement unverified** |
| Vexcel | Multi-date archive per building; Gray Sky for LA fires and Houston tornadoes | MCP / API | Archive depth inferred; Gray Sky events confirmed; **per-building availability unverified** |
| Vexcel | MCP tool names, schemas, rate limits | MCP | **Unverified** (behind login) |

## Every pairing of layers exposes a gap no single vendor can see

Each layer is an incomplete witness. CoStar records what people *reported*: leases, sales, tenants, square footage. Matterport records what the *interior looked like on scan day*. Vexcel records what the *exterior looked like on each flight date*. Every interesting signal sits where two of these disagree, or where one moves before the others catch up. The matrix below lists the combinations the research turned up. The final column says how crowded each one already is.

| Combination | What the join reveals | Concrete derived signal | Crowdedness |
|---|---|---|---|
| CoStar × Matterport | Records vs. interior reality | Sum of floor `areaFloor` vs. RBA; floor `width × depth` vs. Typical Floor SF; "leased" floors that look cleared; tenant type vs. what is stored inside | **Open.** CoStar's own in-tour AI is a consumer Q&A chatbot ([AIM Group](https://aimgroup.com/2026/07/15/costar-embeds-ai-conversations-into-matterport-3d-tours-on-homes-com-apartments-com/)) |
| CoStar × Vexcel | Records vs. exterior reality over time | Elements stories × footprint area vs. RBA; counted stalls and vehicles vs. Parking Ratio; vehicle counts across flight dates vs. leased %; rooftop equipment vs. year built or renovated | Parking counts alone are crowded (Orbital Insight); **reconciling them to CoStar fields is open** |
| Matterport × Vexcel | One geometry, seen inside and out | Floor-to-floor height × floors vs. DSM−DTM height; interior window positions vs. facade in obliques; ground-floor mechanical rooms vs. Elements entrance and ground elevation | **Open.** Incumbents are almost all exterior-only |
| CoStar × Matterport × Vexcel | A full "building truth ledger" | Per-field consensus or disagreement with a confidence score; anomalies routed to a researcher | **Open, and exactly CoStar's stated 2027 plan** |
| Any layer × time | Who moved first | Vexcel flight dates, Matterport `created` date, CoStar lease start/expiry and sale dates on one timeline | **Least explored dimension** |

Two points from this matrix should shape brainstorming.

**Time is the hidden fourth layer.** Each source carries a date: Matterport's `created`/`modified`, Elements attributes tied to timestamped imagery, and CoStar's lease and sale dates. Very few projects will line these up on one timeline. Doing so turns a static comparison into a prediction ("the parking lot emptied two flights before the lease expired").

**The matrix also implies a build order.** Every concept below needs the same base first: join the three layers on one building, then compute the reconciliation fields (area, stories, parking). That base is a fallback project on its own, because it directly mirrors CoStar's Vexcel thesis. Build it in the first 8–10 hours, then put a vertical use case on top.

Geometry join tips:

- Vexcel takes WKT in EPSG:4326 ([Vexcel MCP](https://vexceldata.com/?p=28421)).
- Matterport has a GeoCoordinate API ([Property Intelligence docs](https://developers.matterport.com/api/property-intelligence/)).
- Matterport floorplan `origin` and `resolution` let you overlay a scan's floorplan onto the Vexcel footprint polygon. This gives a strong "inside and out" visual on the same screen.

## Jev is the agent's eyes, not its brain

Jev is TypeSafe's non-generative "System One" model ([docs.typesafe.ai](https://docs.typesafe.ai)):

- **Input:** a `state` (text, JSON and/or images) plus any number of typed questions.
- **Output:** calibrated, typed answers from one parallel call, using four primitives ([Quickstart](https://docs.typesafe.ai/introduction/quickstart.md)):

| Primitive | Returns |
|---|---|
| **Choice** | an option, with probabilities |
| **Score** | a scored rating, with probabilities |
| **Noul** | a yes/no probability between 0 and 1 |
| **Box** | a bounding box in an image |

- **Price:** **$0.042 per million input tokens**, and **output tokens are free** ([Models](https://docs.typesafe.ai/models.md)).
- **Speed:** a vendor-stated **70–500 ms** per call, which has not been independently reproduced.
- **Batching:** questions in one request run in parallel. One documented case put 13 questions in a single call and got "12.2x cheaper and 11.8x faster with no change in answers" ([llms.txt](https://docs.typesafe.ai/llms.txt)).

Jev's limits matter as much as its strengths. TypeSafe documents that Jev "does not count reliably," is "not a calculator," compares dates unreliably, struggles with multi-hop reasoning, leans toward the first option in a Choice, and does not generate text ([Model jaggedness](https://docs.typesafe.ai/model-jaggedness.md)). That defines the architecture: **the LLM plans and writes, Jev perceives and judges, code counts and computes.** It also guarantees the agentic depth judges score at 30%: a planner calls Vexcel MCP and Matterport GraphQL tools, fans the images out to Jev, gates actions on Jev's confidence, and escalates uncertain cases.

### Image constraints that will bite with this data

Image support is labelled "Dreamer-ready" and must be switched on with the header `TypeSafe-Danger-Zone-Images: true` ([Images](https://docs.typesafe.ai/images.md)). The rules from the same page:

- PNG or JPEG only.
- **Each side must be 280–1568 px.** Out-of-range images are rejected, not resized, and one rejected image fails the whole request.
- EXIF data is stripped, so rotate the pixels upright before sending.

What that means for each data source:

- **Matterport 2K skybox faces (2048 px) will be rejected.** Request the `high` (1024) faces or downscale first.
- **Vexcel obliques must be cropped or tiled** to fit.
- **Box returns one box per question,** and it misses small targets in large images. The recommended pattern is to tile the image, run a Choice over the tiles, then run Box on the winning tile ([Box](https://docs.typesafe.ai/primitives/box.md)).
- **Use the direct API, not a gateway.** Vercel and OpenRouter carry Jev, but they may not forward the image headers. That is unverified.
- **Check access on day one.** Secondary sources call Jev "waitlisted," while the docs describe self-serve keys ([Quickstart](https://docs.typesafe.ai/introduction/quickstart.md)). The research could not resolve which is true.

### Where Jev fits in this data

| Agent task | Jev primitive and pattern | Input state | What code does |
|---|---|---|---|
| Is this floor occupied or cleared? | Score with a rubric ("active workspace" → "abandoned") | Matterport `high` skybox faces per sweep | Aggregates sweep scores into floor-level occupancy, weighted by `areaFloor` |
| Is this parking stall occupied? | One Noul per stall tile | Tiled Vexcel ortho/oblique crops | Sums stalls, then compares with Elements vehicle count and CoStar Parking Ratio |
| Locate a hazard or fixture (FDC, extinguisher, electrical panel) | Choice over tiles, then Box | Oblique tiles or skybox faces | Back-projects the box to 3D using the sweep pose, then calls `addMattertag` |
| Does this space look like the producer's reference still? | **Image-as-criteria** Choice, then Score | Scan frames as state, reference stills as options | Ranks candidates and filters by CoStar availability |
| Is the agent allowed to act? | Noul gate with **confidence routing** | Any proposed write or flag | Writes the tag or flag only above a threshold; otherwise routes to a human |
| Check CoStar fields extracted by an LLM | "SDE cascade": cheap extractor, Jev checks each field, only failures escalate | Record JSON plus derived evidence | Writes the ledger entry with per-field confidence |

These patterns come from TypeSafe's use-case map and cookbooks ([Use case map](https://docs.typesafe.ai/concepts/use-case-map.md); [llms.txt](https://docs.typesafe.ai/llms.txt)). Their closest demo to this track is Airbnb search, which found the 10 best of 1,000 listings "in about a second" by shortlisting with Choice and ranking with Score ([Demos](https://docs.typesafe.ai/demos.md)). That is a direct template for screening every CoStar building in a submarket.

**Don't duplicate what Vexcel already computes.** Elements already gives vehicle counts and roof objects, so spend Jev on judgments no vendor precomputes: interior occupancy, facade states, hazards, and the look of a space.

Two pitch lines:

- "Jev lets the agent look at 10,000 images in the time an LLM looks at 10."
- Show **calibrated probabilities on screen**, for example "87% confident, routed to a human." This makes "the agent knows when to stop" visible, which separates real agentic depth from a chat wrapper.

TypeSafe does not document **how many tokens an image consumes**. Measure it in the console in hour one before you size a fan-out.

## Roofs, solar, parking counts and site maps are already taken

The "we didn't know you could do that" bar rules out anything a CoStar judge has already seen in a pitch deck or on Devpost. Each cliché can be inverted into something open.

| Cliché | Who already owns it | Inversion that stays open |
|---|---|---|
| Roof condition, solar or peril scores from aerials | Moody's bought CAPE Analytics in January 2025 ([TechCrunch](https://techcrunch.com/2025/01/13/moodys-agrees-to-acquire-cape-analytics-which-develops-geospatial-ai-for-insurance-providers)); Nearmap bought Betterview ([CB Insights](https://www.cbinsights.com/compare/betterview-vs-cape-analytics)) | The **ground floor and interior** (mechanical rooms, entrance elevation, tenant business interruption), which roof-down vendors can't see |
| Rooftop solar estimation | HackPrinceton F25 Best Overall "Watt's Up" (SegFormer + NASA irradiance) ([Devpost](https://devpost.com/software/watt-s-up)) | Rooftop solar only as a *firefighter hazard* inside a pre-incident plan |
| "Agent scores sites and explains them on a map" | HackPrinceton F25 Best Overall "TerraLink" ([crafterwiki PR](https://github.com/RikepilB/crafterwiki/pull/22)) | Agents that **produce an artifact** (an annotated 3D tour, a pre-plan, a test-fit), not a ranked map |
| Parking-lot car counts as a business signal | Orbital Insight, 55,000+ retail lots ([Orbital Insight](https://medium.com/from-the-macroscope/orbital-insight-correctly-predicts-retail-sales-miss-hit-rate-grows-to-78-aa65ea445423)); academic proof it predicts earnings ([JFQA](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/2F5F99D68D1F8940F61578F198D6C005/S0022109023001448a.pdf/on-the-capital-market-consequences-of-big-data-evidence-from-outer-space.pdf)) | Counts **reconciled against CoStar leased SF and interior scans** at office buildings, not retail tickers |
| Q&A chatbot inside a 3D tour | CoStar shipped this on Homes.com and Apartments.com in July 2026 ([AIM Group](https://aimgroup.com/2026/07/15/costar-embeds-ai-conversations-into-matterport-3d-tours-on-homes-com-apartments-com/)) | An agent that **writes into** the tour (`addMattertag`) and outputs an auditable report |
| Vexcel's own MCP demos (rank a ZIP by roof condition, find pools, summarize tornado damage) | Vexcel's launch materials ([Vexcel MCP press release](https://vexceldata.com/?p=28435)) | Anything that needs interior or CoStar data Vexcel doesn't have |
| Facility "digital passports" for first responders | Matterport markets these, and Digital Twin Imaging sells them ([Matterport](https://matterport.com/blog/how-to-create-facility-passport)) | Fuse with the **CoStar tenant roster**, which neither offers |
| Office-to-residential conversion scoring | Widely discussed since LA's 2026 ordinance | Only differentiated if the scan drives a **real unit test-fit** |

The pattern across the table: incumbents work from **outside the building looking down**. The Matterport interior, joined to CoStar's tenant and lease records, is what none of them can show. Spend demo time there. Two caveats: the HackPrinceton Spring 2026 gallery and most F25 Devpost pages could not be reviewed, and no record of any earlier CoStar-sponsored hackathon track was found. That suggests judges have no "seen it" baseline for three-layer fusion.

## Houston and LA give the team two very different problem sets

The two metros share high office vacancy, but their building-level pressures differ, and each project direction should name its city. Broker figures disagree by several points, so cite ranges, not single numbers, in any pitch.

| Problem | Houston | Los Angeles |
|---|---|---|
| Office distress | Q3 2026 vacancy runs from **19.4% (Lee)** to **25.6% (Newmark)** and **27.6% (Colliers)** ([Lee](https://www.lee-associates.com/wp-content/uploads/2026/10/2026-Q3-Houston-TX-Office.pdf); [Newmark via CRE Daily](https://www.credaily.com/?p=224274); [TenantBase](https://www.tenantbase.com/houston/q3-2026/)). CBD is at 32.8%, and FM 1960 and North Belt are above 44% ([theBrokerList](https://blog.thebrokerlist.com/houston-office-isnt-recovering-its-splitting-in-two/)). The market still drew $1.5B of investment, and a demolition boom is under way ([CRE Daily](https://www.credaily.com/?p=223210)) | 23.4% vacancy in Q2 2026 (Cushman & Wakefield) and 25.1% at end-2025 (CBRE) ([Commercial Observer](https://commercialobserver.com/2026/05/california-office-vacancy-housing-conversion-policy/)) |
| Industrial and logistics | 7.2–10.0M SF of Q3 2026 absorption depending on source, with record $8.16/SF asking rents ([Lee](https://www.lee-associates.com/houston/2026/10/01/houston-industrial-distribution-market-report-q3-2026/); [Cushman](https://www.cushmanwakefield.com/en/united-states/insights/us-marketbeats/houston-marketbeats/industrial)). Yet **infill industrial vacancy is at a 20-year high** ([CoStar News](https://www.costar.com/article/719348529/houston-infill-industrial-market-faces-highest-vacancy-in-20-years-but-investors-keep-buying)). Houston ranks second nationally for data-center-related logistics demand ([CoStar](https://www.costar.com/article/1290934298/houstons-emergence-as-data-center-growth-market-generates-new-demand-for-industrial-real-estate)) | Not researched |
| Disasters and insurance | Hurricane Beryl (July 2024) caused massive power outages ([NOAA](https://nesdis.noaa.gov/news/hurricane-beryl-brings-massive-power-outages-east-texas)). Vexcel imaged the December 2024 EF2 tornadoes ([Vexcel](https://vexceldata.com/stories/gray-sky-houston-area-tornadoes/)). Flood and insurance cost burdens are widely cited, but only by low-authority sources | The January 2025 fires damaged or destroyed **374 commercial buildings worth nearly $2B** by CoStar's count ([Commercial Observer](https://commercialobserver.com/2025/01/la-fires-commercial-properties-2b/)). Palisades Village reopened in August 2026 after a $100M restoration ([Insurance Journal](https://www.insurancejournal.com/news/west/2026/08/19/881591.htm)) |
| Policy forcing building-level decisions | Not researched | The **Citywide Adaptive Reuse Ordinance** took effect February 2026 ([Greenberg Glusker](https://www.greenbergglusker.com/publications/citywide-adaptive-reuse-a-potential-solution-to-vacancy-and-housing)). The soft-story retrofit program covers about **13,500 buildings** and the non-ductile concrete program about 1,400–1,500 ([Bisnow](https://www.bisnow.com/news/los-angeles/multifamily/what-las-new-seismic-retrofit-law-means-for-building-owners-51989)). **Measure ULA** cut large-property sales by up to 50% per CoStar ([CoStar](https://www.costar.com/article/325930750/los-angeles-mansion-tax-faces-dual-rollback-efforts)) and had raised $1.03B ([Bisnow](https://www.bisnow.com/news/los-angeles/multifamily/measure-ula-1-billion-revenue-132634)) |
| Non-obvious demand | Industrial tenants with hazardous occupancies (inferred from the logistics mix) | On-location film shoot days fell **16.1% in 2025** to 19,694 ([FilmLA](https://filmla.com/wp-content/uploads/FilmLA-News-Release-Q2-2026-LA-Production-Report.pdf)). **8,667 federal ADA Title III suits** were filed in 2025, with California leading ([JD Supra](https://www.jdsupra.com/legalnews/ada-title-iii-federal-lawsuit-filings-2632226/)) |

Houston's problems are **market-structural and physical**: a split office market, a two-speed industrial market, and wind, flood and tornado exposure. Its best angles are distress prediction and ground-floor and occupancy risk. LA's problems are **regulatory and catastrophic**: conversion law, seismic mandates, a transfer tax, wildfire rebuild and ADA litigation. Each of these forces a decision about a specific building. Its best angles produce a building-specific artifact that answers a policy question.

## CoStar is turning AI into cheap proprietary data, and the hackathon is a preview

Read together, CoStar's 2026 announcements describe **one strategy with one motive**. Use AI to turn cheap physical capture (aerial flights, 3D scans, lease documents) into proprietary, verified data fields at a fraction of the cost of human researchers. Then sell that data into more workflows, especially the ones where money moves. Five threads point the same way.

### Thread 1: observe instead of research, at machine scale

**The announcements:**

- **Vexcel.** CoStar says it is buying Vexcel to create a "transformative new ultra low-cost proprietary data source." Florance said "there might be up to 1,000 fields of data you could pull on a building you see from the sky," and that CoStar can "observe and capture valuable data on hundreds of millions of properties in 24 months" ([Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)).
- **Tenant research.** The same call described an AI tenant-research process that lifts researcher productivity "more than tenfold." The goal is to refresh all 6.7M CoStar Tenant locations every year instead of a small fraction.
- **Rent Benchmark.** CoStar launched Rent Benchmark in mid-2026, built from **4 million AI-abstracted lease agreements** ([HousingWire](https://www.housingwire.com/articles/homes-com-helps-drive-costar-to-first-profitable-residential-quarter/)).
- **Document abstraction.** CoStar abstracted about 10M pages of Australian government filings with AI.

**The motive.** CoStar's moat has always been expensive human verification: researchers on the phone, camera cars on the street. AI over scans, aerials and documents is how CoStar keeps that moat while cutting the cost per verified field.

### Thread 2: defend the moat against general-purpose AI agents

**The announcements.** Florance's two recurring claims are that **75% of CoStar's content is not visible on the open internet**, and that an AI agent using only public data had a **75% error rate** against CoStar's single-digit rate. He also described fighting scrapers continuously and said "the law is the law" on copyright ([Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)).

At the same time, CoStar partners with LLMs as **distribution, not replacement**. ChatGPT conversations hand renters off to Apartments.com, and LLM-sourced leads are still "low single digit" percent (same source).

**The motive.** As AI agents become the main way people ask questions about property, CoStar wants to be the **trusted data source inside every agent**, not a website that agents scrape and replace.

### Thread 3: profit discipline under investor pressure

**The pressure.** After an activist campaign by Third Point and D. E. Shaw that called for a board overhaul and a retreat from Homes.com ([Real Estate News](https://www.realestatenews.com/2026/01/27/investor-calls-for-costar-board-overhaul-exit-from-homes-com)), CoStar cut Homes.com net investment by $300M for 2026 ([Online Marketplaces](https://www.onlinemarketplaces.com/articles/costar-signals-spending-pullback-at-homes-com-as-profitability-timeline-sharpens/)).

**The numbers** ([Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)):

- 2026 adjusted EBITDA guidance raised to $820–840M, a **22% margin, up from 14% in 2025**.
- A **$1.25B adjusted EBITDA target for 2028**, reaffirmed.
- About $150M in 2026 cost cuts plus about $200M more in efficiencies.
- Matterport expected to be profitable by end-2027.

**The motive.** AI has to show up as **margin**: fewer researcher hours per field, and new data products that cost little to produce.

### Thread 4: move from information subscriptions into transaction workflows

**The announcements** ([Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)):

- **Debt Solutions Benchmark** launched on **$1.5T of CRE debt across 155,000+ loans**, with **loan origination** capabilities planned for 2027.
- Real Estate Manager and Visual Lease (lease administration) will be integrated into CoStar in late 2027.
- Vexcel aerial features will arrive in CoStar in late 2027.

**The motive.** Lenders, servicers and lease administrators make recurring, high-stakes decisions about specific buildings. Data delivered *inside* those decisions is stickier and more valuable than data in a search tool.

### Thread 5: carry AI from consumer portals to the commercial side

Homes AI (February 2026) and Apartments.com Ai (June 2026) are live. CoStar has said it will extend the same capability to CoStar, LoopNet and other brands ([BusinessWire](https://www.businesswire.com/news/home/20260217810823/en/CoStar-Group-Launches-Transformative-AI-Experience-on-Homes.com-Redefining-the-Future-of-Home-Shopping)). **No commercial-side AI assistant has launched yet.** That is a gap a hackathon prototype can visibly fill.

### What this means for a project

The single most aligned framing is an **"AI researcher" agent**. It looks at a building through Vexcel and Matterport and proposes new or corrected CoStar fields, each with evidence images and a calibrated confidence. It auto-accepts high-confidence fields and queues the rest for a human researcher. It then pushes the anomalies that matter into a lender's or broker's workflow.

That one system hits all five threads:

- cheap observed data (Vexcel/Matterport → fields);
- moat defense (it shows that agents need CoStar's records to be right);
- margin (researcher hours saved per verified field);
- workflow expansion (a lender watchlist);
- commercial-side AI (nothing comparable exists in CoStar Suite).

Jev's confidence scores are the mechanism for "auto-accept vs. human review." The pitch metrics CoStar's executives already use are **fields extracted per building, cost per verified field, error rate versus a public-data-only baseline, and researcher-minutes saved**.

How each direction scores against the strategy:

| Direction | Strategic alignment | Which thread it serves |
|---|---|---|
| Building truth ledger, reframed as an "AI researcher" with a review queue | **Highest** | Observe at scale; margin; moat (beats public-data agents) |
| Shadow Vacancy, delivered as a lender/servicer watchlist | **Highest** | Debt workflows (origination 2027); verified vacancy is CoStar's core product |
| Ground-floor flood and business-interruption exposure | High | New Vexcel-derived fields; lender and insurer risk |
| First Due fire pre-plans | Medium | New buyer for existing data; little margin or workflow fit |
| Scout film locations | Medium-low | Monetizes vacancy for landlords, but outside CoStar's markets |
| Seismic + ULA, ADA, adaptive reuse | Medium | Building-level fields; policy-driven niches |

The recommended merge is to **build the AI researcher as the base, and point its output at Shadow Vacancy for a lender watchlist** as the headline demo. Pitch it as "CoStar's 2027 Vexcel roadmap, running on Houston buildings this weekend, with an audit trail a researcher would sign off on."

The surprise comes from the interior evidence and the timeline alignment. The alignment comes from speaking CoStar's own language: proprietary observed data, researcher productivity, and lender workflows.

## Seven directions, ranked by surprise times buildability

The ranking below reflects this report's own judgment. It weighs the four judging criteria against **data risk**: how badly the concept breaks if the toolkit lacks a field. Scores are 1–5.

| Rank | Direction | City | Data use (30%) | Agentic depth (30%) | Usefulness (25%) | Demo (15%) | Data risk | "We didn't know" line |
|---|---|---|---|---|---|---|---|---|
| 1 | Shadow Vacancy | Houston (also LA) | 5 | 5 | 5 | 4 | **High** (needs lease and multi-date data) | "CoStar says 92% leased. The parking lot and the floors say 41%." |
| 2 | First Due: tenant-aware fire pre-plans | Houston industrial / LA | 5 | 5 | 4 | 5 | Medium (needs tenant names) | "Dispatch to a 10-second pre-plan, written into the 3D tour." |
| 3 | Scout: vacant CRE as film locations | LA | 4 | 4 | 3 | 5 | Medium (needs availability and good interiors) | "Your vacancy is a soundstage." |
| 4 | Ground-floor flood and business-interruption exposure | Houston | 5 | 4 | 4 | 3 | Medium (needs ground-floor scans) | "Insurers score the roof; the losses happen in the basement." |
| 5 | Building truth ledger (the base layer, shipped on its own) | Both | 5 | 4 | 5 | 3 | **Low** | "We built your 2027 aerial-fields roadmap this weekend." |
| 6 | Seismic + ULA forced-seller radar | LA | 3 | 3 | 4 | 3 | High (Matterport is weak here; mostly multifamily) | "Who has to sell before the retrofit deadline, and at what tax." |
| 7 | ADA path-of-travel risk / adaptive-reuse X-ray | LA | 4 | 3 | 4 | 3 | Medium (opening widths need PI Enterprise) | Lower; both ideas are familiar |

### 1. Shadow Vacancy: leased-but-dark detection

**The problem.** Houston office vacancy runs 24–28% on most counts, with submarkets above 44%. Leased space that tenants have stopped using is invisible in lease data until a sublease or a non-renewal.

**The agent loop:**

- **Select candidates.** The LLM planner queries CoStar for buildings with lease expirations in the next 24 months, their tenants and reported leased SF. It also pulls sale and loan history if exposed.
- **Read the exterior.** For each building it calls the Vexcel MCP for multi-date orthos and obliques and the Elements vehicle counts across flight dates. Jev adds per-stall Nouls on tiled crops wherever Elements counts are missing, and facade judgments (blinds drawn, signage removed).
- **Read the interior.** It pulls Matterport sweeps per floor. Jev scores each `high`-resolution skybox face on an occupancy rubric. Code weights the scores by floor `areaFloor`.
- **Reconcile.** It compares "observed occupancy" with CoStar leased SF on one timeline and outputs a ranked watchlist for lenders or brokers. Each flag carries its evidence images and calibrated confidence.

**Why it surprises.** It turns CoStar's own two acquisitions into a verification engine for CoStar's core vacancy product. The interior evidence is something no parking-lot vendor has.

**The trap.** Commercial Matterport scans are often made to **market space that is already available**, so an empty scanned floor is only an anomaly if CoStar lists that floor as *leased*. Compare scan `created` dates against lease dates. Ask whether Vexcel flights happen on weekdays; a Sunday flight empties every lot.

**If the data falls short.** Without lease-expiry fields or multi-date imagery, this collapses to a single-date comparison. Fall back to direction 5.

### 2. First Due: tenant-aware pre-incident plans

**The precedent.** Fire departments already use Matterport models. In one vendor-reported exercise, room-to-room search time fell **from over 7 minutes to under 30 seconds** after pre-planning ([Matterport case study](https://matterport.com/industries/case-studies/transforming-emergency-preparedness-how-digital-twin-imaging-and-matterport)). But Matterport's "facility passports" do not know **who occupies the building or what they store**. CoStar's tenant roster does.

**The agent loop**, run on a simulated dispatch to an address:

- **Classify occupancy.** Read CoStar tenants, use type and after-hours occupancy. Jev runs a Choice over hazard classes, for example battery distributor, chemical storage, daycare or assembly.
- **Read the exterior.** Pull obliques from all four directions. Vexcel Custom Elements, or Jev tile-then-Box, locates fire department connections, hydrants, gates and roof access. Elements supplies stories, roof height and rooftop solar (here a hazard, not a cliché). In LA it also supplies the defensible-space buffers.
- **Read the interior.** Fan Matterport skybox faces out to Jev: Nouls for stairwells, standpipes, electrical panels and storage racks, then Box to locate each. Back-project each box with the sweep pose, then **write it into the tour with `addMattertag`**, gated on confidence.
- **Brief.** The LLM writes a one-page brief. Low-confidence items are marked "verify on arrival."

**Why it ranks second.** It uses all three layers naturally, the write-back is real agentic depth, and a timed live demo is dramatic.

**The risk.** Usefulness to CoStar's *revenue* is indirect. Pitch it as a new buyer for data CoStar already owns.

### 3. Scout: vacant space as film locations

**The problem.** LA on-location shoot days fell 16.1% in 2025, while LA has an estimated 50M+ SF of vacant office (an LA Times figure via a secondary source, [The Pride LA](https://thepridela.com/2026/02/new-law-aims-to-unlock-50-million-square-feet-of-empty-office-space/)).

**The agent loop:**

- A producer uploads reference stills, such as "1970s bank lobby" or "raw industrial loft."
- Jev's **image-as-criteria** Choice compares Matterport scan frames against the references, and Score ranks the matches. Randomize option order to counter Jev's first-option bias.
- Code filters to CoStar spaces that are available now.
- Vexcel orthos and Elements hardscape estimate room for basecamp and truck parking. Obliques show street frontage.
- The LLM drafts landlord outreach with a location-fee estimate.

**Why it surprises.** It turns vacancy, CoStar's bad-news metric, into landlord income, and no CoStar product targets this buyer.

**The weaknesses.** Its usefulness score depends on judges valuing a new market. It also needs LA scans with visually distinctive interiors.

### 4. Ground-floor flood and business-interruption exposure

This direction inverts the crowded roof-scoring market.

- **Exterior.** Vexcel Elements supplies **ground and entrance elevation**, and DSM/DTM gives grade.
- **Interior.** Jev on Matterport frames spots electrical and mechanical equipment on the ground floor and in basements.
- **Tenants.** CoStar tenants give the business-interruption exposure: who goes dark if the ground floor floods.
- **Validation.** Gray Sky imagery of the December 2024 Houston tornadoes is a before/after case for checking damage triage.

It scores high on data fusion, and only Matterport supplies the ground-floor view that CAPE and Betterview lack. Two weaknesses: it needs ground-floor and basement scans, and the research found **no cited 2025–2026 data on Houston flood effects on commercial values**, so the stakes must be argued, not quoted.

### 5. The building truth ledger, shipped on its own

This is the reconciliation base described earlier, finished as a product. For each building it compares:

- CoStar RBA vs. the sum of Matterport `areaFloor` vs. Vexcel stories × footprint;
- CoStar Typical Floor vs. scanned floor dimensions;
- CoStar Parking Ratio vs. stalls counted from aerials.

Each field gets a consensus value, a disagreement flag and a Jev-verified confidence, and anomalies are routed to a "researcher queue."

It is the least surprising concept, and the most directly aligned with CoStar's stated plan to extract "hundreds of data fields per property" from imagery. It carries **low data risk** because it needs only basic attributes. Treat it as the guaranteed-ship fallback.

### 6–7. Forced-seller radar, ADA scoring and the adaptive-reuse X-ray

**Seismic + ULA forced-seller radar (LA).** Custom Elements detects tuck-under soft-story parking on obliques. CoStar supplies owner tenure, last sale and price. Code models retrofit cost plus the ULA tax at sale. The idea is clever, but Matterport adds little, and the target stock is largely multifamily, which CoStar's commercial dataset may not include.

**ADA path-of-travel scorer (LA retail).** This is concrete given the litigation volume. But the cheap door-width signal needs Property Intelligence `openings.width`, which is Enterprise-only, and that weakens it.

**Adaptive-reuse X-ray.** Floor-plate depth to windows, plus core positions, plus lease-expiry timing produces a unit test-fit. It is policy-relevant under LA's ordinance but widely pitched, and it is only worth building if the interior-derived test-fit is real rather than a score.

## Fifteen questions to settle with CoStar sponsors before committing

Ask these in the first two hours. The answers decide which concept survives.

| #   | Question                                                                                                                                                        | Why it matters                                                                        | Gates      |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------- |
| 1   | What is the join key across CoStar, Matterport and Vexcel (property ID, lat/long, footprint)?                                                                   | Every concept starts with the join                                                    | All        |
| 2   | How many buildings, how many in Houston vs. LA, and which property types (office, industrial, retail, multifamily)?                                             | Shadow Vacancy needs office; First Due prefers industrial; Scout needs LA             | All        |
| 3   | Which CoStar fields are exposed: lease comps and **expiration dates**, **tenant names and use**, availabilities, sale comps, owners, loans, market time series? | Shadow Vacancy needs expirations; First Due needs tenants; Scout needs availabilities | 1, 2, 3, 6 |
| 4   | Is the Matterport token Enterprise tier: is Property Intelligence (vector walls, opening widths, room classes) enabled?                                         | Opening widths and room labels shortcut ADA, test-fit and pre-plans                   | 2, 7       |
| 5   | Are any bundles (MatterPak, E57, schematic floorplans) pre-unlocked?                                                                                            | Point clouds can't be bought and delivered within 36 hours                            | 4, 7       |
| 6   | Does our token have **write scope** for `addMattertag` / `patchMattertag`?                                                                                      | Write-back is the strongest agentic-depth moment                                      | 2          |
| 7   | Which skybox resolutions are available (2K? 4K?), and are defurnished `views` included?                                                                         | Jev needs faces between 280 and 1568 px; defurnished views help Scout and test-fit    | 1, 2, 3    |
| 8   | What are the Matterport scan dates (`created`) relative to lease events? Were scans captured for leasing vacant space?                                          | Avoids the Shadow Vacancy false positive                                              | 1          |
| 9   | Which Vexcel entitlements are on: Elements, Custom Elements, embeddings search, DSM/DTM, Gray Sky?                                                              | Custom Elements on obliques powers First Due and Seismic                              | 1, 2, 4, 6 |
| 10  | How many **flight dates** per building, and on which days of the week?                                                                                          | Multi-date change detection and parking-occupancy validity                            | 1, 4       |
| 11  | What are the MCP tool names and schemas, and the rate limits for every service?                                                                                 | Sizes the fan-out and avoids throttling mid-demo                                      | All        |
| 12  | Data policy: may CoStar data and imagery go to third-party models (Claude, Jev), and may it appear in a public Devpost or video?                                | CoStar actively enforces its terms; a policy breach is disqualifying                  | All        |
| 13  | May we join outside public data (FEMA flood zones, LADBS seismic lists, FilmLA)?                                                                                | Several concepts get stronger with one public layer                                   | 3, 4, 6    |
| 14  | Who are the judges (research, Matterport, Vexcel, product), and is there a TypeSafe/Jev credit or waitlist path for hackers?                                    | Pitch framing, and confirming Jev is reachable at all                                 | All        |
| 15  | Can one submission enter both the CoStar and AWS (Amazon) prizes, and does the CoStar data policy allow processing on AWS (Bedrock, S3)? | Building one project for two prizes only pays off if the rules allow it and the data may be hosted on AWS | All |

The decision rule:

- **Expirations, tenants and multi-date flights all exposed:** build Shadow Vacancy on top of the ledger.
- **Tenants but no lease timeline:** pivot to First Due.
- **The LA set is rich in interiors but thin on records:** Scout.
- **Everything is thinner than hoped:** ship the truth ledger with one vertical demo, and win on fusion and polish.

Split the team three ways. One person owns the join and the ledger. One owns the agent loop and the Jev integration (including measuring image token cost in hour one). One owns the 3D/aerial UI and the demo script. The demo should show the Matterport interior and the Vexcel exterior side by side, with Jev's confidence numbers visible on screen.

## Conclusion

The research changes what "use of data" means for this track. The obvious reading is "pull from two APIs and put both on a dashboard." The stronger reading is that the layers are **adversarial evidence**: each was captured by a different process on a different date, and their disagreements carry the information CoStar's researchers currently pay people to find. CoStar's own pitch to investors is that proprietary, directly observed data beats public-data AI (the 75% vs. single-digit error claim), and that aerial AI will generate hundreds of new fields per property by late 2027. A team that shows those fields being *checked against the interior* and *aligned on a timeline with leases* is showing CoStar something it has announced but not shipped.

The less obvious implication concerns Jev. Its value here is not speed for its own sake. Calibrated, typed judgments make an agent's restraint visible: it writes a tag into a live 3D tour only when it is 90% sure and sends the rest to a human. That turns "agentic depth" from a count of tool calls into something judges can watch, and a CoStar executive can picture running across millions of property records.
