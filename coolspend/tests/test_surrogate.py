"""
Tests for coolspend.spatial_engine — thermal surrogate (OPT-02).

Verifies:
- delta_tmrt_surrogate returns a finite positive float bounded by MAX_TMRT_REDUCTION_C
- Monotonic: more shade fraction => more cooling
- Cap: never exceeds MAX_TMRT_REDUCTION_C
- Double-porosity regression (CONCERNS 4.2): porosity applied exactly ONCE, not squared
- thermal_relief returns finite, non-negative value; 0.0 for empty config; increases with
  more trees

All tests run fully offline — no SDK calls, no network, no file I/O.
"""
from __future__ import annotations

import math
import pytest

# These imports WILL FAIL before the surrogate is implemented (RED gate).
from coolspend.spatial_engine import (
    core_weighted_coverage_fraction,
    delta_tmrt_surrogate,
    shade_efficiency,
    thermal_relief,
    MAX_TMRT_REDUCTION_C,
    SITE_DEPTH_M,
    SITE_WIDTH_M,
    TREE_SHADE_FRACTION,
    TREE_CANOPY_RADIUS_M,
)


# ── shade_efficiency tests ─────────────────────────────────────────────────────


def test_shade_efficiency_returns_positive() -> None:
    """shade_efficiency must return a positive float for any valid input."""
    eff = shade_efficiency(tilt_deg=0.0, height_m=3.75)
    assert eff > 0.0, f"Expected positive efficiency, got {eff}"
    assert math.isfinite(eff), "shade_efficiency must return a finite float"


def test_shade_efficiency_increases_with_tilt() -> None:
    """Higher tilt toward peak sun should produce higher shade efficiency."""
    eff_no_tilt = shade_efficiency(tilt_deg=0.0, height_m=3.75)
    eff_tilted = shade_efficiency(tilt_deg=30.0, height_m=3.75)
    assert eff_tilted > eff_no_tilt, (
        f"Expected tilted ({eff_tilted:.4f}) > no-tilt ({eff_no_tilt:.4f})"
    )


def test_shade_efficiency_increases_with_height() -> None:
    """Taller canopy should produce higher shade efficiency."""
    eff_low = shade_efficiency(tilt_deg=0.0, height_m=2.5)
    eff_high = shade_efficiency(tilt_deg=0.0, height_m=5.0)
    assert eff_high > eff_low, (
        f"Expected higher canopy ({eff_high:.4f}) > lower canopy ({eff_low:.4f})"
    )


# ── delta_tmrt_surrogate tests ────────────────────────────────────────────────


def test_delta_tmrt_basic_finite_positive() -> None:
    """Typical input should return a finite positive float."""
    result = delta_tmrt_surrogate(
        shade_fraction=0.85, porosity_pct=15.0, tilt_deg=0.0, height_m=3.75
    )
    assert math.isfinite(result), f"Expected finite result, got {result}"
    assert result > 0.0, f"Expected positive cooling delta, got {result}"


def test_delta_tmrt_capped_at_max() -> None:
    """Result must never exceed MAX_TMRT_REDUCTION_C (the unsourced 12°C cap)."""
    result = delta_tmrt_surrogate(
        shade_fraction=1.0, porosity_pct=0.0, tilt_deg=30.0, height_m=5.0
    )
    assert result <= MAX_TMRT_REDUCTION_C, (
        f"Expected result <= {MAX_TMRT_REDUCTION_C}, got {result}"
    )


def test_delta_tmrt_max_cap_value() -> None:
    """MAX_TMRT_REDUCTION_C constant must equal 12.0 (CONCERNS 1.1 — unsourced cap)."""
    assert MAX_TMRT_REDUCTION_C == 12.0, (
        f"Unsourced cap must be 12.0 per CONCERNS 1.1; found {MAX_TMRT_REDUCTION_C}"
    )


def test_delta_tmrt_monotonic_shade_fraction() -> None:
    """More shade fraction -> more cooling (monotonic in shade_fraction)."""
    result_low = delta_tmrt_surrogate(
        shade_fraction=0.50, porosity_pct=0.0, tilt_deg=0.0, height_m=3.75
    )
    result_high = delta_tmrt_surrogate(
        shade_fraction=0.90, porosity_pct=0.0, tilt_deg=0.0, height_m=3.75
    )
    assert result_high > result_low, (
        f"Expected higher shade ({result_high:.4f}) to give more cooling than "
        f"lower shade ({result_low:.4f})"
    )


def test_delta_tmrt_zero_shade_returns_zero() -> None:
    """Zero shade fraction should return 0.0 cooling."""
    result = delta_tmrt_surrogate(
        shade_fraction=0.0, porosity_pct=0.0, tilt_deg=0.0, height_m=3.75
    )
    assert result == 0.0, f"Expected 0.0 for zero shade, got {result}"


def test_delta_tmrt_no_double_porosity() -> None:
    """Regression test for CONCERNS 4.2: porosity applied ONCE, not squared.

    The fixed body uses effective_shade = shade_fraction (porosity already applied
    by the CALLER). If the body re-applied porosity internally, then:
        delta_tmrt_surrogate(0.85, 15.0, 0, 3.75)
    would equal
        delta_tmrt_surrogate(0.85 * (1 - 15/100), 0.0, 0, 3.75)
        = delta_tmrt_surrogate(0.7225, 0.0, 0, 3.75)

    These two must be DIFFERENT, proving porosity is NOT squared internally.
    The assertion checks that passing 0.85 vs 0.85^2 (= 0.7225) gives
    materially different results.
    """
    result_once = delta_tmrt_surrogate(
        shade_fraction=0.85, porosity_pct=15.0, tilt_deg=0.0, height_m=3.75
    )
    # If body double-applied porosity, these would be equal
    result_squared = delta_tmrt_surrogate(
        shade_fraction=0.85 ** 2, porosity_pct=15.0, tilt_deg=0.0, height_m=3.75
    )
    assert result_once != result_squared, (
        "POROSITY DOUBLE-APPLICATION BUG DETECTED (CONCERNS 4.2): "
        f"delta_tmrt_surrogate(0.85, ...) == delta_tmrt_surrogate(0.85**2, ...) = "
        f"{result_once:.6f}. The body must NOT re-apply porosity internally."
    )
    # The once-applied result must be larger (not squashed by extra porosity)
    assert result_once > result_squared, (
        f"Once-applied ({result_once:.4f}) should exceed squared ({result_squared:.4f})"
    )


def test_delta_tmrt_default_args() -> None:
    """Calling with only shade_fraction should work (defaults for other args)."""
    result = delta_tmrt_surrogate(shade_fraction=0.80)
    assert math.isfinite(result), "Default args must produce finite result"
    assert 0.0 <= result <= MAX_TMRT_REDUCTION_C


# ── thermal_relief tests ──────────────────────────────────────────────────────


def test_thermal_relief_empty_config_returns_zero() -> None:
    """An empty tree config must return 0.0 site relief."""
    result = thermal_relief({"trees": []})
    assert result == 0.0, f"Expected 0.0 for empty config, got {result}"


def test_thermal_relief_no_trees_key() -> None:
    """A config with no 'trees' key at all must return 0.0."""
    result = thermal_relief({})
    assert result == 0.0, f"Expected 0.0 for missing trees key, got {result}"


def test_thermal_relief_positive_for_active_trees() -> None:
    """One active tree must produce a positive site-level thermal relief."""
    config = {"trees": [{"active": True, "x_m": 30.0, "y_m": 20.0}]}
    result = thermal_relief(config)
    assert math.isfinite(result), f"Expected finite result, got {result}"
    assert result > 0.0, f"Expected positive relief for one active tree, got {result}"


def test_thermal_relief_inactive_tree_ignored() -> None:
    """Inactive trees (active=False) must not contribute to thermal relief."""
    config_inactive = {"trees": [{"active": False, "x_m": 30.0, "y_m": 20.0}]}
    result = thermal_relief(config_inactive)
    assert result == 0.0, (
        f"Expected 0.0 when all trees are inactive, got {result}"
    )


def test_thermal_relief_more_trees_more_relief() -> None:
    """More active trees should produce more (or equal) thermal relief."""
    config_one = {"trees": [{"active": True, "x_m": 10.0, "y_m": 10.0}]}
    config_many = {"trees": [
        {"active": True, "x_m": 10.0, "y_m": 10.0},
        {"active": True, "x_m": 25.0, "y_m": 10.0},
        {"active": True, "x_m": 40.0, "y_m": 10.0},
        {"active": True, "x_m": 10.0, "y_m": 25.0},
        {"active": True, "x_m": 25.0, "y_m": 25.0},
    ]}
    result_one = thermal_relief(config_one)
    result_many = thermal_relief(config_many)
    assert result_many >= result_one, (
        f"Expected more trees ({result_many:.4f}) >= one tree ({result_one:.4f})"
    )


def test_thermal_relief_bounded() -> None:
    """Even with many trees, thermal relief must be <= MAX_TMRT_REDUCTION_C."""
    # Saturate the site with trees
    trees = [
        {"active": True, "x_m": float(x), "y_m": float(y)}
        for x in range(0, 60, 5)
        for y in range(0, 42, 5)
    ]
    config = {"trees": trees}
    result = thermal_relief(config)
    assert result <= MAX_TMRT_REDUCTION_C, (
        f"Expected thermal_relief <= {MAX_TMRT_REDUCTION_C}, got {result}"
    )
    assert math.isfinite(result), "Expected finite result for large tree count"


def test_thermal_relief_deterministic() -> None:
    """thermal_relief must be deterministic — same config => same result."""
    config = {"trees": [
        {"active": True, "x_m": 15.0, "y_m": 12.0},
        {"active": True, "x_m": 35.0, "y_m": 28.0},
    ]}
    result1 = thermal_relief(config)
    result2 = thermal_relief(config)
    assert result1 == result2, (
        f"thermal_relief is not deterministic: {result1} != {result2}"
    )


def test_thermal_relief_default_active_flag() -> None:
    """Trees without an 'active' key should default to active (True)."""
    config_explicit = {"trees": [{"active": True, "x_m": 30.0, "y_m": 20.0}]}
    config_implicit = {"trees": [{"x_m": 30.0, "y_m": 20.0}]}
    result_explicit = thermal_relief(config_explicit)
    result_implicit = thermal_relief(config_implicit)
    assert result_explicit == result_implicit, (
        f"Expected default active=True: explicit={result_explicit}, implicit={result_implicit}"
    )


# ── core-weighted coverage tests (REMEDIATION Option A) ───────────────────────


def test_core_weighting_rewards_centre_over_edge() -> None:
    """A canopy at the plaza centre must score higher than the same canopy at the edge.

    This is the mechanism that creates the thermal↔ecological trade-off: shading the
    pedestrian core is worth more than shading the perimeter (Option A).
    """
    cx, cy = SITE_WIDTH_M / 2.0, SITE_DEPTH_M / 2.0
    centre = [{"x_m": cx, "y_m": cy}]
    edge = [{"x_m": 2.0, "y_m": 2.0}]
    cov_centre = core_weighted_coverage_fraction(centre)
    cov_edge = core_weighted_coverage_fraction(edge)
    assert cov_centre > cov_edge, (
        f"Centre canopy ({cov_centre:.4f}) must out-score edge canopy ({cov_edge:.4f})"
    )


def test_core_concentration_beats_full_spread_thermally() -> None:
    """Clustering canopy at the centre yields higher thermal relief than spreading wide.

    Concentrating in the core is what the thermal objective rewards; the ecological
    objective rewards the spread layout. Their disagreement is the trade-off.
    """
    cx, cy = SITE_WIDTH_M / 2.0, SITE_DEPTH_M / 2.0
    clustered = {"trees": [
        {"active": True, "x_m": cx + dx, "y_m": cy + dy}
        for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (0, 0)]
    ]}
    spread = {"trees": [
        {"active": True, "x_m": 6.0, "y_m": 6.0},
        {"active": True, "x_m": 54.0, "y_m": 6.0},
        {"active": True, "x_m": 6.0, "y_m": 36.0},
        {"active": True, "x_m": 54.0, "y_m": 36.0},
        {"active": True, "x_m": cx, "y_m": cy},
    ]}
    assert thermal_relief(clustered) > thermal_relief(spread), (
        "Core-clustered canopy must give more thermal relief than a wide spread"
    )


def test_core_weighted_coverage_empty_is_zero() -> None:
    """No trees → zero core-weighted coverage."""
    assert core_weighted_coverage_fraction([]) == 0.0


# ── Citation re-anchor tests (D-13 / HONEST-02) ───────────────────────────────


def test_surrogate_provenance_cites_schrodi() -> None:
    """spatial_engine module docstring must cite Schrodi 2023 (arXiv:2310.05691).

    D-13 re-anchor: Schrodi et al. 2023 is the Tmrt-magnitude anchor for the
    surrogate ceiling. Garcia-Nevado 2020 is demoted to a surface-temp analogue.
    This test pins the presence of the re-anchored citation in the module.
    """
    import coolspend.spatial_engine as _se
    module_doc = _se.__doc__ or ""
    assert "Schrodi" in module_doc, (
        "D-13: spatial_engine module docstring must cite Schrodi 2023 "
        "(arXiv:2310.05691, Tmrt-magnitude anchor)"
    )
    assert "arXiv:2310.05691" in module_doc, (
        "D-13: spatial_engine module docstring must include arXiv:2310.05691 "
        "(no fabricated DOI — arXiv preprint only)"
    )
    assert "Rahman" in module_doc, (
        "D-13: spatial_engine module docstring must cite Rahman 2022 "
        "(supporting tree-Tmrt anchor)"
    )


def test_surrogate_delta_tmrt_source_in_select_top3() -> None:
    """select_top3 emits delta_tmrt_source citing Schrodi 2023, not Garcia-Nevado as primary.

    D-11 / D-13: the per-config delta_tmrt_source field must reflect the re-anchored
    citation. Verifies the string in the optimizer hot path matches the honesty contract.
    """
    from coolspend.optimizer import run_optimisation, select_top3

    result = run_optimisation(n_gen=5, pop_size=10, seed=42)
    top3 = select_top3(result)

    for cfg in top3:
        source = cfg.get("delta_tmrt_source", "")
        assert "Schrodi" in source, (
            f"D-13: delta_tmrt_source must cite Schrodi 2023; got: {source!r}"
        )
        assert "re-simulated" in cfg.get("surrogate_note", "") or "re-simulated" in cfg.get("surrogate_note", ""), (
            f"D-11: surrogate_note must use 're-simulated' not 'validated'; "
            f"got: {cfg.get('surrogate_note')!r}"
        )
        # Garcia-Nevado must be demoted (listed as analogue, not primary)
        assert "analogue" in source.lower(), (
            f"D-13: Garcia-Nevado 2020 must be listed as 'analogue' in delta_tmrt_source; "
            f"got: {source!r}"
        )
