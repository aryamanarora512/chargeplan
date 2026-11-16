"""Check that a PlanInput is well-formed and inside the MVP's scope.

`validate_plan` returns a list of Issues; an empty list means "safe to solve".
It does NOT mean every vehicle can be ready -- a valid request can still be
impossible, and that is decided later by the solver.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import PlanInput
from .slots import SLOT

MAX_HORIZON = timedelta(hours=24)
MAX_VEHICLES = 10


@dataclass(frozen=True)
class Issue:
    field: str  # where the problem is, e.g. "vehicles[1].departure"
    message: str  # plain-language explanation for the user


def validate_plan(plan: PlanInput) -> list[Issue]:
    issues = _check_site(plan)
    horizon_issues = _check_horizon(plan)
    issues += horizon_issues
    # Rate coverage and vehicle windows are measured against the horizon,
    # so only check them once the horizon itself makes sense.
    issues += _check_rates(plan, horizon_ok=not horizon_issues)
    issues += _check_vehicles(plan, horizon_ok=not horizon_issues)
    return issues


# ---------------------------------------------------------------- helpers


def _is_finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _fmt(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M")


def _time_issues(field: str, t) -> list[Issue]:
    if not isinstance(t, datetime):
        return [Issue(field, "Enter a date and time.")]
    if t.tzinfo is not None:
        return [Issue(field, "Enter local clock time at the site; the site time zone sets the UTC offset.")]
    if t.minute % 30 or t.second or t.microsecond:
        return [Issue(field, f"{_fmt(t)} is not on a 30-minute boundary (use :00 or :30).")]
    return []


# ---------------------------------------------------------------- checks


def _check_site(plan: PlanInput) -> list[Issue]:
    issues = []
    if not _is_finite(plan.site_limit_kw) or plan.site_limit_kw <= 0:
        issues.append(Issue("site_limit_kw", "The power limit must be a positive number of kW."))
    if not _is_finite(plan.efficiency) or not 0 < plan.efficiency <= 1:
        issues.append(Issue("efficiency", "Efficiency must be more than 0% and at most 100%."))
    return issues


def _check_horizon(plan: PlanInput) -> list[Issue]:
    try:
        tz = ZoneInfo(plan.timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError, OSError):
        return [Issue("timezone", f"Unknown time zone {plan.timezone!r}. Use an IANA name such as 'America/New_York'.")]

    issues = _time_issues("horizon_start", plan.horizon_start) + _time_issues("horizon_end", plan.horizon_end)
    if issues:
        return issues

    start, end = plan.horizon_start, plan.horizon_end
    if end <= start:
        return [Issue("horizon_end", "The night must end after it starts.")]
    if end - start > MAX_HORIZON:
        return [Issue("horizon_end", "The night can be at most 24 hours.")]
    if _crosses_clock_change(tz, start, end):
        return [
            Issue(
                "horizon_start",
                f"This night crosses a daylight-saving clock change in {plan.timezone}. "
                "ChargePlan can't plan those yet.",
            )
        ]
    return []


def _crosses_clock_change(tz: ZoneInfo, start: datetime, end: datetime) -> bool:
    """True if any slot boundary has a different UTC offset than the start,
    or does not exist as a local time (the skipped spring-forward hour)."""
    first_offset = start.replace(tzinfo=tz).utcoffset()
    t = start
    while t <= end:
        aware = t.replace(tzinfo=tz)
        round_trip = aware.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None)
        if aware.utcoffset() != first_offset or round_trip != t:
            return True
        t += SLOT
    return False


def _check_rates(plan: PlanInput, horizon_ok: bool) -> list[Issue]:
    if not plan.rates:
        return [Issue("rates", "Add at least one rate.")]

    issues = []
    for i, band in enumerate(plan.rates):
        field = f"rates[{i}]"
        times = _time_issues(f"{field}.start", band.start) + _time_issues(f"{field}.end", band.end)
        issues += times
        if not times and band.end <= band.start:
            issues.append(Issue(f"{field}.end", "A rate must end after it starts."))
        elif not times and horizon_ok and (band.start < plan.horizon_start or band.end > plan.horizon_end):
            issues.append(Issue(field, f"The rate {_fmt(band.start)}–{_fmt(band.end)} runs outside the night."))
        if not _is_finite(band.price_per_kwh) or band.price_per_kwh < 0:
            issues.append(Issue(f"{field}.price_per_kwh", "A rate must be a number, $0 or more."))
    if issues or not horizon_ok:
        return issues

    # Walk the bands in time order: each must start exactly where the last ended.
    cursor = plan.horizon_start
    for i, band in sorted(enumerate(plan.rates), key=lambda pair: pair[1].start):
        if band.start > cursor:
            issues.append(Issue("rates", f"No rate covers {_fmt(cursor)}–{_fmt(band.start)}."))
        elif band.start < cursor:
            issues.append(Issue(f"rates[{i}]", f"The rate {_fmt(band.start)}–{_fmt(band.end)} overlaps another rate."))
        cursor = max(cursor, band.end)
    if cursor < plan.horizon_end:
        issues.append(Issue("rates", f"No rate covers {_fmt(cursor)}–{_fmt(plan.horizon_end)}."))
    return issues


def _check_vehicles(plan: PlanInput, horizon_ok: bool) -> list[Issue]:
    if not plan.vehicles:
        return [Issue("vehicles", "Add at least one van.")]
    issues = []
    if len(plan.vehicles) > MAX_VEHICLES:
        issues.append(Issue("vehicles", f"ChargePlan plans at most {MAX_VEHICLES} vans at a time."))

    seen_ids = set()
    for i, v in enumerate(plan.vehicles):
        field = f"vehicles[{i}]"
        if not isinstance(v.id, str) or not v.id.strip():
            issues.append(Issue(f"{field}.id", "Each van needs an ID."))
        elif v.id in seen_ids:
            issues.append(Issue(f"{field}.id", f"Van ID {v.id!r} is used more than once."))
        seen_ids.add(v.id)
        if not isinstance(v.name, str) or not v.name.strip():
            issues.append(Issue(f"{field}.name", "Each van needs a name."))
        if not _is_finite(v.energy_needed_kwh) or v.energy_needed_kwh < 0:
            issues.append(Issue(f"{field}.energy_needed_kwh", "Energy to add must be zero or a positive number of kWh."))
        if not _is_finite(v.max_power_kw) or v.max_power_kw <= 0:
            issues.append(Issue(f"{field}.max_power_kw", "Charger power must be a positive number of kW."))

        times = _time_issues(f"{field}.arrival", v.arrival) + _time_issues(f"{field}.departure", v.departure)
        issues += times
        if times:
            continue
        if v.departure <= v.arrival:
            issues.append(Issue(f"{field}.departure", "A van must leave after it arrives."))
        elif horizon_ok and (v.arrival < plan.horizon_start or v.departure > plan.horizon_end):
            issues.append(
                Issue(
                    field,
                    f"{v.name or 'This van'} must arrive and leave within the night "
                    f"({_fmt(plan.horizon_start)} to {_fmt(plan.horizon_end)}).",
                )
            )
    return issues
