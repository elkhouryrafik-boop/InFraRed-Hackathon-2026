# Codebase Structure

**Analysis Date:** 2026-05-21
**Context:** Reference NatureGooddest files in this directory, plus proposed clean coolspend/ layout.

---

## Current Directory Layout (Reference Files)

```
C:\Users\Rafik\OneDrive\Python Resources\Hackathon\
├── nature_nsga2_coolstock.py     # NSGA-II optimizer + surrogate + Top-3 + TOPSIS + outputs
├── nature_metrics.py             # P0 KPI metrics: UTCI hours, biodiversity, carbon, shade fraction
├── infrared_client_v2.py         # Infrared SDK mock client (deprecated in NG, design reference)
├── nature_infrared_client.py     # Identical to infrared_client_v2.py (same file, two copies)
├── nature_architecture.md        # 6-layer NG platform architecture overview
├── CONCEPT_REPORT.md             # Project concept document
├── HANDOFF.md                    # Handoff notes
├── infrared_hackathon.md         # Hackathon-specific Infrared notes
└── docs/                         # Additional documentation
```

**Note:** `infrared_client_v2.py` and `nature_infrared_client.py` are byte-identical. The `_v2` suffix was added when the original was superseded by the real SDK in the parent project. Both are design references only — neither is imported by coolspend.

---

## Proposed coolspend/ Clean Layout

```
coolspend/
├── app.py                        # Gradio UI entry point
├── optimizer.py                  # NSGA-II problem, run, Top-3, TOPSIS, save_outputs, write_audit_record
├── spatial_engine.py             # Site constants, surrogate functions, grid-snap helpers
├── rules_engine.py               # Spatial constraint enforcement, heritage buffer, stock gate
├── cost_model.py                 # €/module pricing, €/°C computation, embodied carbon
├── sdk_client.py                 # Infrared SDK wrapper: baseline + intervention UTCI, cache
├── requirements.txt              # pymoo, gradio, numpy, infrared-sdk, shapely, ladybug-comfort
├── outputs/                      # Runtime-generated, gitignored
│   ├── top3_configurations.json  # Decision artifact (canonical output)
│   ├── pareto_front.png          # Pareto scatter plot
│   └── audit_record.json         # Provenance trail per run
└── cache/
    └── infrared/                 # geometry-hash keyed UTCI cache files ({metric}_{hash}.json)
```

---

## Directory Purposes

**`coolspend/` root:**
- Purpose: All runtime Python modules for the coolspend app
- Key files: `app.py` (entry point), `optimizer.py` (core loop orchestrator)

**`coolspend/outputs/`:**
- Purpose: Holds all generated artifacts from optimizer runs
- Generated: Yes
- Committed: No (gitignore)
- Key files: `top3_configurations.json` (consumed by Gradio cards and export)

**`coolspend/cache/infrared/`:**
- Purpose: Disk cache keyed by `{metric}_{geometry_hash_16char}.json` — prevents redundant Infrared SDK calls
- Generated: Yes
- Committed: No (gitignore)
- Pattern: `utci_{sha256[:16]}.json` (matches `sdk_client._geometry_hash()` scheme from reference)

---

## Key File Locations

**Entry Points:**
- `coolspend/app.py`: Gradio `gr.Interface` / `gr.Blocks` definition; `python app.py` starts the demo server
- `coolspend/optimizer.py`: `if __name__ == "__main__"` block runs headless pipeline and writes outputs

**Core Logic:**
- `coolspend/spatial_engine.py`: All physics — `shade_efficiency()`, `delta_tmrt_surrogate()`, `pollinator_corridor_score()`, site constants
- `coolspend/optimizer.py`: `COOLSTOCKProblem`, `run_optimisation()`, `select_top3()`, `topsis_rank()`, `save_outputs()`
- `coolspend/sdk_client.py`: `get_baseline_utci()`, `get_intervention_utci()`, `_dispatch()`, `_geometry_hash()`

**Configuration:**
- `coolspend/requirements.txt`: Pinned dependency list
- Environment: `INFRARED_BACKEND=mock|cached|live`, `INFRARED_API_KEY`

**Testing:**
- No test directory in reference; add `coolspend/tests/` with at minimum `test_surrogate.py` (unit tests for `spatial_engine` arithmetic) and `test_optimizer.py` (smoke: NSGA-II runs, returns 3 configs)

---

## Naming Conventions

**Files:**
- `snake_case.py` throughout (matches reference pattern)
- Single-concern modules: each file owns one architectural layer

**Functions:**
- `snake_case` throughout
- Private helpers prefixed with `_` (e.g., `_geometry_hash`, `_dispatch`, `_load_cache`)
- Public API functions have no prefix (e.g., `run_optimisation`, `select_top3`, `topsis_rank`)

**Variables:**
- Physical quantities carry units in name: `x_m`, `y_m`, `width_m`, `height_m`, `tilt_deg`, `porosity_pct`, `delta_tmrt_c`, `cost_eur`
- Never abbreviate unit suffixes — `_m` = metres, `_c` = degrees Celsius, `_pct` = percent, `_deg` = degrees of angle, `_eur` = euros

**Output JSON fields:**
- All field names in `top3_configurations.json` are frozen. Use exact names: `x_m`, `y_m`, `width_m`, `height_m`, `tilt_deg`, `porosity_pct`, `scaffold_modules`, `delta_tmrt_c`, `delta_under_canopy_c`, `delta_tmrt_site_c`, `coverage_fraction`, `topsis_score`, `rank`, `label`

---

## Where to Add New Code

**New physics / surrogate function:**
- Implementation: `coolspend/spatial_engine.py`
- No external API calls permitted inside this module

**New spatial constraint or rule:**
- Implementation: `coolspend/rules_engine.py`
- Rules receive and return config dicts; they do not mutate the NSGA-II problem class directly

**New cost or carbon metric:**
- Implementation: `coolspend/cost_model.py`
- Each metric returns `{value, unit, confidence, sources, note}` dict (matches `nature_metrics.py` pattern)

**New NSGA-II objective or TOPSIS weight preset:**
- Implementation: `coolspend/optimizer.py`
- Update `COOLSTOCKProblem.__init__()` n_obj, `_evaluate()` F assignment, `topsis_rank()` weight docstring, and the TOPSIS slider labels in `app.py`

**New Gradio UI component:**
- Implementation: `coolspend/app.py`
- Keep all UI logic in `app.py`; never import Gradio from any other module

**New SDK metric (e.g., wind, Tmrt in addition to UTCI):**
- Implementation: `coolspend/sdk_client.py`
- Add a new `get_{metric}()` function following the `_dispatch()` cache pattern

---

## Per-Reference-File Port Verdict

| File | Verdict | Reason |
|---|---|---|
| `nature_nsga2_coolstock.py` | **extract-clean** | The NSGA-II problem class, `run_optimisation()`, `select_top3()`, `topsis_rank()`, `save_outputs()`, `write_audit_record()`, `load_pattern_bounds()` are all directly reusable. Surrogate functions (`shade_efficiency`, `delta_tmrt_surrogate`, `pollinator_corridor_score`) and site constants port verbatim into `spatial_engine.py`. Grid-snap and heritage-buffer logic ports into `rules_engine.py`. The demo plotting (`plot_pareto`) ports into `optimizer.py`. Remove: all Flask imports, `demo_app.py` coupling, P01_YAML coupling (use fallback bounds in coolspend). Fix: surrogate is already porosity-bug-fixed (2026-05-20); do not re-introduce the double-penalty. |
| `nature_metrics.py` | **partial** | Port `utci_hours_above()` and `carbon_headroom_kgco2e()` into `cost_model.py` / inline in `optimizer.py`. Do NOT port `_load_epw()` / `_load_arbrat()` full ingest chain — use hardcoded Barcelona site constants for hackathon. Do NOT port `biodiversity_richness()` (GBIF + Arbrat data unavailable). `plaza_shaded_fraction()` is worth porting into `spatial_engine.py` (pure geometry, no external deps beyond shapely). `avoided_heat_mortality()` is leave-behind (requires Iungman JSON data file). |
| `infrared_client_v2.py` | **partial** | Port the `_dispatch()` cache pattern, `_geometry_hash()`, `FieldStats`/`RunMetadata`/`CFDResponse` dataclasses, and the `INFRARED_BACKEND` env-var selection logic into `sdk_client.py`. Leave behind: all mock field generators (`_mock_tmrt_field`, `_mock_utci_field`, `_mock_wind_field`, `_canopy_mask`, `_green_wall_edge`). These were NatureGooddest-specific spatial mocks — coolspend's mock should return a simple scalar UTCI delta, not a 24×24 field grid. |
| `nature_infrared_client.py` | **leave-behind** | Byte-identical to `infrared_client_v2.py`. No additional content to port. |
| `nature_architecture.md` | **leave-behind** | Documents the 6-layer NatureGooddest platform. Not relevant to coolspend's clean subset. The coordinate system section (EPSG:4326 vs plaza-local metres, NSGA-II origin offset) IS referenced — those facts are captured in `ARCHITECTURE.md` and `spatial_engine.py` comments. |
| `CONCEPT_REPORT.md` | **leave-behind** | Project concept document for parent project. |
| `HANDOFF.md` | **leave-behind** | Parent project handoff notes. |
| `infrared_hackathon.md` | **reference only** | Contains Infrared SDK integration notes relevant to `sdk_client.py` implementation; read before writing `sdk_client.py` but do not port as code. |

---

## Special Directories

**`outputs/`:**
- Purpose: Runtime artifact store (JSON, PNG, audit trail)
- Generated: Yes — created by `optimizer.save_outputs()` on first run
- Committed: No — add to `.gitignore`

**`cache/infrared/`:**
- Purpose: Geometry-hash keyed UTCI response cache (avoids redundant SDK calls during hackathon demo)
- Generated: Yes — created by `sdk_client._dispatch()` on first cache-miss
- Committed: Optional — committing a warm cache is acceptable for demo reliability; add `.gitignore` note

**`.planning/codebase/`:**
- Purpose: Architecture and structure docs consumed by GSD planning commands
- Generated: No (human/agent authored)
- Committed: Yes

---

*Structure analysis: 2026-05-21*
