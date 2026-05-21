---
phase: 01-foundation-sdk-boundary
verified: 2026-05-21T00:00:00Z
status: passed
score: 13/13 must-haves verified
overrides_applied: 0
re_verification: false
gaps: []
human_verification: []
---

# Phase 1: Foundation & SDK Boundary — Verification Report

**Phase Goal:** Offline-testable skeleton — clean coolspend/ package with a single Infrared sdk_client (mock|cached|live + SimBudget guard), spatial_engine (GeoJSON + shapely collision + single CRS boundary), and cost_model (CapEx/OpEx, €/°C KPI). Everything runs offline without the API key.
**Verified:** 2026-05-21
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Developer can call get_baseline_utci()/get_intervention_utci() with INFRARED_BACKEND=mock and no API key, getting a deterministic UTCI delta | VERIFIED | sdk_client.py:241-257; test_mock_backend_runs_offline passes; baseline=41.0, intervention=37.33 at coverage_fraction=0.35 |
| 2  | INFRARED_BACKEND=live with no INFRARED_API_KEY raises EnvironmentError | VERIFIED | sdk_client.py:220-225; test_live_without_key_raises passes; error message explicitly names INFRARED_API_KEY |
| 3  | INFRARED_BACKEND=cached with a cache miss raises FileNotFoundError (no fallthrough to mock) | VERIFIED | sdk_client.py:212-218; test_cached_miss_raises passes; uses uuid4 geometry to guarantee miss |
| 4  | Every mock response carries disclaimer="NOT MEASURED DATA ..." | VERIFIED | MOCK_DISCLAIMER constant at sdk_client.py:60; all mock paths return this string; confirmed by direct execution |
| 5  | SimBudget raises RuntimeError past cap and logs each live call | VERIFIED | SimBudget.record() at sdk_client.py:130-143; test_simbudget_caps passes; log has N entries before raise; logger.info emitted per call |
| 6  | spatial_engine loads a site GeoJSON (buildings, streets, site boundary) offline | VERIFIED | load_site() at spatial_engine.py:118-200; DEFAULT_SITE bundled at coolspend/data/angels_site.geojson; 4 features: 1 boundary, 2 buildings, 1 street |
| 7  | is_valid_location returns False for in-building point | VERIFIED | spatial_engine.py:238-241; test_inside_building_rejected passes; uses building centroid |
| 8  | is_valid_location returns False for on-street-centerline point | VERIFIED | spatial_engine.py:243-245; test_on_street_rejected passes; checks distance <= STREET_BUFFER_M=1.5 |
| 9  | is_valid_location returns False for outside-boundary point | VERIFIED | spatial_engine.py:235-237; test_outside_boundary_rejected passes; x_m=-5.0 correctly rejected |
| 10 | EPSG:4326 <-> plaza-local-metres conversion at exactly ONE boundary; round-trips within tolerance | VERIFIED | latlon_to_local_m/local_m_to_latlon defined ONLY in spatial_engine.py (confirmed by grep); test_roundtrip and test_origin_maps_into_site pass at 1e-6 deg tolerance |
| 11 | cost_per_utci_degree returns a finite EUR/degC value with documented CapEx/OpEx constants; zero/negative delta guarded | VERIFIED | cost_model.py:89-160; CAPEX=350, OPEX/yr=35, horizon=10 all visible DECLARED constants; zero+negative guard returns value=None, confidence=LOW, no exception |
| 12 | Banned reference client files NOT imported anywhere in coolspend/ | VERIFIED | grep over all coolspend/*.py finds no `import`/`from` statements for infrared_client_v2, nature_infrared_client, or infrared_sdk; only doc-comment references in sdk_client.py |
| 13 | MOCKS.md honesty ledger documents mock UTCI delta, fixture site, and DECLARED cost constants | VERIFIED | All three rows present: "mock UTCI delta" (MOCK), "angels_site.geojson fixture" (MOCK), "CapEx/OpEx tree cost constants" (DECLARED); REQUIRES_VERIFICATION used; no fabricated citations |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `coolspend/__init__.py` | Package marker + `__version__` | VERIFIED | `__version__ = "0.1.0"` present; module docstring present |
| `coolspend/sdk_client.py` | mock/cached/live dispatch + SimBudget + UTCIResult | VERIFIED | 285 lines (min 120); all 4 exports importable; `_backend()` reads env at dispatch time |
| `coolspend/tests/test_sdk_client.py` | 6 offline backend/SimBudget tests | VERIFIED | 102 lines (min 40); 6 named tests all pass |
| `coolspend/spatial_engine.py` | GeoJSON loader, is_valid_location, single CRS conversion | VERIFIED | 267 lines (min 90); all 4 exports importable; `.contains()`/`.distance()` confirmed present |
| `coolspend/data/angels_site.geojson` | FeatureCollection with boundary, building, street | VERIFIED | Valid JSON; kinds={site_boundary, building, street} present; description notes MOCK status |
| `coolspend/tests/test_spatial_engine.py` | 4 collision validity tests | VERIFIED | 111 lines (min 40); all 4 tests pass |
| `coolspend/tests/test_coordinate_frame.py` | 2 CRS round-trip tests | VERIFIED | 69 lines (min 20); both tests pass |
| `coolspend/cost_model.py` | CapEx/OpEx constants, per_tree_cost, total_cost, cost_per_utci_degree | VERIFIED | 183 lines (min 70); all 3 exports + CAPEX_PER_TREE_EUR importable; REQUIRES_VERIFICATION comment present |
| `coolspend/tests/test_cost_model.py` | 7 cost-model math tests | VERIFIED | 105 lines (min 30); all 7 tests pass (8 collected due to parametrize) |
| `MOCKS.md` | Three rows: mock UTCI, fixture site, DECLARED cost constants | VERIFIED | All three rows confirmed; no fabricated citations |
| `.gitignore` | `.env`, `coolspend/cache/`, `__pycache__/`, `*.pyc` | VERIFIED | All four mandatory entries present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `sdk_client.py` | `INFRARED_BACKEND` env var | `_backend()` reads `os.environ.get("INFRARED_BACKEND"` at dispatch time | WIRED | Pattern confirmed at sdk_client.py:65; env read inside `_dispatch()`, not at import |
| `sdk_client.py::SimBudget` | live UTCI call counter | `record()` increments `self.calls`, appends to `self.log`, raises past cap | WIRED | sdk_client.py:130-143; class SimBudget confirmed; log/raise logic verified by test and direct execution |
| `spatial_engine.py::is_valid_location` | loaded site geometry | shapely `.contains()` / `.distance()` checks | WIRED | spatial_engine.py:235-245; both methods confirmed present in code and by passing tests |
| `spatial_engine.py` | `coolspend/data/angels_site.geojson` | `load_site()` reads `Path(__file__).resolve().parent / "data"` | WIRED | DATA_DIR / DEFAULT_SITE at spatial_engine.py:50-51; Path(__file__) confirmed |
| `cost_model.py::cost_per_utci_degree` | total_cost + validated UTCI delta | euro / degC division with zero-delta guard | WIRED | cost_model.py:126-160; guard checks `delta is None or delta <= 0`; returns `None` without dividing |
| `cost_model.py::per_tree_cost` | CapEx + OpEx constants | `CAPEX_PER_TREE_EUR + OPEX_PER_TREE_YEAR_EUR * horizon` | WIRED | cost_model.py:71; formula confirmed; test_per_tree_cost_capex_only and test_per_tree_cost_includes_opex pass |

---

### Data-Flow Trace (Level 4)

All three modules are pure computation or read-from-fixture (no user-supplied dynamic data). No dashboard/live rendering components.

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `sdk_client.py` | `utci_c` | `UTCI_BASELINE_OPEN_C` / `UTCI_UNDER_CANOPY_C` constants + `coverage_fraction` from input geometry | Yes — deterministic mock scalar; MOCK-tagged | FLOWING |
| `spatial_engine.py` | `boundary`, `buildings`, `streets` | `angels_site.geojson` read via `json.load`; converted to shapely objects | Yes — fixture file produces real shapely geometries | FLOWING |
| `cost_model.py` | `value` | `CAPEX_PER_TREE_EUR`, `OPEX_PER_TREE_YEAR_EUR`, `OPEX_HORIZON_YEARS` constants + config dict | Yes — arithmetic on DECLARED constants + caller-supplied config | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command/Check | Result | Status |
|----------|--------------|--------|--------|
| `INFRARED_BACKEND=mock` path offline (no key) | `get_baseline_utci({'width_m':30,'coverage_fraction':0.35})` | utci_c=41.0, disclaimer="NOT MEASURED DATA ..." | PASS |
| Intervention cools below baseline | `get_intervention_utci(same)` | utci_c=37.33 < 41.0; delta=3.67 | PASS |
| `live` raises EnvironmentError without key | `INFRARED_BACKEND=live; pop INFRARED_API_KEY` | EnvironmentError raised, message names INFRARED_API_KEY | PASS |
| `cached` raises FileNotFoundError on miss | uuid4 geometry; `INFRARED_BACKEND=cached` | FileNotFoundError raised | PASS |
| SimBudget logs 3 calls, raises on 4th | `SimBudget(3); record x3; record overflow` | Log has 3 entries; RuntimeError on 4th | PASS |
| `cost_per_utci_degree` returns finite EUR/degC | 10 trees, delta=0.5 | value=14000.0, unit="EUR/degC", confidence="MED" | PASS |
| Zero/negative delta guarded | delta=0.0 and delta=-0.3 | value=None, confidence="LOW", no exception | PASS |
| CRS round-trip | `latlon_to_local_m` -> `local_m_to_latlon` | Error < 1e-12 deg (well within 1e-6 tolerance) | PASS |
| No banned imports in coolspend/ | grep for `import.*infrared_client_v2|nature_infrared_client|infrared_sdk` | 0 matches (only doc comments reference filenames) | PASS |
| Full pytest suite offline | `python -m pytest coolspend/tests/ -v` | 22/22 passed in 0.14s | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SDK-01 | 01-01 | Single `sdk_client` exposes mock/cached/live selected by `INFRARED_BACKEND`; live reads `INFRARED_API_KEY` | SATISFIED | `_backend()` + `_dispatch()` in sdk_client.py; all three paths tested |
| SDK-02 | 01-01 | App runs end-to-end offline on mock/cached backend (no key required) | SATISFIED | 6 tests pass with no API key; `INFRARED_BACKEND` defaults to "mock" |
| SDK-03 | 01-01 | `SimBudget` guard caps number of real live UTCI calls per run and logs each call | SATISFIED | `SimBudget.record()` caps+logs; test_simbudget_caps passes; `logger.info` emits per call |
| SPATIAL-01 | 01-02 | Load a site as OSM/GeoJSON (buildings, streets, site boundary) | SATISFIED | `load_site()` parses `angels_site.geojson`; returns {boundary, buildings, streets} as shapely geometries |
| SPATIAL-02 | 01-02 | `is_valid_location(x, y)` rejects in-building, on-street, outside-boundary | SATISFIED | All three rejection tests pass; open-point acceptance test passes |
| SPATIAL-03 | 01-02 | EPSG:4326 <-> plaza-local-metres at exactly one documented boundary | SATISFIED | `latlon_to_local_m` / `local_m_to_latlon` exist ONLY in spatial_engine.py; round-trip test passes |
| COST-01 | 01-03 | Per-tree cost = CapEx + OpEx with documented assumptions | SATISFIED | CAPEX=350, OPEX/yr=35, horizon=10 visible DECLARED constants; REQUIRES_VERIFICATION tags; MOCKS.md row present |
| COST-02 | 01-03 | Headline KPI: °C UTCI relief per euro | SATISFIED | `cost_per_utci_degree()` returns standard metric dict with value in EUR/degC; zero/negative guard returns value=None |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | No stubs, placeholders, or hardcoded empty returns found in production paths |

Scanned for: TODO/FIXME/PLACEHOLDER, `return null`/`return []`/`return {}`, `console.log`, props hardcoded empty. The `NotImplementedError` in the live path is intentional and documented — it is the correct Phase 1 boundary marker, not a stub hiding missing work.

---

### Human Verification Required

None. All must-haves are fully verifiable programmatically and the full test suite passes offline.

---

## Gaps Summary

No gaps. All 13 observable truths verified, all 11 required artifacts pass 4-level checks, all 6 key links wired, all 8 requirements satisfied, full pytest suite (22/22) passes offline with no API key.

---

_Verified: 2026-05-21_
_Verifier: Claude (gsd-verifier)_
