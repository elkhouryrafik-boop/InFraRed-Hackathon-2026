// GrowthSlider — canopy-over-time scrubber (Redesign Spec §4.5). Docked inside
// the Result Card. Native <input type="range"> (C7) with ticks at 0/10/20/30/40,
// mint fill, canopy % tweening live as you scrub (tabular-nums). Full keyboard
// + aria-valuetext; dependent readout in aria-live="polite".
//
// Each tree's canopy disk grows on its OWN species allometric curve (see
// lib/growth.ts); this readout shows a representative medium-growth species for
// orientation and states the species spread.

import './GrowthSlider.css'
import { coolingFractionAtAge, MAX_MATURITY_YEARS, type GrowthParams } from '../lib/growth'

interface GrowthSliderProps {
  year: number
  setYear: (y: number) => void
  params?: GrowthParams // retained for API compatibility; not used by the curve
}

// Representative medium-growth species (maturity 30 yr, ~7 m mature crown).
const REF_MATURE_CROWN_M = 7
const REF_MATURITY_YEARS = 30
const TICKS = [0, 10, 20, 30, 40]

export function GrowthSlider({ year, setYear }: GrowthSliderProps) {
  const y = Math.min(year, MAX_MATURITY_YEARS)
  const mature = year >= MAX_MATURITY_YEARS
  const frac = coolingFractionAtAge(REF_MATURE_CROWN_M, REF_MATURITY_YEARS, year)
  const pct = Math.round(frac * 100)
  const fillPct = (y / MAX_MATURITY_YEARS) * 100
  const valueText = mature
    ? `Year ${MAX_MATURITY_YEARS} or more — mature canopy ${pct}%`
    : `Year ${y} — canopy ${pct}%`

  return (
    <div className="growth-slider">
      <div className="growth-slider__head">
        <span className="growth-slider__label">Canopy over time</span>
        <span className="growth-slider__year">
          <strong className="tnum">{mature ? `${MAX_MATURITY_YEARS}+` : `Year ${y}`}</strong>
          <span className="growth-slider__pct tnum"> {pct}% canopy</span>
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={MAX_MATURITY_YEARS}
        step={1}
        value={y}
        onChange={(e) => setYear(Number(e.target.value))}
        aria-label="Years after planting"
        aria-valuemin={0}
        aria-valuemax={MAX_MATURITY_YEARS}
        aria-valuenow={y}
        aria-valuetext={valueText}
        style={{
          background: `linear-gradient(90deg, var(--brand) 0%, var(--brand) ${fillPct}%, var(--surface-3) ${fillPct}%, var(--surface-3) 100%)`,
        }}
      />
      <div className="growth-slider__ticks" aria-hidden>
        {TICKS.map((t) => (
          <span key={t} className="tnum">{t}</span>
        ))}
      </div>
      <div className="growth-slider__stat" aria-live="polite">
        {mature
          ? 'all species mature — heatmap shows mature canopy'
          : 'each species on its own curve (fast ~20 yr, slow ~40 yr); heatmap = mature'}
      </div>
    </div>
  )
}
