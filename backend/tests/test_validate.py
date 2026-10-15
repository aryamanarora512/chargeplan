from dataclasses import replace

import pytest

from chargeplan.engine import RateBand, run_plan, validate_plan
from chargeplan.scenarios import SCENARIOS
from helpers import plan_for, t, van

START, END = "2026-10-15 18:00", "2026-10-16 08:00"


def messages(plan) -> str:
    return " | ".join(f"{i.field}: {i.message}" for i in validate_plan(plan))


@pytest.mark.parametrize("key", sorted(SCENARIOS))
def test_bundled_scenarios_are_valid(key):
    assert validate_plan(SCENARIOS[key].build()) == []


# ------------------------------------------------------------ rate bands


def test_rate_gap_is_reported():
    rates = [RateBand(t(START), t("2026-10-16 00:00"), 0.3), RateBand(t("2026-10-16 01:00"), t(END), 0.1)]
    assert "No rate covers 2026-10-16 00:00–2026-10-16 01:00" in messages(plan_for(START, END, rates=rates))


def test_rate_overlap_is_reported():
    rates = [RateBand(t(START), t("2026-10-16 01:00"), 0.3), RateBand(t("2026-10-16 00:00"), t(END), 0.1)]
    assert "overlaps another band" in messages(plan_for(START, END, rates=rates))


def test_rates_must_reach_the_end_of_the_horizon():
    rates = [RateBand(t(START), t("2026-10-16 06:00"), 0.3)]
    assert "No rate covers 2026-10-16 06:00–2026-10-16 08:00" in messages(plan_for(START, END, rates=rates))


def test_rate_band_outside_horizon_is_rejected():
    rates = [RateBand(t("2026-10-15 17:00"), t(END), 0.3)]
    assert "outside the planning horizon" in messages(plan_for(START, END, rates=rates))


def test_rates_in_any_order_are_accepted_when_they_tile_the_horizon():
    rates = [RateBand(t("2026-10-16 00:00"), t(END), 0.1), RateBand(t(START), t("2026-10-16 00:00"), 0.3)]
    assert validate_plan(plan_for(START, END, rates=rates)) == []


@pytest.mark.parametrize("price", [-0.01, float("nan"), float("inf")])
def test_negative_or_nonfinite_rates_are_rejected(price):
    rates = [RateBand(t(START), t(END), price)]
    assert "rates[0].price_per_kwh" in messages(plan_for(START, END, rates=rates))


def test_zero_rate_is_allowed():
    assert validate_plan(plan_for(START, END, rates=[RateBand(t(START), t(END), 0.0)])) == []


# ------------------------------------------------------------ numbers


@pytest.mark.parametrize("eff", [0, -0.5, 1.01, float("nan")])
def test_efficiency_must_be_in_zero_one(eff):
    assert "efficiency" in messages(plan_for(START, END, efficiency=eff))


def test_efficiency_of_exactly_one_is_allowed():
    assert validate_plan(plan_for(START, END, efficiency=1.0)) == []


@pytest.mark.parametrize("limit", [0, -5, float("inf")])
def test_site_limit_must_be_positive_and_finite(limit):
    assert "site_limit_kw" in messages(plan_for(START, END, site_limit_kw=limit))


@pytest.mark.parametrize(
    "vehicle, field",
    [
        (van("v1", START, END, -1, 7), "energy_needed_kwh"),
        (van("v1", START, END, float("nan"), 7), "energy_needed_kwh"),
        (van("v1", START, END, 10, 0), "max_power_kw"),
        (van("v1", START, END, 10, float("inf")), "max_power_kw"),
    ],
)
def test_bad_vehicle_numbers_are_rejected(vehicle, field):
    assert f"vehicles[0].{field}" in messages(plan_for(START, END, vehicles=[vehicle]))


def test_zero_energy_need_is_valid():
    assert validate_plan(plan_for(START, END, vehicles=[van("v1", START, END, 0, 7)])) == []


# ------------------------------------------------------------ vehicles and times


def test_times_must_align_to_30_minute_slots():
    plan = plan_for(START, END, vehicles=[van("v1", "2026-10-15 18:15", END, 10, 7)])
    assert "not on a 30-minute boundary" in messages(plan)


def test_seconds_are_not_silently_rounded():
    plan = plan_for(START, END, vehicles=[van("v1", START, "2026-10-16 07:59:59", 10, 7)])
    assert "vehicles[0].departure" in messages(plan)


def test_departure_must_follow_arrival():
    plan = plan_for(START, END, vehicles=[van("v1", "2026-10-16 02:00", "2026-10-16 01:00", 10, 7)])
    assert "Departure must be after arrival" in messages(plan)


def test_vehicle_must_fit_inside_horizon():
    plan = plan_for(START, END, vehicles=[van("v1", START, "2026-10-16 09:00", 10, 7)])
    assert "within the planning horizon" in messages(plan)


def test_at_least_one_and_at_most_ten_vehicles():
    assert "Add at least one vehicle" in messages(plan_for(START, END, vehicles=[]))
    eleven = [van(f"v{i}", START, END, 1, 7) for i in range(11)]
    assert "at most 10 vehicles" in messages(plan_for(START, END, vehicles=eleven))


def test_vehicle_ids_must_be_unique():
    plan = plan_for(START, END, vehicles=[van("v1", START, END, 1, 7), van("v1", START, END, 1, 7)])
    assert "used more than once" in messages(plan)


def test_horizon_longer_than_24_hours_is_rejected():
    assert "at most 24 hours" in messages(plan_for("2026-10-15 08:00", "2026-10-16 08:30"))


def test_exactly_24_hour_horizon_is_allowed():
    assert validate_plan(plan_for("2026-10-15 12:00", "2026-10-16 12:00")) == []


def test_unknown_time_zone_is_rejected():
    assert "Unknown time zone" in messages(plan_for(START, END, timezone="Mars/Olympus_Mons"))


def test_offset_aware_input_times_are_rejected():
    plan = plan_for(START, END)
    aware = replace(plan, horizon_start=t("2026-10-15 18:00-04:00"))
    assert "local clock time" in messages(aware)


# ------------------------------------------------------------ daylight saving


@pytest.mark.parametrize(
    "tz, start, end",
    [
        ("America/New_York", "2026-10-31 18:00", "2026-11-01 08:00"),  # fall back
        ("America/New_York", "2026-03-07 18:00", "2026-03-08 08:00"),  # spring forward
        ("America/New_York", "2026-03-07 20:00", "2026-03-08 02:00"),  # ends in the skipped hour
        ("Europe/London", "2026-10-24 18:00", "2026-10-25 08:00"),  # not only a US rule
    ],
)
def test_horizons_crossing_a_clock_change_are_rejected_clearly(tz, start, end):
    result = run_plan(plan_for(start, end, timezone=tz))
    assert result.status == "invalid"
    assert "daylight-saving clock change" in messages(plan_for(start, end, timezone=tz))


def test_ordinary_overnight_across_new_year_is_supported():
    result = run_plan(plan_for("2026-12-31 18:00", "2027-01-01 08:00"))
    assert result.status == "optimal"
    assert len(result.slots) == 28
    assert result.slots[0].start == "2026-12-31T18:00:00-05:00"
    assert result.slots[-1].end == "2027-01-01T08:00:00-05:00"
