import type { PlanRequest, PlanResult } from './types.ts'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (!response.ok) throw new Error(`${path} returned ${response.status}`)
  return response.json() as Promise<T>
}

export const getExample = (key: string) => call<PlanRequest>(`/api/examples/${key}`)

export const solvePlan = (request: PlanRequest) =>
  call<PlanResult>('/api/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
