import { describe, it, expect } from 'vitest'
import {
  ringAreaM2,
  haversineM,
  rectRing,
  circleRing,
  areaStatus,
  closeRing,
  MAX_AREA_M2,
  MIN_AREA_M2,
  type LngLat,
} from './draw'

// A reference point in the Eixample, Barcelona.
const C: LngLat = [2.167, 41.383]

describe('ringAreaM2', () => {
  it('measures a ~100 m square within 1%', () => {
    // 100 m east + 100 m north of C, built via circleRing math indirectly:
    // construct a rectangle whose sides are ~100 m using metre offsets.
    const mPerDegLat = (Math.PI / 180) * 6_378_137
    const mPerDegLon = mPerDegLat * Math.cos(C[1] * (Math.PI / 180))
    const a: LngLat = C
    const b: LngLat = [C[0] + 100 / mPerDegLon, C[1] + 100 / mPerDegLat]
    const area = ringAreaM2(rectRing(a, b))
    expect(area).toBeGreaterThan(9_900)
    expect(area).toBeLessThan(10_100)
  })

  it('returns 0 for degenerate rings', () => {
    expect(ringAreaM2([C, C])).toBe(0)
  })
})

describe('haversineM', () => {
  it('is ~0 for identical points', () => {
    expect(haversineM(C, C)).toBeCloseTo(0, 6)
  })
  it('measures a known short distance', () => {
    const mPerDegLat = (Math.PI / 180) * 6_378_137
    const north: LngLat = [C[0], C[1] + 50 / mPerDegLat]
    expect(haversineM(C, north)).toBeGreaterThan(49)
    expect(haversineM(C, north)).toBeLessThan(51)
  })
})

describe('rectRing', () => {
  it('returns a closed 5-point ring regardless of corner order', () => {
    const r = rectRing([2.17, 41.39], [2.16, 41.38])
    expect(r.length).toBe(5)
    expect(r[0]).toEqual(r[4])
  })
})

describe('circleRing', () => {
  it('approximates circle area = pi r^2', () => {
    const mPerDegLat = (Math.PI / 180) * 6_378_137
    const edge: LngLat = [C[0], C[1] + 60 / mPerDegLat] // r ~ 60 m
    const area = ringAreaM2(circleRing(C, edge, 64))
    const expected = Math.PI * 60 * 60
    // 64-gon slightly under-fills the circle; allow 3%.
    expect(area).toBeGreaterThan(expected * 0.97)
    expect(area).toBeLessThanOrEqual(expected)
  })
})

describe('areaStatus', () => {
  it('classifies against the caps', () => {
    expect(areaStatus(MIN_AREA_M2 - 1)).toBe('too_small')
    expect(areaStatus(MAX_AREA_M2 + 1)).toBe('too_large')
    expect(areaStatus((MIN_AREA_M2 + MAX_AREA_M2) / 2)).toBe('ok')
  })
})

describe('closeRing', () => {
  it('closes an open ring and leaves a closed one', () => {
    const open: LngLat[] = [[0, 0], [1, 0], [1, 1]]
    expect(closeRing(open).length).toBe(4)
    expect(closeRing(closeRing(open)).length).toBe(4)
  })
})
