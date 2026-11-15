# Data pilot: does the "lie detector" find real contradictions?

Run: Sat Nov 14, 2026, ~2:15–2:45 AM ET, by Asmit's Claude. 29 Houston non-apartment buildings (offices, industrial, flex, retail, hotels), 43 Matterport scans, 29 Vexcel property lookups, plus CoStar tenancies, suites and listings from the kit. Evidence images are in `evidence/`.

## Verdict

**Yes, real contradictions exist. But naive comparisons are mostly false alarms.** The checks only become trustworthy when you align dates and pick the right building. That alignment is the product.

## What the kit actually contains (bigger than we thought)

- 3,339 commercial properties (1,758 Houston), 10,492 Matterport scans, 74,093 tenancies (with suite + move-in/out dates), 1,022 listings with suite-level availability.
- 708 scans are named by suite or floor (400 in Houston, 334 properties), so the suite-level check can run automatically.
- **Vexcel Elements works with our key:** building footprints, structure count, roof condition, material and defects, rooftop AC units, vehicle counts and capture date. **Stories and roof height came back empty for all 29**, so those can't be checked from Vexcel attributes.
- **Matterport:** room areas, ceiling heights (often 0 for big open spaces) and downloadable 360° photos. The automatic room types are unreliable ("Breakroom" was classified as "Balcony"). `created` = 2026-11-10 on every scan (the date they were re-hosted), so **the real scan date is CoStar's attachment `originationDate`**.
- Most scans are single suites made to market vacant space, so "empty" is the default state of a scan.

## Confirmed contradictions

| # | Building | Records say | Evidence says | Sources |
|---|---|---|---|---|
| 1 | **1400 N Sam Houston Pkwy E, Suite 155** (Northgreen Business Center) | Commercial Drywall Contractors occupies Suite 155 (750 sf) **until Jul 23, 2026**; building recorded as 100% occupied | Scan dated **Mar 9–10, 2026** shows Suite 155 empty (door number "155" visible), marketed as "1,794 SF", with a listing floor plan | CoStar tenancy + Matterport photos + CoStar attachment date |
| 2 | **10607 Grant Rd** | 3,000 sf building, 2 stories | Its own tenant record says 3,636 sf occupied; the Vexcel footprint under the CoStar pin is 3,984 sf (one floor alone exceeds the total); the attached scan is "Suite 213 – 3,281 SF (**10601** Grant Road)", a multi-office suite | CoStar + Vexcel + Matterport |
| 3 | **1800 Sherwood Forest St** | GBA 24,567 sf but RBA and typical floor 18,000 sf on a 1-story building | Vexcel footprint 24,269 sf matches GBA; occupied 17,850 + available 7,800 = 25,650 sf, more than the 18,000 sf RBA | CoStar internal + Vexcel |
| 4 | **10402 Valley Forge Dr** | 3 stories, typical floor 4,732 sf, GBA 21,000 sf | 4,732 × 3 ≠ 21,000; the Vexcel footprint of 7,136 sf matches GBA ÷ 3 | CoStar internal + Vexcel |
| 5 | Scans attached to a different address | 4 of 29 sampled buildings | 9750 vs 9700 Tanner; 10601 vs 10607 Grant; 16821 vs 16903 Buccaneer; 16909 vs 16910 Rolling Creek | CoStar attachment captions vs. property address |
| 6 | Vexcel gap | One parcel at Northgreen holds 4 buildings | Elements returned 1 structure, 166 m from the CoStar pin | Vexcel vs. aerial photo |

## False alarms the engine must avoid (all explained by dates)

| Scan | Looked like | Actually |
|---|---|---|
| York Centre Suite 159 / 260 | Empty, but CoStar lists Manpower / OEG | Scanned Jan 2020; tenants moved in Jun 2023 / Jul 2020 |
| 10920 W Sam Houston Suite 100 | Empty, but AMOGY listed (9,453 sf) | Scanned Apr 5, 2023; AMOGY moved in May 1, 2023 |
| 1800 Sherwood Suite C-1A | Empty, but Cascade Showerworks listed | Scanned Oct 2025; tenant moved in Feb 2026 |
| Footprint 1.83× at Northgreen | Size mismatch | Compared the wrong building in a 4-building parcel |
| Towers (1415 Louisiana 2.1×, 1002 Noble Energy 4.3×) | Size mismatch | Probably podium or garage in the footprint; needs review |

## Agreement (controls)

- 16 of 29 building footprints are within ±20% of CoStar's floor size.
- 3 of 3 suite scans that matched a listing agree with CoStar's availability (Willow Place 315 at 1,382 sf, FM 1960 #3939, Wynnwood 9,900 sf).

## What this means for the pitch

- The "lie detector" holds, but the honest framing is **record freshness and integrity**, not "the lender's building is secretly empty". We have no multi-date parking evidence yet.
- Hit rate in this sample: 1 confirmed occupancy lag out of 9 suite checks; 3 size or structure record issues; 4–6 scans linked to the wrong building, out of 29 buildings.
- **The demo:** show the false alarm being cleared by the timeline (York Centre), then the real one (Suite 155 photo + CoStar record + dates). That proves the engine reasons rather than pattern-matches.
- **The scale claim:** 708 suite- or floor-named scans can be checked this way automatically.

## Caveats

- Small sample (29 buildings). The "scan date" is when CoStar attached it, so the actual capture could be a little earlier.
- The Suite 155 size disagreement may partly reflect different measurement standards.
- Vexcel point lookups use the CoStar pin, so parcels with several buildings need the pin-in-footprint match used here.
