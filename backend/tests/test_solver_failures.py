"""A timeout or solver crash is not proof that a plan is impossible,
and a solver's 'success' is not trusted without our own check."""

from types import SimpleNamespace

import numpy as np
import pytest

from chargeplan import scenarios
from chargeplan.engine import optimizer, run_plan
from chargeplan.engine.checks import check_schedule
from chargeplan.engine.slots import availability, build_slots


def fake_linprog(status, x=None, message="fake"):
    return lambda *args, **kwargs: SimpleNamespace(status=status, x=x, message=message)


@pytest.mark.parametrize("status, expected", [(1, "solver_limit"), (4, "solver_error")])
def test_solver_limits_and_errors_are_not_called_infeasible(monkeypatch, status, expected):
    monkeypatch.setattr(optimizer, "linprog", fake_linprog(status))
    result = run_plan(scenarios.hand_checkable())
    assert result.status == expected
    assert result.optimized is None
    assert result.infeasibility_reasons == []
    assert "does NOT mean the plan is impossible" in result.explanation[0]


def test_solver_exception_becomes_solver_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("HiGHS crashed")

    monkeypatch.setattr(optimizer, "linprog", boom)
    result = run_plan(scenarios.hand_checkable())
    assert result.status == "solver_error"
    assert "HiGHS crashed" in result.solver_message


def test_solver_success_that_fails_verification_is_rejected(monkeypatch):
    plan = scenarios.hand_checkable()
    n_vars = len(plan.vehicles) * 28
    monkeypatch.setattr(optimizer, "linprog", fake_linprog(0, x=np.zeros(n_vars)))  # charges nothing
    result = run_plan(plan)
    assert result.status == "solver_error"
    assert result.optimized is None
    assert "failed independent verification" in result.solver_message


def test_checker_flags_broken_limits():
    plan = scenarios.hand_checkable()
    slots = build_slots(plan)
    avail = availability(plan, slots)
    x = np.zeros((2, len(slots)))
    x[:, 0] = 5.0  # 2 x 5 kWh in 30 min = 20 kW, above the 10 kW site limit
    x[0, 1] = 50.0  # far above the van's 10 kW charger
    violations = " ".join(check_schedule(plan, slots, avail, x).violations)
    assert "site allowance" in violations
    assert "charger limit" in violations
    assert "more energy than requested" in violations
