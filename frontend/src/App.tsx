import { useCallback, useEffect, useState } from 'react'
import { getExample, solvePlan } from './api.ts'
import { PlanFormView } from './components/PlanForm.tsx'
import { Result } from './components/Result.tsx'
import { fromRequest, toRequest, type FieldErrors, type PlanForm } from './plan.ts'
import type { PlanRequest, PlanResult } from './types.ts'

const EXAMPLE = 'early_departure'
const OFFLINE = 'Try again in a moment.'

export default function App() {
  const [form, setForm] = useState<PlanForm | null>(null)
  const [result, setResult] = useState<PlanResult | null>(null)
  const [solved, setSolved] = useState<PlanRequest | null>(null) // the request behind `result`
  const [inputErrors, setInputErrors] = useState<FieldErrors>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [isExample, setIsExample] = useState(true)

  const plan = useCallback(async (f: PlanForm) => {
    const { request, errors } = toRequest(f)
    setInputErrors(errors)
    if (!request) return
    setBusy(true)
    setError('')
    try {
      setResult(await solvePlan(request))
      setSolved(request)
    } catch {
      setError(OFFLINE)
    } finally {
      setBusy(false)
    }
  }, [])

  const showExample = useCallback(
    (example: PlanRequest) => {
      const f = fromRequest(example)
      setForm(f)
      setIsExample(true)
      return plan(f)
    },
    [plan],
  )

  const resetExample = () => getExample(EXAMPLE).then(showExample, () => setError(OFFLINE))

  // On first load, fetch and solve the example so a new user sees a result straight away.
  // `ignore` drops the answer if React unmounts before it arrives (it mounts twice in development).
  useEffect(() => {
    let ignore = false
    getExample(EXAMPLE).then(
      (example) => {
        if (!ignore) showExample(example)
      },
      () => {
        if (!ignore) setError(OFFLINE)
      },
    )
    return () => {
      ignore = true
    }
  }, [showExample])

  // The result is out of date once the form no longer matches what was solved.
  const current = form ? toRequest(form).request : null
  const stale = result !== null && JSON.stringify(current) !== JSON.stringify(solved)

  // The engine's messages for invalid inputs, first one per field, until the next edit.
  const engineErrors: FieldErrors = {}
  if (result?.status === 'invalid' && !stale) {
    for (const issue of result.issues) engineErrors[issue.field] ??= issue.message
  }

  return (
    <main className="app">
      <header className="intro">
        <h1>ChargePlan</h1>
        <p>
          Plan tonight's charging for a small EV fleet. Enter your vans, power limit and electricity rates. ChargePlan
          finds the cheapest schedule that gets every van out on time.
        </p>
      </header>

      <Result result={result} request={solved} stale={stale} example={isExample} busy={busy} error={error} />

      {form && (
        <PlanFormView
          form={form}
          errors={{ ...engineErrors, ...inputErrors }}
          busy={busy}
          onChange={(f) => {
            setForm(f)
            setIsExample(false)
          }}
          onSubmit={() => plan(form)}
          onReset={resetExample}
        />
      )}
    </main>
  )
}
