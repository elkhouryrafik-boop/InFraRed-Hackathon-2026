# Architecture

**Analysis Date:** 2026-06-01

## Pattern Overview

**Overall:** Three-tier decision-support system — a Python computational core, exposed through a FastAPI HTTP service, consumed by a deck.gl/Mapbox React (TypeScript/Vite) web client. Verified against PAPER.md Section 5 and the actual `coolspend/*.py` modules.

**Key Characteristics:**
- **Honesty architecture / three-tier Infrared backend** selected by the `INFRARED_BACKEND` env var (`mock` | `cached` | `live`), so a synthetic preview can never masquerade as a measured result. Dispatch lives in `coolspend/sdk_client.py` (`_backend()` reads `os.environ.get("INFRARED_BACKEND", "mock")`; routing at `sdk_client.py:668`+ for `cached`/`live`/`mock`).
- **Geometry-real placement on every backend** — placement depends on OSM geometry + a demand/proxy field, not on measured cooling, so it stays valid even when the cooling number is a labelled synthetic preview.
- **Deterministic core** — seed 42 through the pipeline; greedy placement tie-breaks are total (deterministic by construction).
- **Bounded live cost** — `SimBudget` (`coolspend/sdk_client.py:125`) hard-caps live Infrared calls at 3 per run; a 4th raises `RuntimeError`.
- **Separation of single-site and city-wide paths**, both of which run the *same* `smart_evaluate` chain per site.

## Layers

**Computational core (`coolspend/` Python package):**
- Purpose: all spatial computation, optimisation, ecology, costing, metrics, and the Infrared boundary.
- Location: `coolspend/`
- Contains: slot generation, demand-field assembly, greedy placement, shade proxy, species ecology, cost model, growth curves, design metrics, population served, city-wide allocator, web-bundle export.
- Depends on: OSM/Overpass (cached), `scored_grid.geojson`, municipal data, the Infrared SDK (live tier only).
- Used by: the FastAPI service and CLI/test entry points.

**Service layer (`coolspend/api_server.py`):**
- Purpose: thin FastAPI HTTP backend that makes the static web viewer interactive.
- Location: `coolspend/api_server.py`
- Contains: request models (`PolygonRequest`, `EvaluateRequest`), endpoints, server-side polygon area cap (`MAX_AREA_M2 = 62_500.0`, `MIN_AREA_M2 = 400.0`), CORS, static-file mounting.
- Depends on: `app_pipeline.smart_evaluate`/`run_decision`, `export_web.export_web_bundle`, `citywide`.
- Used by: the web client over HTTP.

**Web client (`web/src/`):**
- Purpose: render the result on a Mapbox satellite basemap with a deck.gl overlay.
- Location: `web/src/`
- Contains: React app (`App.tsx`), scene components, deck.gl layers, bundle loader, growth curve (mirrors Python), API client.
- Depends on: the FastAPI endpoints and the on-disk web bundles under `web/public/`.

## Data Flow

**Single-site path (draw → evaluate):**

1. **Draw** — user draws a capped polygon anywhere in Barcelona in the web client; the frontend mirrors the server area cap.
2. **Preview** — `POST /api/buildings` returns building count + impervious analysis for the drawn ring; **no simulation** (fast).
3. **Evaluate** — `POST /api/evaluate` runs `app_pipeline.smart_evaluate` (`coolspend/app_pipeline.py:526`):
   - `reset_site_origin()` cleans the coordinate frame.
   - **Stage 1 — smart placement** (`placement_inputs.run_smart_placement`, `placement_inputs.py:360`):
     - `assemble_inputs` (`placement_inputs.py:177`) builds candidate slots via `candidate_slots.generate_slots` (`candidate_slots.py:86`) on a 4 m lattice with building/street/furniture/spacing exclusions, and builds the **demand field** via `build_demand_cells` (`placement_inputs.py:88`).
     - On `live`, the demand field is built from a **baseline UTCI grid** (`UTCI > 26 °C ∧ impervious ∧ not-already-shaded ∧ ¬NaN`, weight `UTCI − 26`), cropped to its non-NaN bounding box. On `mock`/`cached`, a uniform proxy demand substitutes.
     - **Greedy placement** (`smart_placement.place_trees_greedy`, `smart_placement.py:148`) solves budgeted weighted max-coverage using shade-gain from `shade_proxy.py`; stops on a real condition (`stop_reason`), never a fixed iteration cap.
   - **Stage 2 — live validation**: `sdk_client.get_baseline_utci` + `get_intervention_utci` produce two measured 512×512 grids; reported ΔUTCI = `baseline.utci_c − intervention.utci_c`; cooled footprint via `sdk_client.cooled_footprint_m2` (`sdk_client.py:259`).
4. **Bundle** — `export_web.export_web_bundle` (`export_web.py:98`) writes a self-contained bundle (decision JSON, trees + boundary GeoJSON, raster bounds, baseline/intervention PNGs, optional `scene.glb`) into `web/public/eval_bundle/` (`_EVAL_DIR`), distinct from the curated showcase `web/public/web_bundle/` (`_BUNDLE_DIR`) so a user run can't overwrite the demo.
5. **Render** — client loads the fresh bundle; `liveBundle` overrides the static bundle (`App.tsx`).

**City-wide path (€1,000,000 allocation):**

1. `POST /api/citywide/scan` — fast ranking of the 494 `scored_grid` cells by `composite_score_B`; **no live calls**.
2. `POST /api/citywide/allocate` → `citywide.allocate_citywide` (`citywide.py:260`):
   - Ranks all 494 cells; takes the top-N candidates.
   - Builds a centred **200 m × 200 m** sample polygon per candidate (`_CELL_SAMPLE_SIZE_M = 200.0`, under the 62 500 m² cap).
   - Runs the full single-site `smart_evaluate` chain per cell at a per-site budget cap (PAPER: €150,000).
   - Funds best-first (by measured €/m²-cooled when live, else descending `composite_score_B`) until budget committed, with per-*barri* de-duplication and minimum site separation.
   - Aggregates trees, cooled area, canopy, person-degrees, de-duplicated population served.

**State Management:**
- Server is effectively stateless per request; live results are cached to disk by SHA-256 geometry hash (`cached` tier replays them). Coordinate-frame origin is reset per run (`spatial_engine.reset_site_origin`).
- Client state is a phase machine in `App.tsx` (`intro` | `citywide` | result), persisted via `localStorage` (`coolspend_seen`, `coolspend_video_seen`).

## Key Abstractions

**Three-tier Infrared backend (`CoolingEstimator` / `sdk_client` dispatch):**
- Purpose: make the measured-vs-synthetic distinction explicit at the type level.
- Examples: `coolspend/sdk_client.py` (`_backend`, `get_baseline_utci`, `get_intervention_utci`), `coolspend/cooling_estimator.py`.
- Pattern: `mock` = deterministic scalar UTCI, no network, "NOT MEASURED DATA" disclaimer; `cached` = disk replay keyed by geometry hash, raises on miss; `live` = real engine, requires `INFRARED_API_KEY`, writes through to cache.

**Validated candidate slot + demand cell:**
- Purpose: discretise placement into a finite validated lattice and a weighted demand field.
- Examples: `coolspend/candidate_slots.py` (`generate_slots`), `coolspend/placement_inputs.py` (`build_demand_cells`, `assemble_inputs`).
- Pattern: 4 m lattice (`GRID_STEP_M`), 8 m min spacing (`MIN_SPACING_M`), in-ground vs planter modes; `requires_utility_survey` flag on in-ground slots.

**Cost-benefit greedy coverage maximiser:**
- Purpose: deployed placement engine (not NSGA-II).
- Examples: `coolspend/smart_placement.py:place_trees_greedy`, `coolspend/shade_proxy.py`.
- Pattern: precompute static coverage, rank by marginal-gain-per-euro with cooling-score/marginal tie-breaks, anti-monoculture cap (`max_species_share = 0.40` after a `diversity_grace = 4` window).

**NSGA-II alternative (benchmark only, not shipped):**
- Examples: `coolspend/optimizer.py`, surrogate `coolspend/spatial_engine.py:delta_tmrt_surrogate` (`spatial_engine.py:805`), calibration `coolspend/calibration.py`.
- Pattern: bi-objective (thermal vs ecological), TOPSIS selection, fixed seed 42. Documented as a design alternative; the deployed path is the greedy.

## Entry Points

**FastAPI service (`coolspend/api_server.py`):**
- Triggers: HTTP from the web client.
- Endpoints: `GET /api/health`, `POST /api/buildings` (fast preview), `POST /api/evaluate` (full single-site pipeline), `POST /api/citywide/scan`, `POST /api/citywide/allocate`.
- Responsibilities: validate/area-cap input, dispatch to the core, write bundles, serve static files.

**CLI / app (`coolspend/main.py`, `coolspend/app.py`, `app_3d.py`, `app_viz.py`):**
- Triggers: direct invocation / Gradio-style UI / visualization.
- Responsibilities: drive `run_decision`/`smart_evaluate` outside the HTTP path (also used by tests).

**Web client (`web/src/main.tsx` → `App.tsx`):**
- Triggers: browser load.
- Responsibilities: load bundle, run the phase machine, draw polygons, call the API, render deck.gl overlays.

## Error Handling

**Strategy:** Graceful degradation with logged warnings; never silently fabricate measured data.

**Patterns:**
- OSM/Overpass unreachable → exclusion sets degrade to empty (logged), placement still runs.
- Demand filter eliminates all cells → fall back to all hot, unshaded ground (logged warning).
- `cached` cache miss → raises rather than falling through to `mock`.
- `live` without `INFRARED_API_KEY` → `EnvironmentError`.
- 4th live call in a run → `RuntimeError` via `SimBudget`.
- GeoJSON parsed via `json.loads` only, never `eval`/`exec`.

## Cross-Cutting Concerns

**Logging:** Standard `logging` module per-module loggers (e.g. `logging.getLogger("coolspend.api_server")`, `"coolspend.citywide"`); `app_pipeline` attaches a `_CaptureHandler` to record every SDK call into a `call_log` for the run.
**Validation:** Pydantic request models (`PolygonRequest`, `EvaluateRequest`) plus server-side area caps; placement validity enforced from OSM geometry.
**Authentication:** Infrared API key read by the SDK from the environment only (`INFRARED_API_KEY`); never accepted over HTTP, logged, or returned.

---

*Architecture analysis: 2026-06-01*
