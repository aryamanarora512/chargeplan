"""Daily time-of-use tariffs that repeat every day, turned into rate bands for one night.

A DailyTariff lists (start, end, $/kWh) by clock time and must cover all 24 hours.
A band may wrap past midnight, e.g. ("21:00", "09:00", 0.165).
"""

from dataclasses import dataclass
from datetime import datetime, time

from ..engine.models import RateBand
from ..engine.slots import SLOT

SLOTS_PER_DAY = 48


@dataclass(frozen=True)
class DailyTariff:
    name: str
    bands: tuple[tuple[str, str, float], ...]  # ("HH:MM", "HH:MM", price)
    note: str = ""

    def price_at(self, clock: time) -> float:
        for band in self.bands:
            if _covers(band, clock):
                return band[2]
        raise ValueError(f"{self.name}: no price covers {clock:%H:%M}")

    def check(self) -> None:
        """Every 30-minute slot of the day must be covered exactly once."""
        for k in range(SLOTS_PER_DAY):
            clock = time(k // 2, 30 * (k % 2))
            hits = [b for b in self.bands if _covers(b, clock)]
            if len(hits) != 1:
                raise ValueError(f"{self.name}: {clock:%H:%M} is covered by {len(hits)} bands (must be exactly 1)")


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _covers(band, clock: time) -> bool:
    start, end, _ = band
    s, e, minute = _minutes(start), _minutes(end), clock.hour * 60 + clock.minute
    return s <= minute < e if s < e else (minute >= s or minute < e)  # second case wraps midnight


def rates_for_horizon(tariff: DailyTariff, start: datetime, end: datetime) -> tuple[RateBand, ...]:
    """One RateBand per run of equal prices between `start` and `end` (local times)."""
    bands = []
    t = start
    while t < end:
        price = tariff.price_at(t.time())
        if bands and bands[-1].price_per_kwh == price:
            bands[-1] = RateBand(bands[-1].start, t + SLOT, price)
        else:
            bands.append(RateBand(t, t + SLOT, price))
        t += SLOT
    return tuple(bands)


SYNTHETIC_TOU = DailyTariff(
    "Synthetic overnight TOU",
    (("06:00", "00:00", 0.30), ("00:00", "06:00", 0.12)),
    "Invented prices used in the hand-checkable example. Not a real tariff.",
)

# PG&E Electric Schedule BEV, BEV-1 total energy rates effective 2026-03-01.
# Energy only: the kW subscription ($12.41 per 10 kW block per month) is not included.
PGE_BEV1 = DailyTariff(
    "PG&E BEV-1 energy rates",
    (
        ("16:00", "21:00", 0.35711),  # peak
        ("21:00", "09:00", 0.16510),  # off-peak (overnight)
        ("09:00", "14:00", 0.13844),  # super off-peak
        ("14:00", "16:00", 0.16510),  # off-peak (afternoon)
    ),
    "PG&E Schedule BEV, BEV-1, effective 2026-03-01; energy charges only.",
)

TARIFFS = {"synthetic_tou": SYNTHETIC_TOU, "pge_bev1": PGE_BEV1}
