"""
coolspend/osm_buildings.py — real building footprints from OpenStreetMap (Overpass),
so tree placement NEVER lands on a roof or against a facade — on ANY backend.

WHY a separate OSM source: the Infrared ground-material 'building' layer is only
fetched on INFRARED_BACKEND=live (ground_analysis.analyze_impervious). On mock/cached
there were no building footprints, so candidate_slots could place a tree on a building.
Building footprints are the single most important placement exclusion ("is this tree
on a roof?"), so we fetch them from OpenStreetMap (free, no API key) and union them
with the Infrared buildings when live — giving backend-independent, building-aware
placement.

Same pattern as osm_roads/osm_features: one cached Overpass query per bbox →
shapely polygons in site-local metres for candidate_slots' `buildings` exclusion
(contains + facade/foundation clearance). Network failure degrades to "no building
exclusion from OSM" with a logged warning (honest, never faked).

Data: © OpenStreetMap contributors (ODbL).
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger("coolspend.osm_buildings")

_CACHE_DIR = Path(__file__).resolve().parent / "cache" / "osm_buildings"


def _bbox_key(bounds: dict[str, float]) -> str:
    raw = f"{bounds['west']:.5f},{bounds['south']:.5f},{bounds['east']:.5f},{bounds['north']:.5f}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _overpass_query(bounds: dict[str, float]) -> str:
    s, w, n, e = bounds["south"], bounds["west"], bounds["north"], bounds["east"]
    b = f"({s},{w},{n},{e})"
    # Any building way/relation. `out geom` returns way node coords inline; relations
    # (building parts / multipolygons) return their member ways' geometry.
    return (
        "[out:json][timeout:25];("
        f'way["building"]{b};'
        f'relation["building"]{b};'
        ");out geom;"
    )


def fetch_building_ways(bounds: dict[str, float], *, timeout: int = 30) -> list[list[tuple[float, float]]]:
    """Fetch OSM building outlines (cached). Returns a list of lon/lat rings (>=4 pts).

    Returns [] on any failure (network/parse) — logged, so the missing exclusion is
    never silent. Relations contribute each member way's ring (good enough for a
    keep-out footprint; we don't reconstruct multipolygon holes — a hole would only
    make the exclusion slightly conservative, which is the safe direction).
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = _CACHE_DIR / f"bldg_{_bbox_key(bounds)}.json"
    if cache.is_file():
        try:
            return [[(p[0], p[1]) for p in ring] for ring in json.loads(cache.read_text(encoding="utf-8"))]
        except Exception:  # noqa: BLE001 — corrupt cache, refetch
            pass

    from coolspend.osm_roads import _overpass_fetch  # noqa: PLC0415 — shared UA + mirrors
    elements = _overpass_fetch(_overpass_query(bounds), timeout)
    if elements is None:
        logger.warning("OSM building fetch failed (all mirrors); no OSM building exclusion applied")
        return []

    rings: list[list[tuple[float, float]]] = []
    for el in elements:
        etype = el.get("type")
        if etype == "way" and "geometry" in el:
            coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(coords) >= 4:
                rings.append(coords)
        elif etype == "relation":
            for m in el.get("members", []):
                if m.get("type") == "way" and "geometry" in m:
                    coords = [(p["lon"], p["lat"]) for p in m["geometry"]]
                    if len(coords) >= 4:
                        rings.append(coords)

    cache.write_text(json.dumps(rings), encoding="utf-8")
    logger.info("OSM buildings: %d footprint rings in bbox", len(rings))
    return rings


def buildings_local_m(
    bounds: dict[str, float],
    to_local_m: Callable[[float, float], tuple[float, float]],
    *,
    timeout: int = 30,
) -> list:
    """OSM building footprints as shapely polygons in site-local metres.

    For candidate_slots' `buildings` exclusion (contains + facade/foundation
    clearance). Degenerate/invalid rings are buffer(0)-repaired or skipped.
    """
    from shapely.geometry import Polygon  # noqa: PLC0415

    polys = []
    for ring in fetch_building_ways(bounds, timeout=timeout):
        local = [to_local_m(lon, lat) for lon, lat in ring]
        if len(local) < 4:
            continue
        try:
            g = Polygon(local)
            if not g.is_valid:
                g = g.buffer(0)
            if not g.is_empty and g.area > 0:
                polys.append(g)
        except Exception:  # noqa: BLE001 — skip a degenerate footprint
            continue
    return polys
