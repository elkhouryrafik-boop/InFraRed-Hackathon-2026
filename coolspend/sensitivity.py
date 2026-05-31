"""
coolspend/sensitivity.py — robustness checks for the ranking decision.

The audit flagged two adjustable, non-calibrated knobs that feed the headline
pick: the TOPSIS weights (default 0.6 thermal / 0.4 ecological) and the fact
that the *published* rank is actually decided by the €/°C primary key with
TOPSIS only as a tie-break. A defensible recommendation must show the rank-1
pick does not flip when those knobs move within plausible ranges.

This module is PURE ANALYSIS over already-evaluated configurations — it never
re-runs a simulation and makes no network calls. It answers two questions:

  1. closeness_weight_sweep: if we ranked purely by TOPSIS closeness, how often
     does the same configuration win as the thermal/ecological weight sweeps
     across the simplex? (Measures how weight-sensitive a closeness ranking is.)

  2. primary_key_invariance: under the ACTUAL decision rule (ascending €/°C,
     TOPSIS tie-break), is the rank-1 pick invariant to the weights? It is,
     unless two configs tie on €/°C — this quantifies and confirms that.

Each config is expected to carry: delta_utci_c, ecological_score, and
cost_per_utci_degree (a dict with a numeric "value", as attached by
optimizer.topsis_rank / cost_model.cost_per_utci_degree).
"""
from __future__ import annotations

from typing import Any

import numpy as np


def _config_label(cfg: dict[str, Any], idx: int) -> str:
    return str(cfg.get("label") or cfg.get("rank") or f"config_{idx}")


def _performance_matrix(configs: list[dict[str, Any]]) -> np.ndarray:
    """[delta_utci_c, ecological_score] per config — both higher-is-better.

    Mirrors optimizer.topsis_rank exactly so the sweep is consistent with the
    production ranking maths.
    """
    return np.array(
        [
            [float(c.get("delta_utci_c") or 0.0), float(c.get("ecological_score", 0.0))]
            for c in configs
        ],
        dtype=float,
    )


def _closeness(matrix: np.ndarray, weights: tuple[float, float]) -> np.ndarray:
    """TOPSIS relative closeness per row for a 2-criteria matrix + weights.

    Identical normalisation/closeness to optimizer.topsis_rank (Hwang & Yoon).
    """
    norms = np.linalg.norm(matrix, axis=0)
    norms[norms == 0] = 1e-9
    weighted = (matrix / norms) * np.array(weights, dtype=float)
    ideal_best = weighted.max(axis=0)
    ideal_worst = weighted.min(axis=0)
    d_best = np.linalg.norm(weighted - ideal_best, axis=1)
    d_worst = np.linalg.norm(weighted - ideal_worst, axis=1)
    denom = d_best + d_worst
    denom[denom == 0] = 1e-9
    return d_worst / denom


def closeness_weight_sweep(
    configs: list[dict[str, Any]],
    n_steps: int = 21,
) -> dict[str, Any]:
    """Sweep w_thermal over [0, 1] (w_eco = 1 − w_thermal) and, for each weight,
    record which config wins on TOPSIS closeness alone.

    Returns a summary dict:
      - n_steps
      - modal_winner:       label that wins most often across the sweep
      - modal_winner_share: fraction of the sweep the modal winner takes (1.0 = never flips)
      - flips:              True if more than one distinct config ever wins
      - winners_by_weight:  [{w_thermal, w_ecological, winner}] compact trace
    """
    if not configs:
        return {"n_steps": n_steps, "modal_winner": None, "modal_winner_share": 0.0,
                "flips": False, "winners_by_weight": []}

    matrix = _performance_matrix(configs)
    trace: list[dict[str, Any]] = []
    tally: dict[str, int] = {}
    for w_t in np.linspace(0.0, 1.0, n_steps):
        w = (float(w_t), float(1.0 - w_t))
        closeness = _closeness(matrix, w)
        winner_idx = int(np.argmax(closeness))
        label = _config_label(configs[winner_idx], winner_idx)
        tally[label] = tally.get(label, 0) + 1
        trace.append({"w_thermal": round(w[0], 4), "w_ecological": round(w[1], 4), "winner": label})

    modal_winner = max(tally, key=tally.get)
    return {
        "n_steps": n_steps,
        "modal_winner": modal_winner,
        "modal_winner_share": round(tally[modal_winner] / n_steps, 4),
        "flips": len(tally) > 1,
        "winners_by_weight": trace,
    }


def primary_key_invariance(configs: list[dict[str, Any]]) -> dict[str, Any]:
    """Confirm the PUBLISHED rank-1 (ascending €/°C) is invariant to TOPSIS weights.

    The production rule sorts by cost_per_utci_degree value ascending and uses
    TOPSIS only to break exact €/°C ties. So the rank-1 pick depends on the
    weights only when the two best configs tie on €/°C. This returns:
      - rank1_by_primary:    label with the lowest €/°C
      - weight_invariant:    True if no other config ties its €/°C (weights cannot change rank-1)
      - min_kpi_gap:         smallest gap between the best and 2nd-best €/°C (0.0 => a tie exists)
    """
    kpis: list[tuple[float, str]] = []
    for idx, c in enumerate(configs):
        kpi = (c.get("cost_per_utci_degree") or {})
        val = kpi.get("value") if isinstance(kpi, dict) else kpi
        if isinstance(val, (int, float)):
            kpis.append((float(val), _config_label(c, idx)))

    if not kpis:
        return {"rank1_by_primary": None, "weight_invariant": True, "min_kpi_gap": None}

    kpis.sort(key=lambda t: t[0])
    rank1 = kpis[0][1]
    gap = round(kpis[1][0] - kpis[0][0], 6) if len(kpis) > 1 else float("inf")
    return {
        "rank1_by_primary": rank1,
        "weight_invariant": gap != 0.0,
        "min_kpi_gap": gap if gap != float("inf") else None,
    }


def rank_sensitivity_report(
    configs: list[dict[str, Any]],
    n_steps: int = 21,
) -> dict[str, Any]:
    """Combined robustness summary for the decision narrative.

    A defensible headline pick is one where weight_invariant is True (the €/°C
    winner cannot be unseated by reweighting) OR the closeness modal_winner is
    stable across the sweep. Surfaces both so the limitation is explicit rather
    than hidden.
    """
    sweep = closeness_weight_sweep(configs, n_steps=n_steps)
    invariance = primary_key_invariance(configs)
    return {
        "method": "TOPSIS weight sweep + €/°C primary-key invariance (offline, no re-sim)",
        "closeness_weight_sweep": sweep,
        "primary_key_invariance": invariance,
        "verdict": (
            "rank-1 invariant to TOPSIS weights (decided by €/°C primary key)"
            if invariance["weight_invariant"]
            else "rank-1 can flip — best two configs tie on €/°C; weights decide"
        ),
    }
