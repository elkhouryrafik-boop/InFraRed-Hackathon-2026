"""
coolspend/tests/test_app_viz.py — Headless offline tests for render_before_after.

Uses matplotlib Agg backend (forced by app_viz import). No display required.
All tests run without browser or API key.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def minimal_config():
    """A minimal valid tree config with one active tree."""
    return {
        "trees": [
            {"x_m": 30.0, "y_m": 10.0, "species": "tilia", "active": True},
        ],
        "tree_count": 1,
        "validated_backend": "mock",
        "validated_disclaimer": "NOT MEASURED DATA — synthetic mock value for UI integration only.",
        "rank": 1,
        "label": "MAX_THERMAL_RELIEF",
    }


@pytest.fixture
def minimal_before_after():
    """A minimal before_after dict matching the run_decision contract."""
    return {
        "baseline_utci_c": 41.0,
        "chosen_validated_utci_c": 39.59,
        "headline_delta_utci_c": 1.41,
        "chosen_label": "MAX_THERMAL_RELIEF",
        "source": "NOT MEASURED DATA — synthetic mock value for UI integration only.",
        "note": "before = baseline UTCI; after = rank-1 intervention validated UTCI",
    }


@pytest.fixture
def empty_trees_config(minimal_config):
    """Config with no active trees — tests robustness to empty tree list."""
    cfg = dict(minimal_config)
    cfg["trees"] = []
    cfg["tree_count"] = 0
    return cfg


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_render_returns_existing_png_path(tmp_path, minimal_config, minimal_before_after):
    """render_before_after returns a path to an existing non-empty PNG file."""
    from coolspend.app_viz import render_before_after

    out_path = tmp_path / "test_output.png"
    result_path = render_before_after(minimal_config, minimal_before_after, out_path=str(out_path))

    assert result_path is not None
    assert isinstance(result_path, str)
    p = Path(result_path)
    assert p.exists(), f"Output PNG not found at {result_path}"
    assert p.stat().st_size > 0, f"Output PNG is empty at {result_path}"


def test_render_with_empty_trees_no_crash(tmp_path, empty_trees_config, minimal_before_after):
    """render_before_after with zero active trees does not crash and writes a PNG."""
    from coolspend.app_viz import render_before_after

    out_path = tmp_path / "empty_trees.png"
    result_path = render_before_after(empty_trees_config, minimal_before_after, out_path=str(out_path))

    assert result_path is not None
    p = Path(result_path)
    assert p.exists(), f"Output PNG not found at {result_path}"
    assert p.stat().st_size > 0


def test_render_tempfile_when_no_out_path(minimal_config, minimal_before_after):
    """When out_path is None, render_before_after writes to a tempfile and returns its path."""
    from coolspend.app_viz import render_before_after

    result_path = render_before_after(minimal_config, minimal_before_after, out_path=None)

    assert result_path is not None
    p = Path(result_path)
    assert p.exists(), f"Tempfile PNG not found at {result_path}"
    assert p.stat().st_size > 0


def test_render_invalid_site_path_falls_back(tmp_path, minimal_config, minimal_before_after):
    """When site_path is invalid, render_before_after falls back to the default fixture."""
    from coolspend.app_viz import render_before_after

    out_path = tmp_path / "fallback_test.png"
    result_path = render_before_after(
        minimal_config,
        minimal_before_after,
        site_path="/nonexistent/path/to/site.geojson",
        out_path=str(out_path),
    )

    assert result_path is not None
    p = Path(result_path)
    assert p.exists()
    assert p.stat().st_size > 0


def test_render_is_png_format(tmp_path, minimal_config, minimal_before_after):
    """The output file starts with the PNG magic bytes."""
    from coolspend.app_viz import render_before_after

    out_path = tmp_path / "format_test.png"
    result_path = render_before_after(minimal_config, minimal_before_after, out_path=str(out_path))

    with open(result_path, "rb") as f:
        header = f.read(8)

    PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
    assert header == PNG_MAGIC, f"File is not a valid PNG (header: {header!r})"


def test_render_multiple_trees(tmp_path, minimal_before_after):
    """render_before_after with multiple active trees (full 12-slot config) works correctly."""
    from coolspend.app_viz import render_before_after

    config = {
        "trees": [
            {"x_m": 10.0 + i * 5.0, "y_m": 15.0, "species": "tilia", "active": (i % 3 != 0)}
            for i in range(12)
        ],
        "tree_count": 8,
        "validated_backend": "mock",
        "validated_disclaimer": "NOT MEASURED DATA — test fixture",
        "rank": 1,
        "label": "BALANCED",
    }

    out_path = tmp_path / "multi_trees.png"
    result_path = render_before_after(config, minimal_before_after, out_path=str(out_path))

    p = Path(result_path)
    assert p.exists()
    assert p.stat().st_size > 0
