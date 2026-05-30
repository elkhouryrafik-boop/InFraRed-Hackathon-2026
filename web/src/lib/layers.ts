// deck.gl layer builders. Composition order follows recipe §6.
// NOTE: COORDINATE_SYSTEM imported from @deck.gl/core, NOT the deck.gl barrel
// (recipe §7) to avoid BitmapLayer init assertions.

import { Tile3DLayer } from '@deck.gl/geo-layers'
import {
  BitmapLayer,
  SolidPolygonLayer,
  PolygonLayer,
  IconLayer,
  GeoJsonLayer,
} from '@deck.gl/layers'
import { MaskExtension } from '@deck.gl/extensions'
import { Tiles3DLoader } from '@loaders.gl/3d-tiles'
import type { Layer } from '@deck.gl/core'

import type { TreesGeoJSON, TreeFeature, ImperviousAnalysis } from './types'
import { EXISTING_TREE_COLOR } from './colorscale'

const MASK_ID = 'cutout-mask'

// Stylized tree billboard sprite (web/public/tree.png, 128x128, transparent).
// anchorY at the bottom so the trunk sits on the ground; the canopy rises up.
const TREE_ICON = {
  url: 'tree.png',
  width: 128,
  height: 128,
  anchorX: 64,
  anchorY: 124, // near the very bottom of the sprite (trunk base)
  mask: false,
} as const

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

  // ── Trees (top of overlays) — billboarded 3D-ish tree sprites.
  // IconLayer renders the stylized tree.png as a camera-facing billboard, sized
  // in METERS by crown diameter and anchored at the trunk base so the tree
  // "stands" on the ground in a pitched 3D view. getColor multiply-tints the
  // (green) sprite: ~white keeps a vivid proposed tree, muted olive damps an
  // existing tree. We DON'T billboard the whole canopy flat — sizeUnits:'meters'
  // + bottom anchor makes it read as a standing tree at pitch.
  if (trees && trees.features.length > 0) {
    out.push(
      new IconLayer(
        withLift(
          {
            id: 'trees',
            data: trees.features,
            // Single sprite shared by all trees; tinted per-feature via getColor.
            getIcon: () => TREE_ICON,
            billboard: true,
            sizeUnits: 'meters',
            // The visible tree fills the full sprite height, so size ≈ tree
            // height. Scale crown diameter up to a believable canopy:trunk
            // proportion (~1.8x crown ≈ overall tree height).
            getSize: (f: TreeFeature) => {
              const crown = f.properties.crown_diameter_m ?? 6
              // existing trees a touch smaller so proposed plantings stand out
              const k = f.properties.kind === 'existing' ? 1.55 : 1.8
              // Proposed trees grow with the age slider; existing trees are mature.
              const grow = f.properties.kind === 'existing' ? 1 : treeScale
              return Math.max(4, crown * k * grow)
            },
            // Re-evaluate getSize when the age slider moves.
            updateTriggers: { getSize: treeScale },
            sizeMinPixels: 14, // stay legible when zoomed out
            sizeMaxPixels: 220,
            getPosition: (f: TreeFeature) => f.geometry.coordinates,
            getColor: (f: TreeFeature): [number, number, number, number] => {
              if (f.properties.kind === 'existing') {
                // Muted olive multiply + slight translucency for existing trees.
                const [r, g, b] = EXISTING_TREE_COLOR
                return [r + 60, g + 60, b + 60, 205]
              }
              // Proposed: gently bias the green sprite toward the species color
              // while staying near-white so the baked shading + brown trunk
              // survive the multiply.
              const c = f.properties.color ?? [60, 160, 90]
              const mix = (v: number) => Math.round(190 + (v / 255) * 65)
              return [mix(c[0]), mix(c[1]), mix(c[2]), 255]
            },
            pickable: true,
          },
          modelMatrix,
        ),
      ),
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
