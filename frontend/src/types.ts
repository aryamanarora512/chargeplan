// The API's JSON, as TypeScript types. These mirror backend/chargeplan/api/schemas.py
// (requests) and engine/planner.py's PlanResult (responses).

// Times in requests are local site clock times without an offset: "2026-10-15T18:00".
export type RateIn = { start: string; end: string; price_per_kwh: number }

export type VehicleIn = {
  id: string
  name: string
  arrival: string
  departure: string
  energy_needed_kwh: number // into the battery
  max_power_kw: number
}

export type PlanRequest = {
  timezone: string
  horizon_start: string
  horizon_end: string
  site_limit_kw: number
  efficiency: number // 0.9 means 90%
  rates: RateIn[]
  vehicles: VehicleIn[]
}

// Times in results carry the site's UTC offset: "2026-10-15T18:00:00-04:00".
export type Issue = { field: string; message: string }

export type SlotInfo = { index: number; start: string; end: string; price_per_kwh: number }

export type VehicleStatus = {
  id: string
  name: string
  arrival: string
  departure: string
  requested_kwh: number
  delivered_kwh: number
  grid_kwh: number
  cost: number
  ready: boolean
  shortfall_kwh: number
}

export type ScheduleSummary = {
  policy: 'optimized' | 'baseline'
  grid_kwh: number[][] // [van][slot]
  site_kw: number[]
  vehicles: VehicleStatus[]
  ready_count: number
  all_ready: boolean
  total_grid_kwh: number
  total_cost: number
  violations: string[]
}

export type Comparison = {
  comparable: boolean
  optimized_cost: number | null
  baseline_cost: number | null
  savings: number | null
  savings_pct: number | null
  note: string
}

export type PlanStatus = 'invalid' | 'optimal' | 'infeasible' | 'solver_limit' | 'solver_error'

export type PlanResult = {
  status: PlanStatus
  explanation: string[]
  issues: Issue[]
  slots: SlotInfo[]
  optimized: ScheduleSummary | null
  baseline: ScheduleSummary | null
  comparison: Comparison | null
  infeasibility_reasons: string[]
  suggestions: string[]
  solver_message: string
}
