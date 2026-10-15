# How ChargePlan decides when to charge

This page explains the math in plain English first, then shows exactly what the code hands to the solver.

## 1. Two units that are easy to mix up

- **kW (power)** is a *rate*: how fast energy flows right now.
- **kWh (energy)** is an *amount*: power × time.

ChargePlan uses 30-minute slots, so in one slot a charger running at 10 kW delivers `10 kW × 0.5 h = 5 kWh`.
In the code that conversion factor is `DT_HOURS = 0.5`.

**Efficiency.** Some energy is lost as heat while charging. If a van needs **18 kWh added to its battery** and we assume
90% efficiency, the depot has to draw `18 / 0.9 = 20 kWh` **from the grid**. You pay for all 20 kWh, so losses affect cost.
The 90% is an editable modeling assumption, not a measured number for any particular vehicle or charger.

## 2. The decision, in words

For every vehicle and every 30-minute slot, decide how many kWh to send to that vehicle. Make the total cost as small as possible, subject to four rules:

1. A vehicle can only charge while it is plugged in (between its arrival and departure).
2. A vehicle can't charge faster than its charger allows.
3. All vehicles **together** can't exceed the depot's EV charging allowance in any slot. This is the rule that *couples* the vehicles: one van charging fast leaves less room for the others.
4. Each vehicle must end up with exactly the battery energy it asked for.

## 3. A tiny example you can do by hand

One hour, two slots. Prices: **$0.30/kWh** in slot 1, **$0.10/kWh** in slot 2. Efficiency 90%.

**One van** needs 4.5 kWh in its battery, so 5 kWh from the grid. Its charger is 10 kW (5 kWh per slot). Site limit 10 kW.

- Charge-immediately: 5 kWh in slot 1 → **$1.50**.
- Cheapest: 5 kWh in slot 2 → **$0.50**.

**Add a second, identical van.** Now both want slot 2, but the site limit lets only 5 kWh through per slot.
One van must use slot 1: `5 × 0.10 + 5 × 0.30 =` **$2.00**. Neither van alone forces this; the *shared limit* does.
That is why you can't plan each vehicle separately (or give everyone the same "cheap hours" timer).

## 4. The same thing as a linear program

Let `x[v,t]` be grid kWh for vehicle `v` in slot `t`, `dt = 0.5` h, `price[t]` in $/kWh, `P[v]` the charger limit (kW),
`C` the site allowance (kW), `E[v]` battery energy needed (kWh), and `eta` the efficiency.

```
minimize    Σ_v Σ_t price[t] · x[v,t]

subject to  0 ≤ x[v,t] ≤ P[v]·dt       while v is plugged in      (rules 1, 2)
            x[v,t] = 0                 otherwise                  (rule 1)
            Σ_v x[v,t] ≤ C·dt          for every slot t           (rule 3)
            eta · Σ_t x[v,t] = E[v]    for every vehicle v        (rule 4)
```

**Why it's a *linear* program:** every term is a constant multiplied by one variable (`0.30 · x`, `0.9 · x`).
There are no products of variables, no squares, no yes/no choices. Linear programs can be solved quickly and exactly
(up to floating-point tolerance), and the solver can *prove* when no solution exists.

For the two-van, two-slot example, the code builds (variables ordered `[A1, A2, B1, B2]`):

```
c     = [0.30, 0.10, 0.30, 0.10]          # price of each variable
A_ub  = [[1, 0, 1, 0],                    # slot 1: A1 + B1 ≤ 5
         [0, 1, 0, 1]]                    # slot 2: A2 + B2 ≤ 5
b_ub  = [5, 5]
A_eq  = [[0.9, 0.9, 0,   0  ],            # van A: 0.9·(A1 + A2) = 4.5
         [0,   0,   0.9, 0.9]]            # van B: 0.9·(B1 + B2) = 4.5
b_eq  = [4.5, 4.5]
bounds = [(0, 5)] * 4                     # charger limit (0 outside the window)
```

You can find these exact lines in [`backend/chargeplan/engine/optimizer.py`](../backend/chargeplan/engine/optimizer.py).

## 5. What the library does for us

We don't implement the optimization algorithm. `scipy.optimize.linprog(method="highs")` passes the matrices to
[HiGHS](https://highs.dev), an open-source LP solver, which picks a simplex or interior-point method. We:

- build the matrices (above),
- read `res.status`: `0` optimal, `1` time/iteration limit, `2` infeasible, `3` unbounded, `4` solver problem
  ([SciPy docs](https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs.html)),
- **re-check the returned schedule ourselves** (`checks.py`) before saying any vehicle is ready.

A time limit or solver error is **not** proof that a plan is impossible. Only status `2` is reported as infeasible.

## 6. The worked example in the tests

Two vans arrive 18:00 and leave 08:00. Each needs 18 kWh in the battery (20 kWh from the grid). Each charger allows 10 kW; the site allows 10 kW total.
Synthetic prices: $0.30 until midnight, $0.12 from 00:00–06:00, $0.30 from 06:00–08:00.

- At 10 kW total, 40 kWh takes 4 hours (8 slots). The cheap period lasts 6 hours (12 slots), so it all fits.
- **Optimized:** 40 kWh × $0.12 = **$4.80**.
- **Baseline** (charge as soon as vehicles arrive, earliest departure first, ties broken by ID): Van A 18:00–20:00, then Van B 20:00–22:00, all at $0.30, so 40 kWh × $0.30 = **$12.00**.
- The $7.20 difference comes only from these invented prices. It is not evidence of real savings or a lower utility bill.

Several schedules cost exactly $4.80 (any arrangement inside the cheap period that respects the limits). The solver
returns one of them, so the tests check *cost and constraints*, never a specific arrangement.

## 7. When no plan exists

If HiGHS proves the problem infeasible, ChargePlan tries two simple checks that are *guaranteed* to be correct when they fire:

1. **One vehicle alone:** grid kWh needed > (usable kW) × (hours plugged in). Example: needs 60 kWh, can get 21.6 kWh in 3 hours at 7.2 kW.
2. **Whole night:** total grid kWh needed > the most the site and chargers could deliver across all slots.

If neither fires, every vehicle could be ready **on its own**, so the conflict must come from vehicles sharing the site
allowance. ChargePlan says that and nothing more specific; it doesn't invent a single bottleneck.

## 8. When the baseline fails but the optimizer succeeds

Charging in departure order can paint itself into a corner. In the `baseline_misses_departure` scenario, a van with a fast
charger leaves first and takes the whole 11 kW site allowance from 18:00–22:00. The van with a slow 7 kW charger then
runs out of time and ends up 12.6 kWh short. The optimizer shares power from the start and readies both. Because the
baseline delivers *less* energy, its lower dollar figure isn't a fair comparison, so no saving is shown.

## 9. What this model leaves out

Demand charges ($/kW of peak), fixed fees, taxes, solar, vehicle-to-grid, battery aging, the charging slow-down near
full (taper), minimum charger currents, and real charger control. **Results are modeled charging-energy costs, not
utility bills,** and schedules are plans, not commands a charger is guaranteed to follow.
