# Unexplored Project Opportunities (CoStar data + Matterport + Vexcel + AI agents) and How TypeSafe's Jev Fits

Scope note: Research done on 2026-11-13 (HackPrinceton Fall 2026 starts today). Jev facts come mainly from TypeSafe's own docs (docs.typesafe.ai, fetched as raw .md). Third-party Jev coverage is mostly vendor-adjacent. CRE market facts come from broker reports and trade press, which often disagree with each other. Where they conflict, both figures are listed.

---

## 1. What is Jev (TypeSafe AI), and what are its API, pricing, latency, limits, availability and demos?

### Takeaway
Jev is a non-generative "System One" model. You send it a `state` (text, JSON and/or PNG/JPEG images) plus many typed questions, and it returns calibrated typed answers in one parallel call: Choice, Score, Noul (a yes/no probability) and Box (a bounding box in an image). It is cheap: $0.042 per million input tokens, and output is free. It is fast: 70–500 ms, a vendor figure. It is strong at quick judgments and weak at counting, math, dates, multi-hop reasoning and text generation. Image and Box support is labelled "Dreamer-ready" (prototype-grade) and must be switched on with a header. That makes Jev the fast perception and triage layer inside an agent, with an LLM doing the planning and talking.

### Cited Findings
**What it is**
- Jev is "TypeSafe's flagship model and the first System One model". It "evaluates typed questions against a state and returns structured results, so your code can use the output directly without parsing generated text." — [docs.typesafe.ai](https://docs.typesafe.ai)
- The primitives are:
  - Choice returns `choice`, `probabilities` and `confidence`.
  - Score returns `score`, `probabilities` and `confidence`.
  - Noul returns `noul` (0–1).
  - Box returns `box` (top/bottom/left/right as fractions of the image) and `confidence`.
  — [Quickstart](https://docs.typesafe.ai/introduction/quickstart.md)
- Question types can be mixed in one request. "All questions run in parallel against the same state, and adding questions barely changes response time." Each question is evaluated in isolation, so there is no context rot. — [docs.typesafe.ai](https://docs.typesafe.ai)
- Jev "does not generate text, write code, or hold a conversation". It is not a drop-in LLM for coding agents. Use it "inside an agent or app you're building" for routing, rubric scoring, checking whether a statement is true before an action, and replacing fragile "return JSON" prompts. — [Jev with coding agents](https://docs.typesafe.ai/introduction/coding-agents.md)
- Jev is trained with "RLCD" to return calibrated decisions. It is not fine-tuned per customer; you customize it through state, instructions and criteria. — [Models](https://docs.typesafe.ai/models.md)

**API and SDKs**
- Every model is served by one endpoint, `POST /v1/systemone` (base `https://api.typesafe.ai`). The `model` field selects the model. — [Models](https://docs.typesafe.ai/models.md)
- Python SDK:
  - Install: `pip install typesafe-sdk` (Python 3.10+).
  - Import: `from typesafe_sdk import Choice, Noul, Score, TypeSafeClient`.
  - Call: `client.system_one(state=..., questions={...})`.
  - Answers: `response.choices[...]`, `response.scores[...]`, `response.nouls[...]`.
  — [Quickstart](https://docs.typesafe.ai/introduction/quickstart.md)
- JS/TS SDK:
  - Install: `npm install @typesafe-ai/sdk` (Node 20+).
  - Import: `import { choice, noul, score, TypeSafeClient }`.
  - Call: `client.systemOne({state, questions})`.
  - Answers: `response.answers.<name>`.
  — [Quickstart](https://docs.typesafe.ai/introduction/quickstart.md)
- The API key comes from console.typesafe.ai/keys, set as env var `TYPESAFE_API_KEY`. A browser Playground is available at console.typesafe.ai/playground. — [Quickstart](https://docs.typesafe.ai/introduction/quickstart.md); [Coding agents page](https://docs.typesafe.ai/introduction/coding-agents.md)
- There is an agent skill for Claude Code. Install with `claude plugin marketplace add typesafe-ai/skills` then `claude plugin install typesafe@typesafe-ai`. For other agents, use `npx skills add typesafe-ai/skills --skill typesafe-ai`. — [Quickstart](https://docs.typesafe.ai/introduction/quickstart.md)
- An OpenAPI spec is at https://api.typesafe.ai/openapi.json. A full docs index for coding agents is at https://docs.typesafe.ai/llms.txt. — [llms.txt](https://docs.typesafe.ai/llms.txt)

**Models, pricing and limits**
- Current models are Jev 1.14 (`jev-1.14.0`, released Oct 14, 2026) and Jev 1.13. The aliases `jev-latest` and `jev-preview` both point to 1.14. Box questions need 1.14. — [Models](https://docs.typesafe.ai/models.md); [Changelog](https://docs.typesafe.ai/changelog.md)
- **Price: $42 per billion input tokens ($0.042 per million). Output tokens are free.** — [Models](https://docs.typesafe.ai/models.md)
- Context limits:
  - Default: 64k tokens per request and 32k per question.
  - Header `TypeSafe-Danger-Zone-Long-Context: true` raises both to 262k, at the same price but slower and less accurate.
  - There is no cap on the number of questions.
  — [Models](https://docs.typesafe.ai/models.md)
- Rate limits are set per organization and visible in the console, measured in tokens/sec and requests/sec. A 429 or 529 means retry; the SDKs back off automatically. — [Models](https://docs.typesafe.ai/models.md); [Errors](https://docs.typesafe.ai/api/errors.md)
- The request body can be at most 32 MiB, with at most 64 nesting levels and finite numbers only. gzip and zstd compression are supported. — [Errors](https://docs.typesafe.ai/api/errors.md)

**Images and Box ("Dreamer-ready", not production)**
- Image support has to be switched on:
  - Send header `TypeSafe-Danger-Zone-Images: true`.
  - Images can go in `state`, in `instructions`, **and as `criteria`**, for example a reference photo as a Choice option.
  - Multipart upload is preferred over base64.
  — [Images](https://docs.typesafe.ai/images.md)
- Image limits:
  - PNG or JPEG only, still images.
  - Each side must be 280–1568 px; images outside this range are rejected, not resized.
  - At most 16 MiB per file and 32 MiB for all images in a request.
  - If one image is rejected, the whole request fails.
  - The API strips EXIF, so rotate the pixels upright before sending.
  — [Images](https://docs.typesafe.ai/images.md)
- Box rules:
  - "One box per question". To find several targets, ask several Box questions.
  - Small targets in large images can be missed. Recommended: tile the image, use a Choice over the tiles, then Box on the chosen tile.
  - No recommended confidence threshold yet.
  — [Box](https://docs.typesafe.ai/primitives/box.md); [Images](https://docs.typesafe.ai/images.md)

**Known weaknesses ("jaggedness")**
- Jev:
  - reads instructions literally;
  - "does not count reliably";
  - is "not a calculator";
  - compares dates unreliably;
  - struggles with indirection and multi-hop reasoning;
  - loses accuracy when the state is large and full of irrelevant detail;
  - can be steered by adversarial content;
  - shows a Choice option-order bias toward the first option;
  - is "not trained to generate text".
- Recommended workarounds: do arithmetic and counting in code, with one Noul per candidate. — [Model jaggedness](https://docs.typesafe.ai/model-jaggedness.md)

**Latency, launch and availability**
- Latency is "70 to 500 ms", a vendor-stated figure that was not independently reproduced. — summarized from [nexos.ai guide](https://nexos.ai/blog/what-is-jev/), [The New Stack](https://thenewstack.io/typesafe-jev-system-one/) (403 on fetch; snippet only)
- Launch facts: Jev launched Sept 15, 2026. TypeSafe has "$40 million in funding". Founder Diogo Almeida previously worked at OpenAI. — [VKTR](https://www.vktr.com/ai-platforms/chatgpt-cocreator-launches-typesafe-ai-with-jev/); [LetsDataScience](https://letsdatascience.com/news/typesafe-ai-launches-jev-decision-model-889a38c0)
- Access is described as "closed, hosted, and waitlisted", with no open weights. This conflicts with the docs, which describe self-serve keys from the console. I could not resolve whether a waitlist still applies. — search summary of secondary sources; [Quickstart](https://docs.typesafe.ai/introduction/quickstart.md)
- Gateways:
  - Vercel AI Gateway: Vercel says Jev reached more than twice as many paid teams within 24 hours of launch as any previous model launch. TechCrunch: "Jev is Vercel's fastest adopted AI model ever" (Oct 16, 2026). — [TechCrunch](https://techcrunch.com/2026/10/16/jev-is-vercels-fastest-adopted-ai-model-ever/)
  - OpenRouter: available per a secondary guide. — [freeapihub / respan summaries via search](https://www.respan.ai/articles/what-is-the-jev-ai-model)
  - Other gateways: LLMGateway lists `jev`, `jev-1.13.0` and `jev-1.14.0` uptime pages. ZenMux lists `typesafe/jev-1.13`. — [LLMGateway](https://llmgateway.io/models/jev-1.14.0/uptime); [ZenMux](https://zenmux.ai/typesafe/jev-1.13)
- Benchmarks are self-reported, which TypeSafe acknowledges. — search summary of [LetsDataScience](https://letsdatascience.com/news/typesafe-ai-launches-jev-decision-model-889a38c0)

**Demos, cookbooks and use-case map relevant to this hackathon**
- Content audit: "all 279 pages of the Django docs on 45 questions each in about 4 seconds" for about $0.10. — [Demos](https://docs.typesafe.ai/demos.md); [llms.txt](https://docs.typesafe.ai/llms.txt)
- Airbnb search: the 10 best of 1,000 Cape Town listings "in about a second" from a Google Sheets formula, using 11 requests instead of 1,000. Choice shortlists, then Score ranks. This is a direct analog for ranking CoStar buildings. — [Demos](https://docs.typesafe.ai/demos.md)
- Image cookbooks:
  - Feeder-cam visit log: frames → 5 questions including a Box → per-species log in code.
  - Scanned vaccination record: Noul plus Box plus Choice-with-"unreadable".
  - OCR bounding-box verification.
  — [llms.txt](https://docs.typesafe.ai/llms.txt)
- Patterns that suit agents:
  - Speculative fan-out: ask every question you might need in one call.
  - Noul screen first: a yes/no gate before expensive steps.
  - Companion Noul: "does any option fit?".
  - Confidence routing and probability routing: riskier actions need higher thresholds.
  - Composite scoring: atomic scores weighted in code.
  - SDE cascade: a cheap model extracts, Jev checks each field, and only failures escalate to a reasoning model.
  — [llms.txt](https://docs.typesafe.ai/llms.txt); [Use case map](https://docs.typesafe.ai/concepts/use-case-map.md)
- Parallel questions: batching 13 questions into one call was "12.2x cheaper and 11.8x faster with no change in answers". — [llms.txt](https://docs.typesafe.ai/llms.txt)

### Inferences
- **The core architecture is "LLM plans, Jev perceives and judges, code acts".**
  - An LLM agent (Claude or similar) decomposes the goal and calls tools.
  - Jev runs fast, typed, calibrated judgments over many Matterport frames, Vexcel oblique crops and CoStar records.
  - Code does all arithmetic: counts, areas, $/SF, dates.
  - Low-confidence answers escalate to the LLM or to a human.
  - This fits Jev's documented strengths and avoids its weaknesses.
- **Cost is negligible at hackathon scale.** Tokens per image are not documented (see Gaps), but even a few thousand tokens per image × thousands of images costs cents.
- **Two image features suit this data especially well:**
  - Image-as-criteria: "which of these reference photos does this frame most resemble?"
  - Tile-then-Box search: locate a hydrant connection, transformer or tuck-under parking in a large Vexcel oblique.
- **Expect wrong answers and design for them.** Box is "Dreamer-ready", so the demo must use confidence-based fallbacks. Never ask Jev to count cars or measure feet; ask one Noul per parking stall tile and sum in code.
- **The pitch line for judges:** "Jev lets the agent look at 10,000 images in the time an LLM looks at 10."

### Gaps
- How many tokens an image consumes, which drives cost and fit within 64k: not documented on the pages fetched.
- Per-organization default rate limits: only visible in the console.
- Independent latency measurements: none found.
- Whether HackPrinceton participants get free or sponsored TypeSafe credits: not found.
- Whether OpenRouter carries Jev 1.14 with image and Box support or only 1.13 text: not confirmed. Gateways may not pass the `TypeSafe-Danger-Zone-*` headers, so use the direct API for images.

---

## 2. What real built-environment and CRE problems does Houston have in 2024–2026?

### Takeaway
Houston's office market is deeply distressed, with roughly 24–28% vacancy depending on source and some submarkets above 44%. Industrial is booming, with record absorption, data-center-adjacent logistics and Port-driven demand. The city also carries some of the highest insurance costs in the US, real flood exposure, and repeat wind and tornado events (Beryl 2024; December 2024 EF2 tornadoes). These are three distinct problem spaces: "split" office, booming industrial, and climate and insurance risk.

### Cited Findings
**Office vacancy (sources disagree)**
- CBRE Q3 2026: 23.9% vacancy (CBD 25.5%, Katy Freeway 10.4%), Q3 net absorption −30,000 SF. Newmark: 25.6%. Colliers' Q3 headline: 27.6%. Yardi Matrix July 2026: 24.1%, up 330 bp year over year. — [TenantBase Q3 2026](https://www.tenantbase.com/houston/q3-2026/); [Newmark](https://www.nmrk.com/insights/market-report/houston-market-reports); [CRE Daily](https://www.credaily.com/briefs/houston-office-market-draws-1-5b-despite-24-1-vacancy/)
- CBD 32.8% vacancy with (264,988) SF of year-to-date absorption. FM 1960 and North Belt above 44% vacancy. The narrative is "Houston Office Isn't Recovering. It's Splitting in Two." — [theBrokerList](https://blog.thebrokerlist.com/houston-office-isnt-recovering-its-splitting-in-two/); [Partners Q1 2026](https://partnersrealestate.com/research/houston-office-q1-2026-quarterly-market-report/)
- The office market still drew $1.5B of investment despite 24.1% vacancy. — [CRE Daily](https://www.credaily.com/briefs/houston-office-market-draws-1-5b-despite-24-1-vacancy/)

**Industrial and logistics (sources disagree)**
- Q3 2026 vacancy:
  - about 6.3% (Cushman & Wakefield, CBRE);
  - 5.2% direct (Lee & Associates);
  - 7.5% (Houston.org).
  — [Cushman](https://www.cushmanwakefield.com/en/united-states/insights/us-marketbeats/houston-marketbeats/industrial); [Lee](https://www.lee-associates.com/houston/2026/10/01/houston-industrial-distribution-market-report-q3-2026/); [Houston.org](https://houston.org/houston-data/quarterly-update-industrial-market/)
- Q3 2026 absorption:
  - 7.2M SF (CBRE);
  - 7.5M SF (Savills);
  - a record 10.0M SF (Lee).
- Leasing: 14.6M SF (Cushman).
- Rents: record $8.16/SF asking (Cushman). — [CBRE](https://www.cbre.com/insights/figures/houston-industrial-figures-q3-2026); [Lee](https://www.lee-associates.com/houston/2026/10/01/houston-industrial-distribution-market-report-q3-2026/)
- Houston ranks second nationally for logistics occupancy tied to data-center-related industries. Demand is concentrated around the Port of Houston, manufacturing, and AI-infrastructure-adjacent space. — [CoStar article](https://www.costar.com/article/1290934298/houstons-emergence-as-data-center-growth-market-generates-new-demand-for-industrial-real-estate); [Cresa Q2 2026](https://www.cresa.com/-/media/Cresa/Files/PDF-Market-Reports/Houston/2026/HOU-Q2-2026-Industrial-Market-Report.pdf)

**Climate, insurance and disasters**
- Houston has "some of the highest property insurance costs in the country", plus significant property taxes and "real flood exposure" that "can quietly sink a pro forma". — [rodkhleif.com submarket analysis](https://rodkhleif.com/sub-market-analysis-houston-texas/) (investor blog, low authority)
- Hurricane Beryl (July 2024) made landfall near Matagorda as a Category 1, with winds up to 80 mph, and caused massive power outages in Houston. — [NOAA NESDIS](https://nesdis.noaa.gov/news/hurricane-beryl-brings-massive-power-outages-east-texas); [Nearmap Beryl](https://nearmap.com/white-papers/hurricane-beryl-government)
- Nearmap captured and published Beryl imagery within 36 hours of landfall. — [Nearmap](https://nearmap.com/white-papers/hurricane-beryl-government)
- Vexcel's Gray Sky program has covered Houston-area events:
  - EF2 tornadoes on Dec 28, 2024, imaged as oblique, ortho and multispectral at 7.5 cm;
  - a tornado outside Houston, imagery published Nov 26, 2025.
  — [Vexcel Gray Sky Houston tornadoes](https://vexceldata.com/gray-sky-event-tornado-hits-metro-areas-in-houston-texas); [Vexcel stories](https://vexceldata.com/stories/2025/11)

### Inferences
- **"Splitting in two" plus 44% submarkets is an opening for a building-level distress early warning.** Which leased-but-dark buildings will tip next? Aerial parking fill and interior scans can expose "shadow vacancy" that CoStar lease records alone cannot.
- **Flood and wind are underwritten at the roof (Cape and Betterview), not at the ground floor.** In Houston, the ground floor and mechanical rooms are where flood losses and business interruption come from. That is an open angle:
  - first-floor height, where electrical and mechanical equipment sits, and loading-dock elevation;
  - combined with the CoStar tenant roster to estimate who goes dark.
- **The industrial boom suggests a project around "which warehouses can host data-center-adjacent or cold-chain uses".** Signals: clear height and power from the interior scan, yard and trailer parking from aerial, lease expiry from CoStar.

### Gaps
- No source quantified Beryl's specific effect on commercial values or on post-Beryl insurance renewals for CRE.
- I did not research Houston's extreme heat or petrochemical-adjacent risk in this session.
- No Harris County flood-buyout or first-floor-elevation dataset was located.

---

## 3. What real built-environment and CRE problems does Los Angeles have in 2024–2026?

### Takeaway
LA has a stack of active, building-level policy pressures:
- the citywide Adaptive Reuse Ordinance (effective about Feb 2026), set against more than 50M SF of vacant office;
- seismic retrofit mandates (about 13,500 soft-story and about 1,400–1,500 non-ductile concrete buildings);
- Measure ULA, a transfer tax that cut sales of large commercial and multifamily properties by about 30–50% per some studies, and is still in effect;
- the January 2025 Palisades and Eaton fire rebuild and the commercial insurance squeeze;
- AB 2097 parking reform (27 sq mi of surface lots);
- heavy ADA litigation;
- a collapsing on-location film industry (shoot days down 16.1% in 2025).

### Cited Findings
**Adaptive reuse**
- The citywide Adaptive Reuse Ordinance removed the earlier limits to downtown, Chinatown, Hollywood and Koreatown. It took effect around Feb 1, 2026.
- Buildings 15 or more years old are eligible by right, and some parking structures at 5 years. That 5-year figure needs verification.
- LADBS issued Information Bulletin IB-BC-2026-164, effective Sept 14, 2026, for office-to-residential conversions.
- Historic districts and hotels still need discretionary review.
  — [BOMA on the Frontline](https://www.bomaonthefrontline.com/2026/01/02/la-expands-adaptive-reuse-ordinance-beyond-high-density-hubs/); [Propmodo](https://propmodo.com/playbook/los-angeles-unlocks-citywide-office-to-housing-conversions-with-sweeping-adaptive-reuse-reform/); [ArchDaily](https://www.archdaily.com/1028693/los-angeles-approves-adaptive-reuse-ordinance-to-tackle-housing-shortage)
- More than 50M SF of LA office is vacant (LA Times, via secondary source).
- Pipeline figures, both traced to one LA Times report and unverified:
  - 5,640 adaptive-reuse units in progress citywide;
  - about 2,843 of those from office-to-residential.
- RentCafe projects about 4,400 conversion units. — [The Pride LA](https://thepridela.com/2026/02/new-law-aims-to-unlock-50-million-square-feet-of-empty-office-space/); [Kenny Stevens blog](https://kennystevensteam.com/blog/los-angeles-adaptive-reuse-ordinance)

**Seismic retrofits**
- The soft-story program covers about 13,500 buildings. The final compliance deadline was around April 2026; sources contradict each other on which priority tier was due when.
- The non-ductile concrete program covers about 1,400–1,500 buildings on a multi-step timeline (checklist, then plans, then completion over up to 25 years). Sources conflict on the timeline and ordinance numbers.
- An LA Times map showed about 6,000 structures needing retrofit.
  — [Bisnow](https://www.bisnow.com/news/los-angeles/multifamily/what-las-new-seismic-retrofit-law-means-for-building-owners-51989); [SEAOSC FAQ](https://www.seaosc.org/la-retrofit-faq); [Archinect / LA Times map](https://archinect.com/news/article/150408920/a-new-la-times-map-shows-6-000-structures-in-need-of-seismic-retrofit-across-los-angeles)

**Measure ULA**
- A 2025 study found a 30–50% drop in transactions across commercial, industrial and multifamily properties. CoStar reported LA commercial sales fell by up to 50% while nearby cities without ULA were steadier. A RAND report found ULA reduced apartment construction. — [CoStar](https://www.costar.com/article/325930750/los-angeles-mansion-tax-faces-dual-rollback-efforts); [CRE Daily](https://www.credaily.com/briefs/measure-ula-surpasses-1b-in-revenue/)
- ULA had raised $1.03B by Nov 2025, mostly from commercial transactions rather than luxury homes. — [Bisnow](https://www.bisnow.com/news/los-angeles/multifamily/measure-ula-1-billion-revenue-132634)
- Status:
  - The City Council ditched its ULA ballot measure in July 2026.
  - BOMA says ULA "remains fully in effect".
  - One guide claims a statewide repeal is on the November 2026 ballot; this conflicts with other reports.
  — [The Real Deal](https://therealdeal.com/la/2026/07/06/la-city-council-ditches-mansion-tax-ballot-measure/); [reedcorp.tax](https://reedcorp.tax/helpful-guides/california/california-measure-ula-repeal-ballot-may-2026/)

**January 2025 wildfires**
- Permits: LADBS approved more than 3,090 building and electrical permits out of more than 6,600 applications across the burn areas as of early 2026. Another source counts 928 single-family Palisades rebuild permits through May 2026. — [The Real Deal](https://therealdeal.com/magazine/january-2026/after-the-la-fires/); [Benson Construction](https://www.bensonconstructiongroup.com/fire-rebuild-los-angeles)
- FAIR Plan, commercial side:
  - The commercial cap was about $8.4M per location before July 2025.
  - A Commercial High Value pilot runs through July 2028.
  - A 29.1% average dwelling rate increase took effect Oct 15, 2026.
  - The one-year non-renewal moratorium for fire areas expired Jan 7, 2026.
  — [latentinsure (vendor)](https://www.latentinsure.com/california-fair-plan); [Schneiderman Insurance](https://schneidermaninsurance.com/rebuilding-in-the-pacific-palisades-the-insurance-side/)

**Parking reform (AB 2097)**
- AB 2097 ends parking minimums for housing within half a mile of major transit. It has not been repealed, so the premise in the brief was wrong.
- LA has 27 sq mi of land devoted to surface parking (Woods Bagot, 2018).
- AB 2712 (2024) bars residential parking permits for AB 2097-exempt projects.
- In June 2025, a council motion (Blumenfield and Raman) asked Planning to study removing parking mandates citywide.
  — [Long Beach Post](https://lbpost.com/news/californias-newest-housing-law-will-eliminate-parking-mandates-near-transit); [Abundant Housing LA](https://abundanthousingla.org/ab2097/); [Urban Land](https://urbanland.uli.org/economy-markets-trends/california-relaxes-parking-mandates-to-free-up-multifamily-development-but-will-neighbors-and-lenders-approve?p=39)

**ADA litigation**
- 8,667 federal ADA Title III suits were filed in 2025. California led with 3,252 federal filings; this figure is suspicious because it matches 2024 exactly.
- About 22,000 California state-court Unruh Act filings were made in 2022–2025 (editorial estimate).
- The California Commission on Disability Access (CCDA) publishes semiannual "Top Ten Alleged Construction-Related Violations" lists, through Jan–Jun 2026.
  — [JD Supra / Seyfarth](https://www.jdsupra.com/legalnews/ada-title-iii-federal-lawsuit-filings-2632226/); [Disability World](https://www.disabilityworld.org/articles/ada-filings-move-to-state-court-post-acheson/); [CCDA Top Ten Jan–Jun 2026](https://www.dgs.ca.gov/CCDA/Resources/Page-Content/California-Commission-on-Disability-Access-Resources-List-Folder/Top-Ten-Alleged-Construction-Related-Disability-Access-Violations--January-through-June-2026)

**Film production**
- 2025 on-location shoot days: 19,694, down 16.1% from 23,480 in 2024.
- Q1 2026: 5,121 days, down 3.3% year over year.
- Q2 2026: 4,711 days, down 12.7% year over year.
- A headline reports a further 4.8% drop in Q3 2026 (headline only).
  — [FilmLA Q2 2026 release](https://filmla.com/wp-content/uploads/FilmLA-News-Release-Q2-2026-LA-Production-Report.pdf); [TheWrap](https://www.thewrap.com/industry-news/industry-trends/los-angeles-on-location-shooting-drops-again-in-q3-filmla-study-shows/)

### Inferences
- **The ARO plus the vacancy glut makes conversion screening a natural fit, but it is an obvious idea.** It only becomes surprising if:
  - the interior scan supplies the hard physical constraints (floor-plate depth to windows, core and plumbing-stack location, column grid);
  - CoStar supplies the "lease-expiry cliff" timing;
  - the agent outputs a unit test-fit, not just a score.
- **Seismic plus ULA is an underexplored combination: "who is forced to sell, and when."**
  - Soft-story buildings are visually identifiable from oblique imagery (tuck-under parking on wood posts).
  - CoStar gives owner tenure, last sale and a ULA-threshold price estimate.
  - Retrofit cost combined with the ULA tax at sale models distress.
- **Film location supply is an untapped use of CRE data.**
  - Vacant LA office, retail and industrial space (in CoStar) is idle inventory.
  - Shoot days are collapsing, so cheap, searchable, scan-previewed locations matter to both landlords and producers.
  - This is very LA-specific and very "we didn't know you could do that."

### Gaps
- No authoritative LADBS count of soft-story or non-ductile concrete buildings still non-compliant after the April 2026 deadline.
- No commercial-specific fire rebuild permit counts.
- Not researched: Measure ULA's effect specifically on office sales (versus multifamily), LA homelessness and building interactions, EV charging mandates.
- 5G small-cell siting was not researched.

---

## 4. Which non-obvious users could benefit from building-level data, and what do they need?

### Takeaway
The strongest non-obvious users found are:
- fire departments building pre-incident plans, where Matterport already markets "facility passports" but without CRE tenant data;
- film and TV location scouts in LA;
- disability-access auditors and the landlords who get sued;
- insurers' ground-floor and flood underwriting;
- quant and "alt-data" investors who already use parking-lot counts.

Each needs the fusion of interior + exterior + tenant/market data that no single vendor provides.

### Cited Findings
**Fire and public safety**
- Digital Twin Imaging uses Matterport Pro3 scans of schools, hospitals and public buildings, annotated with extinguishers, AEDs, exits and hydrants for first responders. In a vendor-reported SWAT exercise, room-to-room search time fell from more than 7 minutes to under 30 seconds after pre-planning on models. — [Matterport case study](https://matterport.com/industries/case-studies/transforming-emergency-preparedness-how-digital-twin-imaging-and-matterport)
- Matterport promotes "facility passports" for mutual aid at critical sites. It names fire departments building pre-incident plans as users, pins hazards and shutoffs, and warns that a pre-plan needing VPN or special software "can fail during an incident". — [Matterport facility passport](https://matterport.com/blog/how-to-create-facility-passport)

**Film location scouting (LA)**
- On-location shoot days are down 16.1% in 2025. California's expanded tax credit only mitigates the decline. — [FilmLA Q2 2026](https://filmla.com/wp-content/uploads/FilmLA-News-Release-Q2-2026-LA-Production-Report.pdf); [ABC7](https://abc7.com/post/amid-decline-la-film-tv-production-newly-expanded-tax-credit-seen-possible-lifeline/18007614/)

**Accessibility**
- California dominates ADA Title III filings, and CCDA tracks the most common construction-related violations. — [JD Supra](https://www.jdsupra.com/legalnews/ada-title-iii-federal-lawsuit-filings-2632226/); [CCDA](https://www.dgs.ca.gov/CCDA/Resources/Page-Content/California-Commission-on-Disability-Access-Resources-List-Folder/Top-Ten-Alleged-Construction-Related-Disability-Access-Violations-July-through-December-2025)
- Pending California bill AB 649 would give CASp-inspected defendants 120 days to fix violations. Its status is uncertain. — [CalMatters Digital Democracy](https://calmatters.digitaldemocracy.org/bills/CA_202520260AB649)

**Investors (alternative data)**
- Satellite parking-lot fill rates (RS Metrics and Orbital Insight data, 2011–2017) predict quarterly retailer earnings. Falling utilization is an especially strong negative signal, and traders short ahead of bad lot data. — [JFQA paper](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/2F5F99D68D1F8940F61578F198D6C005/S0022109023001448a.pdf/on-the-capital-market-consequences-of-big-data-evidence-from-outer-space.pdf); [Berkeley Haas](https://newsroom.haas.berkeley.edu/?p=12181); [Quartz](https://qz.com/1652293/how-to-make-money-with-rs-metrics-and-orbital-insight-space-data)

**Disaster response and insurers**
- Vexcel Gray Sky and Nearmap publish post-event imagery within about 24–36 hours. — [Vexcel](https://vexceldata.com/gray-sky-event-tornado-hits-metro-areas-in-houston-texas); [Nearmap](https://nearmap.com/white-papers/hurricane-beryl-government)

### Inferences
- **Fire pre-plans are a high-impact, visual, agentic and non-cliché fit.** NFPA 1620-style pre-incident plans need:
  - exterior: fire department connection (FDC), hydrant, roof access, solar array hazard, rooftop units;
  - interior: stairs, standpipes, shutoffs, storage hazards;
  - occupancy: from CoStar tenants, e.g. a battery distributor or chemical warehouse in Houston's industrial belt, or a daycare tenant.
  Nobody fuses tenant rosters with scans. A live "dispatch → 10-second brief" demo is dramatic.
- **Location scouting turns vacancy, a CRE negative, into revenue, a positive.** Jev's image-as-criteria feature fits "find a space that looks like this reference still".
- **ADA risk scoring is concrete and checkable,** e.g. door clear width, ramp presence, accessible stalls and path of travel visible in obliques, with retail tenants' lawsuit exposure.
- **Other non-obvious users** (delivery robots and drones, telecom small cells, EV charging operators, ghost kitchens) were not researched in depth. They are plausible but have weaker evidence of urgent pain.

### Gaps
- No independent fire-service data on how many departments maintain digital pre-plans.
- No figures on LA location-fee revenue for commercial landlords.
- Delivery-robot and drone, 5G small-cell and EV-charging angles were not researched this session.

---

## 5. What do existing proptech and AI startups already do, and what did HackPrinceton F25 already do (clichés to avoid)?

### Takeaway
Roof condition, solar and peril scoring from aerial imagery for insurers is a crowded, consolidated market. Examples: CAPE Analytics, bought by Moody's in Jan 2025, about $211M per PitchBook; Betterview, bought by Nearmap in 2023. Retail parking-lot counts as an alt-data signal date from about 2014–2017. HackPrinceton F25's top winners already covered rooftop solar from satellite (Watt's Up) and an agentic renewable site-selection map (TerraLink), so avoid roof-only analysis, solar, and "agent ranks sites on a map" framings.

### Cited Findings
- Moody's announced the acquisition of CAPE Analytics on Jan 13, 2025. It will merge CAPE into its Intelligent Risk Platform and catastrophe models for an address-level property database. CAPE extracts attributes such as solar presence and roof condition from satellite and aerial imagery. — [Insurance Journal](https://www.insurancejournal.com/news/national/2025/01/13/807956.htm); [TechCrunch](https://techcrunch.com/2025/01/13/moodys-agrees-to-acquire-cape-analytics-which-develops-geospatial-ai-for-insurance-providers); [PitchBook](https://pitchbook.com/profiles/company/149308-39)
- Nearmap acquired Betterview in Dec 2023. Both turn aerial imagery into underwriting attributes such as roof condition. — [CB Insights compare](https://www.cbinsights.com/compare/betterview-vs-cape-analytics)
- Orbital Insight identifies cars at more than 55,000 retail lots, and its series correlate with same-store sales. Its own analysts say it works best for large, car-centric retail and needs imagery of about 50 cm. — [Orbital Insight Medium](https://medium.com/from-the-macroscope/orbital-insight-correctly-predicts-retail-sales-miss-hit-rate-grows-to-78-aa65ea445423); [SkyFi](https://skyfi.com/blog/analyzing-foot-traffic-with-satellite)
- HackPrinceton Fall 2025 (Nov 7–9, 2025): 596 participants, 195 teams, 36 hours. — [crafterwiki dataset PR #22](https://github.com/RikepilB/crafterwiki/pull/22); [Devpost](https://hackprinceton-fall-2025.devpost.com/)
  - **Watt's Up** won Best Overall (podium). It segments roofs in satellite imagery (SegFormer) and combines NASA POWER irradiance to estimate solar production, savings and CO2. Stack: React, PyTorch, Gemini. — [crafterwiki PR](https://github.com/RikepilB/crafterwiki/pull/22); [Devpost](https://devpost.com/software/watt-s-up)
  - **TerraLink** won Best Overall (podium) and Best Sustainability. It is an agent that queries Google Earth Engine, scores solar, wind, hydro and geothermal sites, and explains them on a map. Stack: Flask, Gemini, GeoJSON. — [crafterwiki PR](https://github.com/RikepilB/crafterwiki/pull/22)
  - Other indexed F25 winners include spatialmd, terrar-ai, nautilink and ai-bnb (from the PR file list; contents not reviewed). — [crafterwiki PR files](https://github.com/RikepilB/crafterwiki/pull/22)

### Inferences
- **Avoid:**
  - roof condition, solar or peril scores (owned by Moody's/CAPE, Nearmap/Betterview, and Watt's Up);
  - generic "multi-agent chat over property data";
  - "agent ranks sites on a map" (TerraLink);
  - retail parking-lot car counts on their own (Orbital Insight).
- **The open space is fusion and inversion:**
  - interior scans plus oblique facades plus tenant and lease timelines;
  - signals no one vendor holds, such as leased-but-empty space, ground-floor flood vulnerability, film-ready vacant space, or tenant-aware fire pre-plans.
- **Spend demo time on what the incumbents can't show:** the Matterport interior. Incumbents are almost all exterior or aerial.

### Gaps
- Not verified this session, so no claims are made about their current products:
  - Zesty.ai (wildfire and peril AI);
  - Reonomy (acquired by Altus Group in 2021, from background knowledge);
  - Cherre (CRE data unification);
  - Placer.ai (mobile foot traffic);
  - EliseAI (leasing AI agents).
  Verify these before citing them in a pitch.
- The CoStar-track winners and projects from HackPrinceton Spring 2026 were not checked, and could contain closer prior art.
- Devpost gallery pages returned 403, so the full list of F25 projects beyond the prize winners was not reviewed.

---

## 6. What surprising insights can aerial imagery and interior scans produce, and what project concepts follow (with Jev's role)?

### Takeaway
There is documented precedent for imagery-derived economic signals: parking fill predicts earnings, and roof condition predicts claims. Interior 3D scans add the missing physical constraints: floor-plate depth, cores, open ground floors, equipment locations. The highest-surprise projects treat imagery and scans as evidence that contradicts or anticipates CoStar's records ("the lease says occupied; the building says empty"), and use Jev as a high-throughput visual judge inside an LLM-planned agent loop.

### Cited Findings
- Parking-lot fill-rate growth predicts quarterly retailer performance, and declines are the strongest signal. — [JFQA](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/2F5F99D68D1F8940F61578F198D6C005/S0022109023001448a.pdf/on-the-capital-market-consequences-of-big-data-evidence-from-outer-space.pdf)
- Aerial imagery yields underwriting attributes such as roof condition and solar presence, used by insurers. — [TechCrunch on CAPE](https://techcrunch.com/2025/01/13/moodys-agrees-to-acquire-cape-analytics-which-develops-geospatial-ai-for-insurance-providers)
- Matterport models support measuring clearances and pinning hazards and shutoffs at exact 3D locations. — [Matterport facility passport](https://matterport.com/blog/how-to-create-facility-passport)
- Vexcel provides oblique, ortho and multispectral imagery at 7.5 cm, plus rapid post-disaster (Gray Sky) collections. — [Vexcel](https://vexceldata.com/gray-sky-event-tornado-hits-metro-areas-in-houston-texas)
- Jev patterns:
  - tile-and-Choice search over large images;
  - per-item Noul summed in code instead of counting;
  - images as Choice criteria;
  - confidence routing;
  - fan-out of dozens of questions per image at almost no extra latency.
  — [Images](https://docs.typesafe.ai/images.md); [Model jaggedness](https://docs.typesafe.ai/model-jaggedness.md); [Patterns via llms.txt](https://docs.typesafe.ai/llms.txt)

### Inferences (candidate concepts, ranked by surprise × buildability in about 34 hours for 3 people)

**A. "Shadow Vacancy" detector (Houston office; also LA). Recommended #1 for the CoStar track.**
- **Problem:** Houston office is 24–28% vacant, with some submarkets above 44%. Leased-but-unused ("dark") space is invisible in lease data until expiry or sublease.
- **Layers:**
  - CoStar: lease expirations, tenants, reported vacancy, sale and loan history.
  - Vexcel: multi-date obliques/orthos showing parking fill and lit/unlit or blinds-drawn facades.
  - Matterport: empty floors, unused desks, furniture removal.
- **Agent loop:**
  - The LLM picks candidate buildings (lease-expiry cliff in the next 24 months).
  - Jev answers per-stall Nouls on parking tiles; code sums the count.
  - Jev scores each Matterport frame from "fully occupied workspace" to "abandoned/cleared".
  - The agent reconciles these against CoStar "leased SF".
  - It flags gaps, estimates "true occupancy", predicts non-renewal, and drafts a broker outreach list or a lender watchlist.
- **Wow line:** "CoStar says 92% leased. The parking lot and the floors say 41%."
- **Jev fit:** thousands of image judgments at low cost and low latency, with calibrated probabilities feeding a risk model (Autoresearch/CatBoost pattern).

**B. "First Due": tenant-aware fire and EMS pre-incident plans (Houston industrial or LA mixed-use). Recommended #2, the strongest "non-obvious user".**
- **Layers:**
  - Vexcel obliques: FDC, hydrant, roof access, rooftop solar or battery hazard, gate locations.
  - Matterport: stairwells, standpipes, shutoffs, storage racks, dead ends.
  - CoStar tenant roster: occupancy hazard class, such as chemical, lithium battery, daycare or assembly use, and after-hours occupancy.
- **Agent loop:**
  - On a simulated 911 dispatch, the agent plans which data to pull.
  - Jev Box and Noul locate features in tiles and frames.
  - The LLM writes a 1-page, map-annotated pre-plan in seconds.
  - Confidence routing flags "unverified, check on arrival".
- **Novelty:** Matterport sells facility passports but does not fuse tenant and market data. Rooftop solar appears only as a firefighter hazard, not a solar cliché.

**C. "Scout": vacant CRE as film locations (LA). Recommended #3, the highest "we didn't know" factor.**
- **Layers:**
  - CoStar: vacant and available spaces and their owners.
  - Matterport: interior "looks".
  - Vexcel: basecamp and truck parking, street frontage, sun orientation.
- **Agent loop:**
  - A producer uploads reference stills (e.g. "1970s bank lobby").
  - Jev Choice uses the reference images as criteria against scan frames, and Score rates the match.
  - Code filters by CoStar availability.
  - The LLM drafts a landlord outreach and location-fee estimate.
- **Why it works:** FilmLA shoot days fell 16.1% in 2025, and LA has more than 50M SF of vacant office. It turns vacancy into income.

**D. Seismic-plus-ULA "forced seller" radar (LA).**
- Obliques detect tuck-under soft-story parking. CoStar supplies owner tenure, the last sale and the ULA threshold. Code estimates retrofit cost plus transfer tax.
- **Output:** which owners are likely to sell, and at what price.
- **Risk:** the seismic program lists are public, so the novelty is the fusion with ULA economics.

**E. Ground-floor flood and business-interruption exposure (Houston).**
- Obliques show the number of entry steps, ground-level transformers and generators, and dock height. Matterport shows ground-floor mechanical and electrical rooms. The CoStar tenant roster gives business-interruption exposure.
- Post-event Gray Sky imagery gives before/after damage triage.
- **Angle:** the ground floor, not the roof, which differentiates it from CAPE and Betterview.

**F. Adaptive-reuse "X-ray" (LA ARO).**
- Matterport floor-plate depth to windows, core and stack positions; obliques for window-to-wall ratio; CoStar for lease-expiry timing.
- **Output:** a unit test-fit and pro forma.
- **Caveat:** a common idea; only differentiated if the interior-derived test-fit is real.

**G. ADA path-of-travel risk scorer (LA retail).**
- Obliques show accessible stalls and curb ramps; Matterport shows door widths and restroom features; CoStar retail tenants indicate exposure.
- Jev Nouls per CCDA top-ten violation category.

**Build guidance across all concepts**
- Use Claude or another LLM for planning, tool calls and narrative.
- Use Jev with fan-out and confidence routing for every image or record judgment.
- Keep counting, area and $ math in code.
- Pre-cache imagery tiles, because Jev rejects images outside 280–1568 px.
- Show calibrated probabilities on screen; judges like seeing "92% sure, routed to human".

### Gaps
- Not determined:
  - which buildings the hackathon's Matterport scans and Vexcel coverage actually include (Houston vs LA, office vs industrial);
  - whether CoStar provides multi-date imagery or lease-expiry fields in the hackathon dataset.
  Concept A depends on multi-date aerials and lease data. Concept B depends on tenant names plus exterior obliques. Teams should check the data map before choosing.
- Tested accuracy of Jev Box on oblique aerials or Matterport panoramas: none published; expect to iterate.
- No published study was found linking interior-scan layout features to office conversion feasibility or to shadow vacancy. These are hypotheses that would be novel if shown.
