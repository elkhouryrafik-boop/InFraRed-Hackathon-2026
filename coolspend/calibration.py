"""
coolspend/calibration.py — Surrogate ground-truth calibration study.

Purpose (VALID-01 + VALID-03):
  Run 10 deterministic, seed-pinned, coverage-swept configurations through the
  real Infrared UTCI API (live-then-cache) and measure how well the surrogate
  ΔTmrt (routed to UTCI via HOURS_PER_DEGC_REF) predicts real Infrared UTCI
  deltas.  Compute RMSE + R² + an empirical 95% error band, and report ranking
  stability both ways (set-overlap headline naming any rank swaps + Spearman/
  Kendall τ over the full config set).

LIVE-THEN-CACHE OPERATOR PROCEDURE (D-01):
  The study is designed to run once with INFRARED_BACKEND=live (requires
  INFRARED_API_KEY), which writes every response to
  coolspend/cache/infrared/ automatically via sdk_client._dispatch.  Subsequent
  runs with INFRARED_BACKEND=cached replay the recorded fixtures offline, so
  RMSE/R² are reproducible without burning the API key.  CI always runs with
  INFRARED_BACKEND unset (defaults to "mock") — no key required.

  Operator steps (one-time, when key is available):
    1. Set INFRARED_BACKEND=live and INFRARED_API_KEY=<your-key> in .env.
    2. Run: python -m coolspend.calibration
       (or: python -c "from coolspend.calibration import run_calibration_study; run_calibration_study()")
    3. Fixtures are written to coolspend/cache/infrared/.
    4. Switch to INFRARED_BACKEND=cached for offline replay.

SEPARATE SIMBUDGET (D-03):
  run_calibration_study creates SimBudget(max_live_calls = n + 1) — one
  baseline call + n intervention calls = n+1 total.  This is SEPARATE from the
  Top-3 cap of SimBudget(max_live_calls=3) in optimizer.validate_top3_with_infrared,
  which is NOT modified by this module.

DIMENSIONAL CONTRACT (CRITICAL):
  The surrogate UTCI prediction uses the IDENTICAL conversion as the KPI:
    surrogate_pred_utci_delta_c = hours_reduced / HOURS_PER_DEGC_REF
  where HOURS_PER_DEGC_REF is imported from coolspend.cost_model (not re-defined
  here).  Both sides of the RMSE pair are in °C — the pairing is dimensionally
  valid.  Do NOT use cost_per_utci_degree() to get a UTCI delta — it returns
  EUR/°C (a cost ratio, not a temperature).

SDK imports are INSIDE functions only (never at module-top), per project
convention (# noqa: PLC0415 for local imports).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

# ── Study constants ───────────────────────────────────────────────────────────

STUDY_SEED: int = 42
"""Seed for deterministic config generation (D-02).  Identical to NSGA-II SEED."""

N_STUDY_CONFIGS: int = 10
"""Number of coverage-swept configs in the calibration study (D-02 upper bound)."""


# ── Config generator ──────────────────────────────────────────────────────────


def generate_study_configs(
    n: int = N_STUDY_CONFIGS,
    seed: int = STUDY_SEED,
) -> list[dict]:
    """Generate n deterministic, coverage-swept tree configurations for calibration.

    Produces exactly n configs whose realised core_weighted_coverage_fraction
    spans low → high across the surrogate's operating band.  The list is sorted
    by coverage_fraction ascending so the sweep is explicit (D-02).

    Strategy:
      1. Target n evenly-spaced coverage "levels" from a low anchor to the site max.
      2. For each level, place trees at seeded valid locations that achieve a
         coverage_fraction close to the target level.  We vary tree_count from
         a small number to a larger number, placing each tree at a randomly
         selected valid site location (seeded numpy RandomState(seed)).
      3. Compute the actual core_weighted_coverage_fraction for each placement
         and record it in the config.
      4. Sort ascending by coverage_fraction so the sweep is monotonically
         non-decreasing (D-02 requirement).

    Each config carries:
      - "trees": list of tree dicts (x_m, y_m, species, active=True)
      - "tree_count": number of active trees
      - "coverage_fraction": realized core_weighted_coverage_fraction
      - "delta_tmrt_c": thermal_relief(cfg), rounded to 3 d.p.

    Determinism: seeded numpy RandomState(seed) only — no wall-clock, no
    unsorted-set iteration.  Same seed → identical output across calls.

    Args:
        n:    Number of configs to generate (default N_STUDY_CONFIGS = 10).
        seed: RNG seed for deterministic placement (default STUDY_SEED = 42).

    Returns:
        Sorted list of n config dicts, coverage_fraction non-decreasing.
    """
    import numpy as np  # noqa: PLC0415
    from coolspend.spatial_engine import (  # noqa: PLC0415
        SITE_WIDTH_M,
        SITE_DEPTH_M,
        core_weighted_coverage_fraction,
        is_valid_location,
        thermal_relief,
    )
    from coolspend.optimizer import SPECIES  # noqa: PLC0415

    # Use the species palette from the optimizer (same round-robin assignment)
    species_palette = SPECIES

    rng = np.random.RandomState(seed)

    # Build a pool of valid tree locations via rejection sampling
    # We need enough valid locations to fill the largest config
    _MAX_TREES_TARGET = n + 2  # ensure we have locations for all n levels
    _CANDIDATE_POOL = 200     # candidate points to test

    valid_locs: list[tuple[float, float]] = []
    candidates = rng.uniform(
        low=[0.0, 0.0],
        high=[SITE_WIDTH_M, SITE_DEPTH_M],
        size=(_CANDIDATE_POOL, 2),
    )
    for x_m, y_m in candidates:
        if is_valid_location(float(x_m), float(y_m)):
            valid_locs.append((float(x_m), float(y_m)))
        if len(valid_locs) >= _MAX_TREES_TARGET * 4:
            break  # enough locations

    # If too few valid locations, sample more
    extra_attempts = 0
    while len(valid_locs) < _MAX_TREES_TARGET and extra_attempts < 500:
        x_m = rng.uniform(0.0, SITE_WIDTH_M)
        y_m = rng.uniform(0.0, SITE_DEPTH_M)
        if is_valid_location(float(x_m), float(y_m)):
            valid_locs.append((float(x_m), float(y_m)))
        extra_attempts += 1

    # Number of valid locations available
    n_valid = len(valid_locs)

    # Determine tree counts to use: sweep from 1 to n_valid (or to a sensible max)
    # We want n configs spanning the coverage range.  More trees → higher coverage.
    # Use linspace over [1, min(n_valid, 12)] to ensure monotonic growth.
    max_trees = min(n_valid, 12)
    if n <= 1:
        tree_counts_float = [float(max_trees)]
    else:
        # linspace from 1 to max_trees, n steps, rounded to int and deduplicated
        tree_counts_float = np.linspace(1, max_trees, n).tolist()

    # Convert to integers, ensuring they are increasing (for sweep)
    tree_counts: list[int] = []
    prev = 0
    for tc in tree_counts_float:
        tc_int = max(1, int(round(tc)))
        # Ensure non-decreasing counts (coverage_fraction is non-decreasing in tree_count)
        if tc_int <= prev:
            tc_int = prev + 1
        tree_counts.append(min(tc_int, n_valid))
        prev = tc_int

    # Build one config per tree count level
    configs: list[dict] = []
    for level_idx, tree_count in enumerate(tree_counts):
        # Select tree_count valid locations (seeded; no replacement)
        if tree_count > n_valid:
            tree_count = n_valid

        # Use a different sub-seed for each level to avoid identical placements
        level_rng = np.random.RandomState(seed + level_idx)
        chosen_indices = level_rng.choice(n_valid, size=tree_count, replace=False)
        chosen_locs = [valid_locs[i] for i in chosen_indices]

        trees = []
        for i, (x_m, y_m) in enumerate(chosen_locs):
            species = species_palette[i % len(species_palette)]
            trees.append({
                "x_m": round(x_m, 4),
                "y_m": round(y_m, 4),
                "species": species,
                "active": True,
            })

        cfg: dict = {
            "trees": trees,
            "tree_count": tree_count,
        }

        active = [t for t in trees if t.get("active", True)]
        cov_frac = core_weighted_coverage_fraction(active)
        cfg["coverage_fraction"] = round(cov_frac, 6)
        cfg["delta_tmrt_c"] = round(thermal_relief(cfg), 3)

        configs.append(cfg)

    # Sort by coverage_fraction ascending (D-02 explicit sweep)
    configs.sort(key=lambda c: c["coverage_fraction"])

    return configs


# ── Calibration study runner ──────────────────────────────────────────────────


def run_calibration_study(
    n: int = N_STUDY_CONFIGS,
    out_path: str = "outputs/calibration_study.json",
) -> dict:
    """Run the calibration study across n coverage-swept configurations.

    Uses a SEPARATE SimBudget(max_live_calls = n + 1) — one baseline call plus
    one intervention per config.  This is distinct from the Top-3 cap of 3 in
    optimizer.validate_top3_with_infrared (D-03).

    LIVE-THEN-CACHE (D-01): run once with INFRARED_BACKEND=live to record
    fixtures, then replay with INFRARED_BACKEND=cached.  Tests run on mock/cached.

    Surrogate UTCI prediction (DIMENSIONAL CONTRACT):
      surrogate_pred_utci_delta_c = hours_reduced / HOURS_PER_DEGC_REF
    where hours_reduced = utci_hours_above baseline - utci_hours_above with coverage.
    This is the SAME conversion used by cost_per_utci_degree (D-08), so the
    calibration pairing is dimensionally consistent (both sides in °C).

    Args:
        n:        Number of study configs (default N_STUDY_CONFIGS = 10).
        out_path: Path to write the JSON artifact (created with parents).

    Returns:
        Dict with keys: configs, baseline_utci_c, backend, n_configs, seed,
        fit, rank_stability, disclaimer.
    """
    # ── 1. Generate configs ────────────────────────────────────────────────────
    configs = generate_study_configs(n=n, seed=STUDY_SEED)

    # ── 2. SDK budget (separate from Top-3 cap of 3) ──────────────────────────
    from coolspend.sdk_client import get_baseline_utci, get_intervention_utci, SimBudget  # noqa: PLC0415
    budget = SimBudget(max_live_calls=n + 1)  # +1 for the baseline (D-03)

    # ── 3. Geometry builders (reuse optimizer's pattern) ──────────────────────
    from coolspend.optimizer import _config_to_geometry, _build_baseline_geometry  # noqa: PLC0415

    # ── 4. Baseline UTCI ──────────────────────────────────────────────────────
    baseline = get_baseline_utci(_build_baseline_geometry())
    budget.record("baseline study")

    # ── 5. Per-config real UTCI + surrogate prediction ────────────────────────
    # Local imports inside function (SDK isolation convention + D-08 contract)
    from nature_metrics import utci_hours_above  # noqa: PLC0415
    from coolspend.cost_model import hours_per_degc  # noqa: PLC0415

    hpd = hours_per_degc()  # EPW-derived; same conversion the KPI uses (D-08 contract)

    # Baseline UTCI-hours (coverage_fraction=0) for computing hours_reduced
    baseline_utci_hours_dict = utci_hours_above(32.0, 0.0)
    baseline_utci_hours: float = float(baseline_utci_hours_dict.get("value") or 0.0)

    for i, cfg in enumerate(configs):
        # Record budget slot before each live call
        budget.record(f"study intervention {i}")

        # Real Infrared UTCI for this config
        geom = _config_to_geometry(cfg)
        real_result = get_intervention_utci(geom)
        cfg["real_utci_c"] = real_result.utci_c
        cfg["real_delta_utci_c"] = round(baseline.utci_c - real_result.utci_c, 2)
        cfg["validated_backend"] = real_result.backend

        # Surrogate UTCI prediction via HOURS_PER_DEGC_REF (DIMENSIONAL CONTRACT)
        # hours_reduced = baseline_utci_hours - hours_with_coverage (i.e. -delta)
        # utci_hours_above.delta is negative (a reduction), so hours_reduced = -delta
        cov_frac = cfg.get("coverage_fraction", 0.0)
        intervention_uh_dict = utci_hours_above(32.0, cov_frac)
        intervention_uh = float(intervention_uh_dict.get("value") or baseline_utci_hours)

        hours_reduced = baseline_utci_hours - intervention_uh
        if hours_reduced < 0:
            hours_reduced = 0.0  # guard: should not happen, be safe

        cfg["surrogate_pred_utci_delta_c"] = round(hours_reduced / hpd, 3)

    # ── 6. Compute fit and rank stability ──────────────────────────────────────
    fit = compute_fit(configs)
    rank = rank_stability(configs)

    # ── 7. Assemble artifact ──────────────────────────────────────────────────
    artifact: dict = {
        "configs": configs,
        "baseline_utci_c": baseline.utci_c,
        "backend": baseline.backend,
        "n_configs": n,
        "seed": STUDY_SEED,
        "fit": fit,
        "rank_stability": rank,
        "disclaimer": (
            "Calibration of analytical surrogate against real Infrared UTCI; "
            "band is empirical RMSE-derived. "
            "Run once with INFRARED_BACKEND=live (records fixtures); "
            "replay with INFRARED_BACKEND=cached for reproducibility/CI. "
            "Tests use mock/cached backend — no API key required. "
            "SURROGATE: thermal_relief() is an analytical proxy (MOCKS.md). "
            "LIVE-THEN-CACHE procedure (D-01): see coolspend/calibration.py module docstring."
        ),
    }

    # ── 8. Write JSON artifact (no secrets — T-05-08) ─────────────────────────
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return artifact


# ── Fit computation ───────────────────────────────────────────────────────────


def compute_fit(configs: list[dict]) -> dict:
    """Compute RMSE, R², and 95% empirical error band for the surrogate vs real UTCI.

    Paired arrays:
      pred = cfg["surrogate_pred_utci_delta_c"]  — surrogate UTCI delta (°C)
      real = cfg["real_delta_utci_c"]            — measured Infrared UTCI delta (°C)

    RMSE = sqrt(mean((pred - real)²))
    R²   = 1 - SS_res / SS_tot  (guard SS_tot == 0 → r2 = None)
    error_band_c = 1.96 * RMSE  (empirical 95% confidence band)

    Args:
        configs: List of config dicts with surrogate_pred_utci_delta_c and
                 real_delta_utci_c.

    Returns:
        {
          "rmse": float,           — root-mean-squared error (°C)
          "r2": float | None,      — coefficient of determination (None if SS_tot==0)
          "error_band_c": float,   — 1.96 * RMSE (95% empirical band)
          "n": int,                — number of configs in the fit
          "band_basis": str,       — human-readable description of the band
        }
    """
    n = len(configs)
    if n == 0:
        return {
            "rmse": None,
            "r2": None,
            "error_band_c": None,
            "n": 0,
            "band_basis": "1.96 * empirical RMSE (surrogate vs real Infrared UTCI delta)",
        }

    pred: list[float] = [float(c["surrogate_pred_utci_delta_c"]) for c in configs]
    real: list[float] = [float(c["real_delta_utci_c"]) for c in configs]

    # RMSE
    ss_res = sum((p - r) ** 2 for p, r in zip(pred, real))
    rmse = math.sqrt(ss_res / n)

    # R² (coefficient of determination)
    mean_real = sum(real) / n
    ss_tot = sum((r - mean_real) ** 2 for r in real)
    if ss_tot == 0.0:
        r2 = None  # guard: undefined when all real values are identical
    else:
        r2 = 1.0 - ss_res / ss_tot

    # 95% empirical error band: 1.96 * RMSE (documented multiplier)
    error_band_c = round(1.96 * rmse, 3)

    return {
        "rmse": round(rmse, 3),
        "r2": round(r2, 3) if r2 is not None else None,
        "error_band_c": error_band_c,
        "n": n,
        "band_basis": "1.96 * empirical RMSE (surrogate vs real Infrared UTCI delta)",
    }


# ── Rank stability ────────────────────────────────────────────────────────────


def rank_stability(configs: list[dict]) -> dict:
    """Report ranking stability of the surrogate vs real Infrared UTCI (D-05).

    Two-way reporting:
      (a) Set-overlap headline: which of the surrogate Top-3 stayed Top-3 under
          real UTCI, with named rank swaps (e.g. "rank 1<->2") among shared members.
      (b) Rank correlation: Spearman ρ and Kendall τ over the full config set.

    Args:
        configs: List of config dicts with surrogate_pred_utci_delta_c and
                 real_delta_utci_c.

    Returns:
        {
          "spearman_rho": float,      — Spearman rank correlation (full config set)
          "kendall_tau": float,       — Kendall τ rank correlation (full config set)
          "set_overlap_top3": int,    — how many surrogate Top-3 stayed in real Top-3
          "rank_swaps": list[str],    — named rank swaps among shared Top-3 members
          "headline": str,            — human-readable summary
        }
    """
    from scipy.stats import spearmanr, kendalltau  # noqa: PLC0415

    n = len(configs)
    pred: list[float] = [float(c["surrogate_pred_utci_delta_c"]) for c in configs]
    real: list[float] = [float(c["real_delta_utci_c"]) for c in configs]

    # Spearman and Kendall τ over the full config set
    # Guard NaN/None from scipy when inputs are constant (ConstantInputWarning)
    if n < 2:
        rho = 0.0
        tau = 0.0
    else:
        import warnings as _warnings  # noqa: PLC0415
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            rho_result, _ = spearmanr(pred, real)
            tau_result, _ = kendalltau(pred, real)
        # scipy returns NaN when one array is constant; treat as 0 (undefined correlation)
        rho = float(rho_result) if rho_result is not None and rho_result == rho_result else 0.0
        tau = float(tau_result) if tau_result is not None and tau_result == tau_result else 0.0

    # Set-overlap Top-3
    # surrogate Top-3: indices of the 3 highest surrogate predictions
    # real Top-3: indices of the 3 highest real measurements
    top_k = min(3, n)
    surr_ranked = sorted(range(n), key=lambda i: pred[i], reverse=True)
    real_ranked = sorted(range(n), key=lambda i: real[i], reverse=True)
    surr3 = set(surr_ranked[:top_k])
    real3 = set(real_ranked[:top_k])
    set_overlap = len(surr3 & real3)

    # Named rank swaps: compare ordered positions of shared members
    shared = surr3 & real3
    rank_swaps: list[str] = []
    for idx in shared:
        surr_rank = surr_ranked.index(idx) + 1   # 1-based
        real_rank = real_ranked.index(idx) + 1   # 1-based
        if surr_rank != real_rank:
            rank_swaps.append(f"config_{idx}: surrogate rank {surr_rank} -> real rank {real_rank}")

    headline = (
        f"{set_overlap}/3 surrogate Top-3 stayed Top-3 under real UTCI"
    )
    if rank_swaps:
        headline += f" (rank swaps: {', '.join(rank_swaps)})"

    return {
        "spearman_rho": round(rho, 3),
        "kendall_tau": round(tau, 3),
        "set_overlap_top3": set_overlap,
        "rank_swaps": rank_swaps,
        "headline": headline,
    }


# ── Main entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    backend = os.environ.get("INFRARED_BACKEND", "mock")
    print(f"Running calibration study (backend={backend}, n={N_STUDY_CONFIGS}, seed={STUDY_SEED})")
    print("LIVE-THEN-CACHE: set INFRARED_BACKEND=live to record fixtures; "
          "INFRARED_BACKEND=cached to replay offline.")
    print()

    result = run_calibration_study()
    fit = result["fit"]
    rank = result["rank_stability"]

    print(f"RMSE: {fit['rmse']} degC")
    print(f"R2:   {fit['r2']}")
    print(f"Band: +/-{fit['error_band_c']} degC (95% empirical, 1.96 * RMSE)")
    print(f"Rank: {rank['headline']}")
    print(f"  Spearman rho: {rank['spearman_rho']}")
    print(f"  Kendall tau:  {rank['kendall_tau']}")
    print()
    print("Artifact written to: outputs/calibration_study.json")
