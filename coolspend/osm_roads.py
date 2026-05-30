"""
coolspend/osm_roads.py — real road carriageways from OpenStreetMap (Overpass),
so the tree-placement engine never plants in the middle of a road.

WHY: roads are asphalt → impervious → hot → they generate cooling "demand", so a
naive placement would happily put trees on the carriageway. Buildings and existing
trees are already excluded (ground-material footprints + the BCN inventory), but the
drivable road surface was not. This module fetches the vehicle road network for a
polygon, buffers each centerline to an approximate carriageway footprint, and hands
the result to candidate_slots as a `streets` exclusion.

We deliberately fetch ONLY vehicle carriageways (motorway…service). Pedestrian
ways, plazas, footways and paths are NOT excluded — those are exactly where we want
to be able to plant. So a superblock plaza stays plantable while the surrounding
traffic lanes are kept clear.

Data: © OpenStreetMap contributors (ODbL). Fetched via the public Overpass API,
cached to disk so a site is only queried once. Network failure degrades gracefully
to "no road exclusion" with a logged warning (honest: better to flag than to fake
a road network).
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger("coolspend.osm_roads")

_CACHE_DIR = Path(__file__).resolve().parent / "cache" / "osm_roads"
# Overpass mirrors tried in order (public endpoints rate-limit / time out; a mirror
# list + a descriptive User-Agent are required — the default requests UA gets 406).
_OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
_HEADERS = {"User-Agent": "CoolSpend/1.0 (urban tree-cooling research; OSM Overpass client)"}

# Vehicle carriageway classes (exclude footway/pedestrian/path/steps/cycleway —
# those are plantable plaza/sidewalk space, not "the middle of the road").
_VEHICLE_HIGHWAYS = (
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "unclassified", "residential", "living_street", "service",
)

# Approximate carriageway HALF-width (m) per class — centerline is buffered by this
# so the exclusion covers the real driving surface, not just the line. DECLARED
# (typical urban lane widths); a tree must clear this plus candidate_slots' own
# STREET_BUFFER_M. REQUIRES_VERIFICATION against municipal road-width data.
_HALF_WIDTH_M = {
    "motorway": 12.0, "trunk": 10.0, "primary": 8.0, "secondary": 7.0,
    "tertiary": 6.0, "unclassified": 5.0, "residential": 5.0,
    "living_street": 4.0, "service": 3.0,
}
_DEFAULT_HALF_WIDTH_M = 5.0


def _overpass_fetch(query: str, timeout: int) -> list | None:
    """POST an Overpass query, trying each mirror with a proper UA. None on total failure."""
    try:
        import requests  # noqa: PLC0415
    except ImportError:
        return None
    for url in _OVERPASS_URLS:
        try:
            resp = requests.post(url, data={"data": query}, headers=_HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp.json().get("elements", [])
        except Exception as exc:  # noqa: BLE001 — try next mirror
            logger.info("Overpass mirror %s failed (%s)", url, type(exc).__name__)
    return None


def _bbox_key(bounds: dict[str, float]) -> str:
    raw = f"{bounds['west']:.5f},{bounds['south']:.5f},{bounds['east']:.5f},{bounds['north']:.5f}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _overpass_query(bounds: dict[str, float]) -> str:
    s, w, n, e = bounds["south"], bounds["west"], bounds["north"], bounds["east"]
    classes = "|".join(_VEHICLE_HIGHWAYS)
    return (
        f"[out:json][timeout:25];"
        f'way["highway"~"^({classes})$"]({s},{w},{n},{e});'
        f"out geom;"
    )


def fetch_road_ways(bounds: dict[str, float], *, timeout: int = 30) -> list[dict]:
    """Fetch vehicle road ways (cached). Each way = {highway, geometry:[(lon,lat)...]}.

    Returns [] on any failure (network, parse) — caller treats that as "no roads",
    which is logged so the missing exclusion is never silent.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = _CACHE_DIR / f"roads_{_bbox_key(bounds)}.json"
    if cache.is_file():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — corrupt cache, refetch
            pass

    elements = _overpass_fetch(_overpass_query(bounds), timeout)
    if elements is None:
        logger.warning("OSM Overpass road fetch failed (all mirrors); no road exclusion applied")
        return []

    ways: list[dict] = []
    for el in elements:
        if el.get("type") != "way" or "geometry" not in el:
            continue
        coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
        if len(coords) >= 2:
            ways.append({"highway": el.get("tags", {}).get("highway", ""), "geometry": coords})

    cache.write_text(json.dumps(ways), encoding="utf-8")
    logger.info("OSM roads: %d vehicle ways in bbox", len(ways))
    return ways


def road_junction_exclusions_local_m(
    bounds: dict[str, float],
    to_local_m: Callable[[float, float], tuple[float, float]],
    *,
    radius_m: float = 3.0,
    timeout: int = 30,
) -> list:
    """Sight-triangle keep-outs: a buffer around every road intersection.

    Junctions are derived from the already-fetched road ways — a coordinate shared
    by two or more ways (or appearing twice) is an intersection. Each gets a small
    keep-out so a (low-canopy, young) tree never blocks the corner sightline. This
    is the spatial proxy for the visibility-triangle rule (NACTO; ~3 m from corner).
    """
    from shapely.geometry import Point  # noqa: PLC0415

    ways = fetch_road_ways(bounds, timeout=timeout)
    seen: dict[tuple[float, float], int] = {}
    for way in ways:
        # Count endpoint + shared vertices; round to ~1 m to coalesce near-identical coords.
        for lon, lat in way["geometry"]:
            k = (round(lon, 5), round(lat, 5))
            seen[k] = seen.get(k, 0) + 1
    polys = []
    for (lon, lat), count in seen.items():
        if count >= 2:  # shared by ≥2 ways/segments → junction
            x, y = to_local_m(lon, lat)
            polys.append(Point(x, y).buffer(radius_m))
    return polys


def road_exclusion_polygons_local_m(
    bounds: dict[str, float],
    to_local_m: Callable[[float, float], tuple[float, float]],
    *,
    timeout: int = 30,
) -> list:
    """Buffered carriageway polygons (shapely, site-local metres) for candidate_slots.

    Each road centerline is projected to local metres and buffered by its class
    half-width, yielding an approximate driving-surface footprint that candidate_slots
    excludes (plus its own STREET_BUFFER_M clearance).
    """
    from shapely.geometry import LineString  # noqa: PLC0415

    ways = fetch_road_ways(bounds, timeout=timeout)
    polys = []
    for way in ways:
        local = [to_local_m(lon, lat) for lon, lat in way["geometry"]]
        if len(local) < 2:
            continue
        half_w = _HALF_WIDTH_M.get(way["highway"], _DEFAULT_HALF_WIDTH_M)
        try:
            polys.append(LineString(local).buffer(half_w))
        except Exception:  # noqa: BLE001 — skip a degenerate way
            continue
    return polys
