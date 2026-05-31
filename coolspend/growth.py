"""Species-specific canopy growth over time (the "years after planting" model).

PAPER limitation (growth accuracy): the old establishment curve was a single
flat *linear* ramp (0.2 → 1.0 over 25 yr) applied to every species. Real crown
growth is sigmoid and species-paced. This module replaces the linear ramp with
a **Chapman–Richards** growth function — the standard forestry/urban-tree growth
form — anchored to two values we already hold per species:

    * mature crown diameter  (coolspend.bcn_species, from the BCN inventory bands)
    * time-to-near-mature-canopy (coolspend.ecology.maturity_years: 20/30/40 yr)

We do NOT invent per-species fitted coefficients. We fit the single rate
parameter ``k`` so the curve reaches 95 % of the mature crown at the species'
maturity year, start from a realistic large-caliper nursery crown, and use the
classic sigmoid shape exponent. The result is a defensible parametric curve per
species — strictly more honest than one linear ramp — that can later be swapped
for measured i-Tree/Pretzsch species coefficients without changing the call
sites.

Form:  crown(age) = max(PLANTING_CROWN_M, A · (1 − e^(−k·age))^P)
where A = mature crown, P = 3 (sigmoid), k solved from maturity_years.
Cooling/shade scales with crown AREA, so cooling_fraction = (crown/A)^2.
"""
from __future__ import annotations

import math

# Large-caliper (20–25 cm) nursery stock — the planting crown at age 0. This is
# the standard street-tree planting stock the cost model already prices (€600
# tree_stock line). Crown of such stock is ~1.5 m.
PLANTING_CROWN_M: float = 1.5

# Sigmoid shape exponent of the Chapman–Richards form. P=3 gives the slow-fast-
# plateau shape typical of broadleaf urban trees.
_SHAPE_P: float = 3.0

# We anchor "near-mature" at 95 % of the mature crown at maturity_years.
_MATURITY_FRACTION: float = 0.95


def _rate_k(maturity_years: float) -> float:
    """Solve k so (1 − e^(−k·T))^P = 0.95 at T = maturity_years."""
    if maturity_years <= 0:
        return 1.0
    inner = 1.0 - _MATURITY_FRACTION ** (1.0 / _SHAPE_P)  # = e^(−k·T)
    return -math.log(inner) / maturity_years


def crown_diameter_at_age(scientific: str, age_years: float) -> float:
    """Mature-anchored crown diameter (m) at a given age after planting."""
    from coolspend.bcn_species import get_species  # noqa: PLC0415
    from coolspend.ecology import maturity_years  # noqa: PLC0415

    sp = get_species(scientific)
    mature = sp.crown_diameter_m if sp else 6.0
    if age_years <= 0:
        return PLANTING_CROWN_M
    k = _rate_k(float(maturity_years(scientific)))
    raw = mature * (1.0 - math.exp(-k * age_years)) ** _SHAPE_P
    return max(PLANTING_CROWN_M, min(mature, raw))


def cooling_fraction_at_age(scientific: str, age_years: float) -> float:
    """Fraction of mature shade/cooling delivered at a given age (0–1).

    Shade scales with crown projected AREA, so this is (crown(age)/mature)^2.
    At age 0 it is the (small) nursery-crown fraction, not zero.
    """
    from coolspend.bcn_species import get_species  # noqa: PLC0415

    sp = get_species(scientific)
    mature = sp.crown_diameter_m if sp else 6.0
    if mature <= 0:
        return 1.0
    return min(1.0, (crown_diameter_at_age(scientific, age_years) / mature) ** 2)


def growth_params(scientific: str) -> dict:
    """Per-species curve parameters, for the frontend to render the same curve.

    Returns the values the JS port (web/src/lib/growth.ts) needs to compute the
    identical Chapman–Richards crown(age) live for the age slider.
    """
    from coolspend.bcn_species import get_species  # noqa: PLC0415
    from coolspend.ecology import maturity_years  # noqa: PLC0415

    sp = get_species(scientific)
    mature = sp.crown_diameter_m if sp else 6.0
    my = float(maturity_years(scientific))
    return {
        "mature_crown_m": mature,
        "maturity_years": my,
        "planting_crown_m": PLANTING_CROWN_M,
        "shape_p": _SHAPE_P,
        "rate_k": round(_rate_k(my), 5),
    }
