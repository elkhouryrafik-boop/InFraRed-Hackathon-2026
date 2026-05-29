# Testing Patterns

**Analysis Date:** 2026-05-27

## Test Framework

**Runner:**
- pytest (no explicit config -- discovered via test file naming)
- No `pytest.ini`, `setup.cfg`, `pyproject.toml` pytest configuration found in project root
- No coverage configuration (no `.coveragerc` detected)
- No test markers defined in configuration (markers used but without registration)

**Assertion Library:**
- Standard `pytest` assertions with `pytest.approx()` for floating-point comparison
- Standard Python `assert` for boolean checks and `in`/`not in` for substring checks
- `math.isfinite()` for numeric validity checks

**Run Commands:**
```bash
pytest                                      # Run all tests
pytest -v                                   # Verbose mode
pytest coolspend/tests/                     # Also works with explicit path
pytest coolspend/tests/test_cost_model.py   # Single test file
pytest -k "cost"                            # Run tests matching keyword
python -m pytest                            # Via module invocation
```

## Test File Organization

**Location:**
- All tests live in `coolspend/tests/`, mirroring source structure
- Source module `coolspend/cost_model.py` -> test file `coolspend/tests/test_cost_model.py`
- `conftest.py` at `coolspend/tests/conftest.py` (single shared fixtures file)

**Naming:**
- Test files: `test_<module_name>.py` (e.g., `test_spatial_engine.py`, `test_rules_engine.py`)
- Test functions: `test_<what>_<expected_outcome>()` (e.g., `test_inside_building_rejected`, `test_kpi_not_raw_delta_tmrt`)
- Test classes: PascalCase grouping by component: `class TestGrowthCoolingFraction`, `class TestDefaultCostTable`, `class TestSpacingPenalty`
- Helper/private functions prefixed with underscore: `_tree()`, `_config()`, `_default_dict()`

**Structure:**
```
coolspend/tests/
├── __init__.py                        # Package marker ("Test package marker for coolspend")
├── conftest.py                        # Shared fixtures (autouse site origin reset)
├── test_app.py                        # Gradio UI tests (headless, 233 lines)
├── test_app_pipeline.py               # run_decision pipeline (191 lines)
├── test_app_viz.py                    # Visualization rendering (150 lines)
├── test_calibration.py                # Calibration study (516 lines)
├── test_coordinate_frame.py           # UTM CRS boundary tests (300 lines)
├── test_cost_config.py                # Cost config JSON load/edit (330 lines)
├── test_cost_model.py                 # KPI math + CostTable (565 lines)
├── test_decision_artifact.py          # Output artifact JSON (313 lines)
├── test_optimizer.py                  # NSGA-II integration (410 lines)
├── test_requirements.py               # HF Spaces deploy contract (170 lines)
├── test_rules_engine.py               # Ecological/spacing score (321 lines)
├── test_sdk_client.py                 # SDK dispatch offline (211 lines)
├── test_sdk_client_live.py            # Live SDK path with fake (279 lines)
├── test_spatial_engine.py             # Collision validity (111 lines)
└── test_surrogate.py                  # Thermal surrogate (337 lines)
```

Total: 17 test files, 4,465 lines.

## Test Categories

**Unit Tests (pure arithmetic, no I/O):**
- `test_cost_model.py` -- KPI math, growth/discount functions, CostTable totals
- `test_rules_engine.py` -- spacing_penalty, species_diversity_score, ecological_score
- `test_surrogate.py` -- delta_tmrt_surrogate, shade_efficiency, thermal_relief, core_weighted_coverage_fraction
- `test_cost_config.py` -- load_cost_table, cost_table_from_dict, dictionary round-trip
- `test_calibration.py` -- compute_fit (RMSE, R2), rank_stability

**Integration Tests (mock backend):**
- `test_optimizer.py` -- run_optimisation, select_top3, validate_top3_with_infrared (mock), topsis_rank
- `test_decision_artifact.py` -- save_outputs, before-after record, full pipeline through mock
- `test_app_pipeline.py` -- run_decision with mock backend, determinism across runs
- `test_spatial_engine.py` -- load_site, is_valid_location against bundled fixture
- `test_coordinate_frame.py` -- CRS round-trip via pyproj (citywide accuracy, fail-closed guard)

**Live/SDK Path Tests (fake SDK injection, no real key):**
- `test_sdk_client_live.py` -- monkeypatches `infrared_sdk` into `sys.modules` with `MagicMock` to exercise live code path offline
- `test_sdk_client.py` -- cached backend reads/writes, cache provenance labelling, SimBudget

**UI Tests (headless Gradio):**
- `test_app.py` -- build_demo returns Blocks, on_submit mock returns valid 4-tuple, bad geojson no crash, no traceback in UI
- `test_app_viz.py` -- render_before_after returns valid PNG, handles empty trees, tempfile fallback

**Deployment Contract:**
- `test_requirements.py` -- requirements.txt pins, README YAML header, gradio version drift guard, mock/live documentation

**Distinction mechanism:**
- No pytest markers (`@pytest.mark.slow`, `@pytest.mark.live`) -- all tests run together
- Live-path tests use fake SDK injection (`test_sdk_client_live.py`), so all tests are truly offline
- Calibration tests use `_ensure_mock_backend(monkeypatch)` helper to strip live env vars

## Fixtures

**File: `coolspend/tests/conftest.py`** (lines 1-27)

```python
@pytest.fixture(autouse=True)
def _reset_site_origin():
    """Reset spatial_engine's per-site UTM origin state before (and after) each test."""
    spatial_engine.reset_site_origin()
    yield
    spatial_engine.reset_site_origin()
```

- Single autouse fixture that wraps every test with a clean spatial_engine origin state
- Resets mutable module globals (`SITE_WIDTH_M`, `SITE_DEPTH_M`, `_SITE_ORIGIN_E`, `_SITE_ORIGIN_N`)
- Double yield pattern: reset before AND after each test

**Module-scoped fixtures (in individual test files):**

| File | Fixture | Scope | Purpose |
|------|---------|-------|---------|
| `test_optimizer.py` | `small_result` | module | `run_optimisation(n_gen=20, pop_size=40, seed=42)` -- shared Pareto result |
| `test_optimizer.py` | `top3_configs` | module | `select_top3(small_result)` -- pre-extracted Top-3 |
| `test_optimizer.py` | `real_result` | module | `run_optimisation(n_gen=40, pop_size=40, seed=42)` -- larger front for non-degeneracy tests |
| `test_spatial_engine.py` | `site` | module | `load_site()` -- cached site geometry |
| `test_app_viz.py` | `minimal_config` | function | Minimal tree config with 1 active tree |
| `test_app_viz.py` | `minimal_before_after` | function | Before-after dict matching run_decision contract |
| `test_app_viz.py` | `empty_trees_config` | function | Config with 0 active trees |
| `test_sdk_client_live.py` | `_clean_sdk_modules` | autouse | Remove fake infrared_sdk from sys.modules before/after |
| `test_app_pipeline.py` | `_force_mock_backend` | autouse | Strip live env vars before each test |
| `test_requirements.py` | `req_text` | module | `requirements.txt` content |
| `test_requirements.py` | `readme_text` | module | `README.md` content |
| `test_requirements.py` | `spaces_header` | module | YAML front-matter extracted from README |

**Helper functions (used as fixture-like data builders):**

| File | Helper | Purpose |
|------|--------|---------|
| `test_rules_engine.py` | `_config(*trees)` | Build config dict from tree dicts |
| `test_rules_engine.py` | `_tree(x, y, species, active)` | Build single tree dict |
| `test_cost_config.py` | `_default_dict()` | Build dict mirroring shipped cost_config.json defaults |
| `test_calibration.py` | `_ensure_mock_backend(monkeypatch)` | Strip API env vars safely |
| `test_sdk_client_live.py` | `_make_fake_infrared_sdk()` | Build fake infrared_sdk module tree |
| `test_sdk_client_live.py` | `_install_fake_sdk(fake_sdk)` | Register fake SDK in sys.modules |
| `test_decision_artifact.py` | `_make_config(tree_count, delta_utci_c, eco, label)` | Build hand-made config for TOPSIS isolation |
| `test_calibration.py` | `_make_configs(n, offset)` | Build synthetic configs with known surrogate/real deltas |

## Mocking Strategy

**Monkeypatch is the primary mocking tool** (from `pytest.MonkeyPatch`):

**Environment variable manipulation (most common):**
```python
monkeypatch.delenv("INFRARED_API_KEY", raising=False)    # Strip key
monkeypatch.delenv("INFRARED_BACKEND", raising=False)     # Strip backend
monkeypatch.setenv("INFRARED_BACKEND", "cached")           # Set backend
monkeypatch.setenv("INFRARED_API_KEY", DUMMY_KEY)          # Set dummy key (live path tests)
```

**Function replacement:**
```python
# test_optimizer.py -- prove hot path is SDK-free
monkeypatch.setattr(sdk_client_module, "get_intervention_utci", _raise)

# test_coordinate_frame.py -- simulate CRS drift
monkeypatch.setattr(se, "local_m_to_latlon", _bad_inverse)

# test_app.py -- simulate unexpected exception in run_decision
monkeypatch.setattr(app, "run_decision", _explode)

# test_optimizer.py -- capture baseline geometry for inspection
monkeypatch.setattr(sdk_module, "get_baseline_utci", _capture_baseline)
```

**Full SDK module injection (`test_sdk_client_live.py` only):**
```python
# Build a fake infrared_sdk tree with MagicMock for every required method
fake_sdk, fake_client = _make_fake_infrared_sdk()
_install_fake_sdk(fake_sdk)  # registers in sys.modules
```
This is the ONLY test file that fakes a full third-party SDK. It creates a `types.ModuleType` tree with `MagicMock` stubs for `InfraredClient`, `UtciModelRequest`, `AnalysesName`, etc.

**What is mocked:**
- `get_intervention_utci` -- to prove it is never called in hot path
- `local_m_to_latlon` -- to simulate CRS drift (fail-closed guard tests)
- `save_outputs` -- to redirect artifact output to tmp_path
- `run_decision` -- to simulate unexpected exceptions in UI error handling
- Entire `infrared_sdk` package -- to test live code path offline

**What is NOT mocked:**
- `spatial_engine` geometry functions (tested with real bundled `angels_site.geojson`)
- `cost_model` arithmetic (tested with real constants)
- `rules_engine` scoring functions (tested with pure arithmetic)
- `pyproj` CRS converters (real PROJ data, offline capable)
- `shapely` geometry operations (real library, offline capable)

## Test Data

**GeoJSON fixtures:**
- `coolspend/data/angels_site.geojson` -- bundled offline fixture (Plaça dels Àngels, Barcelona)
  - Contains `site_boundary` polygon, two `building` polygons, one `street` linestring
  - Loaded by `spatial_engine.load_site()` and used in `test_spatial_engine.py`, `test_optimizer.py`, `test_coordinate_frame.py`

**Generated test data:**
- Inline dicts in test files for cost config, tree configs, geometry payloads
- `_default_dict()` helper builds a complete cost config dict from `DEFAULT_COST_TABLE`
- `test_sdk_client_live.py` plants and reads cache files in `tmp_path`
- `test_calibration.py` builds synthetic configs via `_make_configs(n, offset)` with known surrogate_pred/real_delta values

**No external data files used in tests** beyond the bundled GeoJSON fixture.

## Test Structure

**Suite Organization (typical pattern):**

```python
class TestFeatureName:
    """Brief description of what this class covers."""

    def test_case_description(self) -> None:
        """One-line docstring explaining expected behavior."""
        # Arrange (often inline)
        config = _config(_tree(0.0, 0.0), _tree(1.0, 0.0))
        # Act
        result = spacing_penalty(config)
        # Assert
        assert result > 0.0
```

**Patterns:**
- **Triple-A (Arrange-Act-Assert)** -- clean separation in each test
- **Inline docstrings** on every test function (one-liner describing behavior)
- **Module-level docstring** describing the test file's scope and requirements covered
- **Floating-point comparison** uses `pytest.approx(expected)`, never `==`
- **Substring matching** for error messages: `with pytest.raises(RuntimeError, match="SimBudget exceeded")`
- **Determinism tests** -- comparing identical and different seeds: `test_seed_determinism_same_seed_identical`, `test_seed_determinism_different_seed_differs`
- **Parametrized tests** sparingly used -- `@pytest.mark.parametrize("n", [0, 1, 25])` in `test_cost_model.py`
- **File I/O tests** use `tmp_path` and `monkeypatch` (never real filesystem)

**Test class pattern:** Tests are organized into classes when multiple related tests share setup. Classes are NOT used when tests are simple standalone functions.

## Coverage

**No coverage tool configured** -- no `.coveragerc` or `--cov` flags found. Coverage is manual/approximate.

**Modules with tests:**
- `cost_model.py` -- `test_cost_model.py` (565 lines) + `test_cost_config.py` (330 lines) -- thorough coverage
- `optimizer.py` -- `test_optimizer.py` (410 lines) + `test_decision_artifact.py` (313 lines) -- thorough coverage
- `spatial_engine.py` -- `test_spatial_engine.py` (111 lines) + `test_surrogate.py` (337 lines) + `test_coordinate_frame.py` (300 lines) -- thorough coverage
- `rules_engine.py` -- `test_rules_engine.py` (321 lines) -- thorough coverage
- `sdk_client.py` -- `test_sdk_client.py` (211 lines) + `test_sdk_client_live.py` (279 lines) -- thorough coverage
- `calibration.py` -- `test_calibration.py` (516 lines) -- thorough coverage
- `app.py` -- `test_app.py` (233 lines) -- moderate coverage
- `app_pipeline.py` -- `test_app_pipeline.py` (191 lines) -- good coverage
- `app_viz.py` -- `test_app_viz.py` (150 lines) -- good coverage

**Modules with minimal/indirect test coverage:**
- `bcn_data.py` -- no dedicated test file (exercised indirectly by optimizer pipeline)
- `bcn_species.py` -- no dedicated test file (exercised indirectly via species-optimizer tests)
- `bcn_lidar.py` -- no dedicated test file
- `main.py` -- tested only in `test_decision_artifact.py` via `test_main_writes_artifact`

**Estimated overall coverage:** ~65-70% of source lines (all core logic has tests; data modules and main entry point are thinner)

## CI/CD

**No CI pipeline detected:**
- No `.github/workflows/` directory
- No tox.ini
- No pre-commit configuration
- No coverage upload configuration

## Notes on Specific Test Files

**`test_cost_model.py`** (565 lines, largest test file):
- Tests per_tree_cost, total_cost, cost_per_utci_degree KPI
- CostTable/CostLine dataclass tests in `TestCostLineDataclass`, `TestDefaultCostTable`
- Growth/discount function tests in `TestGrowthCoolingFraction`, `TestDiscountedLifetimeDegc`, `TestDiscountedTotalCost`, `TestGrowthDiscountParams`
- KPI routing tests in `TestCostPerUtciDegreeGrowthDiscount`
- All tests are pure arithmetic, no I/O

**`test_calibration.py`** (516 lines):
- Tests generate_study_configs, SimBudget, run_calibration_study, compute_fit, rank_stability
- Test classes for each function: `TestGenerateStudyConfigs`, `TestStudySimBudget`, `TestComputeFit`, `TestRankStability`
- Artifact JSON validation in `TestCalibrationArtifact`
- Dimensional contract tests ensure `HOURS_PER_DEGC_REF` is imported, not redefined
- Helper `_ensure_mock_backend(monkeypatch)` strips env vars

**`test_optimizer.py`** (410 lines):
- Module-scoped `small_result` fixture runs `run_optimisation(n_gen=20, pop_size=40)` once
- Tests: Pareto min size, no SDK in hot path (monkeypatch), invalid placements excluded, select_top3 distinct, exactly 3 validation calls, budget constraint active
- REMEDIATION tests: non-degenerate front, distinct deltas/costs, seed determinism, no naive baseline
- WAVE-2 REMEDIATION: baseline geometry polygon_lonlat

**`test_sdk_client_live.py`** (279 lines):
- Unique approach: injects fake `infrared_sdk` into `sys.modules` to exercise live code path offline
- `_make_fake_infrared_sdk()` builds a complete fake module tree with `MagicMock`
- Tests: import without SDK, live without key (raises), live calls SDK and caches, cached replays live result, key never logged
- `_clean_sdk_modules` autouse fixture removes fake modules before/after each test

**`test_app.py`** (233 lines):
- Tests Gradio UI headless: build_demo, on_submit mock outputs, bad GeoJSON no crash, no traceback in UI (security L1)
- Headless launch smoke test with infrastructure skip on OSError/httpx errors

## TDD Pattern

The git log shows evidence of RED/GREEN TDD workflow:
```
test(06-02): add failing tests for KPI routing through growth+discount (RED)
feat(06-02): route cost_per_utci_degree through growth+discount (GREEN)
test(06-02): add failing tests for growth curve + discount functions (RED)
feat(06-02): implement GrowthDiscountParams + growth/discount functions (GREEN)
```

Tests are written first (RED commit), then implementation (GREEN commit). This pattern is visible in the git history with explicit `(RED)` and `(GREEN)` markers in commit messages.

---

*Testing analysis: 2026-05-27*
