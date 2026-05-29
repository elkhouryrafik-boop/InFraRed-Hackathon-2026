// Loads the "web bundle" from /web_bundle/. Pure data fetching — no deck.gl.

import type {
  Decision,
  BoundaryGeoJSON,
  TreesGeoJSON,
  RasterBounds,
  WebBundle,
} from './types'

const BASE = `${import.meta.env.BASE_URL}web_bundle`

async function getJson<T>(name: string): Promise<T> {
  const res = await fetch(`${BASE}/${name}`)
  if (!res.ok) throw new Error(`Failed to load ${name}: ${res.status} ${res.statusText}`)
  return (await res.json()) as T
}

/**
 * Extract the outer ring of the site boundary as a closed [lon, lat][] array,
 * suitable for SolidPolygonLayer / PolygonLayer `polygon`.
 */
export function boundaryOuterRing(boundary: BoundaryGeoJSON): [number, number][] | null {
  const f = boundary.features.find((x) => x.geometry?.type === 'Polygon')
  if (!f) return null
  const ring = f.geometry.coordinates?.[0]
  if (!ring || ring.length < 3) return null
  return ring
}

/** BitmapLayer wants [west, south, east, north]. */
export function toDeckBounds(b: RasterBounds): [number, number, number, number] {
  return [b.west, b.south, b.east, b.north]
}

/** Load every file in the bundle in parallel. */
export async function loadWebBundle(): Promise<WebBundle> {
  const [decision, boundary, trees, bounds] = await Promise.all([
    getJson<Decision>('decision.json'),
    getJson<BoundaryGeoJSON>('boundary.geojson'),
    getJson<TreesGeoJSON>('trees.geojson'),
    getJson<RasterBounds>('bounds.json'),
  ])

  return {
    decision,
    boundary,
    trees,
    bounds,
    baselineImageUrl: `${BASE}/utci_baseline.png`,
    interventionImageUrl: `${BASE}/utci_intervention.png`,
  }
}
