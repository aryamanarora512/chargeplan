"""Fixed 30-minute time slots and the vehicle availability grid.

Call these only after `validate_plan` has returned no issues: they assume the
horizon is slot-aligned, fully covered by rate bands, and free of
daylight-saving changes (so local clock arithmetic equals real elapsed time).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np

from .models import PlanInput

SLOT = timedelta(minutes=30)
DT_HOURS = 0.5  # slot length in hours: kW * DT_HOURS = kWh in one slot


@dataclass(frozen=True)
class Slot:
    index: int
    start: datetime  # offset-aware instant at the site
    end: datetime
    price_per_kwh: float


def build_slots(plan: PlanInput) -> list[Slot]:
    tz = ZoneInfo(plan.timezone)
    slots = []
    t = plan.horizon_start
    while t < plan.horizon_end:
        slots.append(
            Slot(
                index=len(slots),
                start=t.replace(tzinfo=tz),
                end=(t + SLOT).replace(tzinfo=tz),
                price_per_kwh=_price_at(plan, t),
            )
        )
        t += SLOT
    return slots


def _price_at(plan: PlanInput, local_time: datetime) -> float:
    for band in plan.rates:
        if band.start <= local_time < band.end:
            return band.price_per_kwh
    raise ValueError(f"No rate covers {local_time}; run validate_plan first.")


def availability(plan: PlanInput, slots: list[Slot]) -> np.ndarray:
    """avail[v, t] is True when vehicle v is plugged in for the whole of slot t."""
    avail = np.zeros((len(plan.vehicles), len(slots)), dtype=bool)
    for v, vehicle in enumerate(plan.vehicles):
        for slot in slots:
            start = slot.start.replace(tzinfo=None)  # back to local clock time
            avail[v, slot.index] = vehicle.arrival <= start and start + SLOT <= vehicle.departure
    return avail


def slot_prices(slots: list[Slot]) -> np.ndarray:
    return np.array([slot.price_per_kwh for slot in slots])
