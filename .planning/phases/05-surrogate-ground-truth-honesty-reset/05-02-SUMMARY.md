---
phase: 05-surrogate-ground-truth-honesty-reset
plan: "02"
subsystem: kpi
tags: [utci, cost-model, uncertainty-interval, kpi, ladybug, tdd]

# Dependency graph
requires:
  - phase: 05-surrogate-ground-truth-honesty-reset plan 01
    provides: UTM-31N CRS migration (D-06/D-07) — not directly used here but same phase
  - phase: 01-foundation-sdk-boundary plan 03
    provides: cost_per_utci_degree baseline implementation + DECLARED cost constants
provides:
  - "UTCI-routed KPI: cost_per_utci_degree routes through utci_hours_above, never raw Tmrt (D-08)"
  - "Dual-unit KPI: EUR/degC (primary) + EUR/annual-UTCI-hour-above-32°C reduced (secondary, D-09)"
  - "Interval KPI: [value_lo, value] [value, value_hi] with band_c parameter and band_source label (D-10/VALID-04)"
  - "HOURS_PER_DEGC_REF=200.0 module constant (Plan 05-03 imports this by exact name)"
  - "PRE_CALIBRATION_BAND_C=4.0 module constant — labelled pre-calibration assumed band"
  - "cost_per_utci_hour_lo/hi interval on secondary unit"
affects:
  - 05-03-calibration (imports HOURS_PER_DEGC_REF by exact name)
  - app.py / app_viz.py (consume cost_per_utci_degree result dict — new keys available)
  - optimizer.py (cost_per_utci_degree is ranking metric)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "UTCI-hours routing before KPI formation (D-08): never use raw Tmrt as denominator"
    - "Dual-unit KPI reporting (D-09): EUR/degC primary + EUR/UTCI-hour secondary"
    - "Interval KPI with band propagation (D-10): cost/(degc+band)=lo, cost/(degc-band)=hi"
    - "Pre-calibration band labelling: assumed ±4°C until Plan 05-03 RMSE is available"
    - "Cross-plan constant contract: HOURS_PER_DEGC_REF = explicit API for Plan 05-03"

key-files:
  created: []
  modified:
    - coolspend/cost_model.py
    - coolspend/tests/test_cost_model.py

key-decisions:
  - "HOURS_PER_DEGC_REF=200.0: Barcelona strong heat stress mean UTCI excess ~3°C above threshold; baseline ~600h/yr / 3°C = 200h/°C — consistent with 12°C Tmrt ≈ 3-5°C UTCI note"
  - "Prefer-measured rule preserved: if delta_utci_c is positive float, use it as degc_drop (MED confidence); UTCI-hours still called for cost_per_utci_hour dual-unit reporting"
  - "Upper bound unbounded when band >= degc_drop: value_hi = None with note — prevents division by zero / negative denominator"
  - "EPW unavailability guard: utci_hours_above error captured gracefully; prefer-measured path still attempted"
  - "CAPEX_PER_TREE_EUR/OPEX constants intentionally untouched — D-15 explicit debt, Phase 6/COST-03 owner"

patterns-established:
  - "Local imports inside function body for heavy modules (nature_metrics, spatial_engine) with noqa: PLC0415"
  - "KPI interval propagation pattern: lo = cost/(degc+band), hi = cost/max(degc-band, EPS)"

requirements-completed: [VALID-02, VALID-04]

# Metrics
duration: 25min
completed: "2026-05-21"
---

# Phase 05 Plan 02: KPI Honesty Reset (UTCI Routing + Interval + Dual Units) Summary

**EUR/degC KPI now routes through utci_hours_above (never raw Tmrt), reports both EUR/degC and EUR/UTCI-hour, and emits an uncertainty interval [value_lo, value_hi] with pre-calibration ±4°C band labelling via HOURS_PER_DEGC_REF=200.0 cross-plan constant**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-21T16:30:00Z
- **Completed:** 2026-05-21T16:55:00Z
- **Tasks:** 2 (both TDD: RED → GREEN)
- **Files modified:** 2

## Accomplishments

- Removed the raw-Tmrt-as-denominator path from `cost_per_utci_degree` — the KPI °C denominator is now always UTCI-hours-derived (D-08 / VALID-02)
- Added dual-unit reporting: primary EUR/degC preserved for v1 framing compatibility; secondary `cost_per_utci_hour` (EUR / annual UTCI-hour above 32°C reduced) added (D-09)
- Added uncertainty interval [value_lo, value_hi] and [cost_per_utci_hour_lo/hi] propagated from `band_c` parameter, defaulting to `PRE_CALIBRATION_BAND_C=4.0°C` labelled "pre-calibration, assumed ±4°C" (D-10 / VALID-04)
- Defined `HOURS_PER_DEGC_REF=200.0` as a documented module constant — Plan 05-03's calibration module imports this exact name to re-anchor against empirical RMSE

## Task Commits

Each task was committed atomically (TDD RED then GREEN):

1. **RED: Failing tests for all new behavior** - `adf4df1` (test)
2. **GREEN: Full UTCI-routed dual-unit interval KPI (Tasks 1+2 combined)** - `cdf429b` (feat)

_Note: Both tasks share one implementation file and are closely coupled (Task 2 extends Task 1's output dict). They were combined into a single GREEN commit after both RED tests were written together._

## Files Created/Modified

- `coolspend/cost_model.py` — Extended `cost_per_utci_degree(config, band_c=None)` with UTCI routing, dual units, interval; added `HOURS_PER_DEGC_REF`, `PRE_CALIBRATION_BAND_C`, `_EPS` constants
- `coolspend/tests/test_cost_model.py` — 18 tests covering all new behavior (UTCI routing invariant, dual units, interval ordering, band label, cross-plan constant)

## Decisions Made

- **HOURS_PER_DEGC_REF = 200.0:** Derived from Barcelona EPW strong heat stress context: mean UTCI excess above 32°C threshold ≈3°C (midpoint of 32–38°C band); baseline ≈600 h/yr → 600/3=200 h/°C. Cross-checked against "12°C Tmrt ≈ 3–5°C UTCI" note: at 20% coverage, UTCI-hours reduction ≈600–1000 h, dividing by 200 gives 3–5°C, which matches the literature anchor.
- **Prefer-measured path preserved:** When `delta_utci_c` is a positive validated float, it is used as the °C drop (MED confidence). `utci_hours_above` is still called to populate `cost_per_utci_hour` for dual-unit completeness.
- **Upper bound unbounded handling:** When `band >= degc_drop`, `value_hi = None` with a note "upper bound unbounded (band exceeds °C estimate)" — prevents negative denominator without silent suppression.
- **EPW guard:** `utci_hours_above` errors captured via broad exception; `hours_reduced` falls back to None; prefer-measured path still attempted, so the function never crashes.

## Deviations from Plan

None — plan executed exactly as written. Tasks 1 and 2 were implemented in a single GREEN commit (per plan's own note that they are tightly coupled), matching the plan's specification of extending the same function.

## Known Mock Debt (D-15 — explicitly flagged, Phase 6 owner)

`CAPEX_PER_TREE_EUR=350.0` and `OPEX_PER_TREE_YEAR_EUR=35.0` remain DECLARED placeholder assumptions. These are 10× below real fully-loaded cost (NYC ~$3,300 CapEx, Boston ~$900/tree/yr). This plan fixes KPI **unit-correctness only** (D-08/D-09/D-10). The cost **magnitude** fix is deferred to:

- **Phase 6 / COST-03** — sourced lifecycle cost from municipal data, per-city editability
- Both constants carry `# SOURCE: REQUIRES_VERIFICATION` comments and are listed in MOCKS.md

## Issues Encountered

- 4 pre-existing test failures in `test_optimizer.py` and `test_surrogate.py` (not related to this plan):
  - `test_pareto_front_is_non_degenerate` — NSGA-II Pareto front collapses to 1 unique row
  - `test_top3_configs_differ_in_delta_and_cost` — top-3 delta_utci_c values not distinct
  - `test_seed_determinism_different_seed_differs` — different seed produces identical front
  - `test_core_concentration_beats_full_spread_thermally` — core clustering doesn't beat spread
  These were introduced in commit `cba1a7b` (remediation test wave, prior to this plan) and are **scope boundary violations** per deviation rules — pre-existing failures in unrelated files, not caused by this plan's changes. Logged here for visibility; not fixed here.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. `cost_model.py` reads from `nature_metrics.utci_hours_above` which uses a local EPW file (pre-existing, accepted in T-05-06). The KPI interval (T-05-04) is now mitigated: bare point estimate is impossible. Raw-Tmrt path removed (T-05-05) and pinned by test.

## Self-Check

- [x] `coolspend/cost_model.py` — exists and contains `HOURS_PER_DEGC_REF`, `PRE_CALIBRATION_BAND_C`, `utci_hours_above`, `value_lo`, `value_hi`, `cost_per_utci_hour`, `band_c`, `band_source`
- [x] `coolspend/tests/test_cost_model.py` — 18 tests, all pass
- [x] Commit `adf4df1` exists (RED test commit)
- [x] Commit `cdf429b` exists (GREEN feat commit)
- [x] `pytest coolspend/tests/test_cost_model.py` exits 0 (18 passed)

## Self-Check: PASSED

## Next Phase Readiness

- Plan 05-03 (calibration study) can import `HOURS_PER_DEGC_REF` from `coolspend.cost_model` by exact name to re-anchor the conversion against empirical RMSE
- `cost_per_utci_degree(config, band_c=calibration_rmse)` is ready to accept the empirical band — calling code only needs to pass the RMSE value
- The KPI result dict shape is backward-compatible (new keys added, no keys removed except the raw-Tmrt fallback which was a bug)
- App UI (`app_viz.py`) can surface `value_lo`/`value_hi` as a confidence range and `cost_per_utci_hour` as the secondary KPI — both keys now guaranteed in the result dict

---
*Phase: 05-surrogate-ground-truth-honesty-reset*
*Completed: 2026-05-21*
