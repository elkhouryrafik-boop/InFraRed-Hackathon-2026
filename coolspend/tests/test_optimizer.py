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
    _build_baseline_geometry,
    decode,
    naive_baseline_config,
    run_optimisation,
    save_outputs,
    select_top3,
    topsis_rank,
    validate_top3_with_infrared,
)
from coolspend.sdk_client import SimBudget
from coolspend.spatial_engine import is_valid_location, load_site


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


# ── REMEDIATION TESTS (Option A — non-degeneracy, determinism, naive baseline) ─


@pytest.fixture(scope="module")
def real_result():
    """A realistic NSGA-II run (seed 42) used to assert a non-degenerate front.

    Smaller than the production 60×60 to keep the suite fast, but large enough that
    the core-weighted thermal↔ecological trade-off (Option A) spreads the front.
    """
    return run_optimisation(n_gen=40, pop_size=40, seed=42)


def test_pareto_front_is_non_degenerate(real_result):
    """REMEDIATION root-cause fix: the Pareto front has > 1 UNIQUE objective row.

    Before Option A the front collapsed to a single point (thermal and ecological
    objectives were correlated). Core-weighted thermal coverage creates a genuine
    trade-off, so distinct objective vectors must now appear on the front.
    """
    F = np.atleast_2d(real_result.F)
    n_unique = np.unique(F, axis=0).shape[0]
    assert n_unique > 1, (
        f"Pareto front is DEGENERATE: only {n_unique} unique objective row(s). "
        "Option A core-weighting must produce a spread front."
    )


def test_top3_configs_differ_in_delta_and_cost(real_result):
    """Top-3 configs differ in delta_utci_c AND euro/°C — not just their labels.

    A degenerate front would yield three configs with identical thermal/cost
    values distinguished only by label. After Option A the validated UTCI deltas
    and the euro/°C KPIs must take more than one distinct value.
    """
    top3 = select_top3(real_result)
    budget = SimBudget(max_live_calls=3)
    top3 = validate_top3_with_infrared(top3, budget=budget)
    top3 = topsis_rank(top3)

    deltas = {c["delta_utci_c"] for c in top3}
    kpis = {c["cost_per_utci_degree"]["value"] for c in top3}

    assert len(deltas) > 1, (
        f"Top-3 delta_utci_c values are not distinct: {deltas} — front is degenerate."
    )
    assert len(kpis) > 1, (
        f"Top-3 euro/°C KPIs are not distinct: {kpis} — ranking is degenerate."
    )


def test_seed_determinism_same_seed_identical():
    """TRUE seed determinism: seed 42 twice → identical F AND X matrices."""
    r1 = run_optimisation(n_gen=20, pop_size=30, seed=42)
    r2 = run_optimisation(n_gen=20, pop_size=30, seed=42)

    F1, F2 = np.atleast_2d(r1.F), np.atleast_2d(r2.F)
    X1, X2 = np.atleast_2d(r1.X), np.atleast_2d(r2.X)

    assert F1.shape == F2.shape, f"F shapes differ: {F1.shape} vs {F2.shape}"
    assert np.array_equal(F1, F2), "seed 42 produced different F across runs"
    assert X1.shape == X2.shape, f"X shapes differ: {X1.shape} vs {X2.shape}"
    assert np.array_equal(X1, X2), "seed 42 produced different X across runs"


def test_seed_determinism_different_seed_differs():
    """Different seed (7) must produce a DIFFERENT front than seed 42.

    Proves the seed actually drives the RNG (not a hard-coded result).
    """
    r_a = run_optimisation(n_gen=20, pop_size=30, seed=42)
    r_b = run_optimisation(n_gen=20, pop_size=30, seed=7)

    F_a, F_b = np.atleast_2d(r_a.F), np.atleast_2d(r_b.F)
    # Different shape OR different contents both prove divergence.
    differs = (F_a.shape != F_b.shape) or (not np.array_equal(F_a, F_b))
    assert differs, "seed 7 produced an identical front to seed 42 — seed is ignored"


def test_naive_baseline_is_valid_and_deterministic():
    """naive_baseline_config: deterministic, valid placements, round-robin species."""
    cfg1 = naive_baseline_config()
    cfg2 = naive_baseline_config()

    # Deterministic
    coords1 = [(t["x_m"], t["y_m"]) for t in cfg1["trees"]]
    coords2 = [(t["x_m"], t["y_m"]) for t in cfg2["trees"]]
    assert coords1 == coords2, "naive_baseline_config is not deterministic"

    # Exactly N_TREES slots, at least one active, all active ones valid
    assert len(cfg1["trees"]) == N_TREES
    assert cfg1["tree_count"] >= 1, "naive grid produced zero valid trees"
    for t in cfg1["trees"]:
        if t["active"]:
            assert is_valid_location(t["x_m"], t["y_m"]), (
                f"active naive tree at ({t['x_m']:.1f}, {t['y_m']:.1f}) is not valid"
            )


def test_naive_baseline_present_and_improvement_finite(tmp_path, real_result):
    """Artifact carries baseline_naive + a finite improvement_vs_naive_pct on rank-1."""
    import json
    import math

    top3 = select_top3(real_result)
    budget = SimBudget(max_live_calls=3)
    top3 = validate_top3_with_infrared(top3, budget=budget)
    top3 = topsis_rank(top3)

    json_path = save_outputs(top3, real_result, out_dir=tmp_path)
    artifact = json.loads(json_path.read_text(encoding="utf-8"))

    assert "baseline_naive" in artifact, "artifact missing baseline_naive block"
    naive = artifact["baseline_naive"]
    assert naive.get("label") == "NAIVE_GRID"
    assert naive.get("tree_count", 0) >= 1
    assert naive.get("delta_utci_c") is not None

    assert "improvement_vs_naive_pct" in artifact, "missing improvement_vs_naive_pct"
    improvement = artifact["improvement_vs_naive_pct"]
    assert improvement is not None, "improvement_vs_naive_pct is None"
    assert math.isfinite(improvement), f"improvement not finite: {improvement}"

    # rank-1 config also carries the field
    assert artifact["configurations"][0].get("improvement_vs_naive_pct") == improvement


def test_select_top3_always_returns_three():
    """select_top3 returns exactly 3 entries even on a tiny/near-degenerate run."""
    result = run_optimisation(n_gen=3, pop_size=6, seed=42)
    top3 = select_top3(result)
    assert len(top3) == 3, f"Expected exactly 3 configs, got {len(top3)}"
    ranks = [c["rank"] for c in top3]
    assert ranks == [1, 2, 3], f"Ranks must be 1,2,3: {ranks}"
    labels = [c["label"] for c in top3]
    assert len(set(labels)) == 3, f"Labels must be distinct (incl. padded): {labels}"


# ── WAVE-2 REMEDIATION: baseline geometry tests ───────────────────────────────


def test_baseline_geometry_has_polygon_lonlat():
    """_build_baseline_geometry returns a non-empty polygon_lonlat key.

    On the live backend, _live_utci requires 'polygon_lonlat' (or 'polygon_local_m')
    to build a WGS84 GeoJSON payload; passing {} raises ValueError (no polygon keys).
    This test verifies that the baseline geometry is never the empty dict that caused
    that crash (Fix 1 — Code Reviewer M-4, HIGH).
    """
    geom = _build_baseline_geometry()

    assert "polygon_lonlat" in geom, (
        "_build_baseline_geometry must include 'polygon_lonlat' for the live path"
    )
    assert isinstance(geom["polygon_lonlat"], list), "polygon_lonlat must be a list"
    assert len(geom["polygon_lonlat"]) >= 4, (
        f"polygon_lonlat ring too short: {len(geom['polygon_lonlat'])} points"
    )
    # Closed ring: first == last
    assert geom["polygon_lonlat"][0] == geom["polygon_lonlat"][-1], (
        "polygon_lonlat ring must be closed (first == last point)"
    )
    # Zero coverage — open-site baseline has no canopy
    assert geom["width_m"] == 0.0, "baseline geometry must have width_m=0"
    assert geom["coverage_fraction"] == 0.0, "baseline geometry must have coverage_fraction=0"


def test_validate_top3_calls_get_baseline_utci_with_nonempty_geometry(
    monkeypatch, top3_configs
):
    """validate_top3_with_infrared calls get_baseline_utci with non-empty geometry.

    Before Fix 1, get_baseline_utci was called with {} (empty dict). On the live
    backend that causes a ValueError inside _live_utci (no polygon key). This test
    records what geometry is passed and asserts it is not the empty dict.
    """
    import coolspend.sdk_client as sdk_module

    captured_geoms: list[dict] = []

    original_get_baseline = sdk_module.get_baseline_utci

    def _capture_baseline(geometry: dict):
        captured_geoms.append(geometry)
        return original_get_baseline(geometry)

    monkeypatch.setattr(sdk_module, "get_baseline_utci", _capture_baseline)
    monkeypatch.delenv("INFRARED_BACKEND", raising=False)

    budget = SimBudget(max_live_calls=3)
    validate_top3_with_infrared(list(top3_configs), budget=budget)

    assert len(captured_geoms) >= 1, "get_baseline_utci was not called"
    for geom in captured_geoms:
        assert geom != {}, (
            "get_baseline_utci was called with empty geometry {}; "
            "this would crash the live backend (no polygon key). "
            "Use _build_baseline_geometry() instead."
        )
        assert "polygon_lonlat" in geom, (
            f"baseline geometry missing 'polygon_lonlat' key: {list(geom.keys())}"
        )
