"""Independent checks on schedules, and simple proofs that a request is impossible.

`check_schedule` re-verifies ANY schedule (optimizer or baseline) directly
against the inputs, so "ready" never rests only on a solver's word.

`find_simple_impossibilities` tests necessary conditions. If one fails, no
schedule can ready every vehicle. If all pass, a plan may still be impossible
because of how vehicles compete for shared power at the same time.
"""

from dataclasses import dataclass

import numpy as np

from .models import PlanInput
from .slots import DT_HOURS, Slot

# Numerical tolerance for comparing energies (kWh). HiGHS works to about 1e-7
# by default, so differences smaller than this are rounding, not real errors.
TOL_KWH = 1e-6


@dataclass
class ScheduleCheck:
    violations: list[str]  # broken limits: the schedule itself is invalid
    delivered_kwh: list[float]  # battery energy added per vehicle (after losses)
    ready: list[bool]  # delivered >= requested, per vehicle
    shortfall_kwh: list[float]

    @property
    def all_ready(self) -> bool:
        return not self.violations and all(self.ready)


def check_schedule(plan: PlanInput, slots: list[Slot], avail: np.ndarray, x: np.ndarray) -> ScheduleCheck:
    """x[v, t] is grid kWh for vehicle v in slot t."""
    violations = []
    if x.shape != avail.shape or not np.isfinite(x).all():
        return ScheduleCheck(["Schedule has the wrong shape or non-numeric values."], [], [], [])

    for v, vehicle in enumerate(plan.vehicles):
        cap = vehicle.max_power_kw * DT_HOURS
        for slot in slots:
            amount, when = x[v, slot.index], slot.start.strftime("%H:%M")
            if amount < -TOL_KWH:
                violations.append(f"{vehicle.name}: negative energy at {when}.")
            if not avail[v, slot.index] and amount > TOL_KWH:
                violations.append(f"{vehicle.name}: charging at {when} while not plugged in.")
            if amount > cap + TOL_KWH:
                violations.append(f"{vehicle.name}: above its {vehicle.max_power_kw:g} kW charger limit at {when}.")

    site_cap = plan.site_limit_kw * DT_HOURS
    for slot in slots:
        if x[:, slot.index].sum() > site_cap + TOL_KWH:
            violations.append(
                f"Total charging above the {plan.site_limit_kw:g} kW site allowance at {slot.start.strftime('%H:%M')}."
            )

    delivered, ready, shortfall = [], [], []
    for v, vehicle in enumerate(plan.vehicles):
        added = plan.efficiency * float(x[v].sum())
        need = vehicle.energy_needed_kwh
        if added > need + TOL_KWH:
            violations.append(f"{vehicle.name}: receives more energy than requested.")
        delivered.append(added)
        ready.append(added >= need - TOL_KWH)
        shortfall.append(max(0.0, need - added))
    return ScheduleCheck(violations, delivered, ready, shortfall)


def find_simple_impossibilities(plan: PlanInput, avail: np.ndarray) -> list[str]:
    reasons = []

    # 1. Each vehicle on its own: is its window long enough at its usable power?
    for v, vehicle in enumerate(plan.vehicles):
        need_grid = vehicle.energy_needed_kwh / plan.efficiency
        usable_kw = min(vehicle.max_power_kw, plan.site_limit_kw)
        hours = int(avail[v].sum()) * DT_HOURS
        most = usable_kw * hours
        if need_grid > most + TOL_KWH:
            reasons.append(
                f"{vehicle.name} needs {need_grid:.2f} kWh from the grid "
                f"({vehicle.energy_needed_kwh:.2f} kWh into the battery at {plan.efficiency * 100:g}% efficiency), "
                f"but can receive at most {most:.2f} kWh in its {hours:g}-hour window at up to {usable_kw:g} kW."
            )

    # 2. All vehicles together: total need vs. the most the site could deliver.
    total_need = sum(vehicle.energy_needed_kwh for vehicle in plan.vehicles) / plan.efficiency
    max_kw = np.array([vehicle.max_power_kw for vehicle in plan.vehicles])
    total_most = sum(min(plan.site_limit_kw, float(max_kw[avail[:, t]].sum())) * DT_HOURS for t in range(avail.shape[1]))
    if total_need > total_most + TOL_KWH:
        reasons.append(
            f"Together the vehicles need {total_need:.2f} kWh from the grid, but at most {total_most:.2f} kWh "
            f"can be delivered overnight with a {plan.site_limit_kw:g} kW site allowance and these charger limits."
        )
    return reasons
