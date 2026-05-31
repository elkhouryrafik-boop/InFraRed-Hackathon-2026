import { describe, it, expect } from 'vitest'
import {
  coolingFraction,
  canopyScale,
  DEFAULT_GROWTH,
  crownDiameterAtAge,
  coolingFractionAtAge,
  PLANTING_CROWN_M,
} from './growth'

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

// Chapman–Richards species curve — must match coolspend/growth.py.
// Python reference: Tipuana (mature 10, maturity 20): age0=1.50, age10≈6.58,
// age20≈9.50. Cercis (mature 5, maturity 40): age20≈3.29.
describe('crownDiameterAtAge', () => {
  it('starts at the planting crown at age 0', () => {
    expect(crownDiameterAtAge(10, 20, 0)).toBeCloseTo(PLANTING_CROWN_M, 6)
  })
  it('matches the Python curve at intermediate ages', () => {
    expect(crownDiameterAtAge(10, 20, 10)).toBeCloseTo(6.58, 1)
    expect(crownDiameterAtAge(10, 20, 20)).toBeCloseTo(9.5, 1)
    expect(crownDiameterAtAge(5, 40, 20)).toBeCloseTo(3.29, 1)
  })
  it('never exceeds the mature crown', () => {
    for (const age of [0, 10, 25, 60, 200]) {
      expect(crownDiameterAtAge(10, 20, age)).toBeLessThanOrEqual(10 + 1e-9)
    }
  })
  it('fast species lead slow species at the same age', () => {
    expect(coolingFractionAtAge(10, 20, 20)).toBeGreaterThan(
      coolingFractionAtAge(5, 40, 20),
    )
  })
  it('reaches ~90% cooling (area) at the maturity year', () => {
    expect(coolingFractionAtAge(10, 20, 20)).toBeCloseTo(0.9, 1)
  })
})
