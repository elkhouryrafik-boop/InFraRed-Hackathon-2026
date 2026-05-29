// UTCI colour-scale legend. Uses the pure colorscale module — no deck.gl.

import { useMemo } from 'react'
import { utciGradientCss, UTCI_MIN, UTCI_MAX, UTCI_STOPS } from '../lib/colorscale'

export function Legend() {
  const gradient = useMemo(() => utciGradientCss(28), [])
  return (
    <div className="legend">
      <div className="legend__title">Felt temperature (UTCI °C)</div>
      <div className="legend__bar" style={{ background: gradient }} />
      <div className="legend__scale">
        {UTCI_STOPS.map((s) => (
          <span key={s.value}>{s.value}°</span>
        ))}
      </div>
      <div className="legend__scale" style={{ marginTop: 2 }}>
        <span>{UTCI_MIN}° comfortable</span>
        <span>{UTCI_MAX}° extreme</span>
      </div>
    </div>
  )
}
