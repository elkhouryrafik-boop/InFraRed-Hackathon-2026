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
