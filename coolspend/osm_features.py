"""
coolspend/osm_features.py — point/line street-furniture exclusions from OpenStreetMap,
so tree placement respects hydrants, crossings, stops, lamps, signals and overhead
lines (see docs/placement_spatial_constraints.md).

Same pattern as osm_roads: one cached Overpass query per bbox → buffered exclusion
polygons (site-local metres) for candidate_slots. Network failure degrades to "no
extra exclusions" with a logged warning (honest, never faked).

Clearances (metres) are the rule-of-thumb minimums from the research checklist; each
is a HARD keep-out radius around the feature.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger("coolspend.osm_features")

_CACHE_DIR = Path(__file__).resolve().parent / "cache" / "osm_features"

# Feature → keep-out radius (m). Point features buffered by the radius; line
# features (power) buffered too. Sources in docs/placement_spatial_constraints.md.
_POINT_CLEARANCE_M = {
    "fire_hydrant": 3.0,
    "crossing": 5.0,
    "bus_stop": 5.0,
    "platform": 5.0,
    "street_lamp": 2.5,
    "traffic_signals": 3.0,
    "manhole": 1.5,
    "ventilation_shaft": 2.0,
    "entrance": 2.0,
}
_POWER_LINE_CLEARANCE_M = 2.0  # trunk keep-out under/near overhead conductors


def _bbox_key(bounds: dict[str, float]) -> str:
    raw = f"{bounds['west']:.5f},{bounds['south']:.5f},{bounds['east']:.5f},{bounds['north']:.5f}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _overpass_query(bounds: dict[str, float]) -> str:
    s, w, n, e = bounds["south"], bounds["west"], bounds["north"], bounds["east"]
    b = f"({s},{w},{n},{e})"
    # Point/area street furniture + overhead power lines. Nodes for furniture, ways
    # for power lines and platforms.
    return (
        "[out:json][timeout:25];("
        f'node["emergency"="fire_hydrant"]{b};'
        f'node["highway"="crossing"]{b};'
        f'node["highway"="street_lamp"]{b};'
        f'node["highway"="traffic_signals"]{b};'
        f'node["highway"="bus_stop"]{b};'
        f'node["public_transport"="platform"]{b};'
        f'node["man_made"="manhole"]{b};'
        f'node["railway"="ventilation_shaft"]{b};'
        f'node["entrance"]{b};'
        f'way["power"~"^(line|minor_line)$"]{b};'
        ");out geom;"
    )


def _classify(tags: dict) -> str | None:
    """Map an OSM element's tags to a clearance key (or None to ignore)."""
    if tags.get("emergency") == "fire_hydrant":
        return "fire_hydrant"
    if tags.get("highway") in ("crossing", "street_lamp", "traffic_signals", "bus_stop"):
        return tags["highway"]
    if tags.get("public_transport") == "platform":
        return "platform"
    if tags.get("man_made") == "manhole":
        return "manhole"
    if tags.get("railway") == "ventilation_shaft":
        return "ventilation_shaft"
    if "entrance" in tags:
        return "entrance"
    if tags.get("power") in ("line", "minor_line"):
        return "power_line"
    return None


def fetch_features(bounds: dict[str, float], *, timeout: int = 30) -> list[dict]:
    """Fetch street-furniture/power elements (cached). Returns [] on failure."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = _CACHE_DIR / f"feat_{_bbox_key(bounds)}.json"
    if cache.is_file():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass

    from coolspend.osm_roads import _overpass_fetch  # noqa: PLC0415 — shared UA+mirror POST
    elements = _overpass_fetch(_overpass_query(bounds), timeout)
    if elements is None:
        logger.warning("OSM feature fetch failed (all mirrors); no furniture exclusions applied")
        return []

    feats: list[dict] = []
    for el in elements:
        key = _classify(el.get("tags", {}))
        if key is None:
            continue
        if el.get("type") == "node" and "lat" in el and "lon" in el:
            feats.append({"key": key, "kind": "point", "coords": [(el["lon"], el["lat"])]})
        elif el.get("type") == "way" and "geometry" in el:
            coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(coords) >= 2:
                feats.append({"key": key, "kind": "line", "coords": coords})

    cache.write_text(json.dumps(feats), encoding="utf-8")
    logger.info("OSM features: %d street-furniture/power exclusions in bbox", len(feats))
    return feats


def feature_exclusion_polygons_local_m(
    bounds: dict[str, float],
    to_local_m: Callable[[float, float], tuple[float, float]],
    *,
    timeout: int = 30,
) -> list:
    """Buffered exclusion polygons (shapely, local m) for candidate_slots."""
    from shapely.geometry import Point, LineString  # noqa: PLC0415

    feats = fetch_features(bounds, timeout=timeout)
    polys = []
    for f in feats:
        key = f["key"]
        local = [to_local_m(lon, lat) for lon, lat in f["coords"]]
        try:
            if f["kind"] == "point":
                r = _POINT_CLEARANCE_M.get(key, 2.0)
                polys.append(Point(local[0]).buffer(r))
            else:  # power line
                polys.append(LineString(local).buffer(_POWER_LINE_CLEARANCE_M))
        except Exception:  # noqa: BLE001 — skip a degenerate element
            continue
    return polys
