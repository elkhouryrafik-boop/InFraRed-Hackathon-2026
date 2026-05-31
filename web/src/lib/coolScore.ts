// Cool Score — the Tree-Equity-Score move (Redesign Spec §4.2): collapse the
// cooling composite into ONE legible 0–100 number. Pure + headless-testable.
//
// Inputs come straight from the existing Decision contract (no new data). The
// score blends three measured signals when available, each already produced by
// the pipeline:
//   • mean UTCI drop (ΔUTCI °C, positive = cooling) — the headline cooling
//   • cooled fraction of the site (cooled_footprint_m2 / a reference area)
//   • peak felt-like relief (baseline_peak − intervention_peak)
// On the mock backend (Δ = 0, KPIs null) the score is null → the card shows a
// PREVIEW state instead of a fake number.

import type { Configuration, Decision } from './types'

export interface CoolScoreView {
  /** 0–100, or null when there is no measured cooling to score (mock). */
  score: number | null
  /** Short verdict for under the gauge. */
  verdict: string
  /** True only when cooling is genuinely measured (drives the MEASURED badge). */
  measured: boolean
}

/** City-wide reference for the "vs city avg" sparkline baseline (§4.2). */
export const CITY_AVG_COOL_SCORE = 41

function verdictFor(score: number): string {
  if (score >= 75) return 'strong impact'
  if (score >= 55) return 'solid impact'
  if (score >= 35) return 'modest impact'
  if (score > 0) return 'limited impact'
  return 'no measured cooling'
}

/**
 * Compute the 0–100 Cool Score from a configuration. Returns null when nothing
 * measurable is present (mock backend). The mapping is a transparent linear
 * blend, clamped — it is a presentation index for legibility, NOT a new
 * physical claim (the measured cooling is ΔUTCI itself).
 */
export function coolScoreFor(c: Configuration | null): number | null {
  if (!c) return null
  const delta = c.delta_utci_c // positive = cooling in this pipeline
  const bp = c.utci_baseline_peak
  const ip = c.utci_intervention_peak
  const peakDrop = Number.isFinite(bp) && Number.isFinite(ip) ? (bp as number) - (ip as number) : null

  // Nothing measured → no score (mock has Δ=0 and null peaks).
  const hasSignal =
    (Number.isFinite(delta) && Math.abs(delta) > 1e-6) ||
    (peakDrop != null && Math.abs(peakDrop) > 1e-6) ||
    (c.cooled_footprint_m2 != null && c.cooled_footprint_m2 > 0)
  if (!hasSignal) return null

  // ΔUTCI: 0 °C → 0, ~4 °C mean drop → full marks (a strong street-scale result).
  const deltaPts = Math.max(0, Math.min(1, delta / 4)) * 60
  // Peak relief: 0 → 0, 6 °C → full marks.
  const peakPts = peakDrop != null ? Math.max(0, Math.min(1, peakDrop / 6)) * 25 : 0
  // Cooled footprint presence (any measured cooled area) → up to 15.
  const cooledPts = c.cooled_footprint_m2 != null && c.cooled_footprint_m2 > 0 ? 15 : 0

  return Math.round(Math.max(0, Math.min(100, deltaPts + peakPts + cooledPts)))
}

/**
 * Credibility resolver (Redesign Spec §4.2 + HARD REQUIREMENT): MEASURED only
 * when the backend is NOT mock AND cooling is genuinely measured. Otherwise
 * PREVIEW. Never both.
 */
export function isMeasured(decision: Decision): boolean {
  return decision.backend !== 'mock' && (decision.backend === 'live' || decision.backend === 'cached')
}

export function coolScoreView(decision: Decision, c: Configuration | null): CoolScoreView {
  const measured = isMeasured(decision)
  const score = measured ? coolScoreFor(c) : null
  return {
    score,
    verdict: score != null ? verdictFor(score) : 'preview — run live to measure',
    measured,
  }
}
