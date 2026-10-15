"""Minimum-cost charging schedule as a linear program (LP), solved by HiGHS.

Decision variable: x[v, t] = grid kWh delivered to vehicle v during slot t.

    minimize    sum over v,t of  price[t] * x[v, t]
    subject to  0 <= x[v, t] <= P[v] * dt     while v is plugged in
                x[v, t] = 0                   otherwise
                sum over v of x[v, t] <= C * dt     for every slot t  (shared site limit)
                eta * sum over t of x[v, t] = E[v]  for every vehicle v (battery energy)

Every term is a constant times one x[v, t], so the objective and constraints
are linear: that is what makes this an LP. We build the matrices; SciPy's
linprog hands them to the HiGHS solver, which does the actual optimization.
"""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog

from .models import PlanInput
from .slots import DT_HOURS, Slot, slot_prices

DEFAULT_TIME_LIMIT_S = 10.0
NOISE_KWH = 1e-9  # solver round-off below this is set to exactly zero

# linprog result.status codes, from the SciPy docs for method="highs".
# 3 (unbounded) cannot happen here because every variable has an upper bound.
_STATUS = {0: "optimal", 1: "solver_limit", 2: "infeasible", 3: "solver_error", 4: "solver_error"}


@dataclass
class SolveOutcome:
    status: str  # "optimal" | "infeasible" | "solver_limit" | "solver_error"
    message: str  # the solver's own message, kept for debugging
    x: np.ndarray | None  # grid kWh, shape (vehicles, slots); only when optimal


def solve_min_cost(
    plan: PlanInput, slots: list[Slot], avail: np.ndarray, time_limit_s: float = DEFAULT_TIME_LIMIT_S
) -> SolveOutcome:
    n_vehicles, n_slots = avail.shape
    n_vars = n_vehicles * n_slots

    def col(v: int, t: int) -> int:  # where x[v, t] sits in linprog's flat vector
        return v * n_slots + t

    prices = slot_prices(slots)
    c = np.zeros(n_vars)
    bounds = []
    for v, vehicle in enumerate(plan.vehicles):
        for t in range(n_slots):
            c[col(v, t)] = prices[t]
            upper = vehicle.max_power_kw * DT_HOURS if avail[v, t] else 0.0
            bounds.append((0.0, upper))

    # Shared site limit: one row per slot, adding up every vehicle in that slot.
    A_ub = np.zeros((n_slots, n_vars))
    for t in range(n_slots):
        for v in range(n_vehicles):
            A_ub[t, col(v, t)] = 1.0
    b_ub = np.full(n_slots, plan.site_limit_kw * DT_HOURS)

    # Battery energy: one row per vehicle, adding up that vehicle's slots.
    A_eq = np.zeros((n_vehicles, n_vars))
    for v in range(n_vehicles):
        for t in range(n_slots):
            A_eq[v, col(v, t)] = plan.efficiency
    b_eq = np.array([vehicle.energy_needed_kwh for vehicle in plan.vehicles])

    try:
        res = linprog(
            c,
            A_ub=A_ub,
            b_ub=b_ub,
            A_eq=A_eq,
            b_eq=b_eq,
            bounds=bounds,
            method="highs",
            options={"time_limit": time_limit_s},
        )
    except Exception as exc:  # a crash says nothing about whether a plan exists
        return SolveOutcome("solver_error", f"Solver raised {type(exc).__name__}: {exc}", None)

    status = _STATUS.get(res.status, "solver_error")
    if status != "optimal":
        return SolveOutcome(status, res.message, None)
    if res.x is None:
        return SolveOutcome("solver_error", "Solver reported success but returned no schedule.", None)

    x = res.x.reshape(n_vehicles, n_slots)
    x = np.where(np.abs(x) < NOISE_KWH, 0.0, x)
    return SolveOutcome("optimal", res.message, x)
