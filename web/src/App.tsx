import { useEffect, useState } from 'react'
import { Scene } from './components/Scene'
import { FallbackScene } from './components/FallbackScene'
import { IntroVideoGate } from './components/IntroVideoGate'
import { loadWebBundle } from './lib/bundle'
import type { WebBundle, Phase } from './lib/types'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined
const hasMapboxToken = !!MAPBOX_TOKEN && MAPBOX_TOKEN.trim().length > 0

const SEEN_KEY = 'coolspend_seen'
const VIDEO_SEEN_KEY = 'coolspend_video_seen'

export default function App() {
  const [bundle, setBundle] = useState<WebBundle | null>(null)
  // A bundle produced live by /api/evaluate (drawing flow) overrides the initial
  // static bundle once the user evaluates a hand-drawn area.
  const [liveBundle, setLiveBundle] = useState<WebBundle | null>(null)
  const [error, setError] = useState<string | null>(null)

  // First-visit explainer gate: plays the ~11-min film, then drops the viewer
  // into the populated citywide plan (skips the redundant in-app intro story).
  const [showVideo, setShowVideo] = useState<boolean>(() => {
    try {
      return localStorage.getItem(VIDEO_SEEN_KEY) !== '1'
    } catch {
      return false
    }
  })

  // ── Phase machine (Redesign Spec §3.1): the single source of truth that
  // absorbs the old loose appMode. First run → the intro story. A returning
  // judge boots straight into the €1M CITYWIDE plan, so you immediately see the
  // trees placed across the 7 funded sites + all the measured data — not an
  // empty draw canvas.
  const [phase, setPhase] = useState<Phase>(() => {
    try {
      return localStorage.getItem(SEEN_KEY) === '1' ? 'citywide' : 'intro'
    } catch {
      return 'citywide'
    }
  })

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

  const dismissVideo = () => {
    try {
      localStorage.setItem(VIDEO_SEEN_KEY, '1')
      localStorage.setItem(SEEN_KEY, '1')
    } catch {
      /* ignore */
    }
    setPhase('citywide')
    setShowVideo(false)
  }

  // The live (evaluated) bundle takes precedence over the initial static one.
  const active = liveBundle ?? bundle

  // Route on Mapbox token: full Mapbox+Cesium scene (with the drawing flow), or
  // flat deck.gl fallback (view-only; drawing needs the Mapbox map).
  return (
    <>
      {showVideo && <IntroVideoGate onDone={dismissVideo} />}
      {hasMapboxToken ? (
        <Scene
          bundle={active}
          onBundle={setLiveBundle}
          phase={phase}
          setPhase={setPhase}
          seenKey={SEEN_KEY}
        />
      ) : (
        <FallbackScene bundle={active} />
      )}
    </>
  )
}
