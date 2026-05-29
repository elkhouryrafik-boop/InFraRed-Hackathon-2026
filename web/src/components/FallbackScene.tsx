// No-Mapbox-token fallback: render deck.gl on its own canvas over a flat dark
// background (no basemap, no Cesium tiles). Overlays still fully render so the
// app NEVER white-screens (recipe spec #7).

import { useMemo, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { MapView } from '@deck.gl/core'
import type { Layer } from '@deck.gl/core'

import { Hud } from './Hud'
import { buildLayers } from '../lib/layers'
import { boundaryOuterRing, toDeckBounds } from '../lib/bundle'
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

      <Hud
        decision={bundle.decision}
        scenario={scenario}
        onScenarioChange={setScenario}
        rasterOpacity={rasterOpacity}
        onRasterOpacityChange={setRasterOpacity}
      />

      <div className="notice">
        Add a Mapbox token (and Cesium Ion token) for the photorealistic 3D city.
      </div>
    </div>
  )
}
