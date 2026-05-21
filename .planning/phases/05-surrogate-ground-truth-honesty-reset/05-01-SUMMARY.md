---
phase: 05-surrogate-ground-truth-honesty-reset
plan: "01"
subsystem: spatial-engine
tags: [crs, utm, pyproj, coordinate-transform, fail-closed-guard, d-06, d-07, valid-05]
dependency_graph:
  requires: []
  provides:
    - "UTM-31N (EPSG:32631) CRS boundary in spatial_engine — citywide Barcelona accuracy"
    - "per-site SW-corner origin via set_site_origin_from_polygon"
    - "fail-closed CRS round-trip guard assert_crs_roundtrip + CRSConsistencyError"
    - "guard wired into sdk_client._live_utci before every live API call"
  affects:
    - "coolspend/optimizer.py — SITE_WIDTH_M/SITE_DEPTH_M now follow set polygon automatically"
    - "coolspend/sdk_client.py — _live_utci now guarded by CRS round-trip check"
tech_stack:
  added:
    - "pyproj>=3.6,<4 (3.7.2 installed) — UTM-31N Transformer pair"
  patterns:
    - "pyproj Transformer.from_crs(always_xy=True) — canonical lon/lat input order"
    - "module-level state (_SITE_ORIGIN_E/_N) with lazy fallback initializer"
    - "fail-closed guard pattern: exception before SDK call, unreachable on failure"
key_files:
  modified:
    - coolspend/spatial_engine.py
    - coolspend/sdk_client.py
    - coolspend/tests/test_coordinate_frame.py
    - requirements.txt
decisions:
  - "D-06 honored: pyproj EPSG:32631, always_xy=True, per-site SW UTM corner origin, [0,width]x[0,depth] local frame preserved, no NSGA-II bound rewrite"
  - "D-07 honored: assert_crs_roundtrip measures error in UTM metres (not degrees), raises CRSConsistencyError >= 1m, inserted before InfraredClient call"
  - "Lazy fallback: _ensure_origin_initialized() loads angels_site.geojson boundary on first use — all existing tests/optimizer work unchanged without explicit set_site_origin_from_polygon call"
  - "Test strategy: monkeypatch local_m_to_latlon to return wrong coordinates for fail-closed tests (origin corruption does not work because forward/inverse use same offset — error cancels)"
  - "assert_crs_roundtrip uses _TO_UTM.transform on both original and round-tripped points for UTM euclidean distance — degree-scale errors are avoided per D-07"
metrics:
  duration: "~15m"
  completed: "2026-05-21"
  tasks_completed: 2
  files_modified: 4
---

# Phase 05 Plan 01: UTM-31N CRS Migration + Fail-Closed Guard Summary

**One-liner:** pyproj UTM-31N (EPSG:32631) replaces equirectangular cos-lat; per-site SW-corner origin + CRSConsistencyError guard before every live Infrared call.

## What Was Built

### Task 1: UTM-31N CRS Boundary (D-06)

Replaced the single-anchor equirectangular cos-lat CRS approximation in `spatial_engine.py` with proper pyproj UTM-31N projection (EPSG:32631). The old code was only accurate within ±200 m of the hardcoded Plaça dels Àngels centroid; the new code is valid citywide in Barcelona with sub-metre distortion.

**Key changes:**

- `_TO_UTM` and `_TO_WGS` module-level cached `Transformer` objects with `always_xy=True` (call order: lon, lat → easting, northing and vice versa).
- `set_site_origin_from_polygon(ring_lonlat)`: computes the per-site UTM origin as `(min_easting, min_northing)` of the polygon ring in UTM-31N. Also updates `SITE_WIDTH_M = max(E) - min(E)` and `SITE_DEPTH_M = max(N) - min(N)` so the NSGA-II optimizer bounds follow the site automatically (no optimizer rewrite needed).
- `_ensure_origin_initialized()`: lazy fallback that reads the bundled `angels_site.geojson` boundary on first use. All existing tests and the optimizer work unchanged without an explicit `set_site_origin_from_polygon` call.
- `latlon_to_local_m`: `(e - _SITE_ORIGIN_E, n - _SITE_ORIGIN_N)` — true UTM offsets from SW corner.
- `local_m_to_latlon`: `_TO_WGS.transform(x_m + _SITE_ORIGIN_E, y_m + _SITE_ORIGIN_N)`.
- `load_site()`: first-pass extracts the `site_boundary` ring and calls `set_site_origin_from_polygon` before converting any coordinates.
- `pyproj>=3.6,<4` added to `requirements.txt`.

### Task 2: Fail-Closed Round-Trip Guard (D-07)

Added `CRSConsistencyError(RuntimeError)` and `assert_crs_roundtrip(ring_lonlat, tol_m=1.0)` to `spatial_engine.py`, and wired the guard into `sdk_client._live_utci` immediately after the ring is built and before `with InfraredClient()`.

- Error is measured in **UTM metres** (not degrees) — euclidean distance between the original point and the round-tripped point in UTM-31N space. Satisfies D-07's "measured in metres" requirement.
- Guard is fail-closed: `CRSConsistencyError` propagates out of `_live_utci`; the `InfraredClient` call is unreachable on failure.
- Guard touches only geometry; `INFRARED_API_KEY` is never read, logged, or formatted in this code path (T-05-02 mitigated).

## Test Results

```
33 passed in 18.14s

test_coordinate_frame.py (14 tests):
  - test_roundtrip_plaza_centroid        PASSED  (< 1e-6 m error at plaza)
  - test_roundtrip_far_barcelona_point   PASSED  (Sagrada ~4.4 km from plaza)
  - test_roundtrip_second_barcelona_site PASSED  (Eixample ~1.5 km NE)
  - test_per_site_origin_sw_corner...    PASSED  (SW corner → (0,0) ±1 m)
  - test_site_width_depth_follow_polygon PASSED  (SITE_WIDTH_M updated)
  - test_load_site_still_returns_valid   PASSED  (regression: positive area)
  - test_epsg_32631_present              PASSED
  - test_always_xy_true_present          PASSED
  - test_no_equirectangular_code         PASSED  (0 occurrences)
  - test_assert_crs_roundtrip_passes...  PASSED  (valid Barcelona ring)
  - test_guard_fails_closed_on_bad_ring  PASSED  (CRSConsistencyError raised)
  - test_crs_consistency_error_message   PASSED  (numeric metres in msg)
  - test_guard_blocks_sdk_call...        PASSED  (SDK unreachable on failure)
  - test_assert_crs_roundtrip_symbol...  PASSED  (importable from spatial_engine)

test_spatial_engine.py (4 tests):   4 PASSED  (no regression)
test_optimizer.py (15 tests):       15 PASSED (no regression)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test strategy for fail-closed guard required monkeypatching, not origin corruption**
- **Found during:** Task 2 test implementation (GREEN phase)
- **Issue:** The original test plan for `test_guard_fails_closed_on_bad_ring` patched `_SITE_ORIGIN_E/_SITE_ORIGIN_N` to a far-off value expecting a round-trip error. This doesn't work because `latlon_to_local_m` and `local_m_to_latlon` both use the same origin — the error cancels out perfectly (the round-trip is always algebraically exact regardless of origin value).
- **Fix:** Changed test to monkeypatch `local_m_to_latlon` to return a point ~10 km away, simulating a broken CRS inverse. Same for the "SDK blocked" test. The guard correctly detects the >1 m error and raises `CRSConsistencyError`.
- **Files modified:** `coolspend/tests/test_coordinate_frame.py`
- **Commit:** 81c2433

## Acceptance Criteria — All Satisfied

| Criterion | Result |
|-----------|--------|
| `grep -c "EPSG:32631" coolspend/spatial_engine.py >= 1` | 5 occurrences |
| `grep -c "pyproj" requirements.txt == 1` | 1 occurrence |
| `grep -c "always_xy=True" coolspend/spatial_engine.py >= 1` | 3 occurrences |
| `grep -c "def set_site_origin_from_polygon" == 1` | 1 occurrence |
| `grep -c "equirectangular" == 0` | 0 occurrences |
| `python -c "import pyproj"` exits 0 | pyproj 3.7.2 installed |
| `pytest test_coordinate_frame.py` exits 0 | 14/14 passed |
| `grep -c "def assert_crs_roundtrip" == 1` | 1 occurrence |
| `grep -c "class CRSConsistencyError" == 1` | 1 occurrence |
| `grep -c "assert_crs_roundtrip" coolspend/sdk_client.py >= 1` | 2 occurrences |
| `pytest test_spatial_engine.py` exits 0 | 4/4 passed |
| `pytest test_optimizer.py` exits 0 | 15/15 passed |

## Known Stubs

None — this plan owns only coordinate transforms and the CRS guard. No UI, no data rendering stubs introduced.

## Threat Surface Scan

T-05-01 (Tampering) and T-05-02 (Information disclosure) from the plan's threat model are both mitigated:
- T-05-01: `assert_crs_roundtrip` fires before every live call, fails closed on >= 1 m mismatch.
- T-05-02: Guard only touches geometry coordinates; `INFRARED_API_KEY` is never read, formatted, or logged in the guard code path.

No new threat surface introduced beyond what was planned.

## Self-Check: PASSED

All key files exist. All 3 task commits found (3aa4f14, 81c2433, 48b042c). 33/33 tests pass.
