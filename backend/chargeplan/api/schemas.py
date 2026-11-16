"""The JSON shape the API accepts, and its conversion to engine inputs.

Pydantic answers "is this well-formed JSON with the right types?" (otherwise 422).
The engine's validate_plan answers "does this make sense as a charging plan?",
and its answers come back inside a normal result with status "invalid".
"""

from dataclasses import asdict
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..engine.models import PlanInput, RateBand, Vehicle

# Generous caps that only bound request size; the engine gives the friendly
# product limits (for example, at most 10 vans).
MAX_RATES = 96
MAX_VEHICLES_IN_REQUEST = 50


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RateIn(_Strict):
    start: datetime  # local clock time at the site, e.g. "2026-10-15T18:00"
    end: datetime
    price_per_kwh: float


class VehicleIn(_Strict):
    id: str = Field(max_length=40)
    name: str = Field(max_length=60)
    arrival: datetime
    departure: datetime
    energy_needed_kwh: float  # into the battery
    max_power_kw: float


class PlanRequest(_Strict):
    timezone: str = Field(max_length=64)
    horizon_start: datetime
    horizon_end: datetime
    site_limit_kw: float
    efficiency: float  # 0.9 means 90%
    rates: list[RateIn] = Field(max_length=MAX_RATES)
    vehicles: list[VehicleIn] = Field(max_length=MAX_VEHICLES_IN_REQUEST)

    def to_engine(self) -> PlanInput:
        return PlanInput(
            timezone=self.timezone,
            horizon_start=self.horizon_start,
            horizon_end=self.horizon_end,
            site_limit_kw=self.site_limit_kw,
            efficiency=self.efficiency,
            rates=tuple(RateBand(r.start, r.end, r.price_per_kwh) for r in self.rates),
            vehicles=tuple(
                Vehicle(v.id, v.name, v.arrival, v.departure, v.energy_needed_kwh, v.max_power_kw) for v in self.vehicles
            ),
        )

    @classmethod
    def from_engine(cls, plan: PlanInput) -> "PlanRequest":
        return cls.model_validate(asdict(plan))
