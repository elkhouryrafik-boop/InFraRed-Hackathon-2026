// The full map scene: Mapbox basemap + deck.gl overlay + HUD.
// Only mounted when a Mapbox token IS present (App routes otherwise to
// FallbackScene). Cesium 3D tiles degrade gracefully if that token is absent.

import 'mapbox-gl/dist/mapbox-gl.css'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Map, type ViewStateChangeEvent, type MapRef } from 'react-map-gl'

import type { Layer } from '@deck.gl/core'
import { DeckOverlay } from './DeckOverlay'
import { Hud } from './Hud'
import { useCesiumTileset, tilesetOpacity } from './useCesiumTileset'
import { buildLayers } from '../lib/layers'
import { boundaryOuterRing, toDeckBounds } from '../lib/bundle'
import {
  computeLiftMeters,
  fetchDemElevation,
  liftMatrix,
} from '../lib/elevation'
import type { WebBundle, UtciScenario } from '../lib/types'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string

// A neutral, empty Mapbox style: a single dark background layer, no streets,
// no labels, no tiles. Used as the basemap once the Google photoreal 3D mesh is
// active so nothing competes with the photogrammetry. Inline = zero network.
const EMPTY_MAP_STYLE = {
  version: 8 as const,
  name: 'coolspend-empty',
  sources: {},
  // Glyphs kept so any future text layer wouldn't crash; harmless when unused.
  glyphs: 'mapbox://fonts/mapbox/{fontstack}/{range}.pbf',
  layers: [
    {
      id: 'bg',
      type: 'background' as const,
      paint: { 'background-color': '#0b0f14' },
    },
  ],
}

interface SceneProps {
  bundle: WebBundle
}

export function Scene({ bundle }: SceneProps) {
  const [lon, lat] = bundle.decision.site_center_lonlat
  const mapRef = useRef<MapRef | null>(null)

  const [viewState, setViewState] = useState({
    longitude: lon,
    latitude: lat,
    zoom: 16,
    pitch: 55,
    bearing: -18,
  })

  const [scenario, setScenario] = useState<UtciScenario>('intervention')
  const [rasterOpacity, setRasterOpacity] = useState(0.7)
  const [credits, setCredits] = useState<string | null>(null)

  // ── Elevation lift: sample DEM once at site centre, build a modelMatrix.
  const [modelMatrix, setModelMatrix] = useState<number[] | null>(null)
  useEffect(() => {
    let cancelled = false
    fetchDemElevation(lon, lat).then((ortho) => {
      if (cancelled) return
      const ground = ortho ?? 12 // Eixample ground ~12 m AMSL fallback
      setModelMatrix(liftMatrix(computeLiftMeters(ground)))
    })
    return () => {
      cancelled = true
    }
  }, [lon, lat])

  // ── Cesium photogrammetry (latched on zoom).
  const cesium = useCesiumTileset(viewState.zoom)
  const tilesOpacity = tilesetOpacity(viewState.zoom)

  // ── Basemap switch (FIX: kill the double-map clash).
  // When the Google photoreal 3D mesh is the dominant layer, the OSM-style
  // streets/labels of the Mapbox "standard" basemap clash with the
  // photogrammetry (two maps overlaid). So once the tileset is active we drop
  // Mapbox to a neutral *empty* style — just a dark canvas behind the mesh — so
  // the photoreal city is the only "map" the user perceives. Until then (no
  // token, or zoomed out before tiles fade in) we keep the readable streets
  // basemap so the app never looks broken.
  const photorealActive = !!cesium.url && tilesOpacity > 0.5
  const mapStyle = photorealActive
    ? EMPTY_MAP_STYLE
    : 'mapbox://styles/mapbox/standard'

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
        // Only feed the tileset URL once it's resolved AND we're zoomed enough
        // to want it; opacity ramp keeps the fade smooth.
        tilesetUrl: cesium.url && tilesOpacity > 0 ? cesium.url : null,
        boundaryRing,
        raster: { image: rasterImage, bounds: rasterBounds },
        rasterOpacity,
        trees: bundle.trees,
        modelMatrix,
        onTilesetLoad: (tileset) => {
          const t = tileset as {
            credits?: { attributions?: { html?: string }[] }
          }
          const html = t?.credits?.attributions
            ?.map((a) => a.html)
            .filter(Boolean)
            .join(' · ')
          if (html) {
            const div = document.createElement('div')
            div.innerHTML = html
            setCredits(div.textContent || 'Google')
          }
        },
      }),
    [
      cesium.url,
      tilesOpacity,
      boundaryRing,
      rasterImage,
      rasterBounds,
      rasterOpacity,
      bundle.trees,
      modelMatrix,
    ],
  )

  const onMove = useCallback((e: ViewStateChangeEvent) => {
    setViewState((v) => ({ ...v, ...e.viewState }))
  }, [])

  // Hide Mapbox's own 3D objects when Google tiles are on (recipe §7:
  // avoid z-fighting between Mapbox extrusions and the photogrammetry mesh).
  // Only relevant on the "standard" style (the empty style has no basemap
  // config and no 3D buildings at all). Re-runs when the style swaps.
  useEffect(() => {
    const map = mapRef.current?.getMap?.()
    if (!map) return
    const apply = () => {
      try {
        if (cesium.url && typeof mapStyle === 'string') {
          ;(map as unknown as {
            setConfigProperty: (s: string, p: string, v: unknown) => void
          }).setConfigProperty('basemap', 'show3dObjects', false)
        }
      } catch {
        /* style not loaded yet / non-standard style */
      }
    }
    if (map.isStyleLoaded?.()) apply()
    else map.once?.('style.load', apply)
  }, [cesium.url, mapStyle])

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <Map
        ref={mapRef}
        reuseMaps
        {...viewState}
        onMove={onMove}
        mapboxAccessToken={MAPBOX_TOKEN}
        mapStyle={mapStyle}
        style={{ width: '100%', height: '100%' }}
        antialias
      >
        <DeckOverlay layers={layers} />
      </Map>

      <Hud
        decision={bundle.decision}
        scenario={scenario}
        onScenarioChange={setScenario}
        rasterOpacity={rasterOpacity}
        onRasterOpacityChange={setRasterOpacity}
      />

      {cesium.hasToken && cesium.url && tilesOpacity < 1 && (
        <div className="notice">Zoom in for photorealistic 3D…</div>
      )}

      {!cesium.hasToken && (
        <div className="notice">Add Cesium Ion token for photorealistic 3D.</div>
      )}

      {credits && <div className="attribution">{credits}</div>}
    </div>
  )
}
