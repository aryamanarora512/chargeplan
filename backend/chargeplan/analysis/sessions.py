"""Turn a table of charging sessions (one row per plug-in) into one PlanInput per night.

CSV columns:
    vehicle_id    any label
    arrival       date-time the vehicle plugged in, e.g. 2026-04-01 17:42
    departure     date-time it unplugged (or had to leave)
    energy_kwh    energy drawn FROM THE GRID in that session (what a charger meter reports)
    max_power_kw  optional; that charger's limit (otherwise NightConfig.default_max_power_kw)

Times without a UTC offset are read as local site time; times with one (e.g. "...Z")
are converted to the site time zone.

Real timestamps rarely sit on :00 or :30, so this adapter rounds CONSERVATIVELY:
arrival rounds up and departure rounds down. The engine never sees a longer window
than the one that really happened. Sessions left shorter than one slot are dropped
and counted.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import pandas as pd

from ..engine.models import PlanInput, Vehicle
from ..engine.slots import SLOT
from ..engine.validate import MAX_VEHICLES
from .tariffs import DailyTariff, rates_for_horizon

REQUIRED_COLUMNS = ["vehicle_id", "arrival", "departure", "energy_kwh"]


@dataclass(frozen=True)
class NightConfig:
    timezone: str
    horizon_start: time = time(16, 0)  # each night's plan starts at this clock time
    horizon_hours: int = 18  # and lasts this long (at most 24)
    site_limit_kw: float = 36.0
    efficiency: float = 0.9
    default_max_power_kw: float = 11.0


@dataclass
class Night:
    date: date
    plan: PlanInput | None  # None when the night was skipped
    skipped: str  # why it was skipped; "" if usable
    dropped_sessions: int  # sessions shorter than one slot after rounding


def load_sessions(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Session file is missing column(s): {', '.join(missing)}")
    return df


def _local_naive(column: pd.Series, timezone: str) -> pd.Series:
    times = pd.to_datetime(column, format="mixed")
    if times.dt.tz is not None:
        times = times.dt.tz_convert(timezone).dt.tz_localize(None)
    return times


def _round_up(t: datetime) -> datetime:
    floor = _round_down(t)
    return floor if floor == t else floor + SLOT


def _round_down(t: datetime) -> datetime:
    return t.replace(minute=30 * (t.minute // 30), second=0, microsecond=0)


def nights_from_sessions(sessions: pd.DataFrame, tariff: DailyTariff, cfg: NightConfig) -> list[Night]:
    df = sessions.copy()
    df["arrival"] = _local_naive(df["arrival"], cfg.timezone)
    df["departure"] = _local_naive(df["departure"], cfg.timezone)
    df = df.sort_values(["arrival", "vehicle_id"], kind="stable")

    # A session belongs to the night whose horizon its arrival falls in. An arrival in
    # the daytime gap between one night's end and the next night's start belongs to
    # the next night (it simply waits until that night's plan begins).
    offset = timedelta(hours=cfg.horizon_start.hour, minutes=cfg.horizon_start.minute)
    night_start = (df["arrival"] - offset).dt.normalize() + offset
    in_gap = df["arrival"] >= night_start + timedelta(hours=cfg.horizon_hours)
    night_of = (night_start + pd.to_timedelta(in_gap.astype(int), unit="D")).dt.date

    nights = []
    for night_date, group in df.groupby(night_of, sort=True):
        start = datetime.combine(night_date, cfg.horizon_start)
        end = start + timedelta(hours=cfg.horizon_hours)
        vehicles, dropped, seen = [], 0, {}
        for row in group.itertuples(index=False):
            arrive = max(_round_up(row.arrival.to_pydatetime()), start)
            depart = min(_round_down(row.departure.to_pydatetime()), end)
            if depart - arrive < SLOT:
                dropped += 1
                continue
            label = str(row.vehicle_id)
            seen[label] = seen.get(label, 0) + 1
            vid = label if seen[label] == 1 else f"{label}~{seen[label]}"  # a 2nd plug-in is its own job
            power = getattr(row, "max_power_kw", float("nan"))
            vehicles.append(
                Vehicle(
                    id=vid,
                    name=vid,
                    arrival=arrive,
                    departure=depart,
                    energy_needed_kwh=float(row.energy_kwh) * cfg.efficiency,  # grid kWh -> battery kWh
                    max_power_kw=cfg.default_max_power_kw if pd.isna(power) else float(power),
                )
            )

        if not vehicles:
            nights.append(Night(night_date, None, "no usable sessions", dropped))
        elif len(vehicles) > MAX_VEHICLES:
            nights.append(Night(night_date, None, f"more than {MAX_VEHICLES} sessions", dropped))
        else:
            plan = PlanInput(
                timezone=cfg.timezone,
                horizon_start=start,
                horizon_end=end,
                site_limit_kw=cfg.site_limit_kw,
                efficiency=cfg.efficiency,
                rates=rates_for_horizon(tariff, start, end),
                vehicles=tuple(vehicles),
            )
            nights.append(Night(night_date, plan, "", dropped))
    return nights
