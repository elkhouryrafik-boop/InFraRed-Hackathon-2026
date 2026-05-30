// Data-contract types for the "web bundle" produced by the Python exporter.
// These mirror the files in /public/web_bundle/ exactly.

export interface Configuration {
  rank: number
  label: string
  tree_count: number
  cost_eur: number
  cooled_footprint_m2: number
  eur_per_m2: number
  delta_utci_c: number
  utci_baseline_mean: number
  utci_baseline_peak: number
  utci_intervention_mean: number
  utci_intervention_peak: number
  species: string[]
}

export interface Decision {
  headline: string
  backend: string
  disclaimer: string
  budget_eur: number
  site_center_lonlat: [number, number] // [lon, lat]
  site_size_m: number
  generated_at: string
  configurations: Configuration[]
}

export interface BoundaryProperties {
  kind: 'site_boundary'
  [k: string]: unknown
}

export interface BoundaryFeature {
  type: 'Feature'
  properties: BoundaryProperties
  geometry: {
    type: 'Polygon'
    coordinates: [number, number][][] // [ring][vertex] = [lon, lat]
  }
}

export interface BoundaryGeoJSON {
  type: 'FeatureCollection'
  features: BoundaryFeature[]
}

export type TreeKind = 'proposed' | 'existing'

export interface TreeProperties {
  kind: TreeKind
  species: string
  crown_diameter_m: number
  height_m: number
  color: [number, number, number] // 0-255 rgb
}

export interface TreeFeature {
  type: 'Feature'
  properties: TreeProperties
  geometry: {
    type: 'Point'
    coordinates: [number, number] // [lon, lat]
  }
}

export interface TreesGeoJSON {
  type: 'FeatureCollection'
  features: TreeFeature[]
}

export interface RasterBounds {
  west: number
  south: number
  east: number
  north: number
}

export type UtciScenario = 'baseline' | 'intervention'

/** Impervious-pavement (depave) analysis from the backend ground-material complement. */
export interface ImperviousAnalysis {
  impervious_m2: number
  permeable_m2: number
  site_area_m2: number
  impervious_fraction: number
  geojson: {
    type: 'FeatureCollection'
    features: {
      type: 'Feature'
      properties: { material: string }
      geometry: { type: 'Polygon' | 'MultiPolygon'; coordinates: unknown }
    }[]
  }
  available: boolean
  permeable_fraction: number
  permeable_target_min: number
  permeable_target_max: number
  /** Set on /api/evaluate: impervious m² the proposed canopy shades. */
  depaved_cooled_m2?: number
  /** Set on /api/evaluate: permeable fraction if pavement under canopy is depaved. */
  permeable_fraction_if_depaved?: number
}

/** Canopy-cover analysis vs the 30-40% climate-responsive target. */
export interface CanopyCover {
  cover_fraction: number
  canopy_m2: number
  site_area_m2: number
  target_min: number
  target_max: number
  in_band: boolean
}

export interface WebBundle {
  decision: Decision
  boundary: BoundaryGeoJSON
  trees: TreesGeoJSON
  bounds: RasterBounds
  // Resolved object URLs / paths for the two heatmap PNGs.
  baselineImageUrl: string
  interventionImageUrl: string
  /** Depaveable impervious pavement, when available (live runs). */
  impervious?: ImperviousAnalysis | null
  /** Canopy cover vs the 30-40% target (set on /api/evaluate). */
  canopy?: CanopyCover | null
  /** Establishment-ramp params from cost_model, for the age slider. */
  growth?: { ramp_years: number; initial_fraction: number; horizon_years: number } | null
}
