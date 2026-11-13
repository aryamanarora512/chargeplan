"""Build a savings report from a history of charging sessions.

    python -m chargeplan.analysis.report --demo --out ../docs/analysis
    python -m chargeplan.analysis.report --sessions my_sessions.csv --timezone America/Los_Angeles \
        --site-limit 36 --tariff pge_bev1 --out reports

Writes, into --out:
    summary.md                       every number, as tables (the charts' text twin)
    power-profile-<tariff>-*.svg     average charging power across the night
    readiness-<tariff>-*.svg         share of nights all vans ready vs. charging allowance
    savings-*.svg                    estimated annual savings with 90% intervals
    nights-<tariff>.csv              one row per night, every policy
"""

import argparse
from datetime import time
from pathlib import Path

import pandas as pd

from .charts import THEMES, power_profile, readiness_sizing, save, savings_estimate
from .estimate import POLICIES, POLICY_LABELS, annual_estimate, nightly_savings, readiness_sweep, replay
from .sessions import NightConfig, load_sessions, nights_from_sessions
from .synthetic import synthetic_sessions
from .tariffs import TARIFFS

# When a site-wide timer would sensibly start for each tariff: the start of the cheap
# overnight period.
DEFAULT_TIMERS = {"synthetic_tou": time(0, 0), "pge_bev1": time(21, 0)}


def _picture(stem: str, alt: str) -> str:
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="{stem}-dark.svg">'
        f'<img alt="{alt}" src="{stem}-light.svg"></picture>'
    )


def _money(v) -> str:
    return "-" if pd.isna(v) else f"${v:,.2f}"


def build_report(sessions: pd.DataFrame, cfg: NightConfig, tariff_keys, out_dir, *, source: str, label: str, timers=None, sweep_kw=(12, 15, 18, 21, 24, 30, 36)) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    timers = {**DEFAULT_TIMERS, **(timers or {})}
    estimates, md = {}, [
        "# Savings report",
        "",
        f"**Data:** {source}  ",
        f"**Site:** {cfg.timezone}, nightly plan {cfg.horizon_start:%H:%M} + {cfg.horizon_hours} h, "
        f"EV charging allowance {cfg.site_limit_kw:g} kW, efficiency {cfg.efficiency * 100:g}%  ",
        f"**Sessions:** {len(sessions)}",
        "",
        "Costs are modeled **energy charges only** (no demand or subscription charges, fees, or taxes). "
        "Savings are compared only on nights where both plans ready every van, so both deliver the same energy.",
    ]

    for key in tariff_keys:
        tariff = TARIFFS[key]
        tariff.check()
        timer = timers[key]
        rep = replay(nights_from_sessions(sessions, tariff, cfg), timer)
        nights = rep.nights
        nights.to_csv(out / f"nights-{key}.csv", index=False)
        est = {b: annual_estimate(nightly_savings(nights, b)) for b in ("arrival", "timer")}
        estimates[tariff.name] = est
        sweep = readiness_sweep(sessions, tariff, cfg, timer, sweep_kw)
        detail = f"{label} · {tariff.name} · timer at {timer:%H:%M}"

        for theme in THEMES:
            if rep.profiles["optimized"].size:
                save(power_profile(rep, site_limit_kw=cfg.site_limit_kw, title_detail=detail, theme=theme),
                     out / f"power-profile-{key}-{theme}.svg", theme)
            save(readiness_sizing(sweep, title_detail=detail, theme=theme), out / f"readiness-{key}-{theme}.svg", theme)

        usable = nights[~nights["status"].str.startswith(("skipped", "invalid"))]
        md += ["", f"## {tariff.name}", "", f"*{tariff.note}* Shared timer starts at {timer:%H:%M}.", ""]
        md += [f"Nights: {len(nights)} total, {len(usable)} usable, "
               f"{int((nights['status'] == 'infeasible').sum())} impossible even for the optimizer, "
               f"{int(nights['dropped_sessions'].sum())} sessions dropped by conservative rounding.", ""]
        md += ["| Policy | Nights every van ready | Mean energy cost on those nights |", "|---|---:|---:|"]
        for p in POLICIES:
            ready = usable[usable[f"ready_{p}"]]
            md.append(f"| {POLICY_LABELS[p]} | {len(ready)}/{len(usable)} | {_money(ready[f'cost_{p}'].mean())} |")
        md += ["", "| ChargePlan savings | Per night | Per year (x365) | 90% interval | Nights compared |", "|---|---:|---:|---:|---:|"]
        for b, e in est.items():
            if e is None:
                md.append(f"| vs {POLICY_LABELS[b].lower()} | not comparable | | | 0 |")
            else:
                md.append(f"| vs {POLICY_LABELS[b].lower()} | {_money(e.per_night)} | ${e.annual:,.0f} | ${e.low:,.0f}–${e.high:,.0f} | {e.nights} |")
        if rep.profiles["optimized"].size:
            md += ["", _picture(f"power-profile-{key}", f"Average charging power across the night, {tariff.name}")]
        table = sweep.pivot(index="allowance_kw", columns="policy", values="share_ready")
        md += ["", "Share of nights every van is ready, by EV charging allowance:", "",
               "| Allowance | " + " | ".join(POLICY_LABELS[p] for p in POLICIES) + " |", "|---:|" + "---:|" * len(POLICIES)]
        for kw, row in table.iterrows():
            md.append(f"| {kw:g} kW | " + " | ".join(f"{row[p]:.0%}" for p in POLICIES) + " |")
        md += ["", _picture(f"readiness-{key}", f"Share of nights every van is ready by allowance, {tariff.name}")]

    for theme in THEMES:
        save(savings_estimate(estimates, title_detail=f"{label} · mean nightly saving x 365, 90% bootstrap interval",
                              theme=theme), out / f"savings-{theme}.svg", theme)
    md += [
        "", "## Estimated annual savings", "", _picture("savings", "Estimated annual savings with 90% intervals"), "",
        "## How to read this", "",
        "- **Per year** = average saving per comparable night x 365. It assumes future nights look like these nights.",
        "- **90% interval** comes from a bootstrap: resample these nights with replacement 5,000 times and take the middle "
        "90% of the averages. It reflects night-to-night variation in this history, not future changes to tariffs, "
        "routes, or the fleet.",
        "- **Charge on arrival** is an easy baseline to beat. **Shared timer** is the realistic do-it-yourself "
        "alternative, so the savings against it are the honest number.",
        "- Readiness matters as much as dollars: a plan that's cheaper but leaves a van short is not a saving.",
    ]
    (out / "summary.md").write_text("\n".join(md) + "\n")
    return estimates


def _hhmm(text: str) -> time:
    h, m = text.split(":")
    return time(int(h), int(m))


def main() -> None:
    p = argparse.ArgumentParser(description="Estimate ChargePlan savings from a history of charging sessions.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--demo", action="store_true", help="use the bundled synthetic 6-van history")
    src.add_argument("--sessions", help="CSV of sessions (see chargeplan/analysis/sessions.py for columns)")
    p.add_argument("--timezone", default="America/Los_Angeles")
    p.add_argument("--site-limit", type=float, default=36.0, help="EV charging allowance in kW")
    p.add_argument("--efficiency", type=float, default=0.9)
    p.add_argument("--horizon-start", default="16:00")
    p.add_argument("--horizon-hours", type=int, default=18)
    p.add_argument("--tariff", action="append", choices=sorted(TARIFFS), help="repeatable; default: all")
    p.add_argument("--timer", action="append", default=[], metavar="TARIFF=HH:MM", help="override a timer start")
    p.add_argument("--out", default="reports")
    args = p.parse_args()

    if args.demo:
        sessions, source, label = synthetic_sessions(), "Synthetic 6-van history (120 nights). NOT real fleet data.", "Synthetic data"
    else:
        sessions, source, label = load_sessions(args.sessions), Path(args.sessions).name, Path(args.sessions).stem
    cfg = NightConfig(args.timezone, _hhmm(args.horizon_start), args.horizon_hours, args.site_limit, args.efficiency)
    timers = {k: _hhmm(v) for k, v in (t.split("=") for t in args.timer)}
    out = Path(args.out)
    if args.demo:
        out.mkdir(parents=True, exist_ok=True)
        sessions.to_csv(out / "sessions-synthetic.csv", index=False)
    build_report(sessions, cfg, args.tariff or list(TARIFFS), out, source=source, label=label, timers=timers)
    print(f"Report written to {out / 'summary.md'}")


if __name__ == "__main__":
    main()
