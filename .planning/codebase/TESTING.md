# Testing Patterns

**Analysis Date:** 2026-06-01

## Test Framework

**Runner:**
- pytest 9.0.x (caches show `pytest-9.0.3`).
- No `pytest.ini` / `pyproject.toml` / `setup.cfg` / `tox.ini` is committed — pytest runs with defaults and auto-discovers `test_*.py` under `coolspend/tests/`.

**Assertion Library:**
- Plain `assert` plus `pytest.approx` for float comparisons. No separate assertion library.

**Shared fixtures:**
- `coolspend/tests/conftest.py` defines one autouse fixture, `_reset_site_origin`, that calls `spatial_engine.reset_site_origin()` before and after every test. This prevents the per-site UTM-CRS origin state (`SITE_WIDTH_M`, `SITE_DEPTH_M`, `_SITE_ORIGIN_E/N` module globals) from leaking between tests and causing order-dependent failures in the optimizer/surrogate geometry frame. Any new test that mutates site origin relies on this reset — do not remove it.

**Run commands:**
```bash
# From repo root (C:\Users\Rafik\OneDrive\Python Resources\Hackathon)
python -m pytest coolspend/tests              # run the whole suite
python -m pytest coolspend/tests --co -q      # collect-only (count tests, no run)
python -m pytest coolspend/tests/test_cost_model.py        # one module
python -m pytest coolspend/tests/test_cost_model.py -k roundtrip   # filter by name
```

## VERIFIED Test Count vs PAPER Claim

PAPER.md Section 6.3 ("Reproducibility and security posture") claims:
> "The Python test suite passes (392 passed / 1 skipped at the last run)" — i.e. **393 tests total**.

**Verified on 2026-06-01** by running collection in this environment:
```
python -m pytest coolspend/tests --co -q  →  393 tests collected in 5.43s
```
The collected total (**393**) exactly matches the paper's 392 passed + 1 skipped = 393. The paper's count is accurate. (Collection was run; a full pass/skip execution was not re-run here, so the 392/1 split is the paper's last-run figure, not re-measured. The skipped test is most likely a provenance test that `pytest.skip`s when an optional artifact such as `scored_grid.geojson` or numpy is absent — see Provenance section.)

## Test File Organization

**Location:** Co-located in `coolspend/tests/`, one `test_<module>.py` per source module. 37 test modules + `__init__.py` + `conftest.py`.

**Largest suites (test count per file, from collection):**

| File | Tests | Covers |
|------|------:|--------|
| `test_cost_model.py` | 55 | Per-tree CapEx/OpEx model, €/°C KPI, growth-ramp + discount math |
| `test_calibration.py` | 47 | Calibration study: RMSE, R², error band (1.96·RMSE), SimBudget cap |
| `test_rules_engine.py` | 31 | Decision rules engine |
| `test_cost_config.py` | 25 | `cost_config.json` load / round-trip / fail-open / validation |
| `test_surrogate.py` | 23 | ΔTmrt surrogate, thermal relief, provenance citations |
| `test_requirements.py` | 15 | Dependency / requirements checks |
| `test_optimizer.py` | 14 | Greedy / NSGA-II allocation |
| `test_coordinate_frame.py` | 14 | UTM/lon-lat coordinate conversions |
| `test_sdk_client.py` | 13 | Infrared SDK client (cached) |
| `test_smart_placement.py` | 11 | Building/street-aware placement |

Remaining modules (3–10 tests each): `test_app_pipeline`, `test_citywide`, `test_population`, `test_ground_analysis`, `test_growth`, `test_ecology`, `test_cooling_estimator`, `test_epw_weather`, `test_decision_artifact`, `test_candidate_slots`, `test_app_viz`, `test_api_server`, `test_sensitivity`, `test_sdk_client_live`, `test_design_metrics`, `test_canopy_denominator`, `test_app`, `test_spatial_engine`, `test_shade_gain_placement`, `test_provenance`, `test_placement_inputs`, `test_placement_audit`, `test_osm_features`, `test_hours_per_degc`, `test_osm_roads`, `test_calibrated_band`.

## Test Structure

Two coexisting styles:

**Class-grouped (preferred for a feature surface)** — `coolspend/tests/test_cost_config.py` groups related cases under `TestCostTableRoundTrip`, `TestLoadCostTable`, `TestLoadCostTableFailOpen`, `TestCostTableFromDictEdits`, `TestCostPerUtciDegreeBackwardCompat`. Each method has a one-line docstring stating the exact invariant:
```python
class TestLoadCostTable:
    """load_cost_table() reads cost_config.json and returns correct defaults."""

    def test_capex_total_is_2200(self) -> None:
        """load_cost_table() → table.capex_total() == 2200.0."""
        table, _ = load_cost_table()
        assert table.capex_total() == pytest.approx(2200.0)
```

**Flat module-level functions** — `coolspend/tests/test_provenance.py`, `test_placement_audit.py` use top-level `def test_*` functions. Use this for a small, focused module.

Every test file opens with a docstring tying the tests to a paper limitation or a design decision ID (e.g. "Guards PAPER Limitation #1's fix", "COST-04 / D-05 / Plan 06-03 Task 1", "D-04: compute_fit → RMSE, R², error_band_c (1.96*RMSE)"). Match this: state *what invariant or paper claim the test defends*.

## What the Suite Covers (key guarantees)

**Provenance regression (R²=1.0)** — `coolspend/tests/test_provenance.py`:
- `test_weights_are_a_convex_combination` — `COMPOSITE_B_WEIGHTS` sum to 1.0, all ≥ 0.
- `test_composite_b_reproduces_exactly_over_all_cells` — recompute `composite_score_B` for all ≥400 cells; `max_abs_residual < 1e-9` (exact to float epsilon).
- `test_weights_are_recoverable_from_data_when_numpy_present` — least-squares recovers the weights from data with `r2 > 0.999999`.
- `test_reproduce_single_cell_matches_helper` — synthetic cell hits the documented weight formula exactly.
- **Skip behavior:** `pytest.skip(...)` when `scored_grid.geojson` is not present or numpy is missing — this is the likely source of the paper's "1 skipped".

**Placement audit (independent OSM re-check)** — `coolspend/tests/test_placement_audit.py`:
- `test_tree_on_building_is_flagged` — a tree on a stubbed building footprint sets `n_on_building == 1` and `all_valid is False`.
- `test_clear_well_spaced_trees_pass` — clear, spaced trees give `n_on_building == 0`, `all_valid is True`.
- `test_clump_is_flagged` — trees under the 8 m spacing floor are flagged `n_too_close`.
- `test_empty_trees_safe` — empty input is safe (`all_valid is True`).
- The audited module `coolspend/placement_audit.py` re-fetches OSM buildings via a *second independent data path* and re-checks every placed tree; PAPER §6.3 states it "confirms zero trees placed on buildings across the committed plan."

**Calibration / uncertainty band** — `coolspend/tests/test_calibration.py` (+ `test_calibrated_band.py`):
- Deterministic study-config generation (same seed → same configs), coverage-fraction monotonicity, required keys.
- `compute_fit` → RMSE, R², `error_band_c = 1.96 * RMSE`.
- `test_budget_cap_is_n_plus_1` asserts the study uses `SimBudget(max_live_calls=n+1)`, not a hardcoded cap of 3 (design decision D-03) — a live-API-call cap test.

**Cost model / config** — `test_cost_model.py` (55) + `test_cost_config.py` (25): KPI math, growth-ramp/discount, and the full fail-open + validation contract for `cost_config.json` (missing path, invalid JSON, non-dict root, non-positive value, invalid confidence tag, missing key all fall back without raising).

## Mocking & Fixtures

- **Mocking framework:** `pytest`'s `monkeypatch` fixture (e.g. `test_budget_cap_is_n_plus_1(self, monkeypatch)`). No `unittest.mock`-heavy patterns observed.
- **Local stub fixtures:** small per-file fixtures like `_stub_building` in `test_placement_audit.py` inject a fake building footprint so the OSM-dependent audit can be exercised offline.
- **Real cached data over mocks:** the project's stated bar is "no mocks except the real Infrared API." Tests run against **cached real artifacts** under `coolspend/cache/` (`cache/infrared/utci_baseline_*.json`, `utci_intervention_*.json`, `cache/bcn_data/`, `cache/bcn_lidar/`) rather than fabricated fixtures. `test_sdk_client_live.py` is the live-API counterpart to the cached `test_sdk_client.py`.
- **Temp files:** fail-open tests write throwaway configs with `tempfile.NamedTemporaryFile(... delete=False)` and clean up in a `finally: os.unlink(...)`.

## Float Assertions

Always `pytest.approx` for monetary/physical equality (`== pytest.approx(2200.0)`); exact `<` epsilon bounds for reproduction residuals (`< 1e-9`, `< 1e-12`).

## Web Tests

- Vitest is configured (`web/vitest.config.ts`); scripts in `web/package.json`: `npm test` → `vitest run`, `npm run test:watch` → `vitest`.
- The **enforced** web gate per PAPER §6.3 is the type-check + build, not unit tests:
```bash
cd web
npm run typecheck    # tsc -b --noEmit
npm run build        # tsc -b && vite build  — must build clean
```

---

*Testing analysis: 2026-06-01*
