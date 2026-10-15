"""Measure end-to-end planning time at the largest supported size (10 vehicles, 48 slots).

    python -m chargeplan.benchmark            # 50 runs
    python -m chargeplan.benchmark --runs 200

Times `run_plan` (validation, baseline, LP solve, checks, summary). It does not
include HTTP or database time, which do not exist yet.
"""

import argparse
import platform
import statistics
import time

import numpy
import scipy

from .engine import run_plan
from .scenarios import full_depot

TARGET_S = 2.0  # provisional target from the project plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=50)
    args = parser.parse_args()

    plan = full_depot()
    run_plan(plan)  # warm-up: first call pays one-time import/initialisation costs
    times = []
    for _ in range(args.runs):
        start = time.perf_counter()
        result = run_plan(plan)
        times.append(time.perf_counter() - start)
        assert result.status == "optimal"

    times.sort()
    p95 = times[min(len(times) - 1, int(0.95 * len(times)))]
    print(f"Problem: {len(plan.vehicles)} vehicles x {len(result.slots)} slots, {args.runs} runs after 1 warm-up")
    print(f"Machine: {platform.machine()} | {platform.platform()} | {platform.processor() or 'unknown CPU'}")
    print(f"Python {platform.python_version()} | NumPy {numpy.__version__} | SciPy {scipy.__version__}")
    print(f"run_plan latency: median {statistics.median(times) * 1000:.1f} ms | p95 {p95 * 1000:.1f} ms | max {times[-1] * 1000:.1f} ms")
    print(f"Target < {TARGET_S:g} s: {'met' if times[-1] < TARGET_S else 'NOT met'} on this machine")


if __name__ == "__main__":
    main()
