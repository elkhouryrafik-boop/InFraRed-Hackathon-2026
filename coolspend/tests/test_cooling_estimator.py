"""CoolingEstimator + shade proxy (PAPER limitations #2/#3 Tier 0): a sim-free,
geometry-real cooling estimate with a centralised measured-vs-estimate label.
"""
from __future__ import annotations

import math

from coolspend import shade_proxy as sp
from coolspend.cooling_estimator import (
    ShadeProxyEstimator,
    MockScalarEstimator,
    estimate_site_cooling,
)

_POLY = [[2.1664, 41.3824], [2.1672, 41.3824], [2.1672, 41.3830],
         [2.1664, 41.3830], [2.1664, 41.3824]]
_TREES = [
    {"lon": 2.1666, "lat": 41.3826, "species": "Tipuana tipu"},
    {"lon": 2.1669, "lat": 41.3827, "species": "Celtis australis"},
    {"lon": 2.1667, "lat": 41.3828, "species": "Styphnolobium japonicum"},
]


def test_solar_positions_july_are_daytime_sun():
    suns = sp.solar_positions_july(41.39)
    assert len(suns) >= 3
    for s in suns:
        assert math.degrees(s.altitude_rad) > 5.0
        assert abs((s.east ** 2 + s.north ** 2) - 1.0) < 1e-6  # unit horizontal vector


def test_shade_proxy_is_never_measured():
    e = ShadeProxyEstimator().estimate(_TREES, _POLY)
    assert e.fidelity == "shade_proxy"
    assert e.is_measured is False
    assert "NOT measured" in e.label


def test_shade_proxy_estimates_positive_cooled_area():
    e = estimate_site_cooling(_TREES, _POLY, "proxy")
    assert e.cooled_m2 is not None and e.cooled_m2 > 0
    assert e.mean_delta_c is not None


def test_more_trees_cool_more():
    one = estimate_site_cooling(_TREES[:1], _POLY, "proxy").cooled_m2
    three = estimate_site_cooling(_TREES, _POLY, "proxy").cooled_m2
    assert three >= one


def test_no_trees_yields_no_cooling():
    e = estimate_site_cooling([], _POLY, "proxy")
    assert not e.cooled_m2  # None or 0


def test_mock_scalar_is_not_measured():
    e = MockScalarEstimator().estimate(_TREES, _POLY)
    assert e.fidelity == "scalar"
    assert e.is_measured is False


def test_existing_canopy_reduces_new_shade_gain():
    # A cell already shaded by an existing crown should not count as newly shaded.
    cells = [sp.ProxyCell(0.0, -5.0, 5.0, 4.0)]
    tree = [sp.ProxyTree(0.0, 0.0, 4.0, 10.0)]
    suns = sp.solar_positions_july()
    bare = sp.shade_gain_per_cell(cells, tree, suns)
    withexisting = sp.shade_gain_per_cell(cells, tree, suns, already_shaded=tree)
    assert withexisting[0] <= bare[0]
