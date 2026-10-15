"""Price-blind benchmark policy: earliest departure first, as soon as possible.

In every slot, the plugged-in vehicles that still need energy are served in
order of departure time (ties broken by vehicle ID). Each gets as much as its
charger allows, without going past what it still needs or what is left of the
shared site allowance in that slot.

This is a benchmark, NOT a feasibility test. It can leave a vehicle short even
when the optimizer finds a schedule that readies every vehicle.
"""

import numpy as np

from .checks import TOL_KWH
from .models import PlanInput
from .slots import DT_HOURS


def earliest_departure_first(plan: PlanInput, avail: np.ndarray) -> np.ndarray:
    """Return x[v, t] = grid kWh given to vehicle v in slot t."""
    n_vehicles, n_slots = avail.shape
    x = np.zeros((n_vehicles, n_slots))
    still_needed = [v.energy_needed_kwh / plan.efficiency for v in plan.vehicles]  # grid kWh
    order = sorted(range(n_vehicles), key=lambda v: (plan.vehicles[v].departure, plan.vehicles[v].id))

    for t in range(n_slots):
        site_left = plan.site_limit_kw * DT_HOURS
        for v in order:
            if not avail[v, t] or still_needed[v] <= TOL_KWH:
                continue
            amount = min(plan.vehicles[v].max_power_kw * DT_HOURS, still_needed[v], site_left)
            x[v, t] = amount
            still_needed[v] -= amount
            site_left -= amount
    return x
