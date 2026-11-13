# Datasets you can analyze with ChargePlan

*Checked 2026-11-13. "Verified" means we found the dataset's own page or a mirror describing it. We have
not downloaded these datasets, so confirm column names after you download one.*

The savings report needs **charging sessions**: when a vehicle plugged in, when it left, and how much energy it
took. Convert any dataset below into this CSV and run the report:

```text
vehicle_id,arrival,departure,energy_kwh,max_power_kw
van1,2026-04-01 17:42,2026-04-02 06:50,27.3,11
```

```bash
python -m chargeplan.analysis.report --sessions my_sessions.csv --timezone America/Los_Angeles --site-limit 36 --out reports
```

`energy_kwh` is energy **from the grid** (what a charger meter reports); `max_power_kw` is optional. Times with a UTC
offset (such as `...Z`) are converted to the site time zone. The `reports/` folder is git-ignored, so your data isn't
pushed by accident.

## Real session data (best for analysis)

| Dataset | What's in it | Fit for ChargePlan | Access |
|---|---|---|---|
| **[Caltech ACN-Data](https://ev.caltech.edu/dataset)** | Real workplace charging sessions (Caltech, JPL, an office site): connection and disconnection times, kWh delivered, plus drivers' estimated departure and energy request; 4-second charging time series | **Best fit.** It's the rare dataset with requested energy *and* departure, which matches the model's inputs. It's daytime workplace charging, so use e.g. `--horizon-start 06:00`, and pick ≤10 stations per day (the engine's limit) | Free API token; a Python client (`acnportal`) exists |
| **Kaggle: Electric Vehicle Charging Dataset** (`michaelbryantds/electric-vehicle-charging-dataset`, [mirror description](https://baselight.app/u/kaggle/dataset/michaelbryantds_electric_vehicle_charging_dataset)) | 3,395 real sessions, Nov 2014 – Oct 2015, 85 drivers, 105 stations, 25 workplace sites; columns include total kWh and start/end times | Good practice data. Group by site to make "depots" | Free Kaggle account |
| **City of Palo Alto EV charging** ([described here](https://groups.ischool.berkeley.edu/charged_up/index.html)) | Public charging sessions at 9 city locations, through 2020 | Public chargers, not a fleet depot, so good for pandas and visualization practice but weak for fleet claims | City open-data portal |

## Fleet driving data (for realistic energy needs)

| Dataset | What's in it | Use |
|---|---|---|
| **[NREL Fleet DNA](https://www.nrel.gov/fleetdna)** | Real driving data for commercial vehicles, including 974 days from 94 delivery vans | Estimate realistic *daily energy needs* (distance × kWh per mile) to replace the synthetic generator's guesses |

## Synthetic datasets (fine for testing, never as evidence)

| Dataset | Note |
|---|---|
| [Mendeley: Electric Vehicle Charging Dataset](https://data.mendeley.com/datasets/5zrtmp7gwd/1) (Gholizadeh & Musilek, 2024) | Explicitly synthetic, generated from Caltech data with CTGAN and kernel density estimation |
| Kaggle: Electric Vehicle Charging Patterns (`valakhorasani`, [mirror](https://baselight.app/u/kaggle/dataset/valakhorasani_electric_vehicle_charging_patterns)) | 1,320 rows; time of day is only a coarse label (Morning/Afternoon), and a preview is labeled AI-generated. Avoid for any claim |
| ChargePlan's own `synthetic_sessions()` | Invented 6-van history used in the demo report |

## For the battery and solar extension (later)

Tariffs: OpenEI Utility Rate Database. Solar output: NREL PVWatts. Building load profiles: NREL ComStock.
Wholesale prices: CAISO OASIS. All are free and need an account or API key.

## Rules for using any of these

- Label synthetic data as synthetic, everywhere it appears.
- Workplace or public charging data is **not** fleet-depot data. Say so when you present results from it.
- Don't commit a real fleet's data to this public repo. Keep it in `reports/`, which git ignores.
