"""Sim-free physical shade proxy — first-order radiative cooling estimate.

PAPER limitation #2/#3: on non-live backends the system had no measured cooling,
so placement weighting fell back to a flat baseline-heat coverage proxy and the
€1M portfolio ranked by heat-vulnerability alone. This module computes, with
pure geometry (no Infrared, no network), how much *new direct-sun blockage* a
set of tree crowns buys over hot ground — the first-order driver of pedestrian
Tmrt in a hot, dry, radiation-dominated climate, which is exactly the quantity
shade interventions move.

Method (RayShader/SVF reduced to what placement needs):
  * Sample a handful of solar positions across Barcelona's July 09:00–17:00
    peak-heat window (vendored declination/hour-angle solar geometry — no dep).
  * Each tree casts a shadow: its crown disk, offset along the ground by
    height / tan(altitude) in the anti-sun direction.
  * A hot demand cell is "newly shaded" at a sun position if it falls under a
    proposed crown's shadow and was not already shaded by an existing canopy or
    building. A cell's shade-gain = fraction of sampled suns it becomes shaded.

Outputs feed CoolingEstimator.ShadeProxyEstimator. Everything here is a labelled
ESTIMATE, never "measured" — the live UTCI sim remains ground truth.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Barcelona. Used only if a site centroid is not supplied.
BARCELONA_LAT = 41.39

# July peak-heat sampling window (matches the Infrared UTCI window). Solar hours.
_JULY_DAY_OF_YEAR = 196  # ~mid-July
_SAMPLE_HOURS = (9.0, 11.0, 13.0, 15.0, 17.0)

# Documented shade→UTCI anchor for the coarse mean-Δ estimate. Full direct-sun
# removal in a Mediterranean plaza lowers pedestrian UTCI by roughly this much
# (Tmrt-dominated; Bowler 2010 review ~1 °C air but several °C felt under shade;
# conservative midpoint). ESTIMATE only — the live sim measures the real value.
_SHADE_UTCI_DROP_C = 3.0


@dataclass(frozen=True)
class SunDir:
    """A sampled sun position: altitude plus the horizontal direction to the sun."""
    altitude_rad: float
    # Unit horizontal vector pointing TOWARD the sun in local metres (x=E, y=N).
    east: float
    north: float


def solar_positions_july(lat_deg: float = BARCELONA_LAT) -> list[SunDir]:
    """Sun altitude + horizontal direction for the July sampling hours.

    Vendored solar geometry (declination + hour angle); accurate to ~0.5°, ample
    for shadow placement. Night/low-sun samples (altitude ≤ 5°) are dropped.
    """
    phi = math.radians(lat_deg)
    decl = math.radians(23.45 * math.sin(math.radians(360.0 * (284 + _JULY_DAY_OF_YEAR) / 365.0)))
    out: list[SunDir] = []
    for hour in _SAMPLE_HOURS:
        H = math.radians(15.0 * (hour - 12.0))  # hour angle
        sin_alt = math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.cos(H)
        alt = math.asin(max(-1.0, min(1.0, sin_alt)))
        if alt <= math.radians(5.0):
            continue
        # Azimuth measured from north, positive clockwise (toward east in the
        # morning H<0). Standard formula.
        cos_az = (math.sin(decl) - math.sin(alt) * math.sin(phi)) / (math.cos(alt) * math.cos(phi) + 1e-9)
        cos_az = max(-1.0, min(1.0, cos_az))
        az = math.acos(cos_az)
        if H > 0:  # afternoon → sun in the west
            az = 2 * math.pi - az
        # Horizontal unit vector toward the sun (x=east, y=north).
        east = math.sin(az)
        north = math.cos(az)
        out.append(SunDir(alt, east, north))
    return out


def _shadow_center(tx: float, ty: float, height_m: float, sun: SunDir) -> tuple[float, float]:
    """Ground point where a crown centred at (tx,ty) casts its shadow centre."""
    reach = height_m / max(math.tan(sun.altitude_rad), 0.05)  # cap very low sun
    # Shadow falls OPPOSITE the sun direction.
    return tx - reach * sun.east, ty - reach * sun.north


@dataclass(frozen=True)
class ProxyTree:
    """A shade-casting tree for the proxy: crown radius + height drive shadow length."""
    x_m: float
    y_m: float
    crown_r_m: float
    height_m: float


@dataclass(frozen=True)
class ProxyCell:
    """A ground cell whose sun-blockage we score (site-local metres)."""
    x_m: float
    y_m: float
    weight: float       # baseline heat priority (UTCI − comfort), ≥0
    area_m2: float      # ground area this cell represents


def shade_gain_per_cell(
    cells: list[ProxyCell],
    trees: list[ProxyTree],
    suns: list[SunDir],
    already_shaded: "list[ProxyTree] | None" = None,
) -> dict[int, float]:
    """For each demand cell index, the fraction of sampled suns it is NEWLY shaded
    by the proposed trees (0..1). Existing canopy/buildings (``already_shaded``,
    as crown-like discs) remove suns from the "new" count.
    """
    if not suns:
        return {}
    already = already_shaded or []
    out: dict[int, float] = {}
    for ci, c in enumerate(cells):
        blocked = 0
        for sun in suns:
            # Skip if an existing obstacle already shades this cell for this sun.
            pre = False
            for ob in already:
                sx, sy = _shadow_center(ob.x_m, ob.y_m, ob.height_m, sun)
                if (c.x_m - sx) ** 2 + (c.y_m - sy) ** 2 <= ob.crown_r_m ** 2:
                    pre = True
                    break
            if pre:
                continue
            for t in trees:
                sx, sy = _shadow_center(t.x_m, t.y_m, t.height_m, sun)
                if (c.x_m - sx) ** 2 + (c.y_m - sy) ** 2 <= t.crown_r_m ** 2:
                    blocked += 1
                    break
        out[ci] = blocked / len(suns)
    return out


@dataclass(frozen=True)
class ShadeProxyResult:
    """Site-level sim-free shade estimate (all values are ESTIMATES, not measured)."""
    cooled_m2: float          # hot ground newly shaded (sun-weighted), m²
    mean_delta_c: float | None
    weighted_gain: float      # Σ cell.weight × shade_gain (the placement objective)
    n_suns: int


def estimate_shade_cooling(
    cells: list[ProxyCell],
    trees: list[ProxyTree],
    lat_deg: float = BARCELONA_LAT,
    already_shaded: "list[ProxyTree] | None" = None,
) -> ShadeProxyResult:
    """Site-level sim-free cooling estimate from crown sun-blockage over hot cells."""
    suns = solar_positions_july(lat_deg)
    gains = shade_gain_per_cell(cells, trees, suns, already_shaded)
    cooled_m2 = sum(cells[ci].area_m2 * g for ci, g in gains.items())
    weighted_gain = sum(cells[ci].weight * g for ci, g in gains.items())
    mean_delta = _SHADE_UTCI_DROP_C if cooled_m2 > 0 else None
    return ShadeProxyResult(
        cooled_m2=round(cooled_m2, 1),
        mean_delta_c=mean_delta,
        weighted_gain=round(weighted_gain, 2),
        n_suns=len(suns),
    )
