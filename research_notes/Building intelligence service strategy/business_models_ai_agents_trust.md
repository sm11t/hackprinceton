# Building Intelligence Service: Business Models, Pricing, AI Agents in Real Estate, Trust/Compliance, Licensing, GTM (as of 2026-11-13)

Research scope note: ~18 tool calls (searches + 2 page fetches). Most findings come from search-result summaries; only the Bisnow (Feb 2026) and Speedwell (3Q26) pages were opened in full. Items marked **[UNVERIFIED]** are single-source, vendor-sourced, or not confirmed against a primary document.

---

## 1. Pricing and packaging benchmarks (per-property API, seats, per-report, DaaS vs SaaS vs outcome)

### Takeaway
Public price points cluster in three tiers: self-serve per-record APIs (~$0.10–$0.15 per parcel record, Regrid), entry-level property-data API subscriptions (~$500/month, ATTOM), and enterprise seat licenses (CoStar, estimated ~$200–$600+/user/month, not published). Insurance-grade AI property attributes (CAPE, Zesty.ai) and Snowflake/Databricks delivery are quote-only. Human-delivered reports, the thing an AI "building intelligence" product would displace or speed up, cost ~$1,250–$3,500 for a baseline commercial PCA and $10K+ for large or complex assets.

### Cited Findings
**Per-record / API pricing**
- Regrid self-serve API: each monthly plan includes 2,000 parcel records + 200,000 tiles; overage is $0.10 per parcel record (Standard schema) or $0.15 (Premium schema), plus $0.001 per extra tile. Users can set a monthly maximum spend. Limits are about 200 requests/min and 10 concurrent requests. 30-day free sandbox. — [Regrid support: plan options](https://support.regrid.com/reference/plan-options); [Regrid self-serve API blog](https://regrid.com/blog/introducing-regrids-updated-self-serve-api); [Regrid General FAQs](https://support.regrid.com/docs/general-faqs)
- Regrid historical annual bundles (2020, **old**): $12K/yr Standard and $18K/yr Premium, each with 120,000 parcel records + 12M tiles, which works out to ~$0.10–$0.15/record. The annual price lines up with the current overage price. — [Regrid API packages blog](https://regrid.com/blog/apipackages)
- ATTOM: "Basic Property API plans start at $500 per month." Premium pricing "varies based on data requirements, usage and application needs." 30-day free trial. — [ATTOM Property Data API pricing](https://www.attomdata.com/solutions/delivery/property-data-api/pricing/)
- ATTOM production plans (annual API subscriptions, bulk licensing, Snowflake Secure Data Share / Databricks Delta Share delivery) are negotiated with sales. Under Snowflake, the buyer also pays Snowflake compute and storage separately. — [ATTOM Snowflake FAQs](https://www.attomdata.com/solutions/delivery/cloud-delivery/snowflake/faqs/); [Datarade ATTOM listing](https://datarade.ai/data-providers/attom)
- Cotality (formerly CoreLogic) delivers via REST API, bulk files, and Databricks / Google Cloud / Snowflake marketplaces. Pricing is subscription-based and "tailored" per sales rep, with no public prices. — [Cotality vs ATTOM](https://www.cotality.com/compare/cotality-vs-attom); [CoreLogic joins Snowflake Data Marketplace (2020, old)](https://businesswire.com/news/home/20201208005473/en/CoreLogic-Joins-Snowflake-Data-Marketplace-to-Provide-Further-Access-to-Unrivaled-Property-Data)
- ZestyAI publishes no tiered pricing ("Book a Demo"). A third-party comparison site estimates "$2–$8 per property" **[UNVERIFIED, likely unreliable]**. — [checkthat.ai ZestyAI](https://checkthat.ai/brands/zestyai)
- CAPE Analytics: no public pricing. Says "nearly half of the top 50 U.S. property insurers" plus some leading banks use CAPE in pricing/underwriting. Moody's agreed to acquire CAPE in Jan 2025 (terms undisclosed, expected to close Q1 2025). — [Insurance Journal, Jan 13 2025](https://www.insurancejournal.com/news/national/2025/01/13/807956.htm); [BusinessWire](https://www.businesswire.com/news/home/20250113472182/en); [TechCrunch](https://techcrunch.com/2025/01/13/moodys-agrees-to-acquire-cape-analytics-which-develops-geospatial-ai-for-insurance-providers/%C2%A0)

**Seat / subscription pricing**
- CoStar does not publish prices. Third-party estimates put it at $200–$500+ per user/month. A BiggerPockets user reported $200 to nearly $600+/month per broker (anecdotal). — [brainbound CoStar pricing guide](https://brainbound.blog/costar-pricing-guide); [BiggerPockets forum](https://www.biggerpockets.com/forums/32/topics/82859-how-much-does-costar-cost?page=2) **[UNVERIFIED estimates]**
- ThePricer claims CoStar Suite (All Markets) is ~$3,400/month per license, with one license covering 3 users. Another source (RISMedia) frames $3,400 as annual. The sources conflict. — [ThePricer](https://www.thepricer.org/how-much-does-costar-membership-cost); [RISMedia Q1 2026 earnings](https://www.rismedia.com/2026/04/29/costar-group-celebrates-strong-financial-agent-subscriber-count-growth-price-raises-new-members-q1-earnings/) **[CONFLICTING]**
- Price drivers: seat count, geography, modules, and contract length. Annual terms reportedly save 10–20% vs month-to-month. — [brainbound CoStar subscription guide](https://www.brainbound.blog/costar-subscription-guide) **[UNVERIFIED]**
- CoStar retention metrics as a stickiness benchmark: CoStar renewal rate 92%, and Apartments.com monthly renewal 98.4% (3Q26). — [Speedwell Research 3Q26 recap](https://www.speedwellmemos.com/p/costar-3q26-business-recap)

**Per-report pricing (the human-services benchmark)**
- Baseline commercial PCA (ASTM E2018): ~$1,250–$2,500, with large or complex assets >$10,000. — [Florida Commercial Building Inspectors / frcpi](https://frcpi.pages.dev/pricing) **[vendor marketing]**
- A 5,000–15,000 sf retail/office building costs $1,500–$3,500 for a standard ASTM E2018-15 PCA. Mid-size (5K–50K sf) runs $3,000–$15,000, and complex or older buildings $5,000–$25,000+. — [RSB Environmental PCA cost](https://rsbenv.com/astm-property-condition-assessment-cost/); [inspectandtest.net](https://inspectandtest.net/guides/how-much-does-a-property-inspection-cost/) **[vendor marketing]**
- 2011 benchmark (**old**): equity-focused PCR ~$10,000 vs ~$2,500 for a standard ASTM PCA. — [GlobeSt 2011](https://www.globest.com/2011/07/18/property-condition-reports-spend-a-little-to-save-a-lot/)
- The current standard is ASTM E2018-24. Fannie/Freddie multifamily lending imposes PCA scope beyond the ASTM baseline, which changes price. — [en-standard.eu E2018-24](https://www.en-standard.eu/astm-e2018-24-standard-guide-for-property-condition-assessments-baseline-property-condition-assessment-process/); [Apers third-party reports](https://apers.app/learn/transaction-lifecycle/due-diligence/third-party-reports-appraisal-pca-esa-zoning)

### Inferences
- A defensible price ladder for the hackathon service: (1) a self-serve per-property attribute API at roughly $0.10–$2 per building lookup (between Regrid's raw parcel pricing and the [UNVERIFIED] $2–$8 insurer-grade AI attribute estimate); (2) a per-report "desktop pre-PCA / building dossier" at ~$100–$500, a fraction of a $1,500–$3,500 PCA, positioned as pre-screening rather than a replacement; (3) enterprise annual license or Snowflake share for portfolios (lenders, insurers, REITs).
- Outcome-based pricing (e.g., per avoided site visit, per loss-ratio point) is attractive for insurers. Nothing found here confirms a property-data vendor that publicly prices this way, so treat it as a hypothesis.
- Regrid's 2020 annual price matching its 2026 overage price points to price stability in commodity parcel data. Differentiated, AI-derived interior/condition attributes should command a premium over parcel records.

### Gaps
- No public pricing found for CAPE, Zesty.ai, Cherre, Reonomy, Placer.ai, CompStak, CREXi Pro, or Snowflake marketplace listings for property data (not searched in depth due to the tool budget). CREXi Pro and CompStak list prices were not retrieved.
- Appraisal fees and BOV pricing were not researched. Commercial appraisal fees are commonly cited in the low thousands of dollars, but no source was retrieved **[gap]**.
- Usage-based AI pricing for real-estate agents (per conversation, per lease abstracted) was not found as published pricing.

---

## 2. Moats, network effects, data flywheels, and why verified/proprietary data matters in the AI era

### Takeaway
CoStar is the clearest case study: it argues its nonpublic, researcher-verified data is the moat against general AI ("AI cannot create data from nothing"). Its CEO cited head-to-head tests in which an AI agent using only public data had a **75% error rate**, versus CoStar's claimed "single-digit" error rate. That figure is a CEO claim relayed by a secondary source, with no published methodology. CoStar has also been consolidating the exact inputs the hackathon plans to use: it owns Matterport and (per Speedwell) Vexcel.

### Cited Findings
- 3Q26 earnings: Andy Florance said "In head-to-head tests, an AI agent using only publicly available data had a 75% error rate" and "We believe our solution operates with single-digit error rates." The context was the leasing business and fears that AI could replicate CoStar's data gathering. No test design, sample size, or date was disclosed. — [Speedwell Research, CoStar 3Q26 Business Recap](https://www.speedwellmemos.com/p/costar-3q26-business-recap) **[company claim, secondary source; primary transcript not reviewed]**
- Feb 2026: Florance said "AI cannot create data from nothing" and that CoStar's nonpublic data sets it apart ("we have more, we have significantly more"). William Blair called CoStar "one of the few companies we track with market-ready, differentiated AI solutions." Executives said AI had replaced ~500 roles (Jan 2026). — [Bisnow, Feb 24 2026](https://www.bisnow.com/news/national/commercial-real-estate/costar-ceo-andy-florance-touts-ai-push-as-stock-hits-7-year-low-133384)
- CoStar says Homes AI data "remains entirely within the Homes.com proprietary ecosystem and is never used to train or refine external AI models." It is powered by Microsoft Azure OpenAI. — [BusinessWire, Feb 17 2026](https://secure.businesswire.com/news/home/20260217810823/en/CoStar-Group-Launches-Transformative-AI-Experience-on-Homes.com-Redefining-the-Future-of-Home-Shopping)
- Counterpoint on accuracy: Online Marketplaces found Homes AI returned some factually incorrect data in a niche Miami search (anecdote). — [OnlineMarketplaces](https://onlinemarketplaces.com/articles/the-new-industry-leader-in-ai-home-search-in-conversation-with-the-team-behind-homes-ai/)
- Demand-side signal: a Cotality survey found 64% of buyers worry AI is recycling unverified information from other websites. — via [nowbam.com](https://nowbam.com/6-things-real-estate-agents-need-to-know-about-homebuyers-and-ai-in-2026/) **[secondary]**
- AI discovery is concentrating on listing sites. Peek's study (June–Aug 2026) found 72% of sources AI cited for apartments were ILSs (Zillow, Apartments.com), and Zillow + CoStar networks cover 86% of listing data AI reads (1,701 assessments across 4 AI models). — [Peek AI Discovery Black Book](https://www.peek.us/ai-discovery-black-book) **[vendor study]**
- Apartments.com Ai logged 5.2M+ sessions between June 13 and Oct 5, 2026. Apartments.com has a partnership with ChatGPT. — [Inman, Oct 21 2026](https://www.inman.com/2026/10/21/what-ai-search-conversations-reveal-about-renters/); [Speedwell](https://www.speedwellmemos.com/p/costar-3q26-business-recap)
- Proprietary content as moat: Speedwell cites "proprietary content like the Matterport 3D walkthroughs" as a defensive advantage. Matterport grows ~11% y/y. **Vexcel (the imagery behind Bing Maps) is described as a CoStar acquisition, with LTM revenue of $140M growing >30%.** CoStar LTM revenue is $3.7B. — [Speedwell](https://www.speedwellmemos.com/p/costar-3q26-business-recap) **[Vexcel ownership by CoStar: confirm against a primary CoStar press release]**
- Proprietary-media enforcement: CoStar acquired Matterport for $1.6B. Zillow removed Matterport tours after CoStar declined to renew the API agreement. CoStar's terms (revised Sept 29, 2025) give customers a "limited, revocable, non-transferable, non-sublicensable license" for CoStar media, including Matterport tours. — [RISMedia, Oct 20 2025](https://www.rismedia.com/2025-10-20/zillow-removes-matterport-escalating-dispute-costar/); [nowbam](https://nowbam.com/why-zillow-is-pulling-matterport-tours-from-its-platform/)
- CoStar does not publish a self-serve API. Access is through commercial agreements, and it enforces license terms. — [Pacific Software Ventures](https://pacificsoftwareventures.com/newsroom/can-ai-pull-costar-data-commercial-real-estate) **[secondary]**

### Inferences
- The hackathon's three inputs (CoStar records, Matterport interiors, Vexcel aerials) appear to all sit inside CoStar Group. The most credible "sellable" framing is therefore an AI layer CoStar (or a CoStar-licensed partner) could ship, a verified building-intelligence agent, not a standalone company reselling CoStar data. That makes the play an internal product, an embedded partner, or a showcase of the "fused proprietary data beats public-data AI" thesis.
- Flywheel to pitch: each Matterport scan plus Vexcel capture adds verified attributes (roof condition, interior finishes, ADA features, MEP visible condition). Those improve the models, which improve report accuracy, which drives more scans and listings onto the platform. CoStar's 75%-vs-single-digit claim is the marketing frame, but a team should show its own measured error rate per attribute.
- The moat is shifting from "having data" to "having verified data with provenance that AI agents can cite." Chat/agent surfaces (ChatGPT, Apartments.com Ai) route traffic to whoever has structured, trustworthy listing-level data.

### Gaps
- Primary CoStar 3Q26 transcript not reviewed. The 75% figure's methodology is unknown.
- No independent study measuring AI error rates on CRE building attributes was found.
- Vexcel acquisition date and terms were not confirmed from a primary source.

---

## 3. AI agents in real estate 2025–2026: what exists and what is missing

### Takeaway
2025–2026 AI agents in real estate cluster in (a) consumer search assistants on portals (Homes AI, Apartments.com Ai), (b) leasing and resident communication (EliseAI, >$200M ARR, $4B valuation reported), (c) data platforms with agent builders (Cherre Agent.STUDIO, now owned by RealPage), and (d) document-centric CRE underwriting, lease abstraction, and due-diligence agents (Cadastral, CarbonAI, Fifth Dimension). No product found fuses verified records with interior 3D scans and aerial imagery into an explainable, per-attribute building-condition agent. That is the open lane.

### Cited Findings
- **CoStar Homes AI** (launched Feb 17, 2026): natural-language home search over Homes.com listings plus proprietary market data, on Azure OpenAI. CoStar laid off 200 Homes.com staff a day later. — [BusinessWire](https://www.businesswire.com/news/home/20260217810823/en/); [Bisnow](https://www.bisnow.com/news/national/commercial-real-estate/costar-ceo-andy-florance-touts-ai-push-as-stock-hits-7-year-low-133384)
- **Apartments.com Ai**: conversational rental search, 5.2M+ sessions June–Oct 2026. — [Inman](https://www.inman.com/2026/10/21/what-ai-search-conversations-reveal-about-renters/); [letsdatascience](https://letsdatascience.com/news/costar-launches-apartmentscom-ai-conversational-search-38921227)
- **EliseAI** (leasing/resident AI): $250M Series E in Aug 2025 at a $2.2B valuation, led by a16z with Bessemer, Sapphire, and Navitas. A later $350M round at a $4B valuation was reported after it passed $200M ARR (round date not confirmed). — [Bisnow](https://www.bisnow.com/news/national/property-management/eliseai-raises-350m-funding-round-plans-automation-expansion); [pulse2](https://pulse2.com/eliseai-raises-350-million-at-4-billion-valuation/) **[$4B round date unconfirmed]**
- **Cherre**: launched Agent.STUDIO (July 14, 2025), a platform for building custom AI agents on connected real estate data, and an AI Agent Marketplace (Oct 2025). RealPage completed its acquisition of Cherre (announced July 2026, terms undisclosed). — [Cherre blog, Agent.STUDIO](https://blog.cherre.com/2025/07/14/cherre-launches-agent-studio); [Cherre AI Agent Marketplace](https://blog.cherre.com/2025/10/31/introducing-cherre-ai-agent-marketplace/); [Thoma Bravo / RealPage acquires Cherre](https://thomabravo.com/press-releases/realpage-acquires-cherre); [Propmodo analysis](https://technology.propmodo.com/p/what-realpage-s-acquisition-of-cherre-reveals-about-its-strategy-after-the-antitrust-settlement)
- **Cadastral** (Feb 2026, $9.5M, led by Navitas with JLL Spark): an "AI analyst in a box" for lease abstraction, acquisitions due diligence, and end-to-end underwriting. Reportedly 40+ customers. Bisnow reports AvalonBay and Equity Residential participated. — [pulse2](https://pulse2.com/cadastral-9-5-million-funding); [Bisnow](https://bisnow.com/national/news/proptech/cadastral-raises-95m-for-ai-platform-from-avalonbay-equity-residential-133110)
- **CarbonAI** (Oct 15, 2026, $12M led by Cowboy Ventures): agents for CRE lending underwriting, due diligence, and post-close monitoring. Claims up to 90% faster lease review (no methodology). US only. — [letsdatascience](https://letsdatascience.com/news/carbonai-raises-12m-led-by-cowboy-ventures-for-cre-lending-a-c20ca913) **[aggregator source]**
- **Fifth Dimension** ($26M Series A): unifies structured and unstructured data for institutional underwriting and reporting. Claims underwriting goes from weeks to days. — [CRE Daily](https://www.credaily.com/?p=217911) **[date not confirmed; company claims]**
- **Insurance property AI**: CAPE Analytics (geospatial AI, now Moody's) is used by ~half of the top-50 US property insurers. — [Insurance Journal](https://www.insurancejournal.com/news/national/2025/01/13/807956.htm)
- Analyst view: AI agents may shift discovery from site level to listing level and could disintermediate marketplaces. Property management software might feed listings directly into AI agents. This is a "theoretical risk" for now. — [Speedwell](https://www.speedwellmemos.com/p/costar-3q26-business-recap)

### Inferences
- **What's missing (opportunity):**
  1. Multimodal building-condition agents that fuse interior scans (Matterport), oblique aerials (Vexcel), and transactional/building records (CoStar) and output attribute-level findings with evidence links (image crop, scan location, capture date). Existing underwriting agents are document-centric (leases, OMs, rent rolls), and insurance AI (CAPE, Zesty) is exterior and aerial only.
  2. Agentic pre-inspection or a "desktop PCA": agents that triage which buildings need a physical inspection and pre-populate ASTM E2018 sections. No product was found doing this.
  3. Verification and provenance layers that let other AI agents (ChatGPT, Claude, Cherre agents) cite building facts with confidence and capture dates.
  4. Vertical-specific outputs from one fused dataset, e.g. insurer roof/hazard score, lender collateral-condition flag, broker listing-enrichment, and Houston-specific flood/hurricane resilience features (elevation, first-floor height, roof type).
- Market consolidation (Moody's–CAPE, RealPage–Cherre, CoStar–Matterport/Vexcel) suggests incumbents buy AI data layers rather than build them. That points to "acquirable feature" positioning for a hackathon pitch.

### Gaps
- Not researched due to the tool budget: Zillow's AI features, Crexi AI, Altus/ARGUS AI, Dealpath AI, Prophia, Leverton (MRI), Proda, Clik.ai, Archer, Northspyre. Their 2025–2026 status is unverified here.
- No agentic property-inspection startup was found in search. This needs a targeted search before claiming it is "white space" definitively.

---

## 4. Trust and compliance: what an AI-derived building attribute must show

### Takeaway
Regulation is principle-based and focuses on governance, documentation, vendor oversight, and explainability rather than prescribed accuracy thresholds. For insurers, the NAIC AI Model Bulletin (adopted by ~24–25 states) makes carriers responsible for third-party AI vendors, so a vendor must supply documentation, validation, and audit support. For banks, SR 11-7 / OCC 2011-12 was **rescinded on April 17, 2026** and replaced by risk-based, non-prescriptive guidance (SR 26-2 / OCC Bulletin 2026-13). Colorado's AI Act was delayed to June 30, 2026, and its 2026 status is unconfirmed.

### Cited Findings
- **NAIC Model Bulletin** (adopted Dec 2023): principle-based, requiring insurers to establish an AI governance program, documentation, and audit procedures. It does not prescribe specific standards. Some states modified provisions such as third-party vendor oversight. — [Fenwick](https://www.fenwick.com/insights/publications/tracking-the-evolution-of-ai-insurance-regulation)
- Adoption: 24 states as of March 2025 (Quarles), and ~23 states + DC by late 2025 (Fenwick). A vendor blog (July 2026) says 25 states adopted, with 8 more in progress. — [Quarles](https://www.quarles.com/newsroom/publications/nearly-half-of-states-have-now-adopted-naic-model-bulletin-on-insurers-use-of-ai); [Openlayer](https://www.openlayer.com/blog/post/naic-model-bulletin-ai-governance) **[2026 count is vendor-sourced]**
- Texas status under NAIC bulletin: not confirmed in this research **[gap; relevant for the Houston focus]**.
- **Bank model risk**: on April 17, 2026, the OCC, Fed, and FDIC issued replacement guidance (Fed SR 26-2, OCC Bulletin 2026-13). It rescinds SR 11-7 / OCC 2011-12, the 2021 BSA/AML model statements, OCC 1997-24 (credit scoring), and the Comptroller's Handbook MRM booklet. New guidance is "risk-based, tailored, and commensurate with" bank size. — [OCC news release NR 2026-29](https://occ.gov/news-issuances/news-releases/2026/nr-occ-2026-29.html); [Orrick, Apr 2026](https://www.orrick.com/ja-JP/Insights/2026/04/Agencies-Overhaul-Model-Risk-Management-Guidance-for-Banks-Heres-What-Changed)
- Commentators describe the new guidance as non-enforceable, without prescriptive requirements. Several consultancies say generative/agentic AI is excluded from the new model-risk scope. — [Elevate Consult](https://elevateconsult.com/insights/sr-11-7-rescinded-model-risk-guidance-ai-gap); [Bonadio](https://www.bonadio.com/article/occs-updated-model-risk-management-guidance/) **[secondary reading; primary text not checked]**
- **Colorado AI Act (SB 24-205)**: effective date delayed from Feb 1, 2026 to June 30, 2026 (SB25B-004, signed Aug 28, 2025). The AG has exclusive enforcement. Commentators expected the 2026 session to amend or narrow it. — [Greenberg Traurig](https://www.gtlaw.com/en/insights/2025/9/colorado-delays-comprehensive-ai-law-with-further-changes-anticipated); [Akin Gump](https://www.akingump.com/en/insights/ai-law-and-regulation-tracker/colorado-postpones-implementation-of-colorado-ai-act-sb-24-205); [PYMNTS](https://www.pymnts.com/artificial-intelligence-2/2025/colorado-delays-ai-act-to-june-2026-businesses-get-breathing-room/)

### Inferences
- What a sellable AI building attribute should carry, synthesized from governance-based regimes:
  - **Provenance**: source (CoStar record ID, Matterport scan ID/sweep, Vexcel capture ID) and capture date.
  - **Evidence**: a viewable image crop or 3D location supporting each attribute, which supports explainability and adverse-action reasoning in insurance.
  - **Confidence**: a calibrated score, with a measured error rate per attribute on a held-out validation set.
  - **Model card**: version, training data description, known limitations, and bias testing. Under NAIC, insurers must oversee vendors and will ask for this.
  - **Human-in-the-loop flag**: when a physical inspection is recommended.
  - **Audit log**: an immutable record of what the agent saw and output.
- Even with SR 11-7 rescinded, bank lenders will still apply risk-based validation to third-party collateral-condition data, so the same documentation pack serves both lenders and insurers.
- For appraisal/valuation use, USPAP places responsibility on the appraiser, so AI attributes would likely be positioned as data the appraiser verifies, not a conclusion **[inference; USPAP not researched]**.

### Gaps
- USPAP / Appraisal Foundation guidance on AI and automated tools was not researched.
- Colorado AI Act status after the 2026 session (amended, delayed again, or in force) was not confirmed. The relationship to Colorado SB21-169 (insurance algorithmic discrimination) was not researched.
- Texas adoption of the NAIC bulletin and the Texas Responsible AI Governance Act (TRAIGA) were not verified, though both are relevant for Houston.

---

## 5. Data licensing constraints (CoStar, Vexcel, Matterport)

### Takeaway
All three sources restrict redistribution and competitive derivative use. Vexcel allows "Derivatives" (features extracted by analysis) but requires written consent for sublicensees and bars building a competing analytics offering. Matterport's ToS (Aug 5, 2026) prohibits using the service to train AI models and bars AI-agent scraping. CoStar media licenses are "limited, revocable, non-transferable, non-sublicensable," and CoStar has no self-serve API. Commercially, the product must run under a CoStar Group agreement.

### Cited Findings
- **Vexcel EULA (Sept 2025)**: "Derivatives" means works created by analyzing the Product and extracting features. The March 2024 version excludes images/pixels themselves from Derivatives. — [Vexcel EULA Sept 2025](https://vexceldata.com/wp-content/uploads/2025/10/2025.09-EULA-for-vexceldata.pdf); [Vexcel EULA Mar 2024](https://vexceldata.com/wp-content/uploads/2024/03/EULA-March-2024.pdf)
- Vexcel sublicensing requires Vexcel's written consent and a binding written agreement naming Vexcel as an express third-party beneficiary. Licensees may not "benchmark, create, or improve a competing commercial imagery dataset, analytics offering, or data." — [Vexcel EULA page](https://vexceldata.com/eula/)
- The Vexcel 3D City EULA is limited to internal use. The evaluation agreement gives Vexcel ownership of feedback and derivative works "created using or inspired by" feedback. — [3D City EULA](https://vexceldata.com/wp-content/uploads/2024/02/2024.01.31-3D-City-EULA.pdf); [Eval & Beta agreement, Mar 2026](https://vexceldata.com/wp-content/uploads/2026/05/2026.03.13-Eval-and-Beta-Testing-Agreement-for-Vexcel-Intelligence-Click-Through-Versio.pdf)
- **Matterport Terms of Use (Aug 5, 2026)** prohibit developing or training AI/ML/generative models and automated scraping by AI agents. — [Matterport Terms of Use](https://matterport.com/terms-of-use)
- **Matterport Services Agreement**: "Matterport Data" (anonymized, aggregated, or de-identified data derived from platform use) is excluded from customer data, so Matterport keeps rights to aggregate derived data. — [Matterport MSA](https://matterport.com/legal/msa)
- **Matterport Submission Terms** (July 1, 2025): submitters keep ownership of Submissions. Matterport may share image data with academic researchers for deep-learning research. — [Matterport Submission Terms](https://matterport.com/legal/submission-terms-and-conditions)
- **CoStar**: the media license is "limited, revocable, non-transferable, non-sublicensable" (terms revised Sept 29, 2025). CoStar declined to renew Zillow's Matterport API agreement. — [RISMedia](https://www.rismedia.com/2025-10-20/zillow-removes-matterport-escalating-dispute-costar/)

### Inferences
- A hackathon prototype is fine under event or sandbox access. A commercial product would need a CoStar Group partner agreement covering (a) output-only derived attributes (not raw pixels or scans), (b) no model training on Matterport content unless licensed, and (c) no competing analytics product against Vexcel unless CoStar is the seller.
- The safe architecture is to sell derived, non-reconstructable attributes plus evidence links that open inside licensed viewers (Matterport/Vexcel viewers), rather than redistributing imagery.

### Gaps
- CoStar's actual data-licensing terms for third-party partner products were not found, and no public CoStar partner program was identified.
- The current Vexcel commercial customer agreement and partner terms were not retrieved (only the EULA). Whether CoStar-era Vexcel terms changed is unknown.

---

## 6. Go-to-market patterns

### Takeaway
Property-data vendors use a layered GTM: a free trial/sandbox or self-serve metered API for developers (Regrid, ATTOM 30-day trials, spend caps), negotiated annual enterprise licenses, and cloud-marketplace delivery (Snowflake Secure Data Share, Databricks Delta Share) for data teams. Insurance AI vendors sell top-down to carriers. Consolidators (Moody's, RealPage, CoStar) acquire AI data layers to embed them into existing workflows.

### Cited Findings
- Self-serve land: Regrid's free 30-day sandbox, monthly plans, and spend caps. ATTOM's 30-day free trial and $500/mo entry. — [Regrid support](https://support.regrid.com/reference/plan-options); [ATTOM pricing](https://www.attomdata.com/solutions/delivery/property-data-api/pricing/)
- Expand: annual contracts and bulk/cloud delivery via Snowflake and Databricks, negotiated with sales. — [ATTOM Snowflake FAQs](https://www.attomdata.com/solutions/delivery/cloud-delivery/snowflake/faqs/); [Cotality vs ATTOM](https://www.cotality.com/compare/cotality-vs-attom)
- Marketplace distribution precedent: CoreLogic joined the Snowflake Data Marketplace in Dec 2020, offering 99.9%+ US property coverage. — [BusinessWire 2020](https://businesswire.com/news/home/20201208005473/en/CoreLogic-Joins-Snowflake-Data-Marketplace-to-Provide-Further-Access-to-Unrivaled-Property-Data) **[old]**
- Agent marketplaces as a channel: Cherre's AI Agent Marketplace hosts third-party and native agents on connected owner/operator data, now inside RealPage. — [Cherre](https://blog.cherre.com/2025/10/31/introducing-cherre-ai-agent-marketplace/); [Thoma Bravo](https://thomabravo.com/press-releases/realpage-acquires-cherre)
- Strategic investors as channel: Cadastral's round included JLL Spark, with AvalonBay and Equity Residential reported. EliseAI's investors include a16z and Bessemer. — [Bisnow Cadastral](https://bisnow.com/national/news/proptech/cadastral-raises-95m-for-ai-platform-from-avalonbay-equity-residential-133110); [Bisnow EliseAI](https://www.bisnow.com/news/national/property-management/eliseai-raises-350m-funding-round-plans-automation-expansion)
- Insurance top-down: CAPE reached ~half of the top-50 US property insurers before Moody's bought it. — [Insurance Journal](https://www.insurancejournal.com/news/national/2025/01/13/807956.htm)
- AI chat as a lead channel: "AI chat is sending leads to Apartments.com," and Apartments.com partners with ChatGPT. — [Speedwell](https://www.speedwellmemos.com/p/costar-3q26-business-recap)

### Inferences
- For the hackathon pitch, a plausible GTM sequence:
  1. Land with one Houston vertical that has acute pain and a regulatory documentation need, e.g. P&C insurers on post-hurricane/flood re-underwriting, or CRE lenders on collateral condition.
  2. Deliver inside existing tools: CoStar/LoopNet property pages, ChatGPT/agent connectors, and Snowflake shares for carrier data teams.
  3. Expand to brokers (listing enrichment), owners (capex planning), and municipalities.
- Exit and partner logic: incumbents acquire rather than build (Moody's–CAPE, RealPage–Cherre, CoStar–Matterport/Vexcel). Position the product as a feature CoStar would ship.

### Gaps
- Verisk/Xactimate integration patterns (e.g., aerial measurement vendors feeding Xactimate) were not researched.
- Yardi, MRI, and Salesforce marketplace embedding was not researched.
- MetaProp, CRETI, a16z, and Bessemer proptech reports were not fetched, so there are no market-size figures here.
