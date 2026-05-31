// UTCI colour-scale legend — gradient key, bottom-right, always visible (§4.8).
// Uses the §2 CVD-safe ramp via the --ramp-utci token; prints numeric °C
// breakpoints at the UTCI stress thresholds so colour is never the sole signal
// (B2). A hatch marks the ≥38 °C "very strong" band for greyscale/CVD readers.

import './Legend.css'

const BREAKS = [20, 26, 32, 38, 46]

export function Legend() {
  return (
    <div className="legend panel" role="img" aria-label="Felt temperature scale, 20 to 46 degrees Celsius, cool to extreme">
      <div className="legend__title">Feels-like (UTCI °C)</div>
      <div className="legend__bar">
        <span className="legend__hatch" aria-hidden title="≥38 °C very strong heat stress" />
      </div>
      <div className="legend__scale tnum">
        {BREAKS.map((v) => (
          <span key={v}>{v}{v === 46 ? '+' : ''}</span>
        ))}
      </div>
      <div className="legend__ends">
        <span>cool</span>
        <span>extreme</span>
      </div>
    </div>
  )
}
