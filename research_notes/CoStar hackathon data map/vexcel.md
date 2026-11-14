# Vexcel Imaging / Vexcel Data Program: Imagery, Derived Data, and Developer APIs (as of Nov 2026)

Research date: 2026-11-13. Sources are mostly Vexcel's own marketing and docs pages plus the CoStar SEC filing. Vexcel's sites (vexceldata.com, vexcel-imaging.com) are vendor self-reporting: accuracy and coverage claims have not been independently checked. The detailed API reference (api.vexcelgroup.com/v2/) needs Vexcel credentials, so exact endpoint paths and parameters could not be confirmed.

## 1. Corporate status: did CoStar acquire Vexcel?

### Takeaway
CoStar has signed an agreement to buy Vexcel but has not closed the deal. CoStar Group agreed on Oct 27, 2026 to buy Vexcel Group, Inc. for about $730M in cash, with closing expected in Q1 2027 subject to regulatory approval. Vexcel keeps its brand and its CEO, Erik Jorgensen. CoStar's stated plan is to run AI over Vexcel imagery to extract "hundreds of data fields per property." The hackathon sponsor track fits that thesis directly.

### Cited Findings
- On Oct 27, 2026, CoStar Group (NASDAQ: CSGP) announced an agreement to acquire Vexcel Group, Inc. for about $730 million in cash. Closing is expected in the first quarter of 2027, subject to customary closing conditions and regulatory approvals. It will be funded from cash on hand and CoStar's revolving credit facility — [CoStar press release, SEC 8-K Ex. 99.2](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm)
- Vexcel's financials: more than $140M in trailing-12-month revenue, up over 30% year over year, mostly from recurring multi-year data contracts, at about a 20% adjusted EBITDA margin — [SEC 8-K Ex. 99.2](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm)
- Vexcel's scale per the release: more than 60M images a year, major US metros refreshed up to 3 times a year, disaster zones flown within 24 hours, more than 45 countries, 320 major metros, 99.6% of the US population, about half a billion properties captured, and 7.5–15 cm resolution ("~16x finer than typical satellite") — [SEC 8-K Ex. 99.2](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm)
- CoStar's rationale: AI applied to the imagery can capture "hundreds of data fields per property," creating an "ultra-low-cost proprietary data source." The imagery would complement CoStar's vehicle-mounted cameras. CoStar also plans to use its roughly 2,000 salespeople to sell Vexcel products — [SEC 8-K Ex. 99.2](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm); [CRE Daily](https://www.credaily.com/briefs/costars-vexcel-acquisition-adds-aerial-imagery-for-730m/?.tsrc=rss)
- Vexcel designs and builds its own UltraCam aerial cameras and controls the aircraft and the processing pipeline end to end — [SEC 8-K Ex. 99.2](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm)
- The CoStar Q3 2026 10-Q references a "Vexcel Merger Agreement" entered into through the CRI subsidiary — [CoStar 10-Q Q3 2026](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000083/csgp-20260930.htm)
- Advisors: Goldman Sachs and Latham & Watkins for CoStar; William Blair and Snell & Wilmer for Vexcel — [SEC 8-K Ex. 99.2](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm); [William Blair](https://www.williamblair.com/News/Vexcel-and-CoStar-Group-Transaction)
- Vexcel's press dateline is Centennial, Colorado — [Vexcel MCP press release](https://vexceldata.com/?p=28435)

### Inferences
- The deal is pending and does not close until about Q1 2027. In Nov 2026 the hackathon's API access is probably a sponsor-provisioned Vexcel license or sandbox, not an integrated CoStar product. The "Sandbox Evaluation" offering on Vexcel's platform page is a likely mechanism.
- CoStar's stated thesis is AI extraction of property fields from aerial imagery, combined with CoStar listings and records and Matterport interiors. Projects that demonstrate exactly this, such as automatically filling or validating CoStar property fields from imagery, are likely to resonate with judges.
- Some reports cite Oct 26 for the announcement and others Oct 27. The SEC exhibit says Oct 27.

### Gaps
- No integrated CoStar–Vexcel product has been announced. CoStar's press materials do not link Vexcel to Homes.com or Matterport.
- Vexcel's corporate history (Graz, Austria origin; UltraCam previously under Microsoft) was not re-verified in this session.

## 2. Imagery types, resolution, cadence, archive, and Gray Sky coverage (Houston, LA)

### Takeaway
Vexcel captures, from a single flight program:
- Ortho (wide-area, 15–20 cm)
- 7.5 cm TrueOrtho (no building lean, pixel-aligned to the DSM)
- 4-direction 45-degree obliques plus nadir at 7.5 cm
- Near-infrared, delivered as color-infrared (CIR)
- DSM/DTM

"Urban" collections are refreshed up to 3 times a year in major US metros, and the archive goes back to about 2012. Gray Sky disaster imagery is confirmed for the LA January 2025 wildfires and for Houston-area tornadoes (Dec 2024 and Nov 2025). I could not confirm Gray Sky coverage of Hurricane Beryl in Houston.

### Cited Findings
**Imagery product line**
- **Oblique:** four cardinal directions at 7.5 cm, "accurate to within a two-pixel standard deviation," matched to ground control points with lossless compression — [Vexcel High Resolution page](https://vexceldata.com/?p=3475)
- **TrueOrtho:** 7.5 cm, matched to the DSM, with "no visible seamlines or building lean" — [Vexcel High Resolution page](https://vexceldata.com/?p=3475); [VDP brochure 2021 (older)](https://vexceldata.com/wp-content/uploads/2021/11/VDP-Overview-Brochure-US_Digital_20211115.pdf)
- **Resolution by area:** urban 7.5–15 cm, rural 15–20 cm — [Vexcel High Resolution page](https://vexceldata.com/?p=3475)
- **Multispectral:** near-infrared is collected during regular captures and delivered as color-infrared (CIR) ortho imagery. The DSM has a "perfect pixel-to-data match" with TrueOrtho and Multispectral — [Vexcel High Resolution page](https://vexceldata.com/?p=3475)
- **Elevate (DSM/DTM):** DSM includes objects, DTM is bare earth — [Vexcel High Resolution page](https://vexceldata.com/?p=3475)
- **UP42 marketplace specs** (third-party reseller listing):

  | Product | Resolution | Absolute accuracy |
  |---|---|---|
  | Ortho | 15 cm | 1 m RMSE |
  | True Ortho | 5.5 cm | 15 cm RMSE x/y/z |
  | Obliques/Nadir | 5.5 cm | 3.8 cm x/y, 7.5 cm z (relative) |

  Also from the same listing:
  - Bands: RGB, plus false-color NIR (690–800 nm) when nadir is present.
  - Delivery: GeoTIFF with GeoJSON metadata, 8-bit.
  - Archive: 2012 to present.
  - Area limits: Obliques max 2.5 × 2.5 km bounding area; Ortho/True Ortho AOI max 50 km².

  — [UP42 docs: Vexcel Aerial](https://docs.up42.com/data/vexcel-aerial). Note: the 5.5 cm figure conflicts with Vexcel's own "7.5 cm" claim and may reflect a newer sensor or a specific collection.
- **Collection layers** named in the MCP docs: "urban" (cities), "wide-area" (regional), and "graysky" (disaster response) — [Get Started with Vexcel MCP](https://vexceldata.com/?p=28421)
- **3D:** Vexcel's UltraMap Studio photogrammetry software can "create, visualize, and export textured 3D meshes and colorized point clouds." True ortho, obliques, and a 3D mesh can come from one consistent dataset — [Vexcel-imaging UltraMap Studio webinar page](https://www.vexcel-imaging.com/news/ultramap-studio-part-8-3d-production/). The API is organized by collection, event, extract, and tile, covering "3D, DSM, DTM, Ortho, and Oriented" data — [Vexcel Platform page](https://vexceldata.com/au/platform/)
- **Lidar** is mentioned in CoStar's release as part of the capture technology, but no Vexcel lidar data product is described — [SEC 8-K Ex. 99.2](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm)
- **Cadence:** major US metros are refreshed up to 3 times a year, and disaster zones are flown within 24 hours — [SEC 8-K Ex. 99.2](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm)

**Gray Sky: LA wildfires (Jan 2025)**
- Collections: Jan 10 and 11, Jan 13 (final initial day, over Palisades), Jan 20, and Feb 2 (Palisades, Hurst, Sunset, Eaton). As of Jan 13, Palisades had been flown 3 times, Eaton 2 times, and Hurst, Kenneth, and Sunset once each — [Gray Sky: California Wildfires](https://vexceldata.com/?p=17177)
- About 360 km² of the first collections were wildfire-affected areas. Products were oblique, ortho, and multispectral; later posts mention 10 cm ortho. Before/after comparison imagery, color-coded damage footprints, and property damage assessments were provided for the Palisades and Eaton collections — [Gray Sky: California Wildfires](https://vexceldata.com/?p=17177)
- The LA wildfire response brief reportedly lists 827,149 structures analyzed and 16,867 homes destroyed — [Vexcel LA Wildfires Response brief (PDF)](https://vexceldata.com/wp-content/uploads/2025/03/Vexcel-LA-Wildfires-Response-brief.pdf). Caveat: these figures come from a search snippet. I could not read the PDF text directly to verify them.
- Vexcel's report includes AI damage analysis in ArcGIS, which identified untouched structures in Pacific Palisades — [The LA Wildfires: Insights and a Report](https://vexceldata.com/?p=17893)

**Gray Sky: Houston**
- Dec 28, 2024 EF2 tornadoes: missions were completed by the following Monday, north and south of Houston's center (including Alvin and Conroe). Products were oblique, ortho, and multispectral at 7.5 cm, plus color-coded damage footprints and assessments. Before-event imagery is available — [Gray Sky: Houston Area Tornadoes](https://vexceldata.com/stories/gray-sky-houston-area-tornadoes/)
- Nov 2025: Gray Sky imagery of a tornado near Louetta, TX, just outside Houston — [Gray Sky: Tornado in Louetta, TX](https://vexceldata.com/?p=24054)
- **Hurricane Beryl (July 2024):** no Vexcel Gray Sky page was found. The post-Beryl Houston aerial imagery I found was from competitor Nearmap — [Nearmap Beryl white paper](https://nearmap.com/white-papers/hurricane-beryl-government)

### Inferences
- Houston and LA are both top US metros, so they likely have multiple blue-sky captures a year and a deep archive (back to about 2012 per UP42). That makes multi-date change detection feasible for real buildings. This is inferred; check per-address coverage with the coverage services.
- For LA, pre-fire, post-fire (Jan–Feb 2025), and later rebuild-era captures would let a project track reconstruction progress parcel by parcel.

### Gaps
- No Vexcel Beryl (2024) or Harvey (2017) Gray Sky collection was confirmed. They may exist behind the platform login.
- No published per-city capture-date lists for Houston and LA were found.
- No public pricing or resolution for the DSM/DTM was found.

## 3. Derived products (Elements AI, Vexcel Intelligence, 3D, elevation)

### Takeaway
Vexcel's AI layer has three tiers:
1. **Elements:** more than 40 precomputed building and property attributes, plus Roadways and Damage Assessment.
2. **Custom Elements** (launched Aug 19, 2026): text-prompted, zero-training object detection on ortho and oblique imagery, returning segmentation polygons.
3. **Semantic search:** more than 3B vector embeddings over 15.1M km² of imagery.

Elevation comes as DSM/DTM. 3D meshes can be produced from UltraMap.

### Cited Findings
**Elements building and roof attributes** (more than 40 validated attributes)

| Group | Attributes |
|---|---|
| Footprint | Footprint polygon, footprint area |
| Ground | Ground elevation, entrance elevation, primary structure, structure distance |
| Building | Volume below eave, number of stories |
| Roof | Condition, material, shape, centroid, elevation, max height, eave height, attic habitable |
| Roof objects | Solar (detected), PV and thermal panels (count and area), AC units, chimneys, satellite dishes, vents, skylights, tree cover over roof |
| Roof discoloration | Algae and vent staining, water pooling (wet/dry), vegetation on roof, organic matter |
| Roof defects | Tarp (detected, area), debris, rust, structural damage |

— [Elements: Property Attributes](https://vexceldata.com/products/elements/property-attributes/)

**Elements property and parcel attributes**

| Group | Attributes |
|---|---|
| Parcel | Parcel geometry, tree cover |
| Defensible space | Buildings and trees within 5, 30, 100, and 200 ft buffers |
| Pools | Pool (detected), pool type, count by type, water slide, diving board |
| Structures and surfaces | Hardscapes, deck, enclosure |
| Recreation | Sport court, playground, trampoline |
| Vehicles | Detected, type, count |

— [Elements: Property Attributes](https://vexceldata.com/products/elements/property-attributes/)

**Elements: other facts**
- Precomputed in the US, Canada, Australia, and New Zealand for "millions of residential and commercial properties."
- Delivered via data files, PDF property reports, partner sites, and the Vexcel Platform (Viewer, APIs, Studio, MCP).
- Updated "as new aerial imagery is collected." Each attribute is tied to timestamped imagery, so changes over time can be tracked.

— [Elements: Property Attributes](https://vexceldata.com/products/elements/property-attributes/); [Elements AI](https://vexceldata.com/au/products/elements)
- 20 of the attributes are roof-specific. Vexcel's sample of 100 random addresses scored roof condition on a 1–5 scale: 43 rated 3/5, 41 rated 4/5, 16 rated 5/5. This is vendor self-reported — [Vexcel: what can 100 random properties tell you about risk](https://vexceldata.com/stories/what-can-100-random-properties-tell-you-about-risk/)

**Damage Assessment and Roadways**
- Damage Assessment (an Elements product): AI applied to Gray Sky imagery produces color-coded damage footprints and property-level damage scores for wildfires, hurricanes, and tornadoes — [Elements: Damage Assessment](https://vexceldata.com/products/elements/damage-assessment/)
- Roadways is a separate Elements product. Its attributes were not detailed on the pages fetched — [Elements AI](https://vexceldata.com/au/?p=29370)

**Vexcel Intelligence**
- The three tiers are named "Ready to Go" (Elements), "Ready to Find" (Custom Elements: e.g., electric poles, docks, street lights, solar farms, propane tanks), and "Ready to Search" (semantic search via vector embeddings and natural language). It is live in more than 45 countries — [Vexcel Intelligence](https://vexceldata.com/ai/)
- Embeddings: more than 3 billion vectors from 15.1M km² across 47 countries. Urban embeddings use ortho plus 45-degree oblique imagery; rural embeddings use ortho only — [Insurance Edge, Sep 30 2026](https://insurance-edge.net/2026/09/30/vexcel-intelligence-offers-aerial-imagery-searchable-using-everyday-language/)
- Custom Elements (Aug 19, 2026): the user names an object, and the system returns its location plus a segmentation polygon with no model training. It is Vexcel's first AI detection on oblique imagery, which makes facades and vertical structures detectable. Access is via Vexcel Studio, APIs, and MCP — [Vexcel Custom Elements launch](https://vexceldata.com/?p=29613)
- Recent Vexcel Intelligence stories: "Where Are the Areas of Rapid Change?" (Oct 28, 2026) and "What Does It Take to Find Culverts in a State?" (Nov 11, 2026). These suggest change-detection capability — [Vexcel Intelligence](https://vexceldata.com/ai/)

### Inferences
- "Vehicles: detected, type, count" at parcel level, combined with a multi-date archive, gives a direct occupancy proxy (cars in lots over time) for commercial properties. CoStar cares about this for office and retail.
- Number of stories, eave height, max roof height, and volume below eave enable gross building area (GBA) estimates. These can be cross-checked against CoStar's recorded building size and Matterport floor plans.
- Custom Elements and semantic search let a team detect objects that are not in the precomputed list, such as EV chargers, rooftop HVAC, parking striping, or construction cranes.

### Gaps
- No standalone "building footprints" or "3D building models" data product page was found for the US beyond the Elements footprint polygon. Whether textured meshes are a sellable data product (as opposed to UltraMap software output) is unclear.
- No published accuracy metrics for Elements were found.
- No full list of Elements attributes specific to commercial properties was found.
- "Blue Sky Ultra" could not be confirmed as a current product name.

## 4. Developer access: APIs, tiles, SDKs, MCP, auth

### Takeaway
Developers have four main routes in:
- **REST API v2** at `https://api.vexcelgroup.com/v2/`. API 1.0 was deprecated on July 6, 2026.
- **Tile services:** OGC WMTS and Esri Image Services for ArcGIS.
- **MapControl JavaScript SDK.**
- **Vexcel MCP server** at `https://api.vexcelgroup.com/v2/mcp` (launched July 1, 2026). It authenticates with an API key and takes WKT geometry. Its capabilities cover ortho and oblique imagery, DSM/DTM, property metadata, damage, embeddings search, and custom elements.

For an AI-agent hackathon, the MCP server is the highest-leverage entry point.

### Cited Findings
**REST API v2**
- The API is a set of HTTPS services for viewing and downloading discrete nadir and oblique images, orthomosaics, DSM/DTM tiles, and metadata. It also covers checking imagery coverage and running imagery operations. The docs require Vexcel Viewer credentials — [Vexcel API 2.0 Documentation (support KB)](https://support1.vexceldata.com/knowledge/vexcel-api-2.0-documentation)
- "API 1.0 was deprecated on July 6, 2026." API v2 is at https://api.vexcelgroup.com/v2/. Migration guides and "API 2.0 Tutorials and Extras" are available — [Vexcel APIDOCS (Atlassian)](https://vexcel.atlassian.net/wiki/spaces/APIDOCS/overview)
- Services are organized by collection, event, extract, and tile, covering 3D, DSM, DTM, Ortho, and Oriented data — [Vexcel Platform](https://vexceldata.com/au/platform/)
- Legacy v1.4 docs describe:
  - an ImageLayerCoverage service that returns coverage geometry as JSON;
  - Coverage services that answer "do we have data here" without returning imagery;
  - a WMTS for Ortho layers usable in ArcGIS and QGIS;
  - GetOrthoImageTile with Vexcel-specific parameters;
  - a feature to extract a large orthomosaic chunk in one call.

  — [Vexcel API docs search results](https://vexcel.atlassian.net/wiki/spaces/APIDOCS); [ImageLayerCoverage v1.4](https://vexcel.atlassian.net/wiki/spaces/APIDOCS/pages/2131887265); [New Feature: Extract Large Orthomosaic Tiles](https://vexceldata.com/?p=2261). Note: these are v1.4 and now deprecated, so they are older info.
- Sample apps, including an authentication demo and an imagery metadata example, accept "Vexcel Data Program or GIC platform credentials" — [Developer Utilities and Demo Applications](https://gicapps.azurewebsites.net/static)

**Other platform components**
- Vexcel Viewer: a no-code web app for measuring area and length, comparing ortho and oblique imagery across collections side by side, and analyzing more than 40 attributes per property.
- MapControl SDK: JavaScript, for web, mobile, GIS, CAMA, and CAD apps.
- Image Services for ArcGIS: ortho, oblique, nadir, and elevation imagery without plug-ins.
- WMTS map tiles.
- On-premises datasets.
- Sandbox Evaluation access by request.

— [Vexcel Platform](https://vexceldata.com/au/platform/)

**Vexcel MCP**
- Server URL: `https://api.vexcelgroup.com/v2/mcp`
- Authentication: an API key from Vexcel support, entered when the app prompts, passed as the `?api_key=` URL parameter, or sent as the `X-API-KEY` header. Tokens also work but expire every 12 hours.
- Client config: a JSON `mcpServers` entry with `"type": "http"`. Named clients are Claude, ChatGPT, Gemini, Claude Code, Cursor, and VS Code.
- Geometry input: WKT `POINT(lon lat)` or `POLYGON(...)`, usually EPSG:4326. Date ranges are supported.
- Capability categories:
  - Orthomosaic imagery, including graysky
  - Oriented imagery (oblique and nadir)
  - DSM/DTM in meters
  - Property and structure metadata (roof condition, footprints, pools, solar)
  - Damage assessment
  - Embeddings similarity search (by text, image, or location)
  - Custom elements (text, image, or embedding prompts)
  - Admin tools (health, usage, profile)
- Products may require separate entitlements. No rate limits are published.
- The tool reference is at api.vexcelgroup.com/v2/api-docs.

— [Get Started with Vexcel MCP](https://vexceldata.com/?p=28421)
- Example prompts from the MCP docs:
  - "Find properties with pools within 500 meters of POINT(-105.270 40.015)"
  - "Get the latest aerial photo for this location"
  - "Show me hurricane-damaged properties in Miami with severe roof damage"
  - "Find properties that visually resemble a commercial greenhouse facility"
  - a multi-step fire-risk ranking within 1 km of a point

  — [Get Started with Vexcel MCP](https://vexceldata.com/?p=28421)
- MCP launch (July 1, 2026): covers ortho, oblique, and multispectral imagery; DSM; property, building, and roadway attributes; Gray Sky damage; and embeddings and semantic search, plus spatial measurement tools. Example uses from the launch: find and measure cooling towers in a city and estimate their capacity; rank the top 25 properties in a ZIP code by roof condition; detect vegetation encroachment along transmission corridors; summarize last week's tornado damage. It is available to licensed customers — [Vexcel MCP press release](https://vexceldata.com/?p=28435)
- One secondary article names a `find_imagery` tool that filters by bbox, date range, and resolution. This was not confirmed by a primary source — [windowsnews.ai](https://windowsnews.ai/article/vexcel-opens-aerial-geospatial-data-to-chatgpt-claude-and-microsoft-copilot-via-new-mcp-connector.433371)

### Inferences
- The hackathon API access is probably an API key or sandbox credentials. With an API key, a team can attach the MCP server to Claude or Claude Code in minutes and build agents directly on the tool calls, without hand-writing REST clients.
- Oblique retrieval by direction is described as a capability: "oriented imagery" covering 4 cardinal directions. The exact v2 parameter names (e.g., orientation N/E/S/W) are not confirmed.

### Gaps
- The exact v2 REST endpoint paths, parameters, rate limits, and the MCP tool names and schemas are behind a login and could not be verified.
- No official Python SDK or open-source client was found.
- No XYZ tile URL template was confirmed; only WMTS and Esri Image Services are documented.

## 5. What can be measured from Vexcel data, and notable use cases

### Takeaway
Many of the measurements on the hackathon wish list exist as precomputed Elements fields:
- roof area, shape, material, and condition
- building height, stories, and volume
- solar panel count and area
- tree cover
- hardscape (a proxy for impervious surface)
- vehicle counts
- defensible space

Anything else can be detected with Custom Elements or measured on imagery and DSM. The core markets are insurance (underwriting and catastrophe response), plus government and assessment (CAMA), utilities, infrastructure, AEC, and mapping.

### Cited Findings
- The relevant measurable attributes are listed in Section 3; see the attribute tables there — [Elements: Property Attributes](https://vexceldata.com/products/elements/property-attributes/)
- The Viewer measures area and length, compares imagery across collections side by side, and shows more than 40 attributes per property — [Vexcel Platform](https://vexceldata.com/au/platform/)
- Insurance: underwriting can use roof condition, tree coverage, and defensible-space data to automate pricing — [Elements AI](https://vexceldata.com/au/products/elements). Catastrophe analytics on Gray Sky imagery produces property-level damage scores — [Elements: Damage Assessment](https://vexceldata.com/products/elements/damage-assessment/)
- CoStar's release lists use cases including insurance underwriting, catastrophe response, infrastructure planning, digital mapping, location intelligence, and AI applications — [SEC 8-K Ex. 99.2](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm)
- Utilities and infrastructure: vegetation encroachment along transmission corridors, cooling-tower capacity estimation, culvert finding, and electric and telephone pole detection — [Vexcel MCP press release](https://vexceldata.com/?p=28435); [Vexcel Intelligence](https://vexceldata.com/ai/); [Custom Elements launch](https://vexceldata.com/?p=29613)
- Property tax and assessment: the MapControl SDK is built for embedding in CAMA systems — [Vexcel Platform](https://vexceldata.com/au/platform/)
- Change detection: a story titled "Where Are the Areas of Rapid Change?" (Oct 28, 2026). Elements values are tied to timestamped imagery so changes can be tracked — [Vexcel Intelligence](https://vexceldata.com/ai/); [Elements: Property Attributes](https://vexceldata.com/products/elements/property-attributes/)

### Inferences (hackathon-relevant, not vendor claims)
- **Parking counts and occupancy:** use Elements vehicle counts per parcel, or Custom Elements for "parking space" and "car," across multiple capture dates. This yields a utilization time series for retail and office properties to set against CoStar vacancy and lease data.
- **Building height and GBA:** DSM minus DTM gives height. Combined with the footprint, this estimates floors and gross area, which can be checked against CoStar records and Matterport scans.
- **Solar potential:** roof facets, shape, and area, combined with DSM shading from tree cover and neighbors, produce a rooftop solar estimate. Existing panels are a detected attribute.
- **Impervious surface and tree canopy:** combine hardscape, footprint, and tree cover with the NIR/CIR band (NDVI-like vegetation index).
- **Construction progress and demolition:** compare footprints and DSM across dates. The LA fire rebuild is a natural demo.
- **Telecom:** oblique views of rooftop equipment such as satellite dishes and antennas, and DSM line-of-sight analysis. No Vexcel telecom-specific source was found.

### Gaps
- No Vexcel-published parking-count or impervious-surface product was found by name.
- No independent (non-vendor) accuracy validation of any measurement was found.
