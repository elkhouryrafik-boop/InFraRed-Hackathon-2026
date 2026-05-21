"""
coolspend/main.py — End-to-end CLI for the CoolSpend tree-budget optimizer.

Runs the full pipeline offline (mock backend by default) and writes the decision
artifact to outputs/top3_configurations.json (DEC-01 + DEC-02).

Offline run (no API key needed):
    INFRARED_BACKEND=mock python -m coolspend.main
    -- or simply --
    python -m coolspend.main   (mock is the default)

Live run (requires API key, available from May 27 2026):
    INFRARED_BACKEND=live INFRARED_API_KEY=<your-key> python -m coolspend.main

Pipeline stages:
  1. run_optimisation()           — NSGA-II on analytical surrogate (seed 42)
  2. select_top3()                — 3 Pareto representatives (thermal, ecological, balanced)
  3. validate_top3_with_infrared()— mock/live UTCI validation (SimBudget cap: 3 calls)
  4. topsis_rank()                — re-rank by €/°C KPI (TOPSIS tie-break)
  5. save_outputs()               — write top3_configurations.json, audit_record.json,
                                    pareto_front.png

DISCLAIMER: all thermal values (delta_tmrt_c, topsis_score) are SURROGATE-DERIVED
with ±4°C uncertainty. validated_utci_c is a mock synthetic value with the mock
backend — NOT MEASURED DATA. Use INFRARED_BACKEND=live after May 27 for real UTCI.
"""
from __future__ import annotations

import os
from pathlib import Path

from coolspend.optimizer import (
    DEFAULT_BUDGET_EUR,
    N_GEN,
    POP_SIZE,
    SEED,
    run_optimisation,
    save_outputs,
    select_top3,
    topsis_rank,
    validate_top3_with_infrared,
)
from coolspend.sdk_client import SimBudget


def main(budget_eur: float = DEFAULT_BUDGET_EUR) -> Path:
    """Run the full CoolSpend pipeline and write the decision artifact.

    Steps:
      1. Run NSGA-II optimizer on the surrogate (seed 42, no live SDK calls).
      2. Select 3 representative Pareto configs.
      3. Validate each with the Infrared SDK (mock by default; live with API key).
      4. Rank by €/°C KPI (TOPSIS tie-break).
      5. Save outputs to outputs/ directory.

    Args:
        budget_eur: Planting budget in EUR (default: DEFAULT_BUDGET_EUR).

    Returns:
        Path to the written top3_configurations.json file.
    """
    backend = os.environ.get("INFRARED_BACKEND", "mock")

    print("=" * 60)
    print("CoolSpend - Tree Budget Optimizer")
    print(f"  Backend:    {backend}")
    print(f"  Budget:     EUR {budget_eur:,.0f}")
    print(f"  Seed:       {SEED}  |  Pop: {POP_SIZE}  |  Gen: {N_GEN}")
    print("=" * 60)
    print()

    # ── Stage 1: NSGA-II optimization on surrogate ────────────────────────────
    print("Stage 1/5  Running NSGA-II optimizer (surrogate hot path)...")
    result = run_optimisation(budget_eur=budget_eur)
    import numpy as np
    F = np.atleast_2d(result.F)
    print(f"           Pareto front: {len(F)} configurations")
    print()

    # ── Stage 2: Select Top-3 representatives ────────────────────────────────
    print("Stage 2/5  Selecting Top-3 Pareto representatives...")
    top3 = select_top3(result)
    for cfg in top3:
        print(
            f"           [{cfg['rank']}] {cfg['label']:20s}  "
            f"thermal={cfg['delta_tmrt_c']:.2f}degC  "
            f"eco={cfg['ecological_score']:.4f}  "
            f"trees={cfg['tree_count']}"
        )
    print()

    # ── Stage 3: Validate with Infrared SDK (mock/cached/live) ────────────────
    print(f"Stage 3/5  Validating Top-3 with Infrared SDK (backend={backend})...")
    budget = SimBudget(max_live_calls=3)
    top3 = validate_top3_with_infrared(top3, budget=budget)
    for cfg in top3:
        print(
            f"           [{cfg['rank']}] {cfg['label']:20s}  "
            f"delta_utci={cfg['delta_utci_c']:.2f}degC  "
            f"backend={cfg['validated_backend']}"
        )
    print()

    # ── Stage 4: TOPSIS ranking by EUR/degC ───────────────────────────────────
    print("Stage 4/5  Ranking by EUR/degC KPI (TOPSIS tie-break)...")
    top3 = topsis_rank(top3)
    for cfg in top3:
        kpi = cfg["cost_per_utci_degree"]["value"]
        kpi_str = f"EUR {kpi:,.0f}/degC" if kpi is not None else "N/A"
        print(
            f"           Rank {cfg['rank']}: {cfg['label']:20s}  "
            f"cost={kpi_str}  "
            f"topsis={cfg['topsis_score']:.4f}  "
            f"trees={cfg['tree_count']}"
        )
    print()

    # ── Stage 5: Save outputs ─────────────────────────────────────────────────
    print("Stage 5/5  Writing decision artifact...")
    json_path = save_outputs(top3, result, budget_eur=budget_eur)
    print(f"           Written: {json_path}")
    print()

    # ── Human summary ─────────────────────────────────────────────────────────
    before_after = {
        "baseline_utci_c": top3[0].get("baseline_utci_c"),
        "chosen_label": top3[0].get("label"),
        "headline_delta_utci_c": top3[0].get("delta_utci_c"),
    }
    print("-" * 60)
    print("DECISION SUMMARY (DEC-01 + DEC-02)")
    print("-" * 60)
    print(
        f"  Before (baseline UTCI):  {before_after['baseline_utci_c']} degC"
    )
    best = top3[0]
    kpi = best["cost_per_utci_degree"]["value"]
    kpi_str = f"EUR {kpi:,.0f}/degC" if kpi is not None else "N/A"
    print(
        f"  After  (rank-1 UTCI):    {best.get('validated_utci_c')} degC  "
        f"(delta = {before_after['headline_delta_utci_c']:.2f} degC)"
    )
    print(f"  Best allocation:         {best['label']} ({best['tree_count']} trees)")
    print(f"  EUR/degC KPI:            {kpi_str}")
    print()
    print(
        "DISCLAIMER: all surrogate metrics (delta_tmrt_c, topsis_score) carry "
        "+/-4 degC uncertainty."
    )
    if backend == "mock":
        print(
            "  validated_utci_c is a MOCK synthetic value - NOT MEASURED DATA."
        )
        print(
            "  Use INFRARED_BACKEND=live INFRARED_API_KEY=<key> after May 27 for real UTCI."
        )
    print("-" * 60)
    print()

    return json_path


if __name__ == "__main__":
    main()
