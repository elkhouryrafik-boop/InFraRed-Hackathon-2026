"""
Temporary RED-phase test for cost_model.py — Task 1 TDD gate.

These tests import cost_model which does not exist yet, so they will fail with
ImportError (RED). Once cost_model.py is implemented (GREEN) this file is
superseded by the full test_cost_model.py and can be removed.
"""
from coolspend.cost_model import (
    per_tree_cost,
    total_cost,
    cost_per_utci_degree,
    CAPEX_PER_TREE_EUR,
)


def test_per_tree_cost_capex_only() -> None:
    assert per_tree_cost(0) == CAPEX_PER_TREE_EUR


def test_zero_delta_returns_none() -> None:
    result = cost_per_utci_degree({"tree_count": 5, "delta_utci_c": 0.0})
    assert result["value"] is None
