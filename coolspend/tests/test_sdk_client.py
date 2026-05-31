"""
Offline tests for coolspend/sdk_client.py — backend dispatch and SimBudget guard.

Tests cover:
  - mock backend runs offline (no API key)
  - intervention cools relative to baseline
  - cached miss raises FileNotFoundError (no fallthrough to mock)
  - live backend without API key raises EnvironmentError
  - SimBudget caps live calls and logs each call
  - _geometry_hash is stable across key-order variations
"""
from __future__ import annotations

import pytest
from uuid import uuid4

from coolspend.sdk_client import (
    get_baseline_utci,
    get_intervention_utci,
    SimBudget,
    UTCIResult,
    _geometry_hash,
)


# ── Test fixtures ─────────────────────────────────────────────────────────────

CANOPY_GEOMETRY = {"width_m": 30.0, "coverage_fraction": 0.35}


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_mock_backend_runs_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock backend returns finite UTCI and disclaimer without any API key."""
    monkeypatch.delenv("INFRARED_BACKEND", raising=False)
    monkeypatch.delenv("INFRARED_API_KEY", raising=False)

    result = get_baseline_utci(CANOPY_GEOMETRY)

    assert isinstance(result, UTCIResult)
    assert isinstance(result.utci_c, float)
    assert result.utci_c > 0
    assert "NOT MEASURED DATA" in result.disclaimer


def test_intervention_cools(monkeypatch: pytest.MonkeyPatch) -> None:
    """Intervention UTCI is lower than baseline for a canopy geometry."""
    monkeypatch.delenv("INFRARED_BACKEND", raising=False)
    monkeypatch.delenv("INFRARED_API_KEY", raising=False)

    baseline = get_baseline_utci(CANOPY_GEOMETRY)
    intervention = get_intervention_utci(CANOPY_GEOMETRY)

    assert intervention.utci_c < baseline.utci_c


def test_cached_miss_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """INFRARED_BACKEND=cached with a guaranteed-miss geometry raises FileNotFoundError."""
    monkeypatch.setenv("INFRARED_BACKEND", "cached")
    monkeypatch.delenv("INFRARED_API_KEY", raising=False)

    # Use a geometry with a unique field to guarantee cache miss
    unique_geometry = {
        "width_m": 30.0,
        "coverage_fraction": 0.35,
        "_unique": uuid4().hex,
    }

    with pytest.raises(FileNotFoundError):
        get_baseline_utci(unique_geometry)


def test_live_without_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """INFRARED_BACKEND=live without INFRARED_API_KEY raises EnvironmentError."""
    monkeypatch.setenv("INFRARED_BACKEND", "live")
    monkeypatch.delenv("INFRARED_API_KEY", raising=False)

    with pytest.raises(EnvironmentError):
        get_baseline_utci(CANOPY_GEOMETRY)


def test_simbudget_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    """SimBudget(2) allows 2 record() calls; 3rd raises RuntimeError; log has 2 entries."""
    budget = SimBudget(max_live_calls=2)

    budget.record("call-1")
    budget.record("call-2")

    assert len(budget.log) == 2

    with pytest.raises(RuntimeError):
        budget.record("call-3-exceeds-cap")


def test_geometry_hash_stable() -> None:
    """Same dict in different key order yields identical _geometry_hash."""
    geom_a = {"width_m": 30.0, "coverage_fraction": 0.35, "site_id": "BCN-001"}
    geom_b = {"site_id": "BCN-001", "coverage_fraction": 0.35, "width_m": 30.0}

    assert _geometry_hash(geom_a) == _geometry_hash(geom_b)
    assert len(_geometry_hash(geom_a)) == 16


# ── Cached provenance tests (wave-2 Fix 2 — H-2) ─────────────────────────────


def test_cached_result_backend_label_is_cached(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """A cache-READ result must report backend='cached:<origin>', not the origin alone.

    Before Fix 2, a cached mock result reported backend='mock', making it
    indistinguishable from a live mock call (un-auditable, H-2).
    After Fix 2, the backend field is 'cached:mock' and the disclaimer retains
    'NOT MEASURED DATA' while adding a 'replayed from cache' note.
    """
    import json
    from coolspend.sdk_client import CACHE_DIR, _geometry_hash, UTCIResult

    geom = {"width_m": 10.0, "coverage_fraction": 0.1, "_test_fix2": "h2_label"}
    ghash = _geometry_hash(geom)
    cache_file = CACHE_DIR / f"utci_baseline_{ghash}.json"

    # Plant a mock-origin cache entry (simulates a previously written mock result)
    mock_entry = UTCIResult(
        utci_c=41.0,
        metric="utci_at_1.1m",
        backend="mock",
        geometry_hash=ghash,
        disclaimer="NOT MEASURED DATA — synthetic field for UI integration only.",
        source="coolspend mock scalar UTCI (CONCERNS.md 1.3 base values)",
    )
    cache_file.write_text(json.dumps(mock_entry.to_dict(), indent=2), encoding="utf-8")

    try:
        monkeypatch.setenv("INFRARED_BACKEND", "cached")
        monkeypatch.delenv("INFRARED_API_KEY", raising=False)

        from coolspend.sdk_client import get_baseline_utci
        result = get_baseline_utci(geom)

        # backend must be relabelled (not just 'mock')
        assert result.backend.startswith("cached:"), (
            f"Expected backend to start with 'cached:', got '{result.backend}'. "
            "Cached results must be labelled to distinguish them from fresh calls."
        )
        assert "mock" in result.backend, (
            f"Expected 'mock' in backend label to preserve origin, got '{result.backend}'"
        )

        # NOT MEASURED DATA must be preserved for originally-mock cached results
        assert "NOT MEASURED DATA" in result.disclaimer, (
            f"'NOT MEASURED DATA' must be retained for a cached mock result. "
            f"Got: '{result.disclaimer}'"
        )

        # replay note must appear in disclaimer
        assert "replayed from cache" in result.disclaimer, (
            f"'replayed from cache' note missing from disclaimer: '{result.disclaimer}'"
        )

        # source must note the origin
        assert "cached replay" in result.source, (
            f"source field missing 'cached replay' note: '{result.source}'"
        )
    finally:
        cache_file.unlink(missing_ok=True)


def test_cached_live_result_no_not_measured_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cached LIVE result must NOT say 'NOT MEASURED DATA' in its disclaimer.

    After Fix 2, the relabelling logic checks the original disclaimer so that a
    live-origin cached result does not inherit the mock honesty text.
    """
    import json
    from coolspend.sdk_client import CACHE_DIR, _geometry_hash, UTCIResult

    geom = {"width_m": 20.0, "coverage_fraction": 0.2, "_test_fix2": "h2_live"}
    ghash = _geometry_hash(geom)
    cache_file = CACHE_DIR / f"utci_baseline_{ghash}.json"

    live_entry = UTCIResult(
        utci_c=38.5,
        metric="utci_at_1.1m",
        backend="live",
        geometry_hash=ghash,
        disclaimer="LIVE Infrared SDK result",
        source="infrared.city SDK run_area_and_wait (UTCI)",
    )
    cache_file.write_text(json.dumps(live_entry.to_dict(), indent=2), encoding="utf-8")

    try:
        monkeypatch.setenv("INFRARED_BACKEND", "cached")
        monkeypatch.delenv("INFRARED_API_KEY", raising=False)

        from coolspend.sdk_client import get_baseline_utci
        result = get_baseline_utci(geom)

        assert result.backend == "cached:live", (
            f"Expected 'cached:live', got '{result.backend}'"
        )
        assert "NOT MEASURED DATA" not in result.disclaimer, (
            "A cached LIVE result must NOT carry 'NOT MEASURED DATA'; it is real data."
        )
        assert "replayed from cache" in result.disclaimer
    finally:
        cache_file.unlink(missing_ok=True)


# ── Cooled-footprint grid reducers (pure analysis of measured UTCI grids) ──────

def _two_grids():
    """3×3 baseline/intervention pair with a known drop pattern + one NaN cell.

    drop = baseline − intervention per cell:
      row0: 0.0, 0.6, 1.2
      row1: 2.5, 0.4, NaN  (NaN = outside polygon)
      row2: 0.5, 3.0, 0.0
    """
    import numpy as np
    baseline = np.array([
        [30.0, 30.6, 31.2],
        [32.5, 30.4, 30.0],
        [30.5, 33.0, 30.0],
    ])
    intervention = np.array([
        [30.0, 30.0, 30.0],
        [30.0, 30.0, np.nan],
        [30.0, 30.0, 30.0],
    ])
    return baseline.tolist(), intervention.tolist()


def test_cooled_footprint_m2_counts_cells_at_threshold():
    from coolspend.sdk_client import cooled_footprint_m2
    b, i = _two_grids()
    # drops >= 0.5: 0.6, 1.2, 2.5, 0.5, 3.0 → 5 cells (0.4 excluded, NaN excluded)
    assert cooled_footprint_m2(b, i, min_drop_c=0.5) == 5.0
    assert cooled_footprint_m2(None, i) is None


def test_cooled_footprint_profile_bands_and_relief():
    from coolspend.sdk_client import cooled_footprint_profile
    b, i = _two_grids()
    prof = cooled_footprint_profile(b, i)
    assert prof is not None
    # bands are monotonically non-increasing as the threshold rises
    band = prof["cooled_m2_by_band"]
    assert band["0.5"] == 5      # 0.6,1.2,2.5,0.5,3.0
    assert band["1"] == 3        # 1.2,2.5,3.0
    assert band["2"] == 2        # 2.5,3.0
    assert band["0.5"] >= band["1"] >= band["2"]
    # 8 valid (non-NaN) cells; 5 cooled ≥0.5
    assert prof["valid_cells_m2"] == 8.0
    assert prof["cooled_fraction"] == round(5 / 8, 4)
    assert prof["peak_drop_c"] == 3.0
    # Measured dispersion over the cooled zone (drops 0.5,0.6,1.2,2.5,3.0).
    assert prof["mean_drop_c"] == pytest.approx(1.56, abs=1e-3)
    assert prof["std_drop_c"] > 0.0
    assert prof["p10_drop_c"] < prof["mean_drop_c"] < prof["p90_drop_c"]
    # heat stress (>=26 °C threshold) — all baseline cells are >=30, all
    # interventions <26? no: interventions are 30, still >=26 → 0 relieved here.
    assert prof["heat_stress_relieved_m2"] == 0.0


def test_cooled_footprint_profile_contiguity():
    pytest.importorskip("scipy")
    from coolspend.sdk_client import cooled_footprint_profile
    # Two separate cooled patches: a 2-cell run and a single isolated cell.
    b = [[31.0, 31.0, 30.0, 31.0],
         [30.0, 30.0, 30.0, 30.0]]
    i = [[30.0, 30.0, 30.0, 30.0],
         [30.0, 30.0, 30.0, 30.0]]
    # drops: row0 = [1,1,0,1] → cells (0,0),(0,1) adjacent = patch of 2; (0,3) = patch of 1
    prof = cooled_footprint_profile(b, i)
    assert prof["n_cooled_patches"] == 2
    assert prof["largest_cooled_patch_m2"] == 2.0


def test_cooled_footprint_profile_heat_stress_relief():
    from coolspend.sdk_client import cooled_footprint_profile
    # baseline above 26 °C threshold, intervention below it → relieved
    b = [[27.0, 27.0], [25.0, 27.0]]
    i = [[25.0, 26.0], [24.0, 25.0]]
    prof = cooled_footprint_profile(b, i, heat_stress_c=26.0)
    # cell(0,0): 27→25 crosses below 26 (relieved). cell(0,1): 27→26 NOT below.
    # cell(1,0): baseline 25 < 26, not stressed. cell(1,1): 27→25 relieved.
    assert prof["heat_stress_relieved_m2"] == 2.0


def test_cooled_footprint_profile_none_on_missing_grid():
    from coolspend.sdk_client import cooled_footprint_profile
    assert cooled_footprint_profile(None, [[1.0]]) is None
    assert cooled_footprint_profile([[1.0]], [[1.0, 2.0]]) is None  # shape mismatch
