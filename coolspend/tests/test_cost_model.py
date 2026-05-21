"""
test_cost_model.py — Deterministic offline tests for cost_model.py.

Tests cover:
    - CapEx-only per_tree_cost (COST-01)
    - CapEx + OpEx composition over horizon (COST-01)
    - total_cost scaling by tree count (COST-01)
    - EUR/degC KPI value and dict shape (COST-02)
    - Surrogate delta fallback flagged as LOW confidence (COST-02)
    - Zero and negative delta guard — value=None, no exception (COST-02)
    - Standard metric-dict key completeness (CONVENTIONS.md)

All tests are pure arithmetic, fully offline, deterministic.  No API key needed.
"""
from __future__ import annotations

import pytest

from coolspend.cost_model import (
    CAPEX_PER_TREE_EUR,
    OPEX_HORIZON_YEARS,
    OPEX_PER_TREE_YEAR_EUR,
    cost_per_utci_degree,
    per_tree_cost,
    total_cost,
)


# ── per_tree_cost tests (COST-01) ────────────────────────────────────────────

def test_per_tree_cost_capex_only() -> None:
    """horizon_years=0 returns exactly CAPEX_PER_TREE_EUR — no OpEx added."""
    assert per_tree_cost(0) == CAPEX_PER_TREE_EUR


def test_per_tree_cost_includes_opex() -> None:
    """Default horizon adds OpEx on top of CapEx — result is strictly larger."""
    assert per_tree_cost() > CAPEX_PER_TREE_EUR
    expected = CAPEX_PER_TREE_EUR + OPEX_PER_TREE_YEAR_EUR * OPEX_HORIZON_YEARS
    assert per_tree_cost() == pytest.approx(expected)


# ── total_cost tests (COST-01) ───────────────────────────────────────────────

@pytest.mark.parametrize("n", [0, 1, 25])
def test_total_cost_scales(n: int) -> None:
    """total_cost scales linearly with tree_count for n in {0, 1, 25}."""
    result = total_cost({"tree_count": n})
    expected = n * per_tree_cost()
    assert result == pytest.approx(expected)


# ── cost_per_utci_degree tests (COST-02) ─────────────────────────────────────

def test_cost_per_degree_value() -> None:
    """Positive delta_utci_c produces value == total_cost/delta, unit EUR/degC,
    and confidence in {MED, HIGH}."""
    config = {"tree_count": 10, "delta_utci_c": 0.5}
    result = cost_per_utci_degree(config)

    expected_value = round(total_cost(config) / 0.5, 2)
    assert result["value"] == pytest.approx(expected_value)
    assert result["unit"] == "EUR/degC"
    assert result["confidence"] in {"MED", "HIGH"}
    assert result["metric_id"] == "cost_per_utci_degree"


def test_surrogate_fallback_flagged() -> None:
    """Config with only delta_tmrt_c (no delta_utci_c) yields confidence LOW
    and a note containing the word 'surrogate'."""
    config = {"tree_count": 5, "delta_tmrt_c": 1.2}
    result = cost_per_utci_degree(config)

    assert result["confidence"] == "LOW"
    assert "surrogate" in result["note"].lower()
    # Value is still computed — it is not None when delta > 0
    assert result["value"] is not None
    assert result["value"] > 0


def test_nonpositive_delta_guarded_zero() -> None:
    """delta_utci_c == 0 returns value=None without raising."""
    result = cost_per_utci_degree({"tree_count": 10, "delta_utci_c": 0.0})
    assert result["value"] is None
    assert result["confidence"] == "LOW"


def test_nonpositive_delta_guarded_negative() -> None:
    """delta_utci_c < 0 returns value=None without raising."""
    result = cost_per_utci_degree({"tree_count": 10, "delta_utci_c": -0.3})
    assert result["value"] is None
    assert result["confidence"] == "LOW"


# ── Standard metric-dict shape (CONVENTIONS.md) ───────────────────────────────

def test_returns_standard_metric_dict() -> None:
    """Result always contains the mandatory standard-dict keys."""
    required_keys = {"value", "unit", "confidence", "sources", "note", "metric_id"}
    config = {"tree_count": 3, "delta_utci_c": 0.7}
    result = cost_per_utci_degree(config)
    assert required_keys.issubset(result.keys())
    assert result["unit"] == "EUR/degC"
    assert result["metric_id"] == "cost_per_utci_degree"
    assert isinstance(result["sources"], list)
