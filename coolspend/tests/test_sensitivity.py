"""Offline tests for coolspend/sensitivity.py — pure ranking-robustness analysis."""
from __future__ import annotations

from coolspend import sensitivity


def _cfgs(kpi_a=1000.0, kpi_b=2000.0, kpi_c=1500.0):
    return [
        {"label": "A", "delta_utci_c": 2.0, "ecological_score": 0.3,
         "cost_per_utci_degree": {"value": kpi_a}},
        {"label": "B", "delta_utci_c": 1.0, "ecological_score": 0.9,
         "cost_per_utci_degree": {"value": kpi_b}},
        {"label": "C", "delta_utci_c": 1.5, "ecological_score": 0.6,
         "cost_per_utci_degree": {"value": kpi_c}},
    ]


def test_closeness_sweep_flips_between_thermal_and_ecological_extremes():
    sweep = sensitivity.closeness_weight_sweep(_cfgs(), n_steps=11)
    assert sweep["n_steps"] == 11
    # all-thermal weight → A (highest delta) wins; all-ecological → B wins.
    first = sweep["winners_by_weight"][0]   # w_thermal = 0 → ecological
    last = sweep["winners_by_weight"][-1]   # w_thermal = 1 → thermal
    assert first["winner"] == "B"
    assert last["winner"] == "A"
    assert sweep["flips"] is True
    assert 0.0 < sweep["modal_winner_share"] <= 1.0


def test_primary_key_invariance_distinct_kpis():
    inv = sensitivity.primary_key_invariance(_cfgs())
    assert inv["rank1_by_primary"] == "A"        # lowest €/°C = 1000
    assert inv["weight_invariant"] is True       # no tie on €/°C
    assert inv["min_kpi_gap"] == 500.0           # 1500 − 1000


def test_primary_key_invariance_detects_tie():
    # A and C both at €/°C = 1000 → a tie exists, weights can decide rank-1.
    inv = sensitivity.primary_key_invariance(_cfgs(kpi_a=1000.0, kpi_c=1000.0))
    assert inv["min_kpi_gap"] == 0.0
    assert inv["weight_invariant"] is False


def test_report_combines_both_and_emits_verdict():
    rep = sensitivity.rank_sensitivity_report(_cfgs(), n_steps=5)
    assert "closeness_weight_sweep" in rep
    assert "primary_key_invariance" in rep
    assert "invariant to TOPSIS weights" in rep["verdict"]


def test_empty_configs_safe():
    assert sensitivity.closeness_weight_sweep([])["modal_winner"] is None
    assert sensitivity.primary_key_invariance([])["rank1_by_primary"] is None
