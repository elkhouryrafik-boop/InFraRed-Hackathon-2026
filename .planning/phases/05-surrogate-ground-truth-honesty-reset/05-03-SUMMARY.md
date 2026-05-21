---
phase: 05-surrogate-ground-truth-honesty-reset
plan: 03
subsystem: calibration
tags: [calibration, surrogate, validation, utci, tdd, rmse, rank-stability]
dependency_graph:
  requires:
    - 05-01  # CRS round-trip guard (assert_crs_roundtrip in _live_utci)
    - 05-02  # HOURS_PER_DEGC_REF defined in cost_model; utci_hours_above routing
  provides:
    - calibration study (coolspend/calibration.py)
    - 10-config RMSE/R2/band artifact (outputs/calibration_study.json when run)
    - ranking stability both ways (D-05)
  affects:
    - coolspend/cost_model.py (cost_per_utci_degree band_c param now has an empirical source)
    - STATE.md (PRE_CALIBRATION_BAND_C can be replaced with RMSE from live run)
tech_stack:
  added:
    - scipy.stats.spearmanr / kendalltau (rank correlation)
    - ladybug_comfort (installed; required by nature_metrics.utci_hours_above)
  patterns:
    - TDD (RED then GREEN: failing tests committed before implementation)
    - SDK imports inside functions only (convention: no module-top SDK imports)
    - live-then-cache operator procedure (D-01: INFRARED_BACKEND=live writes fixtures)
    - Separate SimBudget(n+1) for study; optimizer Top-3 cap=3 untouched (D-03)
    - Dimensional contract: HOURS_PER_DEGC_REF imported, not re-defined (D-04)
key_files:
  created:
    - coolspend/calibration.py
    - coolspend/tests/test_calibration.py
  modified: []
decisions:
  - "D-02: 10 configs, coverage-swept, seed=42, sorted ascending by coverage_fraction"
  - "D-03: Study SimBudget(max_live_calls=n+1=11) distinct from Top-3 cap=3"
  - "D-04: error_band_c = 1.96 * RMSE (95% empirical band, documented multiplier)"
  - "D-05: rank_stability reports both set-overlap headline (naming rank swaps) and Spearman/Kendall over full set"
  - "Rule 3 deviation: installed ladybug_comfort (required by nature_metrics.py at import time)"
  - "NaN guard added for scipy ConstantInputWarning when mock data produces constant real UTCI"
metrics:
  duration: 25m
  completed: "2026-05-21"
  tasks_completed: 2
  files_created: 2
  tests_passed: 47
---

# Phase 5 Plan 03: Calibration Study (Surrogate Ground-Truth) Summary

**One-liner:** 10-config coverage-swept calibration study with RMSE/R2/1.96*RMSE band and dual-axis ranking stability (set-overlap headline + Spearman/Kendall tau) using a separate SimBudget(11), live-then-cache operator procedure documented.

## What Was Built

### coolspend/calibration.py (481 lines)

Four public functions implementing the full calibration pipeline:

**`generate_study_configs(n=10, seed=42) -> list[dict]`**
- Generates exactly n configs deterministically (seeded numpy RandomState)
- Builds a valid-location pool via rejection sampling (is_valid_location)
- Sweeps tree_count from 1 to min(n_valid, 12) via linspace, ensuring monotonic coverage growth
- Computes core_weighted_coverage_fraction and thermal_relief per config
- Sorts by coverage_fraction ascending (D-02 explicit sweep)

**`run_calibration_study(n=10, out_path="outputs/calibration_study.json") -> dict`**
- Creates `SimBudget(max_live_calls=n+1)` — separate from optimizer Top-3 cap of 3 (D-03)
- Calls get_baseline_utci once + get_intervention_utci once per config
- Computes surrogate_pred_utci_delta_c via `hours_reduced / HOURS_PER_DEGC_REF` (D-04 dimensional contract)
- Appends fit + rank_stability to result dict and writes outputs/calibration_study.json (no secrets)

**`compute_fit(configs) -> dict`**
- RMSE = sqrt(mean((pred-real)^2))
- R2 = 1 - SS_res/SS_tot; guard SS_tot==0 -> r2=None
- error_band_c = 1.96 * RMSE (95% empirical band, multiplier documented)

**`rank_stability(configs) -> dict`**
- Spearman rho + Kendall tau over full config set (scipy.stats)
- Set-overlap Top-3: counts shared indices between surrogate and real Top-3
- Named rank swaps: "config_N: surrogate rank A -> real rank B" for shared members in different positions
- Headline: "{n}/3 surrogate Top-3 stayed Top-3 under real UTCI"
- NaN guard for scipy ConstantInputWarning (mock data with constant real UTCI delta)

## Live-Then-Cache Operator Procedure (D-01)

The calibration study is designed for ONE live run, then offline replay:

```bash
# Step 1: Live run (one-time, when INFRARED_API_KEY is available at hackathon)
export INFRARED_BACKEND=live
export INFRARED_API_KEY=<your-key>
python -m coolspend.calibration
# Fixtures auto-written to coolspend/cache/infrared/ by sdk_client._dispatch

# Step 2: Offline replay (CI, review, subsequent analysis)
export INFRARED_BACKEND=cached
python -m coolspend.calibration

# Step 3: Tests (always offline, no key required)
pytest coolspend/tests/test_calibration.py -x
# (runs with INFRARED_BACKEND=mock by default)
```

After a live run, `outputs/calibration_study.json` will contain real Infrared UTCI deltas
and the empirical RMSE/R2/band will be grounded in measured data, not mock scalars.
The `backend` field in each config's `validated_backend` records which backend produced each result.

## Separate SimBudget (D-03)

| Budget | Owner | Cap | Purpose |
|--------|-------|-----|---------|
| `SimBudget(max_live_calls=3)` | optimizer.validate_top3_with_infrared | 3 | Headline 3 live calls for the decision artifact |
| `SimBudget(max_live_calls=n+1)` | calibration.run_calibration_study | 11 | Study: 1 baseline + 10 interventions |

The Top-3 cap of 3 in optimizer.py is UNCHANGED (grep-verified in test_calibration.py).

## Dimensional Contract (Critical — D-04)

```python
# surrogate UTCI prediction (inside run_calibration_study):
from nature_metrics import utci_hours_above               # noqa: PLC0415
from coolspend.cost_model import HOURS_PER_DEGC_REF      # noqa: PLC0415

hours_reduced = baseline_utci_hours - intervention_uh     # h/yr reduction
cfg["surrogate_pred_utci_delta_c"] = round(hours_reduced / HOURS_PER_DEGC_REF, 3)  # °C
```

Both sides of the RMSE pair are in degrees Celsius:
- **pred** = `surrogate_pred_utci_delta_c` (via HOURS_PER_DEGC_REF, same conversion as KPI)
- **real** = `real_delta_utci_c` (measured Infrared UTCI, baseline - intervention, °C)

`cost_per_utci_degree()` is NOT used here (it returns EUR/°C, not a temperature delta).

## Test Results

```
pytest coolspend/tests/test_calibration.py -v
47 passed in 3.10s
```

Test classes:
- `TestGenerateStudyConfigs` (8 tests): determinism, non-decreasing coverage_fraction, required keys, range, span
- `TestStudySimBudget` (3 tests): cap=n+1, RuntimeError on excess, optimizer cap=3 unchanged
- `TestRunCalibrationStudyStructure` (5 tests): result keys, n_configs, real_utci keys, surrogate_pred, seed
- `TestComputeFit` (7 tests): RMSE, R2, error_band=1.96*RMSE, SS_tot==0 guard, n count
- `TestRankStability` (8 tests): all keys, rho/tau=1.0 for perfect order, set_overlap, headline, list type, range, rounding
- `TestCalibrationArtifact` (7 tests): file written, reloadable, fit/rank_stability keys, no secret, disclaimer
- `TestDimensionalContract` (3 tests): HOURS_PER_DEGC_REF imported, no independent constant, pred >= 0
- `TestFunctionExists` (6 tests): all 4 functions + 2 constants

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed ladybug_comfort dependency**
- **Found during:** Task 1 implementation (run_calibration_study import of nature_metrics)
- **Issue:** `nature_metrics.py` imports `ladybug_comfort.utci` at module level; `ladybug_comfort` was not installed, making any `from nature_metrics import utci_hours_above` fail with `ModuleNotFoundError`
- **Fix:** `pip install ladybug-comfort` (installed 0.18.113); also installed ladybug-core and ladybug-geometry as transitive deps; click 8.1.7 downgrade noted (typer 0.25.1 conflict — pre-existing, out of scope)
- **Files modified:** None (pip-only fix)

**2. [Rule 1 - Bug] NaN guard for scipy ConstantInputWarning**
- **Found during:** Task 2 test run (14 ConstantInputWarning warnings from scipy)
- **Issue:** When mock data produces constant real_delta_utci_c (mock model returns same delta for all coverage levels), scipy.stats.spearmanr returns NaN with a ConstantInputWarning
- **Fix:** Wrapped scipy calls in `warnings.catch_warnings(simplefilter("ignore"))` and added NaN guard: `rho = float(rho_result) if rho_result == rho_result else 0.0`
- **Files modified:** `coolspend/calibration.py` (rank_stability function)

## Known Stubs

None. The calibration module produces real computation on all backends:
- Mock backend: deterministic mock UTCI scalars (documented as NOT MEASURED DATA)
- Live backend: real Infrared UTCI values (recorded to cache)
- Cached backend: replay of live results

The `surrogate_pred_utci_delta_c` on mock/cached reflects the actual `utci_hours_above` computation against the real Barcelona EPW, so even on mock it is not a trivial stub.

## Threat Surface Scan

No new network endpoints or auth paths introduced beyond what the plan specifies.
The `run_calibration_study` function inherits the T-05-08 mitigation: only geometry/coverage/UTCI scalars are serialized; `INFRARED_API_KEY` is never read or written by calibration code.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED | `69d37ef` `test(05-03): add failing tests...` | PASS |
| GREEN | `7d708e8` `feat(05-03): implement calibration study module...` | PASS |
| REFACTOR | Not required (no cleanup needed) | N/A |

## Self-Check: PASSED

- [x] `coolspend/calibration.py` exists
- [x] `coolspend/tests/test_calibration.py` exists
- [x] Commit `69d37ef` exists (RED gate)
- [x] Commit `7d708e8` exists (GREEN gate)
- [x] `HOURS_PER_DEGC_REF` imported from `coolspend.cost_model` (grep-verified in test)
- [x] `SimBudget(max_live_calls=3)` still present in `optimizer.py` (grep-verified in test)
- [x] 47 tests pass
- [x] No API key in any serialized output (test assertion)
