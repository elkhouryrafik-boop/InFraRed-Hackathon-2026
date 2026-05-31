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

  it('does not claim cooling when peaks are null (mock backend)', () => {
    const v = toKpiView(
      cfg({ utci_baseline_peak: null, utci_intervention_peak: null }),
    )
    expect(v.isCooling).toBe(false)
    expect(v.baselinePeak).toBe('—')
    expect(v.interventionPeak).toBe('—')
  })

  it('projects the cooling-depth bands and heat-stress relief', () => {
    const v = toKpiView(
      cfg({
        cooled_profile: {
          cooled_m2_by_band: { '0.5': 3940, '1': 2928, '2': 1628 },
          mean_drop_c: 1.9,
          peak_drop_c: 6.82,
          cooled_fraction: 0.48,
          heat_stress_relieved_m2: 1040,
          heat_stress_threshold_c: 26,
          valid_cells_m2: 8167,
          bands_c: [0.5, 1.0, 2.0],
        },
      }),
    )
    expect(v.depth).toBe('2,928 m² ≥1°C · 1,628 m² ≥2°C')
    expect(v.heatStressRelieved).toBe('1,040 m²')
  })

  it('emits an empty depth string when no profile is present', () => {
    expect(toKpiView(cfg()).depth).toBe('')
    expect(toKpiView(cfg()).heatStressRelieved).toBe('—')
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
