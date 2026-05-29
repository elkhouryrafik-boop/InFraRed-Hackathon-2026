import { describe, it, expect } from 'vitest'
import {
  formatCount,
  formatEuro,
  formatArea,
  formatRate,
  formatTemp,
  formatDelta,
  toKpiView,
  rankOne,
} from './format'
import type { Configuration } from './types'

const cfg = (over: Partial<Configuration> = {}): Configuration => ({
  rank: 1,
  label: 'Balanced canopy',
  tree_count: 128,
  cost_eur: 96000,
  cooled_footprint_m2: 12450,
  eur_per_m2: 7.71,
  delta_utci_c: -2.4,
  utci_baseline_mean: 33.1,
  utci_baseline_peak: 41.2,
  utci_intervention_mean: 30.7,
  utci_intervention_peak: 38.8,
  species: ['Platanus', 'Celtis'],
  ...over,
})

describe('format helpers', () => {
  it('formats counts with separators', () => {
    expect(formatCount(1234)).toBe('1,234')
    expect(formatCount(NaN)).toBe('—')
  })

  it('formats euros compactly above thresholds', () => {
    expect(formatEuro(96000)).toBe('€96k')
    expect(formatEuro(1_200_000)).toBe('€1.2M')
    expect(formatEuro(2_000_000)).toBe('€2M')
    expect(formatEuro(950)).toBe('€950')
  })

  it('formats area and rate', () => {
    expect(formatArea(12450)).toBe('12,450 m²')
    expect(formatRate(7.71)).toBe('€7.71/m²')
  })

  it('formats temperature and signed delta', () => {
    expect(formatTemp(38.8)).toBe('38.8°C')
    expect(formatDelta(-2.4)).toBe('−2.4°C')
    expect(formatDelta(0.4)).toBe('+0.4°C')
    expect(formatDelta(0)).toBe('±0.0°C')
  })
})

describe('toKpiView', () => {
  it('projects a configuration into display strings', () => {
    const v = toKpiView(cfg())
    expect(v.trees).toBe('128')
    expect(v.cost).toBe('€96k')
    expect(v.baselinePeak).toBe('41.2°C')
    expect(v.interventionPeak).toBe('38.8°C')
    expect(v.isCooling).toBe(true)
    expect(v.species).toEqual(['Platanus', 'Celtis'])
  })

  it('flags non-cooling outcomes', () => {
    const v = toKpiView(
      cfg({ utci_baseline_peak: 35, utci_intervention_peak: 36 }),
    )
    expect(v.isCooling).toBe(false)
  })
})

describe('rankOne', () => {
  it('returns the lowest-rank configuration', () => {
    const configs = [cfg({ rank: 3 }), cfg({ rank: 1 }), cfg({ rank: 2 })]
    expect(rankOne(configs)?.rank).toBe(1)
  })

  it('returns null for an empty list', () => {
    expect(rankOne([])).toBeNull()
  })
})
