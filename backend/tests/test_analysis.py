from datetime import date, time

import numpy as np
import pandas as pd
import pytest
from pytest import approx

from chargeplan import scenarios
from chargeplan.analysis.estimate import annual_estimate, nightly_savings, readiness_sweep, replay
from chargeplan.analysis.report import build_report
from chargeplan.analysis.sessions import NightConfig, nights_from_sessions
from chargeplan.analysis.synthetic import synthetic_sessions
from chargeplan.analysis.tariffs import PGE_BEV1, SYNTHETIC_TOU, DailyTariff, rates_for_horizon
from chargeplan.engine.baseline import shared_timer
from chargeplan.engine.checks import check_schedule
from chargeplan.engine.slots import availability, build_slots, slot_prices
from chargeplan.engine.summary import schedule_cost
from helpers import t

CFG = NightConfig(timezone="America/Los_Angeles")


def session(arrive, depart, kwh=20.0, vid="van1", **extra):
    return {"vehicle_id": vid, "arrival": arrive, "departure": depart, "energy_kwh": kwh, **extra}


# ------------------------------------------------------------ shared timer baseline


def test_timer_waits_then_can_match_the_optimum():
    plan = scenarios.hand_checkable()
    slots = build_slots(plan)
    avail = availability(plan, slots)
    x = shared_timer(plan, avail, first_slot=12)  # 00:00, start of the cheap period
    assert x[:, :12].sum() == 0
    assert check_schedule(plan, slots, avail, x).all_ready
    assert schedule_cost(x, slot_prices(slots)) == approx(4.80)  # a timer is enough here


def test_timer_strands_a_vehicle_that_leaves_before_it_starts():
    plan = scenarios.early_departure()  # Van A leaves at 23:00
    slots = build_slots(plan)
    avail = availability(plan, slots)
    check = check_schedule(plan, slots, avail, shared_timer(plan, avail, first_slot=12))
    assert check.ready == [False, True]


# ------------------------------------------------------------ tariffs


def test_daily_tariff_wraps_midnight_and_merges_equal_prices():
    PGE_BEV1.check()
    bands = rates_for_horizon(PGE_BEV1, t("2026-04-01 16:00"), t("2026-04-02 10:00"))
    assert [(b.start.strftime("%H:%M"), b.end.strftime("%H:%M"), b.price_per_kwh) for b in bands] == [
        ("16:00", "21:00", 0.35711),
        ("21:00", "09:00", 0.16510),
        ("09:00", "10:00", 0.13844),
    ]


@pytest.mark.parametrize(
    "bands",
    [
        (("00:00", "12:00", 0.2),),  # gap 12:00-24:00
        (("00:00", "13:00", 0.2), ("12:00", "00:00", 0.1)),  # overlap 12:00-13:00
    ],
)
def test_daily_tariff_must_cover_every_slot_once(bands):
    with pytest.raises(ValueError):
        DailyTariff("bad", bands).check()


# ------------------------------------------------------------ sessions -> nights


def test_sessions_round_conservatively_and_convert_grid_to_battery_energy():
    df = pd.DataFrame([session("2026-04-01 17:10", "2026-04-02 06:50", kwh=20.0)])
    (night,) = nights_from_sessions(df, SYNTHETIC_TOU, CFG)
    (v,) = night.plan.vehicles
    assert v.arrival == t("2026-04-01 17:30")  # rounded up
    assert v.departure == t("2026-04-02 06:30")  # rounded down
    assert v.energy_needed_kwh == approx(18.0)  # 20 grid kWh at 90%


def test_daytime_arrival_waits_for_the_next_night():
    df = pd.DataFrame([session("2026-04-01 13:00", "2026-04-02 07:00")])
    (night,) = nights_from_sessions(df, SYNTHETIC_TOU, CFG)
    assert night.date == date(2026, 4, 1)
    assert night.plan.vehicles[0].arrival == t("2026-04-01 16:00")  # clipped to the plan start


def test_sessions_too_short_after_rounding_are_dropped_and_counted():
    df = pd.DataFrame([session("2026-04-01 17:10", "2026-04-01 17:50"), session("2026-04-01 18:00", "2026-04-02 06:00", vid="van2")])
    (night,) = nights_from_sessions(df, SYNTHETIC_TOU, CFG)
    assert night.dropped_sessions == 1
    assert [v.id for v in night.plan.vehicles] == ["van2"]


def test_more_than_ten_sessions_skips_the_night():
    df = pd.DataFrame([session("2026-04-01 18:00", "2026-04-02 06:00", vid=f"v{i}") for i in range(11)])
    (night,) = nights_from_sessions(df, SYNTHETIC_TOU, CFG)
    assert night.plan is None and "more than 10" in night.skipped


def test_utc_timestamps_are_converted_to_site_time():
    df = pd.DataFrame([session("2026-04-02T00:42:00Z", "2026-04-02T13:30:00Z")])  # 17:42 -> 06:30 PDT
    (night,) = nights_from_sessions(df, SYNTHETIC_TOU, CFG)
    v = night.plan.vehicles[0]
    assert (v.arrival, v.departure) == (t("2026-04-01 18:00"), t("2026-04-02 06:30"))


def test_second_plug_in_same_night_is_its_own_job():
    df = pd.DataFrame([session("2026-04-01 17:00", "2026-04-01 19:00"), session("2026-04-01 21:00", "2026-04-02 06:00")])
    (night,) = nights_from_sessions(df, SYNTHETIC_TOU, CFG)
    assert [v.id for v in night.plan.vehicles] == ["van1", "van1~2"]


# ------------------------------------------------------------ replay and estimates


@pytest.fixture(scope="module")
def replayed():
    return replay(nights_from_sessions(synthetic_sessions(n_nights=20), SYNTHETIC_TOU, CFG), timer_at=time(0, 0))


def test_optimizer_never_costs_more_than_a_baseline_that_readies_everyone(replayed):
    n = replayed.nights
    for baseline in ("arrival", "timer"):
        both = n["ready_optimized"] & n[f"ready_{baseline}"]
        assert (n.loc[both, "cost_optimized"] <= n.loc[both, f"cost_{baseline}"] + 1e-9).all()
        assert (nightly_savings(n, baseline) >= 0).all()


def test_savings_ignore_nights_where_the_baseline_left_someone_short():
    nights = pd.DataFrame(
        {
            "ready_optimized": [True, True],
            "ready_timer": [True, False],
            "cost_optimized": [10.0, 10.0],
            "cost_timer": [12.0, 3.0],  # night 2 is "cheaper" only because a van went short
        }
    )
    assert list(nightly_savings(nights, "timer")) == [2.0]


def test_average_profiles_cover_every_slot(replayed):
    for profile in replayed.profiles.values():
        assert profile.shape == (20, len(replayed.slot_clock))
    assert len(replayed.slot_clock) == 36  # 18 hours of 30-minute slots


def test_annual_estimate_bootstrap():
    flat = annual_estimate(np.array([2.0, 2.0, 2.0]))
    assert (flat.annual, flat.low, flat.high, flat.nights) == (730.0, 730.0, 730.0, 3)
    assert annual_estimate(np.array([])) is None
    noisy = np.random.default_rng(1).normal(5, 2, size=60)
    a, b = annual_estimate(noisy, seed=3), annual_estimate(noisy, seed=3)
    assert a == b  # reproducible
    assert a.low < a.annual < a.high


def test_more_power_never_makes_the_optimizer_less_ready():
    sweep = readiness_sweep(synthetic_sessions(n_nights=15), PGE_BEV1, CFG, time(21, 0), [12, 18, 36])
    share = sweep[sweep["policy"] == "optimized"].sort_values("allowance_kw")["share_ready"].to_numpy()
    assert (np.diff(share) >= 0).all()
    assert share[-1] == 1.0


def test_report_writes_charts_tables_and_summary(tmp_path):
    build_report(synthetic_sessions(n_nights=8), CFG, ["synthetic_tou", "pge_bev1"], tmp_path,
                 source="test", label="test", sweep_kw=(18, 36))
    for name in ["summary.md", "savings-light.svg", "savings-dark.svg", "nights-pge_bev1.csv",
                 "power-profile-synthetic_tou-dark.svg", "readiness-pge_bev1-light.svg"]:
        assert (tmp_path / name).stat().st_size > 0
    assert "Shared timer" in (tmp_path / "summary.md").read_text()
