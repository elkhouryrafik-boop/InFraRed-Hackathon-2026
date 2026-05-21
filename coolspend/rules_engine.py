"""
coolspend.rules_engine — Ecological-coherence scoring for the NSGA-II second objective.

This module is PURE / DETERMINISTIC / OFFLINE.
  - No SDK import (no infrared, no requests, no httpx, no network calls).
  - No file I/O, no environment variables, no global state.
  - Returns the same output for the same input every time.

Role in Phase 2:
  The optimizer (Plan 02-03) runs two objectives:
    1. Thermal objective  — delta_tmrt_surrogate() from coolspend.surrogate
    2. Ecological objective — ecological_score() from THIS module (RULES-01 + RULES-02)

  Only TWO ecological rules are implemented here, as per PROJECT.md "Ship as 2-objective"
  decision and CONCERNS 1.2 (degenerate pollinator-corridor objective excluded):
    RULES-01  minimum-spacing penalty
    RULES-02  species-diversity score (Shannon index, normalised)

  NOTE — POLLINATOR CORRIDOR DELIBERATELY EXCLUDED (CONCERNS 1.2):
  The reference code (nature_nsga2_coolstock.py) contains a pollinator_corridor_score()
  that applies a y-clamp heritage-buffer correction. Under the actual site geometry this
  objective degenerates to a near-constant and provides no discriminating gradient for
  the optimizer. Per PROJECT.md key decision "Ship as 2-objective (thermal + ecological)",
  the pollinator corridor is NOT implemented here. Adding it would violate the honesty
  contract — shipping a metric that cannot discriminate is misleading.

Tree config contract (dict shape — same for all Phase 2 modules):
    config = {
        "trees": [
            {"x_m": 12.5, "y_m": 8.0, "species": "platanus"},
            {"x_m": 30.0, "y_m": 20.0, "species": "celtis"},
            # inactive slots carry "active": False
        ],
    }

Coordinates are plaza-local metres (x_m/y_m, SW corner = (0,0)) — CONCERNS 2.3.
"""
from __future__ import annotations

import math
from itertools import combinations

from coolspend.spatial_engine import SITE_DEPTH_M, SITE_WIDTH_M, STREET_BUFFER_M  # noqa: F401

# ── MODULE-LEVEL CONSTANTS ────────────────────────────────────────────────────
# SOURCE: DECLARED — these are demo/planning assumptions, not surveyed values.
# No independent citation; flagged REQUIRES_VERIFICATION in MOCKS.md.

MIN_SPACING_M: float = 4.0
"""Minimum crown-clearance between street trees, metres. SOURCE: DECLARED.
Typical urban street-tree planting guideline; unverified for Barcelona/MACBA site.
REQUIRES_VERIFICATION against Barcelona municipal tree-planting code."""

SPECIES_PALETTE: tuple[str, ...] = ("platanus", "celtis", "tilia", "quercus")
"""Demo resilient species mix for Plaça dels Àngels context. SOURCE: DECLARED.
Selected from common Mediterranean urban-resilient species; no documented source.
REQUIRES_VERIFICATION against Barcelona 'Arbrat Viari' recommended-species list."""


# ── HELPER ────────────────────────────────────────────────────────────────────


def _active_trees(config: dict) -> list[dict]:
    """Return only the active trees from a config dict.

    Trees are active by default; pass ``"active": False`` to exclude a slot.
    Tolerates missing "trees" key (returns []).

    Args:
        config: Tree configuration dict with optional "trees" list.

    Returns:
        List of tree dicts where ``t.get("active", True)`` is truthy.
    """
    return [t for t in config.get("trees", []) if t.get("active", True)]


# ── RULES-01: MINIMUM-SPACING PENALTY ────────────────────────────────────────


def spacing_penalty(config: dict, min_spacing_m: float = MIN_SPACING_M) -> float:
    """Compute the minimum-spacing penalty for a tree configuration. (RULES-01)

    For each unordered pair of active trees, compute the Euclidean distance
    between their (x_m, y_m) coordinates. Pairs closer than ``min_spacing_m``
    contribute ``(min_spacing_m - dist) / min_spacing_m`` to the total penalty
    (a value in (0, 1]). Pairs at or above the minimum distance contribute 0.

    The formula is intentionally linear in the violation depth so the gradient
    is smooth for the NSGA-II optimizer. A pair exactly at the minimum distance
    yields exactly 0.0 (not negative — clamped via max).

    Args:
        config:        Tree configuration dict (see module docstring).
        min_spacing_m: Minimum acceptable spacing in metres. Defaults to
                       ``MIN_SPACING_M`` (4.0 m, DECLARED).

    Returns:
        Total penalty >= 0.0.  Returns 0.0 for 0 or 1 active trees (no pairs).
    """
    trees = _active_trees(config)
    if len(trees) < 2:
        return 0.0

    penalty = 0.0
    for t_a, t_b in combinations(trees, 2):
        dx = t_a["x_m"] - t_b["x_m"]
        dy = t_a["y_m"] - t_b["y_m"]
        dist = math.sqrt(dx * dx + dy * dy)
        # Guard: never go negative (pairs exactly at min_spacing_m → 0.0)
        violation = max(0.0, (min_spacing_m - dist) / min_spacing_m)
        penalty += violation

    return penalty


# ── RULES-02: SPECIES-DIVERSITY SCORE ────────────────────────────────────────


def species_diversity_score(config: dict) -> float:
    """Compute the species-diversity score for a tree configuration. (RULES-02)

    Uses the Shannon diversity index H = -sum(p_i * ln(p_i)) normalised by
    ln(n_distinct) so that:
      - A perfectly balanced mix of N species → 1.0
      - A monoculture (all same species) → 0.0
      - < 2 active trees → 0.0 (no meaningful diversity signal)

    Guards:
      - log(0) guard: probabilities are computed from positive counts; no
        p_i can be zero in the sum.
      - n_distinct == 1 fallback: Shannon normaliser ln(1) = 0, which would
        cause division by zero. In this case diversity is 0.0 by definition
        (monoculture), returned directly before the division.

    Args:
        config: Tree configuration dict (see module docstring).

    Returns:
        Float in [0.0, 1.0]. Higher = more species-diverse.
    """
    trees = _active_trees(config)
    if len(trees) < 2:
        return 0.0

    # Count species occurrences
    counts: dict[str, int] = {}
    for t in trees:
        sp = t.get("species", "unknown")
        counts[sp] = counts.get(sp, 0) + 1

    n_distinct = len(counts)
    if n_distinct < 2:
        # Monoculture: Shannon H = 0 → normalised score = 0.0
        return 0.0

    n_total = float(len(trees))
    h = 0.0
    for count in counts.values():
        p_i = count / n_total
        # p_i > 0 by construction (only keys with count >= 1 are in dict)
        h -= p_i * math.log(p_i)

    # Normalise: H_max = ln(n_distinct) for a balanced mix
    h_max = math.log(n_distinct)
    # h_max > 0 because n_distinct >= 2, so ln(n_distinct) >= ln(2) > 0
    return h / h_max


# ── COMBINED ECOLOGICAL SCORE ─────────────────────────────────────────────────


def ecological_score(config: dict) -> float:
    """Combine spacing penalty and diversity score into a single [0, 1] float.

    The combined ecological coherence score is the NSGA-II second objective
    (higher = more ecologically coherent). It weights spacing and diversity
    equally (50/50):

        norm_penalty = spacing_penalty(config) / max(1, n_pairs)
        coherence    = 0.5 * (1 - min(1.0, norm_penalty))
                     + 0.5 * species_diversity_score(config)

    Normalising by n_pairs keeps the penalty comparable across tree counts.
    min(1.0, ...) clamps extreme close-packing cases to the [0, 1] range.

    Args:
        config: Tree configuration dict (see module docstring).

    Returns:
        Float in [0.0, 1.0], rounded to 4 decimal places. Deterministic.
    """
    trees = _active_trees(config)
    n = len(trees)

    if n < 2:
        # With 0 or 1 tree: spacing contribution is perfect (0 penalty → 0.5),
        # but diversity is 0.0 (< 2 trees). Net = 0.5 * 1.0 + 0.5 * 0.0 = 0.5
        # HOWEVER: a config with 0 trees should return 0.0 (nothing coherent).
        if n == 0:
            return 0.0
        # 1 tree: no pairs, no diversity → 0.0 (semantically empty)
        return 0.0

    n_pairs = n * (n - 1) // 2  # total unordered pairs; always >= 1 here

    raw_penalty = spacing_penalty(config)
    norm_penalty = raw_penalty / max(1, n_pairs)

    spacing_term = 0.5 * (1.0 - min(1.0, norm_penalty))
    diversity_term = 0.5 * species_diversity_score(config)

    coherence = spacing_term + diversity_term

    # Clamp to [0.0, 1.0] for robustness, then round to 4 dp
    clamped = max(0.0, min(1.0, coherence))
    return round(clamped, 4)


# ── SMOKE TEST (python -m coolspend.rules_engine) ─────────────────────────────

if __name__ == "__main__":
    # Close-packed monoculture (worst ecological coherence)
    monoculture_close = {
        "trees": [
            {"x_m": 0.0, "y_m": 0.0, "species": "platanus"},
            {"x_m": 0.5, "y_m": 0.0, "species": "platanus"},
            {"x_m": 1.0, "y_m": 0.0, "species": "platanus"},
        ]
    }

    # Well-spaced diverse mix (best ecological coherence)
    diverse_spaced = {
        "trees": [
            {"x_m": 0.0,  "y_m": 0.0,  "species": "platanus"},
            {"x_m": 10.0, "y_m": 0.0,  "species": "celtis"},
            {"x_m": 20.0, "y_m": 0.0,  "species": "tilia"},
            {"x_m": 30.0, "y_m": 10.0, "species": "quercus"},
        ]
    }

    print("=" * 60)
    print("CoolSpend rules_engine.py — offline smoke test")
    print("=" * 60)

    for label, cfg in [("close monoculture", monoculture_close),
                       ("spaced diverse mix", diverse_spaced)]:
        sp = spacing_penalty(cfg)
        div = species_diversity_score(cfg)
        eco = ecological_score(cfg)
        print(f"\n[{label}]")
        print(f"  spacing_penalty          = {sp:.4f}")
        print(f"  species_diversity_score  = {div:.4f}")
        print(f"  ecological_score         = {eco:.4f}")

    print("\n[Constants]")
    print(f"  MIN_SPACING_M   = {MIN_SPACING_M}  # SOURCE: DECLARED — REQUIRES_VERIFICATION")
    print(f"  SPECIES_PALETTE = {SPECIES_PALETTE}  # SOURCE: DECLARED — REQUIRES_VERIFICATION")
    print(f"  SITE_WIDTH_M    = {SITE_WIDTH_M}  (from spatial_engine)")
    print(f"  SITE_DEPTH_M    = {SITE_DEPTH_M}  (from spatial_engine)")
    print(f"  STREET_BUFFER_M = {STREET_BUFFER_M}  (from spatial_engine)")
    print("\nSmoke test complete — no network calls made.")
