// GrowthSlider — bottom-centre age slider (0–40 yr after planting). Each tree's
// canopy disk grows on its OWN species allometric curve (Chapman–Richards, see
// lib/growth.ts, mirroring coolspend/growth.py); this readout shows a typical
// medium-growth species for orientation and states the species spread.

import { coolingFractionAtAge, MAX_MATURITY_YEARS, type GrowthParams } from '../lib/growth'

interface GrowthSliderProps {
  year: number
  setYear: (y: number) => void
  params?: GrowthParams // retained for API compatibility; not used by the curve
}

// Representative medium-growth species (maturity 30 yr, ~7 m mature crown) for
// the headline %. Fast species lead this, slow species lag it.
const REF_MATURE_CROWN_M = 7
const REF_MATURITY_YEARS = 30

export function GrowthSlider({ year, setYear }: GrowthSliderProps) {
  const mature = year >= MAX_MATURITY_YEARS
  const frac = coolingFractionAtAge(REF_MATURE_CROWN_M, REF_MATURITY_YEARS, year)
  return (
    <div className="growth-slider">
      <div className="growth-slider__head">
        <span className="growth-slider__label">Years after planting</span>
        <span className="growth-slider__year">
          {mature ? `${MAX_MATURITY_YEARS}+ (mature)` : year}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={MAX_MATURITY_YEARS}
        step={1}
        value={Math.min(year, MAX_MATURITY_YEARS)}
        onChange={(e) => setYear(Number(e.target.value))}
      />
      <div className="growth-slider__stat">
        Typical canopy: <strong>{Math.round(frac * 100)}%</strong> of mature
        <span className="growth-slider__note">
          {mature
            ? 'all species mature — heatmap shows mature canopy'
            : 'each species on its own curve (fast ~20 yr, slow ~40 yr); heatmap = mature'}
        </span>
      </div>
    </div>
  )
}
