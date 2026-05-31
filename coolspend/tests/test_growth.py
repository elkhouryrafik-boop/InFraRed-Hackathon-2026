"""Species allometric growth curves (Chapman–Richards), replacing the flat
linear establishment ramp. Closes the growth-accuracy gap.
"""
from __future__ import annotations

import pytest

from coolspend import growth as g


def test_age_zero_is_planting_crown():
    assert g.crown_diameter_at_age("Tipuana tipu", 0) == g.PLANTING_CROWN_M


def test_crown_monotonic_non_decreasing_in_age():
    prev = -1.0
    for age in range(0, 51, 2):
        d = g.crown_diameter_at_age("Celtis australis", age)
        assert d >= prev - 1e-9
        prev = d


def test_crown_never_exceeds_mature():
    from coolspend.bcn_species import get_species
    mature = get_species("Tipuana tipu").crown_diameter_m
    for age in (0, 10, 20, 40, 100):
        assert g.crown_diameter_at_age("Tipuana tipu", age) <= mature + 1e-9


def test_fast_species_matures_before_slow():
    # At 20 yr, the fast Tipuana (maturity 20) is far closer to mature than the
    # slow Cercis (maturity 40).
    fast = g.cooling_fraction_at_age("Tipuana tipu", 20)
    slow = g.cooling_fraction_at_age("Cercis siliquastrum", 20)
    assert fast > slow
    assert fast > 0.85  # ~90% at its own maturity year


def test_cooling_fraction_in_unit_interval():
    for age in (0, 5, 25, 60):
        cf = g.cooling_fraction_at_age("Jacaranda mimosifolia", age)
        assert 0.0 <= cf <= 1.0


def test_near_mature_fraction_at_maturity_year():
    # By construction crown reaches ~95% of mature at maturity_years, so cooling
    # (area, squared) is ~0.90.
    cf = g.cooling_fraction_at_age("Tipuana tipu", 20)
    assert cf == pytest.approx(0.90, abs=0.05)


def test_growth_params_shape():
    p = g.growth_params("Celtis australis")
    assert p["mature_crown_m"] > 0
    assert p["maturity_years"] in (20.0, 30.0, 40.0)
    assert p["rate_k"] > 0
