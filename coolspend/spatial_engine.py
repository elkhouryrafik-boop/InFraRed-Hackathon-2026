"""
coolspend.spatial_engine — GeoJSON site loader, shapely collision engine,
and the single EPSG:4326 <-> plaza-local-metres CRS boundary.

Project: CoolSpend / Tree Budget Optimizer (infrared.city SDK Buildathon)
Site:    Placa dels Angels, Barcelona (plaza centroid lon=2.1670, lat=41.3826)

Geometry inputs are loaded from a MOCK hand-authored fixture
(coolspend/data/angels_site.geojson). Not surveyed OSM data — see MOCKS.md.

Key functions:
  - load_site(path)         : parse GeoJSON fixture -> shapely geometries in local metres
  - is_valid_location(x, y) : returns False for points in buildings / on streets / outside boundary
  - latlon_to_local_m(lon, lat) : THE ONLY CRS conversion in coolspend (EPSG:4326 -> local m)
  - local_m_to_latlon(x, y)    : THE ONLY inverse CRS conversion (local m -> EPSG:4326)

SPATIAL-03 compliance: no other module may convert CRS. All callers must import
these two functions from this module.
"""
from __future__ import annotations

import json
from math import cos, radians
from pathlib import Path
from typing import Any

# ── SHAPELY IMPORT (guarded for clear error message) ─────────────────────────

try:
    from shapely.geometry import LineString, Point, Polygon
except ImportError as _err:
    raise RuntimeError(
        "coolspend.spatial_engine requires shapely. "
        "Install it with: pip install shapely"
    ) from _err

# ── SITE CONSTANTS ────────────────────────────────────────────────────────────
# Source: ARCHITECTURE.md "Coordinate Systems" + nature_nsga2_coolstock.py lines 74-86

SITE_WIDTH_M: float = 60.0       # E-W extent of the plaza rectangle, metres
SITE_DEPTH_M: float = 42.0       # N-S usable extent of the plaza rectangle, metres
SITE_ORIGIN_LON: float = 2.1670  # EPSG:4326 longitude of plaza centroid (anchor point)
SITE_ORIGIN_LAT: float = 41.3826 # EPSG:4326 latitude of plaza centroid (anchor point)
HERITAGE_BUFFER_M: float = 5.0   # MACBA north-edge no-tree buffer, metres

STREET_BUFFER_M: float = 1.5     # Rejection radius around street centerlines, metres

# ── FILE PATHS ────────────────────────────────────────────────────────────────

DATA_DIR: Path = Path(__file__).resolve().parent / "data"
DEFAULT_SITE: Path = DATA_DIR / "angels_site.geojson"

# ── CRS PROJECTION CONSTANTS ──────────────────────────────────────────────────

_M_PER_DEG_LAT: float = 111_320.0  # metres per degree of latitude (equirectangular)

# ── SINGLE CRS BOUNDARY (SPATIAL-03) ─────────────────────────────────────────


def latlon_to_local_m(lon: float, lat: float) -> tuple[float, float]:
    """Convert EPSG:4326 (lon, lat) to plaza-local metres (x_m, y_m).

    THIS IS THE ONLY PLACE CRS CONVERSION HAPPENS IN coolspend (SPATIAL-03).
    No other module may convert EPSG:4326 to local metres. Import this function
    from here — do not reproduce the formula elsewhere.

    Projection: equirectangular with cos-latitude correction, accurate within
    ±200 m of the plaza centroid. Not suitable for city-scale use.

    Local-metre frame: SW corner of the plaza rectangle = (0, 0).
    x_m = East-West position in [0, SITE_WIDTH_M].
    y_m = North-South position in [0, SITE_DEPTH_M].
    The EPSG:4326 centroid anchor maps to the geometric centre:
    (SITE_WIDTH_M/2, SITE_DEPTH_M/2).

    Args:
        lon: WGS84 longitude in decimal degrees.
        lat: WGS84 latitude in decimal degrees.

    Returns:
        (x_m, y_m) — position in plaza-local metres.
    """
    x_m = (lon - SITE_ORIGIN_LON) * _M_PER_DEG_LAT * cos(radians(SITE_ORIGIN_LAT)) + SITE_WIDTH_M / 2
    y_m = (lat - SITE_ORIGIN_LAT) * _M_PER_DEG_LAT + SITE_DEPTH_M / 2
    return x_m, y_m


def local_m_to_latlon(x_m: float, y_m: float) -> tuple[float, float]:
    """Convert plaza-local metres (x_m, y_m) to EPSG:4326 (lon, lat).

    THIS IS THE ONLY PLACE INVERSE CRS CONVERSION HAPPENS IN coolspend (SPATIAL-03).
    No other module may convert local metres to EPSG:4326. Import this function
    from here — do not reproduce the formula elsewhere.

    Exact algebraic inverse of latlon_to_local_m. See that function for frame
    conventions and projection accuracy notes.

    Args:
        x_m: East-West position in plaza-local metres.
        y_m: North-South position in plaza-local metres.

    Returns:
        (lon, lat) — WGS84 longitude and latitude in decimal degrees.
    """
    lon = (x_m - SITE_WIDTH_M / 2) / (_M_PER_DEG_LAT * cos(radians(SITE_ORIGIN_LAT))) + SITE_ORIGIN_LON
    lat = (y_m - SITE_DEPTH_M / 2) / _M_PER_DEG_LAT + SITE_ORIGIN_LAT
    return lon, lat


# ── SITE CACHE ────────────────────────────────────────────────────────────────

_SITE_CACHE: dict[str, Any] = {}  # keyed by resolved path string


# ── SITE LOADER ───────────────────────────────────────────────────────────────


def load_site(path: str | None = None) -> dict[str, Any]:
    """Load a site GeoJSON fixture and return shapely geometries in local metres.

    Reads the file at `path` (default: bundled coolspend/data/angels_site.geojson)
    using json.load only — never exec/eval — per CONVENTIONS Rule 4.

    The GeoJSON must be a FeatureCollection with features keyed by
    `properties.kind`: "site_boundary", "building", "street".
    All coordinates are converted from EPSG:4326 (lon, lat) to plaza-local metres
    via the single CRS boundary (latlon_to_local_m).

    Results for the default site are cached in _SITE_CACHE to avoid repeated
    disk reads within a session.

    Args:
        path: Optional path to a GeoJSON file. If None, uses DEFAULT_SITE.

    Returns:
        {
          "boundary": Polygon,        # site boundary in local metres
          "buildings": list[Polygon], # building footprints in local metres
          "streets":   list[LineString], # street centerlines in local metres
        }

    Raises:
        RuntimeError: if the file cannot be parsed or shapely is not installed.
        FileNotFoundError: if the specified path does not exist.
    """
    resolved_path = str(Path(path).resolve() if path else DEFAULT_SITE)

    if resolved_path in _SITE_CACHE:
        return _SITE_CACHE[resolved_path]

    site_path = Path(resolved_path)
    if not site_path.exists():
        raise FileNotFoundError(
            f"Site GeoJSON not found: {site_path}. "
            f"Run from the repo root or provide an explicit path."
        )

    with site_path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)  # NEVER eval — CONVENTIONS Rule 4

    if data.get("type") != "FeatureCollection":
        raise RuntimeError(
            f"Expected GeoJSON FeatureCollection, got type={data.get('type')!r}"
        )

    boundary: Polygon | None = None
    buildings: list[Polygon] = []
    streets: list[LineString] = []

    for feature in data.get("features", []):
        kind = feature.get("properties", {}).get("kind", "")
        geom = feature.get("geometry", {})
        geom_type = geom.get("type", "")

        if kind == "site_boundary" and geom_type == "Polygon":
            local_coords = [latlon_to_local_m(lon, lat) for lon, lat in geom["coordinates"][0]]
            boundary = Polygon(local_coords)

        elif kind == "building" and geom_type == "Polygon":
            local_coords = [latlon_to_local_m(lon, lat) for lon, lat in geom["coordinates"][0]]
            buildings.append(Polygon(local_coords))

        elif kind == "street" and geom_type == "LineString":
            local_coords = [latlon_to_local_m(lon, lat) for lon, lat in geom["coordinates"]]
            streets.append(LineString(local_coords))

    if boundary is None:
        raise RuntimeError(
            "Site GeoJSON must contain a feature with properties.kind='site_boundary' "
            f"and geometry.type='Polygon'. Got kinds: "
            f"{[f.get('properties', {}).get('kind') for f in data.get('features', [])]}"
        )

    result: dict[str, Any] = {
        "boundary": boundary,
        "buildings": buildings,
        "streets": streets,
    }
    _SITE_CACHE[resolved_path] = result
    return result


# ── COLLISION GATE ────────────────────────────────────────────────────────────


def is_valid_location(
    x_m: float,
    y_m: float,
    site: dict[str, Any] | None = None,
) -> bool:
    """Return True only if (x_m, y_m) is a plausible tree-planting location.

    Rejects the point if any of the following is true:
    - The point lies outside the site boundary polygon.
    - The point lies inside any building footprint polygon.
    - The point is within STREET_BUFFER_M (1.5 m) of any street centerline.

    Coordinates must be in plaza-local metres (SW corner = (0, 0)).
    Use latlon_to_local_m to convert from EPSG:4326 before calling.

    Args:
        x_m: East-West coordinate in local metres.
        y_m: North-South coordinate in local metres.
        site: Pre-loaded site dict from load_site(). If None, loads the default
              bundled fixture (with caching).

    Returns:
        True if the location is open and plantable; False otherwise.
    """
    if site is None:
        site = load_site()

    p = Point(x_m, y_m)

    if not site["boundary"].contains(p):
        return False

    for building in site["buildings"]:
        if building.contains(p):
            return False

    for street in site["streets"]:
        if street.distance(p) <= STREET_BUFFER_M:
            return False

    return True


# ── SMOKE TEST ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _site = load_site()
    print(f"Site loaded: boundary={_site['boundary'].is_valid}, "
          f"buildings={len(_site['buildings'])}, streets={len(_site['streets'])}")

    # A point clear of buildings and street (open interior)
    _x_open, _y_open = 30.0, 10.0
    print(f"is_valid_location({_x_open}, {_y_open}) = {is_valid_location(_x_open, _y_open)}")

    # A point inside the MACBA building strip (north edge, y≈38)
    _bld = _site["buildings"][0]
    _cx, _cy = _bld.centroid.x, _bld.centroid.y
    print(f"is_valid_location({_cx:.2f}, {_cy:.2f}) = {is_valid_location(_cx, _cy)} [in building, expect False]")

    # CRS round-trip check
    _lon_rt, _lat_rt = local_m_to_latlon(*latlon_to_local_m(SITE_ORIGIN_LON, SITE_ORIGIN_LAT))
    print(f"CRS round-trip: lon_err={abs(_lon_rt - SITE_ORIGIN_LON):.2e}, lat_err={abs(_lat_rt - SITE_ORIGIN_LAT):.2e}")
