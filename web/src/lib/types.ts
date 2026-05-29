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

export interface WebBundle {
  decision: Decision
  boundary: BoundaryGeoJSON
  trees: TreesGeoJSON
  bounds: RasterBounds
  // Resolved object URLs / paths for the two heatmap PNGs.
  baselineImageUrl: string
  interventionImageUrl: string
}
