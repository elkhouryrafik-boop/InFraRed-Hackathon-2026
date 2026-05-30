"""
Offline tests for coolspend/ground_analysis.py (impervious / depave targeting).

The live ground-material fetch needs the network + key, so these tests cover:
  - the non-live short-circuit (mock/cached return a well-formed empty result),
  - the depaved_by_canopy geometry math against a synthetic impervious polygon.
The live path is exercised manually / in integration, not here.
"""
from __future__ import annotations

from coolspend.ground_analysis import (
    analyze_impervious,
    depaved_by_canopy,
    canopy_cover_fraction,
)

# ~120 m x ~150 m polygon in the Eixample.
RING = [[2.1660, 41.3820], [2.1680, 41.3820], [2.1680, 41.3835], [2.1660, 41.3835]]


def test_non_live_returns_empty_but_wellformed():
    r = analyze_impervious(RING, backend="mock")
    assert r["available"] is False
    assert r["impervious_m2"] == 0.0
    assert r["site_area_m2"] > 0  # area is computed locally, no network
    assert r["geojson"]["type"] == "FeatureCollection"
    assert r["geojson"]["features"] == []


def test_site_area_is_plausible():
    """The drawn ~0.16 km x ~0.17 km block should be ~2.5-3 ha."""
    r = analyze_impervious(RING, backend="mock")
    assert 20_000 < r["site_area_m2"] < 35_000


def test_depaved_by_canopy_intersects_impervious():
    """Canopy disks over an impervious polygon yield a positive, bounded area."""
    # A ~100 m square impervious patch around the ring's SW corner, in lon/lat.
    patch = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"material": "impervious"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [2.1660, 41.3820],
                            [2.1675, 41.3820],
                            [2.1675, 41.3832],
                            [2.1660, 41.3832],
                            [2.1660, 41.3820],
                        ]
                    ],
                },
            }
        ],
    }
    trees = [
        {"lon": 2.1665, "lat": 41.3825, "crown_diameter_m": 8.0},
        {"lon": 2.1670, "lat": 41.3828, "crown_diameter_m": 6.0},
    ]
    depaved = depaved_by_canopy(patch, trees)
    # Two disks (r=4, r=3) fully inside the patch -> ~ pi(16)+pi(9) = ~78 m².
    assert 60 < depaved < 90


def test_depaved_by_canopy_handles_empty():
    assert depaved_by_canopy({"features": []}, []) == 0.0
    assert depaved_by_canopy({"features": []}, [{"lon": 2.1, "lat": 41.3}]) == 0.0


def test_non_live_includes_permeable_target():
    """#2: permeable fraction + the 40-50% target band are always present."""
    r = analyze_impervious(RING, backend="mock")
    assert r["permeable_fraction"] == 0.0
    assert r["permeable_target_min"] == 0.40
    assert r["permeable_target_max"] == 0.50


def test_canopy_cover_fraction_shape_and_band():
    """#1: canopy cover reports fraction, m², and 30-40% band membership."""
    # Tree centres inside RING; species crown resolved from bcn_species table.
    trees = [
        {"lon": 2.1668, "lat": 41.3827, "species": "Platanus x acerifolia"},
        {"lon": 2.1672, "lat": 41.3829, "species": "Celtis australis"},
    ]
    c = canopy_cover_fraction(RING, trees)
    assert c["target_min"] == 0.30 and c["target_max"] == 0.40
    assert 0.0 < c["cover_fraction"] < 1.0
    assert c["canopy_m2"] > 0
    assert c["in_band"] == (0.30 <= c["cover_fraction"] <= 0.40)


def test_canopy_cover_resolves_species_crown():
    """A large-crown species (plane, 10 m) yields more canopy than a small one."""
    big = canopy_cover_fraction(RING, [{"lon": 2.167, "lat": 41.3827, "species": "Platanus x acerifolia"}])
    small = canopy_cover_fraction(RING, [{"lon": 2.167, "lat": 41.3827, "species": "Cercis siliquastrum"}])
    assert big["canopy_m2"] > small["canopy_m2"]


def test_canopy_cover_empty_is_zero():
    c = canopy_cover_fraction(RING, [])
    assert c["cover_fraction"] == 0.0
    assert c["canopy_m2"] == 0.0
