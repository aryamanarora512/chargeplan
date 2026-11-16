// The night board: one row per van, one column per half-hour. Pricier hours are
// shaded, charging is drawn as amber blocks (taller = more kW), and each row
// ends at that van's departure. The table under it holds the same numbers.

import { Fragment } from 'react'
import { chargingRanges, clock, cls, money, priceBands } from '../format.ts'
import type { PlanRequest, PlanResult } from '../types.ts'

const SLOT_HOURS = 0.5
const local = (iso: string) => iso.slice(0, 16) // compare site-local times as strings

type Props = { result: PlanResult; request: PlanRequest }

export function NightBoard({ result, request }: Props) {
  const opt = result.optimized
  if (!opt) return null
  const slots = result.slots
  const n = slots.length
  const cheapest = Math.min(...slots.map((s) => s.price_per_kwh))
  const tickEvery = n > 32 ? 8 : 4 // a time label every 2 hours, or 4 on a long night
  const described = opt.vehicles
    .map((v, i) => `${v.name} charges ${chargingRanges(opt.grid_kwh[i], slots).join(', ') || 'never'}`)
    .join('. ')

  return (
    <figure className="board" role="img" aria-label={`Charging schedule. ${described}.`}>
      <div className="board-grid" style={{ gridTemplateColumns: `var(--board-label) repeat(${n}, minmax(0, 1fr))` }} aria-hidden="true">
        <span />
        {priceBands(slots).map((b, i) => (
          <span key={b.first} className="board-price" style={{ gridColumn: `${b.first + 2} / span ${b.count}` }}>
            {i === 0 ? `${money(b.price)}/kWh` : money(b.price)}
          </span>
        ))}

        <span />
        {slots.map((s, i) => (
          <span key={s.index} className="board-time">
            {i % tickEvery === 0 ? clock(s.start) : ''}
          </span>
        ))}

        {opt.vehicles.map((v, row) => {
          const leaves = slots.findIndex((s) => local(s.start) >= local(v.departure))
          const chargerKw = request.vehicles[row]?.max_power_kw ?? 1
          return (
            <Fragment key={v.id}>
              <span className="board-label">{v.name}</span>
              {slots.map((s, i) => {
                const kw = opt.grid_kwh[row][i] / SLOT_HOURS
                const away = local(s.start) < local(v.arrival) || local(s.start) >= local(v.departure)
                return (
                  <span
                    key={s.index}
                    className={cls('board-cell', s.price_per_kwh > cheapest + 1e-9 && 'pricey', away && 'away', i === leaves && 'left')}
                  >
                    {kw > 1e-6 && (
                      <span
                        className="block"
                        style={{ height: `${Math.max(12, (100 * kw) / chargerKw)}%` }}
                        title={`${v.name}, ${clock(s.start)}–${clock(s.end)}, ${kw.toFixed(1)} kW`}
                      />
                    )}
                    {i === leaves && n - i >= 3 && <span className="left-label">left {clock(v.departure)}</span>}
                  </span>
                )
              })}
            </Fragment>
          )
        })}

        <span className="board-label site">
          Site
          <small>limit {request.site_limit_kw} kW</small>
        </span>
        {/* The site row is its own grid with the same columns, so the limit can be one
            continuous dashed line across it. */}
        <span className="site-row" style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}>
          {slots.map((s, i) => {
            const kw = opt.site_kw[i]
            return (
              <span key={s.index} className={cls('board-cell site', s.price_per_kwh > cheapest + 1e-9 && 'pricey')}>
                {kw > 1e-6 && (
                  <span
                    className="block"
                    style={{ height: `${Math.max(8, (100 * kw) / request.site_limit_kw)}%` }}
                    title={`All vans, ${clock(s.start)}–${clock(s.end)}, ${kw.toFixed(1)} of ${request.site_limit_kw} kW`}
                  />
                )}
              </span>
            )
          })}
        </span>
      </div>
    </figure>
  )
}
