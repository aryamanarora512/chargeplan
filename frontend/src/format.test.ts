import assert from 'node:assert/strict'
import { test } from 'node:test'
import { chargingRanges, priceBands, verdict } from './format.ts'
import type { PlanResult, ScheduleSummary, SlotInfo } from './types.ts'

const slots: SlotInfo[] = ['18:00', '18:30', '19:00', '19:30'].map((t, i) => ({
  index: i,
  start: `2026-10-15T${t}:00-04:00`,
  end: `2026-10-15T${['18:30', '19:00', '19:30', '20:00'][i]}:00-04:00`,
  price_per_kwh: i < 2 ? 0.3 : 0.12,
}))

function summary(costs: number[], ready: boolean[]): ScheduleSummary {
  return {
    policy: 'optimized',
    grid_kwh: [],
    site_kw: [],
    vehicles: costs.map((cost, i) => ({
      id: `v${i}`, name: `Van ${i}`, arrival: '', departure: '', requested_kwh: 18, delivered_kwh: 18,
      grid_kwh: 20, cost, ready: ready[i], shortfall_kwh: ready[i] ? 0 : 5,
    })),
    ready_count: ready.filter(Boolean).length,
    all_ready: ready.every(Boolean),
    total_grid_kwh: 40,
    total_cost: costs.reduce((a, b) => a + b, 0),
    violations: [],
  }
}

function result(over: Partial<PlanResult>): PlanResult {
  return {
    status: 'optimal', explanation: [], issues: [], slots, optimized: null, baseline: null, comparison: null,
    infeasibility_reasons: [], suggestions: [], solver_message: '', ...over,
  }
}

test('verdict names the cost and the saving', () => {
  const v = verdict(result({
    optimized: summary([6, 2.4], [true, true]),
    baseline: summary([6, 6], [true, true]),
    comparison: { comparable: true, optimized_cost: 8.4, baseline_cost: 12, savings: 3.6, savings_pct: 0.3, note: '' },
  }))
  assert.equal(v.headline, 'Both vans ready for $8.40.')
  assert.deepEqual(v.lines, ['$3.60 less than charging as soon as they arrive.'])
})

test('no saving is claimed when charging on arrival leaves a van short', () => {
  const v = verdict(result({
    optimized: summary([10, 10, 3.04], [true, true, true]),
    baseline: summary([10, 10, 2.44], [true, true, false]),
    comparison: { comparable: false, optimized_cost: 23.04, baseline_cost: 22.44, savings: null, savings_pct: null, note: '' },
  }))
  assert.equal(v.headline, 'All 3 vans ready for $23.04.')
  assert.deepEqual(v.lines, ['Charging as soon as they arrive would leave 1 van short.'])
})

test('rounding never shows a $0.00 saving as a saving', () => {
  const v = verdict(result({
    optimized: summary([4], [true]),
    baseline: summary([4], [true]),
    comparison: { comparable: true, optimized_cost: 4, baseline_cost: 4, savings: 0.001, savings_pct: 0, note: '' },
  }))
  assert.equal(v.headline, 'The van is ready for $4.00.')
  assert.deepEqual(v.lines, ['Same cost as charging as soon as they arrive.'])
})

test('impossible and failed plans say so plainly', () => {
  const impossible = verdict(result({ status: 'infeasible', infeasibility_reasons: ['Van B needs 60.00 kWh...'] }))
  assert.equal(impossible.headline, 'Not every van can be ready.')
  assert.equal(impossible.lines[0], 'Van B needs 60.00 kWh...')
  assert.equal(verdict(result({ status: 'solver_limit' })).headline, "Couldn't finish the calculation.")
  assert.equal(verdict(result({ status: 'invalid' })).headline, 'Check the highlighted fields.')
})

test('price bands group equal prices', () => {
  assert.deepEqual(priceBands(slots), [
    { first: 0, count: 2, price: 0.3 },
    { first: 2, count: 2, price: 0.12 },
  ])
})

test('charging ranges merge neighbouring slots', () => {
  assert.deepEqual(chargingRanges([5, 5, 0, 5], slots), ['18:00–19:00', '19:30–20:00'])
  assert.deepEqual(chargingRanges([0, 0, 0, 0], slots), [])
})
