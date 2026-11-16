// The form's state and its conversion to and from an API request.
//
// The form holds strings (what the user typed). Rates and vans use clock times
// like "06:00"; the night's start and end carry full dates. atClock() places each
// clock time on the right date inside the night.
//
// Every date-time here is a LOCAL SITE TIME string, "YYYY-MM-DDTHH:MM". They are
// compared as strings and never turned into Date objects in the browser's own
// time zone, which may differ from the depot's.

import type { PlanRequest } from './types.ts'

export type RateRow = { from: string; to: string; price: string }
export type VanRow = { id: string; name: string; arrives: string; leaves: string; kwh: string; kw: string }
export type PlanForm = {
  timezone: string
  start: string // "2026-10-15T18:00"
  end: string
  limitKw: string
  efficiencyPct: string
  rates: RateRow[]
  vans: VanRow[]
}

// Error messages keyed by the same field paths the engine uses, e.g. "vehicles[1].departure".
export type FieldErrors = Record<string, string>

export const MAX_VANS = 10

const minute = (iso: string) => iso.slice(0, 16) // "2026-10-15T18:00:00" -> "2026-10-15T18:00"
export const clockOf = (iso: string) => iso.slice(11, 16) // -> "18:00"

function addDays(day: string, n: number): string {
  const [y, m, d] = day.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10) // UTC math: no time-zone surprises
}

/** The date-time inside the night that has this clock time. A 'start' time (arrival,
 *  rate start) may equal the night's start; an 'end' time may equal the night's end.
 *  A clock time outside the night is returned as-is so the server can say so. */
export function atClock(clock: string, nightStart: string, nightEnd: string, kind: 'start' | 'end'): string {
  const firstDay = nightStart.slice(0, 10)
  for (const day of [firstDay, addDays(firstDay, 1)]) {
    const t = `${day}T${clock}`
    const inside = kind === 'start' ? t >= nightStart && t < nightEnd : t > nightStart && t <= nightEnd
    if (inside) return t
  }
  return `${firstDay}T${clock}`
}

/** 0.3 -> "0.30", but 0.1234 stays "0.1234" so nothing is lost. */
const cents = (price: number) => (Math.abs(price * 100 - Math.round(price * 100)) < 1e-9 ? price.toFixed(2) : String(price))

export function fromRequest(req: PlanRequest): PlanForm {
  return {
    timezone: req.timezone,
    start: minute(req.horizon_start),
    end: minute(req.horizon_end),
    limitKw: String(req.site_limit_kw),
    efficiencyPct: String(Math.round(req.efficiency * 1000) / 10),
    rates: req.rates.map((r) => ({ from: clockOf(r.start), to: clockOf(r.end), price: cents(r.price_per_kwh) })),
    vans: req.vehicles.map((v) => ({
      id: v.id,
      name: v.name,
      arrives: clockOf(v.arrival),
      leaves: clockOf(v.departure),
      kwh: String(v.energy_needed_kwh),
      kw: String(v.max_power_kw),
    })),
  }
}

/** Checks only that numbers are numbers and times are filled in. Whether the plan
 *  makes sense (rates cover the night, vans fit, ...) is the engine's job. */
export function toRequest(form: PlanForm): { request: PlanRequest | null; errors: FieldErrors } {
  const errors: FieldErrors = {}
  const num = (text: string, path: string) => {
    const n = text.trim() === '' ? NaN : Number(text)
    if (!Number.isFinite(n)) errors[path] = 'Enter a number.'
    return n
  }
  const time = (text: string, path: string) => {
    if (!/^\d{2}:\d{2}$/.test(text)) errors[path] = 'Enter a time.'
    return text
  }
  if (!form.start) errors.horizon_start = 'Enter a date and time.'
  if (!form.end) errors.horizon_end = 'Enter a date and time.'

  const request: PlanRequest = {
    timezone: form.timezone,
    horizon_start: form.start,
    horizon_end: form.end,
    site_limit_kw: num(form.limitKw, 'site_limit_kw'),
    efficiency: num(form.efficiencyPct, 'efficiency') / 100,
    rates: form.rates.map((r, i) => ({
      start: atClock(time(r.from, `rates[${i}].start`), form.start, form.end, 'start'),
      end: atClock(time(r.to, `rates[${i}].end`), form.start, form.end, 'end'),
      price_per_kwh: num(r.price, `rates[${i}].price_per_kwh`),
    })),
    vehicles: form.vans.map((v, i) => ({
      id: v.id,
      name: v.name,
      arrival: atClock(time(v.arrives, `vehicles[${i}].arrival`), form.start, form.end, 'start'),
      departure: atClock(time(v.leaves, `vehicles[${i}].departure`), form.start, form.end, 'end'),
      energy_needed_kwh: num(v.kwh, `vehicles[${i}].energy_needed_kwh`),
      max_power_kw: num(v.kw, `vehicles[${i}].max_power_kw`),
    })),
  }
  return { request: Object.keys(errors).length ? null : request, errors }
}

export function newVan(form: PlanForm): VanRow {
  const ids = new Set(form.vans.map((v) => v.id))
  const names = new Set(form.vans.map((v) => v.name))
  let k = form.vans.length + 1
  while (ids.has(`v${k}`)) k++
  const letter = [...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'].find((c) => !names.has(`Van ${c}`)) ?? String(k)
  return { id: `v${k}`, name: `Van ${letter}`, arrives: clockOf(form.start), leaves: clockOf(form.end), kwh: '20', kw: '10' }
}

export function newRate(form: PlanForm): RateRow {
  const last = form.rates.at(-1)
  return { from: last?.to ?? clockOf(form.start), to: clockOf(form.end), price: last?.price ?? '0.20' }
}
