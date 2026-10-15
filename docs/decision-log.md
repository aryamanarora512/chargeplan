# Decision log

Short entries: what we decided, why, and what would change our mind. Newest first.

### 2026-10-15: Milestone 1 (Python engine)

**LP with SciPy/HiGHS, not a hand-written solver or integer program.**
Every constraint is linear in the energy amounts, and nothing is a yes/no decision under the MVP assumptions. That makes it
a linear program, which HiGHS solves exactly and can prove infeasible. *Revisit if* we add on/off charger states or
minimum-current rules (those need integer variables).

**One variable per (vehicle, slot), with upper bound 0 outside the vehicle's window.**
At most 10 × 48 = 480 variables. Keeping "unavailable" as a bound (instead of dropping variables) makes the code line up
one-to-one with the math. *Revisit if* problem size grows by orders of magnitude.

**Engine inputs are plain frozen dataclasses; Pydantic will live only at the API edge.**
Pydantic will answer "is this JSON well-formed?" while `validate_plan` answers "does this make sense as a charging
plan?". The engine stays importable and testable with only NumPy and SciPy.

**Times are local wall-clock values plus an IANA time zone; nights with a daylight-saving change are rejected.**
Within a horizon that has no clock change, local clock arithmetic equals real elapsed time, so slots are simple.
Outputs carry UTC offsets (e.g. `2026-10-15T18:00:00-04:00`). Rejecting DST nights is explicit and tested.
*Revisit:* support DST by building slots in UTC.

**Times must sit on :00 or :30.** We never silently round a departure deadline.

**The baseline is price-blind earliest-departure-first.** It's simple and resembles "plug in and charge." It can fail when
a feasible plan exists (see `baseline_misses_departure`), so baseline failure never labels a scenario infeasible.

**Savings are shown only when both plans ready every vehicle with the same energy.** Otherwise a plan that delivers *less*
energy could look "cheaper." Percent savings are omitted when the baseline costs $0.

**Solver statuses map to five outcomes:** `invalid`, `optimal`, `infeasible`, `solver_limit`, `solver_error`.
Only HiGHS status 2 becomes `infeasible`. Every "optimal" schedule is re-verified by `check_schedule`; if verification
fails, the result is downgraded to `solver_error`.

**Numerical tolerance: 1e-6 kWh** for all constraint checks (HiGHS's default feasibility tolerance is 1e-7). Values below
1e-9 kWh are treated as zero so displays never show "-0.00".

**Known UX gap: equally cheap schedules can look "spiky."** HiGHS returns one of many optimal schedules, and it may jump
between vehicles. A later fix could re-solve with the optimal cost fixed and a secondary goal (e.g. finish earlier or
smoother power). Only do this if users find the spiky schedules confusing.

**CSV export, API, UI, and database are deliberately not built yet.** Each comes with its own milestone.

### 2026-10-15: Deployment direction (no hosting chosen yet)

The Python engine stays on a server behind a small stateless HTTP API. That one API can serve (a) a website (static React
build plus a hosted FastAPI service) and later (b) an iOS app, for example a native app or the same React UI wrapped with
a tool such as Capacitor. Apple can reject apps that are just a thin website wrapper, so an App Store version would need
genuinely app-like value. The public demo will use bundled synthetic examples with no saved-plan storage. No paid
service will be added without asking.
