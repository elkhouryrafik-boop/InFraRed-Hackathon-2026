"""
cost_model.py — Per-tree CapEx + OpEx cost model and euro-per-degC KPI.

CoolSpend — Tree Budget Optimizer (infrared.city SDK Buildathon, Tree Budget track)

Purpose:
    Computes the headline decision metric: euros of tree-planting investment per
    degree Celsius of UTCI street-comfort relief.  This KPI drives the NSGA-II
    ranking in Phase 2 and the allocation display cards in Phase 3.

Constant status:
    CAPEX_PER_TREE_EUR, OPEX_PER_TREE_YEAR_EUR, and OPEX_HORIZON_YEARS are
    DECLARED assumptions (urban street-tree midrange estimates).  They are
    NOT independently verified figures.  Each carries a
    # SOURCE: REQUIRES_VERIFICATION comment.  See MOCKS.md for the ledger row.

Key functions:
    per_tree_cost(horizon_years) -> float          euros per tree over horizon
    total_cost(config)           -> float          total euros for config
    cost_per_utci_degree(config) -> dict           standard metric dict EUR/degC
"""
from __future__ import annotations

from typing import Any

# ── Confidence constants ──────────────────────────────────────────────────────
HIGH = "HIGH"
MED  = "MED"
LOW  = "LOW"

# ── CapEx / OpEx constants (DECLARED assumptions — COST-01) ──────────────────
#
# These are midrange estimates for urban street-tree planting programmes.
# Each value is a DECLARED assumption pending sourcing from municipal data.
# Do NOT present these as verified figures.
#
# SOURCE: REQUIRES_VERIFICATION — no municipal procurement data confirmed yet.
# See MOCKS.md row "CapEx/OpEx tree cost constants".

CAPEX_PER_TREE_EUR: float = 350.0
# planting: nursery stock + labour + initial irrigation (DECLARED assumption,
# urban street-tree midrange, e.g. Madrid / Barcelona municipal programmes)
# UNIT: EUR per tree   SOURCE: REQUIRES_VERIFICATION

OPEX_PER_TREE_YEAR_EUR: float = 35.0
# annual maintenance: watering, pruning, inspection (DECLARED assumption)
# UNIT: EUR per tree per year   SOURCE: REQUIRES_VERIFICATION

OPEX_HORIZON_YEARS: int = 10
# amortisation horizon for OpEx in the headline KPI (DECLARED assumption)
# UNIT: years   SOURCE: REQUIRES_VERIFICATION

# ── Internal source tag used in every result dict ─────────────────────────────
_COST_SOURCE = "DECLARED: CapEx/OpEx assumptions (REQUIRES_VERIFICATION)"


# ── Public API ────────────────────────────────────────────────────────────────

def per_tree_cost(horizon_years: int = OPEX_HORIZON_YEARS) -> float:
    """
    Return the total lifecycle cost per tree over *horizon_years*.

    Cost = CAPEX_PER_TREE_EUR + OPEX_PER_TREE_YEAR_EUR * horizon_years.

    With horizon_years=0 only the CapEx (planting cost) is returned; no OpEx
    is amortised.  Uses the module-level DECLARED constants — see module
    docstring for honesty status.

    Returns a finite positive float in EUR.
    """
    return CAPEX_PER_TREE_EUR + OPEX_PER_TREE_YEAR_EUR * horizon_years


def total_cost(config: dict[str, Any]) -> float:
    """
    Return the total planting + maintenance cost for all trees in *config*.

    Reads tree_count = int(config.get("tree_count", 0)).
    If tree_count <= 0 returns 0.0.

    Returns a finite non-negative float in EUR.
    """
    tree_count = int(config.get("tree_count", 0))
    if tree_count <= 0:
        return 0.0
    return tree_count * per_tree_cost()


def cost_per_utci_degree(config: dict[str, Any]) -> dict[str, Any]:
    """
    Return the headline euro-per-degC KPI for *config* as a standard metric dict.

    Determines the UTCI delta by preference order:
        1. config["delta_utci_c"]  — validated UTCI delta, confidence MED or HIGH
        2. config["delta_tmrt_c"]  — surrogate Tmrt proxy, confidence LOW with note

    Zero / negative delta guard (T-01-10 / Rule 6 honest framing):
        If delta is None, absent, or <= 0 the KPI cannot be computed without
        fabricating a misleading number.  Returns value=None with confidence LOW
        and an explanatory note rather than dividing.

    Returns a standard metric dict:
        value:      float | None   EUR/degC (None if delta <= 0 or missing)
        unit:       "EUR/degC"
        confidence: HIGH | MED | LOW
        sources:    [_COST_SOURCE]
        note:       str
        metric_id:  "cost_per_utci_degree"
    """
    # Determine delta and confidence level
    delta: float | None = config.get("delta_utci_c")
    using_surrogate = False
    note_parts: list[str] = []

    if delta is None:
        # Fall back to Tmrt surrogate if available
        delta = config.get("delta_tmrt_c")
        if delta is not None:
            using_surrogate = True
            note_parts.append(
                "surrogate delta used (delta_utci_c absent) — "
                "replace with validated UTCI for a defensible KPI"
            )

    # Guard: non-positive or missing delta (T-01-10)
    if delta is None or delta <= 0:
        if delta is None:
            note_parts.append(
                "delta_utci_c and delta_tmrt_c both absent — "
                "cannot compute EUR/degC KPI without a UTCI delta"
            )
        else:
            note_parts.append(
                f"non-positive UTCI delta ({delta} degC) — "
                "KPI undefined; a zero or negative delta means no comfort gain"
            )
        return {
            "value": None,
            "unit": "EUR/degC",
            "confidence": LOW,
            "sources": [_COST_SOURCE],
            "note": "; ".join(note_parts) if note_parts else "non-positive or missing delta",
            "metric_id": "cost_per_utci_degree",
        }

    # Compute KPI
    cost = total_cost(config)
    value = round(cost / delta, 2)

    # Confidence: HIGH only if delta came from validated delta_utci_c (not surrogate)
    confidence = LOW if using_surrogate else MED

    return {
        "value": value,
        "unit": "EUR/degC",
        "confidence": confidence,
        "sources": [_COST_SOURCE],
        "note": "; ".join(note_parts) if note_parts else "",
        "metric_id": "cost_per_utci_degree",
    }


# ── Smoke test / integration sample ──────────────────────────────────────────

if __name__ == "__main__":
    import json

    sample_config = {"tree_count": 20, "delta_utci_c": 0.42}

    print("=== cost_model.py smoke test ===")
    print(f"per_tree_cost()        = {per_tree_cost():.2f} EUR")
    print(f"per_tree_cost(0)       = {per_tree_cost(0):.2f} EUR  (CapEx only)")
    print(f"total_cost(20 trees)   = {total_cost(sample_config):.2f} EUR")
    print()
    result = cost_per_utci_degree(sample_config)
    print("cost_per_utci_degree result:")
    print(json.dumps(result, indent=2))
    print()

    # Demonstrate zero-delta guard
    zero_delta_result = cost_per_utci_degree({"tree_count": 10, "delta_utci_c": 0.0})
    print("Zero-delta guard result:")
    print(json.dumps(zero_delta_result, indent=2))
