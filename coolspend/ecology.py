"""
coolspend/ecology.py — per-species ECOSYSTEM profile + ecosystem-health composite.

"You don't plant a tree, you install an ecosystem." This layer attaches the
ecological dimensions a cooling number can't capture — drought/heat fitness,
biodiversity and pollinator value, allergenicity, pest/disease risk, longevity,
water/maintenance burden, and invasive status — and combines them into one
auditable ecosystem-health score (0–1) reported ALONGSIDE the €/m²-cooled KPI
(never blended into it).

Data: coolspend/docs/species_ecology_traits.md (cited; OPALS allergy anchored to
the Ogren scale; values flagged REQUIRES_VERIFICATION there are carried as
declared estimates). Barcelona strategy context (no species >15%; phase down
Platanus; exclude invasives Ailanthus/Robinia/Fraxinus ornus): see
coolspend/docs/bcn_planting_strategy.md.

HONESTY: these are species-typical, literature-anchored estimates for SELECTION /
RANKING — not measured per-tree values. The composite weights are DECLARED design
choices and are sensitivity-testable (see coolspend.sensitivity).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ecology:
    scientific: str
    native_status: str          # "native …" | "naturalised" | "exotic" | "exotic-invasive"
    drought_heat_tolerance: float  # 0–1 (higher better under BCN climate change)
    biodiversity_value: float      # 0–1
    pollinator_value: float        # 0–1
    allergenicity: float           # 0–1 (OPALS/10; higher = WORSE)
    pest_disease_risk: float       # 0–1 (higher = WORSE)
    longevity_years: int           # typical urban midpoint
    growth_rate: str               # slow | medium | fast
    water_demand: str              # low | medium | high
    maintenance_burden: str        # low | medium | high
    carbon_sequestration: float    # 0–1 (size×longevity×growth proxy; NOT measured biomass)
    mycorrhizal_type: str          # AM | EM | mixed
    invasive: bool                 # exotic-invasive in Catalonia / hard penalty
    notes: str = ""


# ── Per-species table (coolspend/docs/species_ecology_traits.md) ───────────────
_TABLE: tuple[Ecology, ...] = (
    Ecology("Platanus x acerifolia", "exotic (hybrid)", 0.75, 0.35, 0.15, 0.85, 0.85, 115, "fast", "medium", "high", 0.90, "AM", False,
            "Worst allergy+disease load of the palette (Corythucha ciliata + lethal Ceratocystis platani); Barcelona is phasing it down from ~30% toward ~12%."),
    Ecology("Celtis australis", "native Mediterranean", 0.85, 0.60, 0.35, 0.80, 0.30, 115, "medium", "low", "low", 0.80, "AM", False,
            "Mediterranean-native, drought-hardy, long-lived, low input — a lead climate-resilient recommendation for Barcelona."),
    Ecology("Styphnolobium japonicum", "exotic", 0.80, 0.55, 0.85, 0.30, 0.25, 75, "medium", "low", "medium", 0.55, "AM", False,
            "Heavy late-summer bee forage (Fabaceae, N-fixing); non-invasive. Allergenicity low but REQUIRES_VERIFICATION (not in OPALS subset)."),
    Ecology("Tipuana tipu", "exotic", 0.90, 0.45, 0.80, 0.30, 0.30, 65, "fast", "low", "high", 0.75, "AM", False,
            "Photosynthesis rises under heat/drought; strong bee forage. Surface roots lift pavement (high maintenance)."),
    Ecology("Melia azedarach", "naturalised", 0.90, 0.40, 0.50, 0.40, 0.25, 40, "fast", "low", "high", 0.45, "AM", False,
            "Very drought/pollution tolerant but short-lived, brittle, heavy toxic-drupe litter; weedy elsewhere (Catalan invasive status REQUIRES_VERIFICATION)."),
    Ecology("Brachychiton populneus", "exotic", 0.95, 0.35, 0.45, 0.30, 0.20, 80, "slow", "low", "low", 0.55, "AM", False,
            "Best drought tolerance + lowest input of the palette (water-storing trunk); safe low-allergen non-invasive choice."),
    Ecology("Ligustrum lucidum", "exotic-invasive", 0.80, 0.45, 0.45, 0.80, 0.25, 55, "fast", "low", "medium", 0.45, "AM", True,
            "Bird-dispersed invasive forming monospecific stands; high allergen (OPALS 8). Invasive penalty applies."),
    Ecology("Jacaranda mimosifolia", "exotic", 0.70, 0.40, 0.70, 0.40, 0.20, 75, "medium", "medium", "medium", 0.55, "AM", False,
            "Showy violet bloom attracts bees/butterflies; one of the lower-allergen members (OPALS 4); non-invasive."),
    Ecology("Ulmus pumila", "exotic-invasive", 0.90, 0.45, 0.20, 0.80, 0.45, 65, "fast", "low", "high", 0.60, "mixed", True,
            "DED-tolerant and hardy but invasive (wind-seeded), brittle, high allergen (OPALS 8). Invasive penalty applies."),
    Ecology("Cercis siliquastrum", "native Mediterranean", 0.80, 0.50, 0.75, 0.25, 0.25, 60, "slow", "low", "low", 0.35, "AM", False,
            "Mediterranean-native, bee-pollinated, small-stature (good under wires), low allergen and low input."),
    Ecology("Robinia pseudoacacia", "exotic-invasive", 0.90, 0.40, 0.90, 0.50, 0.30, 65, "fast", "low", "high", 0.60, "mixed", True,
            "Top pollinator/honey tree BUT invasive in Catalonia (alters soil N, suckers, brittle, thorny) — invasive veto outweighs nectar value."),
    Ecology("Magnolia grandiflora", "exotic", 0.55, 0.30, 0.45, 0.50, 0.15, 100, "slow", "medium", "medium", 0.65, "AM", False,
            "Least drought-adapted of the palette (needs moisture) — a poorer fit for a drying Barcelona without irrigation."),
)


# ── Composite weights (DECLARED; sensitivity-testable — see coolspend.sensitivity) ──
# Benefits sum to 1.0; penalties subtract; invasive is a hard veto-scale penalty.
# Cooling/canopy and carbon are deliberately EXCLUDED to avoid double-counting the
# Infrared UTCI thermal objective and the €/m²-cooled KPI.
_W_DROUGHT = 0.30
_W_BIODIV = 0.20
_W_POLLINATOR = 0.20
_W_LONGEVITY = 0.15
_W_NATIVE = 0.15
_P_ALLERGEN = 0.15
_P_PEST = 0.10
_P_WATER = 0.10
_P_MAINT = 0.10
_INVASIVE_PENALTY = 0.30

_NATIVE_SCORE = {
    "native": 1.0,
    "naturalised": 0.6,
    "exotic": 0.4,
    "exotic-invasive": 0.0,
}
_LEVEL = {"low": 0.2, "medium": 0.55, "high": 0.9}
_LONGEVITY_MIN, _LONGEVITY_MAX = 30.0, 150.0


def _norm_key(name: str) -> str:
    return " ".join(name.replace("×", "x").lower().split())


_BY_NAME: dict[str, Ecology] = {_norm_key(e.scientific): e for e in _TABLE}


def _native_score(status: str) -> float:
    s = status.lower()
    if "invasive" in s:
        return _NATIVE_SCORE["exotic-invasive"]
    if "native" in s:
        return _NATIVE_SCORE["native"]
    if "naturalis" in s or "naturaliz" in s:
        return _NATIVE_SCORE["naturalised"]
    return _NATIVE_SCORE["exotic"]


def _longevity_norm(years: int) -> float:
    return max(0.0, min(1.0, (years - _LONGEVITY_MIN) / (_LONGEVITY_MAX - _LONGEVITY_MIN)))


def ecosystem_score(e: Ecology) -> float:
    """Composite ecosystem-health score in [0, 1].

    benefits − penalties − invasive_veto, each dimension normalised to 0–1.
    Reported ALONGSIDE €/m²-cooled, never blended into it. Cooling/carbon are
    excluded to avoid double-counting the thermal objective.
    """
    benefits = (
        _W_DROUGHT * e.drought_heat_tolerance
        + _W_BIODIV * e.biodiversity_value
        + _W_POLLINATOR * e.pollinator_value
        + _W_LONGEVITY * _longevity_norm(e.longevity_years)
        + _W_NATIVE * _native_score(e.native_status)
    )
    penalties = (
        _P_ALLERGEN * e.allergenicity
        + _P_PEST * e.pest_disease_risk
        + _P_WATER * _LEVEL[e.water_demand]
        + _P_MAINT * _LEVEL[e.maintenance_burden]
        + (_INVASIVE_PENALTY if e.invasive else 0.0)
    )
    return round(max(0.0, min(1.0, benefits - penalties)), 4)


# Species Barcelona is actively PHASING DOWN (do not plant more), distinct from
# exotic-invasive. Platanus × acerifolia (London plane) is ~27% of the street-tree
# population — far above the Pla Director de l'Arbrat's 15%-per-species cap, and
# targeted down to ~12% by 2037 — plus high pollen-allergen + the worst pest/disease
# load (Corythucha ciliata, Ceratocystis platani). So new plantings exclude it.
_PHASE_DOWN: frozenset[str] = frozenset({_norm_key("Platanus x acerifolia")})


def get_ecology(scientific: str) -> Ecology | None:
    return _BY_NAME.get(_norm_key(scientific))


# Typical urban time-to-near-mature-canopy by growth rate (years). Arboricultural
# consensus / i-Tree establishment ranges; consistent with the climate-responsive
# skill's "trees at 8–10 m create continuous canopy at maturity (20–30 years)".
# This is what makes the "years after planting" growth species-specific rather than
# one flat ramp — a fast Tipuana fills its crown ~2× sooner than a slow Cercis.
_MATURITY_YEARS = {"fast": 20, "medium": 30, "slow": 40}


def maturity_years(scientific: str) -> int:
    """Years to near-mature canopy for a species (from its growth_rate band)."""
    e = get_ecology(scientific)
    return _MATURITY_YEARS.get(e.growth_rate if e else "medium", 30)


def is_plantable(scientific: str) -> bool:
    """Whether a species may be used for NEW plantings in Barcelona.

    Excludes (a) exotic-invasive species (Robinia, Ligustrum lucidum, Ulmus pumila)
    and (b) over-represented phase-down species (Platanus × acerifolia, ~27% of the
    city's trees). Single source of truth for the optimizer and the greedy placer.
    """
    if _norm_key(scientific) in _PHASE_DOWN:
        return False
    eco = get_ecology(scientific)
    return not (eco and eco.invasive)


def ecology_public(scientific: str) -> dict | None:
    """Web/inspect-panel payload for a species' ecology (None if not in the table).

    Consumed by coolspend.bcn_species.species_public so the tree's ecology rides
    along in trees.geojson and renders in the click-inspect panel.
    """
    e = get_ecology(scientific)
    if e is None:
        return None
    return {
        "native_status": e.native_status,
        "drought_heat_tolerance": e.drought_heat_tolerance,
        "biodiversity_value": e.biodiversity_value,
        "pollinator_value": e.pollinator_value,
        "allergenicity": e.allergenicity,
        "pest_disease_risk": e.pest_disease_risk,
        "longevity_years": e.longevity_years,
        "growth_rate": e.growth_rate,
        "maturity_years": _MATURITY_YEARS.get(e.growth_rate, 30),
        "water_demand": e.water_demand,
        "maintenance_burden": e.maintenance_burden,
        "carbon_sequestration": e.carbon_sequestration,
        "mycorrhizal_type": e.mycorrhizal_type,
        "invasive": e.invasive,
        "ecosystem_score": ecosystem_score(e),
        "notes": e.notes,
    }


# Stable export of the whole table for diversity/optimizer use.
ECOLOGY_TABLE = _TABLE


if __name__ == "__main__":
    print(f"{'species':<26}{'native':<22}{'eco':>6}  notes")
    for e in sorted(_TABLE, key=ecosystem_score, reverse=True):
        print(f"{e.scientific:<26}{e.native_status:<22}{ecosystem_score(e):>6.3f}")
