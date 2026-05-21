"""
coolspend.optimizer — NSGA-II tree-budget multi-objective optimizer (OPT-01 + OPT-03).

Two objectives (PROJECT.md "Ship as 2-objective" decision):
  F1 = -thermal_relief(config)       maximize cooling     (spatial_engine surrogate)
  F2 = -ecological_score(config)     maximize coherence   (rules_engine)

One budget constraint:
  G1 = total_cost(config) - budget_eur <= 0   (reject / penalise over-budget configs)

Hot path is SURROGATE-ONLY — zero live SDK calls during optimization.
SDK (SimBudget-guarded) is called exactly 3 times in validate_top3_with_infrared().

HONESTY NOTICE:
  thermal_relief() and delta_tmrt_surrogate() are ANALYTICAL PROXIES, not measured
  or simulated results. Uncertainty ±4°C. MAX_TMRT_REDUCTION_C=12°C is unsourced.
  Top-3 surrogate estimates are replaced by labelled real/mock UTCI deltas via
  validate_top3_with_infrared (OPT-03). See MOCKS.md and spatial_engine.py docstring.

SEED: 42 — deterministic run.
PERFORMANCE: POP_SIZE=60, N_GEN=60 gives a qualitative Pareto front in tens of
seconds offline on an analytical surrogate (CONCERNS 3.5).
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.termination import get_termination
from pymoo.optimize import minimize

from coolspend.spatial_engine import (
    is_valid_location,
    local_m_to_latlon,
    thermal_relief,
    SITE_WIDTH_M,
    SITE_DEPTH_M,
    TREE_CANOPY_RADIUS_M,
)
from coolspend.rules_engine import ecological_score
from coolspend.cost_model import total_cost

# SDK imports are at the BOTTOM of this module (validate_top3_with_infrared only).
# DO NOT import sdk_client at the top level — the hot path must be SDK-free.

# ── OPTIMIZER CONSTANTS ───────────────────────────────────────────────────────

N_TREES: int = 12
"""Fixed-length candidate vector: 12 tree slots (each has x_m, y_m => 24 decision vars)."""

DEFAULT_BUDGET_EUR: float = 1_000_000.0
"""Default planting budget in euros ("one million euros for canopy")."""

SPECIES: tuple[str, ...] = ("platanus", "celtis", "tilia", "quercus")
"""Species palette cycled round-robin per slot index."""

SEED: int = 42
"""Deterministic seed — pins the Pareto front across runs with identical problem."""

POP_SIZE: int = 60
"""Population size. 60 gives a good Pareto spread in tens of seconds (CONCERNS 3.5)."""

N_GEN: int = 60
"""Number of NSGA-II generations. 60 × 60 = 3 600 evals on a pure-Python surrogate."""


# ── CHROMOSOME DECODER ───────────────────────────────────────────────────────


def decode(x_flat: np.ndarray) -> dict:
    """Decode a flat chromosome of length 2*N_TREES into a tree configuration dict.

    The chromosome is a flat vector [x0, y0, x1, y1, ..., x_{N-1}, y_{N-1}].
    Each pair (x_i, y_i) defines a candidate tree slot.  A slot is "active" iff
    is_valid_location(x_m, y_m) returns True (i.e. inside boundary, not in a
    building or on a street centerline).  Inactive slots still appear in
    config["trees"] with active=False so decode is invertible / fully determinstic.

    Species are assigned round-robin from SPECIES by slot index.

    Returns:
        {
          "trees": [{"x_m":.., "y_m":.., "species":.., "active": bool}, ...],
          "tree_count": int,   # count of active (valid) slots
        }
    """
    trees = []
    for i in range(N_TREES):
        x_m = float(x_flat[2 * i])
        y_m = float(x_flat[2 * i + 1])
        species = SPECIES[i % len(SPECIES)]
        active = is_valid_location(x_m, y_m)
        trees.append({"x_m": x_m, "y_m": y_m, "species": species, "active": active})

    tree_count = sum(1 for t in trees if t["active"])
    return {"trees": trees, "tree_count": tree_count}


# ── PROBLEM DEFINITION ───────────────────────────────────────────────────────


class TreeBudgetProblem(ElementwiseProblem):
    """NSGA-II problem: 2 objectives (thermal + ecological) + budget constraint.

    Decision variables: flat vector of 2*N_TREES floats.
      x_i in [0, SITE_WIDTH_M]   (East-West position of tree slot i)
      y_i in [0, SITE_DEPTH_M]   (North-South position of tree slot i)

    Objectives (both minimised — standard pymoo convention):
      F[0] = -thermal_relief(cfg)      maximize site-averaged ΔTmrt surrogate
      F[1] = -ecological_score(cfg)    maximize ecological coherence score

    Constraint (inequality, must be <= 0 for feasibility):
      G[0] = total_cost(cfg) - budget_eur   (positive => over budget => infeasible)

    The _evaluate() method calls ONLY the analytical surrogate (thermal_relief +
    ecological_score). No sdk_client import or call appears here (CONCERNS 3.1 /
    T-02-11). SimBudget-guarded SDK calls happen only in validate_top3_with_infrared.
    """

    def __init__(self, budget_eur: float = DEFAULT_BUDGET_EUR) -> None:
        xl = np.zeros(2 * N_TREES)
        xu = np.tile([SITE_WIDTH_M, SITE_DEPTH_M], N_TREES)
        super().__init__(n_var=2 * N_TREES, n_obj=2, n_ieq_constr=1, xl=xl, xu=xu)
        self.budget_eur = budget_eur

    def _evaluate(self, x: np.ndarray, out: dict, *args, **kwargs) -> None:
        """Evaluate a single chromosome. SURROGATE-ONLY — no SDK calls here."""
        cfg = decode(x)

        # Objective F1: maximize thermal relief => minimize negative
        f1 = -thermal_relief(cfg)

        # Objective F2: maximize ecological coherence => minimize negative
        f2 = -ecological_score(cfg)

        # Constraint G1: over-budget configs are infeasible (G > 0)
        g1 = total_cost(cfg) - self.budget_eur

        out["F"] = [f1, f2]
        out["G"] = [g1]


# ── OPTIMIZER ENTRY POINT ────────────────────────────────────────────────────


def run_optimisation(
    budget_eur: float = DEFAULT_BUDGET_EUR,
    pop_size: int = POP_SIZE,
    n_gen: int = N_GEN,
    seed: int = SEED,
):
    """Run NSGA-II on the TreeBudgetProblem and return the pymoo Result.

    Uses SBX crossover (prob=0.9, eta=15), PM mutation (eta=20),
    FloatRandomSampling, eliminate_duplicates=True — ported from
    nature_nsga2_coolstock.py lines 255-273 (adapted for tree coordinates).

    The hot path calls ONLY the surrogate — zero live SDK calls.
    After this function returns, call select_top3() then validate_top3_with_infrared()
    to get the three real/mock UTCI-validated configurations.

    Args:
        budget_eur:  Planting budget in euros (default 1 000 000).
        pop_size:    NSGA-II population size (default 60).
        n_gen:       Number of generations (default 60).
        seed:        RNG seed for deterministic runs (default 42).

    Returns:
        pymoo Result object.  result.F: objective matrix, result.X: decision vars.
    """
    problem = TreeBudgetProblem(budget_eur=budget_eur)

    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
        eliminate_duplicates=True,
    )

    termination = get_termination("n_gen", n_gen)

    result = minimize(
        problem,
        algorithm,
        termination,
        seed=seed,
        verbose=False,
        save_history=False,
    )
    return result


# ── TOP-3 SELECTION ──────────────────────────────────────────────────────────


def select_top3(result) -> list[dict]:
    """Select 3 representative configurations from the Pareto front.

    Representatives:
      rank 1 — MAX_THERMAL_RELIEF: best thermal performance (min F[:,0])
      rank 2 — MAX_ECOLOGICAL:     best ecological coherence (min F[:,1])
      rank 3 — BALANCED:           closest to utopia point (L2 of normalised F)

    Deduplication: if two indices coincide, the while-loop extends with the next
    closest-to-utopia index (ported from nature_nsga2_coolstock.py lines 321-327).

    Each config dict carries:
      rank, label, delta_tmrt_c, delta_tmrt_uncertainty_c, delta_tmrt_source,
      ecological_score, surrogate_note, topsis_score (None — filled by Plan 02-05).

    Args:
        result: pymoo Result from run_optimisation().

    Returns:
        List of exactly 3 decoded+labelled config dicts.
    """
    F = np.atleast_2d(result.F)   # shape (n_pareto, 2): [-thermal, -ecological]
    X = result.X

    # Best per objective
    idx1 = int(np.argmin(F[:, 0]))   # MAX_THERMAL_RELIEF
    idx2 = int(np.argmin(F[:, 1]))   # MAX_ECOLOGICAL

    # Balanced: closest to utopia point in normalised objective space
    f_min = F.min(axis=0)
    f_max = F.max(axis=0)
    F_norm = (F - f_min) / (f_max - f_min + 1e-9)
    idx3 = int(np.argmin(np.linalg.norm(F_norm, axis=1)))

    # Deduplicate to 3 distinct indices
    indices: list[int] = list(dict.fromkeys([idx1, idx2, idx3]))
    sorted_by_utopia = list(np.argsort(np.linalg.norm(F_norm, axis=1)))
    ptr = 0
    while len(indices) < 3 and len(indices) < len(F):
        candidate = int(sorted_by_utopia[ptr])
        ptr += 1
        if candidate not in indices:
            indices.append(candidate)

    labels = ["MAX_THERMAL_RELIEF", "MAX_ECOLOGICAL", "BALANCED"]
    configs = []
    for rank_zero, idx in enumerate(indices[:3]):
        cfg = decode(X[idx])
        thermal = thermal_relief(cfg)
        eco = ecological_score(cfg)

        cfg["rank"] = rank_zero + 1
        cfg["label"] = labels[rank_zero]
        cfg["delta_tmrt_c"] = round(thermal, 3)
        cfg["delta_tmrt_uncertainty_c"] = 4.0
        cfg["delta_tmrt_source"] = (
            "analytical surrogate (Garcia-Nevado 2020 surface-temp proxy, "
            "not Tmrt@1.1m)"
        )
        cfg["ecological_score"] = round(eco, 4)
        cfg["surrogate_note"] = (
            "Analytical proxy — validated below with real Infrared UTCI"
        )
        cfg["topsis_score"] = None   # filled in Plan 02-05

        configs.append(cfg)

    return configs


# ── GEOMETRY BUILDER FOR SDK ──────────────────────────────────────────────────


def _config_to_geometry(cfg: dict) -> dict:
    """Build the SDK geometry payload for a tree configuration.

    Computes coverage_fraction from active-tree canopy footprints (capped at 0.9)
    and includes width_m so the mock intervention model applies cooling.
    Includes polygon_lonlat for the live path via local_m_to_latlon (SPATIAL-03).

    Args:
        cfg: Tree config dict from decode() / select_top3().

    Returns:
        Geometry dict suitable for get_intervention_utci(geometry).
    """
    active = [t for t in cfg.get("trees", []) if t.get("active", True)]
    site_area_m2 = SITE_WIDTH_M * SITE_DEPTH_M

    # Coverage fraction: sum of canopy footprints, capped at 0.9
    tree_shade_area_m2 = math.pi * TREE_CANOPY_RADIUS_M ** 2
    total_shaded_m2 = len(active) * tree_shade_area_m2
    coverage_fraction = min(total_shaded_m2 / site_area_m2, 0.9)

    # width_m: representative width of the canopy cluster (bounding box EW span)
    if active:
        xs = [t["x_m"] for t in active]
        width_m = max(xs) - min(xs) + 2 * TREE_CANOPY_RADIUS_M
    else:
        width_m = 0.0

    # Site boundary polygon in lon/lat (SPATIAL-03 — single CRS conversion point)
    polygon_lonlat = [
        list(local_m_to_latlon(0.0, 0.0)),
        list(local_m_to_latlon(SITE_WIDTH_M, 0.0)),
        list(local_m_to_latlon(SITE_WIDTH_M, SITE_DEPTH_M)),
        list(local_m_to_latlon(0.0, SITE_DEPTH_M)),
        list(local_m_to_latlon(0.0, 0.0)),   # closed ring
    ]

    return {
        "width_m": round(width_m, 2),
        "coverage_fraction": round(coverage_fraction, 4),
        "polygon_lonlat": polygon_lonlat,
        "tree_count": cfg.get("tree_count", len(active)),
    }


# ── TOP-3 VALIDATION (OPT-03) ────────────────────────────────────────────────


def validate_top3_with_infrared(
    top3: list[dict],
    budget: "SimBudget | None" = None,   # type: ignore[name-defined]
) -> list[dict]:
    """Validate Top-3 surrogate configs with real (or mock) Infrared UTCI calls.

    Calls the SDK exactly 3 times — once per Top-3 config — guarded by SimBudget.
    Each call is a get_intervention_utci on the tree-placement geometry.
    Baseline is fetched once (without recording against the budget cap) so the
    headline 3 budget slots are the 3 intervention calls.

    Attaches to each config:
      baseline_utci_c       — open-site UTCI (mock/live)
      validated_utci_c      — post-intervention UTCI (mock/live)
      delta_utci_c          — round(baseline - validated, 2) in °C
      validated_backend     — "mock" | "cached" | "live"
      validated_disclaimer  — honesty string from UTCIResult

    Works offline (INFRARED_BACKEND=mock, default) and with the real API
    (INFRARED_BACKEND=live, requires INFRARED_API_KEY from May 27).

    Args:
        top3:   List of 3 config dicts from select_top3().
        budget: SimBudget(max_live_calls=3). Created internally if None.

    Returns:
        Updated top3 list with validated UTCI fields attached to each config.

    Raises:
        RuntimeError: if more than 3 intervention calls are attempted (SimBudget).
    """
    # SDK imports here only — never at module top level (hot-path isolation)
    from coolspend.sdk_client import get_baseline_utci, get_intervention_utci, SimBudget  # noqa: PLC0415

    if budget is None:
        budget = SimBudget(max_live_calls=3)

    # Baseline: open-site geometry — no budget record (baseline is pre-intervention)
    site_geometry: dict = {}   # empty geometry -> mock returns 41.0 °C baseline
    baseline = get_baseline_utci(site_geometry)

    for cfg in top3:
        label = cfg.get("label", f"config_{cfg.get('rank', '?')}")
        budget.record(f"intervention {label}")

        geom = _config_to_geometry(cfg)
        intervention = get_intervention_utci(geom)

        cfg["baseline_utci_c"] = baseline.utci_c
        cfg["validated_utci_c"] = intervention.utci_c
        cfg["delta_utci_c"] = round(baseline.utci_c - intervention.utci_c, 2)
        cfg["validated_backend"] = intervention.backend
        cfg["validated_disclaimer"] = intervention.disclaimer

    return top3


# ── MAIN ENTRY POINT ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    print(f"Running NSGA-II optimizer (seed={SEED}, pop={POP_SIZE}, gen={N_GEN})")
    print(f"Backend: {os.environ.get('INFRARED_BACKEND', 'mock')}")
    print()

    result = run_optimisation()
    F = np.atleast_2d(result.F)
    print(f"Pareto front size: {len(F)}")

    top3 = select_top3(result)
    print(f"\nTop-3 configs (surrogate):")
    for cfg in top3:
        print(
            f"  [{cfg['rank']}] {cfg['label']:20s} "
            f"thermal={cfg['delta_tmrt_c']:.2f}°C  "
            f"eco={cfg['ecological_score']:.4f}  "
            f"trees={cfg['tree_count']}"
        )

    print("\nValidating Top-3 with Infrared SDK...")
    validated = validate_top3_with_infrared(top3)
    for cfg in validated:
        print(
            f"  [{cfg['rank']}] {cfg['label']:20s} "
            f"delta_utci={cfg['delta_utci_c']:.2f}°C  "
            f"backend={cfg['validated_backend']}"
        )
