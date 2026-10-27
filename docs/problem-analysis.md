# Problem statement: clarification and analysis

*2026-10-26. Desk research and a model run, not customer evidence. No interviews have been completed yet.*

Labels: **[Sourced]** = cited public document · **[Model]** = computed with ChargePlan's own engine from stated inputs ·
**[Hypothesis]** = our belief, untested.

## Summary

1. **The realistic alternative is a timer, not "plug in and charge."** Most of the cost gap between charging on arrival and
   charging overnight can be closed by a single "start at 9 pm" timer. ChargePlan only adds value beyond that when
   power is tight, departures differ, or the site pays for the power level it uses.
2. **Under at least one real fleet EV rate, the money is in the power level, not the cheap hours.** PG&E's Business EV
   rate charges one price for the whole 9 pm–9 am night and bills power as a monthly kW *subscription*. In our model run,
   the planner's distinct value is finding the **smallest subscription that still gets every vehicle ready**.
3. **The dollars for a small fleet are modest.** In the worked example, right-sizing saves about **$450/year for a 6-van
   depot**. That is a useful feature, but a thin standalone business (see [market-sizing.md](market-sizing.md)).

## Who is who

Before asking "why would EV companies need this?", separate the roles:

| Role | Who | Relationship to ChargePlan |
|---|---|---|
| **User** | Person planning tonight's charging (fleet supervisor, dispatcher, facilities manager) | Uses it nightly or when plans change |
| **Buyer** | Owner or operations lead of a 3–10 EV fleet | Pays only if it saves money, time, or missed routes |
| **Possible channel** | Utility fleet advisors, electrical installers, EV consultants | Might use it to size a site for many fleets |
| **Competitors / substitutes** | Charger-maker software, vehicle-maker fleet suites, telematics, charger timers, free utility advisory | Already cover parts of the job |

"EV companies" (vehicle makers, charger networks) are mostly **competitors or partners, not customers**. See the
[market-sizing](market-sizing.md#why-would-ev-companies-need-this) doc for the breakdown.

## Sharper problem statement (v2)

> **A small fleet (3–10 EVs, one depot) has to choose how much charging power to pay for, and how to schedule charging
> under that power level, so that every vehicle is ready for its next departure. Today it guesses: it either pays for
> more power than it needs, or risks a vehicle not being ready when departures, energy needs, or the number of vehicles
> change.**

What changed from v1:
- v1 asked for the "lowest modeled energy cost." v2 adds the **power level as a decision**, because some EV rates bill it
  directly (below).
- v2 names the **failure the customer fears**: a vehicle not ready, or paying for unused power. Interviews can test those
  directly (Q2, Q3).

**We are wrong if** most interviewees (a) already have chargers that share power automatically and are satisfied,
(b) don't pay for power level in a way they can change, or (c) never come close to their power limit.

## The problem has three parts, and they need different tools

| Part | Question | When it matters | Is a simple timer enough? |
|---|---|---|---|
| **Energy cost** | Which hours should vehicles charge in? | Rates differ *within* the hours vehicles are plugged in | Often yes, when everyone is plugged in through the cheap hours and power isn't tight |
| **Readiness** | Will every vehicle make its departure? | Total energy is large relative to power × time, or departures are staggered | No. One shared start time can overload the limit or start too late for early departures |
| **Sizing / what-if** | How much power should we pay for? Can we add a van? What if Van B leaves at 5 am? | Rates bill power level; fleet or routes change | No. This needs re-solving under different limits |

The original engine compares against **charge-on-arrival**, which flatters the optimizer. The fair benchmark is a
**shared timer** (everyone starts at the start of the cheap period). Adding it is a recommended next engineering step.

## Evidence from a real tariff: PG&E Business EV (BEV-1)

**[Sourced]** PG&E's BEV schedule replaces the usual demand charge with a monthly **kW subscription**, sold in 10 kW blocks
on BEV-1 (intended for usage at or below 100 kW). Prices as of 2026-03-01: **$12.41 per block per month**, with a
**$2.48/kW overage fee** for usage above the subscription. Overage is measured as average kW over 15-minute intervals.
Energy prices are **peak $0.35711/kWh (4–9 pm)**, **off-peak $0.16510/kWh (9 pm–9 am and 2–4 pm)**, and **super off-peak
$0.13844/kWh (9 am–2 pm)**, every day. ([PG&E BEV tariff](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_BEV.pdf))

The whole overnight window has a **single price**. For a depot that charges at night, "cheapest hours" reduces to
"don't charge from 4 to 9 pm."

**[Model]** Illustrative depot, not a real fleet: 6 vans arrive at 17:00 and leave at 06:00. Each needs 36 kWh in the
battery (40 kWh from the grid at 90%) and has a 10 kW charger. Output from ChargePlan's engine, with the BEV-1 energy rates as inputs:

| EV charging allowance | BEV-1 blocks | Optimized energy cost / night | Energy at peak price | Charge-on-arrival / night | Charge-on-arrival ready |
|---:|---:|---:|---:|---:|---:|
| 60 kW | 6 | $39.62 | 0 kWh | $85.71 | 6/6 |
| 30 kW | 3 | **$39.62** | 0 kWh | $62.67 | 6/6 |
| 25 kW | 3 | $42.50 | 15 kWh | $58.83 | 6/6 |
| 20 kW | 2 | $51.14 | 60 kWh | $54.98 | 6/6 |
| 18.5 kW | 2 | $53.74 | 73.5 kWh | $52.88 | **5/6** |
| 18 kW | 2 | infeasible | none | $51.80 | 5/6 |

What this shows:
- **Energy:** the $46/night gap between charge-on-arrival ($85.71) and the optimum ($39.62) is closed by a 9 pm timer
  just as well. That saving is real but does not need ChargePlan.
- **Sizing:** 30 kW (3 blocks) reaches the same energy cost as 60 kW (6 blocks). Dropping 3 blocks saves
  3 × $12.41 × 12 ≈ **$447/year**. A naive timer that starts all six vans at 9 pm draws 60 kW, so getting that saving needs a
  staggered plan (or chargers that share power automatically).
- **Don't over-shrink:** going from 3 blocks to 2 saves $12.41/month but adds about $346/month in peak-hour energy.
  ChargePlan's what-if makes that tradeoff visible.
- **Readiness:** at 18.5 kW, charge-on-arrival leaves one van short while the optimizer readies all six. That shows the
  readiness problem is real, although this tight a limit isn't cost-optimal here.

Caveats: one utility, one illustrative depot, 30-minute slots (PG&E measures overage over 15 minutes), and it assumes
the chargers are the only load counted against the subscription. Other utilities' rates may have overnight price
differences; ask interviewees which rate they're on (Q3).

## When the problem is trivial vs. real [Hypothesis]

ChargePlan adds **little** when:
- the power limit comfortably covers all chargers running at once, **and**
- every vehicle is plugged in through the cheap hours, **and**
- the fleet doesn't pay for its power level separately (or never comes near it).

It adds the **most** when:
- the fleet pays for a kW level it can choose (a subscription or demand charge), **or**
- the energy needed is large compared with (power limit × hours plugged in), roughly over half, **or**
- departures are staggered, with some vehicles leaving before the cheap period ends, **or**
- the fleet is about to change (adding vans, new routes) and needs a what-if before committing.

## What this changes

Not built yet. Candidate next steps, each to be confirmed by interviews first:
1. Add a **shared-timer baseline** next to charge-on-arrival, so claimed value is measured against the realistic alternative.
2. Add a **"smallest allowance that keeps everyone ready"** what-if (re-solve over a range of kW limits). The engine can
   already do this one solve at a time.
3. Optionally model a **subscription cost per kW block**, so cost = energy + power level.

New interview questions to add:
- *"How is your charging power billed: demand charge, subscription, or neither? What level are you paying for?"*
- *"Do your chargers share power automatically, or does each charge at full speed?"*
- *"Do you know each vehicle's energy need, or its battery % and route length?"* Telematics may already supply this.

## Sources

- PG&E, [Electric Schedule BEV (Business Electric Vehicle)](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_BEV.pdf). Rates effective 2026-03-01; time periods and subscription rules as stated in the schedule.
- U.S. DOE FEMP, [Managed EV Charging for Federal Fleets](https://www.energy.gov/cmei/femp/managed-ev-charging-federal-fleets): manual "user planning" schedules must be updated when operations or rates change.
- U.S. DOE AFDC, [Electric Vehicles for Fleets](https://afdc.energy.gov/vehicles/electric-fleets): simultaneous charging can trigger demand charges; managed charging can stagger sessions.
