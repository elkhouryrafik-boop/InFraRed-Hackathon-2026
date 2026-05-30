import { useEffect, useState } from 'react'
import { Scene } from './components/Scene'
import { FallbackScene } from './components/FallbackScene'
import { loadWebBundle } from './lib/bundle'
import type { WebBundle } from './lib/types'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined
const hasMapboxToken = !!MAPBOX_TOKEN && MAPBOX_TOKEN.trim().length > 0

export default function App() {
  const [bundle, setBundle] = useState<WebBundle | null>(null)
  // A bundle produced live by /api/evaluate (drawing flow) overrides the initial
  // static bundle once the user evaluates a hand-drawn area.
  const [liveBundle, setLiveBundle] = useState<WebBundle | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    loadWebBundle()
      .then((b) => {
        if (!cancelled) setBundle(b)
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (error) {
    return (
      <div className="center-overlay">
        <strong style={{ color: '#ff9a8a' }}>Could not load web bundle</strong>
        <div style={{ maxWidth: 420, fontSize: 13 }}>{error}</div>
        <div style={{ fontSize: 12, color: '#6f8a84' }}>
          Expected files in <code>public/web_bundle/</code> (decision.json,
          boundary.geojson, trees.geojson, bounds.json, utci_*.png).
        </div>
      </div>
    )
  }

  if (!bundle) {
    return (
      <div className="center-overlay">
        <div className="spinner" aria-label="Loading" />
        <div>Loading Barcelona cooling scenario…</div>
      </div>
    )
  }

  // The live (evaluated) bundle takes precedence over the initial static one.
  const active = liveBundle ?? bundle

  // Route on Mapbox token: full Mapbox+Cesium scene (with the drawing flow), or
  // flat deck.gl fallback (view-only; drawing needs the Mapbox map).
  return hasMapboxToken ? (
    <Scene bundle={active} onBundle={setLiveBundle} />
  ) : (
    <FallbackScene bundle={active} />
  )
}
