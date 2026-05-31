// Tree establishment / growth model for the age slider.
//
// This MIRRORS coolspend/cost_model.py::growth_cooling_fraction exactly — a
// linear ramp from `initial_fraction` at planting to 1.0 at `ramp_years`:
//
//   frac(y) = initial + (1 - initial) * min(y / ramp_years, 1)
//
// It is the project's single, sourced growth curve (DECLARED linear ramp; see
// cost_model GrowthDiscountParams). We do NOT invent a second biological
// crown-diameter curve: the same fraction scales both the cooling readout and
// the visual canopy glyph, so the slider stays consistent with the cost model.

export interface GrowthParams {
  ramp_years: number
  initial_fraction: number
  horizon_years: number
}

export const DEFAULT_GROWTH: GrowthParams = {
  ramp_years: 25,
  initial_fraction: 0.2,
  horizon_years: 40,
}

/** Effective cooling fraction (0..1) at a given age in years. */
export function coolingFraction(year: number, p: GrowthParams = DEFAULT_GROWTH): number {
  const ramp = p.ramp_years > 0 ? Math.min(year / p.ramp_years, 1) : 1
  return p.initial_fraction + (1 - p.initial_fraction) * ramp
}

/**
 * Visual canopy scale (0..1) for the tree glyph at a given age. We scale the
 * glyph by the same establishment fraction (labelled as such in the UI) so the
 * canopy visibly grows with the slider without introducing an unsourced curve.
 */
export function canopyScale(year: number, p: GrowthParams = DEFAULT_GROWTH): number {
  return coolingFraction(year, p)
}

// ── Species-specific allometric growth (Chapman–Richards) ───────────────────
// Mirrors coolspend/growth.py exactly: crown(age) grows sigmoidally from a
// nursery planting crown to the species' mature crown, reaching ~95% at the
// species' maturity year. Used to grow each tree's canopy disk at its OWN pace
// (a fast Tipuana fills in ~2x sooner than a slow Cercis) instead of one flat
// global ramp. Anchored to real per-species values (mature crown + maturity
// band), not invented coefficients.

export const PLANTING_CROWN_M = 1.5 // large-caliper nursery stock crown at age 0
export const MAX_MATURITY_YEARS = 40 // slowest band — the slider's upper bound
const SHAPE_P = 3.0
const MATURITY_FRACTION = 0.95

function rateK(maturityYears: number): number {
  if (maturityYears <= 0) return 1.0
  const inner = 1 - Math.pow(MATURITY_FRACTION, 1 / SHAPE_P) // = e^(−k·T)
  return -Math.log(inner) / maturityYears
}

/** Mature-anchored crown diameter (m) at a given age after planting. */
export function crownDiameterAtAge(
  matureCrownM: number,
  maturityYears: number,
  ageYears: number,
): number {
  if (ageYears <= 0) return PLANTING_CROWN_M
  const k = rateK(maturityYears)
  const raw = matureCrownM * Math.pow(1 - Math.exp(-k * ageYears), SHAPE_P)
  return Math.max(PLANTING_CROWN_M, Math.min(matureCrownM, raw))
}

/** Fraction of mature shade delivered at a given age (crown AREA ratio, 0..1). */
export function coolingFractionAtAge(
  matureCrownM: number,
  maturityYears: number,
  ageYears: number,
): number {
  if (matureCrownM <= 0) return 1
  const r = crownDiameterAtAge(matureCrownM, maturityYears, ageYears) / matureCrownM
  return Math.min(1, r * r)
}
