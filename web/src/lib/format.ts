// Pure KPI formatting helpers. NO deck.gl import — unit-testable headless.

import type { Configuration } from './types'

/** Format an integer count with thousands separators, e.g. 1234 -> "1,234". */
export function formatCount(n: number): string {
  if (!Number.isFinite(n)) return '—'
  return Math.round(n).toLocaleString('en-US')
}

/**
 * Format euros. Compact above ten thousand (€1.2M, €340k), exact below.
 * Always prefixed with the euro sign.
 */
export function formatEuro(n: number): string {
  if (!Number.isFinite(n)) return '—'
  if (Math.abs(n) >= 1_000_000) return `€${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)}M`
  if (Math.abs(n) >= 10_000) return `€${(n / 1000).toFixed(0)}k`
  return `€${Math.round(n).toLocaleString('en-US')}`
}

/** Format square metres with thousands separators and the m² unit. */
export function formatArea(n: number): string {
  if (!Number.isFinite(n)) return '—'
  return `${Math.round(n).toLocaleString('en-US')} m²`
}

/** Format a €/m² rate to two decimals. */
export function formatRate(n: number): string {
  if (!Number.isFinite(n)) return '—'
  return `€${n.toFixed(2)}/m²`
}

/** Format a temperature in °C with one decimal. */
export function formatTemp(n: number): string {
  if (!Number.isFinite(n)) return '—'
  return `${n.toFixed(1)}°C`
}

/**
 * Format a signed temperature delta, e.g. -2.3°C or +0.4°C.
 * Cooling (a reduction) is conventionally a NEGATIVE delta_utci_c.
 */
export function formatDelta(n: number): string {
  if (!Number.isFinite(n)) return '—'
  const sign = n > 0 ? '+' : n < 0 ? '−' : '±'
  return `${sign}${Math.abs(n).toFixed(1)}°C`
}

/** A flat, render-ready KPI bundle for the rank-1 (or any) configuration. */
export interface KpiView {
  rank: number
  label: string
  trees: string
  cost: string
  cooledArea: string
  rate: string
  baselinePeak: string
  interventionPeak: string
  delta: string
  /** True when the intervention is cooler than baseline (good). */
  isCooling: boolean
  species: string[]
}

/** Project a Configuration into formatted, display-ready strings. */
export function toKpiView(c: Configuration): KpiView {
  return {
    rank: c.rank,
    label: c.label,
    trees: formatCount(c.tree_count),
    cost: formatEuro(c.cost_eur),
    cooledArea: formatArea(c.cooled_footprint_m2),
    rate: formatRate(c.eur_per_m2),
    baselinePeak: formatTemp(c.utci_baseline_peak),
    interventionPeak: formatTemp(c.utci_intervention_peak),
    delta: formatDelta(c.delta_utci_c),
    isCooling: c.utci_intervention_peak <= c.utci_baseline_peak,
    species: c.species,
  }
}

/** Pick the rank-1 configuration (lowest rank). Falls back to the first. */
export function rankOne(configs: Configuration[]): Configuration | null {
  if (!configs || configs.length === 0) return null
  return [...configs].sort((a, b) => a.rank - b.rank)[0]
}
