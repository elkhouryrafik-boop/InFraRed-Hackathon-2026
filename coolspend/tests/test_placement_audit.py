"""Post-placement audit: independently verify no tree sits on a building (roof =
impossible to plant/depave) + flag clumps. Uses a stubbed OSM building fetch so
the test is offline + deterministic.
"""
from __future__ import annotations

import pytest

from coolspend import placement_audit


@pytest.fixture
def _stub_building(monkeypatch):
    # One square building footprint around (2.2000, 41.4000), ~30 m a side.
    d = 0.00015  # ~16 m in lon/lat at this latitude
    ring = [
        (2.2000 - d, 41.4000 - d),
        (2.2000 + d, 41.4000 - d),
        (2.2000 + d, 41.4000 + d),
        (2.2000 - d, 41.4000 + d),
        (2.2000 - d, 41.4000 - d),
    ]
    monkeypatch.setattr(
        "coolspend.osm_buildings.fetch_building_ways", lambda bounds, **k: [ring]
    )
    return ring


def test_tree_on_building_is_flagged(_stub_building):
    trees = [
        {"lon": 2.2000, "lat": 41.4000, "species": "Tipuana tipu"},  # dead centre of building
        {"lon": 2.2030, "lat": 41.4000, "species": "Celtis australis"},  # ~250 m east, clear
    ]
    rep = placement_audit.audit_trees(trees)
    assert rep.n_on_building == 1
    assert rep.all_valid is False
    assert any("building" in r for v in rep.violations for r in v.reasons)


def test_clear_well_spaced_trees_pass(_stub_building):
    # Two trees ~30 m apart, both well clear of the building.
    trees = [
        {"lon": 2.2040, "lat": 41.4000, "species": "Tipuana tipu"},
        {"lon": 2.2044, "lat": 41.4000, "species": "Celtis australis"},
    ]
    rep = placement_audit.audit_trees(trees)
    assert rep.n_on_building == 0
    assert rep.all_valid is True


def test_clump_is_flagged(_stub_building):
    # Two trees ~4 m apart (well under the 8 m spacing) → a clump.
    trees = [
        {"lon": 2.2040, "lat": 41.4000, "species": "Tipuana tipu"},
        {"lon": 2.20405, "lat": 41.4000, "species": "Celtis australis"},  # ~4 m east
    ]
    rep = placement_audit.audit_trees(trees)
    assert rep.n_too_close >= 1


def test_empty_trees_safe():
    rep = placement_audit.audit_trees([])
    assert rep.n_trees == 0
    assert rep.all_valid is True
