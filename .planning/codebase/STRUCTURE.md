# Codebase Structure

**Analysis Date:** 2026-06-01

## Directory Layout

```
Hackathon/
├── coolspend/              # Python computational core + FastAPI service (the system)
│   ├── *.py                # ~40 source modules (placement, ecology, cost, citywide, sdk_client…)
│   ├── tests/              # pytest suite (~40 test_*.py + conftest.py)
│   ├── data/               # site GeoJSONs + calibration_summary.json
│   ├── docs/               # domain knowledge bases + datasheets (markdown)
│   ├── cost_config.json    # itemised cost table (loaded by cost_model.py)
│   └── (cache/ at runtime) # cached Infrared results, keyed by geometry hash
├── web/                    # deck.gl/Mapbox React + TypeScript + Vite client
│   ├── src/                # App.tsx, components/, lib/, data/, styles/
│   └── public/             # served bundles: web_bundle/, eval_bundle/, scored_grid.geojson, citywide_plan.json
├── L1_INGEST_data/         # upstream ingested data (scored_grid lives here)
│   ├── data_for_all/       # scored_grid.geojson (494 cells) + shared inputs
│   ├── climate/            # EPW / climate inputs
│   └── README.md           # provenance README per artifact
├── video/                  # Remotion explainer video project (out-of-band of the core)
├── tools/                  # utility scripts (e.g. transcribe.py)
├── PAPER.md                # full APA-7 paper (Section 5 = system architecture)
├── README.md, DATA_SOURCES.md, MOCKS.md
└── requirements.txt        # Python deps
```

## Directory Purposes

**`coolspend/`:**
- Purpose: the entire computational core and the HTTP service.
- Contains: ~40 `*.py` modules (see module map below), `tests/`, `data/`, `docs/`, `cost_config.json`.
- Key files: `api_server.py`, `app_pipeline.py`, `smart_placement.py`, `citywide.py`, `sdk_client.py`.

**`web/src/`:**
- Purpose: React/TypeScript client.
- Contains: `App.tsx`, `main.tsx`, `components/`, `lib/`, `data/`, `styles/`, `vite-env.d.ts`.
- Key files: `App.tsx` (phase machine), `components/Scene.tsx` / `DeckOverlay.tsx` / `CitywidePanel.tsx` / `TreeInspect.tsx`, `lib/api.ts`, `lib/bundle.ts`, `lib/layers.ts`, `lib/growth.ts` (mirrors `coolspend/growth.py`).

**`web/public/`:**
- Purpose: static artifacts served at the web root.
- Contains: `web_bundle/` (curated showcase), `eval_bundle/` (live `/api/evaluate` output), `scored_grid.geojson`, `citywide_plan.json`. Each bundle = `decision.json`, `boundary.geojson`, `trees.geojson`, `bounds.json`, `scene.glb`.
- Generated: yes (bundles written by `export_web.py` / the API). Committed: yes (showcase + precomputed plan).

**`L1_INGEST_data/`:**
- Purpose: upstream ingested data products consumed by the core.
- Contains: `data_for_all/scored_grid.geojson` (the 494-cell vulnerability grid, loaded by `citywide.py` via `_SCORED_GRID = L1_INGEST_data/data_for_all/scored_grid.geojson`), `climate/`, and a provenance `README.md`.

**`coolspend/docs/`:**
- Purpose: domain knowledge bases + provenance datasheets.
- Key files: `scored_grid_datasheet.md`, `species_ecology_traits.md`, `bcn_planting_strategy.md`, `depaving_practice.md`, `placement_spatial_constraints.md`, `limitations_remediation_design.md`.

**`coolspend/data/`:**
- Purpose: fixture site geometry + calibration outputs.
- Key files: `angels_plaza_site.geojson`, `angels_site.geojson`, `calibration_summary.json`.

## Key File Locations

**Entry Points:**
- `coolspend/api_server.py`: FastAPI service (all `/api/*` endpoints).
- `coolspend/main.py`, `coolspend/app.py`: CLI / app entry.
- `web/src/main.tsx`: web client bootstrap.

**Configuration:**
- `coolspend/cost_config.json`: cost table.
- `requirements.txt`: Python deps. `web/` has its own `package.json`/Vite config.
- Env: `INFRARED_BACKEND` (mock|cached|live), `INFRARED_API_KEY`, web `VITE_MAPBOX_TOKEN`.

**Core Logic:**
- `coolspend/app_pipeline.py`: `smart_evaluate` + `run_decision` orchestration.
- `coolspend/smart_placement.py`: deployed greedy engine.
- `coolspend/citywide.py`: multi-site allocator.
- `coolspend/sdk_client.py`: Infrared boundary + three-tier backend.

**Testing:**
- `coolspend/tests/`: ~40 `test_*.py` (e.g. `test_smart_placement.py`, `test_citywide.py`, `test_shade_gain_placement.py`, `test_placement_audit.py`, `test_provenance.py`).

## Module Map (`coolspend/*.py`)

| Module | Responsibility |
|---|---|
| `candidate_slots.py` | `generate_slots` — 4 m lattice of validated planting slots (building/street/spacing exclusions, planter vs in-ground). |
| `placement_inputs.py` | `assemble_inputs`, `build_demand_cells`, `run_smart_placement` — demand field (live UTCI or proxy) + placement driver; `requires_utility_survey` flag. |
| `smart_placement.py` | `place_trees_greedy` — deployed budgeted weighted-max-coverage greedy. |
| `shade_proxy.py` | ray-cast shade-gain (fraction of sampled July suns whose crown shadow hits a cell). |
| `sdk_client.py` | Infrared boundary; three-tier dispatch; `SimBudget`; `cooled_footprint_m2`/`cooled_footprint_profile`; `get_baseline_utci`/`get_intervention_utci`. |
| `ecology.py` | `is_plantable` gate + ecosystem-health composite (single species source of truth). |
| `bcn_species.py` | 12-species candidate table (crown/height bands from the inventory). |
| `growth.py` | Chapman–Richards crown growth (mirrored in `web/src/lib/growth.ts`). |
| `cost_model.py` | cost table (`cost_config.json`), CapEx/OpEx, discounting, `hours_per_degc`. |
| `citywide.py` | `allocate_citywide` — multi-site €1M allocator over the 494-cell grid. |
| `population.py` | population-served (300 m catchment, EPSG:25831, de-duplicated union). |
| `design_metrics.py` | canopy area/cover, person-degrees, estimated air-temp drop. |
| `app_pipeline.py` | `smart_evaluate` (single-site chain) + `run_decision` orchestration. |
| `api_server.py` | FastAPI HTTP service. |
| `export_web.py` | `export_web_bundle` — writes the self-contained web bundle. |
| `optimizer.py` | NSGA-II alternative (benchmark only, not deployed). |
| `spatial_engine.py` | coordinate frame + `delta_tmrt_surrogate` (surrogate, used only by NSGA-II path). |
| `calibration.py` | live calibration study (±0.78 °C band). |
| `cooling_estimator.py` | three-tier `CoolingEstimator` (mock scalar → shade proxy → measured UTCI). |
| `provenance.py` | reproduces `composite_score_B` weight vector (R² = 1.0). |
| `placement_audit.py` | independent OSM re-check that no tree lands on a building. |
| `sensitivity.py` | sensitivity testing of the ecology weights. |
| `osm_buildings.py`, `osm_roads.py`, `osm_features.py` | OSM building / road / furniture geometry (Overpass, cached). |
| `ground_analysis.py` | impervious / ground-material analysis. |
| `bcn_data.py`, `bcn_lidar.py` | Barcelona municipal data / LiDAR inputs. |
| `epw_weather.py` | EPW weather (TMYx) machinery for the hours-per-°C constant. |
| `rules_engine.py`, `sites.py`, `app.py`, `app_3d.py`, `app_viz.py`, `main.py` | rules, site defs, CLI/viz/3D apps. |

## PAPER.md Section 5 module-claim verification

Every module named in PAPER.md Section 5 **exists** in `coolspend/`, and the named functions/classes resolve:

- `candidate_slots.py` ✓ (function is `generate_slots`, not `generate_candidate_slots`)
- `placement_inputs.py` ✓ (`assemble_inputs`, `build_demand_cells`)
- `smart_placement.py` ✓ — `place_trees_greedy`
- `shade_proxy.py` ✓
- `sdk_client.py` ✓ — `SimBudget`, `cooled_footprint_m2`
- `ecology.py` ✓ — `is_plantable`
- `bcn_species.py` ✓
- `growth.py` ✓
- `cost_model.py` ✓ — `hours_per_degc`
- `citywide.py` ✓ — `allocate_citywide`
- `population.py` ✓
- `app_pipeline.py` ✓ — `smart_evaluate`
- `api_server.py` ✓
- `export_web.py` ✓ — `export_web_bundle`
- `optimizer.py`, `spatial_engine.py` (`delta_tmrt_surrogate`), `calibration.py`, `cooling_estimator.py`, `provenance.py`, `design_metrics.py`, `placement_audit.py`, `sensitivity.py` ✓

**No PAPER.md-named module is missing.** Path/naming flags to note:
- PAPER references `docs/scored_grid_datasheet.md`; the file actually lives at `coolspend/docs/scored_grid_datasheet.md`.
- PAPER's prose says `scored_grid` is in-repo; it is loaded from `L1_INGEST_data/data_for_all/scored_grid.geojson` (`citywide.py:42`), with a separate served copy at `web/public/scored_grid.geojson`. There is no top-level `data/` dir — data lives under `coolspend/data/` and `L1_INGEST_data/`.
- `web/src/lib/growth.ts` confirmed present, mirroring `coolspend/growth.py` as PAPER claims.

## Naming Conventions

**Files:**
- Python: `snake_case.py`; tests `test_<module>.py` in `coolspend/tests/`.
- Web: components `PascalCase.tsx`, libs `camelCase.ts`, co-located `*.test.ts`.

**Directories:**
- lowercase; ingested data prefixed `L1_INGEST_`.

## Where to Add New Code

**New core computation / pipeline stage:**
- Implementation: new `coolspend/<feature>.py`; wire into `app_pipeline.smart_evaluate` or `citywide.allocate_citywide`.
- Tests: `coolspend/tests/test_<feature>.py`.

**New HTTP endpoint:**
- Add to `coolspend/api_server.py` with a Pydantic request model.

**New web layer / panel:**
- Component: `web/src/components/`; deck.gl layer logic: `web/src/lib/layers.ts`; API call: `web/src/lib/api.ts`.

**Shared cost / species / ecology constants:**
- `coolspend/cost_config.json` (costs), `coolspend/ecology.py` (ecology weights — single source of truth), `coolspend/bcn_species.py` (species table).

## Special Directories

**`web/public/eval_bundle/` and `web/public/web_bundle/`:**
- Purpose: rendered result bundles (`eval_bundle` = live user runs; `web_bundle` = curated showcase).
- Generated: yes. Committed: yes (kept separate so a user run can't overwrite the demo).

**`coolspend/cache/` (runtime):**
- Purpose: cached Infrared UTCI/building results keyed by SHA-256 geometry hash for the `cached` tier.
- Generated: yes (written by the `live` tier). Committed: cached non-proprietary artifacts only.

---

*Structure analysis: 2026-06-01*
