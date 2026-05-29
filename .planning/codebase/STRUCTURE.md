# Codebase Structure

**Analysis Date:** 2026-05-27

## Directory Layout

```
Hackathon/
+-- .planning/                         # Project planning artifacts (phases, config, analysis)
|   +-- codebase/                      # Codebase analysis docs (this file)
|   +-- phases/                        # 6 phase directories with PLAN/SUMMARY/VERIFICATION files
|   +-- config.json                    # Project phase configuration
|   +-- PROJECT.md                     # Project definition
|   +-- REQUIREMENTS.md                # Requirements document
|   +-- ROADMAP.md                     # Implementation roadmap
|   +-- STATE.md                       # Current state document
+-- coolspend/                         # Main application package (14 Python files, ~6000 lines)
|   +-- __init__.py                    # Package marker, version 0.1.0
|   +-- app.py                         # Gradio Blocks web UI (434 lines)
|   +-- app_pipeline.py                # UI-agnostic pipeline orchestrator (466 lines)
|   +-- app_viz.py                     # Before/after site visualization (227 lines)
|   +-- bcn_data.py                    # Real Barcelona tree inventory client (178 lines)
|   +-- bcn_lidar.py                   # ICGC+CREAF LiDAR canopy height (129 lines)
|   +-- bcn_species.py                 # Per-species attributes + cooling proxy (124 lines)
|   +-- calibration.py                 # Surrogate ground-truth calibration study (481 lines)
|   +-- cost_config.json               # Per-city cost table config (65 lines)
|   +-- cost_model.py                  # Cost model, GrowthDiscount, KPI (1000 lines)
|   +-- main.py                        # CLI entry point (159 lines)
|   +-- optimizer.py                   # NSGA-II optimizer, Top-3 selection, ranking (937 lines)
|   +-- rules_engine.py                # Ecological-coherence scoring (262 lines)
|   +-- sdk_client.py                  # Infrared SDK boundary, SimBudget (607 lines)
|   +-- spatial_engine.py              # Geometry, CRS boundary, thermal surrogate (923 lines)
|   +-- data/                          # Fixture data
|   |   +-- angels_site.geojson        # Default site (Plaça dels Angels), hand-authored
|   +-- cache/                         # Disk cache directories
|   |   +-- bcn_data/                  # BCN tree inventory CSVs (30-day TTL)
|   |   +-- bcn_lidar/                 # LiDAR raster + per-point height cache
|   |   +-- infrared/                  # UTCIResult JSON (metric+hash keyed)
|   +-- tests/                         # 17 test files (co-located in package)
|       +-- __init__.py                # Test package marker
|       +-- conftest.py                # Shared fixtures, autouse reset_site_origin
|       +-- test_app.py                # Gradio UI tests
|       +-- test_app_pipeline.py       # Pipeline orchestrator tests
|       +-- test_app_viz.py            # Visualization tests
|       +-- test_calibration.py        # Calibration study tests
|       +-- test_coordinate_frame.py   # CRS round-trip tests
|       +-- test_cost_config.py        # Cost config loading tests
|       +-- test_cost_model.py         # Cost model/KPI tests
|       +-- test_decision_artifact.py  # Top-3 output artifact tests
|       +-- test_optimizer.py          # NSGA-II optimizer tests
|       +-- test_requirements.py       # Dependency check tests
|       +-- test_rules_engine.py       # Ecological scoring tests
|       +-- test_sdk_client.py         # SDK client tests
|       +-- test_sdk_client_live.py    # Live SDK integration tests
|       +-- test_spatial_engine.py     # Geometry/surrogate tests
|       +-- test_surrogate.py          # Thermal surrogate tests
+-- outputs/                           # Decision artifacts (gitignored?)
|   +-- audit_record.json              # Provenance trail
|   +-- pareto_front.png               # Pareto scatter plot
|   +-- top3_configurations.json       # Main decision artifact
+-- .gitignore
+-- .env                               # Environment config (secrets - NEVER read)
+-- CHANGELOG.md                       # Change history
+-- CONCEPT_REPORT.md                  # Concept report for hackathon
+-- DATA_SOURCES.md                    # Data provenance documentation
+-- DEMO_SCRIPT.md                     # Demo script for hackathon
+-- HANDOFF.md                         # Developer handoff notes
+-- MOCKS.md                           # Honesty ledger: all mock/surrogate/declared values
+-- README.md                          # Project readme with HF Spaces header
+-- REMEDIATION-SUMMARY.md             # Bug fixes and remediation summary
+-- SUBMISSION.md                      # Hackathon submission document
+-- infrared_hackathon.md              # Buildathon context document
+-- nature_architecture.md             # Partner library documentation
+-- requirements.txt                   # Pip dependencies
```

## Module Map

### Core Pipeline Modules

| Module | Lines | Key Exports | Dependencies | Role |
|---|---|---|---|---|
| `__init__.py` | 10 | `__version__` = "0.1.0" | None | Package marker |
| `main.py` | 159 | `main()` | optimizer, sdk_client.SimBudget | CLI entry point |
| `app_pipeline.py` | 466 | `run_decision()`, `parse_site_geojson()` | cost_model, optimizer, sdk_client, spatial_engine | Pipeline orchestrator |
| `optimizer.py` | 937 | `run_optimisation()`, `select_top3()`, `validate_top3_with_infrared()`, `topsis_rank()`, `save_outputs()`, `decode()` | spatial_engine, rules_engine, cost_model, bcn_species | NSGA-II optimization + ranking |
| `spatial_engine.py` | 923 | `load_site()`, `is_valid_location()`, `latlon_to_local_m()`, `local_m_to_latlon()`, `thermal_relief()`, `delta_tmrt_surrogate()`, `core_weighted_coverage_fraction()`, `set_site_origin_from_polygon()`, `assert_crs_roundtrip()` | shapely, pyproj | Geometry, CRS, thermal surrogate |
| `rules_engine.py` | 262 | `ecological_score()`, `spacing_penalty()`, `species_diversity_score()` | spatial_engine (constants) | Ecological coherence scoring |
| `cost_model.py` | 1000 | `CostTable`, `CostLine`, `GrowthDiscountParams`, `cost_per_utci_degree()`, `total_cost()`, `per_tree_cost()`, `load_cost_table()`, `cost_table_from_dict()`, `discounted_lifetime_degc()`, `discounted_total_cost()` | spatial_engine (optional), nature_metrics | Cost model + EUR/degC KPI |
| `sdk_client.py` | 607 | `UTCIResult`, `SimBudget`, `get_baseline_utci()`, `get_intervention_utci()`, `cooled_footprint_m2()` | bcn_species, spatial_engine | Infrared API boundary |

### Real Data Modules

| Module | Lines | Key Exports | Dependencies | Role |
|---|---|---|---|---|
| `bcn_species.py` | 124 | `Species`, `SPECIES_TABLE`, `cooling_score()`, `get_species()`, `cooling_score_by_name()`, `palette()` | math, dataclasses | Species attributes table |
| `bcn_data.py` | 178 | `resolve_resource()`, `download_inventory()`, `load_trees()`, `species_frequency()` | requests, csv | Open Data BCN CKAN client |
| `bcn_lidar.py` | 129 | `canopy_height_m()`, `ensure_raster()`, `site_canopy_context()` | rasterio, requests | ICGC+CREAF LiDAR canopy height |

### UI / Visualization Modules

| Module | Lines | Key Exports | Dependencies | Role |
|---|---|---|---|---|
| `app.py` | 434 | `build_demo()`, `on_submit()` | app_pipeline, app_viz, cost_model, spatial_engine | Gradio Blocks web UI |
| `app_viz.py` | 227 | `render_before_after()` | spatial_engine, matplotlib | Before/after site map PNG |

### Supporting Modules

| Module | Lines | Key Exports | Dependencies | Role |
|---|---|---|---|---|
| `calibration.py` | 481 | `run_calibration_study()`, `generate_study_configs()`, `compute_fit()`, `rank_stability()` | optimizer, sdk_client, cost_model, spatial_engine, nature_metrics | Surrogate-vs-real RMSE study |

### Configuration File

| File | Lines | Purpose |
|---|---|---|
| `coolspend/cost_config.json` | 65 | Per-city itemized cost table: 6 lines (5 CapEx + 1 OpEx) + growth/discount params. Loaded by `cost_model.load_cost_table()`. |

## Entry Points

### `coolspend/app.py` -- Gradio Web UI (HF Spaces primary entry point)

```
app_file (HF Spaces config): coolspend/app.py
```

- `build_demo()` (line 264) constructs the `gr.Blocks` UI headlessly (testable without launching).
- Module-level `demo = build_demo()` (line 423) -- HF Spaces loads this.
- `if __name__ == "__main__": demo.launch(...)` (line 425) -- local dev.
- `on_submit()` callback (line 94) receives all Gradio inputs, assembles edited CostTable, calls `app_pipeline.run_decision()`, renders results.
- Runs on port 7860 by default (configurable via env vars).

### `coolspend/main.py` -- CLI Entry Point

```
python -m coolspend.main                                   # mock backend
INFRARED_BACKEND=live INFRARED_API_KEY=<key> python -m coolspend.main  # live
```

- `main(budget_eur)` (line 46) runs the full pipeline with print-based output.
- Stages: optimize -> select_top3 -> validate_top3_with_infrared -> topsis_rank -> save_outputs.
- Writes to `outputs/top3_configurations.json`.
- Default budget: 1,000,000 EUR.

### `coolspend/app_pipeline.py` -- Orchestrator Entry Point

```python
from coolspend.app_pipeline import run_decision
result = run_decision(budget_eur=500000, weights=(0.7, 0.3),
                      geojson_text='...', backend="cached",
                      center_lonlat=(2.168, 41.390), site_size_m=120.0)
```

- `run_decision()` (line 157) sets up SDK logging capture, flips `INFRARED_BACKEND` env var, calls `_run_pipeline()`, and restores env in `finally`.
- `_run_pipeline()` (line 272) runs stages 0-5 internally.
- `parse_site_geojson()` (line 70) validates user GeoJSON via `json.loads` only (T-03-01).

## Test Structure

Tests are co-located within the package at `coolspend/tests/`. 17 test files, all offline/deterministic.

| Test File | Tests What | Key Fixtures |
|---|---|---|
| `conftest.py` | Autouse `reset_site_origin()` before every test, shared imports | Numpy, shapely, pyproj |
| `test_spatial_engine.py` | `load_site`, `is_valid_location`, `thermal_relief`, CRS round-trip, site origin | `angels_site.geojson` |
| `test_surrogate.py` | `delta_tmrt_surrogate`, `thermal_relief`, core-weighing | Sample tree configs |
| `test_rules_engine.py` | `spacing_penalty`, `species_diversity_score`, `ecological_score` | Monoculture/diverse configs |
| `test_cost_model.py` | `total_cost`, `cost_per_utci_degree`, GrowthDiscount, zero-delta guard | Sample configs |
| `test_cost_config.py` | `load_cost_table`, `cost_table_from_dict`, validation, fail-open | `cost_config.json` |
| `test_optimizer.py` | `run_optimisation`, `select_top3`, `decode`, `topsis_rank` | Via `run_optimisation()` |
| `test_decision_artifact.py` | `save_outputs`, audit record, Pareto plot | Mock pymoo Result |
| `test_sdk_client.py` | `UTCIResult`, `SimBudget`, `_dispatch`, mock/cached/live paths | Sample geometry dicts |
| `test_sdk_client_live.py` | Live SDK integration (requires INFRARED_API_KEY) | (skipped without key) |
| `test_app.py` | `build_demo()` constructs headless UI | None |
| `test_app_pipeline.py` | `run_decision`, `parse_site_geojson`, env restore | Sample GeoJSON strings |
| `test_app_viz.py` | `render_before_after` produces valid PNG | Sample config, default site |
| `test_calibration.py` | `generate_study_configs`, `run_calibration_study`, `compute_fit`, `rank_stability` | Default site |
| `test_coordinate_frame.py` | UTM-31N CRS: origin, round-trip, square_ring_lonlat, `set_site_origin_from_polygon` | Known lon/lat values |
| `test_requirements.py` | Ensures required packages importable | None |

### Fixture pattern

- `conftest.py` provides an autouse fixture that calls `spatial_engine.reset_site_origin()` before each test.
- Tests that need `load_site()` call it directly with the default `angels_site.geojson`.
- Mock UTCI geometry is built inline per test (simple dicts with `width_m` and `coverage_fraction`).
- Mock pymoo Result is constructed via `MagicMock` for `test_decision_artifact.py`.

## Data Files

### GeoJSON Fixtures

| File | Purpose | Type | Status |
|---|---|---|---|
| `coolspend/data/angels_site.geojson` | Default site boundary + buildings + streets for Placa dels Angels | GeoJSON FeatureCollection | MOCK -- hand-authored, not OSM surveyed |

### Cache Directories

| Directory | Content | Keyed By | Lifetime |
|---|---|---|---|
| `coolspend/cache/infrared/` | UTCIResult JSON files | `{metric_key}_{16-char-sha256}.json` | Manual cleanup |
| `coolspend/cache/bcn_data/` | CKAN resource metadata + inventory CSV | `resolve_{slug}.json`, `{slug}.csv` | 30-day TTL |
| `coolspend/cache/bcn_lidar/` | 166 MB LiDAR raster + per-point height | `hmitjana_2016_2017.tif`, `pt_{lat}_{lon}.json` | Manual cleanup |

### Output Files

| File | Written By | Contents |
|---|---|---|
| `outputs/top3_configurations.json` | `optimizer.save_outputs()` | Run metadata, 3 ranked configurations, before/after record (DEC-01 + DEC-02) |
| `outputs/audit_record.json` | `optimizer.write_audit_record()` | Provenance trail, surrogate flags, TOPSIS weights, data source tags |
| `outputs/pareto_front.png` | `optimizer.plot_pareto()` | Scatter plot of thermal vs ecological objectives (best-effort) |
| `outputs/calibration_study.json` | `calibration.run_calibration_study()` | RMSE, R-squared, rank stability, all config data |

## Documentation Files

| File | Purpose |
|---|---|
| `README.md` | HF Spaces header, run instructions, architecture mermaid diagram, project structure |
| `HANDOFF.md` | Developer handoff: current state, what's done, what's not done, tried-failed items |
| `MOCKS.md` | Honesty ledger: every mock/surrogate/DECLARED constant with source tag |
| `DATA_SOURCES.md` | Full provenance and field schema for Barcelona data layers |
| `CHANGELOG.md` | Change history |
| `CONCEPT_REPORT.md` | Hackathon concept report |
| `DEMO_SCRIPT.md` | Presentation demo script |
| `SUBMISSION.md` | Hackathon submission document |
| `REMEDIATION-SUMMARY.md` | Bug fixes and Option A remediation summary |
| `infrared_hackathon.md` | Infrared SDK Buildathon context |
| `nature_architecture.md` | NatureMetrics helper library documentation |

## Naming Conventions

**Files:** `snake_case.py` for all Python modules. Configuration: `kebab-case.json` (`cost_config.json`). Data: `snake_case.geojson` (`angels_site.geojson`).

**Functions:** `snake_case` for all public and private functions (e.g., `run_optimisation`, `core_weighted_coverage_fraction`, `_build_baseline_geometry`).

**Classes:** `PascalCase` (e.g., `CostLine`, `GrowthDiscountParams`, `TreeBudgetProblem`, `UTCIResult`, `SimBudget`, `Species`, `CRSConsistencyError`).

**Constants:** `UPPER_SNAKE_CASE` for module-level constants (e.g., `MAX_TMRT_REDUCTION_C`, `N_TREES`, `POP_SIZE`, `DEFAULT_BUDGET_EUR`, `HOURS_PER_DEGC_REF`).

**Types:** `Backend` as `Literal["mock", "cached", "live"]`. Type hints via `from __future__ import annotations` throughout.

**Private:** Single underscore prefix for module-internal functions and globals (e.g., `_dispatch`, `_SITE_ORIGIN_E`, `_ensure_origin_initialized`). Double underscore is not used.

## Where to Add New Code

### New Feature (e.g., to add a KPI or constraint)

1. Add calculations to the appropriate domain module (`cost_model.py`, `rules_engine.py`, `spatial_engine.py`).
2. If a new optimizer objective is needed, modify `TreeBudgetProblem._evaluate()` in `optimizer.py`.
3. Wire it through `app_pipeline._run_pipeline()` if the result needs to appear in the output dict.
4. Add UI controls in `app.py` `build_demo()` and the `on_submit()` callback.
5. Add tests in `coolspend/tests/` matching the module name (`test_{module}.py`).

### New Data Source

1. Create a new file at `coolspend/{domain}.py` (e.g., `coolspend/bcn_surface.py`).
2. Follow the `canonical import path` pattern: imports inside functions if the package is optional.
3. Add disk caching to `coolspend/cache/{source}/`.
4. Wire into `spatial_engine.py` if it feeds the surrogate, or `sdk_client.py` if it feeds the live API.
5. Add to `DATA_SOURCES.md`.

### New Backend (beyond mock/cached/live)

1. Implement the backend function in `sdk_client.py` (signature: `def _new_backend_fn(geometry: dict) -> UTCIResult`).
2. Add the backend string to `Backend` type literal.
3. Add a branch in `_dispatch()`.
4. Add tests in `test_sdk_client.py`.

### New UI Entry Point (e.g., FastAPI)

1. Create `coolspend/api.py` that calls `app_pipeline.run_decision()`.
2. Keep entry points thin -- all orchestration logic stays in `app_pipeline.py` / `optimizer.py`.

---

*Structure analysis: 2026-05-27*
