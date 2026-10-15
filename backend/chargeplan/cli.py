"""Command-line runner: plan a bundled scenario without any frontend or database.

    python -m chargeplan.cli                    # list scenarios
    python -m chargeplan.cli hand_checkable     # print a readable report
    python -m chargeplan.cli hand_checkable --json
    python -m chargeplan.cli --all
"""

import argparse
import json
from datetime import datetime

from .engine import PlanInput, PlanResult, run_plan
from .engine.slots import DT_HOURS
from .engine.summary import BASELINE_NAME, ScheduleSummary
from .scenarios import SCENARIOS


def _hm(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%H:%M")


def _local(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M")


def _vehicle_table(summary: ScheduleSummary) -> list[str]:
    rows = [f"  {'ID':<5}{'Vehicle':<24}{'Departs':<18}{'Needs kWh':>10}{'Gets kWh':>10}  Ready"]
    for vs in summary.vehicles:
        ready = "yes" if vs.ready else f"NO ({vs.shortfall_kwh:.2f} kWh short)"
        rows.append(
            f"  {vs.id:<5}{vs.name[:23]:<24}{_local(vs.departure):<18}{vs.requested_kwh:>10.2f}{vs.delivered_kwh:>10.2f}  {ready}"
        )
    return rows


def _schedule_table(plan: PlanInput, result: PlanResult, summary: ScheduleSummary) -> list[str]:
    ids = [v.id for v in plan.vehicles]
    head = f"  {'Time':<7}{'$/kWh':>6}" + "".join(f"{i:>7}" for i in ids) + f"{'Total':>8}{'Limit':>7}"
    rows = [head]
    for slot in result.slots:
        per_vehicle = [summary.grid_kwh[v][slot.index] / DT_HOURS for v in range(len(ids))]  # kWh -> kW
        total = summary.site_kw[slot.index]
        bar = "#" * round(20 * total / plan.site_limit_kw)
        rows.append(
            f"  {_hm(slot.start):<7}{slot.price_per_kwh:>6.2f}"
            + "".join(f"{kw:>7.1f}" for kw in per_vehicle)
            + f"{total:>8.1f}{plan.site_limit_kw:>7g}  {bar}"
        )
    return rows


def report(key: str) -> str:
    scenario = SCENARIOS[key]
    plan = scenario.build()
    result = run_plan(plan)
    out = [
        f"ChargePlan | {scenario.title}  (synthetic data)",
        f"Site time zone {plan.timezone} | {plan.horizon_start:%Y-%m-%d %H:%M} -> {plan.horizon_end:%Y-%m-%d %H:%M}"
        f" | EV charging allowance {plan.site_limit_kw:g} kW | efficiency {plan.efficiency * 100:g}%",
        "",
        f"STATUS: {result.status.upper()}",
    ]
    if result.status == "invalid":
        out += [f"  - {issue.field}: {issue.message}" for issue in result.issues]
        return "\n".join(out)

    opt, base, cmp = result.optimized, result.baseline, result.comparison
    n = len(plan.vehicles)
    out += [
        "",
        f"  {'':<22}{'Optimized':>12}{'Baseline*':>12}",
        f"  {'Vehicles ready':<22}{(f'{opt.ready_count}/{n}' if opt else '-'):>12}{f'{base.ready_count}/{n}':>12}",
        f"  {'Grid energy (kWh)':<22}{(f'{opt.total_grid_kwh:.2f}' if opt else '-'):>12}{base.total_grid_kwh:>12.2f}",
        f"  {'Energy cost':<22}{(f'${opt.total_cost:.2f}' if opt else '-'):>12}{f'${base.total_cost:.2f}':>12}",
    ]
    if cmp.comparable:
        pct = f" ({cmp.savings_pct:.1%})" if cmp.savings_pct is not None else ""
        out.append(f"  {'Savings vs baseline':<22}{f'${cmp.savings:.2f}{pct}':>12}")
    else:
        out.append(f"  {'Savings vs baseline':<22}{'not comparable':>16}")
    out.append(f"  * Baseline = {BASELINE_NAME}.")

    out += ["", "Optimized plan by vehicle:" if opt else "Baseline by vehicle:"]
    out += _vehicle_table(opt or base)
    if opt:
        out += ["", "Optimized schedule (kW per 30-minute slot; # = share of site limit):"]
        out += _schedule_table(plan, result, opt)

    out += ["", "What this means:"] + [f"  - {line}" for line in result.explanation]
    if result.infeasibility_reasons:
        out += ["", "Why it is impossible:"] + [f"  - {r}" for r in result.infeasibility_reasons]
        out += ["", "What to try:"] + [f"  - {s}" for s in result.suggestions]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan a bundled synthetic ChargePlan scenario.")
    parser.add_argument("scenario", nargs="?", choices=sorted(SCENARIOS))
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    parser.add_argument("--all", action="store_true", help="run every bundled scenario")
    args = parser.parse_args()

    if args.all:
        print(("\n\n" + "=" * 80 + "\n\n").join(report(key) for key in SCENARIOS))
    elif args.scenario and args.json:
        print(json.dumps(run_plan(SCENARIOS[args.scenario].build()).to_dict(), indent=2))
    elif args.scenario:
        print(report(args.scenario))
    else:
        print("Bundled synthetic scenarios:")
        for key, scenario in SCENARIOS.items():
            print(f"  {key:<28}{scenario.title}")
        print("\nRun one with: python -m chargeplan.cli <scenario>")


if __name__ == "__main__":
    main()
