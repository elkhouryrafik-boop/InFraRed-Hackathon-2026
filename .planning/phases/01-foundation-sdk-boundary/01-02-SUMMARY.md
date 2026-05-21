---
phase: 01-foundation-sdk-boundary
plan: "02"
subsystem: spatial-engine
tags: [spatial, geojson, shapely, crs, offline, tdd]
dependency_graph:
  requires: [01-01-sdk-boundary]
  provides: [spatial_engine, angels_site.geojson, CRS-boundary, is_valid_location]
  affects: [02-optimizer, 02-rules-engine]
tech_stack:
  added: [shapely==2.1.2, numpy>=2.4.0]
  patterns: [single-CRS-boundary, offline-fixture, shapely-collision, module-cache]
key_files:
  created:
    - coolspend/spatial_engine.py
    - coolspend/data/angels_site.geojson
    - coolspend/tests/test_spatial_engine.py
    - coolspend/tests/test_coordinate_frame.py
  modified:
    - MOCKS.md
decisions:
  - "equirectangular + cos-latitude correction for small-area CRS conversion — accurate within +/-200m of plaza centroid, no geodesy dep"
  - "EPSG:4326 centroid anchor maps to (SITE_WIDTH_M/2, SITE_DEPTH_M/2) so the local-metre origin stays at SW corner = (0,0)"
  - "STREET_BUFFER_M=1.5 m rejection radius around street centerlines — prevents tree placement on pavement edge"
  - "shapely import wrapped in RuntimeError guard — fails loudly if dep missing, never silently returns wrong results"
  - "load_site() caches by resolved path string in _SITE_CACHE — avoids repeated disk reads in NSGA-II loop"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-21T00:20:01Z"
  tasks_completed: 3
  files_created: 4
  files_modified: 1
  commits: 3
---

# Phase 01 Plan 02: Spatial Engine Summary

**One-liner:** GeoJSON site loader with shapely collision (buildings/streets/boundary) and a single documented EPSG:4326 <-> plaza-local-metres CRS boundary — tested offline against a hand-authored fixture.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Author offline site GeoJSON fixture + MOCKS.md row | cbdb4df | coolspend/data/angels_site.geojson, MOCKS.md |
| 2 (RED) | TDD failing tests for spatial_engine collision + CRS | 74c173d | coolspend/tests/test_spatial_engine.py, coolspend/tests/test_coordinate_frame.py |
| 2 (GREEN) | Implement spatial_engine.py — site loader, CRS boundary, is_valid_location | 786b275 | coolspend/spatial_engine.py |
| 3 | Tests verified — collision + CRS (included in RED/GREEN commits above) | 74c173d / 786b275 | — |

## Verification Results

- `python -c "from coolspend import spatial_engine"` — PASS
- `python -m pytest coolspend/tests/test_spatial_engine.py coolspend/tests/test_coordinate_frame.py -q` — PASS (6 passed)
- `python -m pytest coolspend/tests/ -q` — PASS (12 passed, all plans)
- `grep -Eq "def latlon_to_local_m|def local_m_to_latlon" coolspend/spatial_engine.py` — PASS
- `grep -q "eval(" coolspend/spatial_engine.py` — PASS (exit 1, no match)
- `grep -q "angels_site.geojson" MOCKS.md` — PASS
- `python -c "import json; d=json.load(open('coolspend/data/angels_site.geojson')); kinds={...}; assert {'site_boundary','building','street'} <= kinds"` — PASS

## What Was Built

### `coolspend/data/angels_site.geojson` (81 lines)
Valid GeoJSON FeatureCollection in EPSG:4326 (GeoJSON spec: lon, lat order), anchored
at plaza centroid (lon=2.1670, lat=41.3826). Contains:
- `kind="site_boundary"`: Polygon 60m E-W x 42m N-S enclosing the plaza
- `kind="building"` (x2): MACBA north-edge strip (8m deep, full width) + east pavilion block (7m x 7m)
- `kind="street"` (x1): E-W centerline at y=21m (plaza mid-point), extending full site width

### `coolspend/spatial_engine.py` (267 lines)
Core spatial engine:

- **`SITE_WIDTH_M`, `SITE_DEPTH_M`, `SITE_ORIGIN_LON`, `SITE_ORIGIN_LAT`, `HERITAGE_BUFFER_M`, `STREET_BUFFER_M`** — module-level constants
- **`latlon_to_local_m(lon, lat)`**: THE ONLY CRS conversion in coolspend (SPATIAL-03). Equirectangular + cos-latitude correction. Docstring explicitly states single-boundary rule.
- **`local_m_to_latlon(x_m, y_m)`**: THE ONLY inverse CRS conversion. Exact algebraic inverse.
- **`load_site(path=None)`**: reads GeoJSON via `json.load` (never exec/eval), converts all coordinates to local metres, builds shapely Polygon/LineString geometries, caches by path, raises clear errors on bad input.
- **`is_valid_location(x_m, y_m, site=None)`**: returns False for in-building (`.contains`), near-street (`.distance`), and out-of-boundary; True for open interior points.
- `__main__` smoke block exercises all public functions.

### `coolspend/tests/test_spatial_engine.py` (111 lines)
Four pytest tests:
1. `test_inside_building_rejected` — centroid of building polygon -> False
2. `test_on_street_rejected` — point within STREET_BUFFER_M/2 of street vertex -> False
3. `test_outside_boundary_rejected` — x_m=-5 (west of site) -> False
4. `test_open_location_valid` — (30.0, 10.0) clear of all obstacles -> True (with grid fallback)

### `coolspend/tests/test_coordinate_frame.py` (69 lines)
Two pytest tests:
1. `test_roundtrip` — centroid + offset point round-trip within 1e-6 deg
2. `test_origin_maps_into_site` — SITE_ORIGIN maps to (SITE_WIDTH_M/2, SITE_DEPTH_M/2)

### `MOCKS.md`
New row: `angels_site.geojson fixture` — status MOCK, hand-authored, replacement path is real OSM export.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] shapely not installed in active Python venv**
- **Found during:** RED phase test run
- **Issue:** `python -m pytest` ran in the hermes-agent venv (Python 3.11.15) which had no pip bootstrapped and no shapely installed. Tests failed with `ModuleNotFoundError: No module named 'shapely'`.
- **Fix:** Bootstrapped pip via `python -m ensurepip --upgrade` then `python -m pip install shapely` which installed shapely 2.1.2 + numpy 2.4.6 into the venv.
- **Files modified:** none (venv installation)
- **Commit:** no separate commit needed (infrastructure fix)

**2. [Rule 1 - Bug] `eval(` literal in docstring comment caused acceptance test failure**
- **Found during:** GREEN phase acceptance criteria check
- **Issue:** The docstring for `load_site()` contained the text `never eval()` for documentation, which caused the acceptance criterion `grep -q "eval(" coolspend/spatial_engine.py` (which should return exit 1 = no match) to return exit 0 (match found).
- **Fix:** Changed docstring text from `never eval()` to `never exec/eval` — preserves intent while eliminating the pattern match.
- **Files modified:** coolspend/spatial_engine.py (docstring only)
- **Commit:** included in GREEN commit 786b275

## TDD Gate Compliance

- RED gate: commit `74c173d` — `test(01-02): add failing tests for spatial_engine collision + CRS boundary`
- GREEN gate: commit `786b275` — `feat(01-02): implement spatial_engine.py ...`
- REFACTOR gate: not needed (implementation was clean on first pass)

## Known Stubs

None — all functions fully implemented and tested. The fixture geometry is hand-authored
(documented in MOCKS.md as required) but serves its purpose as a deterministic offline test fixture.

## Threat Flags

No new unplanned security surface. All four planned mitigations implemented:

- **T-01-05 (Tampering/code injection):** `json.load` only; `grep -q "eval(" coolspend/spatial_engine.py` exits 1 (no match).
- **T-01-06 (CRS integrity):** Single documented boundary verified by test_coordinate_frame.py.
- **T-01-07 (Spoofing/fixture confusion):** MOCKS.md row added with status=MOCK and replacement path.
- **T-01-08 (DoS/malformed GeoJSON):** Accepted as local-only; file size bounded by hand-authored content.

## Self-Check: PASSED

All created files exist:
- FOUND: coolspend/spatial_engine.py
- FOUND: coolspend/data/angels_site.geojson
- FOUND: coolspend/tests/test_spatial_engine.py
- FOUND: coolspend/tests/test_coordinate_frame.py
- FOUND: MOCKS.md (modified)
- FOUND: .planning/phases/01-foundation-sdk-boundary/01-02-SUMMARY.md

All commits verified:
- FOUND: cbdb4df (Task 1 — GeoJSON fixture + MOCKS.md)
- FOUND: 74c173d (Task 2 RED — failing tests)
- FOUND: 786b275 (Task 2/3 GREEN — spatial_engine implementation)
