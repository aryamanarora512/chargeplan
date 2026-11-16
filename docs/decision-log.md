# Decision log

Short entries: what we decided, why, and what would change our mind. Newest first.

### 2026-11-15: Milestone 2 (working web slice)

**One POST endpoint does everything.** `POST /api/plan` validates and solves in one call. A separate validate
endpoint would only repeat it, because the engine already returns `status: "invalid"` with per-field messages.
Pydantic rejects malformed JSON with a 422, but plan problems are never HTTP errors.

**The browser never does time-zone math.** Every time stays a local-site string like `2026-10-15T18:00` and is
compared as text. A `Date` object would silently shift times into the viewer's own zone. Rates and vans take clock
times only, and `atClock()` places each one on the right date within the night (tested across midnight, a 24-hour
night, and New Year).

**Only one round of number checks in the browser.** The browser checks that numbers are numbers, so nothing
unparseable is sent. Everything else, like "a van must leave after it arrives", stays in the engine. That's one
source of truth for the rules, the same split Pydantic and `validate_plan` use on the server.

**The engine's user-facing messages now use the app's words:** "van", "power limit", and "night".

**No UI or chart library.** The night board is a CSS grid of plain elements. There are two runtime packages beyond
React: the Barlow fonts, self-hosted so no font service is called. Tests use Node's built-in runner instead of Vitest,
which also avoided an npm 10.9.2 installer bug with Vitest 5's optional peer packages.

**A "Plan tonight" button, not live recalculation.** Edits mark the result "out of date" until the user presses
the button. This keeps the person in control, makes it obvious which inputs produced which result, and avoids
solving half-typed numbers.

### 2026-11-15: UI design direction (proposed)

**Design follows [avoid-ai-design](https://github.com/funboy322/avoid-ai-design), as requested.** The look comes from
the depot's own world, not a dashboard template. The night runs left to right like a dispatch board, pricier hours are
shaded like a tariff table, and charging is lit in sodium-lamp amber. The contract lives in `DESIGN.md`.

**What the first wireframe got wrong:** a stock GitHub-blue button, a row of three KPI cards (L4), a bordered panel
around every section (K2), and a system font with no chosen face (T1). The new one has none of these.

**Minimal copy, and no tutorial.** The app opens with a two-line intro and an example plan already solved, so a new user
sees what a result looks like before typing. The engine's long explanation sits behind "Why this plan".

**The default example becomes `early_departure`.** One van leaves before the cheap hours, which shows the shared power
limit and departures at a glance. The hand-checkable example's equally cheap schedules look scattered on the board.

### 2026-11-13: Savings estimator

**"Predict savings" = replay history + bootstrap, not machine learning.** Given one night's inputs, the engine computes
cost exactly in milliseconds, so a model trained to imitate it would add error and nothing else. The real uncertainty is
*which nights come next*, so we replay every historical night and bootstrap the average. ML becomes worth it later, for
forecasting tomorrow's energy needs from real history, and only if it beats a simple average on held-out dates.

**Savings are reported against a shared timer too, and only on comparable nights.** This was the gap flagged on
2026-10-26. A night where a baseline leaves a van short is excluded from dollar savings and counted as a readiness failure.

**Historical timestamps are rounded conservatively** (arrival up, departure down) by the data adapter, never silently by
the engine, so replay never assumes more charging time than really existed.

**Charts are static SVG from matplotlib**, in a light and a dark version, with one color per policy everywhere.
Every chart has a table twin in `summary.md`. The web UI will draw interactive versions from the same numbers later.

**New dependencies:** pandas and matplotlib, for analysis only. The engine still needs just NumPy and SciPy.

### 2026-10-26: Problem and market analysis (no code changes)

**Benchmark against a shared timer, not only charge-on-arrival.** A 9 pm timer captures most of the cheap-hours saving,
so charge-on-arrival overstates ChargePlan's value. Planned: add a timer baseline before claiming savings in the UI.

**Candidate feature: "smallest allowance that keeps everyone ready."** On PG&E's BEV rate, power is billed as a kW
subscription and the overnight energy price is flat. Right-sizing was the planner's distinct value in our model run
(about $447/yr for 6 vans). Build it only if interviews confirm fleets pay for, and can change, their power level.

**Market stance:** on current evidence this is a niche (US SAM roughly $0.03M–$4.4M/yr). Treat it as a portfolio
project and possible feature or advisor tool, not a venture pitch, unless interviews or better data change the inputs
in [market-sizing.md](market-sizing.md).

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
