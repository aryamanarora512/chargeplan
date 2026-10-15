"""Plain data types for one overnight charging plan.

These are deliberately simple frozen dataclasses with no web or database
code. All times are *local wall-clock* times at the depot (naive datetimes,
no tzinfo); the plan's IANA time zone says which UTC offset applies.

Units:
    energy  -> kWh
    power   -> kW
    price   -> dollars per kWh
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Vehicle:
    id: str  # stable identifier, used to break ties deterministically
    name: str
    arrival: datetime  # local time the vehicle is plugged in
    departure: datetime  # local time it must leave (charging stops by then)
    energy_needed_kwh: float  # energy to ADD TO THE BATTERY (after losses)
    max_power_kw: float  # charger limit, measured at the grid/charger input


@dataclass(frozen=True)
class RateBand:
    start: datetime
    end: datetime
    price_per_kwh: float  # energy rate only; no demand charges or fees


@dataclass(frozen=True)
class PlanInput:
    timezone: str  # IANA name, e.g. "America/New_York"
    horizon_start: datetime
    horizon_end: datetime
    site_limit_kw: float  # power reserved for EV charging, not the building rating
    efficiency: float  # battery kWh gained per grid kWh, in (0, 1]
    rates: tuple[RateBand, ...]
    vehicles: tuple[Vehicle, ...]
