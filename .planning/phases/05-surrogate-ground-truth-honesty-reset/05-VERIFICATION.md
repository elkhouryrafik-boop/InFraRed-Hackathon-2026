---
phase: 05-surrogate-ground-truth-honesty-reset
verified: 2026-05-21T17:18:12Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
gap_closure_note: "The single SC5/HONEST-03 gap (3 residual 'validated with Infrared' lines in SUBMISSION.md, lines 11/19/47) was closed post-verification — all replaced with 're-simulated with Infrared'. Re-grep across every honesty surface (SUBMISSION/README/CONCEPT_REPORT/DEMO_SCRIPT/MOCKS + code) returns 0 residual 'validated with Infrared' and 0 '88%'/improvement_vs_naive. Full suite remains 205 passed, 1 skipped. Plus a post-merge integration fix (commit d38c053) resolved a frame-desync/non-determinism bug the CRS migration exposed."
gaps: []
---

# Phase 5: Surrogate Ground-Truth & Honesty Reset Verification Report

**Phase Goal:** The headline KPI stops being assumption / assumption — the ΔTmrt surrogate is quantitatively validated against real Infrared UTCI, the KPI reports true UTCI (not raw Tmrt) as an uncertainty interval over one consistent CRS (UTM 31N), and every external claim is relabeled down to what is actually proven.
**Verified:** 2026-05-21T17:18:12Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (5 Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A user can run a calibration study across 5–10 deliberately varied configs and read an RMSE/R² fit + error band quantifying surrogate-vs-real-UTCI accuracy | VERIFIED | `coolspend/calibration.py` implements `run_calibration_study` (10 configs, seed-pinned, coverage-swept), `compute_fit` (RMSE + R² + error_band_c = 1.96*RMSE), `rank_stability` (Spearman + Kendall τ + set-overlap). 47/47 calibration tests pass. Live run confirmed: artifact structure verified via temp-dir run. |
| 2 | The €/°C KPI is computed from a true UTCI-hours delta (surrogate ΔTmrt routed through utci_hours_above()), never raw Tmrt, reported as an uncertainty interval — never a bare point estimate | VERIFIED | `coolspend/cost_model.py` routes through `utci_hours_above` at line 228; raw `delta_tmrt_c` fallback path deleted; `value_lo`/`value_hi` interval always present; `PRE_CALIBRATION_BAND_C=4.0` labelled "pre-calibration, assumed ±4°C"; dual units (EUR/degC + EUR/UTCI-hour). 18/18 cost model tests pass. |
| 3 | A user can see whether surrogate Top-3 stay Top-3 under real Infrared UTCI, with rank shift reported explicitly | VERIFIED | `calibration.rank_stability()` returns `set_overlap_top3`, `rank_swaps` (named, e.g. "config_N: surrogate rank X -> real rank Y"), and `headline` string. Both Spearman ρ and Kendall τ reported. Artifact structure confirmed. |
| 4 | All geometry runs through one projected CRS (UTM 31N / EPSG:32631) end-to-end, and a round-trip consistency assertion fires before any live SDK call | VERIFIED | `spatial_engine.py` uses `_Transformer.from_crs("EPSG:4326", "EPSG:32631", always_xy=True)` (line 69); `assert_crs_roundtrip` defined and raises `CRSConsistencyError` on ≥1 m error; called at `sdk_client.py` line 288 before `InfraredClient`. Per-site origin via `set_site_origin_from_polygon`. 14/14 coordinate frame tests pass. |
| 5 | External copy contains no "validated with Infrared" or "88% vs naive" claims; CONCEPT_REPORT.md matches MOCKS.md; surrogate ceiling cites Schrodi 2023 / Rahman 2022 with Garcia-Nevado demoted; unmodeled siting constraints listed as explicit out-of-scope exclusions | FAILED (partial) | CONCEPT_REPORT.md, README.md, DEMO_SCRIPT.md, MOCKS.md, app.py, optimizer.py, spatial_engine.py, app_viz.py, app_pipeline.py are all clean. Out-of-scope exclusions list (all six items + "geometric feasibility" framing) present in README and CONCEPT_REPORT. Schrodi 2023 + Rahman 2022 cited; Garcia-Nevado demoted. "88%" absent from all target files. **However: SUBMISSION.md retains "validated with Infrared" on lines 11, 19, and 47.** |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `coolspend/spatial_engine.py` | UTM-31N CRS boundary + per-site origin + round-trip guard | VERIFIED | EPSG:32631 transformer, `set_site_origin_from_polygon`, `assert_crs_roundtrip`, `CRSConsistencyError`; Schrodi/Rahman citations in docstrings; no equirectangular code |
| `coolspend/sdk_client.py` | `assert_crs_roundtrip` called before live SDK | VERIFIED | Lines 287-288: `from coolspend.spatial_engine import assert_crs_roundtrip` + `assert_crs_roundtrip(ring)` — before `InfraredClient` |
| `coolspend/tests/test_coordinate_frame.py` | Round-trip <1m + per-site origin + fail-closed guard tests | VERIFIED | 14 tests pass including round-trip, per-site origin, guard pass and fail-closed |
| `requirements.txt` | `pyproj>=3.6,<4` pin | VERIFIED | Line 9: `pyproj>=3.6,<4` |
| `coolspend/cost_model.py` | UTCI-routed KPI + both units + [lo,hi] band | VERIFIED | `utci_hours_above` called, `value_lo`/`value_hi` interval, `cost_per_utci_hour`, `PRE_CALIBRATION_BAND_C=4.0`, `HOURS_PER_DEGC_REF=200.0`; no raw-Tmrt denominator |
| `coolspend/tests/test_cost_model.py` | UTCI routing, band interval, pre-calibration label tests | VERIFIED | 18 tests pass |
| `coolspend/calibration.py` | `run_calibration_study` + 10-config sweep + RMSE/R²/band + rank-stability + live-then-cache | VERIFIED | All four functions present; separate `SimBudget(n+1)`; dimensional contract via `HOURS_PER_DEGC_REF` import; `STUDY_SEED=42`, `N_STUDY_CONFIGS=10` |
| `coolspend/tests/test_calibration.py` | 47 tests covering all calibration aspects | VERIFIED | 47/47 pass |
| `outputs/calibration_study.json` | Calibration artifact with fit + rank_stability | PARTIAL | File not present at `outputs/calibration_study.json` at verification time (live operator run not yet executed). Test suite writes to temp dir and verifies keys. The live-then-cache procedure is documented and the code is verified. Acceptable per verification method: "Treat calibration runs live-then-caches as satisfied if the code path + documented procedure exist and tests pass offline." |
| `coolspend/optimizer.py` | naive-baseline deleted; Schrodi/Rahman citation; honest artifact strings | VERIFIED | Zero matches for `improvement_vs_naive`, `naive_baseline_config`, `_build_naive_baseline`; "Schrodi" present (2 matches); "re-simulated with Infrared UTCI" present (2 matches); zero "validated with Infrared" matches |
| `CONCEPT_REPORT.md` | No CFD/permaculture/energy-exchange; re-simulated phrasing; out-of-scope list | VERIFIED | No "professional-grade CFD", "permaculture engine", "energy exchange"; "re-simulated with Infrared UTCI" present; out-of-scope section with all six items |
| `README.md` | Honest re-simulation phrasing + out-of-scope list | VERIFIED | "validated with Infrared" absent; "re-simulated with Infrared UTCI" at line 148; out-of-scope section at lines 85-96 with all six items + "geometric feasibility" framing |
| `MOCKS.md` | Schrodi/Rahman citation; naive row marked REMOVED; no fabricated DOIs | VERIFIED | Schrodi 2023 arXiv:2310.05691 + Rahman 2022 in surrogate row; naive row marked "REMOVED (Phase 5, D-12)"; no doi.org links |
| `SUBMISSION.md` | Honest re-simulation phrasing; no "validated with Infrared" | STUB (partial) | Line 5 (one-line pitch) correctly uses "re-simulated with Infrared UTCI". Lines 11, 19, 47 retain "validates"/"validated with Infrared" overclaim |
| `coolspend/app.py` | Dual-unit + [lo,hi] interval KPI surfaced; no validated/88% strings | VERIFIED | `value_lo`, `cost_per_utci_hour`, `band_source` all read from KPI dict (lines 169, 179-183); no "validated with Infrared" or "88%" in app.py, app_viz.py, app_pipeline.py |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `sdk_client._live_utci` | `spatial_engine.assert_crs_roundtrip` | Guard call before `InfraredClient` | WIRED | Lines 287-288 in sdk_client.py: import + call inside `_live_utci`, before `with InfraredClient()` |
| `coolspend/optimizer.py::_config_to_geometry` | `spatial_engine.local_m_to_latlon` | polygon_lonlat construction | WIRED | Confirmed by existing optimizer test suite (205 pass) |
| `coolspend/cost_model.py::cost_per_utci_degree` | `nature_metrics.utci_hours_above` | Surrogate ΔTmrt -> coverage -> UTCI-hours delta | WIRED | Line 228: `uh = utci_hours_above(32.0, cov)` — raw Tmrt path deleted |
| `coolspend/calibration.py` | `coolspend.cost_model.HOURS_PER_DEGC_REF` | Dimensional contract — shared conversion factor | WIRED | Line 251: `from coolspend.cost_model import HOURS_PER_DEGC_REF` — same factor as KPI |
| `coolspend/calibration.py` | `coolspend.sdk_client.SimBudget` | Separate study budget cap = n+1 | WIRED | Line 239: `budget = SimBudget(max_live_calls=n + 1)` |
| `CONCEPT_REPORT.md` | `MOCKS.md` | Claims match honesty ledger | WIRED | Schrodi/Rahman citations consistent; overclaims removed from CONCEPT_REPORT; naive row REMOVED in MOCKS |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `cost_model.cost_per_utci_degree` | `hours_reduced` | `utci_hours_above(32.0, cov)` via nature_metrics ladybug | Yes — EPW-derived UTCI-hours, not hardcoded | FLOWING |
| `calibration.run_calibration_study` | `cfg["real_delta_utci_c"]` | `get_intervention_utci(geom)` from sdk_client (mock in CI, live in production) | Real on live backend; mock in CI (documented) | FLOWING (conditional) |
| `calibration.run_calibration_study` | `cfg["surrogate_pred_utci_delta_c"]` | `utci_hours_above` + `HOURS_PER_DEGC_REF` | Analytical, same path as KPI — consistent | FLOWING |
| `app.py allocation table` | `value_lo`, `value_hi`, `cost_per_utci_hour`, `band_source` | `cost_per_utci_degree(config)` result dict | Read directly from cost model — never hardcoded | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Calibration study produces fit + rank_stability keys | `run_calibration_study` in temp dir + check keys | `fit: [rmse, r2, error_band_c, n, band_basis]`, `rank_stability: [spearman_rho, kendall_tau, set_overlap_top3, rank_swaps, headline]` | PASS |
| Coordinate frame tests pass | `pytest test_coordinate_frame.py -q` | 14 passed in 0.03s | PASS |
| Calibration tests pass | `pytest test_calibration.py -q` | 47 passed in 1.69s | PASS |
| Cost model tests pass | `pytest test_cost_model.py -q` | 18 passed in 0.11s | PASS |
| Full test suite | `pytest coolspend/tests/ -q` | 205 passed, 1 skipped in 79.47s | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| VALID-01 | 05-03-PLAN.md | Calibration study across 5–10 configs, RMSE/R²/error band | SATISFIED | `calibration.py::run_calibration_study` + `compute_fit`; 10 configs; RMSE, R², error_band_c=1.96*RMSE; 47 tests pass |
| VALID-02 | 05-02-PLAN.md | ΔTmrt surrogate converted to UTCI-hours delta before KPI | SATISFIED | `cost_model.cost_per_utci_degree` routes through `utci_hours_above`; raw-Tmrt denominator deleted; confirmed by test |
| VALID-03 | 05-03-PLAN.md | Ranking stability — Top-3 stays Top-3 or rank shift reported | SATISFIED | `calibration.rank_stability` returns set_overlap_top3, rank_swaps (named), Spearman ρ, Kendall τ |
| VALID-04 | 05-02-PLAN.md | KPI reported as uncertainty interval [lo,hi], never bare point | SATISFIED | `value_lo`/`value_hi` always in result; `PRE_CALIBRATION_BAND_C=4.0` labelled "pre-calibration, assumed ±4°C"; interval logic in cost_model lines 299-321 |
| VALID-05 | 05-01-PLAN.md | One projected CRS (UTM 31N) end-to-end; round-trip assertion before live SDK call | SATISFIED | EPSG:32631 in spatial_engine.py (lines 69-70); `assert_crs_roundtrip` in sdk_client line 288; per-site origin from polygon bbox |
| HONEST-01 | 05-05-PLAN.md | CONCEPT_REPORT.md aligned down to MOCKS.md | SATISFIED | No "professional-grade CFD", "permaculture engine", "energy exchange" in CONCEPT_REPORT.md |
| HONEST-02 | 05-04-PLAN.md / 05-05-PLAN.md | Schrodi 2023 + Rahman 2022 as anchor; Garcia-Nevado demoted | SATISFIED | Schrodi arXiv:2310.05691 + Rahman 2022 in spatial_engine.py, optimizer.py, MOCKS.md; Garcia-Nevado demoted to analogue; no fabricated DOIs |
| HONEST-03 | 05-04-PLAN.md / 05-05-PLAN.md | "Validated with Infrared" and "88% vs naive" removed from external copy | BLOCKED (partial) | "validated with Infrared" removed from README, DEMO_SCRIPT, CONCEPT_REPORT, app.py, optimizer.py. **SUBMISSION.md lines 11, 19, 47 still say "validates"/"validated with Infrared".** "88%" absent from all target external files (CHANGELOG.md retains it as historical record in a completed-tasks entry — this is a changelog, not external product copy, and does not constitute an active claim). |
| HONEST-04 | 05-05-PLAN.md | Out-of-scope exclusions list in external docs | SATISFIED | Six-item list + "geometric feasibility, not engineering siting sign-off" in both README.md (lines 85-96) and CONCEPT_REPORT.md (lines 35-46) |

**Orphaned requirements check:** VALID-05, HONEST-01/02/03/04 all appear in the traceability table as Phase 5. The REQUIREMENTS.md traceability table still shows VALID-05 and all HONEST-* as "Pending" — this is stale metadata in REQUIREMENTS.md and does not reflect the completed code state. This is a documentation gap only, not a functional gap.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| SUBMISSION.md line 11 | "validates each with Infrared UTCI calls when run live" | BLOCKER (SC5 fail) | Overclaim "validated" survives in external submission copy — violates HONEST-03 contract |
| SUBMISSION.md line 19 | "are validated with three Infrared UTCI SDK calls" | BLOCKER (SC5 fail) | Same overclaim in Technical depth section |
| SUBMISSION.md line 47 | "the Top-3 configurations are validated with Infrared UTCI SDK calls" | BLOCKER (SC5 fail) | Same overclaim in Honesty note section |
| REQUIREMENTS.md traceability | VALID-05, HONEST-01/02/03/04 show "Pending" | WARNING | Stale metadata — code is implemented and tests pass. Does not affect SC5 but is misleading. |
| outputs/calibration_study.json | File absent from outputs/ | INFO | Live operator run has not been executed. Code path exists and tests pass. Per verification method this is acceptable. |

### Human Verification Required

None — all behavioral checks are automatable. The live Infrared calibration run (INFRARED_BACKEND=live) is an operator action documented in the code; CI runs on mock/cached.

### Gaps Summary

**1 gap blocking SC5 / HONEST-03:** SUBMISSION.md retains "validated with Infrared" on three separate lines (11, 19, 47). The one-line pitch at line 5 correctly uses "re-simulated with Infrared UTCI" and the Honesty note at line 35 uses the correct phrasing for the rank-1 numbers, but three other sentences in the same file still use the overclaim phrasing that HONEST-03 requires to be removed.

All other four success criteria are fully verified: the calibration study infrastructure (SC1), UTCI-routed interval KPI (SC2), ranking stability reporting (SC3), and UTM-31N end-to-end CRS with fail-closed guard (SC4) are all substantive, wired, and tested. The full test suite is green (205 passed, 1 skipped).

**Root cause:** SUBMISSION.md was partially updated — the one-line pitch and one sentence in the real-world-impact section were corrected, but the "What it is", "Technical depth", and "Honesty note" sections were not fully swept.

**Fix scope:** Three targeted string replacements in SUBMISSION.md. No code changes required.

---

_Verified: 2026-05-21T17:18:12Z_
_Verifier: Claude (gsd-verifier)_
