---
phase: 05-surrogate-ground-truth-honesty-reset
plan: "04"
subsystem: optimizer + spatial-engine honesty reset
tags: [honesty, citations, d12-naive-baseline-delete, d13-citation-reanchor, d11-artifact-strings]
dependency_graph:
  requires: ["05-01"]
  provides: [honest-artifact-json, honest-audit-record, re-anchored-surrogate-citation]
  affects: [coolspend/optimizer.py, coolspend/spatial_engine.py, coolspend/tests/test_optimizer.py, coolspend/tests/test_surrogate.py, coolspend/main.py]
tech_stack:
  added: []
  patterns: [surrogate-honesty-contract, pending-citation-tags, no-fabricated-dois]
key_files:
  created: []
  modified:
    - coolspend/optimizer.py
    - coolspend/spatial_engine.py
    - coolspend/tests/test_optimizer.py
    - coolspend/tests/test_surrogate.py
    - coolspend/main.py
decisions:
  - "D-12: naive_baseline_config + _build_naive_baseline + improvement_vs_naive_pct deleted entirely — mock-vs-mock overclaim cannot survive anywhere"
  - "D-13: Schrodi 2023 (arXiv:2310.05691, venue PENDING) is the Tmrt-magnitude anchor; Rahman 2022 (DOI PENDING) supporting; Garcia-Nevado 2020 demoted to surface-temp analogue"
  - "D-11 code surfaces: surrogate_note uses 're-simulated below with real Infrared UTCI (not validated)'; audit validated_utci_c renamed 're-simulated with Infrared UTCI'"
  - "12C cap honesty preserved: re-anchoring Tmrt magnitude does NOT claim the linear cap is now sourced — REQUIRES_VERIFICATION maintained"
  - "No fabricated DOIs: all unconfirmed refs tagged PENDING (venue PENDING for Schrodi, DOI PENDING for Rahman)"
metrics:
  duration: "5m"
  completed_date: "2026-05-21"
  tasks_completed: 2
  files_changed: 5
---

# Phase 05 Plan 04: Code-Side Honesty Reset Summary

Deleted the entire naive-baseline machinery (D-12) and re-anchored the surrogate ceiling citation from Garcia-Nevado 2020 to Schrodi 2023 (arXiv:2310.05691) + Rahman 2022, with no fabricated DOIs and preserved 12°C-cap REQUIRES_VERIFICATION honesty.

## What Changed

### Task 1 — Delete naive-baseline machinery and improvement_vs_naive_pct (D-12)

**coolspend/optimizer.py:**
- Deleted `naive_baseline_config()` function (grid-placement naive strategy)
- Deleted `_build_naive_baseline()` function (naive UTCI validation + KPI computation)
- Deleted the `improvement_vs_naive_pct` computation block and `rank1["improvement_vs_naive_pct"]` assignment in `save_outputs()`
- Removed `"baseline_naive"` and `"improvement_vs_naive_pct"` keys from the artifact JSON dict

**coolspend/main.py:**
- Removed the naive-baseline read-back block (`artifact.get("baseline_naive")`, `artifact.get("improvement_vs_naive_pct")`)
- Removed the "Naive grid baseline" and "Improvement vs naive" print lines from the human summary

**coolspend/tests/test_optimizer.py:**
- Removed `naive_baseline_config` from imports
- Removed `test_naive_baseline_is_valid_and_deterministic` (tested deleted function)
- Removed `test_naive_baseline_present_and_improvement_finite` (asserted on deleted artifact keys)
- Added `test_no_naive_baseline_in_artifact` — regression test that runs `save_outputs` on a mock backend and asserts the artifact JSON has NO `"baseline_naive"` and NO `"improvement_vs_naive_pct"` keys (pins D-12 absence permanently)

**Commits:** `a69678b` — 3 files, 22 insertions, 186 deletions

### Task 2 — Re-anchor surrogate citation and fix artifact/audit honesty strings (D-11/D-13)

**coolspend/spatial_engine.py:**
- Module docstring SURROGATE HONESTY block: added Schrodi 2023 / Rahman 2022 citation block; Garcia-Nevado 2020 demoted to analogue; 12°C cap "still UNSOURCED — REQUIRES_VERIFICATION" honesty preserved
- HONESTY NOTICE comment block above the thermal surrogate section: updated with re-anchored citations + explicit "we do NOT use their ML approach"
- `MAX_TMRT_REDUCTION_C` comment: updated with Schrodi/Rahman PENDING tags and explicit "re-anchoring Tmrt magnitude does NOT source this cap" note
- `delta_tmrt_surrogate` docstring HONESTY FLAGS: updated with full re-anchored citation, preserved 12°C-cap REQUIRES_VERIFICATION note

**coolspend/optimizer.py:**
- `select_top3`: `cfg["delta_tmrt_source"]` → `"analytical surrogate ΔTmrt; magnitude anchored to Schrodi 2023 (arXiv:2310.05691, PENDING) + Rahman 2022; Garcia-Nevado 2020 = surface-temp analogue. NOT measured/simulated. ±4°C."`
- `select_top3`: `cfg["surrogate_note"]` → `"Analytical proxy — final picks re-simulated below with real Infrared UTCI (not 'validated')."`
- `write_audit_record`: `surrogate_flags` — added `tmrt_magnitude_anchor` key with full citation; updated `max_tmrt_reduction_c_cap` to include REQUIRES_VERIFICATION; `validated_utci_c` → `"re-simulated with Infrared UTCI ..."`
- `write_audit_record`: `data_sources.surrogate_physics` updated with re-anchored citation; `utci_validation` key renamed `utci_top3_validation` with `"final picks re-simulated with Infrared UTCI"` phrasing

**coolspend/tests/test_surrogate.py:**
- Added `test_surrogate_provenance_cites_schrodi` — asserts "Schrodi", "arXiv:2310.05691", "Rahman" present in `spatial_engine` module docstring
- Added `test_surrogate_delta_tmrt_source_in_select_top3` — asserts `delta_tmrt_source` cites Schrodi, `surrogate_note` uses "re-simulated", Garcia-Nevado listed as "analogue"

**Commits:** `4771b18` — 3 files, 107 insertions, 19 deletions

## Test Results

```
37 passed in 14.71s
```
- 14 tests in test_optimizer.py (including new `test_no_naive_baseline_in_artifact`)
- 23 tests in test_surrogate.py (including 2 new citation/honesty tests)

## Grep Verification

| Check | Result |
|-------|--------|
| `improvement_vs_naive` in coolspend/ (non-test .py) | 0 matches |
| `def naive_baseline_config` in optimizer.py | 0 matches |
| `def _build_naive_baseline` in optimizer.py | 0 matches |
| `baseline_naive` in optimizer.py | 0 matches |
| `validated with infrared` (case-insensitive) in optimizer.py | 0 matches |
| `Schrodi` in spatial_engine.py | 4 matches |
| `arXiv:2310.05691` in spatial_engine.py | 4 matches |
| `Rahman` in spatial_engine.py | 4 matches |
| `Schrodi` in optimizer.py | 3 matches |
| `re-simulated with Infrared UTCI` in optimizer.py | 2 matches |
| `doi.org` in spatial_engine.py | 0 matches |

## Deviations from Plan

**1. [Rule 2 - Missing] Clean up main.py naive-baseline block**
- **Found during:** Task 1
- **Issue:** `coolspend/main.py` had a dead read-back block that called `artifact.get("baseline_naive")` and `artifact.get("improvement_vs_naive_pct")` after `save_outputs()`, plus print lines for "Naive grid baseline" and "Improvement vs naive". With the keys deleted from the artifact, the code still ran but printed useless `N/A` values from the now-empty dict.
- **Fix:** Removed the artifact read-back block, the `import json as _json` inside main, the `baseline_naive` variable, and the naive-comparison print section. Summary block simplified to only the before/after and KPI lines.
- **Files modified:** `coolspend/main.py`
- **Commit:** `a69678b`

## Known Stubs

None — all changes are deletions and honest string replacements; no new stubs introduced.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Changes are pure deletions of misleading code and citation string replacements in docstrings and JSON-emitting functions.

## Self-Check: PASSED

- `coolspend/optimizer.py` exists and contains "Schrodi 2023" ✓
- `coolspend/spatial_engine.py` exists and contains "arXiv:2310.05691" ✓
- `coolspend/tests/test_optimizer.py` contains `test_no_naive_baseline_in_artifact` ✓
- `coolspend/tests/test_surrogate.py` contains `test_surrogate_provenance_cites_schrodi` ✓
- Commit `a69678b` exists ✓
- Commit `4771b18` exists ✓
- 37 tests pass ✓
