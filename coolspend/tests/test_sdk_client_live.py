"""
Offline tests for the live backend path in coolspend/sdk_client.py.

All tests run WITHOUT a real INFRARED_API_KEY and WITHOUT a network connection.
The infrared_sdk package is monkeypatched into sys.modules as a fake so the live
code path can be exercised offline (confirming the real call pattern is wired correctly).

Tests:
  - test_import_does_not_require_sdk       : module importable even without infrared_sdk
  - test_live_without_key_raises           : EnvironmentError when key absent
  - test_live_calls_sdk_and_caches         : fake SDK path returns UTCIResult and writes cache
  - test_cached_replays_live_result        : cached backend reads the file live wrote
  - test_key_never_logged                  : dummy key string absent from all log records
"""
from __future__ import annotations

import importlib
import json
import logging
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

FAKE_GRID = np.array([[35.0, 36.0], [37.0, 38.0]], dtype=float)
FAKE_GRID_MEAN = float(np.mean(FAKE_GRID))  # 36.5

LIVE_GEOMETRY = {
    "polygon_lonlat": [
        [2.1660, 41.3820],
        [2.1680, 41.3820],
        [2.1680, 41.3835],
        [2.1660, 41.3835],
        [2.1660, 41.3820],
    ]
}

DUMMY_KEY = "TEST-KEY-OFFLINE-0000"


def _make_fake_infrared_sdk() -> types.ModuleType:
    """Build a fake infrared_sdk module tree matching the live UTCI call wiring.

    Mirrors the real call surface _live_utci uses: weather lookup + filter,
    buildings/ground_materials fetch, UtciModelRequest.from_weatherfile_payload,
    TimePeriod/Location models, and run_area_and_wait returning a merged_grid.
    """
    # Root package
    fake_sdk = types.ModuleType("infrared_sdk")

    # Fake AnalysesName enum-like object (real member: thermal_comfort_index)
    fake_analyses_name = MagicMock()
    fake_analyses_name.thermal_comfort_index = "thermal-comfort-index"

    # Fake result with merged_grid
    fake_result = MagicMock()
    fake_result.merged_grid = FAKE_GRID

    # Fake area with buildings
    fake_area = MagicMock()
    fake_area.buildings = []

    # Fake ground-materials area with .layers
    fake_gm = MagicMock()
    fake_gm.layers = {}

    # Fake client (context manager)
    fake_client_instance = MagicMock()
    fake_client_instance.buildings.get_area.return_value = fake_area
    fake_client_instance.ground_materials.get_area.return_value = fake_gm
    fake_client_instance.weather.get_weather_file_from_location.return_value = [
        {"uuid": "fake-weather-uuid"}
    ]
    fake_client_instance.weather.filter_weather_data.return_value = []
    fake_client_instance.run_area_and_wait.return_value = fake_result
    # Support context manager protocol
    fake_client_instance.__enter__ = MagicMock(return_value=fake_client_instance)
    fake_client_instance.__exit__ = MagicMock(return_value=False)

    fake_infrared_client_cls = MagicMock(return_value=fake_client_instance)
    fake_sdk.InfraredClient = fake_infrared_client_cls

    # infrared_sdk.analyses.types sub-module
    fake_analyses_mod = types.ModuleType("infrared_sdk.analyses")
    fake_analyses_types_mod = types.ModuleType("infrared_sdk.analyses.types")
    fake_analyses_types_mod.AnalysesName = fake_analyses_name
    fake_analyses_types_mod.UtciModelRequest = MagicMock()
    fake_analyses_types_mod.UtciModelRequest.from_weatherfile_payload.return_value = "fake-payload"
    fake_analyses_types_mod.UtciModelBaseRequest = MagicMock()
    fake_sdk.analyses = fake_analyses_mod
    fake_analyses_mod.types = fake_analyses_types_mod

    # infrared_sdk.models sub-module (TimePeriod, Location)
    fake_models_mod = types.ModuleType("infrared_sdk.models")
    fake_models_mod.TimePeriod = MagicMock()
    fake_models_mod.Location = MagicMock()
    fake_sdk.models = fake_models_mod

    return fake_sdk, fake_client_instance


def _install_fake_sdk(fake_sdk) -> None:
    """Register the fake SDK module tree into sys.modules (incl. .models)."""
    sys.modules["infrared_sdk"] = fake_sdk
    sys.modules["infrared_sdk.analyses"] = fake_sdk.analyses
    sys.modules["infrared_sdk.analyses.types"] = fake_sdk.analyses.types
    sys.modules["infrared_sdk.models"] = fake_sdk.models


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_sdk_modules():
    """Remove fake infrared_sdk from sys.modules before and after each test."""
    for key in list(sys.modules):
        if key.startswith("infrared_sdk"):
            del sys.modules[key]
    yield
    for key in list(sys.modules):
        if key.startswith("infrared_sdk"):
            del sys.modules[key]


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_import_does_not_require_sdk() -> None:
    """Importing coolspend.sdk_client succeeds even when infrared_sdk is absent.

    This verifies the lazy-import design: the SDK is imported only inside
    _live_utci(), not at module load time, so the offline mock/cached paths
    are always available without installing infrared-sdk.
    """
    # Ensure infrared_sdk is NOT in sys.modules
    for key in list(sys.modules):
        if key.startswith("infrared_sdk"):
            del sys.modules[key]

    # Temporarily hide infrared_sdk by injecting a broken finder
    original_meta_path = sys.meta_path[:]

    class _BlockInfraredSDK:
        def find_module(self, name, path=None):
            if name.startswith("infrared_sdk"):
                raise ImportError(f"blocked: {name}")
            return None

    sys.meta_path.insert(0, _BlockInfraredSDK())
    try:
        # Remove from sys.modules to force re-import attempt
        for key in list(sys.modules):
            if "coolspend" in key:
                del sys.modules[key]
        import coolspend.sdk_client  # noqa: F401 — should not raise
    finally:
        sys.meta_path[:] = original_meta_path

    assert True, "Import succeeded without infrared_sdk installed"


def test_live_without_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """INFRARED_BACKEND=live without INFRARED_API_KEY raises EnvironmentError."""
    monkeypatch.setenv("INFRARED_BACKEND", "live")
    monkeypatch.delenv("INFRARED_API_KEY", raising=False)

    # Reload so env is picked up fresh (belt-and-suspenders; _backend() reads env at dispatch)
    from coolspend.sdk_client import get_baseline_utci

    with pytest.raises(EnvironmentError, match="INFRARED_API_KEY"):
        get_baseline_utci(LIVE_GEOMETRY)


def test_live_calls_sdk_and_caches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Live path calls InfraredClient, reduces merged_grid to scalar, writes cache.

    The fake infrared_sdk is injected into sys.modules so no real key or network
    call is needed.
    """
    monkeypatch.setenv("INFRARED_BACKEND", "live")
    monkeypatch.setenv("INFRARED_API_KEY", DUMMY_KEY)

    # Patch CACHE_DIR to tmp_path so we can inspect the written file
    import coolspend.sdk_client as sdk
    monkeypatch.setattr(sdk, "CACHE_DIR", tmp_path)

    # Inject fake infrared_sdk
    fake_sdk, fake_client = _make_fake_infrared_sdk()
    _install_fake_sdk(fake_sdk)

    result = sdk.get_baseline_utci(LIVE_GEOMETRY)

    # Verify UTCIResult fields
    assert result.backend == "live"
    assert result.utci_c == round(FAKE_GRID_MEAN, 2)
    assert result.metric == "utci_at_1.1m"
    assert "LIVE Infrared SDK result" in result.disclaimer
    assert "run_area_and_wait" in result.source

    # Verify cache file was written
    cache_files = list(tmp_path.glob("utci_baseline_*.json"))
    assert len(cache_files) == 1, f"Expected 1 cache file, found {cache_files}"

    cached_raw = json.loads(cache_files[0].read_text(encoding="utf-8"))
    assert cached_raw["utci_c"] == round(FAKE_GRID_MEAN, 2)
    assert cached_raw["backend"] == "live"


def test_cached_replays_live_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """After a live call, INFRARED_BACKEND=cached replays the same scalar offline."""
    import coolspend.sdk_client as sdk

    # First: do a live call to write the cache
    monkeypatch.setenv("INFRARED_BACKEND", "live")
    monkeypatch.setenv("INFRARED_API_KEY", DUMMY_KEY)
    monkeypatch.setattr(sdk, "CACHE_DIR", tmp_path)

    fake_sdk, _ = _make_fake_infrared_sdk()
    _install_fake_sdk(fake_sdk)

    live_result = sdk.get_baseline_utci(LIVE_GEOMETRY)

    # Clear fake SDK from sys.modules — cached path must not need it
    for key in list(sys.modules):
        if key.startswith("infrared_sdk"):
            del sys.modules[key]

    # Second: switch to cached backend and replay
    monkeypatch.setenv("INFRARED_BACKEND", "cached")
    monkeypatch.delenv("INFRARED_API_KEY", raising=False)

    cached_result = sdk.get_baseline_utci(LIVE_GEOMETRY)

    assert cached_result.utci_c == live_result.utci_c
    # wave-2 Fix 2: cache READ must relabel backend as 'cached:<origin>' so the
    # provenance is unambiguous (previously reported 'live', un-auditable — H-2).
    assert cached_result.backend == "cached:live", (
        f"Expected backend='cached:live' on cache read, got '{cached_result.backend}'. "
        "Cached results must be labelled to distinguish them from fresh live calls."
    )
    # Replay note must be present in disclaimer and source
    assert "replayed from cache" in cached_result.disclaimer, (
        f"'replayed from cache' missing from disclaimer: {cached_result.disclaimer!r}"
    )
    assert "cached replay" in cached_result.source, (
        f"'cached replay' missing from source: {cached_result.source!r}"
    )


def test_key_never_logged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The dummy API key must not appear in any log record during a live call."""
    monkeypatch.setenv("INFRARED_BACKEND", "live")
    monkeypatch.setenv("INFRARED_API_KEY", DUMMY_KEY)

    import coolspend.sdk_client as sdk
    monkeypatch.setattr(sdk, "CACHE_DIR", tmp_path)

    fake_sdk, _ = _make_fake_infrared_sdk()
    _install_fake_sdk(fake_sdk)

    with caplog.at_level(logging.DEBUG, logger="coolspend.sdk_client"):
        sdk.get_baseline_utci(LIVE_GEOMETRY)

    for record in caplog.records:
        assert DUMMY_KEY not in record.getMessage(), (
            f"API key found in log record: {record.getMessage()}"
        )
