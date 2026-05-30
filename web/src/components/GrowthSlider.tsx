// GrowthSlider — bottom-centre age slider that animates canopy growth over the
// establishment ramp and reports the cooling fraction at the selected age.
//
// The cooling fraction comes from lib/growth.ts, which mirrors cost_model's
// sourced linear establishment ramp exactly — so this is a real model readout,
// not a decorative slider.

import { coolingFraction, type GrowthParams } from '../lib/growth'

interface GrowthSliderProps {
  year: number
  setYear: (y: number) => void
  params: GrowthParams
}

export function GrowthSlider({ year, setYear, params }: GrowthSliderProps) {
  const frac = coolingFraction(year, params)
  const mature = year >= params.ramp_years
  return (
    <div className="growth-slider">
      <div className="growth-slider__head">
        <span className="growth-slider__label">Years after planting</span>
        <span className="growth-slider__year">{mature ? `${params.ramp_years}+ (mature)` : year}</span>
      </div>
      <input
        type="range"
        min={0}
        max={params.ramp_years}
        step={1}
        value={Math.min(year, params.ramp_years)}
        onChange={(e) => setYear(Number(e.target.value))}
      />
      <div className="growth-slider__stat">
        Canopy cooling: <strong>{Math.round(frac * 100)}%</strong> of mature
        <span className="growth-slider__note">
          {mature
            ? 'full-canopy sim (heatmap shown)'
            : 'establishment ramp — heatmap shows mature canopy'}
        </span>
      </div>
    </div>
  )
}
