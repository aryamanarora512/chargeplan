"""An invented depot history for demos and tests. NOT real fleet data.

Six vans with 11 kW chargers. Each night every van is used with 90% probability.
It plugs in around 17:45 and leaves around 06:45 (both +/- about 40 minutes), and
needs about 28 kWh from the grid (+/- 8 kWh, kept between 5 and 55).
"""

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd


def synthetic_sessions(n_nights: int = 120, n_vans: int = 6, first_night: date = date(2026, 4, 1), seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for k in range(n_nights):
        day = first_night + timedelta(days=k)
        for van in range(1, n_vans + 1):
            if rng.random() < 0.10:
                continue  # van not used today
            arrive = datetime.combine(day, time(17, 45)) + timedelta(minutes=float(np.clip(rng.normal(0, 40), -100, 160)))
            depart = datetime.combine(day + timedelta(days=1), time(6, 45)) + timedelta(
                minutes=float(np.clip(rng.normal(0, 40), -100, 160))
            )
            rows.append(
                {
                    "vehicle_id": f"van{van}",
                    "arrival": arrive.replace(second=0, microsecond=0),
                    "departure": depart.replace(second=0, microsecond=0),
                    "energy_kwh": round(float(np.clip(rng.normal(28, 8), 5, 55)), 1),
                    "max_power_kw": 11.0,
                }
            )
    return pd.DataFrame(rows)
