import assert from 'node:assert/strict'
import { test } from 'node:test'
import { atClock, fromRequest, newVan, toRequest } from './plan.ts'
import type { PlanRequest } from './types.ts'

const START = '2026-10-15T18:00'
const END = '2026-10-16T08:00'

const example: PlanRequest = {
  timezone: 'America/New_York',
  horizon_start: '2026-10-15T18:00:00',
  horizon_end: '2026-10-16T08:00:00',
  site_limit_kw: 10,
  efficiency: 0.9,
  rates: [
    { start: '2026-10-15T18:00:00', end: '2026-10-16T00:00:00', price_per_kwh: 0.3 },
    { start: '2026-10-16T00:00:00', end: '2026-10-16T06:00:00', price_per_kwh: 0.12 },
    { start: '2026-10-16T06:00:00', end: '2026-10-16T08:00:00', price_per_kwh: 0.3 },
  ],
  vehicles: [
    { id: 'v1', name: 'Van A', arrival: '2026-10-15T18:00:00', departure: '2026-10-15T23:00:00', energy_needed_kwh: 18, max_power_kw: 10 },
    { id: 'v2', name: 'Van B', arrival: '2026-10-15T18:00:00', departure: '2026-10-16T08:00:00', energy_needed_kwh: 18, max_power_kw: 10 },
  ],
}

test('clock times land on the right date inside an overnight window', () => {
  assert.equal(atClock('20:00', START, END, 'start'), '2026-10-15T20:00')
  assert.equal(atClock('06:00', START, END, 'end'), '2026-10-16T06:00') // after midnight: next day
  assert.equal(atClock('18:00', START, END, 'start'), '2026-10-15T18:00') // a start may equal the night's start
  assert.equal(atClock('08:00', START, END, 'end'), '2026-10-16T08:00') // an end may equal the night's end
})

test('a 24-hour night tells start and end apart', () => {
  const s = '2026-10-15T12:00'
  const e = '2026-10-16T12:00'
  assert.equal(atClock('12:00', s, e, 'start'), '2026-10-15T12:00')
  assert.equal(atClock('12:00', s, e, 'end'), '2026-10-16T12:00')
})

test('a clock time outside the night is passed on unchanged for the server to reject', () => {
  assert.equal(atClock('12:00', START, END, 'start'), '2026-10-15T12:00')
})

test('month and year boundaries use calendar dates, not browser time zones', () => {
  assert.equal(atClock('02:00', '2026-12-31T18:00', '2027-01-01T08:00', 'end'), '2027-01-01T02:00')
})

test('an example survives the trip into the form and back', () => {
  const { request, errors } = toRequest(fromRequest(example))
  assert.deepEqual(errors, {})
  assert.equal(request?.efficiency, 0.9)
  assert.equal(request?.vehicles[0].departure, '2026-10-15T23:00')
  assert.equal(request?.rates[2].end, '2026-10-16T08:00')
  assert.equal(request?.site_limit_kw, 10)
})

test('form shows efficiency as a percent', () => {
  assert.equal(fromRequest(example).efficiencyPct, '90')
})

test('blank or non-numeric fields are caught before anything is sent', () => {
  const form = fromRequest(example)
  form.limitKw = ''
  form.vans[1].kwh = 'lots'
  form.rates[0].from = ''
  const { request, errors } = toRequest(form)
  assert.equal(request, null)
  assert.deepEqual(Object.keys(errors).sort(), ['rates[0].start', 'site_limit_kw', 'vehicles[1].energy_needed_kwh'])
})

test('a new van gets a fresh id and the next free name', () => {
  const van = newVan(fromRequest(example))
  assert.equal(van.id, 'v3')
  assert.equal(van.name, 'Van C')
  assert.equal(van.arrives, '18:00')
  assert.equal(van.leaves, '08:00')
})
