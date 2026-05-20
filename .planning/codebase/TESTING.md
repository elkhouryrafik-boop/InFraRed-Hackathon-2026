# Testing Patterns

**Analysis Date:** 2026-05-21
**Source files:** `nature_nsga2_coolstock.py`, `nature_metrics.py`, `infrared_client_v2.py`, `nature_infrared_client.py`
**Architecture reference:** `nature_architecture.md` (L5 DEFEND section; `tests/test_sparql_engine.py` mentioned)

---

## Test Framework

**Runner:**
- Not declared in any package manifest in the analysed files; `tests/test_sparql_engine.py` exists per `nature_architecture.md` (27 patterns, behaviour-identical check). Assumed `pytest` (standard for the Python ecosystem used).
- Config file: not detected in the analysed files.

**Assertion Library:**
- Standard `assert` / `pytest` assertions (inferred from `test_sparql_engine.py` reference).

**Run Commands (to establish for coolspend):**
```bash
pytest tests/                     # Run all tests
pytest tests/ -v                  # Verbose
pytest tests/ -k "surrogate"      # Run a specific group
pytest tests/ --tb=short          # Short tracebacks (fast hackathon feedback)
```

---

## Existing Test Coverage in NatureGooddest

**Confirmed tests:**
- `tests/test_sparql_engine.py` — 27 pattern behaviour-identity tests (SPARQL path vs. legacy AST path, 18 fire). Locks the L5 firing engine. Referenced in `nature_architecture.md` L5 section.

**Smoke tests via `__main__` blocks (executable but not in test suite):**
- `nature_nsga2_coolstock.py` — runs full NSGA-II (seed=42, n_gen=100, pop=100), prints Top-3, saves outputs.
- `nature_metrics.py` — calls `compute_all(coverage_fraction=0.237, modules=144, plaza_area_m2=3800.0)`, prints confidence ribbons, reports latency.
- `infrared_client_v2.py` — calls `simulate_all()` with sample geometry, prints per-metric stats and hash.

No unit tests were found in the analysed modules themselves. The project's test discipline lives primarily in: (a) the `tests/test_sparql_engine.py` integration lock, and (b) `__main__` smoke blocks used as manual regression checks.

---

## How the Surrogate Enables Deterministic Seed-Pinned Testing

The NSGA-II optimiser in `nature_nsga2_coolstock.py` is run with `seed=42` in every call:

```python
# nature_nsga2_coolstock.py — run_optimisation()
result = minimize(
    problem,
    algorithm,
    termination,
    seed=seed,       # default seed=42
    verbose=True,
    save_history=False,
)
```

The surrogate objective functions (`delta_tmrt_surrogate`, `shade_efficiency`, `pollinator_corridor_score`) are **pure mathematical functions** — no random state, no I/O, no side effects:

```python
# nature_nsga2_coolstock.py — pure function, deterministic
def shade_efficiency(tilt_deg: float, height_m: float) -> float:
    tilt_factor = 1.0 + 0.15 * (tilt_deg / 30.0)
    height_factor = 1.0 + 0.05 * ((height_m - 2.5) / 2.5)
    return tilt_factor * height_factor
```

**Consequence for testing:** with `seed=42` and the analytical surrogate, the full NSGA-II run is **byte-reproducible** across machines. `result.F` (Pareto front) and `select_top3(result)` return identical values on every run. This means:

- The Top-3 output (`top3_configurations.json`) is a stable regression fixture.
- Any change to the surrogate math immediately shows up as a changed Pareto front — detectable by comparing `result.F` or the extracted `delta_tmrt_c` values.
- Cost-model math (scaffold modules, assembly time, embodied carbon) can be tested by asserting on known seed=42 decoded outputs.

The infrared mock client (`infrared_client_v2.py`) is similarly deterministic: field values are computed via `math.sin`/`math.cos` with fixed row/col indices — no random state. The geometry hash (`_geometry_hash`) is a deterministic SHA-256 of the sorted JSON, so cache keys are stable.

---

## Recommended Minimal Test Strategy for a 3-Day Hackathon

Four test areas, ordered by risk and return on time invested. Target: ~15-20 focused tests total.

---

### Area 1 — Spatial Collision Validity (`spatial_engine.py`)

**Why:** The NSGA-II optimiser generates tree coordinates that must not land inside buildings or outside the site boundary. A silent failure here means the optimiser produces invalid solutions with no error.

**What to test:**
- A point known to be inside a building returns `False` from `is_valid_location(x, y)`.
- A point known to be inside the site boundary but outside all buildings returns `True`.
- A point outside the site boundary returns `False`.
- Edge case: a point exactly on a building boundary (test `contains` vs `intersects` semantics).

**Test pattern:**
```python
# tests/test_spatial_engine.py
import pytest
from spatial_engine import SpatialEngine

GEOJSON_PATH = "data/site_context.geojson"

@pytest.fixture
def engine():
    return SpatialEngine(GEOJSON_PATH)

def test_point_inside_building_is_invalid(engine):
    # Use a coordinate known to be inside a mock building polygon
    assert engine.is_valid_location(10.0, 10.0) is False

def test_point_in_open_space_is_valid(engine):
    assert engine.is_valid_location(30.0, 20.0) is True

def test_point_outside_site_boundary_is_invalid(engine):
    assert engine.is_valid_location(999.0, 999.0) is False
```

**Mock data strategy:** `data/site_context.geojson` should contain at minimum one `building` polygon and one `site` boundary polygon with known coordinates. Do not use real OSM data in unit tests — use a minimal 2-polygon fixture.

---

### Area 2 — Surrogate Determinism (seed=42 regression)

**Why:** Any edit to `delta_tmrt_surrogate`, `shade_efficiency`, or `pollinator_corridor_score` changes the Pareto front. This is the bug that caused the double-porosity-penalty issue (audit C10, `nature_nsga2_coolstock.py` lines 115-155). A regression test catches it immediately.

**What to test:**
- `shade_efficiency` returns the known value for a fixed (tilt, height) input.
- `delta_tmrt_surrogate` returns the known value for a fixed (shade_fraction, porosity_pct, tilt, height) input.
- `pollinator_corridor_score` returns the expected value for a known (x, y, width) combination.
- Full NSGA-II run with `seed=42` produces `len(result.F) > 0` and `select_top3(result)[0]["delta_tmrt_c"]` within a known tolerance.

**Test pattern:**
```python
# tests/test_surrogate.py
from nature_nsga2_coolstock import shade_efficiency, delta_tmrt_surrogate, pollinator_corridor_score

def test_shade_efficiency_known_values():
    # At tilt=30, height=5.0: tilt_factor = 1.15, height_factor = 1.05
    result = shade_efficiency(tilt_deg=30.0, height_m=5.0)
    assert abs(result - 1.15 * 1.05) < 1e-9

def test_delta_tmrt_surrogate_porosity_applied_once():
    # Regression for audit C10: porosity must be applied exactly once.
    # shade_fraction = 1 - 0.12 = 0.88 (porosity 12%)
    val_12pct = delta_tmrt_surrogate(0.88, 12.0, 0.0, 2.5)
    val_15pct = delta_tmrt_surrogate(0.85, 15.0, 0.0, 2.5)
    # 15% porosity should give less cooling than 12%
    assert val_15pct < val_12pct

def test_surrogate_bounded_by_max():
    # Even at perfect shade, delta cannot exceed MAX_TMRT_REDUCTION (12.0)
    result = delta_tmrt_surrogate(1.0, 0.0, 30.0, 5.0)
    assert result <= 12.0

def test_pollinator_score_at_heritage_buffer():
    # y_m = HERITAGE_BUFFER_M (5.0) -> distance_from_north = 0 -> north_score = 1.0
    score = pollinator_corridor_score(x_m=27.5, y_m=5.0, width_m=10.0)
    assert score >= 0.85  # max north component (0.85) + small east bonus
```

**Seed-pinned integration test (optional — ~30s, mark slow):**
```python
# tests/test_nsga2_seed.py
import pytest
from nature_nsga2_coolstock import run_optimisation, select_top3

@pytest.mark.slow
def test_nsga2_seed42_pareto_nonempty():
    result = run_optimisation(n_gen=10, pop_size=20, seed=42)  # fast subset
    assert len(result.F) > 0

@pytest.mark.slow
def test_nsga2_seed42_top3_structure():
    result = run_optimisation(n_gen=10, pop_size=20, seed=42)
    configs = select_top3(result)
    assert len(configs) == 3
    for cfg in configs:
        assert "delta_tmrt_c" in cfg
        assert cfg["delta_tmrt_c"] >= 0
        assert cfg["scaffold_modules"] <= 500  # ULMA_STOCK constraint
```

---

### Area 3 — Cost-Model Math (`rules_engine.py` / metric functions)

**Why:** Carbon, cost, and assembly-time calculations are presented to the jury as credible numbers. Off-by-one or unit errors in these are hard to spot visually but easy to pin in tests.

**What to test from `nature_metrics.py`:**
- `carbon_headroom_kgco2e(modules=100)` returns a value proportional to `100 * 18.0 * steel_gwp` and carries `confidence == "HIGH"` when ÖKOBAUDAT file is present.
- `carbon_headroom_kgco2e(modules=0)` returns `value == 0.0`.
- Any metric function with a missing data file returns `{"value": None, "confidence": "LOW", "error": ...}` — not an exception.

**Test pattern:**
```python
# tests/test_metrics.py
from nature_metrics import carbon_headroom_kgco2e, utci_hours_above

def test_carbon_zero_modules():
    result = carbon_headroom_kgco2e(modules=0)
    # Either 0.0 (if ÖKOBAUDAT present) or None (if missing) — never raises
    assert result["value"] is None or result["value"] == pytest.approx(0.0)

def test_carbon_proportional_to_modules():
    r50  = carbon_headroom_kgco2e(modules=50)
    r100 = carbon_headroom_kgco2e(modules=100)
    if r50["value"] is not None and r100["value"] is not None:
        assert r100["value"] == pytest.approx(r50["value"] * 2, rel=1e-6)

def test_metric_returns_standard_shape():
    result = utci_hours_above(threshold_c=32.0, coverage_fraction=0.0)
    for key in ("value", "unit", "confidence", "sources", "note", "metric_id"):
        assert key in result, f"Missing key: {key}"

def test_missing_data_returns_low_confidence_not_raises(tmp_path, monkeypatch):
    import nature_metrics as nm
    monkeypatch.setattr(nm, "EPW_PATH", tmp_path / "nonexistent.epw")
    nm._EPW_CACHE.clear()
    result = nm.utci_hours_above()
    assert result["confidence"] == "LOW"
    assert result["value"] is None
```

**For coolspend `rules_engine.py` cost model (to be implemented):**
```python
# tests/test_rules_engine.py — template
def test_ecological_score_range():
    # Score must always be in [0.0, 1.0]
    from rules_engine import calculate_ecological_score
    coords = [(10.0, 10.0), (20.0, 20.0)]
    species = ["Quercus ilex", "Pinus pinea"]
    score = calculate_ecological_score(coords, species)
    assert 0.0 <= score <= 1.0

def test_min_spacing_violation_penalises_score():
    # Two trees at the same location should score lower than two trees 10m apart
    close  = calculate_ecological_score([(10.0, 10.0), (10.5, 10.0)], ["A", "B"])
    spaced = calculate_ecological_score([(10.0, 10.0), (20.0, 10.0)], ["A", "B"])
    assert spaced > close
```

---

### Area 4 — SDK Client Mock Path (`infrared_client_v2.py`)

**Why:** The mock backend must be the default and must return structurally valid responses. If `INFRARED_BACKEND` is not set, the client must not attempt a live HTTP call. This is the boundary between "demo works offline" and "demo crashes at jury presentation."

**What to test:**
- Default `INFRARED_BACKEND` (env var not set) resolves to `"mock"`.
- `simulate_tmrt(geometry)` returns a dict with `field`, `stats`, `metadata` keys.
- `metadata["disclaimer"]` contains `"NOT MEASURED DATA"` — the honesty tag is present.
- `stats["mean"]` is a float within the physically plausible range for Tmrt (30–70 °C).
- `_geometry_hash` is deterministic: same input → same hash on repeated calls.
- Setting `INFRARED_BACKEND=live` raises `NotImplementedError` (not a silent HTTP timeout).

**Test pattern:**
```python
# tests/test_infrared_client.py
import os
import pytest
from infrared_client_v2 import simulate_tmrt, simulate_utci, _geometry_hash

SAMPLE_GEOM = {
    "site_id": "TEST-001",
    "polygon": [[0, 0], [60, 0], [60, 60], [0, 60]],
    "fired_patterns": ["P01"],
}

def test_default_backend_is_mock(monkeypatch):
    monkeypatch.delenv("INFRARED_BACKEND", raising=False)
    result = simulate_tmrt(SAMPLE_GEOM)
    assert result["metadata"]["backend"] == "mock"

def test_response_structure():
    result = simulate_tmrt(SAMPLE_GEOM)
    assert "field" in result
    assert "stats" in result
    assert "metadata" in result
    assert result["grid_rows"] == 24
    assert result["grid_cols"] == 24

def test_disclaimer_present():
    result = simulate_tmrt(SAMPLE_GEOM)
    assert "NOT MEASURED DATA" in result["metadata"]["disclaimer"]

def test_tmrt_stats_physically_plausible():
    result = simulate_tmrt(SAMPLE_GEOM)
    stats = result["stats"]
    assert 20.0 <= stats["mean"] <= 80.0
    assert stats["p10"] <= stats["mean"] <= stats["p90"]

def test_geometry_hash_deterministic():
    h1 = _geometry_hash(SAMPLE_GEOM)
    h2 = _geometry_hash(SAMPLE_GEOM)
    assert h1 == h2
    assert len(h1) == 16  # SHA-256 truncated to 16 chars

def test_live_backend_raises_not_implemented(monkeypatch):
    monkeypatch.setenv("INFRARED_BACKEND", "live")
    with pytest.raises(NotImplementedError):
        simulate_tmrt(SAMPLE_GEOM)
```

---

## Test File Organisation

**Recommended layout for coolspend:**
```
coolspend/
├── spatial_engine.py
├── rules_engine.py
├── optimize_trees.py
├── main.py
├── data/
│   └── site_context.geojson      # minimal 2-polygon fixture for tests
└── tests/
    ├── __init__.py
    ├── test_spatial_engine.py     # Area 1: collision validity
    ├── test_surrogate.py          # Area 2: surrogate determinism (fast)
    ├── test_nsga2_seed.py         # Area 2: seed-pinned integration (marked slow)
    ├── test_metrics.py            # Area 3: cost-model math
    └── test_infrared_client.py    # Area 4: SDK mock path
```

**Naming convention:**
- Test files: `test_<module_name>.py`
- Test functions: `test_<what>_<expected_outcome>()` — e.g. `test_point_inside_building_is_invalid`
- Mark slow integration tests: `@pytest.mark.slow` and run with `pytest -m "not slow"` in fast mode

---

## Mock Data Strategy for Tests

Following the `infrared_client_v2.py` pattern, test fixtures should use **structurally correct but minimal data**, not real external files:

- `data/site_context.geojson` — two features: one `building` polygon at known coordinates, one `site` boundary polygon. Checked in, not generated.
- Mock the EPW path in `nature_metrics.py` tests using `monkeypatch` (see Area 3 example above) — do not depend on the real 100 MB EPW file in unit tests.
- For NSGA-II integration tests, use `n_gen=10, pop_size=20` to keep runtime under 5 seconds while still exercising the full code path.

**The Honesty Contract applies to test mocks too:** any test fixture that simulates an external data source (SDK response, EPW file, ÖKOBAUDAT JSON) must be documented in a `tests/FIXTURES.md` note explaining what it is and what real data it approximates. Do not let synthetic fixtures escape into production assertions about physical quantities.

---

## Coverage Priority

Given the 3-day hackathon timeline, focus coverage on correctness-critical paths in this order:

| Priority | Module | What to cover |
|----------|--------|---------------|
| P1 | `spatial_engine.py` | `is_valid_location` — all three cases (inside building, valid open space, outside boundary) |
| P1 | surrogate functions | `delta_tmrt_surrogate` — porosity-once regression (audit C10 bug class) |
| P1 | `infrared_client_v2.py` | Default mock mode, disclaimer present, live raises NotImplementedError |
| P2 | `rules_engine.py` | Score range [0,1], spacing penalty direction |
| P2 | `nature_metrics.py` | Standard return shape, missing-file graceful degradation |
| P3 | NSGA-II seed=42 | `n_gen=10` fast subset — Pareto non-empty, scaffold ≤ 500 |

**Skip for hackathon:** visual output tests (Pareto PNG), full EPW UTCI loop (too slow without fixtures), live SDK integration (no key in CI).
