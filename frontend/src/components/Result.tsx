import { clock, cls, kwh, money, verdict } from '../format.ts'
import type { PlanRequest, PlanResult } from '../types.ts'
import { NightBoard } from './NightBoard.tsx'

type Props = {
  result: PlanResult | null
  request: PlanRequest | null // the request that produced `result`
  stale: boolean // the form changed since
  example: boolean
  busy: boolean
  error: string
}

export function Result({ result, request, stale, example, busy, error }: Props) {
  if (error) {
    return (
      <section className="result" aria-live="polite">
        <h2 className="verdict">Can't reach the planner.</h2>
        <p className="verdict-line">{error}</p>
      </section>
    )
  }
  if (!result) {
    return (
      <section className="result" aria-busy="true">
        <p className="state">Planning…</p>
      </section>
    )
  }

  const v = verdict(result)
  const opt = result.optimized
  const state = busy ? 'Planning…' : stale ? 'Out of date. Press Plan tonight.' : example ? 'Example plan' : ''
  return (
    <section className={cls('result', (stale || busy) && 'stale')} aria-live="polite">
      <p className="state">{state}</p>
      <h2 className="verdict">{v.headline}</h2>
      {v.lines.map((line) => (
        <p className="verdict-line" key={line}>
          {line}
        </p>
      ))}

      {opt && request && <NightBoard result={result} request={request} />}

      {opt && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Van</th>
                <th>Leaves</th>
                <th className="wide">Needs</th>
                <th>Gets</th>
                <th className="wide">Cost</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {opt.vehicles.map((van) => (
                <tr key={van.id}>
                  <td>{van.name}</td>
                  <td>{clock(van.departure)}</td>
                  <td className="wide">{kwh(van.requested_kwh)}</td>
                  <td>{kwh(van.delivered_kwh)}</td>
                  <td className="wide">{money(van.cost)}</td>
                  <td>{van.ready ? '✓ Ready' : <span className="short">Short {kwh(van.shortfall_kwh)}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {result.status !== 'invalid' && (
        <details>
          <summary>Why this plan</summary>
          <ul>
            {result.explanation.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </details>
      )}
      <p className="footnote">Energy cost at the rates entered. Doesn't control chargers.</p>
    </section>
  )
}
