"""Offline tests for coolspend/osm_roads.py (no network — seeded cache + query)."""
from __future__ import annotations

import json

from coolspend import osm_roads

BOUNDS = {"west": 2.166, "south": 41.382, "east": 2.168, "north": 41.3835}


def test_query_targets_vehicle_roads_only():
    q = osm_roads._overpass_query(BOUNDS)
    assert "residential" in q and "primary" in q and "service" in q
    # Pedestrian/footway must NOT be in the carriageway query (plazas stay plantable).
    assert "footway" not in q and "pedestrian" not in q and "cycleway" not in q


def test_road_exclusion_from_cached_ways(tmp_path, monkeypatch):
    monkeypatch.setattr(osm_roads, "_CACHE_DIR", tmp_path)
    # Seed the cache with a fake residential way so no network call happens.
    key = osm_roads._bbox_key(BOUNDS)
    ways = [{
        "highway": "residential",
        "geometry": [(2.1665, 41.3825), (2.1675, 41.3825)],  # ~horizontal segment
    }]
    (tmp_path / f"roads_{key}.json").write_text(json.dumps(ways), encoding="utf-8")

    # Simple local-metre projection (degrees -> ~metres) for the test.
    def to_local(lon, lat):
        return ((lon - 2.166) * 100_000.0, (lat - 41.382) * 100_000.0)

    polys = osm_roads.road_exclusion_polygons_local_m(BOUNDS, to_local)
    assert len(polys) == 1
    # Residential half-width = 5 m → a point on the centerline is inside the buffer.
    from shapely.geometry import Point
    cx, cy = to_local(2.1670, 41.3825)
    assert polys[0].contains(Point(cx, cy))
    # A point 50 m north of the line is outside.
    assert not polys[0].contains(Point(cx, cy + 50.0))


def test_fetch_returns_empty_on_no_cache_no_network(tmp_path, monkeypatch):
    monkeypatch.setattr(osm_roads, "_CACHE_DIR", tmp_path)
    # Force the requests import path to fail → graceful [].
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "requests":
            raise ImportError("no requests in this test")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert osm_roads.fetch_road_ways(BOUNDS) == []
