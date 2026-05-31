"""Offline tests for coolspend/ecology.py — ecosystem-health composite."""
from __future__ import annotations

from coolspend import ecology
from coolspend.bcn_species import species_public, SPECIES_TABLE


def test_every_palette_species_has_ecology():
    for sp in SPECIES_TABLE:
        assert ecology.get_ecology(sp.scientific) is not None, sp.scientific


def test_scores_in_unit_range():
    for e in ecology.ECOLOGY_TABLE:
        s = ecology.ecosystem_score(e)
        assert 0.0 <= s <= 1.0


def test_invasives_are_floored_below_natives():
    cel = ecology.ecosystem_score(ecology.get_ecology("Celtis australis"))
    cer = ecology.ecosystem_score(ecology.get_ecology("Cercis siliquastrum"))
    rob = ecology.ecosystem_score(ecology.get_ecology("Robinia pseudoacacia"))
    lig = ecology.ecosystem_score(ecology.get_ecology("Ligustrum lucidum"))
    # Mediterranean natives clearly beat exotic-invasives.
    assert cel > 0.4 and cer > 0.4
    assert rob < cel and lig < cel
    assert ecology.get_ecology("Robinia pseudoacacia").invasive is True


def test_invasive_penalty_actually_bites():
    # Robinia has top pollinator value (0.90) yet must score low because invasive.
    rob = ecology.get_ecology("Robinia pseudoacacia")
    assert rob.pollinator_value >= 0.85
    assert ecology.ecosystem_score(rob) < 0.15  # nectar does not buy back invasion


def test_hybrid_name_normalisation():
    # "Platanus x acerifolia" must resolve (× / x normalisation).
    assert ecology.get_ecology("Platanus × acerifolia") is not None
    assert ecology.get_ecology("platanus x acerifolia") is not None


def test_ecology_public_shape_and_unknown():
    pub = ecology.ecology_public("Tipuana tipu")
    assert pub is not None
    for k in ("native_status", "drought_heat_tolerance", "ecosystem_score", "invasive"):
        assert k in pub
    assert ecology.ecology_public("Nonexistent species") is None


def test_species_public_carries_ecology():
    # The join point: species_public must surface the ecology block.
    pub = species_public("Celtis australis")
    assert "ecology" in pub
    assert pub["ecology"]["native_status"].startswith("native")
    assert 0.0 <= pub["ecology"]["ecosystem_score"] <= 1.0
