# Adjacent (Non-CRE-Broker/Lender) Buyers of Fused Building Intelligence (records + interior 3D scans + high-res aerial), Houston focus — as of 2026-11-13

Research notes. About 24 tool calls (searches plus one failed fetch). Most findings come from search-result summaries of the cited pages. Only a few pages were opened in full, so the report writer should treat exact numbers as "reported by" the cited page. Items marked **[UNVERIFIED]** could not be tied to a primary page. Items marked **[DATED]** are older than 2025.

---

## Q1. Commercial property insurance (underwriting + claims): decisions, tools, cost, pain, willingness to pay (WTP), what fusion unlocks

### Takeaway
Insurance has the largest existing budget for third-party building data. Carriers already license aerial and AI property data (CAPE/Moody's, ZestyAI, Nearmap/Betterview, Verisk). They also spend on inspections that, by Verisk's own survey, mostly produce no underwriting action. The market context has changed. By 2026 the 2023–24 Texas "insurance crisis" has given way to a **soft commercial property market**: Q2 2026 premiums fell 6.3% and capacity is expanding. The pain has shifted from "can't get coverage" to "pricing and risk selection in a competitive market." That favours better COPE/ITV data, but it lowers the panic-driven urgency.

### Cited Findings
**Market state (2026: soft market)**
- CIAB Q2 2026 survey: commercial property premiums fell an average **6.3%**, the largest decrease of any line and a full year of decreases. **75%** of respondents reported increased property underwriting capacity, up from 72% in Q1. — [Insurance Journal, Aug 20 2026](https://insurancejournal.com/news/national/2026/08/20/882240.htm)
- CIAB Q1 2026 called it a "decisive sign of a softened market" (Q1 property decrease reported as 5.5% or 5.8%; the sources conflict). — [Insurance Journal, May 22 2026](https://amp.insurancejournal.com/news/national/2026/05/22/871041.htm)
- WTW: large commercial accounts saw their first price drop since 2017 (Q2 2026). — [Insurance Business](https://www.insurancebusinessmag.com/us/news/breaking-news/large-commercial-accounts-see-first-price-drop-since-2017-wtw-finds-589348.aspx)
- Marsh's Q2 2026 index reportedly showed US property rates down **13%** **[UNVERIFIED: from a search summary; the Marsh primary was not opened]**. — [Insurance Business](https://www.insurancebusinessmag.com/us/news/property/us-commercial-insurance-rates-split-as-property-falls-casualty-rises-594369.aspx)
- TWIA (Texas windpool) actuarial committee recommended **no rate change** for 2026 residential and commercial policies. — [Insurance Journal, Jul 2025](https://www.insurancejournal.com/news/southcentral/2025/07/15/831577.htm)

**Texas/Houston crisis evidence (2023–2024; still drives owner behaviour)**
- Houston multifamily insurance cost per unit rose **165%**, or **+$671/unit/yr** (Houston Chronicle). — [Houston Chronicle](https://www.houstonchronicle.com/politics/texas/article/affordable-housing-insurance-20180181.php) **[DATED, ~2024]**
- RealPage put Houston multifamily premiums above **$1,100/unit**. — [RealPage](https://www.realpage.com/analytics/soaring-insurance-premiums-hitting-apartment-owners/) **[DATED]**
- Bisnow Houston: high multifamily insurance "shut down the deal", threatening transactions and straining budgets. — [Bisnow Houston](https://www.bisnow.com/news/houston/multifamily/it-shut-down-the-deal-high-multifamily-insurance-rates-threaten-transactions-strain-budgets-122731) **[DATED]**
- National multifamily insurance per unit: **$502 (2021) to $777 (2024)**, +55% (NAA). — [NAA](https://naahq.org/news/premium-pulse-national-multifamily-insurance-cost-acceleration). The Federal Reserve's series is **~$465 (2019) to ~$821 (2024)** in real terms. — [Federal Reserve FEDS Note, Sep 2025](https://www.federalreserve.gov/econres/notes/feds-notes/rising-property-insurance-costs-and-pass-through-to-rents-for-apartment-buildings-accessible-20250919.htm)
- A ZestyAI and Logic Underwriters release (Feb 2026) says **Texas is the most expensive severe convective storm (hail/wind) market in the US**. — [FF News](https://ffnews.com/newsarticle/insurtech/logic-underwriters-adopts-zestyai-to-strengthen-texas-property-underwriting-with-ai-powered-hail-and-wind-models)
- Search results report that Gov. Abbott directed TDI on Aug 24 2026 to act on rising P&C costs, citing average homeowners premiums rising from under $2,000 (2020) to over $3,500 (2026). **[UNVERIFIED: primary press release not opened; concerns homeowners lines, not commercial]**

**Underwriting tools, vendors and inspection economics**
- Moody's agreed to acquire CAPE Analytics in Jan 2025. CAPE's geospatial AI covers residential and commercial properties, and CAPE says **nearly half of the top 50 US property insurers** use it. — [Business Wire](https://www.businesswire.com/news/home/20250113472182/en); [Insurance Journal](https://www.insurancejournal.com/news/national/2025/01/13/807956.htm)
- ZestyAI commercial adoptions: GenStar (Berkshire E&S) picked Z-STORM for hail/wind across its commercial portfolio (Jan 2026) — [FinTech Global](https://fintech.global/2026/01/30/genstar-partners-with-zestyai-to-sharpen-hail-risk-underwriting/). TruStage uses Z-HAIL, Z-FIRE and Z-PROPERTY for commercial (Dec 2025) — [FinTech Global](https://fintech.global/2025/12/22/trustage-adopts-zestyai-climate-analytics-for-commercial-property-underwriting/). Texas carrier Logic Underwriters uses Z-PROPERTY, Z-HAIL and Z-WIND for personal and commercial — [FF News](https://ffnews.com/newsarticle/insurtech/logic-underwriters-adopts-zestyai-to-strengthen-texas-property-underwriting-with-ai-powered-hail-and-wind-models). Z-PROPERTY runs AI over aerial imagery plus parcel data for roof condition and structural complexity. — [ZestyAI products](https://zesty.ai/products)
- Verisk: virtual inspections can cut average inspection cost by about **40%**, and a Verisk survey found **most inspections result in no underwriting action**. — [Verisk blog](https://www.verisk.com/blog/dynamic-duo-pairing-skilled-survey-professionals-with-virtual-technology-is-transforming-commercial-property-inspections/)
- CoreLogic/Cotality: a virtual survey takes about **15 minutes at about half the cost** of a physical inspection. — [CoreLogic whitepaper](https://corelogic.foleon.com/whitepapers/underwriting-inspection-workflow-optimization-maturity-model/capability-dimension-1-inspection-type-used)
- Historical benchmark: carriers spent about **$190M/yr** on inspection programs, at **$25–35 per inspection** (residential-weighted). — [Insurance Journal 2011](https://www.insurancejournal.com/magazines/mag-features/2011/11/07/222983.htm) **[DATED, 2011; likely understates current commercial loss-control costs]**

**Insurance-to-value (ITV) / underinsurance** (only UK data found)
- Gallagher: about **46%** of UK commercial properties are underinsured, with an average shortfall of **40%**; 37% of claims managers blame owners not revaluing. — [Insurance Times](https://www.insurancetimes.co.uk/news/nearly-half-of-commercial-properties-remain-underinsured-gallagher/1453141.article)
- Aviva (Mar 2026): only **7%** of UK properties are correctly insured, and the average underinsured property is covered for **67%** of rebuild cost. — [Insurance Times](https://www.insurancetimes.co.uk/news/underinsurance-rife-as-just-7-of-properties-covered-adequately/1456534.article)

**Claims / CAT response (Houston, Hurricane Beryl, Jul 2024)**
- Nearmap captured, processed and published post-Beryl imagery **within 36 hours** of landfall, with AI classifying damage into 5 FEMA tiers. Insurers used it to triage claims (vendor claim). — [Nearmap white paper](https://www.nearmap.com/white-papers/hurricane-beryl-insurance)
- Civil Air Patrol flew **22 imagery flights** for FEMA damage assessment by Jul 12 2024. — [CAP News](https://www.cap.news/p/texas-wing-provides-beryl-impact-imagery)

### Inferences
- **Fit is the strongest of any vertical.** COPE has four parts:
  - Construction and Exposure are partly visible from aerial imagery, which incumbents already sell.
  - **Occupancy** (who the tenant is and what they do, e.g. restaurant vs. office) comes from records and leases.
  - **Protection** (sprinklers, alarms, interior hazards) needs interior data.
  - Aerial-only vendors (CAPE, Zesty, Nearmap) cannot see Occupancy or Protection. A fused records + interior + exterior file therefore fills exactly the gap that today requires a physical loss-control visit.
- ITV/replacement-cost estimating needs floor area, story count, finish quality and construction class. Interior scans plus records give these directly.
- Claims: a pre-loss interior and exterior baseline lets an adjuster tell new storm damage from pre-existing wear. That is a major dispute driver in Texas hail claims. **[Inference; no Texas-specific dispute statistic found]**
- Go-to-market: incumbents (Verisk, Moody's/CAPE, Cotality, EagleView, Nearmap) are entrenched. The likely entry points are (a) E&S/MGA carriers writing Texas commercial, such as GenStar and Logic, and (b) **owner-side** use: insureds and brokers presenting a "verified building dossier" to win better terms. Owner-side demand is plausibly stronger in a soft market, when carriers compete for well-documented risks.

### Gaps
- No current (2024–26) US per-inspection cost for commercial loss-control surveys. Industry lore puts it at a few hundred dollars per survey **[UNVERIFIED]**.
- No US commercial ITV/underinsurance statistic (only UK).
- No Houston commercial (non-multifamily) premium trend data for 2025–26.
- Not researched: Xactimate pricing, Hover/EagleView commercial claims pricing, desk-adjusting adoption rates.
- CAPE/Zesty pricing is not public.

---

## Q2. Property tax assessment and appeals (HCAD, Houston)

### Takeaway
Both sides of the Houston property-tax fight already pay for building imagery and evidence. HCAD buys oblique aerial imagery (sole-source EagleView, about $750–800K/yr reported) and street-level imagery (Cyclomedia, described as "a step toward a digital twin"). Commercial appeal firms like O'Connor charge **contingency fees of up to 50% of first-year tax savings**. Interior condition, functional obsolescence and lease/rent-roll evidence are what win commercial appeals, and none of these is visible from the air.

### Cited Findings
- HCAD 2026 reappraisal: commercial values up about **1.7%** over 2025 noticed values, with noticed value rising about $5B to about **$269B** (summary wording is ambiguous on whether $269B is the commercial total). — [HCAD 2026 Reappraisal Values](https://hcad.org/hcad-resources/reappraisal/2026-reappraisal-values); [HCAD PDF](https://hcad.org/assets/uploads/pdf/26-07-Reappraisal-Values.pdf)
- HCAD 2026 market trends page. — [HCAD](https://hcad.org/hcad-resources/reappraisal/2026-market-trends) (not opened)
- HCAD board materials (2019) mention the fifth-year purchase of a **six-year sole-source contract with EagleView (Pictometry)** for digital oblique imagery and self-hosting. — [HCAD 2019 board document](https://hcad.org/assets/uploads/pdf/resources/2019/RFP2019-08-Restroom-Remodel-Award.pdf) **[DATED]**
- HCAD aerial photo spending was reportedly **$800,000 (2023)** and **$750,000 (2024)** (secondhand, via O'Connor). — [O'Connor HCAD 2024 summary](https://www.poconnor.com/Harris-county-texas-property-tax-2024); [2023](https://www.poconnor.com/Harris-county-texas-property-tax-2023)
- HCAD + Cyclomedia (street-level imagery) presentation titled "a Step Toward Making a Digital Twin" (H-GAC). — [H-GAC PDF](https://h-gac.com/getmedia/b9c3e59d-4ac0-4808-a971-f4459153c75a/HCAD_Cyclomedia_aStepTowardMakingDigitalTwin_HGAC_compressed)
- Neighbouring districts also procure imagery: Fort Bend CAD RFP for turnkey oblique and ortho imagery — [FBCAD](https://www.fbcad.org/request-for-proposal-rfp-for-digital-aerial-oblique-orthogonal-imagery/); Bexar CAD 2026 aerial ortho RFP — [BCAD PDF](https://bcad.org/wp-content/uploads/2026/06/Aerial-Ortho-RFP-2026.pdf)
- O'Connor's services agreement: contingency fee = **50% of estimated tax savings**, or 25% after a disaster exemption. O'Connor bears the cost of judicial appeals, including legal and expert-witness fees, for commercial accounts. — [O'Connor Terms PDF, 2023](https://www.poconnor.com/wp-content/uploads/2023/06/Our-Terms.pdf)
- O'Connor says its commercial division covers **nearly 10,000 commercial properties** (promotional). — [O'Connor deck on Issuu](https://issuu.com/oconnor2023/docs/commercial_property_tax_program_o_connor)
- The 2026 protest deadline was May 15, or 30 days after the notice (secondary source). — [HCAD deadline reminder PDF](https://hcad.org/assets/uploads/pdf/26-08-Protest-Deadline-Reminder.pdf)

### Inferences
- **Appeal firms are the higher-WTP buyer.** The fee is a share of savings, and the firm pays for experts in judicial appeals. Evidence that wins more or larger reductions converts directly into revenue. Illustrative arithmetic (rough Harris County ~2.0–2.5% effective commercial tax rate assumed, **[UNVERIFIED]**): on a $20M office, a 5% value reduction saves roughly $20–25K/yr in tax, and a 50% fee yields about $10–12K to the firm. A $1–3K building dossier pays back easily if it lifts win rates.
- Arguments that need **interior and records data**:
  - Interior condition and deferred maintenance (physical depreciation).
  - Functional obsolescence (outdated floor plates, column spacing).
  - Vacancy and below-market leases from rent rolls (income approach).
  - Measured net rentable area vs. HCAD's recorded square footage.
- Appraisal districts are a second buyer. HCAD's step from EagleView obliques to Cyclomedia street-level, framed as a "digital twin", shows appetite. But procurement is RFP- and sole-source-driven and slow.
- The Texas annual reappraisal plus protest cycle (HCAD runs one every year) creates **recurring** demand, unlike one-time transactions.

### Gaps
- Number of 2025/2026 HCAD commercial protests and the share settled informally vs. ARB vs. litigation was not found. HCAD's annual report would have it.
- HCAD's current (2025–26) imagery vendor and contract value were not confirmed.
- Commercial contingency fee norms at other Houston firms (e.g., Popp Hutcheson, Ryan, Marvin Poer) were not researched.

---

## Q3. Public safety / fire departments (pre-incident planning, HFD)

### Takeaway
Fit is excellent: pre-plans are literally a fusion of an interior layout, exterior access and hydrants, and occupancy/hazard records. Department budgets are small, from **$800/yr** (small-town FlowMSP) to about **$118K/yr** (Fresno's First Due RMS, 3 years for $354K). In Houston, however, **building owners** of high-rises (>75 ft) must produce fire safety plans under HFD LSB Standard No. 07 (effective 1/1/2024). That shifts the payer to owners and property managers.

### Cited Findings
- NFPA 1660 consolidates NFPA 1600, 1616 and 1620. Its pre-incident planning content is largely carried over from 1620, and it does **not mandate software** but points to accessible, current, interoperable data (vendor blog). — [Emergent](https://www.emergent.tech/blog/nfpa-1660)
- First Due's pre-incident planning is integrated into inspection workflows; customers include **Fort Worth, Seattle, New Orleans**. — [First Due](https://www.firstdue.com/products/preincidentplanning)
- Fresno approved a 3-year, **$354,000** First Due records-management contract (Dec 2024). — [Fresno legislation ID 24-1572](https://agendas.fresno.gov/pa/legislation/id-24-1572-18859)
- Fairbury (small city) approved FlowMSP pre-incident planning at **$800/yr** (date unclear). — [Fairbury News](https://fairburynews.net/post/planning-proposal-approved)
- Memphis invested in FlowMSP + Hexagon (2022). — [FlowMSP blog](https://flowmsp.com/blog/memphis-fire-department-announcement/)
- A Tyler Tech case study describes a department completing **200 pre-plans in three weeks**, implying that throughput is the bottleneck. — [Tyler Technologies](https://tylertech.com/resources/case-studies/fire-department-completes-200-pre-plans-in-three-weeks)
- Esri offers a Pre-Incident Planning solution within ArcGIS (bundled for agencies already licensing ArcGIS). — [ArcGIS Solutions](https://doc.arcgis.com/en/arcgis-solutions/reference/introduction-to-pre-incident-planning.htm)
- **Houston:** HFD LSB Standard No. 07 "High-Rise Fire Safety Plans", effective 01/01/2024, applies to all high-rises (top floor >75 ft above fire access). **Owners and managers of office, residential and hotel high-rises must create fire safety plans.** — [Houston Permitting Center PDF](https://www.houstonpermittingcenter.org/media/9111/download)
- HFD publishes a High-Rise Survey Checklist (form 27), safety plan templates and a "High-Rise Triad" program. — [HFD business information](https://cohips.houstontx.gov/fire/business-information/index.html)
- Houston Fire Code Appendix J: retroactive high-rise sprinkler ordinance. — [Houston Permitting Center PDF](https://www.houstonpermittingcenter.org/media/1976/download)
- A 2016 Houston Chronicle piece ("Prevention efforts falling short") described HFD pre-incident plans produced through firefighter visits plus Life Safety Bureau inspections. — [PressReader / Houston Chronicle 2016](https://www.pressreader.com/usa/houston-chronicle-sunday/20160918/284636076844940) **[DATED]**

### Inferences
- A fused model auto-generates most of an NFPA 1620/1660 pre-plan:
  - Floor plans, stairwells, standpipes and FDC locations from the interior scan.
  - Roof access and apparatus staging from aerial imagery.
  - Occupancy and hazardous-tenant info from records and leases.
- Houston route: sell high-rise **owners** a compliant LSB Std 07 fire safety plan package, then share the data with HFD for free or cheaply. HFD gets better data at no budget cost, and the owner gets compliance plus a data asset reusable for insurance (Q1).
- Selling directly to fire departments has low per-account revenue and grant-dependent budgets (e.g., FEMA AFG). It is good for credibility and pilots, weak as a revenue base.

### Gaps
- HFD's current pre-plan software vendor was not found (HFD has used ESO/other RMS; unconfirmed).
- Zonehaven (now Genasys) is evacuation-zone focused, not interior; not researched further.
- No data on the number of Houston high-rises subject to LSB Std 07 or compliance rates.
- The indoor-navigation-for-responders market (e.g., NIST/DHS programs) was not researched.

---

## Q4. Municipal planning, code enforcement, permitting, building performance, disaster recovery

### Takeaway
Houston is a weak buyer for a building-performance-standard (BPS) use case. It has **no private-building energy benchmarking mandate**; its 2022 policy covers only municipal buildings, and Texas state preemption constrains local building rules. Disaster damage assessment is served by aerial imagery (Nearmap, CAP). Flood buyouts are overwhelmingly residential. Code enforcement and unpermitted-construction detection via aerial change detection are plausible but undocumented for Houston in this research.

### Cited Findings
- Houston's 2022 Municipal Building Decarbonization and Benchmarking Policy covers city-owned buildings only. City benchmarking covers about **400 properties, ~10M sq ft**. — [Texas Comptroller SECO case study](https://Comptroller.Texas.Gov/programs/seco/docs/benchmark-houston.pdf)
- ACEEE 2024 City Clean Energy Scorecard ranks Houston **34 of 75** and recommends it adopt energy benchmarking and retro-commissioning policies (i.e., none exists for private buildings). — [ACEEE Houston one-pager](https://www.aceee.org/sites/default/files/pdfs/2024_City_Scorecard_OnePagers/Houston.pdf)
- In-state precedent: Austin's ECAD ordinance requires commercial buildings ≥10,000 sq ft (Austin Energy customers) to benchmark annually. — [Albireo Energy](https://www.albireoenergy.com/texas-energy-benchmarking)
- Texas Gov. Code 3000.002 restricts local building rules; HB 1360 (89th Leg.) addresses exceptions for energy efficiency (final status unverified). — [Texas Policy Research](https://www.texaspolicyresearch.com/bills/89th-legislature-hb-1360/)
- Houston flood buyouts: Harris County has acquired **4,000+ homes** since 2000 — [Route Fifty/Grist, May 2024](https://route-fifty.com/infrastructure/2024/05/texas-flooding-brings-new-urgency-houston-home-buyout-program/396478). Along the San Jacinto, about 2,400 candidate properties, of which ~800 bought; approvals can take **18+ months**. — [Click2Houston/Texas Tribune, May 2024](https://www.click2houston.com/news/texas/2024/05/20/the-government-wants-to-buy-their-flood-prone-homes-but-these-texans-arent-moving/) **[DATED]**
- Texas GLO Q1 2025 report: Harris County voluntary buyouts ~$11.8M drawn of $12.7M budget; mandatory buyouts ~$14.4M of $14.6M. — [GLO PDF](https://www.glo.texas.gov/sites/default/files/2025-05/hh57m-2025-q1.pdf)
- FEMA's Beryl preliminary damage assessment (DR-4798) record. — [FEMA PDA PDF](https://fema.gov/sites/default/files/documents/PDAReport_FEMA4798DRexpedited-TX.pdf)
- Nearmap markets Beryl imagery to government for damage assessment. — [Nearmap gov white paper](https://nearmap.com/white-papers/hurricane-beryl-government)
- The City of Houston had a Nearmap "Interactive Aerial Imagery Technology" presentation to a council committee (TTI, Apr 2023). The PDF now returns 404, so its content is unverified. — [houstontx.gov (404)](https://311.houstontx.gov/council/committees/tti/20230406/NearMap-Interactive-Aerial-Imagery-Technology.pdf)

### Inferences
- Municipal buyers are low-priority for a commercial-building fusion product in Houston:
  - No BPS mandate.
  - Residential-dominated buyouts.
  - Aerial-only vendors already serve disaster and code-enforcement imagery.
- One exception may be the **permitting/plan-review side**: as-built interior scans could speed alteration permits. Not researched.

### Gaps
- No Houston-specific data on unpermitted construction detection programs or their recovered revenue.
- No Houston commercial-building FEMA public assistance damage figures.

---

## Q5. Utilities / telecom / energy services (EV charging, solar, 5G, audits, data centers)

### Takeaway
Data centers are the high-budget story in Houston (CenterPoint reportedly expects about 8 GW of data-center load by 2029). However, their siting decisions are driven by power, land and fiber, not by interior scans of existing buildings, so fit is moderate. EV, solar, 5G and energy-audit use cases were not well covered in this round.

### Cited Findings
- ERCOT forecasts demand could roughly **quadruple by 2032** (ABC13). — [ABC13](https://abc13.com/post/ercot-expects-energy-demand-quadruple-2032/18908223/)
- The following were reported in search results and attributed to a Houston energy outlet; individual primary sources were not opened **[UNVERIFIED]**. — [EnergyCapitalHTX tag page](https://energycapitalhtx.com/tag/data-center-boom)
  - CenterPoint: **12.2 GW** "firmly committed" new industrial load in its Houston territory; expects to energize **8 GW of data-center load by 2029**.
  - CBRE: Houston had **154 MW** of data-center capacity in H2 2025, with 28.5 MW under construction.
  - Serverfarm: a planned 250-acre, **500+ MW** campus near Houston.
- ERCOT large-load interconnection queue: about **226 GW** (Nov 2025), ~73% data centers; another source cites 420,812 MW of data-center requests (Jun 2026). These are requests, not forecasts **[UNVERIFIED primary]**. — [Bloomberg Gov Texas Brief](https://news.bgov.com/texas-brief/texas-sees-power-demand-more-than-tripling-from-record-by-2032)
- Texas regulators are moving toward a new vetting process for large-load (data center) requests. — [ABC13](https://abc13.com/story/data-centers-seek-tap-texas-energy-regulators-are-close-approving-new-vetting-requests/19322360/)

### Inferences
- Plausible sub-niche: **conversion screening**. This means identifying existing Houston industrial/office buildings (via records + aerial: roof area, substation proximity, floor loading from scans) for edge data centers, battery storage or rooftop solar.
- Audits/electrification: ASHRAE Level 1–2 energy audits need floor area, envelope, HVAC and lighting inventories, which interior scans supply. But in Houston there is no mandate driving demand (see Q4).

### Gaps
- No research done on EV charging siting buyers, rooftop solar installers' use of aerial plus interior data, or 5G small-cell siting. Treat these as open.
- No pricing for energy audits or utility programs (e.g., CenterPoint commercial efficiency incentives).

---

## Q6. Construction/AEC and facilities management (as-builts, fit-out estimating, capital planning, deferred maintenance)

### Takeaway
There is large, documented pain in institutional real estate. Higher-education deferred capital renewal reached **$156 per gross sq ft** in 2026 (Gordian, +8% YoY), and the national backlog is estimated at **$112B–$197B**. Interior scanning is cheap (roughly **$0.05–$0.50/sq ft**), so a fused dossier per building can be priced well below a traditional facility condition assessment (FCA). Houston anchors include the Texas Medical Center, UH and Rice (not researched individually).

### Cited Findings
- Gordian 2026 State of Facilities: deferred capital renewal **$156/GSF**, up 8% YoY and about double 2008 levels. — [Spaces4Learning, Apr 2026](https://spaces4learning.com/articles/2026/04/09/gordian-state-of-facilities-report.aspx?p=1); [Higher Ed Dive](https://www.highereddive.com/news/colleges-facilities-renovations-backlog-campus-operations-gordian/817143/)
- APPA/national higher-education backlog cited at **$112B** — [Spaces4Learning, Oct 2025](https://spaces4learning.com/Articles/2025/10/02/Breaking-Higher-Educations-Billion-Dollar-Backlog-Problem.aspx); a range of **$100B–$197B** depending on methodology — [AcademicJobs](https://www.academicjobs.com/higher-education-news/college-renovations-backlog-hits-record-dollar156gsf-or-academicjobs-12671)
- FCI (deferred maintenance ÷ replacement value) benchmarks of 0–5% good, 5–10% fair, 10–30% poor, 30%+ critical (vendor guide; indicative). — [Oxmaint](https://oxmaint.com/industries/education/capital-planning-from-asset-health-troubleshooting-handbook-for-private-universities)
- Matterport-style commercial scans:
  - **$0.20–$0.50+/sq ft**, with a minimum project fee of **$400–$750**; add-ons (E57 point cloud, floor plans) cost **$50–$250+** per space. — [The Future 3D, Mar 2026](https://www.thefuture3d.com/blog-0/2026/3/1/matterport-pricing-guide-2026/)
  - Commercial building scanning at **$0.05–$0.20/sq ft**; Pro3 camera from about **$3,995–$5,400**. — [3DMag 2026](https://www.3dmag.com/3d-scanners/3d-laser-scanner-for-buildings-price-2026/)

### Inferences
- Value proposition: "FCA-lite" plus as-built.
  - The scan gives measured areas and asset/finish inventory.
  - Aerial gives roof condition and roof-area change over time.
  - Records give age, renovation permits and tenancy.
- Buyers: university facilities offices, hospital systems, school districts (HISD), and corporate FM / outsourcers (JLL, CBRE, Cushman integrated facilities management).
- For fit-out estimating, general contractors and brokers already order scans per job. The fused product's edge is pre-existing scans across many buildings, so estimating can start before site access.
- Unit economics: scanning 100K sq ft at $0.10–0.30/sq ft costs **$10–30K**. That is small relative to a campus capital plan, but it must beat existing FCA vendors (Gordian, Accruent/VFA, Bureau Veritas, not priced here).

### Gaps
- No hospital/healthcare deferred-maintenance or FCA pricing data found.
- No pricing found for traditional FCAs (rule of thumb ~$0.10–0.30/sq ft **[UNVERIFIED]**).
- No Houston-specific institution backlog figures (e.g., UH, HISD bond program, TMC).
- Space-utilization sensor market (e.g., occupancy analytics) not researched.

---

## Q7. Retail/logistics site selection, last-mile delivery/robotics, accessibility (ADA)

### Takeaway
**Texas is not a top ADA Title III lawsuit state.** It ranked about 7th with **177 federal filings in 2025** (down from 224 in 2024). California, Florida and New York dominate. Texas does, however, have a **state-mandated accessibility inspection market**: the Texas Architectural Barriers Act (TABA) requires any commercial or public project ≥$50,000 to register with TDLR and pass Registered Accessibility Specialist (RAS) plan review and on-site inspection. That created **24,856 project registrations in FY25** handled by only **594 RASs**. Retail/logistics and last-mile robotics were not researched in depth.

### Cited Findings
- Seyfarth: federal ADA Title III filings totalled **8,667 in 2025** (−2% YoY). Top states: CA 3,252; FL 1,823; NY 1,471; IL 659; MO 183; MN 179; **TX 177**. — [JD Supra / Seyfarth](https://www.jdsupra.com/legalnews/ada-title-iii-federal-lawsuit-filings-2632226/); [Mondaq](https://www.mondaq.com/unitedstates/constitutional-administrative-law/1745806/ada-title-iii-federal-lawsuit-filings-fall-slightly-to-8667-in-2025)
- 2024: about **8,800** federal Title III filings; Texas **224** (4th in one ranking). — [Mondaq / Seyfarth 2024](https://www.mondaq.com/unitedstates/trials-appeals-compensation/1615434/ada-title-iii-federal-lawsuit-numbers-rebound-to-8800-in-2024)
- Seyfarth counts only federal filings; state-court data is unreliable. — same sources.
- TABA/TDLR: projects with estimated cost **≥$50,000** must register with TDLR and receive RAS plan review plus post-construction inspection; local jurisdictions may require it below $50K. TDLR fact sheet: **594 RASs; 24,856 project registrations (FY25)**. — [TDLR EAB at a Glance](https://www.tdlr.texas.gov/media/pdf/EAB%20at%20a%20Glance.pdf)
- RAS fees are set by the RAS (market-priced). TDLR fees: $175 project filing; $300 RAS application. — [TDLR AB fee schedule](https://www.tdlr.texas.gov/ab/abfees.htm)

### Inferences
- A fused interior scan (door widths, clearances, ramp slopes, restroom layouts) plus exterior aerial (parking, accessible routes, curb ramps) could pre-screen TAS/ADA compliance. Buyers would be:
  - Multi-site retailers and landlords facing demand letters.
  - RAS firms. With about 42 projects per RAS per year (24,856/594), they are capacity-constrained.
- Pain intensity is moderate in Texas (lawsuit volume about 1/18th of California's), but TABA compliance is mandatory and recurring with every alteration.
- Last-mile/robotics: entrance, dock and loading-zone geometry from fused data is plausibly valuable to delivery and robotics firms, but **no evidence was gathered**.

### Gaps
- Retail site-selection vendor landscape (Placer.ai, SiteZeus, Buxton) and pricing were not researched.
- No evidence on last-mile delivery or robotics companies buying building-entrance data.
- Texas state-court ADA filing counts are unavailable.
- Typical RAS inspection fees were not found.

---

## Q8. Ranking: pain intensity × budget × fit (Houston lens)

### Takeaway
Ranked: (1) commercial P&C insurance, both carrier underwriting and owner-side "verified building dossier"; (2) commercial property-tax appeal firms; (3) institutional facilities/capital planning; (4) high-rise fire-safety-plan compliance (owner-paid) bundled with fire-department pre-plans; (5) accessibility/TABA pre-screening; (6) data-center/energy conversion screening; (7) municipal code/BPS; (8) flood buyouts. Insurance and tax appeals score highest because each has a proven, recurring line item already being spent on building data or evidence, and their missing data (occupancy, protection, interior condition, leases) is exactly what aerial-only incumbents cannot supply.

### Cited Findings
(Scores are the researcher's judgement, synthesized from the cited findings above; scale 1–5.)

| Rank | Vertical | Pain | Budget/WTP | Fit (inside+outside+records) | Key evidence |
|---|---|---|---|---|---|
| 1 | Commercial P&C insurance (underwriting, ITV, claims; carrier + owner-side) | 4 (2026 soft market reduces urgency; Texas SCS losses still highest) | 5 | 5 | [CIAB Q2 2026](https://insurancejournal.com/news/national/2026/08/20/882240.htm); [CAPE ~half of top-50 insurers](https://www.businesswire.com/news/home/20250113472182/en); [Verisk: most inspections → no action](https://www.verisk.com/blog/dynamic-duo-pairing-skilled-survey-professionals-with-virtual-technology-is-transforming-commercial-property-inspections/); [TX most expensive SCS market](https://ffnews.com/newsarticle/insurtech/logic-underwriters-adopts-zestyai-to-strengthen-texas-property-underwriting-with-ai-powered-hail-and-wind-models) |
| 2 | Property-tax appeals (firms + owners), secondarily HCAD | 4 (annual cycle) | 4 (50% contingency) | 4 | [O'Connor 50% fee](https://www.poconnor.com/wp-content/uploads/2023/06/Our-Terms.pdf); [HCAD EagleView](https://hcad.org/assets/uploads/pdf/resources/2019/RFP2019-08-Restroom-Remodel-Award.pdf); [HCAD Cyclomedia digital twin](https://h-gac.com/getmedia/b9c3e59d-4ac0-4808-a971-f4459153c75a/HCAD_Cyclomedia_aStepTowardMakingDigitalTwin_HGAC_compressed) |
| 3 | Institutional FM / capital planning (universities, hospitals, K-12) | 4 | 4 (slow procurement) | 4 | [Gordian $156/GSF](https://spaces4learning.com/articles/2026/04/09/gordian-state-of-facilities-report.aspx?p=1) |
| 4 | Fire: high-rise fire safety plans (owner-paid) + FD pre-plans | 3 | 2 (FD) / 3 (owner) | 5 | [HFD LSB Std 07](https://www.houstonpermittingcenter.org/media/9111/download); [FlowMSP $800/yr](https://fairburynews.net/post/planning-proposal-approved); [Fresno First Due $354K/3yr](https://agendas.fresno.gov/pa/legislation/id-24-1572-18859) |
| 5 | Accessibility (TABA/RAS, ADA) | 3 | 2–3 | 3 | [TDLR 24,856 registrations/594 RAS](https://www.tdlr.texas.gov/media/pdf/EAB%20at%20a%20Glance.pdf); [TX 177 ADA suits 2025](https://www.jdsupra.com/legalnews/ada-title-iii-federal-lawsuit-filings-2632226/) |
| 6 | Data centers / energy / solar / EV | 3 | 5 | 2 | [ERCOT demand ×4 by 2032](https://abc13.com/post/ercot-expects-energy-demand-quadruple-2032/18908223/) |
| 7 | Municipal code / BPS / permitting | 2 (no Houston mandate) | 2 | 3 | [ACEEE Houston](https://www.aceee.org/sites/default/files/pdfs/2024_City_Scorecard_OnePagers/Houston.pdf) |
| 8 | Flood buyouts / FEMA | 3 | 2 | 1 (residential, aerial suffices) | [Route Fifty](https://route-fifty.com/infrastructure/2024/05/texas-flooding-brings-new-urgency-houston-home-buyout-program/396478) |

### Inferences
- **The best wedge is cross-sell from a single scan.** One owner-commissioned fused dossier for a Houston high-rise can serve four uses: (a) the LSB Std 07 fire safety plan, (b) an insurance submission (COPE + ITV), (c) property-tax appeal evidence and (d) a capital plan. That spreads the scan cost across several budgets. The building owner or property manager is the natural payer, with carriers, tax firms and HFD as data consumers.
- **Timing risk in insurance:** with 2026 commercial property rates falling, carriers face less urgency to adopt new data, but more pressure to select risks well. Owners have less pain than in 2023–24 but now have leverage to shop terms with better data.
- **Competitive risk:** aerial incumbents (EagleView, Nearmap, Moody's/CAPE, Verisk, ZestyAI) already own the exterior layer. Defensibility comes from the interior and records fusion plus Houston-local coverage density, not from imagery itself.

### Gaps
- Scores are qualitative. No customer interviews or direct pricing quotes were obtained for insurance data products, appeal-firm evidence budgets or HFD.
- Healthcare campuses (Texas Medical Center), retail/logistics, last-mile robotics, EV/solar/5G and Houston unpermitted-construction detection were not investigated in this round. They should be covered before finalizing the ranking.
