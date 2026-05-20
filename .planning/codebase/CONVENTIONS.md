# Coding Conventions

**Analysis Date:** 2026-05-21
**Source files:** `nature_nsga2_coolstock.py`, `nature_metrics.py`, `infrared_client_v2.py`, `nature_infrared_client.py`
**Style guide reference:** `nature_architecture.md` (Honesty Contract section)

---

## Naming Patterns

**Files:**
- `snake_case` throughout: `nature_nsga2_coolstock.py`, `nature_metrics.py`, `infrared_client_v2.py`
- Prefix with domain context for ported modules: `nature_` prefix signals origin; coolspend modules should use a domain prefix (e.g. `coolspend_` or bare module names like `spatial_engine.py`, `rules_engine.py` per v2 plan)
- Version suffixes are acceptable when a clean replacement coexists: `infrared_client_v2.py`

**Functions:**
- `snake_case` for all callables: `load_pattern_bounds`, `delta_tmrt_surrogate`, `run_optimisation`, `pollinator_corridor_score`
- Private helpers prefixed with `_`: `_backend()`, `_geometry_hash()`, `_mock_tmrt_field()`, `_load_epw()`, `_load_arbrat()`, `_dispatch()`
- Public convenience aggregators named `compute_all` / `simulate_all` — one-stop callers that batch sub-calls
- Boolean-returning validators named `is_valid_*`: `is_valid_location()` (v2 plan `SpatialEngine`)

**Variables / constants:**
- Module-level constants in `UPPER_SNAKE_CASE`: `SITE_WIDTH_M`, `BASELINE_TMRT`, `ULMA_STOCK`, `BAY_SIZE_M`, `HIGH`, `MED`, `LOW`
- Local variables in `snake_case`: `shade_fraction`, `coverage_fraction`, `tilt_deg`
- Cache dicts named `_FOO_CACHE`: `_EPW_CACHE`, `_ARBRAT_CACHE`
- Physical quantities include unit suffix in the name: `x_m`, `height_m`, `tilt_deg`, `porosity_pct`, `gwp_kgco2e_per_kg`

**Classes:**
- `PascalCase`: `COOLSTOCKProblem`, `FieldStats`, `RunMetadata`, `CFDResponse`, `SpatialEngine`
- Problem classes inherit from framework base directly: `class COOLSTOCKProblem(ElementwiseProblem)`

**Type aliases / Literals:**
- Use `typing.Literal` for constrained string enums: `Backend = Literal["mock", "cached", "live"]`

---

## Type Hints

**Mandate:** All function signatures carry full type hints. No bare `def foo(x):`.

**Patterns observed:**
```python
# nature_metrics.py — standard return shape
def utci_hours_above(threshold_c: float = 32.0,
                     coverage_fraction: float = 0.0) -> dict[str, Any]:

# nature_nsga2_coolstock.py — Path inputs
def load_pattern_bounds(yaml_path: Path):        # return inferred (xl, xu tuple)

# infrared_client_v2.py — Optional + union syntax
def simulate_tmrt(geometry: dict, climate: dict | None = None) -> dict[str, Any]:

# nature_metrics.py — cfg dict typed broadly (PEP 604 union)
def plaza_shaded_fraction(cfg: dict[str, Any] | None = None,
                          plaza_area_m2: float = 3800.0) -> dict[str, Any]:
```

**`from __future__ import annotations`** is present in `nature_metrics.py` and `infrared_client_v2.py` — use it in every new module to enable PEP 604 union syntax on Python 3.9.

**`from typing import Any`** imported explicitly; `dict[str, Any]` is the standard return type for metric functions and API responses.

---

## Docstring Style

**Format:** Plain narrative paragraphs, NOT NumPy / Google sections.

**Structure for public functions:**
1. One-sentence purpose statement.
2. Source / derivation block: cite the paper or data source inline.
3. Explicit AUDIT / HONESTY notes for any uncertain computation (see Honesty Contract below).
4. Parameter descriptions inline in narrative, not a `Parameters:` block.
5. `Returns:` described inline when non-obvious.

**Examples:**
```python
# nature_nsga2_coolstock.py — surrogate function
def delta_tmrt_surrogate(shade_fraction: float, porosity_pct: float,
                          tilt_deg: float, height_m: float) -> float:
    """
    DEPRECATED 2026-05-19 — kept only because the legacy `/surrogate` POST route
    in demo_app.py (consumed by the old NG3D drag-edit viewer) still calls this
    function. ...
    Note: REPLACE with Juan's Ladybug lookup table when D1-04 is complete
    (currently in_progress per audit_record.json). Track in audit/09_ai_engineer.md.
    """
```

```python
# nature_metrics.py — M1 metric
def utci_hours_above(threshold_c: float = 32.0,
                     coverage_fraction: float = 0.0) -> dict[str, Any]:
    """
    Count annual hours where UTCI exceeds threshold.

    coverage_fraction = NSGA-II output (0-1, fraction of plaza under canopy).
    ...
    Returns:
        {value, unit, confidence, sources, note, baseline_value}
    """
```

**Module docstring:** Required at the top of every file. Must include:
- One-line project / module purpose
- Site or domain context (project name, location if relevant)
- Data-source status (surrogate? mock? real EPW?)
- Key function inventory
- Any DEPRECATED status

---

## Import Organisation

**Order observed (consistent across all source files):**

1. `from __future__ import annotations` (when present — always first)
2. Standard library (`json`, `math`, `os`, `hashlib`, `datetime`, `pathlib`, `typing`, `statistics`, `dataclasses`)
3. Third-party / heavy domain (`numpy`, `pymoo.*`, `ladybug*`, `shapely`)
4. Local project imports (none in the source files — all modules are standalone)

**No `__all__` defined** in any source file; public surface is implicit (leading-underscore convention for private).

**Late imports** are acceptable for optional / heavy deps that may fail:
```python
# nature_metrics.py — shapely is imported inside the function body
def plaza_shaded_fraction(...):
    from shapely.geometry import Polygon, MultiPoint
```

**Framework imports after utility setup** (not at top) are acceptable when order matters:
```python
# nature_nsga2_coolstock.py — pymoo imports come after YAML loader is defined
from pymoo.algorithms.moo.nsga2 import NSGA2
```

---

## Return Shape Convention (Metric Functions)

Every metric function returns a **standard dict** with these keys:

```python
{
    "value":              float | int | None,   # the headline number
    "unit":               str,                  # e.g. "hours / yr with UTCI > 32°C"
    "confidence":         "HIGH" | "MED" | "LOW",
    "confidence_reason":  str,                  # verbose audit explanation
    "sources":            list[str | None],     # connector_id references
    "note":               str,                  # human-readable narrative
    "metric_id":          str,                  # stable snake_case identifier
    # optional:
    "baseline_value":     float | int,
    "delta":              float,
    "components":         dict,
    "error":              str,                  # present only on failure
}
```

This shape is established in `nature_metrics.py` and must be preserved in coolspend metric modules so consumers (API routes, audit writers) can read `.get("confidence")` uniformly.

**Confidence constants** are module-level strings, not an enum:
```python
# nature_metrics.py
HIGH = "HIGH"
MED  = "MED"
LOW  = "LOW"
```

---

## Error Handling

**Pattern: return-error-dict, not raise, for data-missing cases in metric functions:**
```python
# nature_metrics.py
if not EPW_PATH.exists():
    _EPW_CACHE["error"] = f"EPW not found at {EPW_PATH}"
    return _EPW_CACHE

if "error" in epw:
    return {"value": None, "error": epw["error"], "confidence": LOW,
            "sources": [], "note": "EPW unavailable"}
```

**Raise `NotImplementedError` for unimplemented live paths:**
```python
# infrared_client_v2.py
if backend == "live":
    raise NotImplementedError(
        "INFRARED_BACKEND=live not wired yet — set to 'mock' or 'cached'. ..."
    )
```

**Raise `RuntimeError` at provenance gate** (L5 HARD_BLOCK): any `PENDING` or missing data source blocks evaluation entirely (see `nature_architecture.md` L5 section). New modules that call external data must respect this gate.

**Fallback with logging for YAML / config load failures:**
```python
# nature_nsga2_coolstock.py
except Exception as e:
    print(f"  YAML load failed ({e}) — using fallback bounds")
    return FALLBACK_XL, FALLBACK_XU
```

**No bare `except:` or `except Exception:` without logging the error** — every catch prints context.

---

## Environment-Variable Config Pattern

**Pattern: single private function reads the env var with a default; called at dispatch time, not at import:**
```python
# infrared_client_v2.py
def _backend() -> Backend:
    return os.environ.get("INFRARED_BACKEND", "mock")  # type: ignore[return-value]
```

**Observed env vars:**
- `INFRARED_BACKEND` — `"mock"` | `"cached"` | `"live"` (default `"mock"`)
- `INFRARED_API_KEY` — required only when `INFRARED_BACKEND=live`
- `FIRING_ENGINE` — `"sparql"` | `"ast"` (evaluator, default `"sparql"`)
- `HARD_BLOCK` — controls whether provenance failures raise or warn

**Paths are computed relative to `__file__`, never hardcoded absolute:**
```python
# nature_metrics.py
BASE   = Path(__file__).resolve().parent
L1_DIR = BASE / "L1_INGEST_data"
EPW_PATH = L1_DIR / "climate" / "Barcelona_TMYx_2011-2025.epw"
```

**Mock-vs-live switch is always env-driven**, never a function argument or compile-time constant. This allows the same code path to run in test (mock), CI (cached), and production (live) without code changes.

---

## Section / Block Comments

**ASCII-art section separators** are used throughout to divide a module into named blocks:
```python
# ── SITE CONSTANTS (from L1 INGEST) ──────────────────────────────────────────
# ── SURROGATE FUNCTION ───────────────────────────────────────────────────────
# ── PROBLEM DEFINITION ───────────────────────────────────────────────────────
# ── RUN NSGA-II ──────────────────────────────────────────────────────────────
# ── SAVE OUTPUTS ─────────────────────────────────────────────────────────────
# ── Response shapes ──────────────────────────────────────────────────────────
# ── Mock field generators ────────────────────────────────────────────────────
# ── Public API ───────────────────────────────────────────────────────────────
```

Use the same `# ── SECTION NAME ─────` pattern in coolspend modules. Keep the total line length at 80 characters.

**Inline comments** annotate physical units, source references, and known bugs:
```python
MAX_TMRT_REDUCTION = 12.0   # °C — UNSOURCED conservative cap (see note above)
BASELINE_TMRT = 58.0   # °C at 1.1 m, 15:00 summer design day (ICAEN 2024 estimate)
```

---

## The Honesty Contract (Preserve in coolspend)

Defined in `nature_architecture.md` § "The honesty contract in 5 bullets" and implemented throughout the source files. **This is a first-class convention, not optional.**

### Rule 1 — MOCKS.md Ledger

Every mock, stub, surrogate, or synthetic value must have an entry in `MOCKS.md`. The pre-merge check is: `grep -r "mock\|MOCK\|DECLARED\|PENDING\|REQUIRES_VERIFICATION\|heuristic"` must match a `MOCKS.md` entry. New mocks must be added in the same commit that introduces them.

**In-code tagging observed:**
```python
# infrared_client_v2.py — disclaimer in RunMetadata
disclaimer="NOT MEASURED DATA — synthetic field for UI integration only."

# nature_nsga2_coolstock.py — module header
# Surrogate: Analytical geometry proxy (Ladybug calibration pending Juan's S0 sim)

# nature_nsga2_coolstock.py — output field
cfg["utci_class"] = "Under-canopy estimate (surrogate ±4°C — pending Ladybug D1-04)"
cfg["surrogate_note"] = "Analytical proxy — replace with Ladybug D1-04 value"
```

**For coolspend:** any mock SDK response, stub cost model, or surrogate thermal value must carry:
- An inline comment with `# MOCK:` or `# SURROGATE:` prefix naming what it replaces
- An entry in `MOCKS.md` with location, reason, and replacement path

### Rule 2 — DOI Verification

No DOI may appear in code or data files unless it has been CrossRef-verified. Agent-generated DOIs must never be trusted. When a citation cannot be verified, use the explicit placeholder `REQUIRES_VERIFICATION` rather than inventing a DOI.

```python
# nature_nsga2_coolstock.py — module header, verified DOIs only
# Reference: Garcia-Nevado et al. 2020 (DOI:10.1016/j.scs.2020.102458) — surface proxy
#            Vanos et al. 2020 (DOI:10.1007/s00484-020-02056-y) — shade component lower bound
```

### Rule 3 — Data Source Status Tags

Every data source referenced in code must appear in `data_manifest.yaml` with status `VERIFIED` / `PENDING` / `DECLARED`:
- `VERIFIED` — independently confirmed, named verifier recorded
- `DECLARED` — partner-supplied, fires but flagged `honesty_status="DECLARED_INPUTS"` in audit output
- `PENDING` — not yet verified, **hard-blocks** the provenance gate

In-code, confidence propagates from source status:
```python
# nature_metrics.py
confidence = HIGH if UHI_VALIDATED else MED
```

### Rule 4 — No `eval()`

Pattern firing uses `sparql_engine.site_fires_sparql()` (rdflib ASK queries) as default, with `evaluator.safe_eval_filter()` (Python AST walk, no `eval()`) as fallback. New coolspend modules must never use `eval()` or `exec()` to parse user-provided or data-file strings.

### Rule 5 — Per-Run Audit Trail

Every optimisation run writes `audit_record.json` (see `write_audit_record()` in `nature_nsga2_coolstock.py`). The record includes: fired conditions + sources + confidence + surrogate flags + TOPSIS weights. New coolspend run outputs must include an equivalent provenance block.

```python
# nature_nsga2_coolstock.py — surrogate_flags block in audit_record
"surrogate_flags": {
    "delta_tmrt": "UNVALIDATED — Garcia-Nevado 2020 surface temp proxy, not Tmrt at 1.1m",
    "utci_class": "ESTIMATE — derived from surrogate, pending Ladybug D1-04",
    "uncertainty_c": 4.0,
    "ladybug_task": "D1-04",
    "ladybug_status": "in_progress"
}
```

### Rule 6 — Honest Framing in Output Fields

Computed values carry explicit framing strings, not bare numbers:
```python
# nature_metrics.py — avoided_heat_mortality
"honest_per_plaza_framing": src.get("honest_per_plaza_framing").get("_pitch_phrase")
# Prevents "this plaza saves N lives" overclaim
```

---

## File-Level `__main__` Block

All source files have an `if __name__ == "__main__":` block that serves as a **smoke test / integration sample**:
- `nature_nsga2_coolstock.py` — runs the full optimisation, prints Top-3, saves outputs
- `nature_metrics.py` — calls `compute_all()` with a known config, prints confidence ribbons
- `infrared_client_v2.py` — calls `simulate_all()` with a sample geometry, prints stats

New coolspend modules must include a `__main__` block that exercises the public API with a hardcoded example. This is the first-pass sanity check before any test harness is set up.

---

## Recommended Conventions for New coolspend Modules

Following the patterns above, new modules in the coolspend project (e.g. `spatial_engine.py`, `rules_engine.py`, `optimize_trees.py`, `main.py`) should:

1. **Open with a module docstring** that states: module purpose, mock/real status of every external dependency, and any known limitations.

2. **Use `from __future__ import annotations`** as the first import.

3. **Compute all paths relative to `__file__`:**
   ```python
   BASE      = Path(__file__).resolve().parent
   DATA_DIR  = BASE / "data"
   CACHE_DIR = BASE / "cache"
   ```

4. **Expose backend/mode via env var, read in a private `_backend()` function:**
   ```python
   def _sdk_mode() -> Literal["mock", "live"]:
       return os.environ.get("INFRARED_BACKEND", "mock")  # type: ignore
   ```

5. **Return the standard metric dict shape** from all compute functions (`value`, `unit`, `confidence`, `sources`, `note`, `metric_id`). Never return a bare float from a public function.

6. **Tag every mock or surrogate** with an inline `# MOCK:` or `# SURROGATE:` comment AND add a `MOCKS.md` entry in the same commit.

7. **Name physical-quantity variables with unit suffix:** `min_spacing_m`, `utci_threshold_c`, `budget_eur`, `area_m2`.

8. **Use section separators:** `# ── SECTION ──────────────────────────────────────────────────────────────────`

9. **Honour the no-`eval()` rule.** Use AST walk or rdflib for filter evaluation.

10. **Write an `if __name__ == "__main__":` smoke block** in every module.

11. **For `SpatialEngine` and `RulesEngine`** (v2 plan), expose `is_valid_location(x, y) -> bool` and `calculate_ecological_score(tree_coords, species_list) -> float` as the public interface, following the naming in `docs/plans/2026-05-20-tree-budget-optimizer-v2.md`.

12. **Cite DOIs only after CrossRef verification.** Use `# SOURCE: REQUIRES_VERIFICATION` for unverified claims.
