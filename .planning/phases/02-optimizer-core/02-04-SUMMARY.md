---
phase: 02-optimizer-core
plan: "04"
subsystem: optimizer
tags: [nsga2, pymoo, optimizer, pareto, top3, validation, budget-constraint, surrogate]
dependency_graph:
  requires: ["02-01", "02-02", "02-03"]
  provides: ["OPT-01", "OPT-03"]
  affects: ["02-05"]
tech_stack:
  added: ["pymoo==0.6.1", "matplotlib"]
  patterns:
    - "NSGA-II ElementwiseProblem with 2 objectives + 1 budget inequality constraint"
    - "SimBudget-guarded SDK validation separate from hot path"
    - "Fixed-length flat chromosome [x0,y0,...,x11,y11] decoded to tree config dict"
key_files:
  created:
    - coolspend/optimizer.py
    - coolspend/tests/test_optimizer.py
  modified: []
decisions:
  - "N_TREES=12 fixed slots; chromosome length 24 (2*N_TREES x/y pairs)"
  - "select_top3 deduplication via utopia-point sorted fallback (ported from reference)"
  - "validate_top3_with_infrared: baseline called once without budget record; 3 budget slots reserved for interventions"
  - "Pop=60, Gen=60 gives ~60 Pareto points in <0.5s offline; __main__ uses full settings"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-21"
  tasks_completed: 3
  files_created: 2
---

# Phase 02 Plan 04: Optimizer (NSGA-II + Top-3 Validation) Summary

**One-liner:** NSGA-II optimizer over 12-slot fixed-length tree-coordinate vector with thermal+ecological surrogate objectives, budget constraint, seed-42 determinism, and 3 SimBudget-guarded real/mock UTCI validation calls.

## What Was Built

### coolspend/optimizer.py (413 lines)

**Constants:**
- `N_TREES=12`, `DEFAULT_BUDGET_EUR=1_000_000`, `SPECIES=("platanus","celtis","tilia","quercus")`, `SEED=42`, `POP_SIZE=60`, `N_GEN=60`

**`decode(x_flat) -> dict`**
Decodes a flat 24-element chromosome `[x0,y0,...,x11,y11]` into a tree config dict. Each slot gets a species (round-robin from SPECIES) and `active=is_valid_location(x_m,y_m)`. Returns `{"trees":[...], "tree_count": int_active_count}`.

**`class TreeBudgetProblem(ElementwiseProblem)`**
- `n_var=24`, `n_obj=2`, `n_ieq_constr=1`, `xl=zeros(24)`, `xu=tile([60,42],12)`
- `_evaluate`: calls `thermal_relief()` and `ecological_score()` (surrogates only — zero SDK calls); `G1=total_cost-budget_eur`
- T-02-11 mitigated: no `sdk_client` import in `_evaluate`

**`run_optimisation(budget_eur, pop_size, n_gen, seed)`**
SBX(prob=0.9, eta=15), PM(eta=20), FloatRandomSampling, eliminate_duplicates=True. Returns pymoo Result. Hot path: surrogate only, zero live SDK calls.

**`select_top3(result) -> list[dict]`**
3 representatives: MAX_THERMAL_RELIEF (min F[:,0]), MAX_ECOLOGICAL (min F[:,1]), BALANCED (min L2 of normalised F / utopia point). Dedup loop ensures 3 distinct indices. Each config carries: rank, label, delta_tmrt_c, delta_tmrt_uncertainty_c=4.0, delta_tmrt_source, ecological_score, surrogate_note, topsis_score=None.

**`_config_to_geometry(cfg) -> dict`**
Builds SDK geometry payload: coverage_fraction from canopy footprints (capped 0.9), width_m from bounding box of active trees, polygon_lonlat via local_m_to_latlon (SPATIAL-03 compliant).

**`validate_top3_with_infrared(top3, budget=None) -> list[dict]`**
Imports `sdk_client` locally (hot-path isolation). Creates `SimBudget(3)` if not provided. Calls `get_baseline_utci` once (no budget record). Calls `get_intervention_utci` 3 times (one per config, each preceded by `budget.record(f"intervention {label}")`). Attaches `baseline_utci_c`, `validated_utci_c`, `delta_utci_c`, `validated_backend`, `validated_disclaimer` to each config.

### coolspend/tests/test_optimizer.py (214 lines)

6 tests, all passing offline in ~1s:

| Test | What it proves |
|------|----------------|
| `test_pareto_front_min_size` | Pareto front >= 10 distinct configs (pop=30, gen=20) |
| `test_no_sdk_in_hot_path` | Monkeypatches `get_intervention_utci` to raise; `run_optimisation` completes — hot path is SDK-free |
| `test_invalid_placements_excluded` | Building-centroid coords -> `active=False`, `tree_count=0` |
| `test_select_top3_distinct` | 3 distinct ranks/labels + required honesty fields present |
| `test_validate_exactly_three_calls` | `budget.log` length=3 after validation; 4th call raises `RuntimeError` |
| `test_budget_constraint_active` | `G1 > 0` for 1-EUR budget with valid tree slots |

## Performance

Full-settings run (pop=60, gen=60): **<0.5s offline**, Pareto front=60 configs. Tests (pop=30, gen=20): **~0.87s total** for 6 optimizer tests.

## Verification Results

```
python -m coolspend.optimizer
  Pareto front size: 60
  Top-3: MAX_THERMAL_RELIEF, MAX_ECOLOGICAL, BALANCED
  Validation: delta_utci=1.41°C mock backend (3 calls)

python -m pytest coolspend/tests -q
  82 passed in 0.98s
```

## Threat Model Coverage

| Threat | Disposition | Evidence |
|--------|-------------|---------|
| T-02-11: live SDK in hot path | MITIGATED | `test_no_sdk_in_hot_path` monkeypatches raises; optimizer completes |
| T-02-12: invalid tree placements | MITIGATED | `decode()` marks out-of-bounds/in-building slots `active=False` |
| T-02-13: surrogate mistaken for measured | MITIGATED | Top-3 carry `delta_tmrt_uncertainty_c=4.0`, `surrogate_note`; validate replaces with `delta_utci_c` |
| T-02-14: information disclosure | ACCEPTED | No secrets in optimizer; key stays in sdk_client live branch |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**Implementation notes:**
- Task 1 and Task 2 were implemented in a single file creation (select_top3 + validate_top3_with_infrared written together with TreeBudgetProblem/run_optimisation). No deviation from plan intent — both tasks committed individually per protocol (Task 1 commit: ecc5ddd, Task 3 commit: 9527358).
- `np.row_stack` deprecation warning from pymoo 0.6.1 internals (not our code) — out of scope to fix.

## Known Stubs

- `topsis_score = None` in each Top-3 config. Placeholder filled by Plan 02-05 (TOPSIS ranking). This is intentional per plan spec.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1+2 | ecc5ddd | feat(02-04): implement TreeBudgetProblem + run_optimisation + select_top3 + validate |
| Task 3 | 9527358 | feat(02-04): add offline optimizer test suite (6 tests, all passing) |

## Self-Check: PASSED

- coolspend/optimizer.py: FOUND
- coolspend/tests/test_optimizer.py: FOUND
- Commit ecc5ddd: FOUND
- Commit 9527358: FOUND
- 82 tests green offline
