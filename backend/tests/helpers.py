"""Small builders and independent assertions shared by the tests.

The assertion helpers re-check schedules straight from the inputs, without
using the engine's own check_schedule, so a bug there cannot hide a bug here.
"""

from datetime import datetime, timedelta

from pytest import approx

from chargeplan.engine import PlanInput, PlanResult, RateBand, Vehicle

TOL = 1e-6
DT = 0.5


def t(text: str) -> datetime:
    return datetime.fromisoformat(text)


def van(vid: str, arrive: str, depart: str, kwh: float, kw: float, name: str | None = None) -> Vehicle:
    return Vehicle(vid, name or vid, t(arrive), t(depart), kwh, kw)


def plan_for(
    start: str,
    end: str,
    *,
    timezone: str = "America/New_York",
    vehicles=None,
    rates=None,
    site_limit_kw: float = 10,
    efficiency: float = 0.9,
) -> PlanInput:
    """A valid plan by default: one flat rate over the horizon, one van plugged in throughout."""
    return PlanInput(
        timezone=timezone,
        horizon_start=t(start),
        horizon_end=t(end),
        site_limit_kw=site_limit_kw,
        efficiency=efficiency,
        rates=tuple(rates) if rates is not None else (RateBand(t(start), t(end), 0.20),),
        vehicles=tuple(vehicles) if vehicles is not None else (van("v1", start, end, 10, 7),),
    )


def assert_respects_limits(plan: PlanInput, result: PlanResult, grid_kwh: list[list[float]]) -> None:
    """Availability, charger limits and the shared site limit, checked slot by slot."""
    for slot in result.slots:
        start = datetime.fromisoformat(slot.start)
        assert start.utcoffset() is not None, "slot times must be offset-aware"
        local = start.replace(tzinfo=None)
        total = 0.0
        for v, vehicle in enumerate(plan.vehicles):
            kwh = grid_kwh[v][slot.index]
            plugged_in = vehicle.arrival <= local and local + timedelta(minutes=30) <= vehicle.departure
            assert kwh >= -TOL
            assert kwh <= vehicle.max_power_kw * DT + TOL
            if not plugged_in:
                assert abs(kwh) <= TOL, f"{vehicle.name} charges at {local} while unplugged"
            total += kwh
        assert total <= plan.site_limit_kw * DT + TOL, f"site limit exceeded at {local}"


def assert_meets_energy(plan: PlanInput, grid_kwh: list[list[float]]) -> None:
    for v, vehicle in enumerate(plan.vehicles):
        assert plan.efficiency * sum(grid_kwh[v]) == approx(vehicle.energy_needed_kwh, abs=TOL)


def assert_aggregates_match(result: PlanResult, summary) -> None:
    """Totals reported by the engine must equal sums over the returned intervals."""
    x = summary.grid_kwh
    prices = [slot.price_per_kwh for slot in result.slots]
    cost = sum(prices[s] * row[s] for row in x for s in range(len(prices)))
    assert summary.total_cost == approx(cost, abs=1e-9)
    assert summary.total_grid_kwh == approx(sum(map(sum, x)), abs=1e-9)
    for s in range(len(prices)):
        assert summary.site_kw[s] == approx(sum(row[s] for row in x) / DT, abs=1e-9)
    for v, vs in enumerate(summary.vehicles):
        assert vs.grid_kwh == approx(sum(x[v]), abs=1e-9)
        assert vs.cost == approx(sum(prices[s] * x[v][s] for s in range(len(prices))), abs=1e-9)
    assert summary.ready_count == sum(vs.ready for vs in summary.vehicles)
