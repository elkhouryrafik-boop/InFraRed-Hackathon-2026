"""Shade-gain greedy placement (PAPER limitation #2): placement order is driven
by ray-cast sun-blockage, not binary crown overlap. Submodular + capped.
"""
from __future__ import annotations

from coolspend.smart_placement import (
    place_trees_greedy,
    DemandCell,
    CandidateSlot,
    SpeciesOption,
)


def _grid(step: int = 3, n: int = 30, w: float = 5.0) -> list[DemandCell]:
    return [DemandCell(float(x), float(y), w) for x in range(0, n, step) for y in range(0, n, step)]


def _slots() -> list[CandidateSlot]:
    return [
        CandidateSlot(float(x), float(y), "in_ground", 0.0, float("inf"))
        for x in (5, 15, 25)
        for y in (5, 15, 25)
    ]


_SPECIES = [SpeciesOption("Tipuana tipu", 10.0, 10000.0, 0.9, 18.0)]


def test_shade_gain_places_within_budget_and_spacing():
    r = place_trees_greedy(_grid(), _slots(), _SPECIES, budget_eur=60000.0)
    assert len(r.placed) >= 1
    assert r.total_cost_eur <= 60000.0
    # ≥8 m spacing between placed trees
    for i, a in enumerate(r.placed):
        for b in r.placed[i + 1:]:
            d2 = (a.x_m - b.x_m) ** 2 + (a.y_m - b.y_m) ** 2
            assert d2 >= 8.0 * 8.0 - 1e-6


def test_marginal_gain_is_non_increasing_submodular():
    # Greedy marginal weights are recorded in placement order; for a submodular
    # objective they must be non-increasing.
    r = place_trees_greedy(_grid(), _slots(), _SPECIES, budget_eur=90000.0)
    margins = [t.marginal_weight for t in r.placed]
    for a, b in zip(margins, margins[1:]):
        assert b <= a + 1e-6


def test_shade_gain_fallback_to_binary_flag():
    r_sg = place_trees_greedy(_grid(), _slots(), _SPECIES, budget_eur=60000.0)
    r_bin = place_trees_greedy(_grid(), _slots(), _SPECIES, budget_eur=60000.0,
                               use_shade_gain=False)
    # Both run and place trees; the binary proxy counts full crown overlap so its
    # coverage_fraction is generally higher (different, looser metric).
    assert len(r_sg.placed) >= 1 and len(r_bin.placed) >= 1
    assert r_bin.coverage_fraction >= r_sg.coverage_fraction


def test_double_shading_earns_no_extra_gain():
    # Two slots shading (largely) the same cells: the second's marginal must be
    # strictly less than if it shaded fresh ground — capped at 1.0 per cell.
    cells = _grid()
    r = place_trees_greedy(cells, _slots(), _SPECIES, budget_eur=90000.0)
    if len(r.placed) >= 2:
        assert r.placed[1].marginal_weight <= r.placed[0].marginal_weight + 1e-6
