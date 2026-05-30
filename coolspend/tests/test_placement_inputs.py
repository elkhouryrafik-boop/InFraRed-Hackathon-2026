"""Offline tests for the PURE parts of coolspend/placement_inputs.py."""
from __future__ import annotations

import math

from coolspend.placement_inputs import grid_cell_lonlat, build_demand_cells, COMFORT_UTCI_C

BOUNDS = {"west": 2.0, "south": 41.0, "east": 2.01, "north": 41.01}


def test_grid_cell_lonlat_row0_is_north():
    # Row 0 should be the NORTH band (high latitude), last row the south.
    _, lat_top = grid_cell_lonlat(0, 0, 10, 10, BOUNDS)
    _, lat_bot = grid_cell_lonlat(9, 0, 10, 10, BOUNDS)
    assert lat_top > lat_bot
    # Column increases eastward.
    lon_w, _ = grid_cell_lonlat(0, 0, 10, 10, BOUNDS)
    lon_e, _ = grid_cell_lonlat(0, 9, 10, 10, BOUNDS)
    assert lon_e > lon_w


def test_demand_only_hot_impervious_unshaded():
    # 2x2 grid: top-left hot, others not / filtered out.
    grid = [
        [30.0, 20.0],   # 30 hot, 20 cold
        [28.0, 35.0],   # 28 hot (but we'll mark shaded), 35 hot (but permeable)
    ]
    # impervious everywhere except the 35 cell (bottom-right)
    def is_impervious(lon, lat):
        return not (lat < 41.005 and lon > 2.005)  # exclude bottom-right
    # shaded only the bottom-left (28) cell
    def is_shaded(lon, lat):
        return lat < 41.005 and lon < 2.005
    def to_local(lon, lat):
        return ((lon - 2.0) * 1000.0, (lat - 41.0) * 1000.0)

    cells = build_demand_cells(
        grid, BOUNDS, is_impervious=is_impervious, is_shaded=is_shaded, to_local_m=to_local
    )
    # Only the top-left 30°C cell survives: hot, impervious, unshaded.
    assert len(cells) == 1
    assert math.isclose(cells[0].weight, 30.0 - COMFORT_UTCI_C)


def test_demand_skips_nan_and_none_and_cold():
    grid = [[float("nan"), None], [25.0, 26.0]]  # all non-hot or invalid
    cells = build_demand_cells(
        grid, BOUNDS,
        is_impervious=lambda lo, la: True,
        is_shaded=lambda lo, la: False,
        to_local_m=lambda lo, la: (0.0, 0.0),
    )
    assert cells == []  # nan, none, 25 (<26), 26 (heat=0) all excluded


def test_weight_is_degrees_above_comfort():
    grid = [[40.0]]
    cells = build_demand_cells(
        grid, BOUNDS,
        is_impervious=lambda lo, la: True,
        is_shaded=lambda lo, la: False,
        to_local_m=lambda lo, la: (1.0, 2.0),
    )
    assert len(cells) == 1
    assert cells[0].weight == 40.0 - COMFORT_UTCI_C
    assert (cells[0].x_m, cells[0].y_m) == (1.0, 2.0)
