# CoStar Group: Commercial Property Data, Developer Access, and HackPrinceton Fall 2026 Context

Research date: 2026-11-13 (first day of HackPrinceton Fall 2026). Many CoStar product pages (costar.com PDFs, glossary, property records page) returned HTTP 403 to automated fetch, so some field-level detail comes from search-result snippets of those pages rather than full reads. This is flagged where relevant.

## 1. What entities and fields does CoStar track for commercial properties?

### Takeaway
CoStar's core is a researcher-verified, property-centric database. Each property record links to spaces and availabilities, lease comps, sale comps (with buyer, seller, and financing), tenants, owners, and market/submarket analytics with forecasts. Lender-focused products add loan and CMBS risk data (COMPASS default model, Debt Solutions Benchmark). Public sources describe the fields by product, but I found no official export schema or data dictionary. The hackathon toolkit's exact schema is unknown until hackers see it.

### Cited Findings
**Scale and coverage**
- The US Property Records product advertises 8.5M property records. Users can filter them for vacancies, buildings for sale, and expiring leases. Leasing and sales details include ownership, sales history, for-sale status, available space, current tenants, and asking rents. — [CoStar Property Records (search snippet; page 403 on fetch)](https://www.costar.com/products/property-records)
- Count figures vary by date and source. One owner brochure lists 2.1M true owners and 4.3M sale comps, and a later owners page lists 5.6M sale comps. — [CoStar owners brochure](https://www.costar.com/sites/costar.com.na/files/costar-brochure---owners.pdf); [CoStar owners campaign](https://www.costar.com/campaign/owners)
- CoStar Tenant covers 6.7M tenant locations. In Q3 2026 CoStar announced an "AI-driven research process for CoStar Tenant" that it says will raise researcher productivity more than tenfold and update all 6.7M locations every year. — [Q3 2026 earnings call, Motley Fool](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)
- On the Q3 2026 call, CoStar said about 75% of its content is not visible to the broader internet, and it described enforcing its copyright against scrapers. — [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)
- CoStar Q3 2026 business metrics: CoStar product revenue $344M (+8%), 331,000 subscribers (+17%), 92% renewal rate, NPS 70. — [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)

**Property attribute fields (definitions from CoStar glossary and help material; the glossary page is older)**
- **RBA (Rentable Building Area):** square feet, covering usable area plus its share of common areas. Retail properties use **GLA** instead of RBA. — [CoStar Glossary (search snippet)](https://www.costar.com/resources/costar-glossary)
- **Typical Floor:** the floor size that occurs most often in the building, in square feet. — [CoStar Glossary](https://www.costar.com/resources/costar-glossary)
- **Parking Ratio:** spaces per 1,000 SF, calculated as spaces × 1,000 / RBA. — [CoStar Glossary](https://www.costar.com/resources/costar-glossary)
- **Building Class (A/B/C)** and **CoStar Star Rating (1–5 Star)** are separate fields. For example, a 2020 CoStar property page shows a "2 Star Office" with Class B. The star rating is CoStar's building quality rating, and it can be used as a search filter. — [CoStar property page PDF (2020)](https://images1.showcase.com/d2/VwFmB7aW02uQqm3femny8g6QX-3Xh7Q9BywHwzO44tY/document.pdf); [CoStar Building Rating System flipbook](https://fliphtml5.com/ffoh/kloj); [Introduction to Properties guide](https://www.costar.com/sites/costar.com.na/files/2023-02/introduction-to-properties.pdf)
- A third-party scraper template for CoStar property search lists exported columns including Parking Ratio, RBA/GLA, Class, and "Typ Fl (SF)". This is not an official schema. — [Bardeen template](https://www.bardeen.ai/templates/costar-properties-search)
- A CoStar "Property Report: Guide to Terms, Definitions and Calculations" exists as a PDF; I did not read it in full. — [Property Report guide](https://23372029.fs1.hubspotusercontent-na1.net/hubfs/23372029/Website%20Files/Property%20Report%20Tools%202-24-2022_rev%20(002)%20(1)-1.pdf)

**Lease comps**
- Fields include lease date, asking rent, rent achieved, time on market, expiration, lease starts and expirations, and incentives (UK product page; the US product is analogous). — [CoStar UK Lease Comps](https://costar.co.uk/products/lease-comps)

**Sale comps**
- Each record shows sale date, sale price, and time on market. It also has an "Assessment at Sale" section and a "Market at Sale" section. — [Introduction to Sale Comps (search snippet; PDF 403 on fetch)](https://costar.com/sites/costar.com.na/files/2023-02/introduction-to-sale-comps.pdf)

**Market analytics and forecasts**
- Subscribers get market and submarket analytics with KPI forecasts. The product list includes Market Analytics, Rent Benchmark, and Lease Analysis. — [CoStar owners brochure](https://www.costar.com/sites/costar.com.na/files/costar-brochure---owners.pdf)

**Debt and risk**
- **CoStar Risk Analytics:** uses the COMPASS credit default model, which CoStar describes as more than 17 years old (another page says 18). It combines INTEX CMBS bond data with CoStar property and market data, mapped to deals, loans, and collateral properties. It provides loan reports, cash flow forecasts, expected losses, and price/yield analysis. Lender uses are portfolio surveillance, concentration risk, CECL, CCAR/DFAST, custom stress testing, and a proposed-loan scorecard. — [CoStar Risk Analytics page](https://costar.com/ja-jp/node/1586); [CoStar for Lenders](https://costar.com/it-it/node/1436); [TN Bankers listing](https://tnbankers.org/?p=33392)
- **CoStar Debt Solutions Benchmark:** built on $1.5T of CRE debt across more than 155,000 loans. Loan origination capabilities are planned for 2027. — [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)

**Other data assets in the CoStar Group family**
- Apartments.com (multifamily): 91,155 paid properties, 48M average monthly unique visitors. Also LoopNet (listings), Ten-X (auctions), STR (hospitality benchmarks), CoStar Real Estate Manager and Visual Lease (lease administration), Zonda (homebuilding), Homes.com, Domain (Australia), OnTheMarket (UK), and Business Immo (France). — [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/); [Supergood API report card](https://supergood.ai/api-report-card/costar)

### Inferences
- The likely entity graph for a hackathon dataset: **Property** (location, type, RBA/GLA, class, star rating, year built, floors, typical floor, parking ratio, land area, zoning, amenities) → **Spaces/Availabilities** (floor, SF, asking rent, rent type, availability date) → **Lease comps** (tenant, SF, rent, term, lease type) → **Sale comps** (price, $/SF, cap rate, buyer, seller, lender) → **Contacts** (owner/true owner, property manager, leasing broker) → **Tenants** → **Market/Submarket** time series (vacancy, absorption, rent, forecasts). Fields such as year built/renovated, construction type, zoning, amenities, and property manager are standard CoStar property-page fields. I did not verify them against a primary source in this session, and the toolkit may include only a subset.
- The likely join key across CoStar, Matterport, and Vexcel is a CoStar property ID plus lat/long or building footprint. This is speculation.

### Gaps
- I could not fetch an official CoStar field list or data dictionary (costar.com PDFs returned 403). No official export schema is public.
- Which fields the HackPrinceton toolkit exposes (leases? sale comps? tenants? forecasts?) is unknown. Only "CoStar building data" is confirmed in the brief.

## 2. Does CoStar have a public or partner developer API, MCP server, or SDK? Any 2025–2026 news on CoStar APIs, MCP, agents, or hackathon toolkits?

### Takeaway
As of November 2026, CoStar's core data products (CoStar Suite, COMPS, Market Analytics, LoopNet) have no public API, developer portal, SDK, or official MCP server. Access is through portal login, and CoStar sues over automated access. The HackPrinceton toolkit (SDKs, MCP servers, OpenAPI services, per-team API keys) therefore appears to be a purpose-built, event-specific exposure that I could not find documented anywhere public. Matterport, a CoStar subsidiary, does have a real public developer platform (GraphQL Model API, Showcase/Embed SDK, webhooks), and Vexcel has its own APIs.

### Cited Findings
- An API report card dated November 2026 gives CoStar an "F." It finds no public API for CoStar Suite, COMPS, Market Analytics, or LoopNet; no OAuth or key issuance; no developer portal, docs, SDKs, or webhooks; and Terms of Use that prohibit automated extraction. It notes CoStar enforces with account suspensions and federal lawsuits. Real Estate Manager integrations are sold as professional-services connectors. It found no official or community CoStar MCP server (scorecard verified August 2026). — [Supergood API report card](https://supergood.ai/api-report-card/costar)
- Low-code integration guides say CoStar API access is enterprise-only through a formal approval process, with no self-serve keys. These are vendor-written and lower confidence. — [Rapid Developers, Retool + CoStar](https://www.rapidevelopers.com/retool-integrations/costar)
- The only "CoStar" MCP on public registries is a community Apify scraper of CoStar News (GB) pages. It is not a CoStar product. — [Apify Co-Star scraper MCP](https://apify.com/solutionssmart/co-star-real-estate-scraper/api/mcp)
- None of CoStar's Q3 2026 earnings remarks mention MCP, APIs, or developer offerings. — [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)
- **Matterport developer platform (real and public):**
  - GraphQL APIs. The **Model API** is available to all accounts, while the Account API and Import API (beta) are Enterprise-only. Credentials are a Token ID and Secret from Matterport Cloud. — [Matterport developer docs](https://matterport.github.io/developer-docs/api/)
  - Webhooks fire on model upload, processing, edit, and removal. — [Matterport developer docs](https://matterport.github.io/developer-docs/)
  - The SDKs are the Showcase **Embed SDK** (npm, controls the 3D viewer from a web app), the **Bundle SDK** (self-hosted Showcase with scene-graph and 3D-engine access), and a beta `@matterport/webcomponent`. — [Matterport developer docs](https://matterport.github.io/developer-docs/)
  - The Model API and Showcase SDK use different coordinate conventions, which the docs flag as a common gotcha. — [Matterport developer docs overview](https://matterport.github.io/developer-docs/overview/)
  - **Property Intelligence** is served through the Model API at `https://api.matterport.com/api/models/graph`. It provides `dimensionalEstimates`, `floors`, and `rooms` objects: detected room names, wall measurements, room and floor dimensions, square footage, and vector data for redrawing floorplans. It is Enterprise-only. — [Matterport Property Intelligence docs](https://developers.matterport.com/api/property-intelligence/)
  - The Model API also has GeoCoordinate API docs and a Postman collection. — [Matterport Property Intelligence docs](https://developers.matterport.com/api/property-intelligence/)
- Composio hosts a **third-party Matterport MCP server** that connects Claude, Cursor, OpenAI Agents SDK, and Vercel AI SDK to a Matterport account. — [Composio Matterport toolkit](https://composio.dev/toolkits/matterport)
- **Vexcel delivery:** imagery and data come via Vexcel APIs, Vexcel Viewer, Vexcel Image Services for ArcGIS, and select partners. — [Vexcel Elements: building attributes](https://vexceldata.com/products/elements/building-attributes/); [VDP overview brochure (2021)](https://vexceldata.com/wp-content/uploads/2021/11/VDP-Overview-Brochure-US_Digital_20211115.pdf)
- **HackPrinceton site:** CoStar Group is listed as a sponsor. The public homepage shows six general tracks (Education, Entertainment, Sustainability, Healthcare, Business + Enterprise, Science + Discovery) and "$15K+ in prizes." It does not describe the CoStar "Inside and Out" track, datasets, or toolkit. — [HackPrinceton Fall 2026](https://www.hackprinceton.com/)

### Inferences
- **Speculation about the toolkit:** It probably wraps (a) a CoStar property/building table for Houston and LA, (b) Matterport Model API/Property Intelligence data (rooms, dimensions, floors, sweeps) plus Embed SDK viewers for the same buildings, and (c) Vexcel imagery (ortho/oblique tiles, possibly elevation and building attributes) for those footprints. These would be exposed as OpenAPI REST services and MCP tools, with SDKs likely in Python and TypeScript. Hackers should confirm on site: the available tool names, rate limits, the cross-dataset join key, whether imagery comes as tiles or as derived attributes, and whether lease or sale comps are included.
- Because no public CoStar API exists, any project built on the toolkit is novel by default. Judges will likely value showcasing the joins (CoStar record ↔ Matterport interior ↔ Vexcel exterior), which matches the "30% use of data (combine 2+ layers)" criterion.
- Projects should avoid relying on scraping LoopNet or CoStar, because CoStar actively litigates against automated access.

### Gaps
- I found no public documentation, GitHub repo, or Devpost page for the HackPrinceton CoStar toolkit. Its contents are unverified.
- Vexcel's API endpoints and their access terms for the hackathon are unknown.

## 3. CoStar's AI initiatives 2024–2026; the Matterport and Vexcel acquisitions and their integration

### Takeaway
CoStar's AI push in 2026 is mostly consumer-facing. Homes AI launched February 2026 on Azure OpenAI, Apartments.com Ai launched June 2026, and an OpenAI ChatGPT partnership is live for apartments. On the commercial side it has an AI research pipeline for CoStar Tenant and AI document abstraction. CoStar closed the ~$1.6B Matterport deal on February 28, 2025, and on October 27, 2026 agreed to buy Vexcel for ~$730M (closing expected Q1 2027). It plans to use AI to extract hundreds of data fields per property from aerial imagery.

### Cited Findings
- **Homes AI** launched February 17, 2026 on Homes.com, powered by Microsoft Azure OpenAI. CoStar plans to extend it to Apartments.com, CoStar, LoopNet, Land.com, BizBuySell, and others. — [CoStar press release](https://investors.costargroup.com/news-releases/news-release-details/costar-group-launches-transformative-ai-experience-homescom); [RISMedia](https://www.rismedia.com/2026/02/17/costar-launches-ai-experience-refining-future-home-shopping/)
- **Apartments.com Ai** launched June 16, 2026. It is conversational search that replaces filters, building on the AI Smart Search added in January 2026. — [CoStar press release](https://www.costargroup.com/press-room/2026/costar-group-launches-apartmentscom-ai-redefining-future-apartment-search); [Let's Data Science](https://letsdatascience.com/news/costar-launches-apartmentscom-ai-conversational-search-38921227)
- Homes AI engagement: In Q1 2026, users ran about 4x the searches, favorited 7x the properties, and sent 7x the leads. In Q2 2026, users spent 17+ minutes on site, ran 3x the searches, and were 48% more likely to return within a week. — [Q1 2026 call](https://www.fool.com/earnings/call-transcripts/2026/04/28/costar-csgp-q1-2026-earnings-call-transcript/); [Q2 2026 transcript (roic.ai)](https://www.roic.ai/quote/CSGP/transcripts/2026-year/2-quarter)
- Q3 2026 call details: an OpenAI/ChatGPT partnership takes renters from a ChatGPT conversation to an Apartments.com transaction. CoStar is building direct connections with other LLMs, and LLM-sourced leads are "low single digit" percent. CoStar Tenant AI research process (see Q1). In head-to-head tests, a public-data-only AI agent had a 75% error rate versus CoStar's claimed single-digit rate. About 10M pages of Australian government filings were abstracted with AI. — [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)
- **Matterport:** the acquisition closed February 28, 2025, and Matterport delisted from Nasdaq. CoStar plans to put Matterport's AI, computer vision, and ML to work across its products and digital twins. — [CoStar press release](https://www.costargroup.com/press-room/2025/costar-group-completes-acquisition-matterport-ushering-new-era-3d-digital-twins-and); [RISMedia](https://www.rismedia.com/2025/03/03/costar-completes-acquisition-matterport-which-delists-from-nasdaq/); [CoStar 10-Q Q1 2025](https://www.sec.gov/Archives/edgar/data/1057352/000105735225000067/csgp-20250331.htm)
- Matterport Q3 2026 metrics: subscription revenue up 11% and about 70% of Matterport revenue. Pro3 shipments up 52%. More than 65M renter tour views (+99%). Listings with Matterport get 4x+ the leads and about 6x the tour or application requests. Expected to be profitable by end of 2027. — [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)
- **Vexcel deal terms:** announced October 27, 2026, about $730M cash, expected close Q1 2027. Vexcel keeps its own brand and CEO Erik Jorgensen. — [SEC 8-K Ex 99.2 press release](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm); [Bisnow](https://www.bisnow.com/news/national/technology/costar-to-acquire-aerial-imagery-company-for-730m)
- **Vexcel capabilities:** UltraCam cameras and its own aircraft. More than 60M images a year at 7.5–15 cm resolution, about 16x finer than typical satellite imagery. Coverage of 45+ countries, 320+ metros, and 99.6% of the US population. Major US metros refreshed up to 3x a year. Disaster zones flown within 24 hours. About half a billion properties captured. Revenue $140M+ LTM (+30%), about 20% EBITDA margin. — [SEC press release](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm); [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)
- **Vexcel product line:** Oblique, (True) Ortho at 7.5 cm with no building lean, 3D Cities, Elevate (DSM/DTM), Elements building attributes (footprint polygon, footprint area, ground elevation, roof elevation, roof height, roof condition), Gray Sky disaster imagery (hurricanes, tornadoes, wildfires), Multispectral, and On Demand. — [Vexcel Elements](https://vexceldata.com/products/elements/building-attributes/); [VDP brochure 2021](https://vexceldata.com/wp-content/uploads/2021/11/VDP-Overview-Brochure-US_Digital_20211115.pdf); [Vexcel Data Program](https://www.vexcel-imaging.com/vexcel-data-program/)
- **CoStar's plan for Vexcel imagery:** AI extracting "hundreds of data fields per property" (the press release says "tens of billions" in total; on the call Florance said up to 1,000 fields). The goal is to observe hundreds of millions of properties within 24 months, and CoStar product enhancements using aerials are a late-2027 initiative. — [SEC press release](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm); [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)

### Inferences
- The hackathon brief, which joins CoStar, Matterport, and Vexcel data for the same buildings, previews CoStar's stated 2027 strategy: AI-derived property fields from exterior aerial imagery plus interior 3D scans, reconciled with researcher-verified records. A team that prototypes "AI extracts property fields from imagery and scans, then flags discrepancies against CoStar records" is building exactly what CoStar says it wants.
- Because the Vexcel deal has not closed, the hackathon's Vexcel data is presumably provided under a license or partnership. This is unverified.

### Gaps
- I found no evidence of a generative-AI feature inside the CoStar Suite (commercial research platform) itself, beyond the Tenant AI research process and the stated plan to extend Homes AI.
- I did not find the "Abby" or other named CoStar AI agent products.

## 4. Houston and Los Angeles commercial real estate context (2025–2026)

### Takeaway
Both metros have office vacancy in the low-to-mid 20s percent. Houston is among the highest in the US, and its office reset is driving demolitions. Houston industrial is strong overall, but infill industrial vacancy is at a 20-year high. LA adopted a Citywide Adaptive Reuse Ordinance in February 2026. LA is also rebuilding slowly and unevenly after the January 2025 Palisades and Eaton fires, which CoStar estimated damaged or destroyed 374 commercial buildings worth nearly $2B.

### Cited Findings
**Houston**
- Office vacancy figures vary by broker methodology:
  - 25.6% in Q3 2026 (Newmark), flat quarter over quarter and +30 bps year over year. — [CRE Daily](https://www.credaily.com/?p=224274)
  - 23.8% in Q2 2026 (CBRE). — [CBRE Houston Office Figures Q2](https://mktgdocs.cbre.com/2299/7a74b565-130e-4abe-9d06-85a9dde85590-24103824/CBRE_Houston_Office_Figures_Q2.pdf)
  - 19.4% in Q3 2026 (Lee & Associates). — [Lee & Associates Q3 2026](https://www.lee-associates.com/wp-content/uploads/2026/10/2026-Q3-Houston-TX-Office.pdf)
  - 26.8% in Q1 2026 (JLL). — [CRE Daily search snippet](https://www.credaily.com/?p=224274)
- Houston drew $1.5B of office investment despite 24.1% vacancy, and its office reset is fueling a demolition boom. — [CRE Daily](https://www.credaily.com/?p=223210); [CRE Daily](https://www.credaily.com/?p=219743)
- Industrial posted 7.5M SF of net absorption in Q3 2026 (Savills), and CBRE puts industrial availability at 8.7%. — [Savills](https://www.savills.us/research_articles/229130/395116-0); [CBRE Houston 2026](https://mktgdocs.cbre.com/2299/a886fa81-a8a1-4f5b-b4d8-1f9b72cbd2c4-1992300835/Houston_2026_U.S._Real_Estate_.pdf)
- CoStar News reports Houston infill industrial vacancy at a 20-year high while investors keep buying, and rising vacancy in the I-45 and Highway 249 corridors. — [CoStar News](https://www.costar.com/article/719348529/houston-infill-industrial-market-faces-highest-vacancy-in-20-years-but-investors-keep-buying); [CoStar News](https://www.costar.com/article/518291270/industrial-vacancy-rises-in-houstons-i-45-and-highway-249-corridors-but-capital-keeps-flowing)

**Los Angeles**
- Office vacancy was 23.4% in Q2 2026 (Cushman & Wakefield) and 25.1% at the end of 2025 (CBRE). — [Commercial Observer](https://commercialobserver.com/2026/05/california-office-vacancy-housing-conversion-policy/)
- The **Citywide Adaptive Reuse Ordinance** took effect in February 2026. It provides incentives and streamlining for converting commercial buildings to 5+ residential units, extending the 1999 ordinance (which yielded 12,000+ units) to previously excluded areas. — [Greenberg Glusker](https://www.greenbergglusker.com/publications/citywide-adaptive-reuse-a-potential-solution-to-vacancy-and-housing); [LA Business Journal](https://labusinessjournal.com/featured/adaptive-reuse-to-surge/)
- Conversion feasibility in LA is constrained by cost, seismic requirements, entitlements, and deep floorplates. — [Carrier Johnson](https://carrierjohnson.com/from-vacancy-to-value-what-it-takes-to-make-office-conversions-work-on-the-west-coast/); [Parriva](https://www.parriva.com/los-angeles-office-vacancy-housing-shortage/)
- Nationally, 2025 was the first year that office conversions and demolitions outpaced new office deliveries (CBRE). — [Commercial Observer](https://commercialobserver.com/2026/05/california-office-vacancy-housing-conversion-policy/)
- **January 2025 fires:**
  - CoStar counted 374 commercial buildings damaged or destroyed, worth nearly $2B. Separately, 786 commercial properties were affected by the Palisades fire and 704 by the Eaton fire. — [Commercial Observer](https://commercialobserver.com/2025/01/la-fires-commercial-properties-2b/)
  - Palisades Village reopened in August 2026 after a $100M restoration. — [Insurance Journal](https://www.insurancejournal.com/news/west/2026/08/19/881591.htm)
  - By November 2025, less than 0.1% of homes were rebuilt. — [McKinsey](https://www.mckinsey.com/industries/real-estate/our-insights/how-los-angeles-can-accelerate-recovery-after-the-2025-wildfires)
  - Commercial Observer's one-year review described rebuilding as "arduous, costly and uneven." — [Commercial Observer](https://commercialobserver.com/2026/01/la-fires-rebuilding-one-year/)

### Inferences
- Several high-signal hackathon angles follow from this:
  - Adaptive-reuse screening for LA offices. Combine CoStar floor plates, year built, class, and vacancy with Matterport floor and room dimensions and window depth, plus Vexcel roof and footprint data.
  - Houston flood and roof-risk underwriting, using Vexcel elevation (DSM/DTM) and roof condition plus CoStar property and loan data.
  - Post-fire change detection and rebuild tracking in LA. Vexcel Gray Sky is a disaster-imagery product, but its availability in the toolkit is unverified.
  - Demolition and obsolescence candidate scoring for Houston office.

### Gaps
- I found no 2025–2026 source on Houston flood-risk effects on CRE (insurance, valuations). Background knowledge (Hurricane Harvey 2017, Hurricane Beryl in July 2024) is unsourced here.
- I found no late-2026 statistics on the LA commercial rebuild.

## 5. Customer pain points that data + AI could solve

### Takeaway
CoStar's own disclosures point to pain points around data freshness and verification (researcher-heavy tenant and property updates), unstructured document abstraction, lender surveillance and stress testing, and the high error rate of AI agents that use only public data. Direct customer-voice sources were not gathered.

### Cited Findings
- CoStar says manual tenant research is a bottleneck. Its new AI process aims for a 10x+ productivity gain and annual updates of 6.7M tenant locations, and public-data-only AI agents had a 75% error rate. — [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)
- AI abstraction of about 10M pages of government filings (Australia) shows document-to-structured-data extraction is a priority. — [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)
- Lenders need portfolio surveillance, concentration risk analysis, CECL, CCAR/DFAST, stress testing, and proposed-loan scorecards. — [CoStar for Lenders](https://costar.com/it-it/node/1436)
- 34% of CMBS loans failed to pay off at maturity between 2020 and early 2025 (Trepp), with office the worst. — [CRE Daily](https://www.credaily.com/?p=209312)
- Matterport tours lift leads 4x+ and tour or application requests about 6x on rentals, which shows the value of interior 3D data for marketing and leasing. — [Q3 2026 call](https://www.fool.com/earnings/call-transcripts/2026/10/28/costar-csgp-q3-2026-earnings-call-transcript/)
- CoStar's stated thesis is that direct observation and capture of on-the-ground facts is its differentiator. — [SEC Vexcel press release](https://www.sec.gov/Archives/edgar/data/0001057352/000105735226000078/exhibit992-vexcelpressre.htm)

### Inferences
These are opportunities derived from the findings above, not sourced customer quotes.
- **Brokers:** auto-generated offering memoranda and listing descriptions that blend CoStar facts, Matterport room data, and aerial context; and agentic tenant-rep searches ("find 20k SF Class A with parking ≥3/1,000 near transit, then compare floor plates").
- **Appraisers and lenders:** automated property verification that checks RBA against Matterport square footage and the Vexcel footprint, flags discrepancies, and inspects roof condition. A CoStar Risk Analytics-style loan stress agent fits here too.
- **Investors and developers:** adaptive-reuse and redevelopment screening, and climate exposure from elevation and flood data.
- **Property managers:** capex planning from roof condition and interior scans, and space-planning agents.

### Gaps
- I gathered no direct survey or interview evidence of CoStar customer pain points.

## 6. Past HackPrinceton or other hackathon CoStar track winners and project examples

### Takeaway
I found no record of any prior CoStar-sponsored hackathon track, winners, or Devpost gallery. Fall 2026 appears to be a first, or at least a first public instance.

### Cited Findings
- Searches for CoStar hackathon, Devpost, and Matterport track projects returned only CoStar business news. — [RISMedia](https://www.rismedia.com/2024/04/22/costar-drops-1-billion-acquire-3d-camera-pioneer-matterport); see search notes above
- The HackPrinceton homepage lists CoStar as a sponsor but has no track page. — [HackPrinceton](https://www.hackprinceton.com/)
- A prior HackPrinceton winner, MindPad (an AI workspace, Best Overall), is unrelated to CoStar. — [Illinois CS news](https://siebelschool.illinois.edu/news/golcha-hackprinceton)

### Inferences
- With no precedent, judges have no "already seen it" baseline. Projects that use all three layers (CoStar, Matterport, Vexcel) through MCP tool calls inside a multi-step agent loop are the most direct match to the 30% data-combination and 30% agentic-depth criteria.

### Gaps
- Past HackPrinceton Devpost galleries were not reviewed for real-estate or proptech projects.
