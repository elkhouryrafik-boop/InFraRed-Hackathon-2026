"""
coolspend.spatial_engine — GeoJSON site loader, shapely collision engine,
and the single UTM-31N (EPSG:32631) <-> site-local-metres CRS boundary.

Project: CoolSpend / Tree Budget Optimizer (infrared.city SDK Buildathon)
Default site: Placa dels Angels, Barcelona.

Geometry inputs are loaded from a MOCK hand-authored fixture
(coolspend/data/angels_site.geojson). Not surveyed OSM data — see MOCKS.md.

CRS: UTM-31N (EPSG:32631) via pyproj. Valid across all of Barcelona with
sub-metre distortion (D-06). Per-site SW-corner local frame derived from UTM offsets.

Key functions:
  - load_site(path)                  : parse GeoJSON fixture -> shapely geometries in local metres
  - is_valid_location(x, y)          : returns False for points in buildings / on streets / outside boundary
  - latlon_to_local_m(lon, lat)      : THE ONLY CRS conversion in coolspend (EPSG:4326 -> local m)
  - local_m_to_latlon(x, y)          : THE ONLY inverse CRS conversion (local m -> EPSG:4326)
  - set_site_origin_from_polygon(ring) : set per-site UTM origin from polygon bbox SW corner (D-06)
  - assert_crs_roundtrip(ring)        : fail-closed guard: <1 m round-trip or raises CRSConsistencyError (D-07)
  - shade_efficiency(tilt_deg, height_m) : sun-path alignment bonus (analytical, OPT-02)
  - delta_tmrt_surrogate(shade_fraction, ...) : fast analytical ΔTmrt proxy (OPT-02 hot path)
  - thermal_relief(config)           : site-averaged ΔTmrt for a tree config (OPT-02)

SPATIAL-03 compliance: no other module may convert CRS. All callers must import
these functions from this module.

SURROGATE HONESTY (OPT-02 / CONCERNS 1.1):
  delta_tmrt_surrogate is an ANALYTICAL PROXY, NOT a measured or simulated result.
  Uncertainty ±4°C. MAX_TMRT_REDUCTION_C=12°C is still an UNSOURCED cap — REQUIRES_VERIFICATION.
  Use for optimizer hot-path only; validate Top-3 with real Infrared SDK UTCI calls.

  Tmrt-magnitude anchor: Schrodi et al. 2023 (arXiv:2310.05691, venue PENDING) —
  tree-placement point-wise ΔTmrt; an ML method, cited for the Tmrt magnitude only
  (we do NOT use their ML approach; ML stays ruled out). Supporting: Rahman et al. 2022
  (tree-Tmrt anchor, DOI PENDING). Garcia-Nevado 2020 is a shade-structure /
  surface-temperature ANALOGUE only (measures pavement surface temp, not Tmrt at 1.1 m),
  demoted from the primary anchor. No fabricated DOIs; unverified refs tagged PENDING.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ── SHAPELY IMPORT (guarded for clear error message) ─────────────────────────

try:
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union
except ImportError as _err:
    raise RuntimeError(
        "coolspend.spatial_engine requires shapely. "
        "Install it with: pip install shapely"
    ) from _err

# ── PYPROJ UTM-31N TRANSFORMERS (D-06) ────────────────────────────────────────
# always_xy=True: call order is (lon, lat) -> (easting, northing) for _TO_UTM,
# and (easting, northing) -> (lon, lat) for _TO_WGS. Consistent everywhere.

try:
    from pyproj import Transformer as _Transformer
except ImportError as _err:
    raise RuntimeError(
        "coolspend.spatial_engine requires pyproj. "
        "Install it with: pip install 'pyproj>=3.6,<4'"
    ) from _err

_TO_UTM = _Transformer.from_crs("EPSG:4326", "EPSG:32631", always_xy=True)
_TO_WGS = _Transformer.from_crs("EPSG:32631", "EPSG:4326", always_xy=True)

# ── CRS CONSISTENCY ERROR (D-07) ─────────────────────────────────────────────


class CRSConsistencyError(RuntimeError):
    """Raised when a WGS84->UTM->WGS84 round-trip exceeds the 1 m tolerance (D-07).

    This error is fail-closed: when raised, the downstream live SDK call is aborted.
    The error message names the worst round-trip error in metres.
    """


# ── SITE CONSTANTS ────────────────────────────────────────────────────────────
# SITE_WIDTH_M and SITE_DEPTH_M are updated by set_site_origin_from_polygon()
# when a real polygon is loaded. Defaults match the bundled angels_site.geojson.
# The NSGA-II optimizer reads these module-level values for its decision-variable
# bounds — they automatically follow whatever polygon was last set. (D-06)

_DEFAULT_SITE_WIDTH_M: float = 60.0  # immutable default E-W extent (Plaça dels Àngels), metres
_DEFAULT_SITE_DEPTH_M: float = 42.0  # immutable default N-S extent (Plaça dels Àngels), metres

SITE_WIDTH_M: float = _DEFAULT_SITE_WIDTH_M  # E-W extent in metres; updated per-site by set_site_origin_from_polygon
SITE_DEPTH_M: float = _DEFAULT_SITE_DEPTH_M  # N-S usable extent in metres; updated per-site
SITE_ORIGIN_LON: float = 2.1670  # WGS84 longitude — DEFAULT fallback (Plaça dels Àngels centroid)
SITE_ORIGIN_LAT: float = 41.3826 # WGS84 latitude  — DEFAULT fallback (Plaça dels Àngels centroid)
HERITAGE_BUFFER_M: float = 5.0   # MACBA north-edge no-tree buffer, metres
STREET_BUFFER_M: float = 1.5     # Rejection radius around street centerlines, metres

# ── FILE PATHS ────────────────────────────────────────────────────────────────

DATA_DIR: Path = Path(__file__).resolve().parent / "data"
DEFAULT_SITE: Path = DATA_DIR / "angels_site.geojson"

# ── PER-SITE UTM ORIGIN STATE (D-06) ─────────────────────────────────────────
# Set by set_site_origin_from_polygon(ring_lonlat); lazily initialized from the
# default site if never explicitly set (backwards-compatible fallback).
# _SITE_ORIGIN_E: UTM-31N easting of the polygon's SW corner (min easting).
# _SITE_ORIGIN_N: UTM-31N northing of the polygon's SW corner (min northing).

_SITE_ORIGIN_E: float | None = None   # UTM-31N easting of SW corner (metres)
_SITE_ORIGIN_N: float | None = None   # UTM-31N northing of SW corner (metres)

_ORIGIN_INITIALIZED: bool = False  # True once _ensure_origin_initialized() has run

# Active-site override (D-06 "scan anywhere"). When set, is_valid_location() uses
# THIS site dict instead of lazily loading the bundled angels_site.geojson — so
# retargeting to an arbitrary Barcelona polygon is not silently clobbered by the
# default-site loader. None -> default behaviour (load bundled fixture).
_ACTIVE_SITE: dict[str, Any] | None = None


def set_site_origin_from_polygon(
    ring_lonlat: list[tuple[float, float]],
) -> tuple[float, float]:
    """Compute and store the per-site UTM origin from a polygon ring's UTM bbox.

    The site origin is set to the SW corner of the polygon's UTM bounding box —
    i.e. (min_easting, min_northing) of the ring in UTM-31N. After this call:
      - latlon_to_local_m maps the SW UTM corner to (0, 0).
      - local_m_to_latlon maps (0, 0) back to the SW UTM corner.
      - SITE_WIDTH_M = max(E) - min(E) over the ring.
      - SITE_DEPTH_M = max(N) - min(N) over the ring.
    The NSGA-II optimizer bounds ([0, SITE_WIDTH_M] x [0, SITE_DEPTH_M]) follow
    the site automatically — no NSGA-II bound rewrite needed (D-06).

    Per-site real sites call this; existing code that does NOT call it gets a
    lazy fallback from the bundled angels_site.geojson boundary (see _ensure_origin_initialized).

    Args:
        ring_lonlat: Polygon ring as a list of (lon, lat) tuples. May be closed
                     (first == last) or open; duplicates are handled correctly.

    Returns:
        (width_m, depth_m): UTM extents of the polygon in metres.
    """
    global _SITE_ORIGIN_E, _SITE_ORIGIN_N, SITE_WIDTH_M, SITE_DEPTH_M, _ORIGIN_INITIALIZED

    eastings: list[float] = []
    northings: list[float] = []
    for lon, lat in ring_lonlat:
        e, n = _TO_UTM.transform(lon, lat)
        eastings.append(e)
        northings.append(n)

    _SITE_ORIGIN_E = min(eastings)
    _SITE_ORIGIN_N = min(northings)
    SITE_WIDTH_M = max(eastings) - min(eastings)
    SITE_DEPTH_M = max(northings) - min(northings)
    _ORIGIN_INITIALIZED = True

    # Invalidate any cached site rectangles so they rebuild with new dimensions
    _SITE_RECT_CACHE.clear()
    _CORE_RECT_CACHE.clear()

    return SITE_WIDTH_M, SITE_DEPTH_M


def reset_site_origin() -> None:
    """Reset the per-site UTM origin + extents to the default (uninitialized) state.

    Restores SITE_WIDTH_M/SITE_DEPTH_M to their module defaults, clears the stored
    UTM origin, and marks the origin uninitialized so the next coordinate conversion
    lazily re-loads the default angels_site.geojson (see _ensure_origin_initialized).

    Why this exists (D-06 follow-up): the per-site origin is mutable module state.
    Without an explicit reset, processing site A then site B in one process — or one
    test after another — leaves stale extents that silently corrupt the next caller's
    frame. Call this between sites in a multi-site run, and it is invoked autouse before
    every test (coolspend/tests/conftest.py) to guarantee deterministic test isolation.
    """
    global _SITE_ORIGIN_E, _SITE_ORIGIN_N, SITE_WIDTH_M, SITE_DEPTH_M, _ORIGIN_INITIALIZED
    global _ACTIVE_SITE
    _SITE_ORIGIN_E = None
    _SITE_ORIGIN_N = None
    SITE_WIDTH_M = _DEFAULT_SITE_WIDTH_M
    SITE_DEPTH_M = _DEFAULT_SITE_DEPTH_M
    _ORIGIN_INITIALIZED = False
    _ACTIVE_SITE = None
    _SITE_RECT_CACHE.clear()
    _CORE_RECT_CACHE.clear()


def set_active_site(site: dict[str, Any] | None) -> None:
    """Set (or clear with None) the active site dict used by is_valid_location.

    Use with set_site_origin_from_polygon when scanning an arbitrary location so the
    valid-location check uses the chosen site instead of the bundled default fixture.
    """
    global _ACTIVE_SITE
    _ACTIVE_SITE = site


def open_square_site(width_m: float, depth_m: float) -> dict[str, Any]:
    """Build a synthetic open-ground site: the full [0,width]x[0,depth] rectangle.

    No building/street exclusions — every point in the square is plantable. Used for
    "scan anywhere" surrogate placement when we have not (yet) fetched real building
    footprints for the polygon. The LIVE Infrared UTCI run still uses the REAL
    buildings fetched for the polygon, so the measured cooling reflects true geometry;
    only the surrogate's pre-screen treats the square as open. Building-aware
    placement for arbitrary sites is a planned refinement.
    """
    boundary = Polygon([(0.0, 0.0), (width_m, 0.0), (width_m, depth_m), (0.0, depth_m)])
    return {"boundary": boundary, "buildings": [], "streets": []}


def square_ring_lonlat(lon: float, lat: float, side_m: float) -> list[list[float]]:
    """Build a closed square WGS84 ring of side `side_m` centred on (lon, lat).

    Squared in UTM-31N (EPSG:32631) metres so it is a true metric square anywhere
    in Barcelona, then converted back to lon/lat. This is the "scan any location"
    primitive: pass the result to set_site_origin_from_polygon() to retarget the
    optimizer to that site, and as polygon_lonlat to the live Infrared UTCI call.

    Args:
        lon, lat: centre in WGS84 degrees.
        side_m:   square side length in metres.

    Returns:
        A closed ring [[lon,lat], ...] (5 points, first == last), CCW.
    """
    e, n = _TO_UTM.transform(lon, lat)
    h = side_m / 2.0
    corners_utm = [
        (e - h, n - h), (e + h, n - h), (e + h, n + h), (e - h, n + h), (e - h, n - h),
    ]
    return [list(_TO_WGS.transform(ee, nn)) for ee, nn in corners_utm]


def ensure_site_origin() -> None:
    """Public: guarantee the site origin + extents are initialized before use.

    Callers that read SITE_WIDTH_M/SITE_DEPTH_M (e.g. the NSGA-II optimizer building
    its decision-variable bounds) MUST call this first so the active-site extents are
    stable for the whole run. Without it, the first coordinate conversion could lazily
    change the extents MID-run, desyncing the optimizer's bounds from the geometry
    frame and making the surrogate result depend on init timing (non-deterministic).

    Idempotent — does nothing if the origin is already initialized.
    """
    _ensure_origin_initialized()


def _ensure_origin_initialized() -> None:
    """Lazily initialize the site origin from the default angels_site.geojson if needed.

    Called before any coordinate conversion when no explicit set_site_origin_from_polygon
    call has been made. Provides backwards-compatible fallback so existing tests and
    the NSGA-II optimizer work without explicitly calling set_site_origin_from_polygon.

    Default site origin: SW corner of the angels_site.geojson boundary polygon in UTM-31N.
    """
    global _ORIGIN_INITIALIZED
    if _ORIGIN_INITIALIZED:
        return

    # Load the default site boundary ring and set origin from it
    if DEFAULT_SITE.exists():
        with DEFAULT_SITE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        for feature in data.get("features", []):
            kind = feature.get("properties", {}).get("kind", "")
            geom = feature.get("geometry", {})
            if kind == "site_boundary" and geom.get("type") == "Polygon":
                ring = [(lon, lat) for lon, lat in geom["coordinates"][0]]
                set_site_origin_from_polygon(ring)
                return

    # Absolute fallback: derive from SITE_ORIGIN_LON/LAT (plaza centroid) if GeoJSON unavailable
    # The centroid is NOT the SW corner; approximate the SW corner from known 60x42 m dimensions.
    # This path is a last resort and documents its own limitation.
    global _SITE_ORIGIN_E, _SITE_ORIGIN_N
    e_ctr, n_ctr = _TO_UTM.transform(SITE_ORIGIN_LON, SITE_ORIGIN_LAT)
    _SITE_ORIGIN_E = e_ctr - SITE_WIDTH_M / 2.0
    _SITE_ORIGIN_N = n_ctr - SITE_DEPTH_M / 2.0
    _ORIGIN_INITIALIZED = True


# ── SINGLE CRS BOUNDARY (SPATIAL-03) ─────────────────────────────────────────


def latlon_to_local_m(lon: float, lat: float) -> tuple[float, float]:
    """Convert EPSG:4326 (lon, lat) to site-local metres (x_m, y_m) via UTM-31N.

    THIS IS THE ONLY PLACE CRS CONVERSION HAPPENS IN coolspend (SPATIAL-03).
    No other module may convert EPSG:4326 to local metres. Import this function
    from here — do not reproduce the formula elsewhere.

    Projection: UTM-31N (EPSG:32631) via pyproj, valid across all of Barcelona with
    sub-metre distortion (D-06). Per-site SW-corner local frame derived from UTM offsets.

    Local-metre frame: SW corner of the site polygon's UTM bounding box = (0, 0).
    x_m = East-West UTM offset from the SW corner (true metres).
    y_m = North-South UTM offset from the SW corner (true metres).
    For the default angels_site.geojson: x_m in [0, ~60], y_m in [0, ~42].
    For any other polygon: [0, width_m] x [0, depth_m] per set_site_origin_from_polygon.

    Per-site real calls: call set_site_origin_from_polygon(ring) first (done automatically
    by load_site()). Fallback for callers that never set an explicit origin: lazily
    initialised from the default site boundary (backwards-compatible).

    Args:
        lon: WGS84 longitude in decimal degrees.
        lat: WGS84 latitude in decimal degrees.

    Returns:
        (x_m, y_m) — position in site-local metres relative to the SW UTM corner.
    """
    _ensure_origin_initialized()
    e, n = _TO_UTM.transform(lon, lat)
    return (e - _SITE_ORIGIN_E, n - _SITE_ORIGIN_N)


def local_m_to_latlon(x_m: float, y_m: float) -> tuple[float, float]:
    """Convert site-local metres (x_m, y_m) to EPSG:4326 (lon, lat) via UTM-31N.

    THIS IS THE ONLY PLACE INVERSE CRS CONVERSION HAPPENS IN coolspend (SPATIAL-03).
    No other module may convert local metres to EPSG:4326. Import this function
    from here — do not reproduce the formula elsewhere.

    Exact algebraic inverse of latlon_to_local_m via pyproj UTM-31N transformers.
    Valid citywide in Barcelona (D-06). See latlon_to_local_m for frame conventions.

    Args:
        x_m: East-West position in site-local metres.
        y_m: North-South position in site-local metres.

    Returns:
        (lon, lat) — WGS84 longitude and latitude in decimal degrees.
    """
    _ensure_origin_initialized()
    lon, lat = _TO_WGS.transform(x_m + _SITE_ORIGIN_E, y_m + _SITE_ORIGIN_N)
    return lon, lat


# ── FAIL-CLOSED ROUND-TRIP GUARD (D-07) ──────────────────────────────────────


def assert_crs_roundtrip(
    ring_lonlat: list[tuple[float, float]] | list[list[float]],
    tol_m: float = 1.0,
) -> float:
    """Assert that every vertex in ring_lonlat round-trips through the CRS with <tol_m error.

    WGS84 -> UTM-31N (via latlon_to_local_m) -> WGS84 (via local_m_to_latlon),
    then measure the ground error in METRES using UTM-31N euclidean distance
    (NOT degrees — metres, as required by D-07).

    Fail-closed: if any vertex round-trips with error >= tol_m, raises CRSConsistencyError
    naming the worst error in metres. The SDK call that follows this guard is unreachable
    on failure — the exception propagates out.

    Args:
        ring_lonlat: Polygon ring as a list of [lon, lat] pairs or (lon, lat) tuples.
        tol_m: Tolerance in metres (default 1.0 m, per D-07).

    Returns:
        max_error_m: Maximum round-trip error in metres across all vertices. < tol_m.

    Raises:
        CRSConsistencyError: if any vertex round-trips with error >= tol_m (D-07).
    """
    max_error_m: float = 0.0

    for pair in ring_lonlat:
        lon, lat = float(pair[0]), float(pair[1])
        x_m, y_m = latlon_to_local_m(lon, lat)
        lon2, lat2 = local_m_to_latlon(x_m, y_m)

        # Measure error in UTM metres (NOT degrees) — D-07 requirement
        e1, n1 = _TO_UTM.transform(lon, lat)
        e2, n2 = _TO_UTM.transform(lon2, lat2)
        import math  # noqa: PLC0415 — kept inline for hot-path clarity
        error_m = math.hypot(e1 - e2, n1 - n2)
        if error_m > max_error_m:
            max_error_m = error_m

    if max_error_m >= tol_m:
        raise CRSConsistencyError(
            f"CRS round-trip {max_error_m:.3f} m exceeds {tol_m} m — "
            f"aborting live call (D-07)"
        )

    return max_error_m


# ── SITE CACHE ────────────────────────────────────────────────────────────────

_SITE_CACHE: dict[str, Any] = {}  # keyed by resolved path string


# ── SITE LOADER ───────────────────────────────────────────────────────────────


def load_site(path: str | None = None) -> dict[str, Any]:
    """Load a site GeoJSON fixture and return shapely geometries in local metres.

    Reads the file at `path` (default: bundled coolspend/data/angels_site.geojson)
    using json.load only — never exec/eval — per CONVENTIONS Rule 4.

    IMPORTANT: Before converting any feature coordinates, this function calls
    set_site_origin_from_polygon with the site_boundary ring, so the local-metre
    origin is the polygon's own SW UTM corner (per D-06). The NSGA-II optimizer
    bounds follow the site automatically.

    The GeoJSON must be a FeatureCollection with features keyed by
    `properties.kind`: "site_boundary", "building", "street".
    All coordinates are converted from EPSG:4326 (lon, lat) to site-local metres
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

    # First pass: find the site_boundary ring and set the per-site UTM origin (D-06).
    for feature in data.get("features", []):
        kind = feature.get("properties", {}).get("kind", "")
        geom = feature.get("geometry", {})
        if kind == "site_boundary" and geom.get("type") == "Polygon":
            ring_lonlat = [(lon, lat) for lon, lat in geom["coordinates"][0]]
            set_site_origin_from_polygon(ring_lonlat)
            break

    # Second pass: convert all feature coordinates now that the origin is set.
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

    Coordinates must be in site-local metres (SW UTM corner = (0, 0)).
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
        # Active-site override (scan anywhere) takes precedence over the default
        # fixture; load_site() is only called when neither is set. This prevents
        # the default-site loader from clobbering an explicit per-site origin.
        site = _ACTIVE_SITE if _ACTIVE_SITE is not None else load_site()

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


# ── THERMAL SURROGATE (OPT-02) ────────────────────────────────────────────────
#
# Fast, pure-math analytical proxy for ΔTmrt used in the NSGA-II hot path.
# ZERO SDK calls. ZERO file I/O. Fully deterministic.
#
# HONESTY NOTICE (CONCERNS 1.1 / T-02-04):
#   This is NOT a measured or simulated Tmrt result. It is a linear surrogate.
#   Tmrt-magnitude anchor: Schrodi et al. 2023 (arXiv:2310.05691, venue PENDING) —
#   tree-placement point-wise ΔTmrt; ML method cited for Tmrt magnitude ONLY
#   (we do NOT use their ML approach). Supporting anchor: Rahman et al. 2022
#   (tree-Tmrt anchor, DOI PENDING). Garcia-Nevado 2020 is a shade-structure /
#   surface-temperature ANALOGUE only (pavement IR thermography — surface temp,
#   NOT Tmrt at 1.1 m), demoted from primary anchor.
#   Uncertainty: ±4°C. MAX_TMRT_REDUCTION_C = 12.0°C is still an UNSOURCED
#   hard-coded linear cap — REQUIRES_VERIFICATION — see MOCKS.md.
#   Re-anchoring the Tmrt magnitude does NOT claim this cap is now sourced.
#
# POROSITY BUG (CONCERNS 4.2 / T-02-06 — FIXED):
#   The original nature_nsga2_coolstock.py body applied porosity twice (squared).
#   Porosity is now applied EXACTLY ONCE by the CALLER before passing shade_fraction.
#   The body uses shade_fraction as-is (effective_shade = shade_fraction).
#   Test test_delta_tmrt_no_double_porosity pins this fix permanently.

# SOURCE: nature_nsga2_coolstock.py lines 81-83 (Barcelona July peak sun geometry,
# analytical geometry at 41.38°N latitude)
PEAK_SUN_ALTITUDE_DEG: float = 63.0   # degrees above horizon at solar noon — Barcelona July
PEAK_SUN_AZIMUTH_DEG: float = 215.0   # SW afternoon peak — Barcelona July

# SOURCE: nature_nsga2_coolstock.py lines 138-146 (UNSOURCED operational cap — see CONCERNS 1.1)
# Tmrt-magnitude anchor: Schrodi et al. 2023 (arXiv:2310.05691, venue PENDING) + Rahman et al. 2022
# (DOI PENDING). Garcia-Nevado 2020 = surface-temp analogue, NOT Tmrt@1.1m.
# NOTE: re-anchoring the Tmrt magnitude does NOT source this linear cap — still REQUIRES_VERIFICATION.
# MOCK: unsourced conservative cap estimate, no error bar, no Ladybug/Infrared validation
MAX_TMRT_REDUCTION_C: float = 12.0    # °C — still an UNSOURCED linear cap — REQUIRES_VERIFICATION (see MOCKS.md)

# SOURCE: DECLARED — mature street-tree typical canopy shade fraction assumption
# REQUIRES_VERIFICATION: not from Barcelona Arbrat Viari data
TREE_SHADE_FRACTION: float = 0.80     # fraction of solar radiation blocked by a mature canopy

# SOURCE: DECLARED — typical effective shaded radius per street tree
# REQUIRES_VERIFICATION: not from surveyed Barcelona tree inventory
TREE_CANOPY_RADIUS_M: float = 3.0     # metres — effective shaded ground radius per tree

# Maximum fraction of the site we credit as canopy-shaded (no plaza is 100% canopy).
MAX_SITE_COVERAGE: float = 0.90       # cap on coverage_fraction — see MOCKS.md

# ── CORE-WEIGHTED COVERAGE CONSTANTS (REMEDIATION — Option A) ─────────────────
# SOURCE: DECLARED — modelling choice to create a genuine thermal↔ecological
# trade-off so the Pareto front is non-degenerate. Shading the pedestrian CORE
# (plaza centre, where people gather) is worth more than shading the perimeter.
# The thermal score therefore rewards CONCENTRATING canopy in the centre, which is
# in tension with the ecological objective (min-spacing + diversity push trees
# apart toward the edges). These are NOT surveyed footfall values —
# REQUIRES_VERIFICATION. See MOCKS.md.
CORE_BLEND: float = 0.6     # weight on the core-concentration term vs the spread term
CORE_RADIUS_M: float = 6.0   # radial reach (m) over which centre-proximity weight decays to 0
N_CORE_REF: float = 6.0      # reference: 6 canopies stacked on centre = full core score
# Backward-compatible aliases (documentation / centre sub-rectangle for viz).
CORE_FRACTION: float = 0.34  # central sub-rectangle fraction (used only by _core_rectangle/viz)
CORE_WEIGHT: float = CORE_BLEND  # legacy alias

# Site rectangle polygon, lazily built and cached (used to clip canopy unions).
_SITE_RECT_CACHE: dict[str, Any] = {}
# Core sub-rectangle polygon, lazily built and cached (for documentation/viz).
_CORE_RECT_CACHE: dict[str, Any] = {}


def _site_rectangle() -> Polygon:
    """Return (and cache) the plaza rectangle polygon in local metres.

    SW corner = (0, 0), extent SITE_WIDTH_M × SITE_DEPTH_M. Canopy unions are
    intersected with this rectangle so that canopy area spilling outside the
    site does not inflate coverage.
    """
    rect = _SITE_RECT_CACHE.get("rect")
    if rect is None:
        rect = Polygon(
            [
                (0.0, 0.0),
                (SITE_WIDTH_M, 0.0),
                (SITE_WIDTH_M, SITE_DEPTH_M),
                (0.0, SITE_DEPTH_M),
            ]
        )
        _SITE_RECT_CACHE["rect"] = rect
    return rect


def _core_rectangle() -> Polygon:
    """Return (and cache) the centred CORE sub-rectangle of the plaza.

    The core is the central CORE_FRACTION (34%) of each site dimension, centred on
    the plaza geometric centre. Canopy that falls inside this rectangle is the
    pedestrian-priority shade and is weighted CORE_WEIGHT× the perimeter (Option A).
    """
    rect = _CORE_RECT_CACHE.get("rect")
    if rect is None:
        half_w = SITE_WIDTH_M * CORE_FRACTION / 2.0
        half_d = SITE_DEPTH_M * CORE_FRACTION / 2.0
        cx = SITE_WIDTH_M / 2.0
        cy = SITE_DEPTH_M / 2.0
        rect = Polygon(
            [
                (cx - half_w, cy - half_d),
                (cx + half_w, cy - half_d),
                (cx + half_w, cy + half_d),
                (cx - half_w, cy + half_d),
            ]
        )
        _CORE_RECT_CACHE["rect"] = rect
    return rect


def core_weighted_coverage_fraction(active_trees: list[dict]) -> float:
    """Core-weighted canopy coverage as a fraction in [0, MAX_SITE_COVERAGE].

    REMEDIATION — Option A. This is the SHARED coverage model used by BOTH
    thermal_relief (objective F1) and optimizer._config_to_geometry (the mock-UTCI
    geometry payload) so the surrogate ranking and the mock UTCI stay consistent.

    The score is a blend of two pure-geometry terms (deterministic, no SDK, no file
    I/O beyond the cached rectangles):

      A) SPREAD term — non-overlapping canopy UNION clipped to the site, divided by
         site area. Maximised by DISPERSING trees so canopies cover distinct ground
         (overlap gives diminishing returns). Aligned with the ecological objective.

      B) CORE-CONCENTRATION term — a radial, OVERLAP-COUNTING sum of each tree's
         canopy area weighted by closeness to the plaza centre. A tree whose canopy
         sits on the centre contributes far more than one at the edge, and STACKING
         several canopies on the centre keeps adding value (overlap is NOT
         de-duplicated here). Maximised by CLUSTERING trees tightly in the centre —
         which drives them closer than the ecological MIN_SPACING and lowers the
         ecological score. This is the source of the genuine THERMAL↔ECOLOGICAL
         trade-off that spreads the Pareto front (root-cause fix — REMEDIATION).

    coverage = (1 - CORE_BLEND) * spread + CORE_BLEND * core_concentration,
    capped at MAX_SITE_COVERAGE.

    Both terms are normalised to [0, 1] so the blend is well-scaled. Because term B
    rewards centre-clustering and term A + the ecological objective reward spreading,
    no single placement maximises everything: the optimizer must trade thermal
    against ecological coherence, so np.unique(F) > 1.

    Args:
        active_trees: List of tree dicts each carrying "x_m" and "y_m" (metres).

    Returns:
        Core-weighted coverage fraction in [0, MAX_SITE_COVERAGE]. 0.0 for empty.
    """
    if not active_trees:
        return 0.0

    # ── Term A: SPREAD (non-overlapping union, clipped to site) ───────────────
    disks = [
        Point(float(t["x_m"]), float(t["y_m"])).buffer(TREE_CANOPY_RADIUS_M)
        for t in active_trees
    ]
    union = unary_union(disks)
    covered = union.intersection(_site_rectangle())
    site_area_m2 = SITE_WIDTH_M * SITE_DEPTH_M
    spread = covered.area / site_area_m2 if not covered.is_empty else 0.0

    # ── Term B: CORE CONCENTRATION (radial, overlap-counting) ─────────────────
    # Each tree contributes its full canopy area (π r²) scaled by a radial weight
    # that decays from 1.0 at the plaza centre to 0.0 at CORE_RADIUS_M. Overlap is
    # intentionally NOT removed: stacking canopies on the centre keeps adding value.
    cx = SITE_WIDTH_M / 2.0
    cy = SITE_DEPTH_M / 2.0
    canopy_area = 3.141592653589793 * TREE_CANOPY_RADIUS_M * TREE_CANOPY_RADIUS_M
    concentration = 0.0
    for t in active_trees:
        dx = float(t["x_m"]) - cx
        dy = float(t["y_m"]) - cy
        dist = (dx * dx + dy * dy) ** 0.5
        weight = max(0.0, 1.0 - dist / CORE_RADIUS_M)
        concentration += weight * canopy_area
    # Normalise by the value of N_CORE_REF canopies stacked exactly on the centre.
    core_norm = N_CORE_REF * canopy_area
    core_concentration = min(1.0, concentration / core_norm)

    fraction = (1.0 - CORE_BLEND) * spread + CORE_BLEND * core_concentration
    return min(fraction, MAX_SITE_COVERAGE)


def canopy_coverage_fraction(active_trees: list[dict]) -> float:
    """Non-overlapping canopy coverage of the site as a fraction in [0, MAX_SITE_COVERAGE].

    Builds the shapely union of canopy disks — Point(x_m, y_m).buffer(
    TREE_CANOPY_RADIUS_M) — for every active tree, intersects that union with the
    site rectangle, and divides the resulting area by the site area.

    This is PLACEMENT-SENSITIVE: overlapping/clustered trees share canopy area so
    their union grows slowly (diminishing returns), while dispersed trees cover
    distinct ground and yield a larger union → higher coverage → higher relief.
    Replaces the previous count-only model (count × π r² / area) that made the
    optimizer ranking degenerate on mock data (REMEDIATION — review finding #1).

    Pure geometry — no SDK calls, no file I/O beyond the cached site rectangle.
    Deterministic for a given set of coordinates.

    Args:
        active_trees: List of tree dicts each carrying "x_m" and "y_m" (metres).

    Returns:
        Union canopy area clipped to the site / site area, capped at
        MAX_SITE_COVERAGE. 0.0 for an empty list.
    """
    if not active_trees:
        return 0.0

    disks = [
        Point(float(t["x_m"]), float(t["y_m"])).buffer(TREE_CANOPY_RADIUS_M)
        for t in active_trees
    ]
    union = unary_union(disks)
    covered = union.intersection(_site_rectangle())
    site_area_m2 = SITE_WIDTH_M * SITE_DEPTH_M
    fraction = covered.area / site_area_m2
    return min(fraction, MAX_SITE_COVERAGE)


def shade_efficiency(tilt_deg: float, height_m: float) -> float:
    """Sun-path alignment bonus: canopy tilt/height modifies shade quality.

    Analytical geometry: tilt toward peak sun azimuth (SW, 215°) increases
    effective shade length by ~15% per 30° of tilt. Taller canopies slightly
    reduce reflected longwave from the ground (+5% per 2.5 m above 2.5 m base).

    Source: analytical geometry — adapted from Garcia-Nevado 2020 tilt analysis
    (nature_nsga2_coolstock.py lines 91-103). Uses math (not numpy) to keep the
    module numpy-light and usable in the NSGA-II hot path without array overhead.

    Args:
        tilt_deg: Canopy tilt angle in degrees toward peak sun azimuth (0 = flat).
        height_m: Canopy base height above ground in metres.

    Returns:
        Efficiency multiplier (>= 1.0 for tilt/height > baseline).
    """
    # Projected horizontal shade length increases with tilt aligned to sun
    tilt_factor = 1.0 + 0.15 * (tilt_deg / 30.0)
    # Height factor: higher canopy slightly reduces reflected longwave from ground
    height_factor = 1.0 + 0.05 * ((height_m - 2.5) / 2.5)
    return tilt_factor * height_factor


def delta_tmrt_surrogate(
    shade_fraction: float,
    porosity_pct: float = 0.0,
    tilt_deg: float = 0.0,
    height_m: float = 3.0,
) -> float:
    """Analytical proxy for mean radiant temperature reduction (ΔTmrt) at 1.1 m height.

    NOT MEASURED — analytical surrogate only. Use in the NSGA-II hot path.
    Validate Top-3 configs with real Infrared SDK UTCI calls (Plan 02-04).

    HONESTY FLAGS:
    - MAX_TMRT_REDUCTION_C = 12°C is still an UNSOURCED hard-coded linear cap —
      REQUIRES_VERIFICATION. Re-anchoring the Tmrt magnitude does NOT claim this cap
      is now sourced (see MOCKS.md / CONCERNS 1.1).
    - Tmrt-magnitude anchor: Schrodi et al. 2023 (arXiv:2310.05691, venue PENDING) —
      tree-placement point-wise ΔTmrt; ML method cited for Tmrt magnitude ONLY
      (we do NOT use their ML approach). Supporting: Rahman et al. 2022 (DOI PENDING).
      Garcia-Nevado 2020 = shade-structure / surface-temp ANALOGUE only (pavement IR
      thermography, NOT Tmrt at 1.1 m pedestrian height), demoted from primary anchor.
    - Uncertainty: ±4°C per parent audit_record.json.

    POROSITY FIX (CONCERNS 4.2 / T-02-06):
    Callers must pass shade_fraction = (1 - porosity_pct/100) * base_shade_fraction.
    The body does NOT re-apply porosity — effective_shade = shade_fraction exactly.
    The porosity_pct parameter is retained in the signature for call-site
    compatibility but is intentionally unused in the body (see CONCERNS 1.1 / 4.2).

    Args:
        shade_fraction: Effective fraction of solar radiation blocked, after any
                        porosity adjustment applied by the CALLER (0.0–1.0).
                        Do NOT pass raw shade fraction and expect this body to
                        apply porosity reduction — that was the bug.
        porosity_pct: Canopy porosity percentage (retained for signature compatibility;
                      NOT used in the body — porosity must be applied by caller).
        tilt_deg: Canopy tilt angle in degrees (0 = flat, 30 = toward SW peak sun).
        height_m: Canopy base height above ground in metres.

    Returns:
        Estimated ΔTmrt (°C cooling), capped at MAX_TMRT_REDUCTION_C. 0.0 for
        zero shade. Never negative (min 0.0 by construction for valid inputs).
    """
    # CONCERNS 1.1 / 4.2: porosity is applied ONCE by the caller; the body treats
    # shade_fraction as already-corrected effective shade. Do NOT multiply by
    # (1 - porosity_pct/100) here — that would square the porosity penalty.
    effective_shade = shade_fraction  # porosity already applied by caller (CONCERNS 4.2)
    eff = shade_efficiency(tilt_deg, height_m)
    return min(MAX_TMRT_REDUCTION_C * effective_shade * eff, MAX_TMRT_REDUCTION_C)


def thermal_relief(config: dict) -> float:
    """Estimate site-averaged ΔTmrt (°C) for a tree configuration.

    Aggregates per-tree surrogate cooling into a single site-level relief value
    the NSGA-II optimizer (Plan 02-03) maximises as objective F1 (thermal).
    Zero SDK calls — pure math, fully offline, deterministic.

    Method (CORE-WEIGHTED, PLACEMENT-SENSITIVE — REMEDIATION Option A):
    1. Collect active trees (active=True or no 'active' key — defaults True).
    2. Per-tree under-canopy ΔTmrt = delta_tmrt_surrogate(TREE_SHADE_FRACTION).
    3. site_coverage_fraction = core_weighted_coverage_fraction(active_trees) — the
       NON-OVERLAPPING shapely canopy union clipped to the site, with canopy in the
       central pedestrian CORE weighted CORE_WEIGHT× the perimeter, normalised and
       capped at MAX_SITE_COVERAGE (0.90).
    4. Return per_tree_delta × site_coverage_fraction (site-averaged relief).

    Because core m² count more than perimeter m², CONCENTRATING canopy in the plaza
    centre maximises thermal relief — directly opposing the ecological objective
    (spacing + diversity), which is maximised by spreading trees apart toward the
    edges. This genuine TRADE-OFF spreads the Pareto front so the optimizer ranking
    is non-degenerate on mock data (root cause fix — REMEDIATION review).

    Args:
        config: Dict with a "trees" list. Each tree may have:
                - "active": bool (default True if absent)
                - "x_m", "y_m": coordinates (NOW used — drive the union coverage)
                Other keys are ignored.

    Returns:
        Site-averaged ΔTmrt in °C, rounded to 3 decimal places. 0.0 for zero
        active trees. Always non-negative and <= MAX_TMRT_REDUCTION_C.
    """
    active_trees = [
        t for t in config.get("trees", [])
        if t.get("active", True)
    ]

    if not active_trees:
        return 0.0

    # Per-tree surrogate ΔTmrt — using canonical TREE_SHADE_FRACTION (DECLARED)
    per_tree_delta = delta_tmrt_surrogate(TREE_SHADE_FRACTION)

    # Core-weighted, placement-sensitive coverage (REMEDIATION Option A): canopy
    # union clipped to site, with the central pedestrian core weighted CORE_WEIGHT×.
    site_coverage_fraction = core_weighted_coverage_fraction(active_trees)

    return round(per_tree_delta * site_coverage_fraction, 3)


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

    # CRS round-trip check via UTM-31N
    _lon_rt, _lat_rt = local_m_to_latlon(*latlon_to_local_m(SITE_ORIGIN_LON, SITE_ORIGIN_LAT))
    import math as _math
    _e1, _n1 = _TO_UTM.transform(SITE_ORIGIN_LON, SITE_ORIGIN_LAT)
    _e2, _n2 = _TO_UTM.transform(_lon_rt, _lat_rt)
    _err_m = _math.hypot(_e1 - _e2, _n1 - _n2)
    print(f"CRS round-trip error: {_err_m:.4f} m (< 1 m required by D-07)")
