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

Decision artifact functions (Plan 02-05):
  topsis_rank(top3, weights)  — rank validated Top-3 by €/°C (TOPSIS tie-break)
  save_outputs(top3, result)  — write top3_configurations.json, audit_record.json,
                                pareto_front.png  (DEC-01 + DEC-02)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

logger = logging.getLogger("coolspend.optimizer")

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.termination import get_termination
from pymoo.optimize import minimize

from coolspend.spatial_engine import (
    core_weighted_coverage_fraction,
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

    # First pass: fill from distinct Pareto points (closest-to-utopia order).
    ptr = 0
    while len(indices) < 3 and ptr < len(sorted_by_utopia):
        candidate = int(sorted_by_utopia[ptr])
        ptr += 1
        if candidate not in indices:
            indices.append(candidate)

    # GUARANTEE EXACTLY 3 (REMEDIATION fix #4): if the unique Pareto front is
    # smaller than 3 distinct points (e.g. a near-degenerate run), pad
    # DETERMINISTICALLY by repeating the best-thermal index. Padded slots are
    # relabelled with an explicit "(duplicate of …)" note so the artifact never
    # silently presents a repeated config as a genuinely distinct alternative.
    padded_slots: set[int] = set()
    while len(indices) < 3:
        padded_slots.add(len(indices))
        indices.append(idx1)

    labels = ["MAX_THERMAL_RELIEF", "MAX_ECOLOGICAL", "BALANCED"]
    configs = []
    for rank_zero, idx in enumerate(indices[:3]):
        cfg = decode(X[idx])
        thermal = thermal_relief(cfg)
        eco = ecological_score(cfg)

        cfg["rank"] = rank_zero + 1
        if rank_zero in padded_slots:
            # Distinct, honest label for a padded (duplicate) slot.
            cfg["label"] = f"{labels[rank_zero]}_DUP{rank_zero + 1}"
            cfg["padded_duplicate"] = True
            cfg["padding_note"] = (
                "Pareto front had < 3 distinct points; this slot duplicates the "
                "best-thermal config to guarantee exactly 3 entries (REMEDIATION fix #4)."
            )
        else:
            cfg["label"] = labels[rank_zero]
            cfg["padded_duplicate"] = False
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


# ── NAIVE BASELINE (REMEDIATION fix #3) ───────────────────────────────────────


def naive_baseline_config() -> dict:
    """Build a DETERMINISTIC naive tree placement for honest before/after framing.

    The naive strategy is what a planner might do WITHOUT the optimizer: drop
    N_TREES on an evenly-spaced rectangular grid spanning the site, keeping only
    the grid points that pass is_valid_location (inside boundary, not in a building,
    off the street buffer). Species are assigned round-robin from SPECIES, exactly
    as decode() does, so the comparison is apples-to-apples on the SAME backend.

    Fully deterministic (no RNG): the grid is a fixed function of N_TREES and the
    site dimensions. This is the "do-nothing-clever" reference the optimizer is
    measured against (improvement_vs_naive_pct), NOT a competing recommendation.

    Returns:
        A config dict in the same shape as decode():
        {"trees": [...], "tree_count": int}.
    """
    # Choose a near-square grid covering N_TREES slots.
    n_cols = int(np.ceil(np.sqrt(N_TREES)))
    n_rows = int(np.ceil(N_TREES / n_cols))

    # Evenly space grid points with a margin so points are not on the boundary.
    margin_x = SITE_WIDTH_M / (n_cols + 1)
    margin_y = SITE_DEPTH_M / (n_rows + 1)

    trees: list[dict] = []
    for i in range(N_TREES):
        col = i % n_cols
        row = i // n_cols
        x_m = margin_x * (col + 1)
        y_m = margin_y * (row + 1)
        species = SPECIES[i % len(SPECIES)]
        active = is_valid_location(x_m, y_m)
        trees.append(
            {"x_m": float(x_m), "y_m": float(y_m), "species": species, "active": active}
        )

    tree_count = sum(1 for t in trees if t["active"])
    return {"trees": trees, "tree_count": tree_count}


def _build_naive_baseline(budget: "SimBudget | None" = None) -> dict:  # type: ignore[name-defined]
    """Validate the naive placement and return its baseline block for the artifact.

    Computes the naive placement (naive_baseline_config), runs the SAME mock/live
    UTCI validation path used for the Top-3 (so the comparison is honest and on the
    same backend), and computes its euro/°C KPI.

    A separate SimBudget is used so the naive validation does not consume the
    Top-3 SimBudget cap (the headline 3 live slots remain the 3 Top-3 calls).

    Returns:
        {
          "label": "NAIVE_GRID",
          "tree_count": int,
          "delta_utci_c": float,
          "validated_utci_c": float,
          "baseline_utci_c": float,
          "cost_eur": float,
          "cost_per_utci_degree": float | None,
          "validated_backend": str,
          "note": str,
        }
    """
    from coolspend.sdk_client import get_baseline_utci, get_intervention_utci, SimBudget  # noqa: PLC0415
    from coolspend.cost_model import cost_per_utci_degree, total_cost  # noqa: PLC0415

    if budget is None:
        budget = SimBudget(max_live_calls=1)

    cfg = naive_baseline_config()
    cfg["delta_tmrt_c"] = round(thermal_relief(cfg), 3)
    cfg["ecological_score"] = round(ecological_score(cfg), 4)

    baseline = get_baseline_utci(_build_baseline_geometry())
    budget.record("intervention NAIVE_GRID")
    geom = _config_to_geometry(cfg)
    intervention = get_intervention_utci(geom)

    cfg["baseline_utci_c"] = baseline.utci_c
    cfg["validated_utci_c"] = intervention.utci_c
    cfg["delta_utci_c"] = round(baseline.utci_c - intervention.utci_c, 2)
    cfg["validated_backend"] = intervention.backend

    kpi = cost_per_utci_degree(cfg)
    return {
        "label": "NAIVE_GRID",
        "tree_count": cfg["tree_count"],
        "delta_utci_c": cfg["delta_utci_c"],
        "validated_utci_c": cfg["validated_utci_c"],
        "baseline_utci_c": cfg["baseline_utci_c"],
        "cost_eur": round(total_cost(cfg), 2),
        "cost_per_utci_degree": kpi.get("value"),
        "validated_backend": cfg["validated_backend"],
        "note": (
            "Deterministic evenly-spaced grid placement (no optimizer). Honest "
            "reference for improvement_vs_naive_pct; SAME backend as Top-3."
        ),
    }


# ── GEOMETRY BUILDER FOR SDK ──────────────────────────────────────────────────


def _config_to_geometry(cfg: dict) -> dict:
    """Build the SDK geometry payload for a tree configuration.

    Computes coverage_fraction from the SAME core-weighted non-overlapping canopy
    union used by thermal_relief (core_weighted_coverage_fraction, capped at
    MAX_SITE_COVERAGE) and includes width_m so the mock intervention model applies
    cooling. Using the IDENTICAL coverage model keeps the mock UTCI consistent with
    the surrogate objective (REMEDIATION Option A).
    Includes polygon_lonlat for the live path via local_m_to_latlon (SPATIAL-03).

    Args:
        cfg: Tree config dict from decode() / select_top3().

    Returns:
        Geometry dict suitable for get_intervention_utci(geometry).
    """
    active = [t for t in cfg.get("trees", []) if t.get("active", True)]

    # Coverage fraction: SAME core-weighted canopy union used by thermal_relief
    # (spatial_engine.core_weighted_coverage_fraction). This makes the mock UTCI —
    # which reads coverage_fraction — placement-sensitive AND consistent with the
    # surrogate objective, so the Top-3 configs differ on mock instead of
    # collapsing to one value (REMEDIATION Option A).
    coverage_fraction = core_weighted_coverage_fraction(active)

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


# ── BASELINE GEOMETRY BUILDER ─────────────────────────────────────────────────


def _build_baseline_geometry() -> dict:
    """Build the open-site (no-trees) geometry for the baseline UTCI call.

    Returns the same site polygon ring that _config_to_geometry produces for
    interventions, but with coverage_fraction=0 and width_m=0 (no canopy).

    On the mock backend, the mock ignores polygon_lonlat and reads only width_m
    (0 → returns 41.0 °C baseline), so mock behaviour is unchanged.

    On the live backend, _live_utci requires 'polygon_lonlat' to build the
    WGS84 GeoJSON payload; passing {} causes a ValueError (no polygon keys) —
    this function supplies the required polygon so the live baseline call works.

    Returns:
        {
          "width_m": 0.0,
          "coverage_fraction": 0.0,
          "tree_count": 0,
          "polygon_lonlat": [...],   # closed WGS84 ring of the site boundary
        }
    """
    polygon_lonlat = [
        list(local_m_to_latlon(0.0, 0.0)),
        list(local_m_to_latlon(SITE_WIDTH_M, 0.0)),
        list(local_m_to_latlon(SITE_WIDTH_M, SITE_DEPTH_M)),
        list(local_m_to_latlon(0.0, SITE_DEPTH_M)),
        list(local_m_to_latlon(0.0, 0.0)),   # closed ring
    ]
    return {
        "width_m": 0.0,
        "coverage_fraction": 0.0,
        "tree_count": 0,
        "polygon_lonlat": polygon_lonlat,
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

    # Baseline: real site polygon with no trees/canopy.
    # Using _build_baseline_geometry() ensures the live path has a valid
    # polygon_lonlat (preventing ValueError in _live_utci) while keeping mock
    # behaviour identical (mock reads only width_m=0 → returns 41.0 °C).
    site_geometry = _build_baseline_geometry()
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


# ── TOPSIS RANKING (DEC-01 / Plan 02-05) ────────────────────────────────────


def topsis_rank(
    top3: list[dict],
    weights: tuple[float, float] = (0.6, 0.4),
) -> list[dict]:
    """Rank validated Top-3 configs by euro/°C KPI, using TOPSIS as tie-breaker.

    IMPORTANT — weights are ADJUSTABLE USER PARAMETERS, not stakeholder-derived
    constants.  They will be exposed as Gradio sliders in Phase 3.  Do NOT present
    them as calibrated values (ARCHITECTURE.md Known Issues #3 / CONCERNS 1.6).

    Ranking procedure (Hwang & Yoon 1981, adapted):
      1. Build a 3×2 performance matrix:
           column 0 = delta_utci_c  (validated thermal relief, higher is better)
           column 1 = ecological_score (higher is better)
      2. Vector-normalise each column (guard zero-norms with 1e-9).
      3. Apply weights.
      4. Identify ideal-best (column max) and ideal-worst (column min).
      5. Euclidean distance from ideal-best and ideal-worst per row.
      6. Relative closeness = D_worst / (D_best + D_worst).
      7. Set cfg["topsis_score"] = round(closeness, 4).

    PRIMARY ranking criterion: cfg["cost_per_utci_degree"]["value"] ascending
    (best euros-per-degree first).  TOPSIS closeness is used as a tie-breaker.
    Configs with cost_per_utci_degree value=None are ranked last.

    After ranking, each config receives:
      cfg["rank"]                   — 1, 2, or 3 (1 = best euro/°C)
      cfg["cost_eur"]               — total_cost(cfg) in EUR
      cfg["cost_per_utci_degree"]   — standard metric dict from cost_model
      cfg["topsis_score"]           — TOPSIS relative closeness (0–1)

    Args:
        top3:    List of 3 configs from validate_top3_with_infrared().
        weights: (w_thermal, w_ecological) — must be positive, needn't sum to 1.

    Returns:
        The same list (in-place modified), re-sorted by ascending euro/°C with
        ranks reassigned 1..3.
    """
    from coolspend.cost_model import cost_per_utci_degree, total_cost  # noqa: PLC0415

    # Attach cost fields to each config
    for cfg in top3:
        cfg["cost_eur"] = round(total_cost(cfg), 2)
        cfg["cost_per_utci_degree"] = cost_per_utci_degree(cfg)

    # ── TOPSIS ────────────────────────────────────────────────────────────────
    # Performance matrix: [delta_utci_c, ecological_score] — both higher is better
    matrix = np.array(
        [
            [float(cfg.get("delta_utci_c") or 0.0), float(cfg.get("ecological_score", 0.0))]
            for cfg in top3
        ],
        dtype=float,
    )

    # Vector-normalise (guard zero norms)
    norms = np.linalg.norm(matrix, axis=0)
    norms[norms == 0] = 1e-9
    norm_matrix = matrix / norms

    # Apply weights
    w = np.array(weights, dtype=float)
    weighted = norm_matrix * w

    # Ideal best (max each column) and worst (min each column)
    ideal_best = weighted.max(axis=0)
    ideal_worst = weighted.min(axis=0)

    # Euclidean distances
    d_best = np.linalg.norm(weighted - ideal_best, axis=1)
    d_worst = np.linalg.norm(weighted - ideal_worst, axis=1)

    # Relative closeness
    denom = d_best + d_worst
    denom[denom == 0] = 1e-9
    closeness = d_worst / denom

    for i, cfg in enumerate(top3):
        cfg["topsis_score"] = round(float(closeness[i]), 4)

    # ── PRIMARY SORT: ascending euro/°C (None last), tie-break: desc TOPSIS ──
    def _sort_key(cfg: dict):
        kpi = cfg["cost_per_utci_degree"]["value"]
        # None → sort to end; otherwise ascending cost, descending topsis
        if kpi is None:
            return (1, 0.0, -cfg["topsis_score"])
        return (0, float(kpi), -cfg["topsis_score"])

    top3.sort(key=_sort_key)

    # Reassign ranks 1..3
    for rank_zero, cfg in enumerate(top3):
        cfg["rank"] = rank_zero + 1

    return top3


# ── BEFORE/AFTER RECORD (DEC-02 / Plan 02-05) ────────────────────────────────


def _build_before_after(top3: list[dict]) -> dict:
    """Build the DEC-02 before/after record from the rank-1 (best euro/°C) config.

    Returns a dict with:
      baseline_utci_c          — open-site UTCI before intervention
      chosen_label             — label of the selected config
      chosen_validated_utci_c  — post-intervention UTCI (mock or live)
      headline_delta_utci_c    — comfort improvement in °C (positive = better)
      source                   — backend / disclaimer string
      note                     — human-readable interpretation
    """
    chosen = top3[0]   # rank-1: best euro/°C after topsis_rank()
    return {
        "baseline_utci_c": chosen.get("baseline_utci_c"),
        "chosen_label": chosen.get("label"),
        "chosen_validated_utci_c": chosen.get("validated_utci_c"),
        "headline_delta_utci_c": chosen.get("delta_utci_c"),
        "source": chosen.get("validated_disclaimer", chosen.get("validated_backend")),
        "note": "before = baseline UTCI; after = chosen intervention validated UTCI",
    }


# ── SAVE OUTPUTS (DEC-01 + DEC-02 / Plan 02-05) ──────────────────────────────


def _result_pop_size(result) -> int:
    """Return the configured NSGA-II population size for run_metadata.

    Reads the real population size off the pymoo Result's algorithm
    (result.algorithm.pop_size) when available, falling back to the module
    POP_SIZE constant. Replaces the previous dead expression
    `int(getattr(result, "algorithm", None) and 0 or POP_SIZE)`, which always
    evaluated to POP_SIZE because the `and 0` short-circuited to 0 → `0 or POP_SIZE`
    (REMEDIATION fix #5 — dead expression).
    """
    algorithm = getattr(result, "algorithm", None)
    pop_size = getattr(algorithm, "pop_size", None)
    if isinstance(pop_size, int) and pop_size > 0:
        return pop_size
    return POP_SIZE


def save_outputs(
    top3: list[dict],
    result,
    out_dir: Path = Path("outputs"),
    budget_eur: float = DEFAULT_BUDGET_EUR,
) -> Path:
    """Write the decision artifact, audit record, and Pareto PNG to *out_dir*.

    Fulfils DEC-01 (ranked allocation) and DEC-02 (before/after record).
    Every config is guaranteed to carry a non-empty "disclaimer" key (honesty).

    Files written:
      outputs/top3_configurations.json  — DEC-01 + DEC-02 main artifact
      outputs/audit_record.json         — provenance trail
      outputs/pareto_front.png          — Pareto scatter (best-effort; pipeline
                                          continues if matplotlib is unavailable)

    Args:
        top3:       Ranked Top-3 configs from topsis_rank().
        result:     pymoo Result from run_optimisation() — needed for metadata.
        out_dir:    Output directory (created if absent).
        budget_eur: Planting budget used in this run (for run_metadata).

    Returns:
        Path to the written top3_configurations.json file.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    F = np.atleast_2d(result.F)

    # Ensure every config carries a "disclaimer" key (T-02-15 honesty)
    surrogate_disclaimer = (
        "SURROGATE-DERIVED — delta_tmrt from analytical proxy (±4°C uncertainty). "
        "validated_utci_c is mock backend (NOT MEASURED DATA) until INFRARED_BACKEND=live. "
        "See MOCKS.md."
    )
    for cfg in top3:
        if not cfg.get("disclaimer"):
            # Use the validated disclaimer if present, otherwise the surrogate note
            validated_disclaimer = cfg.get("validated_disclaimer", "")
            if validated_disclaimer:
                cfg["disclaimer"] = (
                    f"{surrogate_disclaimer} | Backend: {validated_disclaimer}"
                )
            else:
                cfg["disclaimer"] = surrogate_disclaimer

    # ── Naive baseline + improvement_vs_naive (REMEDIATION fix #3) ────────────
    baseline_naive = _build_naive_baseline()
    rank1 = top3[0]
    rank1_kpi = rank1.get("cost_per_utci_degree", {}).get("value")
    naive_kpi = baseline_naive.get("cost_per_utci_degree")
    if rank1_kpi is not None and naive_kpi not in (None, 0):
        # Lower euro/°C is better; positive pct = optimizer is cheaper per degree.
        improvement_vs_naive_pct = round((naive_kpi - rank1_kpi) / naive_kpi * 100.0, 2)
    else:
        improvement_vs_naive_pct = None
    rank1["improvement_vs_naive_pct"] = improvement_vs_naive_pct

    # ── Build artifact JSON ───────────────────────────────────────────────────
    artifact = {
        "run_metadata": {
            "algorithm": "NSGA-II (pymoo 0.6.1)",
            "site": "Plaça dels Àngels, Barcelona",
            "population": _result_pop_size(result),
            "generations": N_GEN,
            "seed": SEED,
            "pareto_front_size": len(F),
            "surrogate": (
                "Analytical geometry proxy (±4°C) — see MOCKS.md. "
                "Outputs are surrogate-driven except validated_utci_c."
            ),
            "budget_eur": budget_eur,
        },
        "configurations": top3,
        "before_after": _build_before_after(top3),
        "baseline_naive": baseline_naive,
        "improvement_vs_naive_pct": improvement_vs_naive_pct,
    }

    json_path = out_dir / "top3_configurations.json"
    json_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Wrote decision artifact: %s", json_path)

    # Write audit record and Pareto plot (best-effort; failures do not block JSON)
    write_audit_record(top3, result, out_dir)
    plot_pareto(result, out_dir / "pareto_front.png")

    return json_path


# ── AUDIT RECORD (provenance trail / Plan 02-05) ─────────────────────────────


def write_audit_record(top3: list[dict], result, out_dir: Path) -> None:
    """Write a provenance audit record to *out_dir*/audit_record.json.

    Captures:
      - surrogate flags (which values are UNVALIDATED)
      - per-config data-source tags (mock vs validated)
      - TOPSIS weights echoed (as adjustable parameters, not calibrated constants)
      - generation timestamp
    """
    out_dir = Path(out_dir)

    # Per-config summary (lightweight — no full tree list)
    config_audit = []
    for cfg in top3:
        config_audit.append(
            {
                "rank": cfg.get("rank"),
                "label": cfg.get("label"),
                "delta_tmrt_source": cfg.get("delta_tmrt_source", "surrogate"),
                "delta_tmrt_c_status": "UNVALIDATED — surrogate proxy (±4°C)",
                "delta_utci_c_status": (
                    f"validated by {cfg.get('validated_backend', 'unknown')} backend"
                ),
                "cost_per_utci_degree_value": (
                    cfg.get("cost_per_utci_degree", {}).get("value")
                ),
                "topsis_score": cfg.get("topsis_score"),
                "disclaimer": cfg.get("disclaimer", ""),
                "validated_backend": cfg.get("validated_backend", "unknown"),
            }
        )

    F = np.atleast_2d(result.F)
    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "surrogate_flags": {
            "delta_tmrt_c": "UNVALIDATED — analytical proxy, NOT measured/simulated",
            "uncertainty_c": 4.0,
            "max_tmrt_reduction_c_cap": "12°C — UNSOURCED hard cap (ARCHITECTURE.md Known Issues #4)",
            "validated_utci_c": "mock backend (NOT MEASURED DATA) until INFRARED_BACKEND=live",
        },
        "topsis_weights": {
            "w_thermal": 0.6,
            "w_ecological": 0.4,
            "note": (
                "Adjustable parameters — NOT stakeholder-derived constants. "
                "Will be exposed as Gradio sliders in Phase 3 (CONCERNS 1.6)."
            ),
        },
        "pareto_front_size": len(F),
        "configurations": config_audit,
        "data_sources": {
            "cost_constants": "DECLARED assumptions (REQUIRES_VERIFICATION) — see MOCKS.md",
            "surrogate_physics": "Analytical proxy ported from NatureGooddest — see MOCKS.md",
            "utci_validation": "mock / cached / live via INFRARED_BACKEND env var",
        },
    }

    audit_path = out_dir / "audit_record.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Wrote audit record: %s", audit_path)


# ── PARETO PLOT (best-effort / Plan 02-05) ────────────────────────────────────


def plot_pareto(result, out_path: Path) -> None:
    """Scatter-plot the Pareto front (thermal relief vs ecological score) as a PNG.

    This function is intentionally best-effort: if matplotlib is not installed or
    rendering fails, a warning is logged and the function returns without raising
    so the JSON artifact pipeline is never blocked (T-02-18).

    Args:
        result:   pymoo Result from run_optimisation().
        out_path: Full path to write the PNG (e.g. outputs/pareto_front.png).
    """
    try:
        import matplotlib  # noqa: PLC0415
        matplotlib.use("Agg")   # non-interactive backend (safe for headless runs)
        import matplotlib.pyplot as plt  # noqa: PLC0415
    except ImportError:
        logger.warning(
            "matplotlib not installed — skipping Pareto plot. "
            "Install matplotlib to enable pareto_front.png output."
        )
        return

    try:
        F = np.atleast_2d(result.F)
        # Negate objectives to get positive "improvement" axes
        thermal = -F[:, 0]
        ecological = -F[:, 1]

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(thermal, ecological, c="steelblue", alpha=0.7, s=40, edgecolors="none")
        ax.set_xlabel("Thermal relief — ΔTmrt surrogate (°C)")
        ax.set_ylabel("Ecological coherence score")
        ax.set_title(
            "Pareto front — CoolSpend NSGA-II\n"
            "(surrogate objectives; ±4°C uncertainty on thermal axis)"
        )
        ax.grid(True, linestyle="--", alpha=0.4)
        fig.tight_layout()

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=120)
        plt.close(fig)
        logger.info("Wrote Pareto plot: %s", out_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pareto plot failed (pipeline continues): %s", exc)


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
