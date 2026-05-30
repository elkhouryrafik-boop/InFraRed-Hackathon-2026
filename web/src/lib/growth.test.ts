import { describe, it, expect } from 'vitest'
import { coolingFraction, canopyScale, DEFAULT_GROWTH } from './growth'

// These values must match coolspend/cost_model.py::growth_cooling_fraction
// (verified against the Python implementation: 0→0.2, 5→0.36, 12→0.584, 25→1.0).
describe('coolingFraction', () => {
  it('starts at initial_fraction at year 0', () => {
    expect(coolingFraction(0)).toBeCloseTo(0.2, 6)
  })
  it('reaches 1.0 at ramp_years and stays there', () => {
    expect(coolingFraction(DEFAULT_GROWTH.ramp_years)).toBeCloseTo(1.0, 6)
    expect(coolingFraction(DEFAULT_GROWTH.ramp_years + 15)).toBeCloseTo(1.0, 6)
  })
  it('matches the Python linear ramp at intermediate years', () => {
    expect(coolingFraction(5)).toBeCloseTo(0.36, 6)
    expect(coolingFraction(12)).toBeCloseTo(0.584, 6)
  })
  it('is monotonic non-decreasing', () => {
    let prev = -1
    for (let y = 0; y <= 30; y++) {
      const f = coolingFraction(y)
      expect(f).toBeGreaterThanOrEqual(prev)
      prev = f
    }
  })
  it('respects custom params', () => {
    const p = { ramp_years: 10, initial_fraction: 0.5, horizon_years: 40 }
    expect(coolingFraction(0, p)).toBeCloseTo(0.5, 6)
    expect(coolingFraction(10, p)).toBeCloseTo(1.0, 6)
  })
})

describe('canopyScale', () => {
  it('tracks coolingFraction (single sourced curve)', () => {
    expect(canopyScale(0)).toBeCloseTo(coolingFraction(0), 6)
    expect(canopyScale(25)).toBeCloseTo(1.0, 6)
  })
})
