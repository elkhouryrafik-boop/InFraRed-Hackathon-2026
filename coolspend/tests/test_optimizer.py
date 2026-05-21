"""
coolspend/tests/test_optimizer.py — Offline smoke tests for the NSGA-II optimizer.

All tests run offline with INFRARED_BACKEND=mock (default).
No live SDK calls are made; SimBudget proves the hot path is SDK-free.

Tests:
  test_pareto_front_min_size         — Pareto front >= 10 distinct configs
  test_no_sdk_in_hot_path            — hot path never touches get_intervention_utci
  test_invalid_placements_excluded   — in-building coords -> active=False
  test_select_top3_distinct          — 3 distinct labelled configs returned
  test_validate_exactly_three_calls  — exactly 3 intervention calls, 4th raises
  test_budget_constraint_active      — over-budget configs produce G1 > 0

Convention: small n_gen / pop_size values keep total suite time well under 10s.
"""
from __future__ import annotations

import os

import numpy as np
import pytest

from coolspend.optimizer import (
    N_TREES,
    DEFAULT_BUDGET_EUR,
    TreeBudgetProblem,
    decode,
    run_optimisation,
    select_top3,
    validate_top3_with_infrared,
)
from coolspend.sdk_client import SimBudget
from coolspend.spatial_engine import load_site


# ── FIXTURES ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def small_result():
    """Run a small optimisation once for the whole module (shared, fast)."""
    return run_optimisation(n_gen=20, pop_size=30, seed=42)


@pytest.fixture(scope="module")
def top3_configs(small_result):
    """Return the top-3 configs for the shared optimisation result."""
    return select_top3(small_result)


# ── TEST 1: Pareto front minimum size ────────────────────────────────────────


def test_pareto_front_min_size(small_result):
    """run_optimisation() returns a Pareto front with >= 10 distinct configurations."""
    F = np.atleast_2d(small_result.F)
    assert len(F) >= 10, (
        f"Expected Pareto front >= 10 configs, got {len(F)}. "
        f"Check pop_size/n_gen are large enough for population diversity."
    )


# ── TEST 2: No SDK in hot path ───────────────────────────────────────────────


def test_no_sdk_in_hot_path(monkeypatch):
    """The NSGA-II hot path never calls get_intervention_utci.

    Monkeypatches get_intervention_utci to raise AssertionError.
    If run_optimisation() completes without raising, the hot path is SDK-free.
    """
    import coolspend.sdk_client as sdk_client_module

    def _raise(*args, **kwargs):
        raise AssertionError(
            "get_intervention_utci was called from the NSGA-II hot path! "
            "The _evaluate() method must use surrogates only."
        )

    monkeypatch.setattr(sdk_client_module, "get_intervention_utci", _raise)

    # Should complete without raising
    result = run_optimisation(n_gen=5, pop_size=10, seed=42)
    F = np.atleast_2d(result.F)
    assert len(F) > 0, "Optimisation produced no results"


# ── TEST 3: Invalid placements excluded ──────────────────────────────────────


def test_invalid_placements_excluded():
    """decode() marks in-building coordinates as active=False.

    Uses the first building's centroid from the loaded site fixture.
    The slot at that coordinate must have active=False.
    """
    site = load_site()
    assert len(site["buildings"]) > 0, "Test requires at least one building in fixture"

    building = site["buildings"][0]
    cx, cy = building.centroid.x, building.centroid.y

    # Build a chromosome where slot 0 is inside the building
    x_flat = np.tile([cx, cy], N_TREES).astype(float)
    cfg = decode(x_flat)

    # Slot 0 should be inactive (inside building)
    assert cfg["trees"][0]["active"] is False, (
        f"Expected tree slot 0 at ({cx:.2f}, {cy:.2f}) to be inactive "
        f"(inside building), but got active=True"
    )
    # tree_count must not count it
    # (other slots also use the same building centroid so all should be False)
    assert cfg["tree_count"] == 0, (
        f"Expected tree_count=0 when all slots are inside a building, "
        f"got {cfg['tree_count']}"
    )


# ── TEST 4: select_top3 returns 3 distinct labelled configs ──────────────────


def test_select_top3_distinct(top3_configs):
    """select_top3() returns exactly 3 configs with distinct ranks and labels."""
    assert len(top3_configs) == 3, f"Expected 3 configs, got {len(top3_configs)}"

    ranks = [c["rank"] for c in top3_configs]
    labels = [c["label"] for c in top3_configs]

    # All ranks distinct
    assert len(set(ranks)) == 3, f"Ranks not distinct: {ranks}"
    # All labels distinct
    assert len(set(labels)) == 3, f"Labels not distinct: {labels}"
    # Expected label set
    assert set(labels) == {"MAX_THERMAL_RELIEF", "MAX_ECOLOGICAL", "BALANCED"}, (
        f"Unexpected labels: {labels}"
    )

    # Each config must carry the required honesty fields
    for cfg in top3_configs:
        assert "delta_tmrt_c" in cfg
        assert cfg["delta_tmrt_uncertainty_c"] == 4.0
        assert "surrogate_note" in cfg
        assert cfg["topsis_score"] is None   # filled later by Plan 02-05


# ── TEST 5: Exactly 3 validation calls ───────────────────────────────────────


def test_validate_exactly_three_calls(top3_configs):
    """validate_top3_with_infrared makes exactly 3 intervention calls.

    The SimBudget log length is the proof. A 4th call raises RuntimeError.
    """
    budget = SimBudget(max_live_calls=3)
    validated = validate_top3_with_infrared(top3_configs, budget=budget)

    # Exactly 3 intervention calls logged
    assert len(budget.log) == 3, (
        f"Expected 3 budget log entries, got {len(budget.log)}. "
        f"Log: {budget.log}"
    )

    # Each validated config has the required UTCI fields
    for cfg in validated:
        assert "baseline_utci_c" in cfg
        assert "validated_utci_c" in cfg
        assert "delta_utci_c" in cfg
        assert "validated_backend" in cfg
        assert "validated_disclaimer" in cfg

    # 4th call must raise (SimBudget cap enforcement)
    with pytest.raises(RuntimeError, match="SimBudget exceeded"):
        budget.record("overflow_call")


# ── TEST 6: Budget constraint G1 > 0 for over-budget configs ─────────────────


def test_budget_constraint_active():
    """A chromosome whose tree_count cost exceeds a tiny budget yields G1 > 0.

    Uses a hand-built chromosome with valid coordinates so tree_count > 0,
    then evaluates the TreeBudgetProblem with a budget of 1 EUR (impossibly low).
    """
    from coolspend.cost_model import per_tree_cost

    # Use a tiny budget guaranteed to be exceeded by even 1 active tree
    tiny_budget = 1.0   # 1 EUR — any planting costs far more

    problem = TreeBudgetProblem(budget_eur=tiny_budget)

    # Build a chromosome with coordinates in the open plaza interior
    # (30, 21) is the centre — should be valid location
    x_flat = np.tile([30.0, 21.0], N_TREES).astype(float)

    out: dict = {}
    problem._evaluate(x_flat, out)

    g1 = out["G"][0]

    # If at least 1 tree is valid, cost > 1 EUR => G1 > 0 (infeasible)
    cfg = decode(x_flat)
    if cfg["tree_count"] > 0:
        assert g1 > 0, (
            f"Expected G1 > 0 for over-budget config (budget={tiny_budget} EUR, "
            f"tree_count={cfg['tree_count']}, "
            f"cost={cfg['tree_count'] * per_tree_cost():.2f} EUR), "
            f"got G1={g1}"
        )
    else:
        # All slots invalid (unlikely for centre coordinate), cost = 0 => G1 <= 0
        assert g1 <= 0, f"Expected G1 <= 0 for zero active trees, got {g1}"
