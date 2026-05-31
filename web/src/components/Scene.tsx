// The full map scene: Mapbox basemap + deck.gl overlay + HUD.
// Only mounted when a Mapbox token IS present (App routes otherwise to
// FallbackScene). Cesium 3D tiles degrade gracefully if that token is absent.

import 'mapbox-gl/dist/mapbox-gl.css'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Map,
  type ViewStateChangeEvent,
  type MapRef,
  type MapLayerMouseEvent,
} from 'react-map-gl'

import type { Layer, PickingInfo } from '@deck.gl/core'
import { DeckOverlay } from './DeckOverlay'
import { Hud } from './Hud'
import { TreeInspect } from './TreeInspect'
import { DrawPanel } from './DrawPanel'
import { GrowthSlider } from './GrowthSlider'
import { useAreaDraw } from './useAreaDraw'
import { canopyScale, DEFAULT_GROWTH, MAX_MATURITY_YEARS } from '../lib/growth'
import { useCesiumTileset, tilesetOpacity } from './useCesiumTileset'
import { buildLayers } from '../lib/layers'
import { boundaryOuterRing, toDeckBounds } from '../lib/bundle'
import {
  computeLiftMeters,
  fetchDemElevation,
  liftMatrix,
} from '../lib/elevation'
import type { WebBundle, UtciScenario, AppMode, CitywideScan, TreeProperties, CityPlan } from '../lib/types'
import type { LngLat } from '../lib/draw'
import { fetchCitywideScan } from '../lib/api'
import { buildCitywideLayer, buildCityPlanLayer } from '../lib/layers'

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
  /** Called with a freshly evaluated bundle from the drawing flow. */
  onBundle?: (b: WebBundle) => void
  appMode: AppMode
  setAppMode: (m: AppMode) => void
}

export function Scene({ bundle, onBundle, appMode, setAppMode }: SceneProps) {
  const [lon, lat] = bundle.decision.site_center_lonlat
  const mapRef = useRef<MapRef | null>(null)

  // Dev-only: expose the Mapbox map for debugging / automated verification.
  useEffect(() => {
    if (import.meta.env.DEV) {
      ;(window as unknown as { __map?: unknown }).__map = mapRef.current?.getMap?.() ?? null
    }
  }, [])

  const [viewState, setViewState] = useState({
    longitude: lon,
    latitude: lat,
    zoom: 16,
    pitch: 55,
    bearing: -18,
  })

  const [scenario, setScenario] = useState<UtciScenario>('intervention')
  const [selectedTree, setSelectedTree] = useState<TreeProperties | null>(null)
  // True only once the photoreal 3D tiles have ACTUALLY loaded. We must not blank
  // the Mapbox basemap merely because a tileset URL resolved — if the Google tiles
  // then fail to fetch (Ion asset / CORS / quota), the user is left with a black
  // void. Gate the empty-style swap on a real load so the basemap stays visible.
  const [tilesLoaded, setTilesLoaded] = useState(false)
  const [rasterOpacity, setRasterOpacity] = useState(0.7)
  const [credits, setCredits] = useState<string | null>(null)
  const [budgetEur, setBudgetEur] = useState(500_000)
  const [showImpervious, setShowImpervious] = useState(true)

  // Age slider: years after planting. Default = mature so the initial view
  // matches the (mature-canopy) UTCI heatmap.
  const growthParams = bundle.growth ?? DEFAULT_GROWTH
  // Default to the slowest species' maturity so the initial view shows every
  // canopy mature (matching the mature-canopy UTCI heatmap). Each tree then
  // shrinks toward its own species curve as the slider moves to younger ages.
  const [plantingYear, setPlantingYear] = useState(MAX_MATURITY_YEARS)
  const treeScale = canopyScale(plantingYear, growthParams)

  // ── Citywide (Mode 2) state.
  const [citywideScan, setCitywideScan] = useState<CitywideScan | null>(null)
  const [citywideGeojson, setCitywideGeojson] = useState<GeoJSON.FeatureCollection | null>(null)
  const [cityPlan, setCityPlan] = useState<CityPlan | null>(null)
  const [citywideLoading, setCitywideLoading] = useState(false)

  useEffect(() => {
    if (appMode !== 'citywide') return
    let cancelled = false
    setCitywideLoading(true)
    // Each source is independent — the static plan + heatmap (just files) must render
    // even when the scan API is down, so a backend hiccup never blanks Mode 2.
    fetch('/scored_grid.geojson').then(r => r.json())
      .then(g => { if (!cancelled) setCitywideGeojson(g as GeoJSON.FeatureCollection) })
      .catch(() => {})
    fetch('/citywide_plan.json').then(r => (r.ok ? r.json() : null))
      .then(p => { if (!cancelled) setCityPlan((p as CityPlan) ?? null) })
      .catch(() => {})
    fetchCitywideScan(50, 1_000_000)
      .then(s => { if (!cancelled) setCitywideScan(s) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setCitywideLoading(false) })
    return () => { cancelled = true }
  }, [appMode])

  // Zoom out to Barcelona overview when switching to citywide mode.
  useEffect(() => {
    if (appMode === 'citywide') {
      setViewState({ longitude: 2.17, latitude: 41.39, zoom: 10.5, pitch: 0, bearing: 0 })
    }
  }, [appMode])

  // ── Drawing flow (select an area anywhere, then Evaluate).
  const draw = useAreaDraw()

  const lngLatOf = (e: MapLayerMouseEvent): LngLat => [e.lngLat.lng, e.lngLat.lat]
  const onMapClick = useCallback(
    (e: MapLayerMouseEvent) => {
      if (draw.mode) draw.onMapClick(lngLatOf(e))
    },
    [draw],
  )
  const onMapMouseMove = useCallback(
    (e: MapLayerMouseEvent) => {
      if (draw.mode) draw.onMapMouseMove(lngLatOf(e))
    },
    [draw],
  )
  const onMapDblClick = useCallback(
    (e: MapLayerMouseEvent) => {
      if (draw.mode === 'polygon') {
        e.preventDefault?.()
        draw.onMapDblClick()
      }
    },
    [draw],
  )

  // Click a tree (deck.gl picking) → open the inspect panel for it.
  const onDeckClick = useCallback((info: PickingInfo) => {
    if (info.layer?.id === 'trees' && info.object) {
      const f = info.object as { properties?: TreeProperties }
      if (f.properties) setSelectedTree(f.properties)
    } else {
      setSelectedTree(null)
    }
  }, [])

  // When the user evaluates, recenter the camera on the new site.
  const handleEvaluated = useCallback(
    (b: WebBundle) => {
      draw.clear()
      setSelectedTree(null)
      onBundle?.(b)
      setPlantingYear(MAX_MATURITY_YEARS) // reset to mature (all species)
      const c = b.decision.site_center_lonlat
      if (c) setViewState((v) => ({ ...v, longitude: c[0], latitude: c[1] }))
    },
    [draw, onBundle],
  )

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
  // Swap to the empty style only once the photoreal tiles have ACTUALLY loaded;
  // until then keep a readable basemap so a Google-tile failure never leaves a void.
  // Satellite imagery is the reliable hero basemap: real Barcelona aerial with no
  // 3D mesh to occlude the UTCI heatmap or the tree canopy disks. (Photoreal mesh
  // plumbing is retained but inactive — see tilesetUrl below — and can return as a
  // separately-composited toggle once the mask/occlusion is solved.)
  const photorealActive = tilesLoaded && tilesOpacity > 0.5
  const mapStyle = photorealActive
    ? EMPTY_MAP_STYLE
    : 'mapbox://styles/mapbox/satellite-streets-v12'

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
        // Photoreal mesh disabled (occludes the analysis); satellite basemap instead.
        tilesetUrl: null,
        boundaryRing,
        raster: { image: rasterImage, bounds: rasterBounds },
        rasterOpacity,
        trees: bundle.trees,
        treeScale,
        growthYear: plantingYear,
        impervious: bundle.impervious,
        showImpervious,
        // No elevation lift without the ellipsoidal mesh — overlays sit flat.
        modelMatrix: null,
        onTilesetLoad: (tileset) => {
          setTilesLoaded(true)
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
      treeScale,
      plantingYear,
      bundle.impervious,
      showImpervious,
      modelMatrix,
    ],
  )

  // Citywide heatmap layer (Mode 2).
  const citywideLayer = useMemo(
    () => buildCitywideLayer({ data: citywideGeojson, opacity: 0.55 }),
    [citywideGeojson],
  )
  // €1M plan: funded-site markers on top of the heatmap.
  const cityPlanLayer = useMemo(
    () => buildCityPlanLayer(cityPlan?.allocated_cells ?? null),
    [cityPlan],
  )

  // Site layers + live draw-preview layers on top.
  const allLayers = useMemo(
    () => {
      const result = [...layers]
      if (appMode === 'citywide' && citywideLayer) {
        result.unshift(citywideLayer)
      }
      if (appMode === 'citywide' && cityPlanLayer) {
        result.push(cityPlanLayer)
      }
      if (appMode === 'draw') {
        result.push(...draw.drawLayers)
      }
      return result
    },
    [layers, draw.drawLayers, appMode, citywideLayer, cityPlanLayer],
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
        onClick={appMode === 'draw' ? onMapClick : undefined}
        onMouseMove={appMode === 'draw' ? onMapMouseMove : undefined}
        onDblClick={appMode === 'draw' ? onMapDblClick : undefined}
        dragPan={appMode === 'citywide' || !draw.drawing}
        doubleClickZoom={appMode === 'citywide' || draw.mode !== 'polygon'}
        cursor={appMode === 'draw' && draw.mode ? 'crosshair' : undefined}
        mapboxAccessToken={MAPBOX_TOKEN}
        mapStyle={mapStyle}
        style={{ width: '100%', height: '100%' }}
        antialias
      >
        <DeckOverlay layers={allLayers} onClick={onDeckClick} />
      </Map>

      <TreeInspect tree={selectedTree} onClose={() => setSelectedTree(null)} />

      {appMode !== 'citywide' && (
        <Hud
          decision={bundle.decision}
          scenario={scenario}
          onScenarioChange={setScenario}
          rasterOpacity={rasterOpacity}
          onRasterOpacityChange={setRasterOpacity}
        />
      )}

      <DrawPanel
        mode={draw.mode}
        setMode={draw.setMode}
        clear={draw.clear}
        ring={draw.ring}
        area={draw.area}
        status={draw.status}
        budgetEur={budgetEur}
        setBudgetEur={setBudgetEur}
        onEvaluated={handleEvaluated}
        appMode={appMode}
        setAppMode={setAppMode}
      />

      {appMode === 'citywide' && citywideLoading && !citywideScan && (
        <div className="citywide-bar">
          <span className="citywide-bar__title">Scanning Barcelona…</span>
        </div>
      )}

      {appMode === 'citywide' && citywideScan && (
        <div className="citywide-bar">
          <span className="citywide-bar__title">
            {citywideScan.total_cells} cells · top {citywideScan.cells.length} ranked
          </span>
          <div className="citywide-bar__top">
            {citywideScan.cells.slice(0, 5).map((c) => (
              <span key={c.cell_id} className="citywide-bar__chip" title={`${c.district} · ${c.barri}`}>
                #{c.rank} {c.cell_id.replace('_', ' ')} · {Math.round(c.mean_lst_celsius)}°C ·{' '}
                {Math.round(c.composite_score_B * 100)}%
              </span>
            ))}
          </div>
        </div>
      )}

      {appMode === 'citywide' && cityPlan && (
        <div className="city-plan">
          <div className="city-plan__title">€{(cityPlan.budget_eur / 1e6).toFixed(1)}M across {cityPlan.allocated_count} sites</div>
          <div className="city-plan__kpis">
            <div className="city-plan__kpi"><strong>{cityPlan.total_trees}</strong><span>trees</span></div>
            <div className="city-plan__kpi"><strong>{cityPlan.total_people_served ? cityPlan.total_people_served.toLocaleString() : '—'}</strong><span>people served</span></div>
            <div className="city-plan__kpi"><strong>{Math.round(cityPlan.total_canopy_m2).toLocaleString()} m²</strong><span>new canopy</span></div>
            <div className="city-plan__kpi"><strong>€{Math.round(cityPlan.total_allocated_eur / 1000)}k</strong><span>allocated</span></div>
          </div>
          <div className="city-plan__sites">
            {cityPlan.allocated_cells.map((s) => (
              <div className="city-plan__site" key={s.cell_id}>
                <span className="city-plan__site-name">{s.district}{s.partial ? ' ·partial' : ''}</span>
                <span className="city-plan__site-stat">
                  {s.tree_count} trees · {s.people_served ? s.people_served.toLocaleString() : '—'} ppl · {Math.round(s.mean_lst_celsius)}°C
                </span>
              </div>
            ))}
          </div>
          <div className="city-plan__note">Hottest, most-sealed cells (Landsat × Sentinel); ≥500 m apart; ≥0.5 ha cooled within a 300 m walk = people served (Padró).</div>
        </div>
      )}

      {appMode === 'draw' && bundle.trees && bundle.trees.features.length > 0 && (
        <GrowthSlider year={plantingYear} setYear={setPlantingYear} params={growthParams} />
      )}

      {appMode === 'draw' && (bundle.impervious?.available || bundle.canopy) && (
        <div className="depave-chip">
          {bundle.impervious?.available && (
            <>
              <label className="depave-chip__toggle">
                <input
                  type="checkbox"
                  checked={showImpervious}
                  onChange={(e) => setShowImpervious(e.target.checked)}
                />
                <span className="depave-chip__swatch" /> Impervious pavement
              </label>
              <div className="depave-chip__stat">
                <strong>
                  {Math.round(bundle.impervious.impervious_m2).toLocaleString()} m²
                </strong>{' '}
                depaveable
                <span className="depave-chip__frac">
                  {Math.round(bundle.impervious.impervious_fraction * 100)}% of site
                </span>
              </div>
              {bundle.impervious.depaved_cooled_m2 != null &&
                bundle.impervious.depaved_cooled_m2 > 0 && (
                  <div className="depave-chip__cooled">
                    {Math.round(bundle.impervious.depaved_cooled_m2).toLocaleString()} m² shaded
                    by proposed canopy
                  </div>
                )}
            </>
          )}

          {/* #1 canopy cover vs 30-40% target */}
          {bundle.canopy && (
            <div className="depave-chip__metric">
              <span className="depave-chip__metric-label">Canopy cover</span>
              <strong className={bundle.canopy.in_band ? 'is-ok' : 'is-off'}>
                {Math.round(bundle.canopy.cover_fraction * 100)}%
              </strong>
              <span className="depave-chip__target">
                target {Math.round(bundle.canopy.target_min * 100)}–
                {Math.round(bundle.canopy.target_max * 100)}%
              </span>
            </div>
          )}

          {/* #2 permeable fraction vs 40-50% target, + potential if depaved */}
          {bundle.impervious?.available && (
            <div className="depave-chip__metric">
              <span className="depave-chip__metric-label">Permeable</span>
              <strong
                className={
                  bundle.impervious.permeable_fraction >= bundle.impervious.permeable_target_min
                    ? 'is-ok'
                    : 'is-off'
                }
              >
                {Math.round(bundle.impervious.permeable_fraction * 100)}%
              </strong>
              <span className="depave-chip__target">
                target {Math.round(bundle.impervious.permeable_target_min * 100)}–
                {Math.round(bundle.impervious.permeable_target_max * 100)}%
                {bundle.impervious.permeable_fraction_if_depaved != null &&
                  ` · ${Math.round(bundle.impervious.permeable_fraction_if_depaved * 100)}% if depaved`}
              </span>
            </div>
          )}
        </div>
      )}

      {credits && <div className="attribution">{credits}</div>}
    </div>
  )
}
