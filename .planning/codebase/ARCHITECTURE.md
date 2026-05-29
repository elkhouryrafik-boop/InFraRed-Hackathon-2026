# Architecture

**Analysis Date:** 2026-05-27

## High-Level Architecture

CoolSpend is a pipeline-based decision-support system. Each run starts from a site polygon and a budget, then passes through five sequential stages: surrogate optimization, candidate selection, Infrared validation, multi-criteria ranking, and artifact output.

```
                    ┌─────────────────────────────┐
                    │  User Inputs                │
                    │  - Site polygon (GeoJSON)   │
                    │  - Budget (EUR)             │
                    │  - TOPSIS weights           │
                    │  - Infrared backend choice  │
                    │  - Cost table edits         │
                    └─────────────┬───────────────┘
                                  │
                                  v
               ┌─────────────────────────────────┐
               │  Stage 0: Site targeting        │
               │  app_pipeline._run_pipeline()   │
               │  - Parse GeoJSON (json.loads)   │
               │  - Set UTM origin (D-06)        │
               │  - Create metric-square site    │
               │  - Set active site override     │
               └─────────────┬───────────────────┘
                             │
                             v
               ┌─────────────────────────────────┐
               │  Stage 1: NSGA-II Optimization  │
               │  optimizer.run_optimisation()    │
               │  SURROGATE-ONLY: no SDK calls   │
               │  Objectives:                    │
               │    F1 = thermal_relief x        │
               │         cooling_score_weight    │
               │    F2 = ecological_score        │
               │  Constraint: total_cost <=      │
               │              budget             │
               │  POP_SIZE=60, N_GEN=60          │
               └─────────────┬───────────────────┘
                             │
                             v
               ┌─────────────────────────────────┐
               │  Stage 2: Top-3 Selection       │
               │  optimizer.select_top3()        │
               │  MAX_THERMAL_RELIEF (rank 1)    │
               │  MAX_ECOLOGICAL (rank 2)        │
               │  BALANCED (rank 3)              │
               │  Pareto dedup + padding         │
               └─────────────┬───────────────────┘
                             │
                             v
               ┌─────────────────────────────────┐
               │  Stage 3: Infrared Validation   │
               │  validate_top3_with_infrared()  │
               │  SimBudget(max_live_calls=3)    │
               │  1 baseline + 3 interventions   │
               │  mock / cached / live dispatch  │
               │  Attaches: delta_utci_c,        │
               │  heat_stress_area_removed_m2,   │
               │  cooled_footprint_m2            │
               └─────────────┬───────────────────┘
                             │
                             v
               ┌─────────────────────────────────┐
               │  Stage 4: TOPSIS Ranking        │
               │  optimizer.topsis_rank()        │
               │  Primary: EUR/degC ascending    │
               │  Tie-break: TOPSIS closeness    │
               │  Weights: w_thermal, w_eco      │
               │  Recompute KPI with edited      │
               │  cost table if provided         │
               └─────────────┬───────────────────┘
                             │
                             v
               ┌─────────────────────────────────┐
               │  Stage 5: Output                │
               │  save_outputs()                 │
               │  top3_configurations.json       │
               │  audit_record.json              │
               │  pareto_front.png (best-effort) │
               └─────────────────────────────────┘
```

### Entry Points

Three entry points invoke this pipeline, sharing `optimizer.run_optimisation()` / `select_top3()` / `validate_top3_with_infrared()` / `topsis_rank()`:

| Entry Point | File | Use Case |
|---|---|---|
| `main()` | `coolspend/main.py` (159 lines) | CLI batch -- `python -m coolspend.main` |
| `run_decision()` | `coolspend/app_pipeline.py` (466 lines) | UI-agnostic orchestrator -- called by Gradio |
| `build_demo().launch()` | `coolspend/app.py` (434 lines) | Gradio web UI -- `python -m coolspend.app` |

The CLI and Gradio paths converge through `app_pipeline.run_decision()` whose `_run_pipeline()` private method runs stages 0-5.

## Design Patterns

### Pipeline Pattern
The dominant pattern. Data flows unidirectionally through stages; each stage enriches the result dict with additional keys. Defined in `app_pipeline._run_pipeline()` which calls optimizer functions in sequence. The CLI `main()` similarly stages with print statements between each.

### Strategy Pattern (Backend Selection)
`coolspend/sdk_client.py` defines three backends with identical interfaces but different implementations:
- **mock** (default): `_mock_baseline_utci()` / `_mock_intervention_utci()` -- synthetic scalar values
- **cached**: reads from `CACHE_DIR / {metric_key}_{ghash}.json` -- replay offline
- **live**: `_live_utci()` -- real `infrared_sdk.InfraredClient.run_area_and_wait()`

Selection is via `INFRARED_BACKEND` env var, dispatched in `_dispatch()` (`sdk_client.py:507-557`).

### Factory Method (Cost Table Loading)
`cost_model.load_cost_table()` returns a `(CostTable, GrowthDiscountParams)` tuple from JSON. `cost_table_from_dict()` validates and falls back to defaults per-field. This allows the Gradio UI to build edited tables from slider values.

### Value Object (Dataclasses)
Key data types are frozen/immutable dataclasses:
- `CostLine` (frozen) -- single cost item
- `CostTable` -- collection of CostLines with aggregators
- `GrowthDiscountParams` -- editable growth/discount parameters
- `Species` (frozen) -- per-species attributes
- `UTCIResult` -- mock/cached/live UTCI scalar result with disclaimer

### Elementwise Problem (pymoo)
`TreeBudgetProblem` (line 147-198 of `optimizer.py`) extends `pymoo.core.problem.ElementwiseProblem`. Each chromosome evaluation calls `_evaluate()` on one individual at a time -- pure surrogate (no SDK calls). Uses SBX crossover, PM mutation, FloatRandomSampling.

### Guard Pattern (SimBudget)
`coolspend/sdk_client.SimBudget` (`sdk_client.py:121-156`) caps live API calls at runtime. Raises `RuntimeError` if `max_live_calls` is exceeded. Enforces the architectural invariant: live calls only in `validate_top3_with_infrared`, never in the NSGA-II hot path.

### Fail-Open / Fail-Closed
- **Fail-closed**: `assert_crs_roundtrip()` raises `CRSConsistencyError` if WGS84->UTM->WGS84 round-trip exceeds 1 m tolerance (D-07). Blocks live SDK calls.
- **Fail-open**: `load_cost_table()` returns defaults if JSON is missing. `render_before_after()` falls back to default site fixture. `plot_pareto()` logs warning if matplotlib absent. `canopy_height_m()` returns None on raster failure.

### Template Method (Pipeline with Result Builders)
`app_pipeline._run_pipeline()` calls private result builder functions at the end: `_build_before_after()`, `_build_headline()`, `_build_disclaimer()`. These produce the structured result dict fields.

## Key Abstractions

### Optimizer Core

**`TreeBudgetProblem`** (`optimizer.py:147-198`)
- Extends `ElementwiseProblem` from pymoo
- 3*N_TREES = 36 decision variables (24 x_m/y_m floats + 12 species-selector floats)
- 2 objectives (F1=-thermal_relief, F2=-ecological_score), 1 inequality constraint (budget)
- `_evaluate()` calls surrogate only -- zero SDK imports
- Decision-variable bounds dynamically follow `spatial_engine.SITE_WIDTH_M / SITE_DEPTH_M`

**`decode()`** (`optimizer.py:93-126`)
- Chromosome decoder: converts flat float vector to `{trees: [...], tree_count}`
- Supports species-aware (3*N) and legacy (2*N) layouts
- Each tree slot: x_m, y_m, species (from `bcn_species.SPECIES_TABLE`), active flag

**`run_optimisation()`** (`optimizer.py:204-256`)
- Pins site origin via `_se.ensure_site_origin()` first (critical for determinism)
- Constructs TreeBudgetProblem, NSGA2 algorithm, runs pymoo.minimize

### Spatial Engine

**`spatial_engine.py`** (923 lines) -- single CRS boundary, collision detection, thermal surrogate

Core primitives:
- `latlon_to_local_m()` / `local_m_to_latlon()` (lines 292-343) -- THE ONLY CRS conversion functions (SPATIAL-03). Use UTM-31N (EPSG:32631) via pyproj Transformers.
- `assert_crs_roundtrip()` (lines 349-394) -- fail-closed guard, raises `CRSConsistencyError` if >1 m
- `load_site()` (lines 405-502) -- GeoJSON-to-shapely loader with caching
- `is_valid_location()` (lines 508-551) -- shapely collision gate (inside boundary, not in building, not near street)

Thermal surrogate (OPT-02 hot path):
- `delta_tmrt_surrogate()` (lines 801-848) -- linear analytical proxy, capped at `MAX_TMRT_REDUCTION_C=12.0`
- `thermal_relief()` (lines 851-898) -- site-averaged delta Tmrt for a config
- `core_weighted_coverage_fraction()` (lines 667-736) -- REMEDIATION Option A: core-concentration + spread blend

Per-site state:
- `SITE_WIDTH_M` / `SITE_DEPTH_M` -- mutable module-level floats, updated by `set_site_origin_from_polygon()`
- `_SITE_ORIGIN_E` / `_SITE_ORIGIN_N` -- UTM-31N SW corner of polygon bbox
- `_ACTIVE_SITE` -- override dict for "scan anywhere" (avoids clobbering by default fixture)
- `reset_site_origin()` -- clears all per-site state (called between tests and after anywhere-runs)

### Cost Model

**`CostTable`** / **`CostLine`** (`cost_model.py:117-161`)
- Itemized lifecycle cost: 5 CapEx lines + 1 OpEx line
- `capex_total()` = sum of capex lines (~3,000 EUR/tree)
- `opex_per_year()` = sum of opex lines (~180 EUR/tree/yr)
- `per_tree_cost(horizon)` = capex + opex * horizon

**`GrowthDiscountParams`** (`cost_model.py:320-351`)
- `ramp_years` (25), `initial_fraction` (0.20), `discount_rate` (0.035), `horizon_years` (40)
- Editable via Gradio inputs in `app.py` accordion

**`cost_per_utci_degree()`** (`cost_model.py:690-969`)
- KPI metric dict with `value`, `value_lo`, `value_hi`, `unit`, `confidence`, `sources`, `note`
- Routes through UTCI-hours (D-08), never raw Tmrt
- Prefer-measured rule: uses `delta_utci_c` from Infrared when positive
- Applies growth-horizon discount to both numerator and denominator
- Returns interval, never bare point estimate (D-10 / VALID-04)
- Returns `value=None` for zero/negative delta (honest zero-guard)

### SDK Client

**`UTCIResult`** (`sdk_client.py:84-116`) -- dataclass with `utci_c`, `metric`, `backend`, `geometry_hash`, `disclaimer`, `source`, `heat_stress_area_m2`, `merged_grid`

**`SimBudget`** (`sdk_client.py:121-156`) -- live-call guard with `record(label)` that logs + increments; raises `RuntimeError` past cap

**`_live_utci()`** (`sdk_client.py:328-501`) -- full Infrared SDK integration:
- Lazily imports `infrared_sdk` (module importable offline)
- Fetches site context once per polygon (buildings, ground materials, weather) with process-level caching via `_AREA_CTX_CACHE` / `_WEATHER_CACHE`
- Converts placed trees to vegetation GeoJSON Points via `_trees_to_vegetation()`
- Calls `InfraredClient.run_area_and_wait()` with Location, TimePeriod, weather_data
- Post-processes merged_grid: nanmean for scalar, heat-stress-area, cooled-footprint grid diff

**`_dispatch()`** (`sdk_client.py:507-557`) -- routes to mock/cached/live based on env var. Writes results to cache for future cached replay.

### Rules Engine

**`ecological_score()`** (`rules_engine.py:173-217`) -- combined score in [0,1]:
- 50% spacing penalty (RULES-01): Euclidean distance between tree pairs
- 50% species diversity (RULES-02): Shannon index normalised by ln(n_distinct)
- Pure, deterministic, offline -- no SDK, no file I/O, no global state

### Calibration

**`run_calibration_study()`** (`calibration.py:207-313`) -- compares surrogate predictions against real Infrared UTCI across 10 coverage-swept configs. Computes RMSE, R-squared, 95% empirical band, rank stability (Spearman + Kendall + set-overlap). Uses separate SimBudget (n+1 calls, not the Top-3 cap). LIVE-THEN-CACHE procedure (D-01): run once live to record fixtures, replay cached offline.

### Real Barcelona Data

**`bcn_species.Species`** (`bcn_species.py:33-44`) -- per-species frozen dataclass with scientific name, crown diameter (Verd Urba band midpoint), height, leaf cycle, shade density, cooling proxy score

**`bcn_data.py`** -- Open Data BCN CKAN client: `resolve_resource()`, `download_inventory()`, `load_trees()`, `species_frequency()`. 30-day disk cache. 145k+ street trees.

**`bcn_lidar.py`** -- ICGC+CREAF LiDAR canopy height: `canopy_height_m()` samples a 166 MB local raster for existing-canopy context. Returns None on NoData/0.

## Data Flow

### Data movement through modules

```
User input
  |  geojson_text, budget_eur, weights, backend, cost_line_values
  v
app.py:on_submit()                            -- parses GeoJSON, assembles edited CostTable
  |  calls app_pipeline.run_decision(...)
  v
app_pipeline.run_decision()                    -- env setup, SDK log capture, GeoJSON parse
  |  calls _run_pipeline(...)
  v
_run_pipeline()
  +--  Stage 0:                               app_pipeline line 293-305
  |   center_lonlat -> square_ring_lonlat -> set_site_origin_from_polygon -> set_active_site
  |
  +--  Stage 1: run_optimisation()            optimizer line 204-256
  |   +-- ensure_site_origin()               spatial_engine line 240-251
  |   +-- TreeBudgetProblem()                 optimizer line 147-198
  |   |   _evaluate() calls:
  |   |     decode(x)                         optimizer line 93-126
  |   |     thermal_relief(cfg)               spatial_engine line 851-898
  |   |       core_weighted_coverage_fraction()  spatial_engine line 667-736
  |   |       delta_tmrt_surrogate()               spatial_engine line 801-848
  |   |     ecological_score(cfg)             rules_engine line 173-217
  |   |       spacing_penalty()               rules_engine line 81-114
  |   |       species_diversity_score()       rules_engine line 121-167
  |   |     total_cost(cfg)                   cost_model line 675-687
  |   +-- pymoo.minimize() -> Result
  |
  +--  Stage 2: select_top3(result)           optimizer line 262-352
  |   +-- decode(X[idx]) for 3 Pareto indices
  |   +-- thermal_relief() + ecological_score() for each
  |
  +--  Stage 3: validate_top3_with_infrared   optimizer line 464-544
  |   +-- _build_baseline_geometry()          optimizer line 424-458
  |   +-- get_baseline_utci(geometry)         sdk_client line 563-569
  |   |   +-- _dispatch() -> mock/cached/live
  |   +-- For each config:
  |   |   _config_to_geometry(cfg)            optimizer line 358-418
  |   |     core_weighted_coverage_fraction()
  |   |     local_m_to_latlon() x 4           (site polygon corners)
  |   |     local_m_to_latlon() x n           (per-tree positions)
  |   |   get_intervention_utci(geom)         sdk_client line 572-579
  |   Attach: delta_utci_c, heat_stress_area_removed_m2, cooled_footprint_m2
  |
  +--  Stage 4: topsis_rank(top3, weights)    optimizer line 550-645
  |   +-- cost_per_utci_degree(cfg)           cost_model line 690-969
  |   |   +-- utci_hours_above(32, cov)       nature_metrics package
  |   |   +-- discounted_lifetime_degc()
  |   |   +-- discounted_total_cost()
  |   |   +-- Returns KPI dict with interval [lo, hi]
  |   +-- total_cost(cfg)                     cost_model line 675-687
  |   +-- TOPSIS on [delta_utci_c, ecological_score]
  |
  +--  Stage 4b: Recompute KPI with edited cost table (if provided)
  |
  +--  Stage 4c: Capture WGS84 geometry      optimizer._config_to_geometry()
  |   trees_lonlat + polygon_lonlat on each config
  |
  +--  Stage 5: Build result dict
  |   _build_before_after(), _build_headline(), _build_disclaimer()
  +--  Returns {configurations, before_after, headline, backend, disclaimer, call_log, ...}
```

### Module Dependency Graph

```
coolspend/
  __init__.py              -- no deps
  main.py                  -- optimizer, sdk_client (SimBudget)
  app.py                   -- app_pipeline, app_viz, cost_model, spatial_engine (DEFAULT_SITE)
  app_pipeline.py          -- cost_model, optimizer, sdk_client (SimBudget), spatial_engine
  app_viz.py               -- spatial_engine (load_site, SITE_WIDTH_M, SITE_DEPTH_M)
  optimizer.py             -- spatial_engine, rules_engine, cost_model, bcn_species
  spatial_engine.py        -- shapely, pyproj (stdlib: json, math)
  rules_engine.py          -- spatial_engine (SITE_WIDTH_M, SITE_DEPTH_M, STREET_BUFFER_M)
  cost_model.py            -- spatial_engine (core_weighted_coverage_fraction), nature_metrics
  sdk_client.py            -- bcn_species (get_species), spatial_engine (TREE_CANOPY_RADIUS_M, assert_crs_roundtrip, latlon_to_local_m)
  calibration.py           -- optimizer, sdk_client, spatial_engine, cost_model (HOURS_PER_DEGC_REF), nature_metrics
  bcn_data.py              -- requests, csv
  bcn_lidar.py             -- rasterio, requests
  bcn_species.py           -- math, dataclasses
```

Layer diagram:
```
app.py / main.py (UI/CLI layer)
    |
app_pipeline.py (orchestration layer)
    |
    +-- optimizer.py (optimization / ranking)
    |    +-- spatial_engine.py (geometry / surrogate / CRS)
    |    +-- rules_engine.py (ecological scoring)
    |    +-- cost_model.py (cost model / KPI)
    |    +-- bcn_species.py (species attributes / cooling proxy)
    |
    +-- sdk_client.py (Infrared API boundary)
    |    +-- bcn_species.py (species -> vegetation GeoJSON)
    |
    +-- app_viz.py (visualization)
    |    +-- spatial_engine.py (load_site)
    |
    +-- calibration.py (honesty / RMSE)
         +-- optimizer.py (_config_to_geometry)
         +-- sdk_client.py (get_baseline_utci, get_intervention_utci)
         +-- cost_model.py (HOURS_PER_DEGC_REF)

bcn_data.py (Open Data BCN CKAN)
bcn_lidar.py (ICGC+CREAF LiDAR raster)
```

## State Management

### Per-request state (ephemeral, in-memory)

| State | Location | Lifetime |
|---|---|---|
| `call_log` list | `app_pipeline.run_decision()` | Single run |
| `SimBudget` instance | `_run_pipeline()` | Single run |
| Captured `coolspend.sdk_client` logger handler | `_CaptureHandler` added/removed in `run_decision()` | Single run |
| `INFRARED_BACKEND` env var override | `run_decision()` try/finally | Single run |

### Module-level mutable state

| State | Default | Set by | Purpose |
|---|---|---|---|
| `spatial_engine.SITE_WIDTH_M` | 60.0 | `set_site_origin_from_polygon()` | Per-site E-W extent (m) |
| `spatial_engine.SITE_DEPTH_M` | 42.0 | `set_site_origin_from_polygon()` | Per-site N-S extent (m) |
| `spatial_engine._SITE_ORIGIN_E` | None | `set_site_origin_from_polygon()` | UTM-31N easting of SW corner |
| `spatial_engine._SITE_ORIGIN_N` | None | `set_site_origin_from_polygon()` | UTM-31N northing of SW corner |
| `spatial_engine._ORIGIN_INITIALIZED` | False | `_ensure_origin_initialized()` | Lazy-init flag |
| `spatial_engine._ACTIVE_SITE` | None | `set_active_site()` | Open-square site override |
| `spatial_engine._SITE_RECT_CACHE` | {} | `_site_rectangle()` | Cached site rectangle Polygon |
| `spatial_engine._CORE_RECT_CACHE` | {} | `_core_rectangle()` | Cached core sub-rectangle Polygon |
| `spatial_engine._SITE_CACHE` | {} | `load_site()` | Site fixture cache (keyed by path) |
| `sdk_client._AREA_CTX_CACHE` | {} | `_live_utci()` | Site context (buildings, ground) per polygon |
| `sdk_client._WEATHER_CACHE` | {} | `_live_utci()` | Weather data per lat/lon centroid |

### Process-level caching (disk)

| Cache directory | Content | Cleared by |
|---|---|---|
| `coolspend/cache/infrared/` | UTCIResult JSON by metric+hash | Manual |
| `coolspend/cache/bcn_data/` | Resolved CKAN resources + inventory CSV (30-day TTL) | Manual / TTL expiry |
| `coolspend/cache/bcn_lidar/` | 166 MB LiDAR raster + per-point height cache | Manual |

### Gradio session state

Gradio Blocks manages session state internally. The app uses:
- **No explicit session state** -- `on_submit()` receives all inputs as arguments, returns all outputs as tuples. Each run is stateless from the UI perspective.
- Module-level shipped defaults `_SHIPPED_COST_TABLE` / `_SHIPPED_GD` loaded once at import in `app.py` (line 72).
- `_DEFAULT_POLYGON_TEXT` loaded once from `DEFAULT_SITE` fixture at import (line 67).

### Determinism

- Seed 42 pinned for NSGA-II and calibration study config generation
- `decode()` is deterministic for a given chromosome
- Surrogate functions (`thermal_relief`, `ecological_score`, `delta_tmrt_surrogate`) are pure functions of their inputs
- `reset_site_origin()` called between runs to prevent mutable-state contamination
- `conftest.py` autouse fixture calls `reset_site_origin()` before every test

## Error Handling Strategy

### Pipeline error handling

Errors in `_run_pipeline()` are caught by a top-level `try/except Exception` (line 384), which returns an error dict:
```python
{"configurations": [], "before_after": {}, "headline": "", "backend": backend,
 "disclaimer": "", "call_log": [...], "site_path": site_path,
 "error": f"Pipeline error: {exc}"}
```

The Gradio UI callback `on_submit()` catches its own outer exception (line 168) and shows a generic error to the UI (T-03-09).

### Fallback patterns

| Failure | Behavior | Fallback |
|---|---|---|
| GeoJSON unparseable | `ValueError` caught, returns error dict | User sees error message |
| Site fixture missing | `FileNotFoundError` from `load_site()` | Caught by `_load_site_safe()` in viz |
| Rasterio missing | `canopy_height_m()` returns None | Site context degrades gracefully |
| matplotlib missing | `plot_pareto()` logs warning | Pipeline continues, no PNG |
| cost_config.json missing | `load_cost_table()` logs warning | Returns DEFAULT_COST_TABLE |
| SimBudget exceeded | `RuntimeError` raised | Propagates to pipeline error dict |
| CRS round-trip >1m | `CRSConsistencyError` raised | Live call aborted (fail-closed) |
| Ground materials fetch fails | Logs warning, proceeds without | Uses empty ground_layers dict |
| Weather stations not found | `RuntimeError` raised | Propagates to pipeline error |

### Threat mitigation (T-03-x / Security)

- T-03-01: GeoJSON parsed via `json.loads` only -- no eval/exec
- T-03-02: `SimBudget(max_live_calls=3)` caps live SDK calls per run
- T-03-03: `INFRARED_API_KEY` never read, logged, or written in `app_pipeline.py`
- T-03-05: API key never referenced in `app.py` -- only backend name shown
- T-03-07: SimBudget cap enforced inside `run_decision()`
- T-03-08: Mock backend always surfaces "NOT MEASURED DATA" in disclaimer
- T-03-09: `on_submit()` shows generic error to UI; full traceback logged server-side only
- T-05-08: Calibration artifact JSON written with no secrets

## Configuration

### Environment variables

| Variable | Default | Used by | Purpose |
|---|---|---|---|
| `INFRARED_BACKEND` | "mock" | `sdk_client._backend()` | Backend selection |
| `INFRARED_API_KEY` | (none) | `sdk_client._live_utci()` | Infrared SDK auth |
| `GRADIO_SERVER_NAME` | "127.0.0.1" | `app.py` launch | Gradio server host |
| `GRADIO_SERVER_PORT` | "7860" | `app.py` launch | Gradio server port |
| `GRADIO_SHARE` | "" | `app.py` launch | Create public link |

### Configuration files

| File | Format | Purpose |
|---|---|---|
| `coolspend/cost_config.json` | JSON | Editable per-city cost table (6 lines + growth/discount params) |
| `coolspend/data/angels_site.geojson` | GeoJSON | Default bundled site fixture (Plaça dels Angels) |
| `requirements.txt` | pip | Dependency pins for HF Spaces |

### Hardcoded constants (DECLARED, need local verification)

Key strategic constants. All tagged with source/status in the code (DECLARED, PENDING, REQUIRES_VERIFICATION):

| Constant | Value | Module | Status |
|---|---|---|---|
| `MAX_TMRT_REDUCTION_C` | 12.0 | `spatial_engine.py` | UNSOURCED cap |
| `TREE_SHADE_FRACTION` | 0.80 | `spatial_engine.py` | DECLARED |
| `TREE_CANOPY_RADIUS_M` | 3.0 | `spatial_engine.py` | DECLARED |
| `MAX_SITE_COVERAGE` | 0.90 | `spatial_engine.py` | DECLARED |
| `CAPEX_PER_TREE_EUR` | 3000.0 | `cost_model.py` (derived) | DECLARED/PENDING |
| `OPEX_PER_TREE_YEAR_EUR` | 180.0 | `cost_model.py` (derived) | PENDING (US anchor) |
| `OPEX_HORIZON_YEARS` | 40 | `cost_model.py` | DECLARED |
| `STUDY_SEED` / `SEED` | 42 | `calibration.py` / `optimizer.py` | Deterministic |
| `UTCI_HEAT_STRESS_C` | 26.0 | `sdk_client.py` | Moderate threshold |
| `HOURS_PER_DEGC_REF` | 200.0 | `cost_model.py` | DERIVED, REQUIRES_VERIFICATION |

---

*Architecture analysis: 2026-05-27*
