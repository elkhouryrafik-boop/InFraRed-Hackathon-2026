"""Provenance: composite_score_B must be exactly reproducible in-repo.

Guards PAPER Limitation #1's fix — if the scored grid is regenerated with a
different composite formula, this fails and the datasheet must be updated.
"""
from __future__ import annotations

import pytest

from coolspend import provenance


def test_weights_are_a_convex_combination():
    assert abs(sum(provenance.COMPOSITE_B_WEIGHTS.values()) - 1.0) < 1e-9
    assert all(w >= 0 for w in provenance.COMPOSITE_B_WEIGHTS.values())


def test_composite_b_reproduces_exactly_over_all_cells():
    res = provenance.verify_scored_grid()
    if not res["available"]:
        pytest.skip("scored_grid.geojson not present")
    assert res["n_cells"] >= 400
    # Reconstruction is exact to floating-point epsilon, not approximate.
    assert res["max_abs_residual"] is not None
    assert res["max_abs_residual"] < 1e-9


def test_weights_are_recoverable_from_data_when_numpy_present():
    res = provenance.verify_scored_grid()
    if not res["available"] or res.get("recovered_weights") is None:
        pytest.skip("scored_grid or numpy not present")
    assert res["r2"] is not None and res["r2"] > 0.999999
    for key, w in provenance.COMPOSITE_B_WEIGHTS.items():
        assert abs(res["recovered_weights"][key] - w) < 1e-4


def test_reproduce_single_cell_matches_helper():
    # Synthetic cell: B = 0.45*1 + 0.20*0 + 0.15*0 + 0.05*0 + 0.15*0 = 0.45
    props = {"s1_sealed": 1.0, "s2_lst_anomaly": 0.0, "s3_inverted_ndvi": 0.0,
             "s4_mismatch": 0.0, "prpi": 0.0}
    assert abs(provenance.reproduce_composite_b(props) - 0.45) < 1e-12
