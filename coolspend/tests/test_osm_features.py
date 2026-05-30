"""Offline tests for coolspend/osm_features.py (no network — seeded cache + query)."""
from __future__ import annotations

import json

from coolspend import osm_features

BOUNDS = {"west": 2.166, "south": 41.382, "east": 2.168, "north": 41.3835}


def test_query_includes_furniture_and_power():
    q = osm_features._overpass_query(BOUNDS)
    for tag in ("fire_hydrant", "crossing", "street_lamp", "traffic_signals",
                "bus_stop", "platform", "manhole", "power"):
        assert tag in q


def test_classify_maps_tags():
    assert osm_features._classify({"emergency": "fire_hydrant"}) == "fire_hydrant"
    assert osm_features._classify({"highway": "crossing"}) == "crossing"
    assert osm_features._classify({"power": "line"}) == "power_line"
    assert osm_features._classify({"amenity": "cafe"}) is None


def test_feature_exclusions_from_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(osm_features, "_CACHE_DIR", tmp_path)
    key = osm_features._bbox_key(BOUNDS)
    feats = [
        {"key": "fire_hydrant", "kind": "point", "coords": [(2.1670, 41.3825)]},
        {"key": "power_line", "kind": "line", "coords": [(2.1665, 41.3828), (2.1675, 41.3828)]},
    ]
    (tmp_path / f"feat_{key}.json").write_text(json.dumps(feats), encoding="utf-8")

    def to_local(lon, lat):
        return ((lon - 2.166) * 100_000.0, (lat - 41.382) * 100_000.0)

    polys = osm_features.feature_exclusion_polygons_local_m(BOUNDS, to_local)
    assert len(polys) == 2
    from shapely.geometry import Point
    hx, hy = to_local(2.1670, 41.3825)
    # Hydrant 3 m keep-out: a point 1 m away is excluded, 10 m away is not.
    assert polys[0].contains(Point(hx + 1.0, hy))
    assert not polys[0].contains(Point(hx + 10.0, hy))


def test_fetch_graceful_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr(osm_features, "_CACHE_DIR", tmp_path)
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "requests":
            raise ImportError("no requests")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert osm_features.fetch_features(BOUNDS) == []
