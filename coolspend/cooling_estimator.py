"""CoolingEstimator — one fidelity ladder for "how much does this layout cool?".

PAPER limitations #2/#3/#4 each answered that question differently and labelled
the answer inconsistently. This module unifies them behind one interface so each
consumer (placement, optimizer, portfolio) picks a backend by fidelity + sim
budget, and so the measured-vs-estimate honesty label is enforced in ONE place
(the ``is_measured`` / ``fidelity`` / ``label`` fields) instead of scattered
disclaimer strings — the paper's honesty architecture made structural.

Fidelity ladder (low → high):
    MockScalarEstimator   scalar       synthetic, NOT measured
    ShadeProxyEstimator   shade_proxy  sim-free ray-cast sun-blockage (real geometry)
    CachedUTCIEstimator   cached_utci  replayed measured grid (zero new live sims)
    LiveUTCIEstimator     live_utci    live Infrared UTCI (SimBudget-guarded)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from coolspend import shade_proxy as sp


@dataclass(frozen=True)
class CoolingEstimate:
    cooled_m2: float | None       # cooled footprint (≥0.5 °C for measured; shaded hot m² for proxy)
    mean_delta_c: float | None    # mean ΔUTCI over the cooled zone
    fidelity: str                 # "scalar" | "shade_proxy" | "cached_utci" | "live_utci"
    is_measured: bool             # True only for cached_utci / live_utci
    band_c: float | None          # uncertainty (±°C); None if not characterised
    label: str                    # honesty string for the UI/payload
    per_cell: dict | None = None  # optional cell→shade-gain map (placement weighting)


# ── Local projection helper (self-contained; no global site frame needed) ────
def _to_local_m(polygon_lonlat: list, trees_lonlat: list):
    """Project a polygon ring + trees to local metres around the polygon centroid."""
    ring = polygon_lonlat[:-1] if (polygon_lonlat and polygon_lonlat[0] == polygon_lonlat[-1]) else polygon_lonlat
    if not ring:
        return None, [], (0.0, 0.0)
    lon0 = sum(p[0] for p in ring) / len(ring)
    lat0 = sum(p[1] for p in ring) / len(ring)
    mlat = math.cos(math.radians(lat0))

    def proj(lon, lat):
        return ((lon - lon0) * 111_320.0 * mlat, (lat - lat0) * 110_540.0)

    ring_m = [proj(lon, lat) for lon, lat in ring]
    trees_m = []
    for t in trees_lonlat or []:
        x, y = proj(t["lon"], t["lat"])
        trees_m.append((x, y, t.get("species", "")))
    return ring_m, trees_m, (lat0, lon0)


def _hot_cells_over_polygon(ring_m, step_m: float = 4.0) -> list[sp.ProxyCell]:
    """Uniform candidate hot-ground cells across the polygon bbox (proxy demand)."""
    xs = [p[0] for p in ring_m]
    ys = [p[1] for p in ring_m]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    # Point-in-polygon (ray cast) so we only count ground inside the site.
    def inside(px, py):
        n = len(ring_m)
        c = False
        j = n - 1
        for i in range(n):
            xi, yi = ring_m[i]
            xj, yj = ring_m[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi):
                c = not c
            j = i
        return c

    cells = []
    x = minx
    while x <= maxx:
        y = miny
        while y <= maxy:
            if inside(x, y):
                cells.append(sp.ProxyCell(x, y, weight=1.0, area_m2=step_m * step_m))
            y += step_m
        x += step_m
    return cells


def _proxy_trees(trees_m: list) -> list[sp.ProxyTree]:
    from coolspend.bcn_species import get_species  # noqa: PLC0415

    out = []
    for x, y, species in trees_m:
        s = get_species(species)
        crown = s.crown_diameter_m if s else 6.0
        height = s.height_m if s else 10.0
        out.append(sp.ProxyTree(x, y, crown / 2.0, height))
    return out


class ShadeProxyEstimator:
    """Sim-free first-order radiative cooling estimate (Limitation #2/#3 Tier 0)."""

    fidelity = "shade_proxy"

    def estimate(self, trees_lonlat: list, polygon_lonlat: list) -> CoolingEstimate:
        ring_m, trees_m, (lat0, _lon0) = _to_local_m(polygon_lonlat, trees_lonlat)
        if not ring_m or not trees_m:
            return CoolingEstimate(None, None, self.fidelity, False, None,
                                   "estimate (shade-proxy): no trees/site")
        cells = _hot_cells_over_polygon(ring_m)
        trees = _proxy_trees(trees_m)
        res = sp.estimate_shade_cooling(cells, trees, lat_deg=lat0)
        return CoolingEstimate(
            cooled_m2=res.cooled_m2,
            mean_delta_c=res.mean_delta_c,
            fidelity=self.fidelity,
            is_measured=False,
            band_c=None,
            label="estimate (shade-proxy, sim-free sun-blockage; NOT measured)",
        )


class MockScalarEstimator:
    """The legacy synthetic scalar — explicitly not measured."""

    fidelity = "scalar"

    def estimate(self, trees_lonlat: list, polygon_lonlat: list) -> CoolingEstimate:
        return CoolingEstimate(None, None, self.fidelity, False, None,
                               "synthetic scalar (NOT measured)")


def estimate_site_cooling(
    trees_lonlat: list,
    polygon_lonlat: list,
    source: str = "proxy",
) -> CoolingEstimate:
    """Convenience: pick an estimator by ``source`` and run it.

    ``proxy`` → ShadeProxyEstimator (sim-free, default). ``scalar`` → mock.
    Cached/live measured estimates are produced by the sdk_client path in
    smart_evaluate (which already returns a measured cooled_footprint_m2); this
    helper is the sim-free branch used when no measured grid is available.
    """
    est = ShadeProxyEstimator() if source == "proxy" else MockScalarEstimator()
    return est.estimate(trees_lonlat, polygon_lonlat)
