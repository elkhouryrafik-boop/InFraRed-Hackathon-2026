---
phase: 02-optimizer-core
plan: "03"
subsystem: sdk_client / infrared-live-backend
tags: [sdk, live, infrared, utci, real-call, offline-default, lazy-import, caching, security]
requirements: [OPT-03]

dependency_graph:
  requires:
    - coolspend/sdk_client.py (Phase 01-01 contract — UTCIResult, SimBudget, mock/cached branches)
    - coolspend/spatial_engine.py (local_m_to_latlon — single CRS conversion boundary, SPATIAL-03)
  provides:
    - _live_utci() helper — real InfraredClient.run_area_and_wait UTCI call, lazy SDK import
    - live→cache write — INFRARED_BACKEND=cached replays live results offline
    - test_sdk_client_live.py — offline tests for live path via monkeypatched fake SDK
  affects:
    - MOCKS.md — added live UTCI row tagged VERIFIED (live) vs mock NOT MEASURED DATA

tech_stack:
  added: []
  patterns:
    - lazy import (infrared_sdk imported inside _live_utci only — not at module level)
    - monkeypatched fake SDK module tree (types.ModuleType + MagicMock) for offline test coverage
    - live→cache write (json.dumps to CACHE_DIR) for offline replay

key_files:
  created:
    - coolspend/tests/test_sdk_client_live.py
  modified:
    - coolspend/sdk_client.py
    - MOCKS.md

decisions:
  - "lazy import of infrared_sdk inside _live_utci() only — module importable offline without SDK"
  - "INFRARED_API_KEY validated present before any SDK usage; never logged or embedded in strings (T-02-07)"
  - "live result written to CACHE_DIR so INFRARED_BACKEND=cached replays offline without key/network"
  - "polygon_lonlat OR polygon_local_m accepted — local-m converted via spatial_engine.local_m_to_latlon only (SPATIAL-03 / T-02-10)"
  - "merged_grid reduced to scalar via np.mean — site-mean felt temperature at 1.1m"
  - "TODO inline comment for AnalysesName.utci member name — one-line confirmation needed at May-27 SDK wiring"
  - "mock/cached branches byte-identical to Phase 01-01 baseline"

metrics:
  duration: "15m"
  completed_date: "2026-05-21"
  tasks_completed: 2
  files_modified: 3
---

# Phase 2 Plan 03: Live Infrared Backend Wiring Summary

**One-liner:** Real InfraredClient.run_area_and_wait UTCI call with lazy SDK import, key-from-env only, live→cache write, and full offline test coverage via monkeypatched fake SDK.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Wire live Infrared backend (lazy import, live→cache, key-from-env) | d42d04e | coolspend/sdk_client.py, MOCKS.md |
| 2 | Offline tests for live path via monkeypatched fake SDK | a6640c2 | coolspend/tests/test_sdk_client_live.py |

## What Was Built

### Task 1 — Live backend in sdk_client.py

Added `_live_utci(metric_key, geometry)` helper that:

- Validates `INFRARED_API_KEY` presence (raises `EnvironmentError` naming the variable if absent)
- Lazily imports `from infrared_sdk import InfraredClient` and `from infrared_sdk.analyses.types import AnalysesName` inside the function body — `import coolspend.sdk_client` never requires the SDK (critical for offline-before-May-27 constraint)
- Accepts `polygon_lonlat` or `polygon_local_m` geometry keys; local-m coords converted exclusively via `spatial_engine.local_m_to_latlon` (SPATIAL-03 / T-02-10 single-CRS boundary)
- Calls `InfraredClient` as context manager: `client.buildings.get_area(polygon)` then `client.run_area_and_wait(utci_request, polygon, buildings=area.buildings)`
- Reduces `result.merged_grid` to site-mean scalar via `np.mean` (also lazily imported)
- Returns `UTCIResult(backend="live", disclaimer="LIVE Infrared SDK result", ...)` — no "NOT MEASURED DATA" disclaimer on live results
- Inline TODO comment marks the one-line `AnalysesName.utci` member name for May-27 confirmation

Replaced the `NotImplementedError` live branch in `_dispatch`:
- Calls `_live_utci(metric_key, geometry)`
- Writes result to `CACHE_DIR/{metric_key}_{ghash}.json` so a subsequent `INFRARED_BACKEND=cached` run replays offline
- Returns result

Mock and cached branches are byte-identical to the Phase 01-01 baseline.

### Task 2 — Offline tests

`coolspend/tests/test_sdk_client_live.py` (5 tests, all offline):

| Test | What it verifies |
|------|-----------------|
| `test_import_does_not_require_sdk` | Module importable with infrared_sdk blocked from sys.meta_path |
| `test_live_without_key_raises` | `EnvironmentError` raised when `INFRARED_API_KEY` absent |
| `test_live_calls_sdk_and_caches` | Fake SDK injected via sys.modules; UTCIResult.backend=live; utci_c=mean(fake_grid); cache file written |
| `test_cached_replays_live_result` | After live call, INFRARED_BACKEND=cached returns same scalar offline |
| `test_key_never_logged` | Dummy key string absent from all log records during live call |

## Test Results

```
coolspend/tests/test_sdk_client.py: 6 passed
coolspend/tests/test_sdk_client_live.py: 5 passed
Total: 11 passed in 0.13s
```

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

All threats in the plan's `<threat_model>` are mitigated:

| Threat ID | Mitigation Applied |
|-----------|-------------------|
| T-02-07 (key disclosure) | Key validated present, never logged, never in any string after validation — enforced by `test_key_never_logged` |
| T-02-08 (runaway live calls) | SimBudget guard unchanged; live path reachable only via explicit validate (Plan 02-04), not NSGA-II hot path |
| T-02-09 (cached JSON tampering) | json.loads only (no eval); cache keyed by deterministic geometry hash |
| T-02-10 (wrong polygon CRS) | lon/lat conversion exclusively via `spatial_engine.local_m_to_latlon` |

No new security-relevant surface introduced beyond the plan's threat model.

## Known Stubs

One intentional stub requiring May-27 SDK confirmation:

| Stub | File | Line | Reason |
|------|------|------|--------|
| `utci_request = AnalysesName.utci` | coolspend/sdk_client.py | _live_utci body | AnalysesName member name for UTCI must be confirmed against installed SDK version. Marked with TODO comment. One-line change at May-27 wiring. |

This stub does NOT prevent the plan's goal: the live code path is real and wired; the monkeypatched tests exercise it. The stub is a naming placeholder for the confirmed SDK enum value, not a logic gap.

## Self-Check: PASSED

| Item | Result |
|------|--------|
| coolspend/sdk_client.py exists | FOUND |
| coolspend/tests/test_sdk_client_live.py exists | FOUND |
| MOCKS.md exists | FOUND |
| 02-03-SUMMARY.md exists | FOUND |
| Commit d42d04e exists | FOUND |
| Commit a6640c2 exists | FOUND |
| 11 tests pass offline | PASSED |
