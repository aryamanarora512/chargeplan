# Market sizing: TAM / SAM / SOM (first pass)

*2026-10-26. Desk research only. Every number is labeled **[Sourced]** (cited) or **[Assumption]** (our estimate,
untested). There is no customer or revenue data yet.*

## Summary

- **US small-fleet charge planning, as ChargePlan scopes it, is a small market today.** Serviceable market (SAM):
  roughly **$0.03M–$4.4M per year** (mid case ≈ $0.45M, about 1,250 depots). That's a useful product niche, not a
  venture-scale standalone business, on current evidence.
- **The big "EV charging software" market reports ($1.5–2.8B) are not our market.** Most of that money is public charging
  networks and charger-control software sold with hardware.
- **Timing headwind:** the US commercial clean-vehicle tax credit (45W) ended for vehicles acquired after Sept 30, 2025.
  US electric van sales fell to almost 6,000 in 2025, less than half of 2024.
- **The most promising expansion paths** are (1) a sizing tool for utility advisors and installers, and (2) markets
  outside the US, where most electric vans are sold. Both are untested.

## What exactly are we sizing?

**Product:** software that plans overnight depot charging and answers "will every vehicle be ready, at what modeled
cost, and at what power level?" It **does not control chargers**.
**Geography:** United States. **Unit:** annual software subscription revenue. **Price basis:** per EV per year.

## Why not just quote the big market reports?

| Report (category) | Size | Why it isn't our TAM |
|---|---|---|
| Spherical Insights: EV charging management software platforms | ~$2.06B (2025), ~30.7% CAGR to 2035 | Global, and mostly public-charging operator software |
| ResearchAndMarkets (via Business Wire): same category | ~$2.8B | Same |
| IMARC: same category | ~$1.5B (2024) | Same |
| Meticulous Research: EV fleet management | ~$9.28B (2025) | Includes telematics and hardware, worldwide |

**[Sourced]** These show the *category* is real and growing. They disagree with each other by almost 2×, and none
isolates small-fleet depot planning. Using them as our TAM would be "top-down inflation." We build bottom-up instead.

## Anchors from public data

| Fact | Source |
|---|---|
| US electric light commercial vehicle (van) sales were **more than 25,000 in 2024**, up 55%; Rivian held 40% of that market | **[Sourced]** IEA Global EV Outlook 2025 |
| US electric van sales were **almost 6,000 in 2025**, less than half of 2024, after the commercial tax credit ended (Sept 2025). *2025 figures use a new classification that moves vans over 3.5 t into trucks.* | **[Sourced]** IEA Global EV Outlook 2026 |
| US electric medium/heavy truck sales were **17,000 in 2025**, including nearly 10,000 Rivian delivery vans tied to its Amazon partnership | **[Sourced]** IEA Global EV Outlook 2026 |
| **268 fleet operators** have ordered at least **198,000** electric medium/heavy vehicles (Class 2B–8) since 2017; electric is ~0.6% of Class 4–8 sales (Q1 2025) | **[Sourced]** Atlas EV Hub |
| EVs are ~2.1% of all US vehicles in operation (Q1 2025) | **[Sourced]** Alliance for Automotive Innovation |
| Worldwide electric van sales topped **430,000 in 2025** (+45%) | **[Sourced]** IEA Global EV Outlook 2026 |
| Comparable software prices: €6.90–€9.90 per charge point per month (full charging-management platform with load balancing); about €30–40 per vehicle per month (fleet charging plus dispatch, per a news report) | **[Sourced]** Vaylens pricing; TechCrunch on Guided Energy |
| No public count exists of US fleets with 3–10 EVs at one depot | Our search found none |

**What the anchors imply:** US fleet EV adoption is **concentrated in a few very large fleets.** 198,000 vehicles across
268 operators averages over 700 per operator, and one partnership (Rivian–Amazon) drives a large share of US electric
delivery-van sales.
Small fleets are the long tail, and they are the least-measured part of the market.

## The model

```
TAM = N × p                                   all US depot-charged fleet EVs × annual price per EV
SAM = TAM × s_small × s_need × s_open         share in 3–10 EV single-depot fleets
                                              × share where scheduling or sizing changes outcomes
                                              × share not already served by bundled or free tools
SOM = SAM × capture                           what a tiny team could win in ~3 years
```

| Parameter | Low | Mid | High | Basis |
|---|---:|---:|---:|---|
| N: US fleet EVs that charge at a depot | 100,000 | 200,000 | 300,000 | **[Assumption]** order of magnitude from the IEA sales and Atlas order anchors. **The weakest number; replace it with purchased vehicles-in-operation data.** |
| p: price per EV per year | $30 | $60 | $120 | **[Assumption]** $2.50–$10 per EV per month, below full charging-management platforms because ChargePlan doesn't control chargers |
| s_small: share in 3–10 EV single-depot fleets | 10% | 15% | 25% | **[Assumption]** adoption is concentrated in large fleets |
| s_need: share where scheduling or sizing matters | 30% | 50% | 70% | **[Assumption]** see "when the problem is real" in [problem-analysis.md](problem-analysis.md) |
| s_open: share not covered by bundled or free tools | 30% | 50% | 70% | **[Assumption]** vehicle-maker, charger, and telematics suites plus free utility advisors |
| capture (3 years) | 0.5% | 2% | 5% | **[Assumption]** a solo developer with no sales team |

**Results** (6 EVs per depot assumed for depot counts):

| | Low | Mid | High |
|---|---:|---:|---:|
| **TAM** | $3.0M/yr | $12.0M/yr | $36.0M/yr |
| **SAM** | $27k/yr · 900 EVs · ~150 depots | **$450k/yr · 7,500 EVs · ~1,250 depots** | $4.41M/yr · 36,750 EVs · ~6,100 depots |
| **SOM** | ~$135/yr · ~1 depot | ~$9k/yr · ~25 depots | ~$220k/yr · ~300 depots |

**Value check.** Will customers pay p? In the PG&E example in [problem-analysis.md](problem-analysis.md), right-sizing
saves about **$447/yr for 6 vans, or about $74 per EV per year** **[Model]**. A $60/EV price would take ~80% of that saving.
Customers usually expect to keep most of the value, so either the price must be lower, or the value must also come from
**readiness** (no missed routes) and **time saved**. Interviews have to measure those (Q2).

**How to read this:** every SAM factor is a guess, and the factors multiply, so the range spans two orders of magnitude.
Even the high case is a niche. The honest conclusion is not "the market is $X." It is: **"on current evidence this is a
feature-sized opportunity; these are the numbers that would have to change for it to be bigger."**

## Why now, and why not now

- **Headwind [Sourced]:** the 45W commercial clean-vehicle credit ended for vehicles acquired after Sept 30, 2025. The
  30C charger credit ends for chargers placed in service after June 30, 2026. Fewer small fleets may electrify in the near term.
- **Tailwind [Sourced]:** utilities are introducing EV-specific business rates that bill power as a subscription (PG&E
  BEV). That turns "how much power should we pay for?" into a monthly cost decision a planner can inform.
- **Installed base [Assumption]:** fleets that already electrified still have to operate every night, whatever new sales do.

## Why would EV companies need this?

Short answer: **most EV companies don't need it, and several already sell something like it.** The customer is the
fleet. Here is each type of EV-related company:

| Company type | Do they need ChargePlan? | Evidence | Role |
|---|---|---|---|
| **Vehicle makers' fleet arms** (e.g. Ford Pro) | Unlikely. They bundle charging software with chargers and vehicles | **[Sourced]** Ford Pro Charging covers depot design, installation, and charge-management software | Competitor |
| **Charger makers and charging-software vendors** | No. They control the hardware and already sell load management | **[Sourced]** Vaylens: €6.90–9.90 per charge point per month including dynamic load balancing | Competitor |
| **Telematics providers** (Samsara, Geotab) | Maybe as an integration. They report charge status, but depot scheduling wasn't confirmed | **[Sourced]** Samsara EV tools: charging status, alerts; Geotab: state-of-charge monitoring and overnight-charge alerts | Partner: could supply each vehicle's energy need, our weakest input |
| **Utilities and their fleet advisory programs** | Plausibly, as an advisor's sizing tool. They already give free advice | **[Sourced]** Free fleet advisory from PG&E, PSEG Long Island, Dominion (VA), and Mass Fleet Advisor | Free substitute **and** possible channel |
| **Electrical installers and EV consultants** | Plausibly, for pre-sales sizing ("how much power do you really need?") | **[Hypothesis]** untested; installers are already on the interview list | Possible channel |
| **Small fleets (the actual customer)** | When power is tight, billed by kW level, or the fleet is changing | **[Model]** PG&E example: about $447/yr from right-sizing; readiness risk at tight limits | User and buyer |

**Where ChargePlan could stand out:** it is hardware-independent (works across mixed chargers and vehicles), transparent
(explains *why* and *when it's impossible*), and supports what-if before committing to power or vehicles. Whether
anyone pays for those strengths is the open question.

## What would make this bigger (to test, not assume)

1. **Advisor/installer sizing tool:** one advisor serves many fleets, so a per-seat or per-study price could beat per-EV
   pricing. Test with installers and utility advisors.
2. **Outside the US:** ~430,000 electric vans sold worldwide in 2025 vs. ~6,000 in the US. Rates and charger markets
   differ, so this needs its own research.
3. **Larger fleets:** the model scales to more vehicles, but large fleets are exactly where bundled suites are strongest.

## How to make these numbers less wrong

- Replace **N** with vehicles-in-operation data filtered to commercial registrations (S&P Global Mobility or Experian; paid).
- Ask utilities or public regulatory filings how many customers are on EV business rates such as PG&E BEV (a direct count of
  sites that pay for kW level).
- Use the interviews (Q2–Q4 and the added billing questions) to estimate s_need, s_open, and willingness to pay.

## Sources

- IEA, [Global EV Outlook 2025: Trends in other light-duty EVs](https://www.iea.org/reports/global-ev-outlook-2025/trends-in-other-light-duty-electric-vehicles)
- IEA, [Global EV Outlook 2026: Trends in other EV modes](https://www.iea.org/reports/global-ev-outlook-2026/trends-in-other-ev-modes)
- Atlas EV Hub, [U.S. Market & Policy Update: Medium- and Heavy-Duty EVs](https://www.atlasevhub.com/data-stories/u-s-market-policy-update-medium-and-heavy-duty-electric-vehicles/)
- Alliance for Automotive Innovation, [2025 Q1 EV report](https://www.autosinnovate.org/posts/press-release/2025-q1-get-connected-press-release)
- Spherical Insights, [EV charging management software platform market](https://www.sphericalinsights.com/press-release/ev-charging-management-software-platform-market); [Business Wire / ResearchAndMarkets](https://www.businesswire.com/news/home/20251210688773/en); [IMARC](https://www.imarcgroup.com/ev-charging-management-software-platform-market); [Meticulous Research, EV fleet management](https://www.meticulousresearch.com/product/ev-fleet-management-market-6407)
- [Vaylens pricing](https://vaylens.com/pricing); TechCrunch, [Guided Energy](https://techcrunch.com/2024/02/06/guided-energy-helps-ev-fleet-managers-optimize-battery-charging)
- Business Wire, [Ford Pro Charging launch](https://www.businesswire.com/news/home/20211216005104/en/Ford-Pro-Charging-Launches-to-Help-Businesses-of-All-Sizes-Overcome-the-Hurdle-to-Seamless-Electrification)
- FreightWaves, [Samsara EV management tools](https://www.freightwaves.com/news/fleet-management-provider-samsara-unveils-ev-management-tools); Fleet Equipment, [Geotab acquires FleetCarma](https://www.fleetequipmentmag.com/geotab-acquires-electric-vehicle-technology-provider-fleetcarma/)
- Utility fleet advisory: [PG&E (BayREN slides)](https://tl.bayren.org/sites/default/files/documents/2025/PG%26E%20EV%20Advisory%20Services%20Slides.pdf), [PSEG Long Island](https://www.psegliny.com/saveenergyandmoney/greenenergy/ev/fleetowners/fleetservices), [Dominion Energy](https://www.dominionenergy.com/Virginia/Save-Energy/Electric-Vehicles/Charging-Your-Fleet), [Mass Fleet Advisor](https://www.mass.gov/doc/june-29-2023-evicc-meeting-mass-fleet-advisor-presentation/download)
- Tax credits: EY, [reconciliation law changes to energy credits](https://taxnews.ey.com/news/2025-1434-final-reconciliation-legislation-modifies-some-ira-energy-credits-repeals-others); Electrification Coalition, [tax credit guidance for fleets](https://electrificationcoalition.org/resource/tax-credit-guidance-for-fleets-what-you-need-to-know-about-the-budget-reconciliation-bill/)
- PG&E, [Electric Schedule BEV](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_BEV.pdf)
