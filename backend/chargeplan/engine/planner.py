"""The single entry point: validate -> slots -> baseline -> solve -> check -> summarize.

`run_plan` is pure: same input, same result, no web or database code. The API
(and anything else) should call this rather than re-implementing any step.
"""

from dataclasses import asdict, dataclass

from .baseline import earliest_departure_first
from .checks import check_schedule, find_simple_impossibilities
from .models import PlanInput
from .optimizer import DEFAULT_TIME_LIMIT_S, solve_min_cost
from .slots import availability, build_slots
from .summary import Comparison, ScheduleSummary, compare, explain, summarize_schedule
from .validate import Issue, validate_plan

COMBINED_CONFLICT = (
    "Each vehicle could be ready on its own, but not all of them at once: they compete for the shared "
    "EV charging allowance during overlapping hours. ChargePlan does not pinpoint one exact bottleneck."
)
SUGGESTION = (
    "Try one change and recalculate: a later departure, a smaller energy need, or a higher EV charging "
    "allowance (only if one is already approved for your site). No edit is guaranteed to work until it has been re-solved."
)


@dataclass
class SlotInfo:
    index: int
    start: str  # ISO 8601 with UTC offset
    end: str
    price_per_kwh: float


@dataclass
class PlanResult:
    # "invalid" | "optimal" | "infeasible" | "solver_limit" | "solver_error"
    status: str
    explanation: list[str]
    issues: list[Issue]
    slots: list[SlotInfo]
    optimized: ScheduleSummary | None
    baseline: ScheduleSummary | None
    comparison: Comparison | None
    infeasibility_reasons: list[str]
    suggestions: list[str]
    solver_message: str

    def to_dict(self) -> dict:
        return asdict(self)


def run_plan(plan: PlanInput, time_limit_s: float = DEFAULT_TIME_LIMIT_S) -> PlanResult:
    issues = validate_plan(plan)
    if issues:
        return PlanResult("invalid", explain("invalid", plan, [], None, None, None), issues, [], None, None, None, [], [], "")

    slots = build_slots(plan)
    avail = availability(plan, slots)

    base_x = earliest_departure_first(plan, avail)
    baseline = summarize_schedule("baseline", plan, slots, base_x, check_schedule(plan, slots, avail, base_x))

    outcome = solve_min_cost(plan, slots, avail, time_limit_s)
    status, message, optimized = outcome.status, outcome.message, None
    if outcome.status == "optimal":
        check = check_schedule(plan, slots, avail, outcome.x)
        if check.all_ready:
            optimized = summarize_schedule("optimized", plan, slots, outcome.x, check)
        else:  # never trust a schedule that fails our own check
            status = "solver_error"
            message = "Solver schedule failed independent verification: " + "; ".join(check.violations or ["not all vehicles ready"])

    reasons, suggestions = [], []
    if status == "infeasible":
        reasons = find_simple_impossibilities(plan, avail) or [COMBINED_CONFLICT]
        suggestions = [SUGGESTION]

    comparison = compare(optimized, baseline)
    slot_info = [SlotInfo(s.index, s.start.isoformat(), s.end.isoformat(), s.price_per_kwh) for s in slots]
    return PlanResult(
        status=status,
        explanation=explain(status, plan, slots, optimized, baseline, comparison),
        issues=[],
        slots=slot_info,
        optimized=optimized,
        baseline=baseline,
        comparison=comparison,
        infeasibility_reasons=reasons,
        suggestions=suggestions,
        solver_message=message,
    )
