// Client-side draw geometry for the "select an area in Barcelona" flow.
// Pure functions, no deck.gl / DOM — unit-testable in vitest.
//
// All rings are [lon, lat][] and returned CLOSED (first === last). Areas use a
// latitude-scaled equirectangular projection: at city-block scale (<300 m) the
// error vs a true geodesic area is well under 0.5 %, which is plenty for a
// selection cap.

export type DrawMode = 'rectangle' | 'circle' | 'polygon'

export type LngLat = [number, number]

// Must mirror the server caps in coolspend/api_server.py.
export const MAX_AREA_M2 = 62_500 // 250 m x 250 m
export const MIN_AREA_M2 = 400 // 20 m x 20 m

const EARTH_R = 6_378_137 // WGS84 equatorial radius (m)
const DEG2RAD = Math.PI / 180

/** Polygon area in m² via a latitude-scaled equirectangular shoelace. */
export function ringAreaM2(ring: LngLat[]): number {
  if (ring.length < 3) return 0
  // Reference latitude for the cos scale = mean latitude of the ring.
  const lat0 =
    (ring.reduce((s, p) => s + p[1], 0) / ring.length) * DEG2RAD
  const cosLat0 = Math.cos(lat0)
  const xy = ring.map(([lon, lat]) => [
    lon * DEG2RAD * EARTH_R * cosLat0,
    lat * DEG2RAD * EARTH_R,
  ])
  let area2 = 0
  for (let i = 0; i < xy.length; i++) {
    const [x1, y1] = xy[i]
    const [x2, y2] = xy[(i + 1) % xy.length]
    area2 += x1 * y2 - x2 * y1
  }
  return Math.abs(area2) / 2
}

/** Great-circle distance between two lon/lat points (m). */
export function haversineM(a: LngLat, b: LngLat): number {
  const dLat = (b[1] - a[1]) * DEG2RAD
  const dLon = (b[0] - a[0]) * DEG2RAD
  const lat1 = a[1] * DEG2RAD
  const lat2 = b[1] * DEG2RAD
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2
  return 2 * EARTH_R * Math.asin(Math.min(1, Math.sqrt(h)))
}

/** Axis-aligned rectangle (closed ring) from two opposite corners. */
export function rectRing(a: LngLat, b: LngLat): LngLat[] {
  const w = Math.min(a[0], b[0])
  const e = Math.max(a[0], b[0])
  const s = Math.min(a[1], b[1])
  const n = Math.max(a[1], b[1])
  return [
    [w, s],
    [e, s],
    [e, n],
    [w, n],
    [w, s],
  ]
}

/** Regular n-gon (closed ring) approximating a circle: center + edge point. */
export function circleRing(center: LngLat, edge: LngLat, segments = 48): LngLat[] {
  const radius = haversineM(center, edge)
  const lat0 = center[1] * DEG2RAD
  // metres-per-degree at this latitude
  const mPerDegLat = (Math.PI / 180) * EARTH_R
  const mPerDegLon = mPerDegLat * Math.cos(lat0)
  const ring: LngLat[] = []
  for (let i = 0; i < segments; i++) {
    const t = (i / segments) * 2 * Math.PI
    const dx = radius * Math.cos(t) // east metres
    const dy = radius * Math.sin(t) // north metres
    ring.push([center[0] + dx / mPerDegLon, center[1] + dy / mPerDegLat])
  }
  ring.push(ring[0])
  return ring
}

export type AreaStatus = 'ok' | 'too_small' | 'too_large'

export function areaStatus(area: number): AreaStatus {
  if (area > MAX_AREA_M2) return 'too_large'
  if (area < MIN_AREA_M2) return 'too_small'
  return 'ok'
}

/** Close a ring if the caller left it open. */
export function closeRing(ring: LngLat[]): LngLat[] {
  if (ring.length === 0) return ring
  const [f] = ring
  const l = ring[ring.length - 1]
  return f[0] === l[0] && f[1] === l[1] ? ring : [...ring, f]
}
