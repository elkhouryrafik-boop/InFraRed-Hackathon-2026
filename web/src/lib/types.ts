// Data-contract types for the "web bundle" produced by the Python exporter.
// These mirror the files in /public/web_bundle/ exactly.

// Per-cell analysis of the measured UTCI grids (null on mock/scalar backends).
export interface CooledProfile {
  cooled_m2_by_band: Record<string, number> // e.g. { "0.5": 3940, "1": 2928, "2": 1628 }
  mean_drop_c: number
  std_drop_c: number
  p10_drop_c: number
  p90_drop_c: number
  peak_drop_c: number
  cooled_fraction: number
  heat_stress_relieved_m2: number
  heat_stress_threshold_c: number
  largest_cooled_patch_m2: number | null
  n_cooled_patches: number | null
  valid_cells_m2: number
  bands_c: number[]
}

export interface Configuration {
  rank: number
  label: string
  tree_count: number
  cost_eur: number
  // KPI fields are null on the mock/scalar backend (no measured grid). The
  // exporter writes null, so the type must allow it — formatters guard for it.
  cooled_footprint_m2: number | null
  eur_per_m2: number | null
  delta_utci_c: number
  utci_baseline_mean: number | null
  utci_baseline_peak: number | null
  utci_intervention_mean: number | null
  utci_intervention_peak: number | null
  cost_per_utci_degree?: number | null
  cooled_profile?: CooledProfile | null
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

// Per-species ecological profile (added by the Python ecology layer; optional
// until that layer is wired). Scores are 0–1 unless noted.
export interface TreeEcology {
  native_status?: string
  drought_heat_tolerance?: number
  biodiversity_value?: number
  pollinator_value?: number
  allergenicity?: number // higher = worse pollen burden
  pest_disease_risk?: number // higher = worse
  longevity_years?: number
  growth_rate?: string
  water_demand?: string
  maintenance_burden?: string
  carbon_sequestration?: number
  mycorrhizal_type?: string
  ecosystem_score?: number // composite ecosystem-health score 0–1
  notes?: string
}

export interface TreeProperties {
  kind: TreeKind
  species: string // scientific name
  common?: string
  crown_diameter_m: number
  height_m: number
  leaf_cycle?: string
  shade_density?: string
  crown_area_m2?: number // ground footprint the canopy shades
  cooling_score?: number // 0–1 species cooling proxy (ranking only)
  known?: boolean // false = species not in the BCN palette
  ecology?: TreeEcology
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

/** Citywide cell from /api/citywide/scan ranked results. */
export interface CitywideCell {
  rank: number
  cell_id: string
  district: string
  barri: string
  composite_score_B: number
  mean_sealed: number
  mean_lst_celsius: number
  lst_anomaly: number
  cooling_proxy: number
  sample_area_m2: number
  impervious_area_m2: number
  est_trees: number
  est_cost_eur: number
  allocated_eur: number
  centroid_lonlat: [number, number]
  eval_polygon: [number, number][]
}

export interface CitywideScan {
  mode: string
  total_cells: number
  ranked_count: number
  budget_eur: number
  cumulative_allocated_eur: number
  cells: CitywideCell[]
  note: string
}

/** App display mode: draw (Mode 1) or citywide overview (Mode 2). */
export type AppMode = 'draw' | 'citywide'

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
