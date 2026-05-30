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
