// Display helpers. Numbers arrive at full precision from the API; rounding happens here only.

import type { PlanResult, SlotInfo } from './types.ts'

/** Join the truthy class names: cls('cell', isPricey && 'pricey') */
export const cls = (...names: (string | false | undefined)[]) => names.filter(Boolean).join(' ')

export const money = (dollars: number) => `$${dollars.toFixed(2)}`
export const kwh = (value: number) => `${value.toFixed(1)} kWh`
export const clock = (iso: string) => iso.slice(11, 16) // local site time, whatever the browser's zone
const vans = (n: number) => (n === 1 ? '1 van' : `${n} vans`)

const SAME = 0.005 // under half a cent rounds to $0.00

export type Verdict = { headline: string; lines: string[] }

export function verdict(result: PlanResult): Verdict {
  const opt = result.optimized
  if (result.status === 'optimal' && opt) {
    const n = opt.vehicles.length
    const who = n === 1 ? 'The van is' : n === 2 ? 'Both vans' : `All ${n} vans`
    const headline = `${who} ready for ${money(opt.total_cost)}.`
    const cmp = result.comparison
    const base = result.baseline
    if (cmp?.comparable && cmp.savings !== null) {
      return {
        headline,
        lines: [cmp.savings > SAME ? `${money(cmp.savings)} less than charging as soon as they arrive.` : 'Same cost as charging as soon as they arrive.'],
      }
    }
    if (base && !base.all_ready) {
      const short = base.vehicles.length - base.ready_count
      return { headline, lines: [`Charging as soon as they arrive would leave ${vans(short)} short.`] }
    }
    return { headline, lines: [] }
  }
  if (result.status === 'infeasible') {
    return {
      headline: 'Not every van can be ready.',
      lines: [...result.infeasibility_reasons, 'Try a later departure, less energy, or a higher power limit.'],
    }
  }
  if (result.status === 'invalid') {
    return { headline: 'Check the highlighted fields.', lines: [] }
  }
  return { headline: "Couldn't finish the calculation.", lines: ["That doesn't mean it's impossible. Try again."] }
}

/** Runs of equal price, for the labels above the board. */
export function priceBands(slots: SlotInfo[]): { first: number; count: number; price: number }[] {
  const bands: { first: number; count: number; price: number }[] = []
  for (const s of slots) {
    const last = bands.at(-1)
    if (last && last.price === s.price_per_kwh) last.count++
    else bands.push({ first: s.index, count: 1, price: s.price_per_kwh })
  }
  return bands
}

/** "21:00–23:00" for each continuous stretch of charging, for screen readers and tooltips. */
export function chargingRanges(kwhBySlot: number[], slots: SlotInfo[]): string[] {
  const ranges: string[] = []
  let from = -1
  kwhBySlot.forEach((k, i) => {
    const on = k > 1e-6
    if (on && from < 0) from = i
    const endsHere = from >= 0 && (!on || i === kwhBySlot.length - 1)
    if (endsHere) {
      const last = on ? i : i - 1
      ranges.push(`${clock(slots[from].start)}–${clock(slots[last].end)}`)
      from = -1
    }
  })
  return ranges
}
