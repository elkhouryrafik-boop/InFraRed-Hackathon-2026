# Architecture

**Analysis Date:** 2026-05-21
**Context:** Architecture of the coolspend hackathon app, clean-extracted from the NatureGooddest reference codebase. coolspend is a focused subset — NOT the full 6-layer NG platform. The core loop maps to roughly L3 (optimize) + L4 (simulate/validate) + L5 (defend/emit) from the parent system.

---

## Pattern Overview

**Overall:** Surrogate-optimize → validate top-N with real simulation → rank by composite score → emit decision artifact

**Key Characteristics:**
- Offline NSGA-II Pareto optimization runs on a fast analytical surrogate (no real API calls in the hot optimization loop)
- Top-3 Pareto representatives are post-hoc validated with the real Infrared SDK UTCI simulation
- Multi-criteria decision making (TOPSIS) ranks validated results by configurable weights
- Output is a deterministic JSON artifact: ranked configurations with all provenance fields
- A Gradio app wraps the full pipeline for hackathon demo interaction

---

## Core Loop

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. BASELINE                                                         │
│     sdk_client.py → Infrared SDK → baseline UTCI for the site       │
│     (one call, result cached to disk)                                │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│  2. OPTIMIZE on SURROGATE                                            │
│     optimizer.py → NSGA-II (pymoo) → COOLSTOCKProblem               │
│       Variables: x_m, y_m, width_m, height_m, tilt_deg,             │
│                  porosity_pct  (all in plaza-local metres / degrees) │
│       Surrogate: spatial_engine.py::delta_tmrt_surrogate()           │
│                  (analytical proxy, no API call in hot path)         │
│       Objectives: F1=-ΔTmrt_site, F2=scaffold_modules, F3=-corridor │
│       Constraint: G1=modules - ULMA_STOCK ≤ 0                       │
│       Output: Pareto front (100 points)                              │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│  3. SELECT TOP-3 REPRESENTATIVES                                     │
│     optimizer.py::select_top3()                                      │
│       C1: MAX Tmrt reduction (argmin F[:,0])                         │
│       C2: MIN material count (argmin F[:,1])                         │
│       C3: BALANCED — closest to utopia point (argmin ||F_norm||)     │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│  4. VALIDATE TOP-3 WITH REAL UTCI                                    │
│     sdk_client.py → Infrared SDK per configuration                   │
│       Input: x_m/y_m/width_m/height_m canopy geometry (plaza-local) │
│       Output: real UTCI delta vs baseline, cached per geometry hash  │
│     IMPORTANT: this step is where the surrogate estimate is          │
│     replaced by ground-truth simulation. The surrogate is used ONLY  │
│     to drive Pareto search; validated UTCI is what gets quoted.      │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│  5. COMPUTE €/°C                                                     │
│     cost_model.py → derive scaffold cost from modules                │
│       cost_per_module (€) × scaffold_modules = total_cost_eur        │
│       €_per_utci_degree = total_cost_eur / validated_delta_utci_c    │
│     rules_engine.py → apply spatial rules and flags                  │
│       (heritage buffer, stock limit, porosity range)                 │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│  6. RANK BY TOPSIS                                                   │
│     optimizer.py::topsis_rank()                                      │
│       Weights: thermal (0.5) / material (0.3) / ecology (0.2)        │
│       Presented as user-facing sliders in Gradio app                 │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│  7. EMIT DECISION ARTIFACT                                           │
│     optimizer.py::save_outputs()                                     │
│       top3_configurations.json — full provenance fields (see schema) │
│       pareto_front.png — Pareto scatter                              │
│       audit_record.json — honesty provenance trail                   │
│     app.py → Gradio renders ranked cards + Pareto plot               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Output JSON Schema

The canonical decision artifact is `top3_configurations.json`. Every downstream consumer (Gradio cards, cost display, export) reads from this schema. Field names are locked — do not rename without updating all consumers.

```json
{
  "run_metadata": {
    "algorithm": "NSGA-II (pymoo 0.6.1)",
    "site": "Plaça dels Àngels, Barcelona",
    "population": 100,
    "generations": 100,
    "seed": 42,
    "pareto_front_size": 87,
    "surrogate": "Analytical geometry proxy"
  },
  "configurations": [
    {
      "rank": 1,
      "label": "MAX_TMRT_REDUCTION",
      "x_m": 27.5,
      "y_m": 5.0,
      "width_m": 30.0,
      "height_m": 4.0,
      "tilt_deg": 22.5,
      "porosity_pct": 12.0,
      "scaffold_modules": 144,
      "delta_tmrt_c": 11.7,
      "delta_under_canopy_c": 11.7,
      "delta_tmrt_site_c": 4.42,
      "delta_tmrt_uncertainty_c": 4.0,
      "delta_tmrt_source": "Garcia-Nevado 2020 surface temp proxy (not Tmrt at 1.1m)",
      "utci_class": "Under-canopy estimate (surrogate ±4°C — pending Ladybug D1-04)",
      "coverage_fraction": 0.237,
      "embodied_carbon_kgco2e": 0.0,
      "assembly_time_hours": 36.0,
      "corridor_score": 0.998,
      "upcycled_material_kg": 0.0,
      "local_material_distance_km": 70,
      "material_shade_factor_pct": "34-70",
      "material_source": "Girbau LAB post-consumer textile",
      "topsis_score": null
    }
  ]
}
```

**Key field name notes:**
- `x_m` / `y_m` — canopy centroid in plaza-local metres (SW corner = origin). NOT lat/lon.
- `delta_tmrt_c` — under-canopy reduction (headline for jury)
- `delta_tmrt_site_c` — site-averaged reduction (= delta_under_canopy × coverage_fraction)
- `scaffold_modules` — integer bay count (bays_per_side²)

---

## Coordinate Systems

**This is a known footgun. Three CRSes coexist. Conversion must happen at explicit boundaries.**

| Layer | CRS | Notes |
|---|---|---|
| Raw geospatial inputs (OSM, GBIF, EPW) | EPSG:4326 (WGS84 lat/lon) | e.g., plaza centroid `(2.1670°E, 41.3826°N)` |
| NSGA-II decision variables, output JSON, plan-view display | Plaza-local metres | SW corner of plaza rectangle = `(0, 0)`. x_m = East-West [0, 60], y_m = North-South [0, 42]. y=0 is the MACBA (north) edge. |
| Infrared SDK geometry input | Plaza-local metres (projected) | SDK receives polygon in local metres; centroid anchored at EPSG:4326 site origin for server-side projection |
| Spanish cadastre / EPSG:25831 | ETRS89 / UTM zone 31N | Declared in audit records for provenance only; not used in any computation |

**Critical origin offset (from `nature_architecture.md`):**
NSGA-II `(x_m=30, y_m=5)` maps to 3D scene coords `(0, -25)` because the 3D scene centres the plaza at `(0, 0)` with SW corner at `(-30, -30)`. In coolspend this origin offset is only relevant if a spatial visualisation layer is added. The NSGA-II output fields `x_m`/`y_m` always use the SW-corner-origin convention.

**Projection for small-area SDK calls:** equirectangular with cos-latitude correction. Accurate within ±200 m of plaza centroid. Degrades at longer range.

---

## Layers

**Spatial Engine:**
- Purpose: Encode plaza geometry, site constants, surrogate physics
- Proposed module: `spatial_engine.py`
- Contains: `shade_efficiency()`, `delta_tmrt_surrogate()`, `pollinator_corridor_score()`, grid-snap helpers, site constants (SITE_WIDTH_M, SITE_DEPTH_M, BAY_SIZE_M, BASELINE_TMRT, HERITAGE_BUFFER_M)
- Depends on: numpy only
- Used by: `optimizer.py` (in NSGA-II hot path)

**Rules Engine:**
- Purpose: Enforce spatial and stock constraints; apply heritage buffer clamp
- Proposed module: `rules_engine.py`
- Contains: spatial bound checks, ULMA stock gate, heritage buffer enforcement, porosity range validation
- Depends on: `spatial_engine.py` constants
- Used by: `optimizer.py` `_evaluate()` method, `app.py` for user input validation

**Optimizer:**
- Purpose: Run NSGA-II, select Top-3, run TOPSIS, save outputs
- Proposed module: `optimizer.py`
- Contains: `COOLSTOCKProblem(ElementwiseProblem)`, `run_optimisation()`, `select_top3()`, `topsis_rank()`, `save_outputs()`, `write_audit_record()`
- Depends on: `spatial_engine.py`, `rules_engine.py`, `cost_model.py`, `sdk_client.py`, pymoo
- Used by: `app.py`

**Cost Model:**
- Purpose: Translate scaffold module count into euros, compute €/°C ratio
- Proposed module: `cost_model.py`
- Contains: `cost_per_module_eur`, `total_cost()`, `cost_per_utci_degree()`, embodied carbon computation
- Depends on: nothing (pure arithmetic + config constants)
- Used by: `optimizer.py` post-validation ranking, `app.py` display cards

**SDK Client:**
- Purpose: Call Infrared.city SDK for baseline UTCI and per-config validation; cache results by geometry hash
- Proposed module: `sdk_client.py`
- Contains: `UTCIResult` dataclass, `get_baseline_utci()`, `get_intervention_utci()`, `_geometry_hash()`, `_load_cache()`, `_save_cache()`
- Depends on: `infrared_sdk` (real SDK), `json`, `hashlib`, `pathlib`
- Backend selection via `INFRARED_BACKEND` env var: `mock | cached | live`
- Used by: `optimizer.py` (validation step, post Top-3 selection)

**App:**
- Purpose: Gradio UI wrapping the full pipeline; exposes TOPSIS weight sliders, site parameter inputs, ranked result cards
- Proposed module: `app.py`
- Contains: Gradio interface definition, `run_pipeline()` callback, result card rendering, Pareto plot display
- Depends on: all other modules
- Entry point: `python app.py`

---

## Entry Points

**CLI optimization run (no UI):**
- Invocation: `python optimizer.py`
- Responsibilities: run full pipeline, write `outputs/top3_configurations.json`, `outputs/pareto_front.png`, `outputs/audit_record.json`

**Gradio app:**
- Invocation: `python app.py`
- Triggers: user submits site parameters + TOPSIS weights via Gradio form
- Responsibilities: invoke `optimizer.run_optimisation()`, validate Top-3 via `sdk_client`, rank via TOPSIS, render result cards

---

## Data Flow: Variable Lifecycle

```
User input (Gradio) / defaults
    → site constants in spatial_engine.py (fixed for Plaça dels Àngels)
    → NSGA-II decision variable bounds [xl, xu] from P01_YAML or fallback
    → COOLSTOCKProblem._evaluate()
        → snap to Layher grid (2.5 m bays)
        → apply heritage buffer clamp (y_m ≥ 5 m)
        → shade_quality = 1 - porosity_pct/100  [applied ONCE — do not re-apply]
        → delta_tmrt_surrogate(shade_quality, porosity_pct, tilt_deg, height_m)
        → coverage_fraction = min(width_m² / SITE_AREA_M2, 0.90)
        → delta_tmrt_site = delta_under_canopy × coverage_fraction
        → F = [-delta_tmrt_site, scaffold_modules, -corridor_score]
        → G = [modules - ULMA_STOCK]
    → Pareto front (X, F arrays)
    → select_top3(): decode, label, add provenance fields
    → sdk_client.get_intervention_utci(cfg) per Top-3  [real UTCI validation]
    → cost_model.cost_per_utci_degree(cfg)
    → topsis_rank(result, weights) → topsis_score per cfg
    → save_outputs() → top3_configurations.json
```

---

## Error Handling

**Surrogate:**
- YAML bounds load failure falls back to hardcoded `FALLBACK_XL`/`FALLBACK_XU` arrays (see `load_pattern_bounds()` in `nature_nsga2_coolstock.py`)
- Surrogate is intentionally analytical-only; it must never call external APIs

**SDK Client:**
- Cache miss + `INFRARED_BACKEND=cached` → raise `FileNotFoundError` (do not silently fall through to mock)
- `INFRARED_BACKEND=live` + missing `INFRARED_API_KEY` → raise `EnvironmentError` with clear message
- `INFRARED_BACKEND=mock` → return deterministic synthetic field, always annotate with `disclaimer: "NOT MEASURED DATA"`
- Geometry hash collision is theoretically possible (16-char SHA256 prefix) but not a runtime concern at hackathon scale

**Optimizer:**
- Pareto front degeneration (all solutions identical) → `select_top3()` deduplication loop ensures 3 distinct indices or fewer if front is too small
- `topsis_rank()` zero-norm guard: `norms[norms == 0] = 1e-9`

---

## Known Issues Ported From Reference (Do Not Repeat in coolspend)

1. **Double porosity penalty bug** (fixed in reference 2026-05-20, audit C10): `shade_quality = 1 - p/100` must be passed to `delta_tmrt_surrogate` as `shade_fraction`; the body must NOT multiply by `(1 - p/100)` again. In coolspend: compute `shade_quality` once in the caller, pass it through, never re-apply inside the surrogate.

2. **F3 corridor degeneracy**: The heritage buffer y-clamp pins most solutions to y_m ≈ 5 m, making `pollinator_corridor_score` return ~1.0 for all Pareto solutions. F3 carries near-zero selection pressure. In coolspend, either (a) drop F3 and run as 2-objective, or (b) encode corridor as a 2-D scoring function that doesn't degenerate under the clamp.

3. **TOPSIS weights are arbitrary**: The `(0.5, 0.3, 0.2)` defaults are the founder's judgment, not a stakeholder-derived value. In coolspend, expose them as Gradio sliders and never present them as calibrated constants.

4. **`MAX_TMRT_REDUCTION = 12.0 °C` is unsourced**: Value should be replaced by the maximum ΔTmrt from a calibrated study at 1.1 m or Juan's Ladybug lookup. Until replaced, always flag in output JSON as `"surrogate_note": "Analytical proxy — replace with calibrated value"`.

---

## TARGET coolspend MODULE MAP

| Concept from reference | Reference location | Proposed coolspend module | Action |
|---|---|---|---|
| Site constants, grid-snap, surrogate physics | `nature_nsga2_coolstock.py` lines 73-103, 106-155, 158-193 | `spatial_engine.py` | extract-clean |
| Heritage buffer + spatial constraint enforcement | `nature_nsga2_coolstock.py` `_evaluate()` lines 208-221 | `rules_engine.py` | extract-clean |
| NSGA-II problem class + run + Top-3 + TOPSIS + save | `nature_nsga2_coolstock.py` lines 198-546 | `optimizer.py` | extract-clean |
| €/°C ratio and embodied carbon | `nature_nsga2_coolstock.py` select_top3 + `nature_metrics.py` `carbon_headroom_kgco2e()` | `cost_model.py` | extract-clean (new composition) |
| Infrared SDK call + geometry hash cache | `infrared_client_v2.py` `_dispatch()` + `_geometry_hash()` + cache I/O | `sdk_client.py` | partial (keep mock/cached/live dispatch pattern; drop legacy mock field generators) |
| All metrics computation | `nature_metrics.py` `compute_all()` + M1/M2/M3/M4 | Not a top-level module; metrics called from `optimizer.py` post-validation | partial (port `utci_hours_above()` and `carbon_headroom_kgco2e()` inline) |
| Gradio UI | Does not exist in reference (Flask demo_app.py) | `app.py` | new (no port) |
| Audit record writer | `nature_nsga2_coolstock.py` `write_audit_record()` | `optimizer.py` (inline) | extract-clean |
| YAML P01 bounds loader | `nature_nsga2_coolstock.py` `load_pattern_bounds()` | `spatial_engine.py` | extract-clean (with fallback) |
| OWL/SPARQL pattern KB | `evaluator.py`, `sparql_engine.py` (not in reference files set) | leave-behind | The full 6-layer KB is not part of coolspend scope |
| Flask demo_app.py routes | `demo_app.py` (not in reference files set) | leave-behind | Replace with Gradio in `app.py` |
| GBIF/EPW/OSM ingest pipeline | `nature_metrics.py` EPW + GBIF data paths | leave-behind | Use hardcoded Barcelona constants for hackathon; do not port the full L1 ingest chain |

---

*Architecture analysis: 2026-05-21*
