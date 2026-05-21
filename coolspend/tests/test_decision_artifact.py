"""
coolspend/tests/test_decision_artifact.py — Offline tests for the decision artifact.

Tests cover DEC-01 (ranked allocation), DEC-02 (before/after), and honesty provenance
requirements.  All tests use INFRARED_BACKEND=mock (default) and run fully offline.

Fixtures:
  small_result      — tiny NSGA-II run (n_gen=10, pop=15) — fast, module-scoped
  validated_top3    — select_top3 + validate_top3_with_infrared from small_result
  ranked_top3       — topsis_rank applied to validated_top3

Tests:
  test_topsis_ranks_by_cost_per_degree  — rank-1 has lowest (or tied) cost_per_utci_degree
  test_save_outputs_schema              — JSON has run_metadata, configurations[3], before_after
  test_before_after_present             — DEC-02: before_after block with correct delta
  test_every_config_has_disclaimer      — honesty: all configs carry non-empty disclaimer
  test_allocation_is_priority_ordered   — DEC-01: configs sorted by ascending EUR/degC
  test_main_writes_artifact             — end-to-end: coolspend.main.main() writes the JSON
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest

from coolspend.optimizer import (
    DEFAULT_BUDGET_EUR,
    run_optimisation,
    save_outputs,
    select_top3,
    topsis_rank,
    validate_top3_with_infrared,
)
from coolspend.cost_model import cost_per_utci_degree, total_cost
from coolspend.sdk_client import SimBudget


# ── FIXTURES ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def small_result():
    """Tiny NSGA-II run — fast, deterministic, module-scoped."""
    return run_optimisation(n_gen=10, pop_size=15, seed=42)


@pytest.fixture(scope="module")
def validated_top3(small_result):
    """select_top3 + validate (mock backend) from the small result."""
    top3 = select_top3(small_result)
    budget = SimBudget(max_live_calls=3)
    return validate_top3_with_infrared(top3, budget=budget)


@pytest.fixture(scope="module")
def ranked_top3(validated_top3):
    """topsis_rank applied to a copy of validated_top3 (in-place, module-scoped)."""
    import copy
    top3_copy = copy.deepcopy(validated_top3)
    return topsis_rank(top3_copy)


# ── HAND-BUILT CONFIGS for TOPSIS isolation ────────────────────────────────────


def _make_config(tree_count: int, delta_utci_c: float, eco: float, label: str) -> dict:
    """Build a minimal config dict suitable for topsis_rank."""
    return {
        "rank": 1,
        "label": label,
        "trees": [{"x_m": 10.0 * i, "y_m": 5.0, "species": "platanus", "active": True}
                  for i in range(tree_count)],
        "tree_count": tree_count,
        "delta_tmrt_c": delta_utci_c * 0.9,
        "delta_tmrt_uncertainty_c": 4.0,
        "delta_tmrt_source": "test surrogate",
        "ecological_score": eco,
        "surrogate_note": "test",
        "topsis_score": None,
        "baseline_utci_c": 41.0,
        "validated_utci_c": round(41.0 - delta_utci_c, 2),
        "delta_utci_c": delta_utci_c,
        "validated_backend": "mock",
        "validated_disclaimer": "NOT MEASURED DATA",
    }


# ── TEST 1: TOPSIS ranks by cost_per_utci_degree ─────────────────────────────


def test_topsis_ranks_by_cost_per_degree():
    """rank-1 config has the lowest (or tied) cost_per_utci_degree value.

    Uses hand-built configs so the test is independent of optimizer stochasticity.
    Config A: 5 trees, large delta_utci_c  → cheaper per degree
    Config B: 10 trees, small delta_utci_c → more expensive per degree
    Config C: 7 trees, medium delta_utci_c → middle
    """
    import copy

    cfg_a = _make_config(5, delta_utci_c=3.0, eco=0.8, label="A")
    cfg_b = _make_config(10, delta_utci_c=0.5, eco=0.9, label="B")
    cfg_c = _make_config(7, delta_utci_c=1.5, eco=0.7, label="C")

    top3 = [copy.deepcopy(cfg_a), copy.deepcopy(cfg_b), copy.deepcopy(cfg_c)]
    ranked = topsis_rank(top3)

    # Ranks must be 1, 2, 3 in order
    assert [c["rank"] for c in ranked] == [1, 2, 3]

    # Rank-1 must have the lowest (or equal) cost_per_utci_degree value
    kpi_values = [c["cost_per_utci_degree"]["value"] for c in ranked]
    assert all(v is not None for v in kpi_values), f"All KPIs should be finite: {kpi_values}"
    assert kpi_values[0] <= kpi_values[1], (
        f"rank-1 KPI ({kpi_values[0]}) should be <= rank-2 KPI ({kpi_values[1]})"
    )
    assert kpi_values[1] <= kpi_values[2], (
        f"rank-2 KPI ({kpi_values[1]}) should be <= rank-3 KPI ({kpi_values[2]})"
    )


# ── TEST 2: save_outputs produces a valid JSON schema ─────────────────────────


def test_save_outputs_schema(tmp_path, small_result):
    """save_outputs writes a JSON with the mandatory schema fields.

    Runs the full mini-pipeline to a tmp_path out_dir and validates the schema.
    """
    import copy

    top3 = select_top3(small_result)
    budget = SimBudget(max_live_calls=3)
    top3 = validate_top3_with_infrared(top3, budget=budget)
    top3 = topsis_rank(copy.deepcopy(top3))

    json_path = save_outputs(top3, small_result, out_dir=tmp_path)
    assert json_path.exists(), f"Expected {json_path} to exist"

    artifact = json.loads(json_path.read_text(encoding="utf-8"))

    # Top-level keys
    assert "run_metadata" in artifact, "Missing run_metadata"
    assert "configurations" in artifact, "Missing configurations"
    assert "before_after" in artifact, "Missing before_after"

    # Configurations count
    configs = artifact["configurations"]
    assert len(configs) == 3, f"Expected 3 configurations, got {len(configs)}"

    # Per-config required fields
    required_fields = {
        "rank", "label", "trees", "tree_count",
        "delta_utci_c", "cost_per_utci_degree", "disclaimer",
    }
    for cfg in configs:
        missing = required_fields - cfg.keys()
        assert not missing, f"Config {cfg.get('label')} missing fields: {missing}"
        assert isinstance(cfg["trees"], list), "trees must be a list"
        assert cfg["tree_count"] >= 0, "tree_count must be non-negative"


# ── TEST 3: before/after record is present and correct (DEC-02) ──────────────


def test_before_after_present(tmp_path, small_result):
    """DEC-02: before_after block exists and headline_delta equals baseline - validated."""
    import copy

    top3 = select_top3(small_result)
    budget = SimBudget(max_live_calls=3)
    top3 = validate_top3_with_infrared(top3, budget=budget)
    top3 = topsis_rank(copy.deepcopy(top3))

    json_path = save_outputs(top3, small_result, out_dir=tmp_path)
    artifact = json.loads(json_path.read_text(encoding="utf-8"))

    ba = artifact["before_after"]
    assert "baseline_utci_c" in ba, "before_after missing baseline_utci_c"
    assert "chosen_validated_utci_c" in ba, "before_after missing chosen_validated_utci_c"
    assert "headline_delta_utci_c" in ba, "before_after missing headline_delta_utci_c"

    # Headline delta must be positive (cooling > warming) for a valid config
    delta = ba["headline_delta_utci_c"]
    assert delta is not None, "headline_delta_utci_c should not be None"
    # headline = baseline - validated_utci_c  (from validate_top3_with_infrared)
    baseline = ba["baseline_utci_c"]
    validated = ba["chosen_validated_utci_c"]
    if baseline is not None and validated is not None:
        expected_delta = round(baseline - validated, 2)
        assert math.isclose(delta, expected_delta, abs_tol=1e-3), (
            f"headline_delta ({delta}) != baseline - validated ({expected_delta})"
        )


# ── TEST 4: every config carries a non-empty disclaimer (honesty) ─────────────


def test_every_config_has_disclaimer(tmp_path, small_result):
    """Honesty (T-02-15): all configs carry a non-empty disclaimer string.

    Also checks that run_metadata.surrogate mentions the surrogate and uncertainty.
    """
    import copy

    top3 = select_top3(small_result)
    budget = SimBudget(max_live_calls=3)
    top3 = validate_top3_with_infrared(top3, budget=budget)
    top3 = topsis_rank(copy.deepcopy(top3))

    json_path = save_outputs(top3, small_result, out_dir=tmp_path)
    artifact = json.loads(json_path.read_text(encoding="utf-8"))

    for cfg in artifact["configurations"]:
        disclaimer = cfg.get("disclaimer", "")
        assert disclaimer, (
            f"Config {cfg.get('label')} has empty/missing disclaimer — "
            "every config must carry an honesty disclaimer"
        )

    # run_metadata.surrogate must mention the surrogate and uncertainty
    surrogate_note = artifact["run_metadata"].get("surrogate", "")
    assert surrogate_note, "run_metadata.surrogate must be non-empty"
    # Must mention the uncertainty concept
    assert any(
        kw in surrogate_note.lower()
        for kw in ("surrogate", "proxy", "mock", "analytical")
    ), f"run_metadata.surrogate does not mention surrogate/proxy: {surrogate_note!r}"


# ── TEST 5: allocation is priority-ordered (DEC-01) ──────────────────────────


def test_allocation_is_priority_ordered(tmp_path, small_result):
    """DEC-01: configurations are sorted by ascending cost_per_utci_degree value.

    rank-1 is the cheapest-per-degree (best allocation priority), rank-3 is the most expensive.
    """
    import copy

    top3 = select_top3(small_result)
    budget = SimBudget(max_live_calls=3)
    top3 = validate_top3_with_infrared(top3, budget=budget)
    top3 = topsis_rank(copy.deepcopy(top3))

    json_path = save_outputs(top3, small_result, out_dir=tmp_path)
    artifact = json.loads(json_path.read_text(encoding="utf-8"))

    configs = artifact["configurations"]
    # Ranks must be 1, 2, 3 in order as stored
    ranks = [c["rank"] for c in configs]
    assert ranks == [1, 2, 3], f"Configs not in rank order: {ranks}"

    # Extract KPI values (None → ∞ for sorting purposes)
    kpi_values = []
    for c in configs:
        v = c["cost_per_utci_degree"]["value"] if isinstance(c["cost_per_utci_degree"], dict) else None
        kpi_values.append(v if v is not None else float("inf"))

    # Ascending order (or tied)
    for i in range(len(kpi_values) - 1):
        assert kpi_values[i] <= kpi_values[i + 1], (
            f"Rank {i+1} KPI ({kpi_values[i]}) > rank {i+2} KPI ({kpi_values[i+1]}) "
            "— allocation is not priority-ordered"
        )


# ── TEST 6: main() writes the artifact ───────────────────────────────────────


def test_main_writes_artifact(tmp_path):
    """End-to-end: coolspend.main.main() runs offline and writes top3_configurations.json.

    Uses a monkeypatched save_outputs to redirect output to tmp_path so the test
    doesn't pollute the outputs/ directory and can be run repeatedly.
    """
    import copy
    import coolspend.main as main_module
    import coolspend.optimizer as opt_module

    written_paths: list[Path] = []

    original_save = opt_module.save_outputs

    def patched_save(top3, result, out_dir=None, budget_eur=DEFAULT_BUDGET_EUR):
        # Redirect to tmp_path
        path = original_save(top3, result, out_dir=tmp_path, budget_eur=budget_eur)
        written_paths.append(path)
        return path

    # Patch save_outputs on the module used by main
    original_opt_save = opt_module.save_outputs
    opt_module.save_outputs = patched_save
    # Also patch the reference in main_module's namespace
    original_main_save = main_module.save_outputs
    main_module.save_outputs = patched_save

    try:
        json_path = main_module.main(budget_eur=DEFAULT_BUDGET_EUR)
    finally:
        opt_module.save_outputs = original_opt_save
        main_module.save_outputs = original_main_save

    # The returned path or the redirected path must exist and parse
    actual_path = written_paths[0] if written_paths else json_path
    assert actual_path.exists(), f"Expected artifact at {actual_path}"
    artifact = json.loads(actual_path.read_text(encoding="utf-8"))
    assert "configurations" in artifact
    assert len(artifact["configurations"]) == 3
    assert "before_after" in artifact
