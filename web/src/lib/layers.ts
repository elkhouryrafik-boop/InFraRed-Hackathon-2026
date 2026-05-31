// deck.gl layer builders. Composition order follows recipe §6.
// NOTE: COORDINATE_SYSTEM imported from @deck.gl/core, NOT the deck.gl barrel
// (recipe §7) to avoid BitmapLayer init assertions.

import { Tile3DLayer } from '@deck.gl/geo-layers'
import {
  BitmapLayer,
  SolidPolygonLayer,
  PolygonLayer,
  ScatterplotLayer,
  GeoJsonLayer,
} from '@deck.gl/layers'
import { MaskExtension } from '@deck.gl/extensions'
import { Tiles3DLoader } from '@loaders.gl/3d-tiles'
import type { Layer } from '@deck.gl/core'

import type { TreesGeoJSON, TreeFeature, ImperviousAnalysis } from './types'
import { EXISTING_TREE_COLOR, utciColor, alphaByIntensity } from './colorscale'
import { crownDiameterAtAge } from './growth'
import { speciesDims, foliageColor } from './species'

const MASK_ID = 'cutout-mask'

export interface BuildLayersArgs {
  tilesetUrl: string | null
  boundaryRing: [number, number][] | null
  /** Both UTCI drapes, stacked, so we can cross-fade baseline↔intervention (§5). */
  rasterBaseline: { image: string; bounds: [number, number, number, number] } | null
  rasterIntervention: { image: string; bounds: [number, number, number, number] } | null
  /** 0 = show baseline, 1 = show intervention; tweened by deck for the reveal. */
  rasterMix: number
  rasterOpacity: number
  trees: TreesGeoJSON | null
  /** Visual canopy scale (0..1) for the age slider; 1 = mature. (legacy fallback) */
  treeScale?: number
  /** Years after planting (age slider); each tree grows on its own species curve. */
  growthYear?: number
  /** Depaveable impervious pavement overlay (optional). */
  impervious?: ImperviousAnalysis | null
  showImpervious?: boolean
  /** Shared elevation lift (modelMatrix) for every overlay. */
  modelMatrix: number[] | null
  /** Credit-capture callback for legal attribution. */
  onTilesetLoad?: (tileset: unknown) => void
  /**
   * Enable the signature reveal choreography (Redesign Spec §5): trees pop in
   * via a deck.gl getRadius transition, the heatmap fades. Disabled under
   * prefers-reduced-motion (instant state).
   */
  animateReveal?: boolean
}

type Ring = [number, number][]
interface ImperviousFeature {
  geometry: { coordinates: Ring[] }
}

/** Apply the shared elevation lift to a layer's props, if any. */
function withLift<T extends Record<string, unknown>>(
  props: T,
  modelMatrix: number[] | null,
): T {
  return modelMatrix ? { ...props, modelMatrix } : props
}

export function buildLayers(args: BuildLayersArgs): Layer[] {
  const {
    tilesetUrl,
    boundaryRing,
    rasterBaseline,
    rasterIntervention,
    rasterMix,
    rasterOpacity,
    trees,
    treeScale = 1,
    growthYear,
    impervious,
    showImpervious,
    modelMatrix,
    onTilesetLoad,
    animateReveal = false,
  } = args

  const out: Layer[] = []
  const hasMask = !!boundaryRing && boundaryRing.length >= 3

  // ── Hidden mask layer (recipe §3) — never drawn, feeds the mask texture.
  if (hasMask) {
    out.push(
      new SolidPolygonLayer({
        id: MASK_ID,
        operation: 'mask',
        data: [{ polygon: boundaryRing }],
        getPolygon: (d: { polygon: [number, number][] }) => d.polygon,
      }),
    )
  }

  // ── Photogrammetry (bottom). Mask inverted -> cut a hole INSIDE the ring.
  if (tilesetUrl) {
    out.push(
      new Tile3DLayer({
        id: 'g3d',
        data: tilesetUrl,
        loader: Tiles3DLoader,
        opacity: 1,
        pickable: false,
        loadOptions: {
          tileset: {
            maximumScreenSpaceError: 12,
            maximumMemoryUsage: 512,
            maxRequests: 16,
            debounceTime: 80,
            viewDistanceScale: 0.8,
          },
        },
        extensions: hasMask ? [new MaskExtension()] : [],
        ...(hasMask ? { maskId: MASK_ID, maskInverted: true } : {}),
        onTilesetLoad: onTilesetLoad as never,
      }),
    )
  }

  // ── UTCI heatmap drapes (recipe §5.1) — under trees, over the floor. Two
  // stacked bitmaps (baseline + intervention) whose opacities are driven by
  // rasterMix, so flipping the scenario / running the reveal CROSS-FADES (deck
  // tweens each opacity) instead of a jarring image swap (§5 "money moment").
  const mix = Math.max(0, Math.min(1, rasterMix))
  if (rasterBaseline) {
    out.push(
      new BitmapLayer(
        withLift(
          {
            id: 'utci-raster-baseline',
            image: rasterBaseline.image,
            bounds: rasterBaseline.bounds,
            opacity: rasterOpacity * (1 - mix),
            transitions: animateReveal ? { opacity: 600 } : undefined,
            parameters: { depthTest: true },
          },
          modelMatrix,
        ),
      ),
    )
  }
  if (rasterIntervention) {
    out.push(
      new BitmapLayer(
        withLift(
          {
            id: 'utci-raster-intervention',
            image: rasterIntervention.image,
            bounds: rasterIntervention.bounds,
            opacity: rasterOpacity * mix,
            transitions: animateReveal ? { opacity: 600 } : undefined,
            parameters: { depthTest: true },
          },
          modelMatrix,
        ),
      ),
    )
  }

  // ── Depaveable impervious pavement (the "rip up asphalt" overlay).
  // Drawn above the floor/raster, below trees, so the canopy reads as sitting
  // on top of the pavement it replaces. Warm amber = "paved, depave candidate".
  if (showImpervious && impervious?.available && impervious.geojson.features.length > 0) {
    out.push(
      new PolygonLayer(
        withLift(
          {
            id: 'impervious-depave',
            data: impervious.geojson.features as ImperviousFeature[],
            getPolygon: (f: ImperviousFeature) => f.geometry.coordinates,
            filled: true,
            stroked: true,
            getFillColor: [232, 138, 64, 80] as [number, number, number, number],
            getLineColor: [232, 138, 64, 200] as [number, number, number, number],
            getLineWidth: 1,
            lineWidthUnits: 'pixels',
            lineWidthMinPixels: 1,
          },
          modelMatrix,
        ),
      ),
    )
  }

  // ── Boundary outline (ring stroke).
  if (hasMask) {
    out.push(
      new PolygonLayer(
        withLift(
          {
            id: 'boundary-outline',
            data: [{ polygon: boundaryRing }],
            getPolygon: (d: { polygon: [number, number][] }) => d.polygon,
            stroked: true,
            filled: false,
            getLineColor: [43, 200, 188, 240] as [number, number, number, number],
            getLineWidth: 3,
            lineWidthUnits: 'pixels',
            lineWidthMinPixels: 2,
          },
          modelMatrix,
        ),
      ),
    )
  }

  // ── Trees — canopy-footprint disks (ScatterplotLayer).
  // Each tree is drawn as a filled circle whose RADIUS is the real canopy radius
  // in metres (crown_diameter / 2), i.e. the literal ground area it shades. This
  // is both more honest than a generic sprite (you see the actual shaded
  // footprint) and far more robust to render than meter-sized billboards over a
  // basemap. depthTest:false keeps canopies above the basemap; semi-transparent
  // fill lets the UTCI heatmap read through. Proposed canopies grow with the age
  // slider; existing trees are mature context.
  if (trees && trees.features.length > 0) {
    // Shared canopy radius (m) — used by both the canopy disk and its inner core.
    const treeRadius = (f: TreeFeature): number => {
      const crown = f.properties.crown_diameter_m ?? 6
      // Existing trees are mature context. Proposed trees grow on their own
      // species allometric curve when a growthYear (age slider) is given;
      // otherwise fall back to the legacy global treeScale.
      if (f.properties.kind === 'existing') return Math.max(1.5, crown / 2)
      if (growthYear != null) {
        const maturity = f.properties.ecology?.maturity_years ?? 30
        return Math.max(1.5, crownDiameterAtAge(crown, maturity, growthYear) / 2)
      }
      return Math.max(1.5, (crown / 2) * treeScale)
    }
    out.push(
      new ScatterplotLayer({
        id: 'trees',
        data: trees.features,
        getPosition: (f: TreeFeature) => f.geometry.coordinates,
        radiusUnits: 'meters',
        getRadius: treeRadius,
        radiusMinPixels: 4,
        radiusMaxPixels: 140,
        updateTriggers: { getRadius: [treeScale, growthYear] },
        // Trees pop in / grow on reveal (§5): staggered getRadius transition.
        transitions: animateReveal ? { getRadius: { duration: 800 } } : undefined,
        stroked: true,
        filled: true,
        lineWidthUnits: 'pixels',
        getLineWidth: 1.5,
        lineWidthMinPixels: 1,
        getFillColor: (f: TreeFeature): [number, number, number, number] => {
          if (f.properties.kind === 'existing') {
            const [r, g, b] = EXISTING_TREE_COLOR
            return [r, g, b, 90]
          }
          const c = f.properties.color ?? [60, 160, 90]
          return [c[0], c[1], c[2], 150]
        },
        getLineColor: (f: TreeFeature): [number, number, number, number] =>
          f.properties.kind === 'existing'
            ? [180, 200, 150, 160]
            : [240, 255, 245, 220],
        parameters: { depthTest: false },
        pickable: true,
      }),
    )
    // Inner canopy core — a smaller, lighter, more opaque concentric disk that
    // reads as canopy density/volume from top-down (more tree-like than a flat
    // disk), and gives the foliage a soft highlighted centre. Non-pickable so it
    // never steals clicks from the main canopy.
    out.push(
      new ScatterplotLayer({
        id: 'tree-cores',
        data: trees.features,
        getPosition: (f: TreeFeature) => f.geometry.coordinates,
        radiusUnits: 'meters',
        getRadius: (f: TreeFeature) => treeRadius(f) * 0.5,
        radiusMinPixels: 2,
        radiusMaxPixels: 70,
        updateTriggers: { getRadius: [treeScale, growthYear] },
        stroked: false,
        filled: true,
        getFillColor: (f: TreeFeature): [number, number, number, number] => {
          if (f.properties.kind === 'existing') {
            const [r, g, b] = EXISTING_TREE_COLOR
            return [r, g, b, 70]
          }
          const c = f.properties.color ?? [60, 160, 90]
          // Lighter, denser centre: lift toward white, higher alpha.
          return [
            Math.min(255, c[0] + 50),
            Math.min(255, c[1] + 55),
            Math.min(255, c[2] + 40),
            120,
          ]
        },
        parameters: { depthTest: false },
        pickable: false,
      }),
    )
  }

  return out
}

// ── Citywide (Mode 2) heatmap ────────────────────────────────────────────────

// composite_score_B in the scored grid clusters tightly (~0.45–0.80), so a raw
// 0..1 mapping would wash every cell to the same hot colour. Stretch the live
// range onto the CVD-safe UTCI ramp's intensity so the grid reads as a thermal
// field rather than one flat orange blob (§4.9). Anchored, not invented:
// cool end ≈ 22 °C-equivalent, hot end ≈ 40 °C-equivalent.
const SCORE_LO = 0.45
const SCORE_HI = 0.82
const RAMP_LO_C = 22
const RAMP_HI_C = 40

function scoreToUtciC(score: number): number {
  const t = Math.max(0, Math.min(1, (score - SCORE_LO) / (SCORE_HI - SCORE_LO)))
  return RAMP_LO_C + t * (RAMP_HI_C - RAMP_LO_C)
}

/**
 * Color-scale: composite_score_B → luminous [r, g, b, a].
 * Hot = bright (CVD-safe monotonic-lightness ramp), alpha ramps with intensity
 * so danger glows and cool cells let the city through (§4.9-1/-3).
 * `dim` (citywide focus-vs-context) desaturates + drops alpha for unfunded cells.
 */
function scoreColor(score: number, dim = false): [number, number, number, number] {
  const c = scoreToUtciC(score)
  const t = Math.max(0, Math.min(1, (score - SCORE_LO) / (SCORE_HI - SCORE_LO)))
  let [r, g, b] = utciColor(c)
  let a = Math.round(alphaByIntensity(t) * 255)
  if (dim) {
    // Pull toward a neutral slate (saturate ~0.7) and drop to α≈0.4.
    const gray = Math.round(0.3 * r + 0.59 * g + 0.11 * b)
    r = Math.round(r * 0.7 + gray * 0.3)
    g = Math.round(g * 0.7 + gray * 0.3)
    b = Math.round(b * 0.7 + gray * 0.3)
    a = Math.round(0.4 * 255)
  }
  return [r, g, b, a]
}

/**
 * €1M plan: a mint-ringed marker per funded site, radius ∝ trees planted there
 * (§4.9-5). Funded sites stay full-saturation with a mint contour + glow; the
 * `highlightIndex` (hover/selection) pulses one ring wider.
 */
export function buildCityPlanLayer(
  sites: { centroid_lonlat: [number, number]; tree_count: number; partial?: boolean }[] | null,
  highlightIndex?: number | null,
): Layer | null {
  if (!sites || sites.length === 0) return null
  return new ScatterplotLayer({
    id: 'city-plan-sites',
    data: sites,
    getPosition: (s: { centroid_lonlat: [number, number] }) => s.centroid_lonlat,
    // FIXED-PIXEL ring markers (not metre disks — those ballooned over the trees
    // at site zoom). A small glowing ring locates each funded site at the overview
    // and steps aside for the real canopy disks when you fly in.
    radiusUnits: 'pixels',
    getRadius: (s: { tree_count: number }, info?: { index: number }) => {
      const base = 9 + s.tree_count * 0.35 // ~9–15px
      return highlightIndex != null && info && info.index === highlightIndex ? base + 5 : base
    },
    stroked: true,
    filled: true,
    // Hollow-ish: faint fill so the ring reads as a locator, never a solid blob.
    getFillColor: (s: { partial?: boolean }) =>
      (s.partial ? [240, 185, 104, 45] : [59, 232, 192, 50]) as [number, number, number, number],
    getLineColor: (_s: unknown, info?: { index: number }) =>
      (highlightIndex != null && info && info.index === highlightIndex
        ? [223, 255, 248, 255]
        : [95, 246, 214, 235]) as [number, number, number, number],
    lineWidthUnits: 'pixels',
    getLineWidth: (_s: unknown, info?: { index: number }) =>
      highlightIndex != null && info && info.index === highlightIndex ? 3.5 : 2,
    lineWidthMinPixels: 2,
    updateTriggers: {
      getRadius: [highlightIndex],
      getLineColor: [highlightIndex],
      getLineWidth: [highlightIndex],
    },
    parameters: { depthTest: false },
    pickable: true,
  })
}

/**
 * The €1M plan's actual placed trees, across all funded sites, drawn as real
 * canopy disks + lighter cores (same look as the single-site trees) so the
 * citywide view SHOWS the 99 planted trees — not just abstract pins. Reads
 * `trees_lonlat` from each allocated cell; crown size + foliage colour from the
 * client-side species table. `dimUnselected` fades trees of non-selected sites.
 */
export function buildCityTreesLayer(
  sites:
    | { trees_lonlat?: { lon: number; lat: number; species: string }[]; cell_id: string }[]
    | null,
  opts?: { selectedCellId?: string | null },
): Layer[] {
  if (!sites || sites.length === 0) return []
  const selected = opts?.selectedCellId ?? null
  type CT = { lon: number; lat: number; species: string; cell: string }
  const flat: CT[] = []
  for (const s of sites) {
    for (const t of s.trees_lonlat ?? []) {
      flat.push({ lon: t.lon, lat: t.lat, species: t.species, cell: s.cell_id })
    }
  }
  if (flat.length === 0) return []
  const radiusOf = (d: CT) => Math.max(2.5, speciesDims(d.species).crown_m / 2)
  const focusA = (d: CT, base: number) =>
    selected && d.cell !== selected ? Math.round(base * 0.45) : base
  return [
    new ScatterplotLayer({
      id: 'city-trees',
      data: flat,
      getPosition: (d: CT) => [d.lon, d.lat],
      radiusUnits: 'meters',
      getRadius: radiusOf,
      radiusMinPixels: 5,
      radiusMaxPixels: 90,
      stroked: true,
      filled: true,
      lineWidthUnits: 'pixels',
      getLineWidth: 1,
      lineWidthMinPixels: 0.5,
      getFillColor: (d: CT) => {
        const [r, g, b] = foliageColor(d.species)
        return [r, g, b, focusA(d, 165)] as [number, number, number, number]
      },
      getLineColor: (d: CT) =>
        [235, 255, 240, focusA(d, 200)] as [number, number, number, number],
      updateTriggers: { getFillColor: [selected], getLineColor: [selected] },
      parameters: { depthTest: false },
      pickable: true, // click a canopy → drill into its site (handled in Scene)
    }),
    new ScatterplotLayer({
      id: 'city-tree-cores',
      data: flat,
      getPosition: (d: CT) => [d.lon, d.lat],
      radiusUnits: 'meters',
      getRadius: (d: CT) => radiusOf(d) * 0.5,
      radiusMinPixels: 1.5,
      radiusMaxPixels: 45,
      stroked: false,
      filled: true,
      getFillColor: (d: CT) => {
        const [r, g, b] = foliageColor(d.species)
        return [
          Math.min(255, r + 55),
          Math.min(255, g + 55),
          Math.min(255, b + 45),
          focusA(d, 150),
        ] as [number, number, number, number]
      },
      updateTriggers: { getFillColor: [selected] },
      parameters: { depthTest: false },
      pickable: false,
    }),
  ]
}

export interface CitywideLayerArgs {
  /** GeoJSON FeatureCollection (the scored_grid cells). */
  data: GeoJSON.FeatureCollection | null
  /** Opacity 0..1. */
  opacity?: number
  /**
   * When set, every cell NOT in this set is dimmed to whisper-faint context so
   * the 7 funded sites read as the focus (§4.9-5). Keyed on cell_id.
   */
  fundedCellIds?: Set<string> | null
}

export function buildCitywideLayer(args: CitywideLayerArgs): Layer | null {
  const { data, opacity = 0.6, fundedCellIds = null } = args
  if (!data) return null

  return new GeoJsonLayer({
    id: 'citywide-heatmap',
    data,
    pickable: true,
    stroked: true,
    filled: true,
    extruded: false,
    lineWidthScale: 1,
    lineWidthMinPixels: 0.5,
    getFillColor: (f: { properties?: { composite_score_B?: number; cell_id?: string } }) => {
      const score = f.properties?.composite_score_B ?? 0
      const dim = !!fundedCellIds && !!f.properties?.cell_id && !fundedCellIds.has(f.properties.cell_id)
      return scoreColor(score, dim)
    },
    // Thin iso-contour-style cell edges (§4.9-6): faint white lattice that turns
    // a gradient into readable thermal topography.
    getLineColor: [255, 255, 255, 30] as [number, number, number, number],
    getLineWidth: 0.5,
    opacity,
    updateTriggers: { getFillColor: [opacity, fundedCellIds] },
  })
}
