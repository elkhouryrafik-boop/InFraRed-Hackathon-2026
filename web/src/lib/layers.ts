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
import { EXISTING_TREE_COLOR } from './colorscale'

const MASK_ID = 'cutout-mask'

export interface BuildLayersArgs {
  tilesetUrl: string | null
  boundaryRing: [number, number][] | null
  raster: { image: string; bounds: [number, number, number, number] } | null
  rasterOpacity: number
  trees: TreesGeoJSON | null
  /** Visual canopy scale (0..1) for the age slider; 1 = mature. */
  treeScale?: number
  /** Depaveable impervious pavement overlay (optional). */
  impervious?: ImperviousAnalysis | null
  showImpervious?: boolean
  /** Shared elevation lift (modelMatrix) for every overlay. */
  modelMatrix: number[] | null
  /** Credit-capture callback for legal attribution. */
  onTilesetLoad?: (tileset: unknown) => void
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
    raster,
    rasterOpacity,
    trees,
    treeScale = 1,
    impervious,
    showImpervious,
    modelMatrix,
    onTilesetLoad,
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

  // ── UTCI heatmap drape (recipe §5.1) — under trees, over the floor.
  if (raster) {
    out.push(
      new BitmapLayer(
        withLift(
          {
            id: 'utci-raster',
            image: raster.image,
            bounds: raster.bounds,
            opacity: rasterOpacity,
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
    out.push(
      new ScatterplotLayer({
        id: 'trees',
        data: trees.features,
        getPosition: (f: TreeFeature) => f.geometry.coordinates,
        radiusUnits: 'meters',
        getRadius: (f: TreeFeature) => {
          const crown = f.properties.crown_diameter_m ?? 6
          const grow = f.properties.kind === 'existing' ? 1 : treeScale
          return Math.max(1.5, (crown / 2) * grow)
        },
        radiusMinPixels: 4,
        radiusMaxPixels: 140,
        updateTriggers: { getRadius: treeScale },
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
  }

  return out
}

// ── Citywide (Mode 2) heatmap ────────────────────────────────────────────────

/** Color-scale: composite_score_B → [r, g, b, a]. Hot=red, cold=blue. */
function scoreColor(score: number): [number, number, number, number] {
  // Clamp to [0, 1] then lerp blue (low) → yellow (mid) → red (high).
  const t = Math.max(0, Math.min(1, score))
  // Two-stop: blue(0) → yellow(0.5) → red(1)
  let r: number, g: number, b: number
  if (t < 0.5) {
    const s = t * 2
    r = Math.round(s * 255)
    g = Math.round(s * 200)
    b = Math.round(255 - s * 200)
  } else {
    const s = (t - 0.5) * 2
    r = 255
    g = Math.round(200 - s * 200)
    b = Math.round(55 - s * 55)
  }
  return [r, g, b, 180]
}

export interface CitywideLayerArgs {
  /** GeoJSON FeatureCollection (the scored_grid cells). */
  data: GeoJSON.FeatureCollection | null
  /** Opacity 0..1. */
  opacity?: number
}

export function buildCitywideLayer(args: CitywideLayerArgs): Layer | null {
  const { data, opacity = 0.6 } = args
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
    getFillColor: (f: { properties?: { composite_score_B?: number } }) =>
      scoreColor(f.properties?.composite_score_B ?? 0),
    getLineColor: [30, 30, 40, 100] as [number, number, number, number],
    getLineWidth: 0.5,
    opacity,
    updateTriggers: { getFillColor: [opacity] },
  })
}
