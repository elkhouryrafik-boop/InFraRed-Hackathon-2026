---
phase: 02-optimizer-core
plan: "02-02"
subsystem: spatial_engine / thermal_surrogate
tags: [surrogate, thermal, delta-tmrt, porosity-fix, offline, tdd]
dependency_graph:
  requires:
    - coolspend/spatial_engine.py (CRS + collision sections — must not regress)
  provides:
    - coolspend/spatial_engine.py::shade_efficiency
    - coolspend/spatial_engine.py::delta_tmrt_surrogate
    - coolspend/spatial_engine.py::thermal_relief
    - coolspend/tests/test_surrogate.py
    - MOCKS.md rows for delta_tmrt_surrogate + tree canopy constants
  affects:
    - optimizer.py (Plan 02-03) — imports thermal_relief as F1 objective
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN with explicit gate commits
    - Analytical proxy (pure math, no numpy) for NSGA-II hot-path
    - Honesty-first: unsourced cap + citation mismatch documented in-source + MOCKS ledger
key_files:
  created:
    - coolspend/tests/test_surrogate.py
  modified:
    - coolspend/spatial_engine.py
    - MOCKS.md
decisions:
  - "delta_tmrt_surrogate uses math (not numpy) to keep spatial_engine numpy-light"
  - "thermal_relief aggregates per-tree surrogate with 0.90 site-coverage cap — prevents unrealistic 100% canopy cover"
  - "porosity_pct retained in signature for call-site compatibility but intentionally unused in body (CONCERNS 4.2)"
  - "TREE_SHADE_FRACTION=0.80 and TREE_CANOPY_RADIUS_M=3.0 tagged DECLARED / REQUIRES_VERIFICATION — no fabricated citation"
metrics:
  duration: "5m"
  completed: "2026-05-21"
  tasks_completed: 1
  files_modified: 3
---

# Phase 2 Plan 02: Thermal Surrogate (OPT-02) Summary

**One-liner:** Ported fixed `delta_tmrt_surrogate` + `shade_efficiency` + `thermal_relief` into `spatial_engine.py` — porosity-squared bug regression-pinned, unsourced 12°C cap documented, 18 tests green, zero SDK calls.

## What Was Built

Appended a `# THERMAL SURROGATE (OPT-02)` section to `coolspend/spatial_engine.py` containing:

- **`shade_efficiency(tilt_deg, height_m)`** — analytical sun-path alignment bonus (tilt factor + height factor). Pure `math`, no numpy.
- **`delta_tmrt_surrogate(shade_fraction, porosity_pct, tilt_deg, height_m)`** — fast ΔTmrt proxy ported from `nature_nsga2_coolstock.py` with the porosity-squared bug fixed. Porosity is applied ONCE by the caller; the body uses `effective_shade = shade_fraction` (CONCERNS 4.2 / T-02-06). Capped at `MAX_TMRT_REDUCTION_C = 12.0°C`.
- **`thermal_relief(config)`** — aggregates per-tree surrogate ΔTmrt for a tree coordinate config into a single site-averaged relief value. Zero SDK calls, deterministic, returns 0.0 for empty/inactive configs.

Constants added (each tagged with SOURCE honesty comment):
- `PEAK_SUN_ALTITUDE_DEG = 63.0` (Barcelona July solar noon, analytical geometry)
- `PEAK_SUN_AZIMUTH_DEG = 215.0` (SW afternoon peak)
- `MAX_TMRT_REDUCTION_C = 12.0` (UNSOURCED cap — see MOCKS.md / CONCERNS 1.1)
- `TREE_SHADE_FRACTION = 0.80` (DECLARED / REQUIRES_VERIFICATION)
- `TREE_CANOPY_RADIUS_M = 3.0` (DECLARED / REQUIRES_VERIFICATION)

## Test Coverage

`coolspend/tests/test_surrogate.py` — 18 tests, all passing:

| Test | What it pins |
|------|-------------|
| test_shade_efficiency_returns_positive | finite positive output |
| test_shade_efficiency_increases_with_tilt | monotonic in tilt |
| test_shade_efficiency_increases_with_height | monotonic in height |
| test_delta_tmrt_basic_finite_positive | typical args → finite positive |
| test_delta_tmrt_capped_at_max | result <= MAX_TMRT_REDUCTION_C |
| test_delta_tmrt_max_cap_value | constant = 12.0 (CONCERNS 1.1) |
| test_delta_tmrt_monotonic_shade_fraction | more shade → more cooling |
| test_delta_tmrt_zero_shade_returns_zero | 0.0 input → 0.0 output |
| **test_delta_tmrt_no_double_porosity** | **regression pin for CONCERNS 4.2 porosity-squared bug** |
| test_delta_tmrt_default_args | default args work |
| test_thermal_relief_empty_config_returns_zero | {} trees → 0.0 |
| test_thermal_relief_no_trees_key | missing key → 0.0 |
| test_thermal_relief_positive_for_active_trees | one tree → positive |
| test_thermal_relief_inactive_tree_ignored | active=False → 0.0 |
| test_thermal_relief_more_trees_more_relief | N+1 trees >= N trees |
| test_thermal_relief_bounded | saturation <= MAX_TMRT_REDUCTION_C |
| test_thermal_relief_deterministic | same input → same output |
| test_thermal_relief_default_active_flag | absent key defaults to True |

Full suite: 71/71 passed (no regression in CRS/collision sections).

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED | de8d660 `test(02-02): add failing tests...` | ImportError confirmed before impl |
| GREEN | 7016f16 `feat(02-02): port fixed thermal surrogate...` | 18/18 passing |
| REFACTOR | N/A — code was clean, no refactor needed | Skipped (acceptable) |

## Deviations from Plan

None — plan executed exactly as written.

The `porosity_pct` parameter is retained in the signature (unused in body) as specified by the plan — "retained for call-site compatibility but intentionally no longer used in the body."

## Known Stubs

None. All functions are fully implemented and wired. No placeholder values flow to the optimizer.

## MOCKS.md Updates

Two new rows added to MOCKS.md:

1. **`delta_tmrt_surrogate`** — MOCK/SURROGATE: unsourced 12°C cap, ±4°C uncertainty, Garcia-Nevado 2020 citation mismatch (surface temp ≠ Tmrt at 1.1m), porosity-fix documented.
2. **`TREE_SHADE_FRACTION=0.80 / TREE_CANOPY_RADIUS_M=3.0`** — DECLARED / REQUIRES_VERIFICATION: not from Barcelona Arbrat Viari inventory.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. The surrogate is pure math. T-02-04 (tamper: surrogate presented as measured) mitigated by docstring disclaimers, MOCKS.md rows, and inline CONCERNS 1.1 comments. T-02-06 (repudiation: silent porosity regression) mitigated by `test_delta_tmrt_no_double_porosity`.

## Commits

| Hash | Message |
|------|---------|
| de8d660 | test(02-02): add failing tests for delta_tmrt_surrogate + thermal_relief (RED gate) |
| 7016f16 | feat(02-02): port fixed thermal surrogate + thermal_relief into spatial_engine (GREEN) |
| 99effd9 | docs(02-02): add MOCKS.md rows for delta_tmrt_surrogate + tree canopy constants |

## Self-Check: PASSED
