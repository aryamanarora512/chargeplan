import type { ReactNode } from 'react'
import { MAX_VANS, newRate, newVan, type FieldErrors, type PlanForm, type RateRow, type VanRow } from '../plan.ts'

type Props = {
  form: PlanForm
  errors: FieldErrors
  busy: boolean
  onChange: (form: PlanForm) => void
  onSubmit: () => void
  onReset: () => void
}

const ZONES: string[] = (() => {
  try {
    return Intl.supportedValuesOf('timeZone')
  } catch {
    return []
  }
})()

function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="label">{label}</span>
      {children}
      {error && <span className="error">{error}</span>}
    </label>
  )
}

/** Messages for one table row, e.g. every key starting with "vehicles[1]". */
function rowErrors(errors: FieldErrors, prefix: string): string[] {
  return Object.entries(errors)
    .filter(([key]) => key === prefix || key.startsWith(`${prefix}.`))
    .map(([, message]) => message)
}

export function PlanFormView({ form, errors, busy, onChange, onSubmit, onReset }: Props) {
  const set = (patch: Partial<PlanForm>) => onChange({ ...form, ...patch })
  const setRate = (i: number, patch: Partial<RateRow>) => set({ rates: form.rates.map((r, j) => (j === i ? { ...r, ...patch } : r)) })
  const setVan = (i: number, patch: Partial<VanRow>) => set({ vans: form.vans.map((v, j) => (j === i ? { ...v, ...patch } : v)) })
  const bad = (path: string) => (path in errors ? true : undefined)
  const zones = ZONES.includes(form.timezone) ? ZONES : [form.timezone, ...ZONES]

  return (
    <form
      className="inputs"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit()
      }}
    >
      <fieldset>
        <legend>Night</legend>
        <div className="pair">
          <Field label="Starts" error={errors.horizon_start}>
            <input type="datetime-local" step={1800} value={form.start} aria-invalid={bad('horizon_start')} onChange={(e) => set({ start: e.target.value })} />
          </Field>
          <Field label="Ends" error={errors.horizon_end}>
            <input type="datetime-local" step={1800} value={form.end} aria-invalid={bad('horizon_end')} onChange={(e) => set({ end: e.target.value })} />
          </Field>
        </div>
        <Field label="Time zone" error={errors.timezone}>
          <select value={form.timezone} aria-invalid={bad('timezone')} onChange={(e) => set({ timezone: e.target.value })}>
            {zones.map((z) => (
              <option key={z}>{z}</option>
            ))}
          </select>
        </Field>
      </fieldset>

      <fieldset>
        <legend>Power</legend>
        <div className="pair">
          <Field label="Limit (kW)" error={errors.site_limit_kw}>
            <input inputMode="decimal" value={form.limitKw} aria-invalid={bad('site_limit_kw')} onChange={(e) => set({ limitKw: e.target.value })} />
          </Field>
          <Field label="Efficiency (%)" error={errors.efficiency}>
            <input inputMode="decimal" value={form.efficiencyPct} aria-invalid={bad('efficiency')} onChange={(e) => set({ efficiencyPct: e.target.value })} />
          </Field>
        </div>
      </fieldset>

      <fieldset>
        <legend>Rates</legend>
        <div className="rows rates">
          <span className="label">From</span>
          <span className="label">To</span>
          <span className="label">$/kWh</span>
          <span />
          {form.rates.map((r, i) => (
            <div className="row" key={i}>
              <input type="time" step={1800} aria-label={`Rate ${i + 1} from`} value={r.from} aria-invalid={bad(`rates[${i}].start`)} onChange={(e) => setRate(i, { from: e.target.value })} />
              <input type="time" step={1800} aria-label={`Rate ${i + 1} to`} value={r.to} aria-invalid={bad(`rates[${i}].end`)} onChange={(e) => setRate(i, { to: e.target.value })} />
              <input inputMode="decimal" aria-label={`Rate ${i + 1} price per kWh`} value={r.price} aria-invalid={bad(`rates[${i}].price_per_kwh`)} onChange={(e) => setRate(i, { price: e.target.value })} />
              <button type="button" className="remove" aria-label={`Remove rate ${i + 1}`} disabled={form.rates.length === 1} onClick={() => set({ rates: form.rates.filter((_, j) => j !== i) })}>
                ×
              </button>
              {rowErrors(errors, `rates[${i}]`).map((m) => (
                <span className="error row-error" key={m}>{m}</span>
              ))}
            </div>
          ))}
        </div>
        {errors.rates && <p className="error">{errors.rates}</p>}
        <button type="button" className="text" onClick={() => set({ rates: [...form.rates, newRate(form)] })}>
          Add rate
        </button>
      </fieldset>

      <fieldset>
        <legend>Vans</legend>
        <div className="rows vans">
          <span className="label">Van</span>
          <span className="label">Arrives</span>
          <span className="label">Leaves</span>
          <span className="label" title="Energy to add to the battery">kWh</span>
          <span className="label" title="Charger's maximum power">kW</span>
          <span />
          {form.vans.map((v, i) => (
            <div className="row" key={v.id}>
              <input aria-label={`Van ${i + 1} name`} value={v.name} aria-invalid={bad(`vehicles[${i}].name`)} onChange={(e) => setVan(i, { name: e.target.value })} />
              <input type="time" step={1800} aria-label={`${v.name} arrives`} value={v.arrives} aria-invalid={bad(`vehicles[${i}].arrival`)} onChange={(e) => setVan(i, { arrives: e.target.value })} />
              <input type="time" step={1800} aria-label={`${v.name} leaves`} value={v.leaves} aria-invalid={bad(`vehicles[${i}].departure`)} onChange={(e) => setVan(i, { leaves: e.target.value })} />
              <input inputMode="decimal" aria-label={`${v.name} needs kWh`} value={v.kwh} aria-invalid={bad(`vehicles[${i}].energy_needed_kwh`)} onChange={(e) => setVan(i, { kwh: e.target.value })} />
              <input inputMode="decimal" aria-label={`${v.name} charger kW`} value={v.kw} aria-invalid={bad(`vehicles[${i}].max_power_kw`)} onChange={(e) => setVan(i, { kw: e.target.value })} />
              <button type="button" className="remove" aria-label={`Remove ${v.name}`} disabled={form.vans.length === 1} onClick={() => set({ vans: form.vans.filter((_, j) => j !== i) })}>
                ×
              </button>
              {rowErrors(errors, `vehicles[${i}]`).map((m) => (
                <span className="error row-error" key={m}>{m}</span>
              ))}
            </div>
          ))}
        </div>
        {errors.vehicles && <p className="error">{errors.vehicles}</p>}
        <button type="button" className="text" disabled={form.vans.length >= MAX_VANS} onClick={() => set({ vans: [...form.vans, newVan(form)] })}>
          Add van
        </button>
      </fieldset>

      <div className="actions">
        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Planning…' : 'Plan tonight'}
        </button>
        <button type="button" className="text" onClick={onReset}>
          Reset example
        </button>
      </div>
    </form>
  )
}
