"""
test_rules_engine.py — Deterministic offline tests for rules_engine.py.

Tests cover:
    - spacing_penalty: close pair (< MIN_SPACING_M) > 0.0 (RULES-01)
    - spacing_penalty: far pair (>= MIN_SPACING_M) == 0.0 (RULES-01)
    - spacing_penalty: close pair > far pair (monotonicity) (RULES-01)
    - spacing_penalty: very close pair adds more than moderately close (monotonicity) (RULES-01)
    - spacing_penalty: 0 or 1 active trees → 0.0 (RULES-01)
    - spacing_penalty: inactive trees excluded (RULES-01)
    - species_diversity_score: monoculture → 0.0 (RULES-02)
    - species_diversity_score: diverse mix > 0.0 (RULES-02)
    - species_diversity_score: diverse mix (3 species) > monoculture of same count (RULES-02)
    - species_diversity_score: empty config → 0.0, no exception (RULES-02)
    - species_diversity_score: single tree → 0.0, no exception (RULES-02)
    - ecological_score: returns finite float in [0, 1] (combined) (RULES-01 + RULES-02)
    - ecological_score: deterministic for identical input (RULES-01 + RULES-02)
    - ecological_score: no infrared/network import in module (honesty contract)

All tests are pure arithmetic, fully offline, deterministic. No API key needed.
"""
from __future__ import annotations

import math
import pytest

from coolspend.rules_engine import (
    MIN_SPACING_M,
    SPECIES_PALETTE,
    _active_trees,
    ecological_score,
    spacing_penalty,
    species_diversity_score,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _config(*trees: dict) -> dict:
    """Build a config dict from bare tree dicts."""
    return {"trees": list(trees)}


def _tree(x: float, y: float, species: str = "platanus", active: bool = True) -> dict:
    t = {"x_m": x, "y_m": y, "species": species}
    if not active:
        t["active"] = False
    return t


# ── spacing_penalty (RULES-01) ────────────────────────────────────────────────

class TestSpacingPenalty:

    def test_close_pair_has_positive_penalty(self) -> None:
        """Two trees 1.0 m apart (< MIN_SPACING_M=4.0) → penalty > 0."""
        cfg = _config(_tree(0.0, 0.0), _tree(1.0, 0.0))
        assert spacing_penalty(cfg) > 0.0

    def test_adequate_pair_has_zero_penalty(self) -> None:
        """Two trees 10.0 m apart (>= MIN_SPACING_M) → penalty == 0."""
        cfg = _config(_tree(0.0, 0.0), _tree(10.0, 0.0))
        assert spacing_penalty(cfg) == pytest.approx(0.0)

    def test_close_pair_more_than_adequate_pair(self) -> None:
        """Monotonicity: 1 m spacing penalises more than 10 m spacing."""
        cfg_close = _config(_tree(0.0, 0.0), _tree(1.0, 0.0))
        cfg_far = _config(_tree(0.0, 0.0), _tree(10.0, 0.0))
        assert spacing_penalty(cfg_close) > spacing_penalty(cfg_far)

    def test_closer_pair_penalises_more(self) -> None:
        """Monotonicity: 0.5 m apart penalises strictly more than 2.0 m apart."""
        cfg_very_close = _config(_tree(0.0, 0.0), _tree(0.5, 0.0))
        cfg_moderate = _config(_tree(0.0, 0.0), _tree(2.0, 0.0))
        assert spacing_penalty(cfg_very_close) > spacing_penalty(cfg_moderate)

    def test_zero_trees_returns_zero(self) -> None:
        """Empty config → 0.0, no exception."""
        assert spacing_penalty({}) == pytest.approx(0.0)
        assert spacing_penalty({"trees": []}) == pytest.approx(0.0)

    def test_single_tree_returns_zero(self) -> None:
        """One active tree → no pairs → 0.0."""
        cfg = _config(_tree(5.0, 5.0))
        assert spacing_penalty(cfg) == pytest.approx(0.0)

    def test_inactive_trees_excluded(self) -> None:
        """Inactive trees are ignored; a close inactive pair yields no penalty."""
        cfg = _config(
            _tree(0.0, 0.0, active=False),
            _tree(1.0, 0.0, active=False),
        )
        assert spacing_penalty(cfg) == pytest.approx(0.0)

    def test_inactive_tree_not_counted_in_pair(self) -> None:
        """One active + one inactive close together → no pair → penalty 0."""
        cfg = _config(
            _tree(0.0, 0.0, active=True),
            _tree(0.5, 0.0, active=False),
        )
        assert spacing_penalty(cfg) == pytest.approx(0.0)

    def test_penalty_formula_correctness(self) -> None:
        """Manual verification: distance=1.0, MIN=4.0 → penalty=(4-1)/4=0.75."""
        cfg = _config(_tree(0.0, 0.0), _tree(1.0, 0.0))
        expected = (MIN_SPACING_M - 1.0) / MIN_SPACING_M  # = 0.75
        assert spacing_penalty(cfg) == pytest.approx(expected)

    def test_penalty_at_exact_min_spacing(self) -> None:
        """Trees exactly MIN_SPACING_M apart → penalty == 0.0 (not negative)."""
        cfg = _config(_tree(0.0, 0.0), _tree(MIN_SPACING_M, 0.0))
        assert spacing_penalty(cfg) == pytest.approx(0.0)

    def test_custom_min_spacing_override(self) -> None:
        """Caller can pass a custom min_spacing_m; still correct."""
        cfg = _config(_tree(0.0, 0.0), _tree(3.0, 0.0))
        # With min=5: penalty = (5-3)/5 = 0.4
        assert spacing_penalty(cfg, min_spacing_m=5.0) == pytest.approx(0.4)
        # With min=2: 3m >= 2m → penalty = 0
        assert spacing_penalty(cfg, min_spacing_m=2.0) == pytest.approx(0.0)


# ── species_diversity_score (RULES-02) ────────────────────────────────────────

class TestSpeciesDiversityScore:

    def test_monoculture_is_zero(self) -> None:
        """3 trees all same species → Shannon H = 0 → score 0.0."""
        cfg = _config(
            _tree(0.0, 0.0, "platanus"),
            _tree(5.0, 0.0, "platanus"),
            _tree(10.0, 0.0, "platanus"),
        )
        assert species_diversity_score(cfg) == pytest.approx(0.0)

    def test_diverse_mix_above_zero(self) -> None:
        """3 distinct species → score > 0."""
        cfg = _config(
            _tree(0.0, 0.0, "platanus"),
            _tree(5.0, 0.0, "celtis"),
            _tree(10.0, 0.0, "tilia"),
        )
        assert species_diversity_score(cfg) > 0.0

    def test_diverse_mix_greater_than_monoculture(self) -> None:
        """3 distinct species > monoculture of same tree count."""
        cfg_diverse = _config(
            _tree(0.0, 0.0, "platanus"),
            _tree(5.0, 0.0, "celtis"),
            _tree(10.0, 0.0, "tilia"),
        )
        cfg_mono = _config(
            _tree(0.0, 0.0, "platanus"),
            _tree(5.0, 0.0, "platanus"),
            _tree(10.0, 0.0, "platanus"),
        )
        assert species_diversity_score(cfg_diverse) > species_diversity_score(cfg_mono)

    def test_empty_config_returns_zero(self) -> None:
        """Empty config → 0.0, no exception."""
        assert species_diversity_score({}) == pytest.approx(0.0)
        assert species_diversity_score({"trees": []}) == pytest.approx(0.0)

    def test_single_tree_returns_zero(self) -> None:
        """Single tree → 0.0, no exception."""
        cfg = _config(_tree(5.0, 5.0, "platanus"))
        assert species_diversity_score(cfg) == pytest.approx(0.0)

    def test_balanced_mix_approaches_one(self) -> None:
        """Equal counts of N species → normalised Shannon near 1.0."""
        # 4 species, 1 tree each → H = ln(4), H_max = ln(4) → score = 1.0
        cfg = _config(
            _tree(0.0, 0.0, "platanus"),
            _tree(5.0, 0.0, "celtis"),
            _tree(10.0, 0.0, "tilia"),
            _tree(15.0, 0.0, "quercus"),
        )
        score = species_diversity_score(cfg)
        assert score == pytest.approx(1.0, abs=1e-9)

    def test_score_bounded_zero_to_one(self) -> None:
        """Diversity score is in [0, 1] for any input."""
        configs = [
            _config(_tree(0.0, 0.0, "platanus"), _tree(5.0, 0.0, "celtis")),
            _config(_tree(0.0, 0.0, "platanus"), _tree(5.0, 0.0, "platanus")),
            _config(
                _tree(0.0, 0.0, "platanus"),
                _tree(5.0, 0.0, "platanus"),
                _tree(10.0, 0.0, "celtis"),
                _tree(15.0, 0.0, "tilia"),
            ),
        ]
        for cfg in configs:
            s = species_diversity_score(cfg)
            assert 0.0 <= s <= 1.0, f"score {s} out of [0,1] for {cfg}"

    def test_two_species_unequal_mix(self) -> None:
        """Unbalanced 2-species mix: score in (0, 1) strictly."""
        cfg = _config(
            _tree(0.0, 0.0, "platanus"),
            _tree(5.0, 0.0, "platanus"),
            _tree(10.0, 0.0, "celtis"),
        )
        s = species_diversity_score(cfg)
        assert 0.0 < s < 1.0


# ── ecological_score (combined) ───────────────────────────────────────────────

class TestEcologicalScore:

    def test_returns_finite_float(self) -> None:
        """ecological_score always returns a finite float."""
        cfg = _config(_tree(0.0, 0.0, "platanus"), _tree(5.0, 5.0, "celtis"))
        result = ecological_score(cfg)
        assert isinstance(result, float)
        assert math.isfinite(result)

    def test_bounded_zero_to_one(self) -> None:
        """Score is in [0, 1] for various configs."""
        configs = [
            _config(),
            _config(_tree(0.0, 0.0, "platanus")),
            _config(_tree(0.0, 0.0, "platanus"), _tree(0.5, 0.0, "platanus")),  # close monoculture
            _config(_tree(0.0, 0.0, "platanus"), _tree(10.0, 0.0, "celtis")),   # spaced diverse
            _config(
                _tree(0.0, 0.0, "platanus"),
                _tree(10.0, 0.0, "celtis"),
                _tree(20.0, 0.0, "tilia"),
                _tree(30.0, 0.0, "quercus"),
            ),
        ]
        for cfg in configs:
            s = ecological_score(cfg)
            assert 0.0 <= s <= 1.0, f"score {s} out of [0,1] for {cfg}"

    def test_deterministic_for_identical_input(self) -> None:
        """Same config → same score every call."""
        cfg = _config(
            _tree(12.5, 8.0, "platanus"),
            _tree(30.0, 20.0, "celtis"),
            _tree(5.0, 5.0, "tilia"),
        )
        assert ecological_score(cfg) == ecological_score(cfg)

    def test_diverse_spaced_scores_higher_than_close_monoculture(self) -> None:
        """Well-spaced diverse mix > close-packed monoculture."""
        cfg_good = _config(
            _tree(0.0, 0.0, "platanus"),
            _tree(10.0, 0.0, "celtis"),
            _tree(20.0, 0.0, "tilia"),
        )
        cfg_bad = _config(
            _tree(0.0, 0.0, "platanus"),
            _tree(0.5, 0.0, "platanus"),
            _tree(1.0, 0.0, "platanus"),
        )
        assert ecological_score(cfg_good) > ecological_score(cfg_bad)

    def test_empty_config_returns_zero(self) -> None:
        """Empty config → 0.0, no exception."""
        assert ecological_score({}) == pytest.approx(0.0)

    def test_result_rounded_to_4_decimals(self) -> None:
        """ecological_score returns a value rounded to 4 decimal places."""
        cfg = _config(
            _tree(0.0, 0.0, "platanus"),
            _tree(8.0, 0.0, "celtis"),
        )
        s = ecological_score(cfg)
        assert s == round(s, 4)


# ── _active_trees helper ──────────────────────────────────────────────────────

class TestActiveTreesHelper:

    def test_all_active_by_default(self) -> None:
        """Trees without explicit 'active' key are treated as active."""
        cfg = _config(_tree(0.0, 0.0), _tree(5.0, 0.0))
        assert len(_active_trees(cfg)) == 2

    def test_inactive_excluded(self) -> None:
        """Trees with active=False are excluded."""
        cfg = _config(_tree(0.0, 0.0, active=False), _tree(5.0, 0.0, active=True))
        result = _active_trees(cfg)
        assert len(result) == 1
        assert result[0]["x_m"] == 5.0

    def test_empty_config(self) -> None:
        """Empty trees list → empty result."""
        assert _active_trees({}) == []
        assert _active_trees({"trees": []}) == []


# ── Module-level constants ────────────────────────────────────────────────────

class TestModuleConstants:

    def test_min_spacing_m_value(self) -> None:
        """MIN_SPACING_M must be 4.0 per spec."""
        assert MIN_SPACING_M == 4.0

    def test_species_palette_contains_required_species(self) -> None:
        """SPECIES_PALETTE must include the 4 demo species."""
        required = {"platanus", "celtis", "tilia", "quercus"}
        assert required.issubset(set(SPECIES_PALETTE))

    def test_no_network_imports_in_module(self) -> None:
        """rules_engine must not import infrared, requests, httpx, or any SDK."""
        import importlib.util
        import pathlib

        rules_path = pathlib.Path(__file__).resolve().parent.parent / "rules_engine.py"
        source = rules_path.read_text(encoding="utf-8")
        forbidden = ["import infrared", "import requests", "import httpx",
                     "from infrared", "from requests", "from httpx"]
        for pattern in forbidden:
            assert pattern not in source, (
                f"rules_engine.py must not contain '{pattern}' (offline module)"
            )
