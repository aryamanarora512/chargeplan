# ChargePlan product brief (Milestone 0)

*Last updated 2026-10-15. Status: clearly labeled prototype. No customer interviews have been completed yet.*

Throughout this brief, every statement is tagged as one of:
**[Sourced]** (from a cited public document), **[Hypothesis]** (our belief, not yet tested), or **[Feedback]** (something a real person told us; there is none yet).

## Problem

A small delivery or service fleet (roughly 3–10 EVs) returns to one depot in the evening. Each vehicle needs a different
amount of energy before a different departure time. Electricity may cost more at some hours than others, and the depot
has a fixed amount of power set aside for EV charging. Tonight, someone has to decide **when each vehicle charges**,
find out **whether every vehicle will be ready**, and see **what happens if one departure time or energy need changes**.

**Job to be done [Hypothesis]:** *"When I plan tonight's charging, help me get every vehicle ready for its next trip at the
lowest modeled charging-energy cost without going over the depot's charging power allowance."*

## Customer (target persona, not validated)

The person who plans overnight charging for a small fleet at one depot: a fleet supervisor, dispatcher, or facilities
manager. **[Hypothesis]** They plan with charger timers, a spreadsheet, or "plug in and hope," and lack a quick way to
check readiness and cost *before* the night starts.

## What public sources say

- **[Sourced]** The U.S. DOE describes *managed charging* as controlling when and how fleet vehicles charge. It says
  unmanaged charging (starting the moment a vehicle plugs in) can raise energy costs during peak pricing, raise demand
  charges, and force infrastructure upgrades. It describes two approaches: **user planning** (manually programmed static
  schedules, which have to be updated when operations or rates change) and **smart charge management** (networked chargers
  that adjust power automatically). Savings are described as potential, not quantified.
  ([DOE FEMP](https://www.energy.gov/cmei/femp/managed-ev-charging-federal-fleets))
- **[Sourced]** The DOE Alternative Fuels Data Center notes that simultaneous high-power charging can trigger demand
  charges, and that networked charging can stagger sessions to use off-peak rates and limit peak demand.
  ([AFDC](https://afdc.energy.gov/vehicles/electric-fleets))

**What this means for us:** the problem category is real and already served. Smart-charging products and charger timers
exist. ChargePlan does not invent this category. Our proposed difference is a **transparent, hardware-independent
planning and what-if tool**. Whether that is useful beyond existing tools is exactly what interviews must test.

## Riskiest unvalidated assumptions

1. **[Hypothesis] Existing tools leave a gap.** If the fleet's charger software already answers "will everyone be ready, and
   at what cost?", ChargePlan adds little. *If interviews confirm this, reconsider the product before adding features.*
2. **[Hypothesis] Energy rates matter enough.** Our model excludes demand charges and fixed fees. If those make up most of
   a fleet's charging cost, shifting energy to cheap hours may matter less than the numbers suggest.
3. **[Hypothesis] Inputs are known.** Operators may know battery *percentage* and route plans, not "kWh to add." The
   site's charging allowance may not be a number anyone has written down.
4. **[Hypothesis] A plan is actionable.** ChargePlan doesn't control chargers. Someone must be willing to set timers or
   power limits by hand to follow it.

## Approaches considered

| Approach | Why it's not enough on its own |
|---|---|
| Charge as soon as vehicles arrive | Easy to understand, but ignores price differences and lets vehicles compete for power at once. |
| Same cheap-hours timer for every vehicle | Vehicles have different deadlines and share one site limit, so a vehicle leaving before cheap hours misses out, and everyone starting at once can exceed the allowance. |
| Forecast and disaggregate behind-the-meter solar | A separate estimation problem: grid operators observe only net load, which makes rooftop solar hard to measure directly ([Shaffery et al., 2020](https://research-hub.nlr.gov/en/publications/bayesian-structural-time-series-for-behind-the-meter-photovoltaic-2/)). Not needed for a first product. |
| **Chosen:** price-aware schedule with explicit energy, availability, charger and shared-power constraints | Small enough to explain fully; uses a standard linear program; compared against the first approach as a baseline. |

## User journey

Open the sample (or start a plan) → enter vehicles, rates, and the charging allowance → **Generate plan** → see whether
every vehicle is ready and what the plan costs → change one assumption (e.g. Van B leaves at 05:00) → compare against the
previous run → export the schedule as CSV.

## Success criteria

**Product (to be measured; no results yet)**
- In usability tests, a first-time user can say whether every vehicle will be ready, and what the plan costs, within
  2 minutes without reading the README.
- At least 3 of 5 interviewees describe a recent planning decision ChargePlan would have informed (Q1–Q2).
- At least 2 of 5 say what they would do differently after seeing a plan (Q5).
- Stop signal: most interviewees say their existing charger software already does this.

**Technical (measured, see the [README](../README.md#evaluation-measured-not-estimated))**
- The hand-checkable example gives exactly $12.00 (baseline) and $4.80 (optimized).
- Every "ready" claim is independently re-checked against the inputs.
- Solve time at the largest supported size (10 vehicles × 48 slots) stays under 2 s.

## Wireframe (planned web UI)

See [`images/ui-wireframe.svg`](images/ui-wireframe.svg). One page, two areas; on a phone they stack in a single column.

1. **Plan setup:** site time zone, horizon start and end, EV charging allowance (kW, with help text: "power reserved
   for EV charging, not your building's rating"), efficiency (%), a rate-band table ($/kWh), a vehicle table (name, arrive, depart,
   kWh to add, max kW), **Load sample** and **Generate plan**.
2. **Results:** a status banner ("All 2 vehicles ready" or "Not every vehicle can be ready"), three numbers (ready count,
   modeled energy cost, comparison with the baseline when comparable), a power-over-time chart with the site limit and
   tariff bands, a vehicle status table (requested, delivered, ready, departure), a plain-language explanation, and
   **Edit and recalculate**, **Export CSV**, and **Save run**. After an edit, old results are marked "out of date" until recomputed.

## Customer discovery

Questions, recruiting plan, and the interview log are in [discovery.md](discovery.md). **Feedback received so far: none.**
