"""Tests for coolspend/design_metrics.py — urban-design metric helpers."""
from __future__ import annotations

from coolspend import design_metrics as dm


def _trees(n, species="Tipuana tipu"):
    return [{"species": species} for _ in range(n)]


def test_canopy_area_sums_crown_disks():
    # Tipuana crown 10 m → radius 5 → π·25 ≈ 78.54 m² each.
    a = dm.canopy_area_m2(_trees(2, "Tipuana tipu"))
    assert 155.0 < a < 158.0


def test_canopy_area_empty():
    assert dm.canopy_area_m2([]) == 0.0


def test_design_metrics_cover_and_temp_and_per_euro():
    m = dm.design_metrics(_trees(10, "Tipuana tipu"), site_area_m2=10_000.0, cost_eur=100_000.0)
    assert m["tree_count"] == 10
    assert m["canopy_area_m2"] > 0
    # ~785 m² canopy / 10000 m² ≈ 7.9% cover
    assert 7.0 < m["canopy_cover_pct"] < 9.0
    assert m["canopy_target_pct"] == 30.0
    assert m["canopy_gap_to_target_pct"] > 0
    # ΔT ≈ cover% × 0.075
    assert m["est_air_temp_drop_c"] == round(m["canopy_cover_pct"] * 0.075, 2)
    assert m["canopy_m2_per_1000eur"] is not None


def test_design_metrics_no_area_no_cover():
    m = dm.design_metrics(_trees(3), site_area_m2=None, cost_eur=None)
    assert "canopy_cover_pct" not in m
    assert m["canopy_m2_per_1000eur"] is None


def test_person_degrees():
    assert dm.person_degrees(1000, 1.5) == 1500.0
    assert dm.person_degrees(None, 1.5) is None
    assert dm.person_degrees(1000, None) is None
