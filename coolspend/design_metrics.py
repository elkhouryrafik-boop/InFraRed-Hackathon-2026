"""
coolspend/design_metrics.py — urban-design metrics for a tree-planting layout.

Displayable, defensible metrics derived from the urban-design skill audit
(street-design, climate-responsive-design, public-space-design, sustainability-
scoring, urban-design-foundations). Pure functions over a placed-tree layout +
its site — no network, no sim.

Sourced rules of thumb (cited in the skills):
  - Canopy footprint per tree = π·(crown_radius)²  (crown from bcn_species bands).
  - Air-temperature relief ≈ 0.5–1.0 °C per +10% canopy cover (shade +
    evapotranspiration) → ~0.075 °C per +1 percentage-point of canopy cover
    (climate-responsive-design UHI section; midpoint of the 0.5–1.0 band).
  - Mediterranean street canopy-cover target 30–40% (climate-responsive-design;
    C40 / 3-30-300). We report the gain and the distance to a 30% target.
  - person-degrees = people_served × mean UTCI reduction — a people-weighted
    heat-relief metric (combines reach with cooling depth).

HONESTY: canopy cover and the ΔT estimate are mature-canopy GEOMETRIC estimates
(crown disks), NOT measured leaf-area or a microclimate sim. The measured cooling
is the Infrared UTCI ΔUTCI; these metrics frame the urban-design story around it.
"""
from __future__ import annotations

import math

# Midpoint of the climate-responsive 0.5–1.0 °C per +10% canopy → per 1%.
_DEG_C_PER_CANOPY_PCT: float = 0.075
# Mediterranean street canopy-cover target (climate-responsive-design / C40).
CANOPY_TARGET_PCT: float = 30.0


def _crown_radius_m(species: str) -> float:
    """Mature canopy radius (m) for a species, from the BCN bands (fallback 3 m)."""
    try:
        from coolspend.bcn_species import get_species  # noqa: PLC0415
        sp = get_species(species or "")
        if sp:
            return sp.crown_diameter_m / 2.0
    except Exception:  # noqa: BLE001
        pass
    return 3.0


def canopy_area_m2(trees: list[dict]) -> float:
    """Total mature canopy footprint (m²) = Σ π·r² over placed trees.

    Non-overlapping assumption (trees are ≥8 m spaced, crowns ~5–10 m, so overlap
    is modest); this is the standard 'crown projected area' canopy figure.
    """
    total = 0.0
    for t in trees or []:
        r = _crown_radius_m(t.get("species", ""))
        total += math.pi * r * r
    return round(total, 1)


def design_metrics(
    trees: list[dict],
    site_area_m2: float | None,
    cost_eur: float | None,
    plantable_area_m2: float | None = None,
) -> dict:
    """Urban-design metric bundle for one site's planting.

    Canopy cover is reported against TWO denominators (PAPER limitation #7):
      * the sampled CELL area (``site_area_m2``) — comparable city-wide, but
        understates a small intervention in a large cell;
      * the PLANTABLE strip (``plantable_area_m2``, boundary minus buildings and
        street/furniture buffers) — the truer LOCAL intensity of the planting.
    The headline ``canopy_cover_pct`` uses the plantable strip when available
    (truer locally), and ``canopy_cover_denominator`` records which was used.
    The ambient-ΔT estimate stays keyed to the CELL cover, because the
    0.075 °C / +1% coefficient is a neighbourhood-scale relationship, not a
    plantable-strip one.

    Args:
        trees: placed trees (each with 'species').
        site_area_m2: sampled cell area for the comparable cover %, or None.
        cost_eur: site spend for canopy-per-euro, or None.
        plantable_area_m2: plantable strip area for the truer local cover %, or None.
    """
    canopy = canopy_area_m2(trees)
    out: dict = {
        "tree_count": len(trees or []),
        "canopy_area_m2": canopy,
        "canopy_m2_per_1000eur": round(canopy / (cost_eur / 1000.0), 1) if cost_eur else None,
    }

    cover_cell = None
    if site_area_m2 and site_area_m2 > 0:
        cover_cell = round(100.0 * canopy / site_area_m2, 1)
        out["canopy_cover_pct_cell"] = cover_cell

    cover_plant = None
    if plantable_area_m2 and plantable_area_m2 > 0:
        cover_plant = round(min(100.0, 100.0 * canopy / plantable_area_m2), 1)
        out["canopy_cover_pct_plantable"] = cover_plant
        out["plantable_area_m2"] = round(plantable_area_m2, 1)

    # Headline cover: prefer the plantable strip (truer locally); record which.
    headline = cover_plant if cover_plant is not None else cover_cell
    if headline is not None:
        out["canopy_cover_pct"] = headline
        out["canopy_cover_denominator"] = (
            "plantable_strip" if cover_plant is not None else "sampled_cell"
        )
        out["canopy_target_pct"] = CANOPY_TARGET_PCT
        out["canopy_gap_to_target_pct"] = round(max(0.0, CANOPY_TARGET_PCT - headline), 1)

    # Ambient relief uses the CELL cover (neighbourhood-scale coefficient).
    ambient_basis = cover_cell if cover_cell is not None else headline
    if ambient_basis is not None:
        out["est_air_temp_drop_c"] = round(ambient_basis * _DEG_C_PER_CANOPY_PCT, 2)
    return out


def person_degrees(people_served: float | None, mean_utci_drop_c: float | None) -> float | None:
    """People-weighted heat relief: residents served × mean UTCI °C reduction."""
    if not people_served or not mean_utci_drop_c:
        return None
    return round(float(people_served) * float(mean_utci_drop_c), 1)
