"""Bundled demo scenarios.

All of these are SYNTHETIC: invented prices and vehicles chosen to illustrate
one behaviour each. None is measured fleet data or a real utility tariff.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .engine.models import PlanInput, RateBand, Vehicle

TZ = "America/New_York"


def _t(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _overnight_rates() -> tuple[RateBand, ...]:
    """Synthetic evening/overnight/morning rates for 2026-10-15 18:00 to 10-16 08:00."""
    return (
        RateBand(_t("2026-10-15 18:00"), _t("2026-10-16 00:00"), 0.30),
        RateBand(_t("2026-10-16 00:00"), _t("2026-10-16 06:00"), 0.12),
        RateBand(_t("2026-10-16 06:00"), _t("2026-10-16 08:00"), 0.30),
    )


def _overnight(site_limit_kw: float, vehicles: list[Vehicle], rates=None) -> PlanInput:
    return PlanInput(
        timezone=TZ,
        horizon_start=_t("2026-10-15 18:00"),
        horizon_end=_t("2026-10-16 08:00"),
        site_limit_kw=site_limit_kw,
        efficiency=0.9,
        rates=rates or _overnight_rates(),
        vehicles=tuple(vehicles),
    )


def _van(vid: str, name: str, arrive: str, depart: str, kwh: float, kw: float) -> Vehicle:
    return Vehicle(vid, name, _t(arrive), _t(depart), kwh, kw)


def hand_checkable() -> PlanInput:
    """Two vans, 18 kWh each, 10 kW site limit. Checkable with pencil and paper."""
    return _overnight(
        10,
        [
            _van("v1", "Van A", "2026-10-15 18:00", "2026-10-16 08:00", 18, 10),
            _van("v2", "Van B", "2026-10-15 18:00", "2026-10-16 08:00", 18, 10),
        ],
    )


def flat_rates() -> PlanInput:
    """Same vans, one flat rate all night: timing cannot change the energy cost."""
    flat = (RateBand(_t("2026-10-15 18:00"), _t("2026-10-16 08:00"), 0.20),)
    return _overnight(10, list(hand_checkable().vehicles), rates=flat)


def early_departure() -> PlanInput:
    """Van A leaves at 23:00, before the cheap period starts at midnight."""
    return _overnight(
        10,
        [
            _van("v1", "Van A", "2026-10-15 18:00", "2026-10-15 23:00", 18, 10),
            _van("v2", "Van B", "2026-10-15 18:00", "2026-10-16 08:00", 18, 10),
        ],
    )


def baseline_misses_departure() -> PlanInput:
    """A fast-charging van leaving first hogs the site early; the slow van then runs out of time.
    The optimizer readies both by sharing power, so the scenario is feasible."""
    return _overnight(
        11,
        [
            _van("v1", "Van A (fast charger)", "2026-10-15 18:00", "2026-10-16 05:00", 39.6, 11),
            _van("v2", "Van B (slow charger)", "2026-10-15 18:00", "2026-10-16 06:00", 63, 7),
        ],
    )


def not_enough_time() -> PlanInput:
    """Van B needs far more energy than its 3-hour window can provide."""
    return _overnight(
        20,
        [
            _van("v1", "Van A", "2026-10-15 18:00", "2026-10-16 08:00", 18, 10),
            _van("v2", "Van B", "2026-10-15 18:00", "2026-10-15 21:00", 54, 7.2),
        ],
    )


def evening_conflict() -> PlanInput:
    """Each van is fine alone, but Vans A and B both need the 18:00-20:00 window
    and the 10 kW site limit cannot serve both."""
    return _overnight(
        10,
        [
            _van("v1", "Van A", "2026-10-15 18:00", "2026-10-15 20:00", 16.2, 10),
            _van("v2", "Van B", "2026-10-15 18:00", "2026-10-15 20:00", 4.5, 7),
            _van("v3", "Van C", "2026-10-15 18:00", "2026-10-16 08:00", 9, 7),
        ],
    )


def full_depot() -> PlanInput:
    """Largest supported size: 10 vans over a 24-hour horizon (48 slots)."""
    powers = [7.2, 11, 7.2, 19.2, 11, 7.2, 11, 19.2, 7.2, 11]
    energies = [30, 45, 25, 60, 40, 20, 50, 70, 35, 45]
    vehicles = []
    for i in range(10):
        arrive = _t("2026-10-15 15:00").replace(hour=15 + i // 2, minute=30 * (i % 2))
        depart = _t("2026-10-16 05:00").replace(hour=5 + i // 2, minute=30 * (i % 2))
        vehicles.append(Vehicle(f"v{i + 1:02d}", f"Van {i + 1:02d}", arrive, depart, energies[i], powers[i]))
    return PlanInput(
        timezone=TZ,
        horizon_start=_t("2026-10-15 12:00"),
        horizon_end=_t("2026-10-16 12:00"),
        site_limit_kw=60,
        efficiency=0.9,
        rates=(
            RateBand(_t("2026-10-15 12:00"), _t("2026-10-15 17:00"), 0.18),
            RateBand(_t("2026-10-15 17:00"), _t("2026-10-15 21:00"), 0.32),
            RateBand(_t("2026-10-15 21:00"), _t("2026-10-16 07:00"), 0.11),
            RateBand(_t("2026-10-16 07:00"), _t("2026-10-16 12:00"), 0.18),
        ),
        vehicles=tuple(vehicles),
    )


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    build: Callable[[], PlanInput]


SCENARIOS = {
    s.key: s
    for s in [
        Scenario("hand_checkable", "Hand-checkable savings example", hand_checkable),
        Scenario("flat_rates", "Flat rate all night (zero savings)", flat_rates),
        Scenario("early_departure", "A van leaves before cheap hours", early_departure),
        Scenario("baseline_misses_departure", "Baseline misses a departure; optimizer succeeds", baseline_misses_departure),
        Scenario("not_enough_time", "Impossible: not enough time for one van", not_enough_time),
        Scenario("evening_conflict", "Impossible: vans compete for shared power", evening_conflict),
        Scenario("full_depot", "Largest supported size: 10 vans, 24 hours", full_depot),
    ]
}
