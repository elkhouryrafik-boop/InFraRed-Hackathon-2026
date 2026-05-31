"""Closes PAPER limitation #7: canopy cover reported against BOTH the sampled
cell and the plantable strip, with the plantable strip as the truer headline.
"""
from __future__ import annotations

from coolspend.design_metrics import design_metrics


def _trees(n: int, sp: str = "Tipuana tipu") -> list[dict]:
    return [{"species": sp} for _ in range(n)]


def test_plantable_cover_ge_cell_cover():
    m = design_metrics(_trees(8), site_area_m2=40000.0, cost_eur=120000.0,
                        plantable_area_m2=1200.0)
    assert m["canopy_cover_pct_plantable"] >= m["canopy_cover_pct_cell"]


def test_headline_uses_plantable_when_available():
    m = design_metrics(_trees(8), site_area_m2=40000.0, cost_eur=120000.0,
                        plantable_area_m2=1200.0)
    assert m["canopy_cover_denominator"] == "plantable_strip"
    assert m["canopy_cover_pct"] == m["canopy_cover_pct_plantable"]


def test_headline_falls_back_to_cell_without_plantable():
    m = design_metrics(_trees(8), site_area_m2=40000.0, cost_eur=120000.0)
    assert m["canopy_cover_denominator"] == "sampled_cell"
    assert m["canopy_cover_pct"] == m["canopy_cover_pct_cell"]
    assert "canopy_cover_pct_plantable" not in m


def test_ambient_drop_keyed_to_cell_not_plantable():
    # est ΔT must use the (smaller) cell cover, not the inflated plantable cover,
    # because 0.075 °C/% is a neighbourhood-scale coefficient.
    m = design_metrics(_trees(8), site_area_m2=40000.0, cost_eur=120000.0,
                        plantable_area_m2=1200.0)
    expected = round(m["canopy_cover_pct_cell"] * 0.075, 2)
    assert m["est_air_temp_drop_c"] == expected


def test_plantable_cover_capped_at_100():
    m = design_metrics(_trees(20), site_area_m2=40000.0, cost_eur=120000.0,
                        plantable_area_m2=100.0)
    assert m["canopy_cover_pct_plantable"] <= 100.0
