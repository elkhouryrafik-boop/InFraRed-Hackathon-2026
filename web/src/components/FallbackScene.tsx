// No-Mapbox-token fallback: render deck.gl on its own canvas over a flat dark
// background (no basemap, no Cesium tiles). Overlays still fully render so the
// app NEVER white-screens (recipe spec #7).

import { useMemo, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { MapView } from '@deck.gl/core'
import type { Layer } from '@deck.gl/core'

import { Legend } from './Legend'
import { buildLayers } from '../lib/layers'
import { boundaryOuterRing, toDeckBounds } from '../lib/bundle'
import { rankOne, toKpiView } from '../lib/format'
import { coolScoreView } from '../lib/coolScore'
import type { WebBundle, UtciScenario } from '../lib/types'

interface FallbackSceneProps {
  bundle: WebBundle
}

export function FallbackScene({ bundle }: FallbackSceneProps) {
  const [lon, lat] = bundle.decision.site_center_lonlat
  const [scenario, setScenario] = useState<UtciScenario>('intervention')
  const [rasterOpacity, setRasterOpacity] = useState(0.7)

  const boundaryRing = useMemo(
    () => boundaryOuterRing(bundle.boundary),
    [bundle.boundary],
  )
  const rasterBounds = useMemo(() => toDeckBounds(bundle.bounds), [bundle.bounds])
  const rasterImage =
    scenario === 'baseline'
      ? bundle.baselineImageUrl
      : bundle.interventionImageUrl

  const top = rankOne(bundle.decision.configurations)
  const kpi = top ? toKpiView(top) : null
  const cs = coolScoreView(bundle.decision, top)

  const layers: Layer[] = useMemo(
    () =>
      buildLayers({
        tilesetUrl: null, // no Cesium without a basemap context
        boundaryRing,
        raster: { image: rasterImage, bounds: rasterBounds },
        rasterOpacity,
        trees: bundle.trees,
        modelMatrix: null, // flat — no elevation lift in fallback
      }),
    [boundaryRing, rasterImage, rasterBounds, rasterOpacity, bundle.trees],
  )

  return (
    <div style={{ position: 'absolute', inset: 0, background: '#0b0f14' }}>
      <DeckGL
        views={new MapView({ repeat: true })}
        initialViewState={{
          longitude: lon,
          latitude: lat,
          zoom: 16,
          pitch: 45,
          bearing: -18,
        }}
        controller
        layers={layers}
        style={{ width: '100%', height: '100%' }}
      />

      <section
        className="panel"
        role="region"
        aria-label="Cooling summary"
        style={{
          position: 'absolute',
          top: 'var(--s-5)',
          left: 'var(--s-5)',
          width: 320,
          maxWidth: 'calc(100vw - 2 * var(--s-5))',
          padding: 'var(--s-5)',
          zIndex: 13,
        }}
      >
        <div className="eyebrow" style={{ marginBottom: 'var(--s-2)' }}>
          ◖ COOLSPEND · Barcelona
        </div>
        <h1
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'var(--fs-md)',
            color: 'var(--ink-0)',
            margin: '0 0 var(--s-3)',
            lineHeight: 'var(--lh-snug)',
          }}
        >
          {bundle.decision.headline}
        </h1>
        <span
          className={`rc-badge ${cs.measured ? 'is-measured' : 'is-preview'}`}
          title={cs.measured ? 'Measured on Infrared UTCI' : 'Preview — placement real, cooling estimated'}
        >
          {cs.measured ? '● MEASURED' : '● PREVIEW'}
        </span>

        <div className="tile" style={{ margin: 'var(--s-4) 0' }}>
          <div style={{ fontSize: 'var(--fs-2xl)', fontFamily: 'var(--font-display)', color: 'var(--ink-0)' }} className="tnum">
            {cs.score == null ? '—' : cs.score}
            <span style={{ fontSize: 'var(--fs-sm)', color: 'var(--ink-3)' }}> /100 cooling score</span>
          </div>
          <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--ink-2)' }}>
            {kpi?.trees ?? '—'} trees · {kpi?.cooledArea ?? '—'} cooled · {kpi?.rate ?? '—'}
          </div>
        </div>

        <div className="rail-toggle" role="group" aria-label="Heatmap scenario" style={{ marginBottom: 'var(--s-3)' }}>
          <button
            type="button"
            className={`rail-toggle__btn ${scenario === 'baseline' ? 'is-active' : ''}`}
            aria-pressed={scenario === 'baseline'}
            onClick={() => setScenario('baseline')}
          >
            Baseline
          </button>
          <button
            type="button"
            className={`rail-toggle__btn ${scenario === 'intervention' ? 'is-active' : ''}`}
            aria-pressed={scenario === 'intervention'}
            onClick={() => setScenario('intervention')}
          >
            With trees
          </button>
        </div>

        <label className="rail-opacity" htmlFor="fallback-opacity">
          <span>Heatmap</span>
          <input
            id="fallback-opacity"
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={rasterOpacity}
            onChange={(e) => setRasterOpacity(Number(e.target.value))}
          />
          <span className="tnum">{Math.round(rasterOpacity * 100)}%</span>
        </label>
      </section>

      <div className="legend-dock">
        <Legend />
      </div>

      <div className="notice">
        Add a Mapbox token (and Cesium Ion token) for the photorealistic 3D city.
      </div>
    </div>
  )
}
