"""
coolspend/bcn_species.py — per-species attribute + cooling-proxy table for Barcelona.

This is the "know each tree before you place it" layer. The municipal inventory
(bcn_data.py) has species + position but NO dimensions (removed 2021). This table
attaches, for Barcelona's most-planted REAL street species (verified top species in
arbrat-viari, see DATA_SOURCES.md §A):
  - crown_diameter_m, height_m   — Verd Urbà band midpoints (Diputació de Barcelona)
  - leaf_cycle                   — deciduous / evergreen
  - shade_density                — dense / medium / light (canopy/LAI proxy)
  - cooling_score                — 0–1 proxy ranking summer shade-cooling potential

HONESTY (DATA_SOURCES.md §C/§E):
  * Dimensions are species-typical Verd Urbà BANDS → midpoints (categorical, not
    measured per tree). The `band` field records the source band so it is auditable.
  * cooling_score is a literature-backed PROXY for SPECIES SELECTION/RANKING only —
    crown projected area × shade-density weight × summer-leaf weight (Rahman et al.
    2020 Int J Biometeorol; tree-trait→cooling meta-analyses). It is NOT a measured
    cooling figure. The ground-truth cooling per placement comes from the live
    infrared.city UTCI simulation (sdk_client._live_utci).

Verd Urbà band midpoints used:
  height : Baixa(<6)->4 ; Mitjana(6-15)->10 ; Alta(>15)->18
  crown  : Estreta(2-4)->3 ; Mitjana(4-6)->5 ; Ampla(6-8)->7 ; Molt ampla(>8)->10
  shade  : Densa->1.0 ; Mitjana->0.7 ; Lleugera->0.45  (canopy-density / LAI proxy)
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Species:
    """One Barcelona street-tree species with sourced attributes + cooling proxy."""

    scientific: str          # cat_nom_cientific join key (matches arbrat-viari)
    common: str              # English common name
    height_m: float          # Verd Urbà height band midpoint
    crown_diameter_m: float  # Verd Urbà crown band midpoint
    leaf_cycle: str          # "deciduous" | "evergreen"
    shade_density: str       # "dense" | "medium" | "light"
    height_band: str         # Verd Urbà band label (auditable)
    crown_band: str          # Verd Urbà band label (auditable)


# Shade-density / summer-leaf weights for the cooling proxy.
_SHADE_W = {"dense": 1.0, "medium": 0.7, "light": 0.45}
# July UTCI window: deciduous are at full summer leaf; evergreen slightly lower LAI.
_LEAF_W = {"deciduous": 1.0, "evergreen": 0.85}

# Barcelona's most-planted REAL street species (top of arbrat-viari, 145k trees).
# Dimensions = Verd Urbà band midpoints; leaf/shade = Verd Urbà + standard
# arboricultural references. DECLARED, auditable bands (DATA_SOURCES.md §B/§E).
SPECIES_TABLE: tuple[Species, ...] = (
    Species("Platanus x acerifolia", "London plane", 18.0, 10.0, "deciduous", "dense", "Alta", "Molt ampla"),
    Species("Celtis australis", "European hackberry", 18.0, 7.0, "deciduous", "dense", "Alta", "Ampla"),
    Species("Styphnolobium japonicum", "Japanese pagoda tree", 10.0, 7.0, "deciduous", "medium", "Mitjana", "Ampla"),
    Species("Tipuana tipu", "Tipa", 18.0, 10.0, "deciduous", "dense", "Alta", "Molt ampla"),
    Species("Melia azedarach", "Chinaberry", 10.0, 7.0, "deciduous", "medium", "Mitjana", "Ampla"),
    Species("Brachychiton populneus", "Kurrajong", 10.0, 5.0, "evergreen", "medium", "Mitjana", "Mitjana"),
    Species("Ligustrum lucidum", "Glossy privet", 10.0, 5.0, "evergreen", "dense", "Mitjana", "Mitjana"),
    Species("Jacaranda mimosifolia", "Jacaranda", 10.0, 7.0, "deciduous", "medium", "Mitjana", "Ampla"),
    Species("Ulmus pumila", "Siberian elm", 18.0, 7.0, "deciduous", "medium", "Alta", "Ampla"),
    Species("Cercis siliquastrum", "Judas tree", 4.0, 5.0, "deciduous", "medium", "Baixa", "Mitjana"),
    Species("Robinia pseudoacacia", "Black locust", 18.0, 7.0, "deciduous", "medium", "Alta", "Ampla"),
    Species("Magnolia grandiflora", "Southern magnolia", 10.0, 5.0, "evergreen", "dense", "Mitjana", "Mitjana"),
)

def _norm_key(name: str) -> str:
    """Normalise a scientific name for joining table ↔ inventory.

    The Open Data BCN inventory mixes hybrid-marker conventions: some names use the
    U+00D7 MULTIPLICATION SIGN ("Platanus × acerifolia") while others use ASCII "x"
    ("Tilia x euchlora"). Our SPECIES_TABLE uses ASCII "x". Without normalisation the
    single most-planted street species (Platanus × acerifolia, ~28% of the inventory)
    silently fails the join and degrades to the neutral cooling weight.

    Maps "×" → "x", lowercases, and collapses runs of whitespace.
    """
    return " ".join(name.replace("×", "x").lower().split())


_BY_SCIENTIFIC: dict[str, Species] = {_norm_key(s.scientific): s for s in SPECIES_TABLE}


def crown_projected_area_m2(sp: Species) -> float:
    """Crown projected (plan) area in m² from the crown-diameter band midpoint."""
    return math.pi * (sp.crown_diameter_m / 2.0) ** 2


def _raw_cooling(sp: Species) -> float:
    """Unnormalised cooling proxy: crown area × shade-density × summer-leaf weight."""
    return crown_projected_area_m2(sp) * _SHADE_W[sp.shade_density] * _LEAF_W[sp.leaf_cycle]


# Normalised cooling_score in [0, 1] across the palette (selection/ranking only).
_MAX_RAW = max(_raw_cooling(s) for s in SPECIES_TABLE)


def cooling_score(sp: Species) -> float:
    """Cooling proxy normalised to [0, 1] across the palette. RANKING ONLY (not °C)."""
    return round(_raw_cooling(sp) / _MAX_RAW, 4)


def get_species(scientific: str) -> Species | None:
    """Look up a species by its scientific name (arbrat-viari cat_nom_cientific).

    Join is normalised (hybrid "×"↔"x", case, whitespace) so the real inventory
    spelling matches the table — see _norm_key.
    """
    return _BY_SCIENTIFIC.get(_norm_key(scientific))


# Scientific names in palette order (stable index for the optimizer's species gene).
SCIENTIFIC_NAMES: tuple[str, ...] = tuple(s.scientific for s in SPECIES_TABLE)

_DEFAULT_COOLING_WEIGHT: float = 0.5  # unknown species -> neutral midpoint


def cooling_score_by_name(scientific: str) -> float:
    """cooling_score in [0,1] for a scientific name; neutral 0.5 if unknown.

    Used to weight the optimizer's thermal objective so it prefers higher-cooling
    species (ranking proxy; the live Infrared UTCI is the ground truth).
    """
    sp = _BY_SCIENTIFIC.get(_norm_key(scientific))
    return cooling_score(sp) if sp is not None else _DEFAULT_COOLING_WEIGHT


_DEFAULT_CROWN_M: float = 6.0
_DEFAULT_HEIGHT_M: float = 10.0


def species_public(scientific: str) -> dict:
    """Per-species display payload for the web (tree props + inspect panel).

    SINGLE SOURCE OF TRUTH so the exporter and the UI never drift. The ecology
    layer extends this dict with its EcologyProfile fields (biodiversity,
    drought tolerance, etc.) via the same function — this is the join point.
    """
    sp = get_species(scientific)
    if sp is None:
        crown = _DEFAULT_CROWN_M
        payload = {
            "scientific": scientific or "",
            "common": scientific or "Unknown species",
            "crown_diameter_m": crown,
            "height_m": _DEFAULT_HEIGHT_M,
            "leaf_cycle": "deciduous",
            "shade_density": "medium",
            "crown_area_m2": round(math.pi * (crown / 2.0) ** 2, 1),
            "cooling_score": _DEFAULT_COOLING_WEIGHT,
            "known": False,
        }
    else:
        payload = {
            "scientific": sp.scientific,
            "common": sp.common,
            "crown_diameter_m": sp.crown_diameter_m,
            "height_m": sp.height_m,
            "leaf_cycle": sp.leaf_cycle,
            "shade_density": sp.shade_density,
            "crown_area_m2": round(crown_projected_area_m2(sp), 1),
            "cooling_score": cooling_score(sp),
            "known": True,
        }
    # Ecology layer (optional; absent until the ecology module is wired).
    try:
        from coolspend.ecology import ecology_public  # noqa: PLC0415
        eco = ecology_public(payload["scientific"])
        if eco:
            payload["ecology"] = eco
    except Exception:  # noqa: BLE001 — ecology is additive, never block tree export
        pass
    return payload


def palette(top_n: int | None = None) -> tuple[Species, ...]:
    """Return the species palette (optionally the top-N by cooling_score)."""
    if top_n is None:
        return SPECIES_TABLE
    return tuple(sorted(SPECIES_TABLE, key=cooling_score, reverse=True)[:top_n])


if __name__ == "__main__":
    print(f"{'species':<26}{'crown_m':>8}{'h_m':>5}{'leaf':>11}{'shade':>8}{'cool':>7}")
    for s in sorted(SPECIES_TABLE, key=cooling_score, reverse=True):
        print(f"{s.scientific:<26}{s.crown_diameter_m:>8.1f}{s.height_m:>5.0f}"
              f"{s.leaf_cycle:>11}{s.shade_density:>8}{cooling_score(s):>7.3f}")
