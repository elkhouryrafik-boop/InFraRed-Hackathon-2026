"""
Offline tests for coolspend/smart_placement.py — the budgeted greedy
weighted-max-coverage placement engine.

Covers the properties that make the algorithm "up to standard":
  - budget never exceeded
  - min-spacing between placed trees enforced
  - greedy targets the highest-weight (hottest) demand first
  - submodular diminishing returns (overlapping slots don't both get planted)
  - anti-monoculture diversity cap binds in steady state
  - cost-benefit preference (more cooling per euro wins)
  - the (1 - 1/e) optimality guarantee vs brute-force optimum on a small instance
"""
from __future__ import annotations

import itertools

from coolspend.smart_placement import (
    DemandCell,
    SpeciesOption,
    CandidateSlot,
    place_trees_greedy as _raw_greedy,
)


def place_trees_greedy(*args, **kwargs):
    """These tests verify greedy MECHANICS (hottest-first, cost-benefit, diversity,
    max-crown, the 1-1/e bound) on the deterministic BINARY crown-coverage objective
    — they use synthetic demand cells directly under the slot, which the shade-gain
    model (correctly) casts shadow AWAY from. The shade-gain physics + live A/B are
    covered in test_shade_gain_placement.py. So default these mechanics calls to the
    binary objective unless a test overrides it.
    """
    kwargs.setdefault("use_shade_gain", False)
    return _raw_greedy(*args, **kwargs)


SP = SpeciesOption(name="plane", crown_m=8.0, tree_cost_eur=1000.0, cooling_score=1.0)


def _grid_demand(coords_weights):
    return [DemandCell(x, y, w) for (x, y, w) in coords_weights]


def test_empty_inputs_return_empty():
    r = place_trees_greedy([], [], [SP], budget_eur=10_000)
    assert r.placed == []
    assert r.stop_reason


def test_budget_never_exceeded():
    demand = _grid_demand([(i * 10.0, 0.0, 1.0) for i in range(10)])
    cands = [CandidateSlot(i * 10.0, 0.0, "planter") for i in range(10)]
    r = place_trees_greedy(demand, cands, [SP], budget_eur=2_500, min_spacing_m=1.0)
    assert r.total_cost_eur <= 2_500
    assert len(r.placed) == 2  # 2 x 1000 fits, 3rd (3000) would exceed


def test_min_spacing_enforced():
    demand = _grid_demand([(0.0, 0.0, 5.0), (1.0, 0.0, 5.0)])
    # Two candidates 1 m apart; spacing 5 m → only one can be planted.
    cands = [CandidateSlot(0.0, 0.0, "planter"), CandidateSlot(1.0, 0.0, "planter")]
    r = place_trees_greedy(demand, cands, [SP], budget_eur=10_000, min_spacing_m=5.0)
    assert len(r.placed) == 1


def test_greedy_takes_hottest_first():
    # A hot cell at x=0 (weight 100), a cool one at x=100 (weight 1).
    demand = _grid_demand([(0.0, 0.0, 100.0), (100.0, 0.0, 1.0)])
    cands = [CandidateSlot(0.0, 0.0, "planter"), CandidateSlot(100.0, 0.0, "planter")]
    # Budget for exactly one tree.
    r = place_trees_greedy(demand, cands, [SP], budget_eur=1_000, min_spacing_m=1.0)
    assert len(r.placed) == 1
    assert r.placed[0].x_m == 0.0  # the hot one


def test_submodular_no_double_cover():
    # Two candidates on top of the same single demand cell. Greedy should plant ONE
    # (the second adds zero marginal gain) even though budget allows two.
    demand = _grid_demand([(0.0, 0.0, 10.0)])
    cands = [CandidateSlot(0.0, 0.0, "planter"), CandidateSlot(0.5, 0.0, "planter")]
    r = place_trees_greedy(demand, cands, [SP], budget_eur=10_000, min_spacing_m=0.1)
    assert len(r.placed) == 1
    assert r.stop_reason == "no positive-gain affordable slot remains"


def test_cost_benefit_prefers_cheaper_equal_cover():
    demand = _grid_demand([(0.0, 0.0, 10.0)])
    cheap = SpeciesOption("cheap", 8.0, 500.0, 0.9)
    pricey = SpeciesOption("pricey", 8.0, 2000.0, 1.0)
    cands = [CandidateSlot(0.0, 0.0, "planter")]
    r = place_trees_greedy(demand, cands, [cheap, pricey], budget_eur=10_000, min_spacing_m=0.1)
    assert len(r.placed) == 1
    assert r.placed[0].species == "cheap"  # same coverage, better gain/€


def test_diversity_cap_binds():
    # 12 identical hot cells far apart; two equal species. With a 40% cap, no species
    # should exceed ~40% of the planting in steady state.
    demand = _grid_demand([(i * 50.0, 0.0, 10.0) for i in range(12)])
    cands = [CandidateSlot(i * 50.0, 0.0, "planter") for i in range(12)]
    a = SpeciesOption("a", 8.0, 1000.0, 1.0)
    b = SpeciesOption("b", 8.0, 1000.0, 1.0)
    r = place_trees_greedy(
        demand, cands, [a, b], budget_eur=100_000, min_spacing_m=1.0,
        max_species_share=0.5, diversity_grace=2,
    )
    n = len(r.placed)
    assert n >= 6
    from collections import Counter
    counts = Counter(p.species for p in r.placed)
    # Neither species should dominate beyond the cap (+ grace slack).
    assert max(counts.values()) <= n * 0.5 + 2


def test_max_crown_blocks_oversized_species():
    # One demand cell; a slot that can only host a 4 m crown. A big (8 m) species is
    # rejected; a small (3 m) species is planted.
    demand = _grid_demand([(0.0, 0.0, 10.0)])
    big = SpeciesOption("big", 8.0, 1000.0, 1.0)
    small = SpeciesOption("small", 3.0, 1000.0, 0.5)
    tight = CandidateSlot(0.0, 0.0, "planter", max_crown_m=4.0)
    r = place_trees_greedy(demand, [tight], [big, small], budget_eur=10_000, min_spacing_m=0.1)
    assert len(r.placed) == 1
    assert r.placed[0].species == "small"


def test_max_crown_inf_default_allows_all():
    demand = _grid_demand([(0.0, 0.0, 10.0)])
    big = SpeciesOption("big", 8.0, 1000.0, 1.0)
    wide = CandidateSlot(0.0, 0.0, "planter")  # max_crown_m defaults to inf
    r = place_trees_greedy(demand, [wide], [big], budget_eur=10_000, min_spacing_m=0.1)
    assert len(r.placed) == 1
    assert r.placed[0].species == "big"


def test_coverage_fraction_reported():
    demand = _grid_demand([(0.0, 0.0, 4.0), (3.0, 0.0, 6.0)])  # both within one 8m crown
    cands = [CandidateSlot(1.5, 0.0, "planter")]
    r = place_trees_greedy(demand, cands, [SP], budget_eur=10_000, min_spacing_m=0.1)
    assert r.total_demand_weight == 10.0
    assert r.covered_weight == 10.0
    assert r.coverage_fraction == 1.0


def _brute_force_optimum(demand, cands, sp, budget, spacing):
    """Exhaustive best-coverage subset of candidates under budget + spacing."""
    min_sp2 = spacing * spacing
    crown_r2 = (sp.crown_m / 2.0) ** 2

    def covers(slot):
        return {i for i, c in enumerate(demand)
                if (c.x_m - slot.x_m) ** 2 + (c.y_m - slot.y_m) ** 2 <= crown_r2}

    def feasible(subset):
        if len(subset) * sp.tree_cost_eur > budget:
            return False
        for a, b in itertools.combinations(subset, 2):
            if (cands[a].x_m - cands[b].x_m) ** 2 + (cands[a].y_m - cands[b].y_m) ** 2 < min_sp2:
                return False
        return True

    best = 0.0
    idxs = range(len(cands))
    for k in range(0, len(cands) + 1):
        for subset in itertools.combinations(idxs, k):
            if not feasible(subset):
                continue
            cov = set().union(*(covers(cands[i]) for i in subset)) if subset else set()
            best = max(best, sum(demand[i].weight for i in cov))
    return best


def test_greedy_within_one_minus_one_over_e_of_optimum():
    """On a small instance, greedy coverage must be >= (1 - 1/e) * optimum."""
    import math

    # 6 demand cells of varied weight; 5 candidate slots with partial overlaps.
    demand = _grid_demand([
        (0.0, 0.0, 10.0), (5.0, 0.0, 8.0), (10.0, 0.0, 6.0),
        (0.0, 5.0, 4.0), (5.0, 5.0, 9.0), (20.0, 20.0, 7.0),
    ])
    cands = [
        CandidateSlot(2.5, 2.5, "planter"),
        CandidateSlot(7.5, 2.5, "planter"),
        CandidateSlot(0.0, 0.0, "planter"),
        CandidateSlot(20.0, 20.0, "planter"),
        CandidateSlot(5.0, 0.0, "planter"),
    ]
    sp = SpeciesOption("s", crown_m=10.0, tree_cost_eur=1000.0, cooling_score=1.0)
    budget = 3_000  # up to 3 trees
    spacing = 1.0

    greedy = place_trees_greedy(demand, cands, [sp], budget_eur=budget, min_spacing_m=spacing)
    opt = _brute_force_optimum(demand, cands, sp, budget, spacing)

    bound = (1 - 1 / math.e) * opt
    assert greedy.covered_weight >= bound - 1e-9, (
        f"greedy {greedy.covered_weight} < (1-1/e)*opt {bound} (opt={opt})"
    )
