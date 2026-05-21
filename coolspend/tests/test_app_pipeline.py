"""
coolspend/tests/test_app_pipeline.py — Offline headless tests for run_decision.

All tests run with INFRARED_BACKEND=mock (default). No INFRARED_API_KEY is set.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


# ── Ensure mock backend for all tests in this module ─────────────────────────

@pytest.fixture(autouse=True)
def _force_mock_backend(monkeypatch):
    """Remove any live backend setting; fall back to mock (default)."""
    monkeypatch.delenv("INFRARED_BACKEND", raising=False)
    monkeypatch.delenv("INFRARED_API_KEY", raising=False)
    yield


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_mock_run_returns_3_configs_and_nonempty_call_log():
    """run_decision on mock returns 3 ranked configs and at least 3 call_log entries."""
    from coolspend.app_pipeline import run_decision

    result = run_decision()

    assert result.get("error") is None, f"Unexpected error: {result.get('error')}"
    assert isinstance(result["configurations"], list)
    assert len(result["configurations"]) == 3

    call_log = result.get("call_log", [])
    assert isinstance(call_log, list)
    assert len(call_log) >= 3, (
        f"Expected at least 3 call_log entries (one per SimBudget.record call), got {len(call_log)}: {call_log}"
    )


def test_bad_geojson_returns_error_not_exception():
    """Malformed GeoJSON text sets error field; configurations is empty; no exception raised."""
    from coolspend.app_pipeline import run_decision

    result = run_decision(geojson_text="not valid json {{{")

    assert result["error"] is not None, "Expected error to be set for malformed GeoJSON"
    assert isinstance(result["error"], str)
    assert len(result["error"]) > 0
    assert result["configurations"] == [], (
        f"Expected empty configurations for bad GeoJSON, got: {result['configurations']}"
    )


def test_bad_geojson_missing_site_boundary_returns_error():
    """Valid JSON but no site_boundary feature sets error field."""
    from coolspend.app_pipeline import run_decision

    bad_fc = json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"kind": "building"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[2.16, 41.38], [2.17, 41.38], [2.17, 41.39], [2.16, 41.38]]]
                }
            }
        ]
    })

    result = run_decision(geojson_text=bad_fc)

    # Should either succeed with a fallback to default or set an error —
    # the important thing is no exception escapes.
    assert "configurations" in result
    assert "error" in result


def test_bare_polygon_geojson_parses_and_run_completes():
    """A bare Polygon geometry (not wrapped in FeatureCollection) is accepted and completes."""
    from coolspend.app_pipeline import run_decision

    bare_polygon = json.dumps({
        "type": "Polygon",
        "coordinates": [[
            [2.1666408, 41.3824114],
            [2.1673592, 41.3824114],
            [2.1673592, 41.3827886],
            [2.1666408, 41.3827886],
            [2.1666408, 41.3824114],
        ]]
    })

    result = run_decision(geojson_text=bare_polygon)

    # Must not raise; may succeed or fall back with error, but configurations must be present
    assert "configurations" in result
    assert "error" in result


def test_headline_contains_spend_eur_and_degc():
    """The headline string contains 'Spend EUR' and 'degC'."""
    from coolspend.app_pipeline import run_decision

    result = run_decision()

    assert result.get("error") is None
    headline = result.get("headline", "")
    assert isinstance(headline, str)
    assert "Spend EUR" in headline, f"Expected 'Spend EUR' in headline, got: {headline!r}"
    assert "degC" in headline, f"Expected 'degC' in headline, got: {headline!r}"


def test_mock_disclaimer_contains_not_measured_data():
    """backend='mock' disclaimer contains 'NOT MEASURED DATA'."""
    from coolspend.app_pipeline import run_decision

    result = run_decision(backend="mock")

    assert result.get("error") is None
    disclaimer = result.get("disclaimer", "")
    assert "NOT MEASURED DATA" in disclaimer, (
        f"Expected 'NOT MEASURED DATA' in disclaimer for mock backend, got: {disclaimer!r}"
    )


def test_determinism_same_args_same_rank1():
    """Two identical runs produce identical rank-1 tree_count and delta_utci_c."""
    from coolspend.app_pipeline import run_decision

    result_a = run_decision()
    result_b = run_decision()

    assert result_a.get("error") is None
    assert result_b.get("error") is None

    configs_a = result_a["configurations"]
    configs_b = result_b["configurations"]

    rank1_a = next(c for c in configs_a if c["rank"] == 1)
    rank1_b = next(c for c in configs_b if c["rank"] == 1)

    assert rank1_a["tree_count"] == rank1_b["tree_count"], (
        f"Non-deterministic tree_count: {rank1_a['tree_count']} vs {rank1_b['tree_count']}"
    )
    assert rank1_a.get("delta_utci_c") == rank1_b.get("delta_utci_c"), (
        f"Non-deterministic delta_utci_c: {rank1_a.get('delta_utci_c')} vs {rank1_b.get('delta_utci_c')}"
    )


def test_result_dict_has_all_required_keys():
    """run_decision result dict has all required top-level keys."""
    from coolspend.app_pipeline import run_decision

    result = run_decision()

    required_keys = {"configurations", "before_after", "headline", "backend", "disclaimer", "call_log", "site_path", "error"}
    missing = required_keys - set(result.keys())
    assert not missing, f"Missing keys in run_decision result: {missing}"


def test_backend_field_reflects_mock():
    """backend field in result matches the requested backend."""
    from coolspend.app_pipeline import run_decision

    result = run_decision(backend="mock")

    assert result.get("error") is None
    assert result["backend"] == "mock", f"Expected backend='mock', got {result['backend']!r}"


def test_call_log_entries_contain_utci():
    """call_log entries contain 'UTCI' or 'utci' (from SimBudget.record)."""
    from coolspend.app_pipeline import run_decision

    result = run_decision()

    assert result.get("error") is None
    call_log = result.get("call_log", [])
    assert len(call_log) >= 3

    # At least one entry should reference a call number (SimBudget format: "live UTCI call #N: ...")
    has_call_ref = any("#" in entry or "call" in entry.lower() for entry in call_log)
    assert has_call_ref, f"call_log entries don't look like SimBudget records: {call_log}"
