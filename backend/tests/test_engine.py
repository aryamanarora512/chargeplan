import json
from dataclasses import replace

import numpy as np
import pytest
from pytest import approx

from chargeplan import scenarios
from chargeplan.engine import RateBand, run_plan
from chargeplan.engine.baseline import earliest_departure_first
from chargeplan.engine.planner import COMBINED_CONFLICT
from chargeplan.engine.slots import availability, build_slots
from chargeplan.engine.summary import schedule_cost
from chargeplan.scenarios import SCENARIOS
from helpers import assert_aggregates_match, assert_meets_energy, assert_respects_limits, plan_for, t, van

START, END = "2026-10-15 18:00", "2026-10-16 08:00"


# ------------------------------------------------------------ the worked example


def test_hand_checkable_example_costs_12_and_4_80():
    plan = scenarios.hand_checkable()
    result = run_plan(plan)

    assert result.status == "optimal"
    assert result.baseline.total_cost == approx(12.00)  # 40 kWh at $0.30
    assert result.optimized.total_cost == approx(4.80)  # 40 kWh at $0.12
    assert result.comparison.comparable
    assert result.comparison.savings == approx(7.20)
    assert result.comparison.savings_pct == approx(0.60)

    for summary in (result.optimized, result.baseline):
        assert summary.all_ready
        assert summary.total_grid_kwh == approx(40.0)
        assert_respects_limits(plan, result, summary.grid_kwh)
        assert_meets_energy(plan, summary.grid_kwh)
        assert_aggregates_match(result, summary)

    # Any optimal schedule must put all 40 kWh in the 00:00-06:00 cheap period.
    x = np.array(result.optimized.grid_kwh)
    cheap = [s.index for s in result.slots if s.price_per_kwh == 0.12]
    assert x[:, cheap].sum() == approx(40.0)


# ------------------------------------------------------------ units and conversions


def test_cost_is_price_times_grid_kwh():
    x = np.array([[1.0, 2.0], [3.0, 0.0]])
    prices = np.array([0.10, 0.30])
    assert schedule_cost(x, prices) == approx(1 * 0.10 + 2 * 0.30 + 3 * 0.10)


@pytest.mark.parametrize("eff", [1.0, 0.9, 0.8])
def test_efficiency_converts_battery_kwh_to_grid_kwh(eff):
    plan = replace(scenarios.hand_checkable(), efficiency=eff)
    result = run_plan(plan)
    grid_needed = 2 * 18 / eff
    assert result.optimized.total_grid_kwh == approx(grid_needed)
    assert result.optimized.total_cost == approx(0.12 * grid_needed)  # pay for losses too
    for vs in result.optimized.vehicles:
        assert vs.delivered_kwh == approx(18.0)


# ------------------------------------------------------------ constraints


def test_shared_site_limit_couples_the_vehicles():
    plan = replace(scenarios.hand_checkable(), site_limit_kw=6)  # chargers allow 10 each
    result = run_plan(plan)
    assert result.status == "optimal"
    assert max(result.optimized.site_kw) <= 6 + 1e-6
    assert_respects_limits(plan, result, result.optimized.grid_kwh)
    assert_respects_limits(plan, result, result.baseline.grid_kwh)


def test_per_vehicle_charger_limit_is_respected():
    plan = plan_for(START, END, vehicles=[van("v1", START, END, 18, 3)], site_limit_kw=50)
    result = run_plan(plan)
    assert max(max(row) for row in result.optimized.grid_kwh) <= 3 * 0.5 + 1e-6
    assert_respects_limits(plan, result, result.optimized.grid_kwh)


def test_no_charging_outside_availability_window():
    plan = plan_for(START, END, vehicles=[van("v1", "2026-10-15 22:00", "2026-10-16 02:00", 9, 10)])
    result = run_plan(plan)
    assert_respects_limits(plan, result, result.optimized.grid_kwh)
    assert_respects_limits(plan, result, result.baseline.grid_kwh)


# ------------------------------------------------------------ demo behaviours


def test_flat_rates_give_exactly_zero_savings():
    result = run_plan(scenarios.flat_rates())
    assert result.comparison.comparable
    assert result.comparison.savings == 0.0
    assert result.comparison.savings_pct == 0.0
    assert "cannot change the energy cost" in " ".join(result.explanation)


def test_vehicle_leaving_before_cheap_hours_pays_the_evening_rate():
    result = run_plan(scenarios.early_departure())
    van_a, van_b = result.optimized.vehicles
    assert van_a.cost == approx(20 * 0.30)  # leaves 23:00: no cheap hours available
    assert van_b.cost == approx(20 * 0.12)
    assert result.optimized.total_cost == approx(8.40)
    assert result.comparison.savings == approx(12.00 - 8.40)


def test_zero_energy_vehicle_is_ready_and_costs_nothing():
    vehicles = [van("v1", START, END, 18, 10), van("v2", START, END, 0, 10)]
    result = run_plan(plan_for(START, END, vehicles=vehicles))
    zero = result.optimized.vehicles[1]
    assert result.status == "optimal"
    assert zero.ready and zero.grid_kwh == 0 and zero.cost == 0


def test_zero_baseline_cost_does_not_divide_by_zero():
    result = run_plan(plan_for(START, END, rates=[RateBand(t(START), t(END), 0.0)]))
    assert result.comparison.comparable
    assert result.comparison.savings == 0.0
    assert result.comparison.savings_pct is None


def test_baseline_failure_is_not_scenario_infeasibility():
    plan = scenarios.baseline_misses_departure()
    result = run_plan(plan)

    assert result.status == "optimal"  # the optimizer readies both vans
    assert result.optimized.all_ready
    assert_respects_limits(plan, result, result.optimized.grid_kwh)
    assert_meets_energy(plan, result.optimized.grid_kwh)

    assert result.baseline.ready_count == 1
    van_b = result.baseline.vehicles[1]
    assert not van_b.ready and van_b.shortfall_kwh == approx(12.6)

    # The baseline delivers less energy, so a dollar comparison would mislead.
    assert not result.comparison.comparable
    assert result.comparison.savings is None and result.comparison.savings_pct is None
    assert "leaves 1 vehicle(s) short" in result.comparison.note
    assert "no cost saving is claimed" in " ".join(result.explanation)


# ------------------------------------------------------------ impossible requests


def test_individually_impossible_vehicle_is_named():
    result = run_plan(scenarios.not_enough_time())
    assert result.status == "infeasible"  # valid inputs, impossible request
    assert result.issues == []
    assert result.optimized is None
    assert not result.comparison.comparable
    assert len(result.infeasibility_reasons) == 1
    assert result.infeasibility_reasons[0].startswith("Van B needs 60.00 kWh from the grid")
    assert result.suggestions


def test_total_energy_beyond_site_capacity_is_explained():
    # Each van alone fits in 2 hours at 10 kW, but three need 30 kWh and the site gives 20.
    vehicles = [van(f"v{i}", START, "2026-10-15 20:00", 9, 10) for i in range(3)]
    result = run_plan(plan_for(START, END, vehicles=vehicles))
    assert result.status == "infeasible"
    assert result.infeasibility_reasons[0].startswith("Together the vehicles need 30.00 kWh")


def test_combined_conflict_does_not_invent_a_bottleneck():
    result = run_plan(scenarios.evening_conflict())
    assert result.status == "infeasible"
    assert result.infeasibility_reasons == [COMBINED_CONFLICT]


def test_invalid_inputs_are_not_reported_as_infeasible():
    result = run_plan(plan_for(START, END, efficiency=0))
    assert result.status == "invalid"
    assert result.issues and result.optimized is None and result.baseline is None


# ------------------------------------------------------------ baseline policy


def test_baseline_serves_earliest_departure_first_with_id_tie_break():
    vehicles = [
        van("b", START, "2026-10-16 06:00", 4.5, 10),
        van("a", START, "2026-10-16 06:00", 4.5, 10),  # same departure: "a" wins the tie
        van("c", START, "2026-10-15 23:00", 4.5, 10),  # earliest departure: served first
    ]
    plan = plan_for(START, END, vehicles=vehicles)
    slots = build_slots(plan)
    x = earliest_departure_first(plan, availability(plan, slots))
    # Each van needs 5 grid kWh = one full slot at the 10 kW site limit.
    assert x[2, 0] == approx(5) and x[1, 1] == approx(5) and x[0, 2] == approx(5)
    assert x.sum() == approx(15)


def test_baseline_never_overcharges_or_breaks_limits():
    plan = scenarios.full_depot()
    result = run_plan(plan)
    assert_respects_limits(plan, result, result.baseline.grid_kwh)
    for vs in result.baseline.vehicles:
        assert vs.delivered_kwh <= vs.requested_kwh + 1e-6


# ------------------------------------------------------------ whole-result properties


def test_largest_supported_problem_solves_optimally():
    plan = scenarios.full_depot()
    result = run_plan(plan)
    assert result.status == "optimal"
    assert len(result.slots) == 48 and len(plan.vehicles) == 10
    assert_respects_limits(plan, result, result.optimized.grid_kwh)
    assert_meets_energy(plan, result.optimized.grid_kwh)


@pytest.mark.parametrize("key", sorted(SCENARIOS))
def test_reported_totals_match_the_returned_intervals(key):
    result = run_plan(SCENARIOS[key].build())
    for summary in (result.optimized, result.baseline):
        if summary is not None:
            assert_aggregates_match(result, summary)


@pytest.mark.parametrize("key", sorted(SCENARIOS))
def test_results_are_json_serializable_and_deterministic(key):
    plan = SCENARIOS[key].build()
    first = json.dumps(run_plan(plan).to_dict(), sort_keys=True)
    second = json.dumps(run_plan(plan).to_dict(), sort_keys=True)
    assert first == second
