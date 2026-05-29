# Coding Conventions

**Analysis Date:** 2026-05-27

## Naming Patterns

**Files:**
- snake_case for all Python modules: `cost_model.py`, `spatial_engine.py`, `sdk_client.py`, `rules_engine.py`, `bcn_species.py`, `bcn_lidar.py`, `app_pipeline.py`, `app_viz.py`, `main.py`, `calibration.py`, `optimizer.py`
- `__init__.py` at `coolspend/__init__.py` and `coolspend/tests/__init__.py`
- Test files mirror source names: `coolspend/tests/test_cost_model.py` tests `coolspend/cost_model.py`

**Functions:**
- snake_case throughout: `run_optimisation()`, `total_cost()`, `is_valid_location()`, `load_site()`, `validate_top3_with_infrared()`, `set_site_origin_from_polygon()`, `cost_per_utci_degree()`, `select_top3()`, `topsis_rank()`
- Private helpers prefixed with underscore: `_ensure_origin_initialized()`, `_build_baseline_geometry()`, `_active_trees()`, `_config_to_geometry()`, `_build_before_after()`, `_backend()`, `_geometry_hash()`
- Test helper functions also snake_case: `_make_config()`, `_tree()`, `_building_interior()`, `_default_dict()`, `_ensure_mock_backend()`, `_make_fake_infrared_sdk()`, `_install_fake_sdk()`

**Variables:**
- snake_case: `site_coverage_fraction`, `active_trees`, `hours_reduced`, `per_tree_delta`, `tree_count`, `discount_rate`, `ramp_years`
- Physical quantities carry unit suffix: `x_m`, `y_m`, `width_m`, `height_m`, `tilt_deg`, `budget_eur`, `area_m2`, `band_c`
- Simple coordinate pairs: `e, n` (UTM easting/northing), `lon, lat` (WGS84 decimal degrees)
- Module-level mutable state uses underscore prefix: `_SITE_ORIGIN_E`, `_ACTIVE_SITE`, `_ORIGIN_INITIALIZED`, `_SITE_CACHE`, `_SITE_RECT_CACHE`

**Classes:**
- PascalCase: `TreeBudgetProblem`, `CostLine`, `CostTable`, `GrowthDiscountParams`, `SimBudget`, `UTCIResult`, `CRSConsistencyError`
- Problem classes inherit from pymoo base: `class TreeBudgetProblem(ElementwiseProblem)`
- Test classes use PascalCase with descriptive names: `class TestGrowthCoolingFraction`, `class TestCostLineDataclass`, `class TestDefaultCostTable`, `class TestSpacingPenalty`, `class TestSpeciesDiversityScore`, `class TestEcologicalScore`

**Constants:**
- UPPER_SNAKE_CASE for module-level constants: `MAX_TMRT_REDUCTION_C`, `N_TREES`, `SEED`, `POP_SIZE`, `N_GEN`, `DEFAULT_BUDGET_EUR`, `CAPEX_PER_TREE_EUR`, `OPEX_HORIZON_YEARS`, `OPEX_PER_TREE_YEAR_EUR`, `HOURS_PER_DEGC_REF`, `PRE_CALIBRATION_BAND_C`, `SITE_WIDTH_M`, `SITE_DEPTH_M`, `TREE_CANOPY_RADIUS_M`, `MIN_SPACING_M`, `PEAK_SUN_ALTITUDE_DEG`, `TREE_SHADE_FRACTION`, `MAX_SITE_COVERAGE`
- Confidence constants as bare string values (not enum): `HIGH = "HIGH"`, `MED = "MED"`, `LOW = "LOW"`
- Private constants with underscore prefix: `_EPS`, `_COST_SOURCE`, `_DEFAULT_SITE_WIDTH_M`, `_VALID_CONFIDENCE`, `_REQUIRED_LINE_KEYS`, `_VALID_KINDS`

## Type Hints

**Usage:**
- `from __future__ import annotations` is the first import in every file (both source and test modules). This enables PEP 604 union syntax on Python 3.9+.
- All public function parameters are annotated: `def total_cost(config: dict[str, Any]) -> float:`
- Return types annotated: `-> None`, `-> float`, `-> list[dict]`, `-> dict[str, Any]`, `-> tuple[float, float]`
- Complex types use forward references for self-referencing: `"GrowthDiscountParams | None"`
- Generic collection types consistently used: `dict[str, Any]`, `list[dict]`, `tuple[float, float]`
- Union types use `|` syntax: `str | None`, `float | None`, `Path | str`
- `Literal` type available: `Backend = Literal["mock", "cached", "live"]` in `coolspend/sdk_client.py`
- `TYPE_CHECKING` guard in `coolspend/optimizer.py` line 35: `from typing import TYPE_CHECKING`
- Test functions with `monkeypatch` annotate as `pytest.MonkeyPatch` type

**Patterns found:**
```python
def per_tree_cost(horizon_years: int = OPEX_HORIZON_YEARS) -> float:
def total_cost(config: dict[str, Any]) -> float:
def cost_per_utci_degree(config: dict[str, Any], band_c: float | None = None) -> dict[str, Any]:
def decoded(x_flat: np.ndarray) -> dict:
def validate_top3_with_infrared(top3: list[dict], budget: "SimBudget | None" = None) -> list[dict]:
```

## Imports Organization

**Order:**
1. `from __future__ import annotations` (always first)
2. Standard library: `json`, `logging`, `os`, `math`, `hashlib`, `datetime`, `time`, `warnings`, `pathlib`, `tempfile`, `dataclasses`, `typing`, `uuid`
3. Third-party: `pytest`, `numpy`, `pymoo.*`, `shapely.*`, `pyproj.*`, `alive_progress`
4. Local: `from coolspend.xxx import YYY`

**Grouping:**
- Multi-line imports from same module use parentheses:
```python
from coolspend.spatial_engine import (
    core_weighted_coverage_fraction,
    is_valid_location,
    local_m_to_latlon,
    thermal_relief,
    TREE_CANOPY_RADIUS_M,
)
```

**Lazy/inside-function imports** for heavy SDK to keep module importable offline:
```python
# inside validate_top3_with_infrared() in optimizer.py
from coolspend.sdk_client import (  # noqa: PLC0415
    get_baseline_utci, get_intervention_utci, SimBudget
)
```
This pattern is used in `optimizer.py` (lines 496-501), `cost_model.py` (lines 782, 794), `spatial_engine.py` (line 383), and throughout `sdk_client.py`.

**Path Aliases:**
- Module alias with underscore prefix for private usage: `from coolspend import spatial_engine as _se`
- Constant alias: `from coolspend.bcn_species import SPECIES_TABLE as _BCN_SPECIES`
- No relative imports used; always absolute paths

## Docstring Style

**Module Docstrings (40-90 lines):**
- Purpose statement and project context
- Data-source status (surrogate, mock, real EPW)
- Key function inventory
- Honesty notices and cross-references to requirement docs
- Example from `coolspend/cost_model.py` (lines 1-92): document lifecycle, KPI design, growth-discount rationale, confidence band derivation

**Function Docstrings:**
- Google/NumPy style with `Args:`, `Returns:`, `Raises:` sections
- Brief description followed by detailed explanation
- Examples from `coolspend/optimizer.py`:
```python
def decode(x_flat: np.ndarray) -> dict:
    """Decode a flat chromosome into a tree configuration dict.

    Two chromosome layouts are supported:
      - SPECIES-AWARE (length 3*N_TREES): ...
      - LEGACY (length 2*N_TREES): ...

    Returns:
        {"trees": [{"x_m","y_m","species","active"}, ...], "tree_count": int}
    """
```

**Cross-references:** Requirement codes in docstrings: `(COST-01)`, `(D-07)`, `(SPATIAL-03)`, `(OPT-02)`, `(CONCERNS 1.1)`, `(REMEDIATION)`, `(D-10 / VALID-04)`

**Honesty notes:** Embedded directly in docstrings for surrogate/mock functions:
```
NOT MEASURED — analytical surrogate only. Use in the NSGA-II hot path.
```

## Code Style

**Formatting:**
- No explicit formatter config (no `pyproject.toml`, no `.prettierrc` in project root)
- Code broadly PEP 8 compliant: 4-space indentation, ~100-120 character lines
- Section headers with box-drawing characters:
```python
# ── SECTION NAME ───────────────────────────────────────────────────────
```

**Linting:**
- `# noqa: PLC0415` -- local/inside-function imports (pylint import-outside-toplevel)
- `# noqa: C901` -- function too complex (used on `cost_per_utci_degree`)
- `# noqa: BLE001` -- bare `except Exception` handlers
- `# noqa: E402` -- imports after module-level code (in tests and `optimizer.py`)
- No explicit linter config files detected; rules suppressed inline per-site

**Dataclass Style:**
- `@dataclass(frozen=True)` for immutable data:
```python
@dataclass(frozen=True)
class CostLine:
    key: str
    label: str
    value: float
    unit: str
```
- `@dataclass` (mutable) for editable parameters:
```python
@dataclass
class GrowthDiscountParams:
    ramp_years: float = 25.0
    initial_fraction: float = 0.20
```

## Error Handling

**Patterns:**
1. **Custom exceptions:** `CRSConsistencyError(RuntimeError)` in `coolspend/spatial_engine.py` -- fail-closed guard for CRS round-trip failures. Raised when WGS84->UTM->WGS84 error exceeds 1m.

2. **Fail-open for config loading** in `coolspend/cost_model.py` lines 521-553:
```python
def load_cost_table(path: str | None = None) -> tuple[CostTable, GrowthDiscountParams]:
    """Fail-open: on missing or invalid file, logs a warning and returns defaults."""
    try:
        text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _log.warning("...")
        return DEFAULT_COST_TABLE, DEFAULT_GROWTH_DISCOUNT
```

3. **Guarded bare exceptions** with noqa comment:
```python
except Exception as exc:  # noqa: BLE001
    logger.warning("Pareto plot failed (pipeline continues): %s", exc)
```

4. **SimBudget guard** raises `RuntimeError` when call cap exceeded:
```python
def record(self, label: str) -> None:
    if len(self.log) >= self.max_live_calls:
        raise RuntimeError("SimBudget exceeded: max_live_calls={}")
```

5. **Zero/negative numeric guards:**
```python
if degc_drop is None or degc_drop <= 0:
    return {"value": None, ...}
norms[norms == 0] = 1e-9
denom[denom == 0] = 1e-9
```

6. **Validation with warnings, never raises** -- `cost_table_from_dict()` logs warnings for invalid lines then falls back to defaults

## Logging/Output

**Logging Framework:**
- Standard `logging` module throughout production code
- `print()` only in `if __name__ == "__main__":` smoke-test blocks

**Naming conventions:**
- `logger = logging.getLogger("coolspend.optimizer")` -- explicit namespace name in `optimizer.py`, `sdk_client.py`
- `_log = logging.getLogger(__name__)` -- dynamic name in `cost_model.py`, `app.py`

**Logging Patterns:**
- `_log.info()` for major actions (artifact written, study run complete)
- `_log.warning()` for fallback decisions (missing config, invalid data, matplotlib not installed)
- `_log.warning()` for validation issues: `"cost_table_from_dict: line '%s' value %.4f is non-positive -- falling back to default"`
- No `_log.error()` or `_log.exception()` found in the codebase

## Comments & Documentation

**Section marker comments** (`# ── SECTION ─────`) divide modules into named blocks:
```python
# ── TOP-3 VALIDATION (OPT-03) ─────────────────────────────────────────
# ── GrowthDiscountParams -- editable growth-curve + discount params ────
# ── SIMBUDGET ──────────────────────────────────────────────────────────
```

**Inline annotations:**
- Physical units on constants: `# °C`, `# metres`, `# EUR/tree/yr`
- Source citations: `# SOURCE: nature_nsga2_coolstock.py lines 81-83`
- Bug fix notes: `# POROSITY BUG (CONCERNS 4.2 / T-02-06 -- FIXED):`
- Honesty flags: `# HONESTY NOTICE (CONCERNS 1.1 / T-02-04):`
- Requirement cross-references: `# D-10 / VALID-04: uncertainty interval`
- Status tags: `# DECLARED`, `# PENDING`, `# REQUIRES_VERIFICATION`
- Referenced remediation: `# REMEDIATION -- Option A`

## API / Function Design

**Return Value Convention:**

Complex functions return a **standard metric dict** with consistent keys:
```python
{
    "value":         float | None,    # headline number
    "value_lo":      float | None,    # lower uncertainty bound
    "value_hi":      float | None,    # upper uncertainty bound
    "unit":          str,             # e.g. "EUR/degC"
    "confidence":    str,             # "HIGH" | "MED" | "LOW"
    "sources":       list[str],       # provenance anchors
    "note":          str,             # human-readable narrative
    "metric_id":     str,             # stable snake_case identifier
}
```
This pattern is used in `cost_per_utci_degree()` in `coolspend/cost_model.py` and referenced throughout.

**Dict-as-config pattern:** Functions consume a monolithic `config: dict` and read specific keys with defaults:
```python
tree_count = int(config.get("tree_count", 0))
hot_delta = config.get("delta_utci_c")
```

**Parameter design:**
- Typed with defaults: `def run_optimisation(budget_eur: float = DEFAULT_BUDGET_EUR, ...)`
- Optional params with `None` fallback: `def cost_per_utci_degree(config, band_c: float | None = None, growth_discount: "GrowthDiscountParams | None" = None)`
- `Path` params accept `str | Path` with conversion at function entry

## Module Design

**File Layout Convention (consistent across all modules):**
1. Module docstring (30-90 lines with purpose, honesty, cross-refs)
2. `from __future__ import annotations`
3. Standard library imports
4. Logger setup (`logger = logging.getLogger("coolspend.xxx")`)
5. Third-party imports
6. Local imports
7. Constants and module-level dataclasses
8. Private helper functions
9. Public API functions
10. `if __name__ == "__main__":` smoke test block

**Exports:** No `__all__` defined in any module; public API surface is implicit. Private names prefixed with underscore.
`coolspend/__init__.py` only exports `__version__ = "0.1.0"`.

## Configuration Patterns

**Environment Variables:**
- `INFRARED_BACKEND` -- `"mock"` (default) | `"cached"` | `"live"`
- `INFRARED_API_KEY` -- required for live Infrared SDK calls
- Read at dispatch time via private function, never at import:
```python
def _backend() -> Backend:
    return os.environ.get("INFRARED_BACKEND", "mock")
```
- In tests, stripped via `monkeypatch.delenv("INFRARED_API_KEY", raising=False)`

**JSON config file:**
- `coolspend/cost_config.json` -- editable cost table (CostLine array + GrowthDiscountParams)
- Loaded via `load_cost_table()` with fail-open: returns defaults on missing/invalid file
- Validated via `cost_table_from_dict()` with per-line fallback

**Module constants:**
- Configuration that does NOT require user editing is hardcoded as module-level constants
- Each constant annotated with UNIT and SOURCE comments:
```python
HOURS_PER_DEGC_REF: float = 200.0
# UNIT: annual UTCI-hours-above-32°C per °C equivalent mean-UTCI drop
# SOURCE: derived (Barcelona EPW mean excess + "12°C Tmrt ≈ 3-5°C UTCI" anchor)
# REQUIRES_VERIFICATION: Plan 05-03 replaces with empirical calibration RMSE.
```

**Paths computed relative to `__file__`:**
```python
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
CACHE_DIR = BASE / "cache" / "infrared"
_DEFAULT_CONFIG_PATH = Path(__file__).parent / "cost_config.json"
```

## Git Conventions

**Commit Message Format:** Conventional Commits with scopes and optional RED/GREEN markers

Types observed: `feat`, `fix`, `test`, `docs`, `refactor`
Scopes: phase codes (`06-02`), domain (`cost`, `lidar`, `species-aware`, `anywhere+metric`)

```commit
feat(anywhere+metric): scan ANY Barcelona location + cooled-footprint headline metric
fix(cost): wire real Barcelona EPW + fix UTCI-hours key mismatch & band scaling
test(06-02): add failing tests for KPI routing through growth+discount (RED)
refactor(05-04): delete naive-baseline machinery and improvement_vs_naive_pct (D-12)
```

TDD RED/GREEN markers in commit messages: `(RED)` for failing tests, `(GREEN)` for implementation pass.

---

*Convention analysis: 2026-05-27*
