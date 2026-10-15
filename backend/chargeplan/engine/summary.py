"""Costs, per-vehicle status, the baseline comparison, and the explanation text.

All numbers keep full precision; rounding happens only inside display strings.
"""

from dataclasses import dataclass
from zoneinfo import ZoneInfo

import numpy as np

from .checks import TOL_KWH, ScheduleCheck
from .models import PlanInput
from .slots import DT_HOURS, Slot, slot_prices

MONEY_NOISE = 1e-9  # dollars; differences smaller than this are float round-off


@dataclass
class VehicleStatus:
    id: str
    name: str
    arrival: str  # ISO 8601 with UTC offset
    departure: str
    requested_kwh: float  # battery energy asked for
    delivered_kwh: float  # battery energy this schedule adds
    grid_kwh: float  # energy drawn from the grid (before charging losses)
    cost: float
    ready: bool
    shortfall_kwh: float


@dataclass
class ScheduleSummary:
    policy: str  # "optimized" or "baseline"
    grid_kwh: list[list[float]]  # [vehicle][slot]
    site_kw: list[float]  # total charging power in each slot
    vehicles: list[VehicleStatus]
    ready_count: int
    all_ready: bool
    total_grid_kwh: float
    total_cost: float
    violations: list[str]


@dataclass
class Comparison:
    comparable: bool
    optimized_cost: float | None
    baseline_cost: float | None
    savings: float | None  # baseline minus optimized, when comparable
    savings_pct: float | None  # None when not comparable or baseline cost is zero
    note: str


def schedule_cost(x: np.ndarray, prices: np.ndarray) -> float:
    """Dollars = sum over vehicles and slots of price[t] * grid kWh[v, t]."""
    return float((x * prices).sum())


def summarize_schedule(
    policy: str, plan: PlanInput, slots: list[Slot], x: np.ndarray, check: ScheduleCheck
) -> ScheduleSummary:
    tz = ZoneInfo(plan.timezone)
    prices = slot_prices(slots)
    vehicles = [
        VehicleStatus(
            id=vehicle.id,
            name=vehicle.name,
            arrival=vehicle.arrival.replace(tzinfo=tz).isoformat(),
            departure=vehicle.departure.replace(tzinfo=tz).isoformat(),
            requested_kwh=vehicle.energy_needed_kwh,
            delivered_kwh=check.delivered_kwh[v],
            grid_kwh=float(x[v].sum()),
            cost=schedule_cost(x[v], prices),
            ready=check.ready[v],
            shortfall_kwh=check.shortfall_kwh[v],
        )
        for v, vehicle in enumerate(plan.vehicles)
    ]
    return ScheduleSummary(
        policy=policy,
        grid_kwh=x.tolist(),
        site_kw=(x.sum(axis=0) / DT_HOURS).tolist(),
        vehicles=vehicles,
        ready_count=sum(check.ready),
        all_ready=check.all_ready,
        total_grid_kwh=float(x.sum()),
        total_cost=schedule_cost(x, prices),
        violations=check.violations,
    )


def compare(optimized: ScheduleSummary | None, baseline: ScheduleSummary | None) -> Comparison:
    """Savings are shown only when both plans ready every vehicle with the same energy."""

    def not_comparable(note: str) -> Comparison:
        return Comparison(
            False,
            optimized.total_cost if optimized else None,
            baseline.total_cost if baseline else None,
            None,
            None,
            note,
        )

    if optimized is None or baseline is None:
        return not_comparable("There is no optimized plan to compare.")
    if not baseline.all_ready:
        short = len(baseline.vehicles) - baseline.ready_count
        return not_comparable(
            f"The baseline leaves {short} vehicle(s) short, so its cost is not comparable."
        )
    if abs(optimized.total_grid_kwh - baseline.total_grid_kwh) > TOL_KWH * len(optimized.vehicles):
        return not_comparable("The two plans deliver different amounts of energy, so their costs are not comparable.")

    savings = baseline.total_cost - optimized.total_cost
    if abs(savings) < MONEY_NOISE:
        savings = 0.0
    pct = savings / baseline.total_cost if baseline.total_cost > 0 else None
    return Comparison(True, optimized.total_cost, baseline.total_cost, savings, pct, "Both plans ready every vehicle with the same energy.")


BASELINE_NAME = "charging as soon as vehicles arrive, earliest departure first"
COST_CAVEAT = (
    "Costs cover charging energy at the entered rates only (no demand charges, fixed fees or taxes), "
    "so they are not a utility-bill estimate."
)


def explain(
    status: str,
    plan: PlanInput,
    slots: list[Slot],
    optimized: ScheduleSummary | None,
    baseline: ScheduleSummary | None,
    comparison: Comparison | None,
) -> list[str]:
    """Plain-language sentences built only from the inputs and computed outputs."""
    n = len(plan.vehicles)
    if status == "invalid":
        return ["Some inputs need attention before a plan can be calculated."]
    if status == "infeasible":
        return ["Not every vehicle can be ready by its departure with these inputs.", COST_CAVEAT]
    if status == "solver_limit":
        return ["The solver stopped at its time limit. That does NOT mean the plan is impossible; try recalculating."]
    if status == "solver_error" or optimized is None:
        return ["The solver ran into a problem, so no plan is shown. That does NOT mean the plan is impossible."]

    lines = [f"All {n} vehicle{'s' if n != 1 else ''} can be ready by departure under these inputs."]
    added = sum(vs.delivered_kwh for vs in optimized.vehicles)
    lines.append(
        f"The optimized plan draws {optimized.total_grid_kwh:.1f} kWh from the grid to add {added:.1f} kWh to batteries "
        f"(assuming {plan.efficiency * 100:g}% charging efficiency), for a modeled energy cost of ${optimized.total_cost:.2f}. "
        "The solver reports this as the lowest possible cost under this model."
    )

    prices = slot_prices(slots)
    x = np.array(optimized.grid_kwh)
    if prices.max() - prices.min() < MONEY_NOISE:
        lines.append("The rate is the same all night, so changing when vehicles charge cannot change the energy cost.")
    elif optimized.total_grid_kwh > TOL_KWH:
        cheapest = prices.min()
        share = x[:, prices <= cheapest + MONEY_NOISE].sum() / optimized.total_grid_kwh
        lines.append(f"{share:.0%} of that energy is scheduled at the lowest rate of the night (${cheapest:.2f}/kWh).")

    lines.append(
        f"Total charging power peaks at {max(optimized.site_kw):.1f} kW, within the {plan.site_limit_kw:g} kW EV charging allowance."
    )

    if comparison and comparison.comparable:
        if comparison.savings > 0:
            lines.append(
                f"The baseline ({BASELINE_NAME}) also readies every vehicle but costs ${comparison.baseline_cost:.2f}: "
                f"${comparison.savings:.2f} more for the same energy."
            )
        else:
            lines.append(f"The baseline ({BASELINE_NAME}) costs the same: ${comparison.baseline_cost:.2f}.")
    elif baseline is not None and baseline.ready_count < n:
        short = [f"{vs.name} {vs.shortfall_kwh:.1f} kWh short" for vs in baseline.vehicles if not vs.ready]
        lines.append(
            f"The baseline ({BASELINE_NAME}) would leave {', '.join(short)} at departure. "
            "Because it delivers less energy, no cost saving is claimed."
        )

    lines.append(COST_CAVEAT)
    return lines
