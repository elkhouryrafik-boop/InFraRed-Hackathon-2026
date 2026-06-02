// HTTP client for the CoolSpend backend (coolspend/api_server.py).
// In dev, vite proxies /api -> http://localhost:8000 (see vite.config.ts).
// In a split production deploy (frontend on Vercel, backend on Render) the dev
// proxy does not exist, so VITE_API_BASE (set at build time on Vercel) points at
// the backend origin. Default '' keeps relative paths for local dev + any
// same-origin deploy, so nothing changes unless you opt in.
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? ''
const apiUrl = (path: string): string => API_BASE + path

import type {
  Decision,
  BoundaryGeoJSON,
  TreesGeoJSON,
  RasterBounds,
  WebBundle,
  ImperviousAnalysis,
  CanopyCover,
} from './types'
import type { LngLat } from './draw'

export interface BuildingsPreview {
  polygon_area_m2: number
  context_building_count: number
  buildings_available: boolean
  impervious: ImperviousAnalysis
  backend: string
  note: string
}

export interface EvaluateResponse {
  // On a genuinely unplantable area the API returns { empty: true, headline, ... }
  // (a clean 200, not a 500) — these core fields are then absent.
  empty?: boolean
  headline?: string
  reason?: string
  decision: Decision
  boundary: BoundaryGeoJSON
  trees: TreesGeoJSON
  bounds: RasterBounds
  baselineImageUrl: string | null
  interventionImageUrl: string | null
  impervious?: ImperviousAnalysis | null
  canopy?: CanopyCover | null
  growth?: { ramp_years: number; initial_fraction: number; horizon_years: number } | null
  /** Present only on a payload returned by GET /api/runs/{id} — the saved drawn ring. */
  site_polygon_lonlat?: LngLat[]
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const j = await res.json()
      if (j?.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return (await res.json()) as T
}

export function fetchBuildings(polygon: LngLat[]): Promise<BuildingsPreview> {
  return postJson<BuildingsPreview>('/api/buildings', { polygon })
}

export interface EvaluateParams {
  polygon: LngLat[]
  budget_eur?: number
  w_thermal?: number
  w_ecological?: number
}

export function fetchEvaluate(params: EvaluateParams): Promise<EvaluateResponse> {
  return postJson<EvaluateResponse>('/api/evaluate', params)
}

// ── Citywide (Mode 2) ───────────────────────────────────────────────────────

import type { CitywideScan } from './types'

export async function fetchCitywideScan(topN = 20, budgetEur = 1_000_000): Promise<CitywideScan> {
  const res = await fetch(apiUrl(`/api/citywide/scan?top_n=${topN}&budget_eur=${budgetEur}`))
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return (await res.json()) as CitywideScan
}

// ── Saved runs (make it remember) ────────────────────────────────────────────

/** One row in the saved-runs gallery — headline KPIs only (no heavy geometry). */
export interface RunSummary {
  id: number
  created_at: string
  name: string
  backend: string | null
  budget_eur: number | null
  delta_utci_c: number | null
  cooled_m2: number | null
  n_trees: number | null
  cost_eur: number | null
  eur_per_m2: number | null
}

export interface SaveRunParams {
  name: string
  polygon: LngLat[]
  budget_eur?: number
  w_thermal?: number
  w_ecological?: number
  /** The evaluate response to persist (decision/boundary/trees/bounds + image URLs). */
  payload: EvaluateResponse
}

export function saveRun(params: SaveRunParams): Promise<{ id: number }> {
  return postJson<{ id: number }>('/api/runs', params)
}

export async function listRuns(): Promise<RunSummary[]> {
  const res = await fetch(apiUrl('/api/runs'))
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return (await res.json()) as RunSummary[]
}

/** Load a saved run as an evaluate response the Scene re-renders via the usual path. */
export async function getRun(id: number): Promise<EvaluateResponse> {
  const res = await fetch(apiUrl(`/api/runs/${id}`))
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return (await res.json()) as EvaluateResponse
}

/**
 * Convert an /api/evaluate response into the WebBundle the Scene renders.
 * Image URLs get a cache-buster so a re-evaluation (same filename, overwritten
 * on the server) is not served stale from the browser cache.
 */
export function evaluateResponseToBundle(r: EvaluateResponse): WebBundle {
  const bust = `?t=${Date.now()}`
  return {
    decision: r.decision,
    boundary: r.boundary,
    trees: r.trees,
    bounds: r.bounds,
    baselineImageUrl: r.baselineImageUrl ? r.baselineImageUrl + bust : '',
    interventionImageUrl: r.interventionImageUrl ? r.interventionImageUrl + bust : '',
    impervious: r.impervious ?? null,
    canopy: r.canopy ?? null,
    growth: r.growth ?? null,
  }
}
