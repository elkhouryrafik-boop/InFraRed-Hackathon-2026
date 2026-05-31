"""Offline tests for coolspend/citywide.py (no network needed for load/rank/scan)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from coolspend import citywide

# Build a minimal 3-cell GeoJSON in the same shape as the real scored_grid.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_TEST_GRID = _REPO_ROOT / "L1_INGEST_data" / "data_for_all" / "scored_grid.geojson"


def _fake_cells() -> list[dict]:
    """Minimal hand-built cell list matching the shape from load_scored_grid."""
    return [
        {
            "properties": {
                "cell_id": "C001_TEST",
                "district": "EIXAMPLE",
                "barri": "LA DRETA",
                "composite_score_B": 0.85,
                "mean_sealed": 0.9,
                "mean_lst_celsius": 38.0,
                "lst_anomaly": 5.0,
            },
            "geometry_utm": [(424000, 4586400), (424200, 4586400), (424200, 4586600), (424000, 4586600)],
            "centroid_lonlat": (2.17, 41.39),
            "centroid_utm": (424100, 4586500),
            "bbox_utm": (424000, 4586400, 424200, 4586600),
            "cell_area_m2": 40000.0,
        },
        {
            "properties": {
                "cell_id": "C002_TEST",
                "district": "SANTS",
                "barri": "BADAL",
                "composite_score_B": 0.72,
                "mean_sealed": 0.85,
                "mean_lst_celsius": 36.0,
                "lst_anomaly": 3.0,
            },
            "geometry_utm": [(425000, 4585000), (425200, 4585000), (425200, 4585200), (425000, 4585200)],
            "centroid_lonlat": (2.18, 41.38),
            "centroid_utm": (425100, 4585100),
            "bbox_utm": (425000, 4585000, 425200, 4585200),
            "cell_area_m2": 40000.0,
        },
        {
            "properties": {
                "cell_id": "C003_TEST",
                "district": "GRÀCIA",
                "barri": "VILA DE GRÀCIA",
                "composite_score_B": 0.55,
                "mean_sealed": 0.70,
                "mean_lst_celsius": 34.0,
                "lst_anomaly": 1.5,
            },
            "geometry_utm": [(426000, 4587000), (426200, 4587000), (426200, 4587200), (426000, 4587200)],
            "centroid_lonlat": (2.19, 41.40),
            "centroid_utm": (426100, 4587100),
            "bbox_utm": (426000, 4587000, 426200, 4587200),
            "cell_area_m2": 40000.0,
        },
    ]


# ── Tests ────────────────────────────────────────────────────────────────────

def test_load_scored_grid_real_file():
    """Real file exists, has 494 cells, and parses to expected shape."""
    cells = citywide.load_scored_grid()
    assert len(cells) == 494
    c0 = cells[0]
    assert "properties" in c0
    assert "centroid_lonlat" in c0
    assert "cell_area_m2" in c0
    assert c0["properties"]["cell_id"]
    assert isinstance(c0["centroid_lonlat"], tuple)
    assert len(c0["centroid_lonlat"]) == 2
    # All centroids should be valid lon/lat within Barcelona
    for c in cells:
        lon, lat = c["centroid_lonlat"]
        assert 2.0 < lon < 2.3, f"lon {lon} outside Barcelona"
        assert 41.3 < lat < 41.5, f"lat {lat} outside Barcelona"


def test_load_centroid_is_true_centre_not_ring_biased(tmp_path):
    """A closed ring repeats its first vertex last; the centroid must average the
    distinct corners only, not double-count the duplicate (which would offset the
    centre toward that corner). Regression for the ~57 m citywide offset bug."""
    # Axis-aligned 400 m square in UTM-31N; true centre = (424200, 4586200).
    ring = [
        [424000.0, 4586000.0],
        [424400.0, 4586000.0],
        [424400.0, 4586400.0],
        [424000.0, 4586400.0],
        [424000.0, 4586000.0],  # closing duplicate of the first vertex
    ]
    grid = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"cell_id": "C_CENTRE", "composite_score_B": 0.5},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        }],
    }
    p = tmp_path / "grid.geojson"
    p.write_text(json.dumps(grid), encoding="utf-8")

    cell = citywide.load_scored_grid(p)[0]
    cx, cy = cell["centroid_utm"]
    assert cx == pytest.approx(424200.0, abs=1e-6)
    assert cy == pytest.approx(4586200.0, abs=1e-6)


def test_rank_cells_by_score():
    cells = _fake_cells()
    ranked = citywide.rank_cells(cells, "composite_score_B")
    assert ranked[0]["properties"]["cell_id"] == "C001_TEST"
    assert ranked[1]["properties"]["cell_id"] == "C002_TEST"
    assert ranked[2]["properties"]["cell_id"] == "C003_TEST"

    # Descending by default — reverse it
    asc = citywide.rank_cells(cells, "composite_score_B", descending=False)
    assert asc[0]["properties"]["cell_id"] == "C003_TEST"


def test_cell_eval_polygon():
    cell = _fake_cells()[0]
    ring = citywide.cell_eval_polygon(cell, size_m=200.0)
    # Closed ring
    assert ring[0] == ring[-1]
    assert len(ring) == 5  # 4 corners + close
    # All coords are (lon, lat) pairs
    for pt in ring:
        assert len(pt) == 2
        assert -180 < pt[0] < 180
        assert -90 < pt[1] < 90


def test_scan_cells_with_fake():
    cells = _fake_cells()
    result = citywide.scan_cells(cells, top_n=3, budget_eur=500_000)
    assert result["mode"] == "scan"
    assert result["total_cells"] == 3
    assert len(result["cells"]) == 3
    # First cell should be highest composite_score_B
    assert result["cells"][0]["cell_id"] == "C001_TEST"
    assert result["cells"][0]["composite_score_B"] == 0.85
    # Estimated trees should be positive
    assert result["cells"][0]["est_trees"] > 0
    assert result["cells"][0]["est_cost_eur"] > 0
    # Cooling proxy: LST anomaly × sealed
    assert result["cells"][0]["cooling_proxy"] == pytest.approx(5.0 * 0.9, abs=0.01)


def test_scan_cells_with_real_file():
    """Scan the real 494 cells — must complete in < 1 s and return ranked results."""
    cells = citywide.load_scored_grid()
    result = citywide.scan_cells(cells, top_n=10, budget_eur=1_000_000)
    assert result["mode"] == "scan"
    assert len(result["cells"]) == 10
    # Top cell should have highest composite
    top = result["cells"][0]
    assert top["composite_score_B"] > 0.7  # top cells are hot×sealed
    # Every cell should have eval_polygon
    for c in result["cells"]:
        ring = c["eval_polygon"]
        assert ring[0] == ring[-1]
        assert len(ring) == 5


def test_scan_respects_budget():
    """With a very small budget, only a few cells should be allocated."""
    cells = _fake_cells()
    result = citywide.scan_cells(cells, top_n=3, budget_eur=10_000)
    allocated = sum(1 for c in result["cells"] if c["allocated_eur"] > 0)
    assert allocated < 3  # very small budget


def test_cell_eval_polygon_area():
    """The eval polygon should fit under the 62,500 m² cap."""
    cell = _fake_cells()[0]
    ring = citywide.cell_eval_polygon(cell, size_m=200.0)
    # Shoelace in approximate UTM-equivalent
    from coolspend.api_server import _polygon_area_m2
    area = _polygon_area_m2(ring)
    assert area < 62_500
    # Should be roughly 40,000 m² (200 × 200)
    assert 35_000 < area < 45_000


def test_utm_to_lonlat_roundtrip():
    """Barcelona UTM coords should map to plausible lon/lat."""
    # Approximate centre of Barcelona
    lon, lat = citywide._utm_to_lonlat(430000, 4584000)
    assert 2.1 < lon < 2.2
    assert 41.35 < lat < 41.45
