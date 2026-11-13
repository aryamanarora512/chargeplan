"""Estimate savings by replaying real (or synthetic) nights through three policies.

For every night we compute:
    optimized  the LP schedule (lowest modeled energy cost, every vehicle ready)
    arrival    charge as soon as vehicles arrive, earliest departure first
    timer      one site-wide timer, then earliest departure first (the DIY alternative)

"Predicting" savings here means: assume future nights look like these nights, and
report the average with a bootstrap interval. No machine learning is needed: given
a night's inputs the engine computes cost exactly, so the uncertainty is in WHICH
nights come next, not in the cost formula.
"""

from dataclasses import dataclass, replace
from datetime import time

import numpy as np
import pandas as pd

from ..engine.baseline import shared_timer
from ..engine.checks import check_schedule
from ..engine.planner import run_plan
from ..engine.slots import DT_HOURS, availability, build_slots, slot_prices
from ..engine.summary import MONEY_NOISE, schedule_cost
from .sessions import Night, NightConfig, nights_from_sessions
from .tariffs import DailyTariff

POLICIES = ("optimized", "timer", "arrival")
POLICY_LABELS = {
    "optimized": "ChargePlan (optimized)",
    "timer": "Shared timer",
    "arrival": "Charge on arrival",
}


@dataclass
class Replay:
    nights: pd.DataFrame  # one row per night: status, costs and readiness per policy
    profiles: dict[str, np.ndarray]  # policy -> site kW, shape (optimal nights, slots)
    slot_clock: list[time]  # clock time at the start of each slot
    slot_price: list[float]


def _timer_slot(slots, timer_at: time) -> int:
    for slot in slots:
        if slot.start.time() == timer_at:
            return slot.index
    raise ValueError(f"Timer time {timer_at:%H:%M} is not inside the planning horizon.")


def replay(nights: list[Night], timer_at: time) -> Replay:
    rows, profiles = [], {p: [] for p in POLICIES}
    slot_clock, slot_price = [], []
    for night in nights:
        row = {"date": night.date, "dropped_sessions": night.dropped_sessions}
        if night.plan is None:
            rows.append(row | {"status": f"skipped: {night.skipped}"})
            continue
        plan = night.plan
        result = run_plan(plan)
        row |= {"vehicles": len(plan.vehicles), "grid_kwh_needed": sum(v.energy_needed_kwh for v in plan.vehicles) / plan.efficiency}
        if result.status == "invalid":
            rows.append(row | {"status": "invalid: " + result.issues[0].message})
            continue

        slots = build_slots(plan)
        avail = availability(plan, slots)
        prices = slot_prices(slots)
        timer_x = shared_timer(plan, avail, _timer_slot(slots, timer_at))
        timer_check = check_schedule(plan, slots, avail, timer_x)

        row |= {
            "status": result.status,
            "cost_arrival": result.baseline.total_cost,
            "ready_arrival": result.baseline.all_ready,
            "cost_timer": schedule_cost(timer_x, prices),
            "ready_timer": timer_check.all_ready,
            "cost_optimized": result.optimized.total_cost if result.optimized else np.nan,
            "ready_optimized": result.status == "optimal",
        }
        rows.append(row)

        if result.status == "optimal":
            profiles["optimized"].append(result.optimized.site_kw)
            profiles["arrival"].append(result.baseline.site_kw)
            profiles["timer"].append((timer_x.sum(axis=0) / DT_HOURS).tolist())
            if not slot_clock:
                slot_clock = [s.start.time() for s in slots]
                slot_price = prices.tolist()

    df = pd.DataFrame(rows)
    for p in POLICIES:  # nights that never reached the solver count as "not ready"
        col = f"ready_{p}"
        df[col] = df[col].fillna(False).astype(bool) if col in df else False
    return Replay(df, {p: np.array(v) for p, v in profiles.items()}, slot_clock, slot_price)


def nightly_savings(nights: pd.DataFrame, baseline: str) -> np.ndarray:
    """Baseline cost minus optimized cost, ONLY on nights where both ready every vehicle
    (so both delivered the same energy). Other nights are not comparable in dollars."""
    ok = nights["ready_optimized"] & nights[f"ready_{baseline}"]
    savings = (nights.loc[ok, f"cost_{baseline}"] - nights.loc[ok, "cost_optimized"]).to_numpy(dtype=float)
    return np.where(np.abs(savings) < MONEY_NOISE, 0.0, savings)  # round-off is not a saving


@dataclass
class Estimate:
    per_night: float  # mean savings per comparable night
    annual: float  # per_night * nights_per_year
    low: float  # bootstrap interval for `annual`
    high: float
    nights: int  # how many comparable nights it's based on
    level: float


def annual_estimate(savings: np.ndarray, nights_per_year: int = 365, level: float = 0.90, n_boot: int = 5000, seed: int = 0) -> Estimate | None:
    """Bootstrap: resample the observed nights with replacement many times and see how
    much the average moves. The interval reflects night-to-night variation in THIS
    history only, not future changes to tariffs, routes, or the fleet."""
    if len(savings) == 0:
        return None
    rng = np.random.default_rng(seed)
    means = rng.choice(savings, size=(n_boot, len(savings)), replace=True).mean(axis=1)
    lo, hi = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    mean = float(savings.mean())
    return Estimate(mean, mean * nights_per_year, float(lo) * nights_per_year, float(hi) * nights_per_year, len(savings), level)


def readiness_sweep(sessions: pd.DataFrame, tariff: DailyTariff, cfg: NightConfig, timer_at: time, allowances) -> pd.DataFrame:
    """Share of nights on which each policy readies every vehicle, for a range of
    EV charging allowances. Answers: how much power does this fleet actually need?"""
    rows = []
    for kw in allowances:
        nights = replay(nights_from_sessions(sessions, tariff, replace(cfg, site_limit_kw=kw)), timer_at).nights
        usable = nights[~nights["status"].str.startswith(("skipped", "invalid"))]
        for p in POLICIES:
            rows.append({"allowance_kw": kw, "policy": p, "share_ready": float(usable[f"ready_{p}"].mean()), "nights": len(usable)})
    return pd.DataFrame(rows)
