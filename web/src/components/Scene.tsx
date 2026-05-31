// The full map scene: Mapbox basemap + deck.gl overlay + phase-gated UI.
// Only mounted when a Mapbox token IS present (App routes otherwise to
// FallbackScene). Cesium 3D tiles degrade gracefully if that token is absent.
//
// Redesign Spec v4: this component owns the camera authority (§5) and the phase
// machine's contextual surfaces (§3) — at most ONE dense surface per screen.

import 'mapbox-gl/dist/mapbox-gl.css'
import './Scene.css'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Map,
  Layer as MapLayer,
  type ViewStateChangeEvent,
  type MapRef,
  type MapLayerMouseEvent,
} from 'react-map-gl'

import type { Layer, PickingInfo } from '@deck.gl/core'
import { DeckOverlay } from './DeckOverlay'
import { TreeInspect } from './TreeInspect'
import { ActionRail } from './ActionRail'
import { ModeSwitch } from './ModeSwitch'
import { ResultCard } from './ResultCard'
import { CitywidePanel } from './CitywidePanel'
import { Onboarding, type OnboardingIntent } from './Onboarding'
import { Legend } from './Legend'
import { useAreaDraw } from './useAreaDraw'
import { canopyScale, DEFAULT_GROWTH, MAX_MATURITY_YEARS } from '../lib/growth'
import { useCesiumTileset, tilesetOpacity } from './useCesiumTileset'
import { buildLayers } from '../lib/layers'
import { boundaryOuterRing, toDeckBounds } from '../lib/bundle'
import type {
  WebBundle,
  UtciScenario,
  TreeProperties,
  CityPlan,
  CityPlanSite,
  Phase,
  CameraMode,
} from '../lib/types'
import type { LngLat } from '../lib/draw'
import { buildCitywideLayer, buildCityPlanLayer, buildCityTreesLayer } from '../lib/layers'
import { speciesDims, foliageColor } from '../lib/species'
import { buildTreeSpheres, type TreePoint } from '../lib/treeMesh'
import { useReducedMotion } from '../lib/useReducedMotion'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string

// Camera presets.
const SITE_ZOOM = 16.5
const SITE_PITCH = 50
const SITE_BEARING = -18
const CITY_VIEW = { longitude: 2.17, latitude: 41.39, zoom: 10.5, pitch: 0, bearing: 0 }
const FLYTO_DURATION = 1200

const EMPTY_MAP_STYLE = {
  version: 8 as const,
  name: 'coolspend-empty',
  sources: {},
  glyphs: 'mapbox://fonts/mapbox/{fontstack}/{range}.pbf',
  layers: [{ id: 'bg', type: 'background' as const, paint: { 'background-color': '#0b0f14' } }],
}

interface SceneProps {
  bundle: WebBundle
  onBundle?: (b: WebBundle) => void
  phase: Phase
  setPhase: (p: Phase) => void
  seenKey: string
}

export function Scene({ bundle, onBundle, phase, setPhase, seenKey }: SceneProps) {
  const [lon, lat] = bundle.decision.site_center_lonlat
  const mapRef = useRef<MapRef | null>(null)
  const reducedMotion = useReducedMotion()
  // 3D view toggle: false = clean 2D satellite (analysis), true = cinematic 3D
  // (light basemap + extruded buildings + 3D tree spheres, Infrared.city style).
  const [view3d, setView3d] = useState(false)

  useEffect(() => {
    if (import.meta.env.DEV) {
      ;(window as unknown as { __map?: unknown }).__map = mapRef.current?.getMap?.() ?? null
    }
  }, [])

  // ── Camera authority (Redesign Spec §5). viewState is the result of onMove
  // ONLY; flyTo/jumpTo is the authority for programmatic moves. cameraMode flips
  // to 'user' on the first user gesture and cancels any in-flight scripted fly.
  const [viewState, setViewState] = useState({
    longitude: lon,
    latitude: lat,
    zoom: phase === 'citywide' ? CITY_VIEW.zoom : SITE_ZOOM,
    pitch: phase === 'citywide' ? 0 : SITE_PITCH,
    bearing: phase === 'citywide' ? 0 : SITE_BEARING,
  })
  const cameraModeRef = useRef<CameraMode>('auto')
  // Declared early: flyToCity / fundedCentroids (below) read it to frame the 7 sites.
  const [cityPlan, setCityPlan] = useState<CityPlan | null>(null)

  const flyToSite = useCallback(
    (clon: number, clat: number, opts?: { zoom?: number; pitch?: number; bearing?: number }) => {
      const map = mapRef.current?.getMap()
      const center: [number, number] = [clon, clat]
      const zoom = opts?.zoom ?? SITE_ZOOM
      const pitch = opts?.pitch ?? SITE_PITCH
      const bearing = opts?.bearing ?? SITE_BEARING
      if (!map) {
        // Map not ready yet — seed initial viewState so we open framed.
        setViewState({ longitude: clon, latitude: clat, zoom, pitch, bearing })
        return
      }
      if (reducedMotion) {
        cameraModeRef.current = 'auto'
        map.jumpTo({ center, zoom, pitch, bearing }) // D1: instant cut, land at focal point
      } else {
        cameraModeRef.current = 'auto'
        map.flyTo({ center, zoom, pitch, bearing, duration: FLYTO_DURATION, curve: 1.42, speed: 0.9 })
      }
    },
    [reducedMotion],
  )

  // Funded-site centroids, for framing the citywide view tightly on the 7 sites
  // (not all-Barcelona-plus-sea, where they were lost specks).
  const fundedCentroids = useMemo(
    () =>
      (cityPlan?.allocated_cells ?? [])
        .map((c) => c.centroid_lonlat)
        .filter((p): p is [number, number] => Array.isArray(p)),
    [cityPlan],
  )

  const flyToCity = useCallback(() => {
    const map = mapRef.current?.getMap()
    // Fit the bounding box of the 7 funded sites so they fill the frame.
    if (map && fundedCentroids.length > 0) {
      let w = 180, s = 90, e = -180, n = -90
      for (const [clon, clat] of fundedCentroids) {
        w = Math.min(w, clon); e = Math.max(e, clon)
        s = Math.min(s, clat); n = Math.max(n, clat)
      }
      cameraModeRef.current = 'auto'
      map.fitBounds([[w, s], [e, n]], {
        padding: { top: 110, bottom: 90, left: 380, right: 90 }, // left pad clears the panel
        maxZoom: 13.5,
        pitch: 0,
        bearing: 0,
        duration: reducedMotion ? 0 : FLYTO_DURATION,
      })
      return
    }
    if (!map) {
      setViewState((v) => ({ ...v, ...CITY_VIEW }))
      return
    }
    cameraModeRef.current = 'auto'
    const opts = { center: [CITY_VIEW.longitude, CITY_VIEW.latitude] as [number, number], zoom: CITY_VIEW.zoom, pitch: 0, bearing: 0 }
    if (reducedMotion) map.jumpTo(opts)
    else map.flyTo({ ...opts, duration: FLYTO_DURATION })
  }, [reducedMotion, fundedCentroids])

  const [scenario, setScenario] = useState<UtciScenario>('intervention')
  const [selectedTree, setSelectedTree] = useState<TreeProperties | null>(null)
  const [tilesLoaded, setTilesLoaded] = useState(false)
  const [rasterOpacity, setRasterOpacity] = useState(0.7)
  const [credits, setCredits] = useState<string | null>(null)
  const [budgetEur, setBudgetEur] = useState(500_000)
  const [evaluating, setEvaluating] = useState(false)
  // Vignette dim during scripted flights + intro (§5).
  const [vignette, setVignette] = useState(0.45)

  const growthParams = bundle.growth ?? DEFAULT_GROWTH
  const [plantingYear, setPlantingYear] = useState(MAX_MATURITY_YEARS)
  const treeScale = canopyScale(plantingYear, growthParams)

  // ── Citywide state. (cityPlan is declared earlier — used by flyToCity.)
  const [citywideGeojson, setCitywideGeojson] = useState<GeoJSON.FeatureCollection | null>(null)
  const [citywideLoading, setCitywideLoading] = useState(false)
  const [hoverSiteIndex, setHoverSiteIndex] = useState<number | null>(null)
  const [selectedSiteIndex, setSelectedSiteIndex] = useState<number | null>(null)

  // The citywide plan is needed by the intro too (real measured payoff numbers),
  // so fetch it once on mount, not only when entering citywide.
  useEffect(() => {
    let cancelled = false
    // no-store: the plan is regenerated server-side; never serve a stale cached
    // copy (that showed OLD numbers after a regen).
    fetch('/citywide_plan.json', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((p) => {
        if (!cancelled) setCityPlan((p as CityPlan) ?? null)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  // The scored grid (heatmap) loads when the citywide phase is entered. Each
  // source is independent — the static plan + heatmap (just files) must render
  // even if a backend is down, so a hiccup never blanks Mode 2.
  useEffect(() => {
    if (phase !== 'citywide' || citywideGeojson) return
    let cancelled = false
    setCitywideLoading(true)
    fetch('/scored_grid.geojson', { cache: 'no-store' })
      .then((r) => r.json())
      .then((g) => {
        if (!cancelled) setCitywideGeojson(g as GeoJSON.FeatureCollection)
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setCitywideLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [phase, citywideGeojson])

  // ── Drawing flow.
  const draw = useAreaDraw()
  const isDrawPhase = phase === 'design' || phase === 'result'

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

  const onDeckClick = useCallback(
    (info: PickingInfo) => {
      // While a draw tool is armed, the click belongs to the polygon — never let
      // a tree pick steal it (that blocked placing a polygon over the showcase).
      if (draw.mode) return
      const layerId = info.layer?.id
      // Build a lite TreeProperties from a species name (for layers that only
      // store species+position: the citywide trees + all 3D spheres).
      const liteFromSpecies = (species: string, cell?: string): TreeProperties => {
        const dims = speciesDims(species)
        const [r, g, b] = foliageColor(species)
        const site = cell ? cityPlan?.allocated_cells.find((c) => c.cell_id === cell) : undefined
        return {
          kind: 'proposed',
          species,
          crown_diameter_m: dims.crown_m,
          height_m: dims.height_m,
          crown_area_m2: Math.round(Math.PI * (dims.crown_m / 2) ** 2),
          color: [r, g, b],
          ecology: {
            notes: site
              ? `Part of the €1M plan — ${site.district} · ${site.barri}. Per-tree ecology is in the single-site view.`
              : 'Proposed planting. Per-tree ecology is in the single-site view.',
          },
        } as TreeProperties
      }

      if (layerId === 'trees' && info.object) {
        // 2D single-site icons carry full ecology.
        const f = info.object as { properties?: TreeProperties }
        if (f.properties) setSelectedTree(f.properties)
      } else if ((layerId === 'trees-3d' || layerId === 'city-trees-3d' || layerId === 'city-trees') && info.object) {
        // 3D spheres + 2D citywide canopies → species profile (lite).
        const o = info.object as { species: string; cell?: string }
        setSelectedTree(liteFromSpecies(o.species, o.cell))
      } else if (layerId === 'city-plan-sites' && info.object) {
        // Click a funded pin → drill into that site.
        const o = info.object as { cell_id?: string }
        const sorted = cityPlan ? [...cityPlan.allocated_cells].sort((a, b) => a.rank - b.rank) : []
        const idx = sorted.findIndex((x) => x.cell_id === o.cell_id)
        if (idx >= 0) {
          setSelectedSiteIndex(idx)
          const ctr = sorted[idx].centroid_lonlat
          flyToSite(ctr[0], ctr[1], { zoom: 16.8, pitch: 45 })
        }
      } else {
        setSelectedTree(null)
      }
    },
    [cityPlan, flyToSite, draw.mode],
  )

  // ── Evaluate → recenter via the authoritative flyTo (the camera-bug fix, §5).
  const handleEvaluated = useCallback(
    (b: WebBundle) => {
      draw.clear()
      setSelectedTree(null)
      onBundle?.(b)
      setPlantingYear(MAX_MATURITY_YEARS)
      setPhase('result')
      const c = b.decision.site_center_lonlat
      if (c) flyToSite(c[0], c[1])
      // The "money moment": show the BEFORE heat, then cross-fade to the cooled
      // field once the camera lands (deck tweens the stacked drapes). Instant
      // under reduced-motion.
      if (reducedMotion) {
        setScenario('intervention')
      } else {
        setScenario('baseline')
        window.setTimeout(() => setScenario('intervention'), FLYTO_DURATION + 200)
      }
    },
    [draw, onBundle, setPhase, flyToSite, reducedMotion],
  )

  // Elevation lift is inactive (photoreal mesh disabled; satellite basemap —
  // overlays sit flat), so no modelMatrix is computed here.

  const cesium = useCesiumTileset(viewState.zoom)
  const tilesOpacity = tilesetOpacity(viewState.zoom)

  const photorealActive = tilesLoaded && tilesOpacity > 0.5
  // 2D = clean empty satellite (analysis). 3D = light basemap (white buildings
  // extrude cleanly on it) for the cinematic view.
  const mapStyle = view3d
    ? 'mapbox://styles/mapbox/light-v11'
    : 'mapbox://styles/mapbox/satellite-v9'

  const boundaryRing = useMemo(() => boundaryOuterRing(bundle.boundary), [bundle.boundary])
  const rasterBounds = useMemo(() => toDeckBounds(bundle.bounds), [bundle.bounds])

  // Cross-fade target: 0 = baseline, 1 = with-trees. Deck tweens the two stacked
  // drapes' opacities, so the Evaluate reveal + the toggle dissolve smoothly.
  const rasterMix = scenario === 'baseline' ? 0 : 1

  const layers: Layer[] = useMemo(
    () =>
      buildLayers({
        tilesetUrl: null,
        boundaryRing,
        rasterBaseline: bundle.baselineImageUrl
          ? { image: bundle.baselineImageUrl, bounds: rasterBounds }
          : null,
        rasterIntervention: bundle.interventionImageUrl
          ? { image: bundle.interventionImageUrl, bounds: rasterBounds }
          : null,
        rasterMix,
        rasterOpacity,
        trees: bundle.trees,
        treeScale,
        growthYear: plantingYear,
        impervious: bundle.impervious,
        showImpervious: false,
        modelMatrix: null,
        animateReveal: !reducedMotion && (phase === 'result' || phase === 'intro'),
        onTilesetLoad: (tileset) => {
          setTilesLoaded(true)
          const t = tileset as { credits?: { attributions?: { html?: string }[] } }
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
      boundaryRing,
      rasterMix,
      bundle.baselineImageUrl,
      bundle.interventionImageUrl,
      rasterBounds,
      rasterOpacity,
      bundle.trees,
      bundle.impervious,
      treeScale,
      plantingYear,
      reducedMotion,
      phase,
    ],
  )

  // Funded cell-ids for the citywide focus-vs-context dimming (§4.9-5).
  const fundedCellIds = useMemo(
    () => (cityPlan ? new Set(cityPlan.allocated_cells.map((c) => c.cell_id)) : null),
    [cityPlan],
  )

  const citywideLayer = useMemo(
    () => buildCitywideLayer({ data: citywideGeojson, opacity: 0.42, fundedCellIds }),
    [citywideGeojson, fundedCellIds],
  )

  const sortedSites = useMemo(
    () => (cityPlan ? [...cityPlan.allocated_cells].sort((a, b) => a.rank - b.rank) : []),
    [cityPlan],
  )
  const cityPlanLayer = useMemo(
    () => buildCityPlanLayer(sortedSites, hoverSiteIndex ?? selectedSiteIndex),
    [sortedSites, hoverSiteIndex, selectedSiteIndex],
  )
  // The 99 actual placed trees across the 7 funded sites (real canopy disks, not
  // pins) — so the citywide view SHOWS the planting. Selected site's trees stay
  // full-strength; the rest fade to context.
  const selectedCellId = useMemo(
    () => (selectedSiteIndex != null ? sortedSites[selectedSiteIndex]?.cell_id ?? null : null),
    [selectedSiteIndex, sortedSites],
  )
  const cityTreeLayers = useMemo(
    () => buildCityTreesLayer(sortedSites, { selectedCellId }),
    [sortedSites, selectedCellId],
  )

  // 3D tree-sphere points (used only in view3d).
  const siteTreePoints = useMemo<TreePoint[]>(
    () =>
      (bundle.trees?.features ?? [])
        .filter((f) => f.properties.kind === 'proposed')
        .map((f) => ({
          lon: f.geometry.coordinates[0],
          lat: f.geometry.coordinates[1],
          crown_m: f.properties.crown_diameter_m || 6,
          species: f.properties.species,
        })),
    [bundle.trees],
  )
  const cityTreePoints = useMemo<TreePoint[]>(
    () =>
      sortedSites.flatMap((s) =>
        (s.trees_lonlat ?? []).map((t) => ({
          lon: t.lon,
          lat: t.lat,
          crown_m: speciesDims(t.species).crown_m,
          species: t.species,
          cell: s.cell_id,
        })),
      ),
    [sortedSites],
  )

  const allLayers = useMemo(() => {
    if (phase === 'citywide') {
      // Citywide is its OWN scene: heat grid + funded-site pins + the placed trees.
      const result: Layer[] = []
      if (citywideLayer) result.push(citywideLayer)
      if (cityPlanLayer) result.push(cityPlanLayer)
      if (view3d) {
        const s = buildTreeSpheres('city-trees-3d', cityTreePoints, { selectedCellId })
        if (s) result.push(s)
      } else {
        result.push(...cityTreeLayers) // 2D canopy icons
      }
      return result
    }
    // Design phase = DRAWING. Show ONLY the user's polygon over the satellite
    // basemap. The bundle's climate raster + showcase trees belong to the DEFAULT
    // showcase site, not the polygon being drawn — rendering them here made the
    // heat field look misaligned with the polygon (it sat at a different block).
    // The real, aligned field appears after Evaluate (result phase).
    if (phase === 'design') {
      return [...draw.drawLayers]
    }
    // Single-site: drop the 2D icon 'trees' in 3D and add sphere trees instead.
    const result = view3d ? layers.filter((l) => l.id !== 'trees') : [...layers]
    if (view3d) {
      const s = buildTreeSpheres('trees-3d', siteTreePoints)
      if (s) result.push(s)
    }
    if (isDrawPhase) {
      result.push(...draw.drawLayers)
    }
    return result
  }, [layers, draw.drawLayers, phase, isDrawPhase, citywideLayer, cityPlanLayer, cityTreeLayers, view3d, cityTreePoints, siteTreePoints, selectedCellId])

  // PERF: the map is uncontrolled (initialViewState), so it pans natively on the
  // GPU. We must NOT setViewState on every frame — that re-renders the whole
  // Scene (heavy panels) per frame and makes the pan choppy. onMove only flips
  // camera authority on the first user gesture; the zoom-dependent state syncs
  // once the gesture ends (onMoveEnd).
  const onMove = useCallback((e: ViewStateChangeEvent) => {
    const ev = e as ViewStateChangeEvent & { originalEvent?: unknown }
    if (ev.originalEvent && cameraModeRef.current !== 'user') {
      cameraModeRef.current = 'user'
      mapRef.current?.getMap()?.stop()
    }
  }, [])
  const onMoveEnd = useCallback((e: ViewStateChangeEvent) => {
    setViewState((v) => ({ ...v, ...e.viewState }))
  }, [])

  // ── Camera reactions to phase changes (the bug fix lives here).
  // On entering result, the evaluate handler already flew. On entering design
  // from the intro, frame the site. On citywide, pull to the overview.
  const prevPhaseRef = useRef<Phase>(phase)
  useEffect(() => {
    const prev = prevPhaseRef.current
    prevPhaseRef.current = phase
    if (phase === 'citywide') {
      flyToCity()
    } else if (phase === 'design' && (prev === 'intro' || prev === 'citywide')) {
      // Design is for DRAWING — a flat, top-down view is far easier to place a
      // polygon on than the cinematic 50° tilt (which fought the user's draw).
      flyToSite(lon, lat, { zoom: 16.3, pitch: 0, bearing: 0 })
    }
    // 'result' is driven by handleEvaluated's flyTo.
  }, [phase, lon, lat, flyToSite, flyToCity])

  // Re-fit the citywide frame once the plan's centroids arrive (boot race: we
  // may land in citywide before /citywide_plan.json resolves). Only while the
  // camera is still scripted — never yank a view the user grabbed.
  const didFitCityRef = useRef(false)
  useEffect(() => {
    if (phase === 'citywide' && fundedCentroids.length > 0 && !didFitCityRef.current) {
      if (cameraModeRef.current === 'auto') flyToCity()
      didFitCityRef.current = true
    }
    if (phase !== 'citywide') didFitCityRef.current = false
  }, [phase, fundedCentroids.length, flyToCity])

  // On map-ready, frame the current phase. This guarantees the initial framing
  // even if the mount-time effects ran before the map ref existed — so the app
  // always opens framed on the site, never zoomed-out over all Barcelona (#1 bug).
  const onMapLoad = useCallback(() => {
    if (cameraModeRef.current === 'user') return
    if (phase === 'citywide') flyToCity()
    else if (phase === 'design') flyToSite(lon, lat, { zoom: 16.3, pitch: 0, bearing: 0 })
    else if (phase !== 'intro') flyToSite(lon, lat)
    // intro framing is driven by the Onboarding's first intent.
  }, [phase, lon, lat, flyToCity, flyToSite])

  // Vignette choreography: dim during the intro + briefly on a scripted fly (§5).
  useEffect(() => {
    if (phase === 'intro') {
      setVignette(0.7)
      return
    }
    if (reducedMotion) {
      setVignette(0.45)
      return
    }
    setVignette(0.8)
    const t = setTimeout(() => setVignette(0.45), FLYTO_DURATION)
    return () => clearTimeout(t)
  }, [phase, bundle.decision.site_center_lonlat, reducedMotion])

  // Hide Mapbox's own 3D objects when Google tiles are on.
  useEffect(() => {
    const map = mapRef.current?.getMap?.()
    if (!map) return
    const apply = () => {
      try {
        if (cesium.url && typeof mapStyle === 'string') {
          ;(map as unknown as { setConfigProperty: (s: string, p: string, v: unknown) => void }).setConfigProperty(
            'basemap',
            'show3dObjects',
            false,
          )
        }
      } catch {
        /* style not loaded / non-standard style */
      }
    }
    if (map.isStyleLoaded?.()) apply()
    else map.once?.('style.load', apply)
  }, [cesium.url, mapStyle])

  // ── Onboarding intent → drive the real map (camera framing + scenario).
  const onOnboardingIntent = useCallback(
    (intent: OnboardingIntent) => {
      setScenario(intent.intervention ? 'intervention' : 'baseline')
      if (intent.framing === 'overview') {
        flyToCity()
        setVignette(0.55)
      } else {
        flyToSite(lon, lat)
        setVignette(0.7)
      }
    },
    [lon, lat, flyToCity, flyToSite],
  )

  const finishIntro = useCallback(() => {
    try {
      localStorage.setItem(seenKey, '1')
    } catch {
      /* storage blocked — still proceed */
    }
    setScenario('intervention')
    setPhase('design')
  }, [seenKey, setPhase])

  const replayStory = useCallback(() => {
    setSelectedSiteIndex(null)
    setHoverSiteIndex(null)
    setPhase('intro')
  }, [setPhase])

  // 2D ↔ 3D toggle: ease the pitch up for the cinematic view, flat for analysis.
  const toggle3d = useCallback(() => {
    setView3d((v) => {
      const next = !v
      const map = mapRef.current?.getMap()
      if (map) {
        cameraModeRef.current = 'auto'
        map.easeTo({ pitch: next ? 58 : 0, duration: reducedMotion ? 0 : 600 })
      }
      return next
    })
  }, [reducedMotion])

  const onSelectSite = useCallback(
    (site: CityPlanSite, index: number) => {
      setSelectedSiteIndex(index)
      // Close enough that the ~140 m planting fills the view and each canopy
      // reads as a real disk (not a speck), tilted for depth.
      flyToSite(site.centroid_lonlat[0], site.centroid_lonlat[1], { zoom: 16.8, pitch: 45 })
    },
    [flyToSite],
  )

  const switchMode = phase === 'citywide' ? 'citywide' : 'design'

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <Map
        ref={mapRef}
        reuseMaps
        // UNCONTROLLED camera: the map owns its view so imperative flyTo/jumpTo
        // is authoritative (Redesign Spec §5). onMove mirrors the view into local
        // state (read-only) for zoom-dependent logic; we never feed it back as a
        // controlled prop, which is what previously fought the fly and stranded
        // the camera zoomed-out over all Barcelona.
        initialViewState={viewState}
        onMove={onMove}
        onMoveEnd={onMoveEnd}
        onLoad={onMapLoad}
        onClick={isDrawPhase ? onMapClick : undefined}
        onMouseMove={isDrawPhase ? onMapMouseMove : undefined}
        onDblClick={isDrawPhase ? onMapDblClick : undefined}
        dragPan={phase !== 'design' || !draw.drawing}
        doubleClickZoom={phase !== 'design' || draw.mode !== 'polygon'}
        cursor={isDrawPhase && draw.mode ? 'crosshair' : undefined}
        mapboxAccessToken={MAPBOX_TOKEN}
        mapStyle={mapStyle}
        style={{ width: '100%', height: '100%' }}
        antialias
      >
        {view3d && (
          <MapLayer
            id="3d-buildings"
            type="fill-extrusion"
            source="composite"
            source-layer="building"
            minzoom={13}
            paint={{
              'fill-extrusion-color': '#e9edf2',
              'fill-extrusion-height': ['get', 'height'],
              'fill-extrusion-base': ['get', 'min_height'],
              'fill-extrusion-opacity': 0.95,
            }}
          />
        )}
        <DeckOverlay layers={allLayers} onClick={onDeckClick} />
      </Map>

      {/* Cinematic spotlight overlay (above map, below UI). */}
      <div className="vignette" style={{ opacity: vignette }} aria-hidden />

      <TreeInspect tree={selectedTree} onClose={() => setSelectedTree(null)} />

      {/* ── Phase-gated chrome ───────────────────────────────────────────── */}

      {phase === 'intro' && (
        <Onboarding
          plan={cityPlan}
          onIntent={onOnboardingIntent}
          onFinish={finishIntro}
          onSeeCityPlan={() => {
            finishIntro()
            setPhase('citywide')
          }}
        />
      )}

      {phase !== 'intro' && (
        <ModeSwitch
          mode={switchMode}
          onChange={(m) => {
            if (m === 'citywide') setPhase('citywide')
            else setPhase(phase === 'citywide' ? 'design' : phase)
          }}
        />
      )}

      {phase !== 'intro' && (
        <button
          type="button"
          className={`view3d-toggle ${view3d ? 'is-3d' : ''}`}
          onClick={toggle3d}
          aria-pressed={view3d}
          title="Toggle 2D analysis / 3D cinematic view"
        >
          {view3d ? '◳ 3D' : '⬚ 2D'}
        </button>
      )}

      {/* Design + Result: Action Rail (right). Result also shows the Result Card. */}
      {isDrawPhase && (
        <ActionRail
          mode={draw.mode}
          setMode={draw.setMode}
          clear={draw.clear}
          ring={draw.ring}
          area={draw.area}
          status={draw.status}
          budgetEur={budgetEur}
          setBudgetEur={setBudgetEur}
          onEvaluated={handleEvaluated}
          onEvaluatingChange={setEvaluating}
          scenario={scenario}
          onScenarioChange={setScenario}
          rasterOpacity={rasterOpacity}
          onRasterOpacityChange={setRasterOpacity}
        />
      )}

      {phase === 'design' && (
        <div className="map-hint" role="status">
          Draw any block in Barcelona, then evaluate the cooling.
        </div>
      )}

      {phase === 'result' && (
        <ResultCard
          bundle={bundle}
          year={plantingYear}
          setYear={setPlantingYear}
          growthParams={growthParams}
          showGrowth={!!bundle.trees && bundle.trees.features.length > 0}
          onSeeCityPlan={() => setPhase('citywide')}
        />
      )}

      {phase === 'citywide' && (
        <CitywidePanel
          plan={cityPlan}
          loading={citywideLoading}
          onSelectSite={onSelectSite}
          onHoverSite={setHoverSiteIndex}
          selectedIndex={selectedSiteIndex}
          onCoolOwnBlock={() => {
            setSelectedSiteIndex(null)
            setPhase('design')
          }}
          onReplayStory={replayStory}
        />
      )}

      {/* Always-visible gradient legend (bottom-right). */}
      {phase !== 'intro' && (
        <div className="legend-dock">
          <Legend />
        </div>
      )}

      {/* Narrated wait while the live sim runs (§5 #9). */}
      {evaluating && (
        <div className="eval-overlay" role="status" aria-live="polite">
          <div className="eval-overlay__card panel">
            <div className="spinner" aria-hidden />
            <div className="eval-overlay__title">Measuring the cooling…</div>
            <div className="eval-overlay__line">
              Placing trees on plantable spots · running Infrared UTCI · measuring cooled area
            </div>
          </div>
        </div>
      )}

      {credits && <div className="attribution">{credits}</div>}
    </div>
  )
}
