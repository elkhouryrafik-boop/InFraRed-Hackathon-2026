import { describe, it, expect } from 'vitest'
import {
  utciColor,
  utciCssColor,
  utciGradientCss,
  clamp,
  UTCI_MIN,
  UTCI_MAX,
  UTCI_STOPS,
} from './colorscale'

describe('clamp', () => {
  it('clamps into range', () => {
    expect(clamp(5, 0, 10)).toBe(5)
    expect(clamp(-1, 0, 10)).toBe(0)
    expect(clamp(11, 0, 10)).toBe(10)
  })
})

describe('utciColor', () => {
  it('returns exact stop colours at anchors', () => {
    for (const s of UTCI_STOPS) {
      expect(utciColor(s.value)).toEqual(s.color)
    }
  })

  it('clamps below min and above max', () => {
    expect(utciColor(UTCI_MIN - 50)).toEqual(UTCI_STOPS[0].color)
    expect(utciColor(UTCI_MAX + 50)).toEqual(UTCI_STOPS[UTCI_STOPS.length - 1].color)
  })

  it('interpolates between stops (monotone, valid rgb)', () => {
    const mid = utciColor((UTCI_STOPS[0].value + UTCI_STOPS[1].value) / 2)
    expect(mid).toHaveLength(3)
    for (const c of mid) {
      expect(c).toBeGreaterThanOrEqual(0)
      expect(c).toBeLessThanOrEqual(255)
    }
  })

  it('handles non-finite input gracefully', () => {
    expect(utciColor(NaN)).toEqual([128, 128, 128])
  })
})

describe('css helpers', () => {
  it('emits an rgb() string', () => {
    expect(utciCssColor(UTCI_MIN)).toMatch(/^rgb\(\d+, \d+, \d+\)$/)
  })

  it('builds a linear-gradient spanning 0%..100%', () => {
    const g = utciGradientCss(4)
    expect(g).toContain('linear-gradient(90deg')
    expect(g).toContain('0.0%')
    expect(g).toContain('100.0%')
  })
})
