// HTTP client for the CoolSpend backend (coolspend/api_server.py).
// In dev, vite proxies /api -> http://localhost:8000 (see vite.config.ts).

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
  decision: Decision
  boundary: BoundaryGeoJSON
  trees: TreesGeoJSON
  bounds: RasterBounds
  baselineImageUrl: string | null
  interventionImageUrl: string | null
  impervious?: ImperviousAnalysis | null
  canopy?: CanopyCover | null
  growth?: { ramp_years: number; initial_fraction: number; horizon_years: number } | null
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
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
