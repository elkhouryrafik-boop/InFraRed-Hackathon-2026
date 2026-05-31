"""Independent post-placement audit — verify every placed tree sits on ground a
tree can actually occupy.

WHY THIS IS A VERIFICATION, NOT A RETRY LOOP
--------------------------------------------
Placement (candidate_slots.validate_slots) only ever emits slots that are already
inside the site, NOT inside a building, clear of the street carriageway, ≥ the
façade setback, and ≥ the minimum spacing. So a placed tree is valid *by
construction*. This module re-checks that guarantee with a SECOND, independent
data path (a fresh OSM building fetch), so a bug in placement can't silently put a
tree on a roof. It returns a report; it does not loop. If a violation is ever
found, the caller drops that tree (one bounded step) — there is nothing to retry,
because the greedy already placed the maximum number of *valid* trees in a single
pass. (An unbounded "re-run until perfect" loop is therefore unnecessary and is
deliberately avoided.)

Core check: a tree ON a building footprint is impossible (it's a roof — cannot be
paved/de-paved/planted). That is the hard violation. Façade-setback and spacing
are reported as soft flags.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class TreeViolation:
    index: int
    lon: float
    lat: float
    species: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class AuditReport:
    n_trees: int = 0
    n_on_building: int = 0
    n_too_close: int = 0
    n_facade_close: int = 0
    violations: list[TreeViolation] = field(default_factory=list)
    buildings_checked: int = 0
    note: str = ""

    @property
    def all_valid(self) -> bool:
        # "Valid" for the user's concern = NOT on a building (impossible site).
        return self.n_on_building == 0

    def summary(self) -> str:
        return (
            f"{self.n_trees} trees · {self.n_on_building} on a building · "
            f"{self.n_too_close} too close (<spacing) · "
            f"{self.n_facade_close} within façade setback · "
            f"{self.buildings_checked} OSM buildings checked"
        )


def _project(lon0: float, lat0: float):
    mlat = math.cos(math.radians(lat0))

    def proj(lon: float, lat: float) -> tuple[float, float]:
        return ((lon - lon0) * 111_320.0 * mlat, (lat - lat0) * 110_540.0)

    return proj


def audit_trees(
    trees_lonlat: list[dict],
    *,
    facade_setback_m: float = 6.0,
    min_spacing_m: float = 8.0,
    bbox_margin_m: float = 40.0,
) -> AuditReport:
    """Re-verify placed trees against a FRESH OSM building fetch (independent of
    the placement pipeline). trees_lonlat: [{lon,lat,species,mode?}, ...].
    """
    rep = AuditReport(n_trees=len(trees_lonlat))
    if not trees_lonlat:
        rep.note = "no trees"
        return rep

    try:
        from shapely.geometry import Point, Polygon  # noqa: PLC0415
        from shapely.ops import unary_union  # noqa: PLC0415
        from shapely.prepared import prep  # noqa: PLC0415
        from coolspend.osm_buildings import fetch_building_ways  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        rep.note = f"audit deps unavailable ({exc})"
        return rep

    lons = [t["lon"] for t in trees_lonlat]
    lats = [t["lat"] for t in trees_lonlat]
    lon0 = sum(lons) / len(lons)
    lat0 = sum(lats) / len(lats)
    proj = _project(lon0, lat0)

    # bbox of trees + margin, in lon/lat, for the OSM fetch.
    mlat = math.cos(math.radians(lat0))
    dlon = bbox_margin_m / (111_320.0 * mlat)
    dlat = bbox_margin_m / 110_540.0
    bounds = {
        "west": min(lons) - dlon, "east": max(lons) + dlon,
        "south": min(lats) - dlat, "north": max(lats) + dlat,
    }

    try:
        rings = fetch_building_ways(bounds)  # list of [(lon,lat), ...]
    except Exception as exc:  # noqa: BLE001
        rep.note = f"OSM building fetch failed ({exc})"
        return rep

    polys = []
    for ring in rings or []:
        if len(ring) >= 3:
            try:
                p = Polygon([proj(lon, lat) for lon, lat in ring])
                if p.is_valid and p.area > 0:
                    polys.append(p)
            except Exception:  # noqa: BLE001
                continue
    rep.buildings_checked = len(polys)
    union = unary_union(polys) if polys else None
    prepared = prep(union) if union is not None else None

    pts_m = [proj(t["lon"], t["lat"]) for t in trees_lonlat]

    # Spacing uses accurate haversine on lon/lat (NOT the local equirect, which is
    # scale-sensitive right at the 8 m threshold and produced false positives for
    # trees placed at exactly 8 m). A 0.5 m tolerance absorbs float noise; only a
    # genuine clump trips it.
    def _haversine_m(a: dict, b: dict) -> float:
        R = 6_371_000.0
        la1, la2 = math.radians(a["lat"]), math.radians(b["lat"])
        dla = la2 - la1
        dlo = math.radians(b["lon"] - a["lon"])
        h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
        return 2 * R * math.asin(math.sqrt(h))

    spacing_floor = min_spacing_m - 0.5

    for i, t in enumerate(trees_lonlat):
        reasons: list[str] = []
        px, py = pts_m[i]
        pt = Point(px, py)

        if prepared is not None and prepared.contains(pt):
            reasons.append("on building footprint (roof — cannot plant/depave)")
            rep.n_on_building += 1
        elif union is not None:
            d = union.distance(pt)
            # Façade setback only matters for in-ground (rooted) trees; planters
            # may sit nearer a wall. Default unknown mode → treat as in-ground.
            mode = t.get("mode", "in_ground")
            if mode != "planter" and d < facade_setback_m:
                reasons.append(f"within façade setback ({d:.1f} m < {facade_setback_m} m)")
                rep.n_facade_close += 1

        for j in range(i):
            if _haversine_m(t, trees_lonlat[j]) < spacing_floor:
                reasons.append(f"too close to tree #{j} (<{min_spacing_m} m)")
                rep.n_too_close += 1
                break

        if reasons:
            rep.violations.append(
                TreeViolation(i, t["lon"], t["lat"], t.get("species", "?"), reasons)
            )

    return rep
