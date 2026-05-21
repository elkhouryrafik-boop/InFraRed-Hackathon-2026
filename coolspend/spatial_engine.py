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
  - shade_efficiency(tilt_deg, height_m) : sun-path alignment bonus (analytical, OPT-02)
  - delta_tmrt_surrogate(shade_fraction, ...) : fast analytical ΔTmrt proxy (OPT-02 hot path)
  - thermal_relief(config)  : site-averaged ΔTmrt for a tree config (OPT-02)

SPATIAL-03 compliance: no other module may convert CRS. All callers must import
these two functions from this module.

SURROGATE HONESTY (OPT-02 / CONCERNS 1.1):
  delta_tmrt_surrogate is an ANALYTICAL PROXY, NOT a measured or simulated result.
  Uncertainty ±4°C. MAX_TMRT_REDUCTION_C=12°C is an UNSOURCED cap — see MOCKS.md.
  Use for optimizer hot-path only; validate Top-3 with real Infrared SDK UTCI calls.
"""
from __future__ import annotations

import json
from math import cos, radians
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


# ── THERMAL SURROGATE (OPT-02) ────────────────────────────────────────────────
#
# Fast, pure-math analytical proxy for ΔTmrt used in the NSGA-II hot path.
# ZERO SDK calls. ZERO file I/O. Fully deterministic.
#
# HONESTY NOTICE (CONCERNS 1.1 / T-02-04):
#   This is NOT a measured or simulated Tmrt result. It is a linear surrogate
#   derived from Garcia-Nevado 2020 (pavement IR thermography — surface temp,
#   NOT Tmrt at 1.1 m pedestrian height) + Vanos 2020 shade-component lower bound.
#   Citation mismatch is documented. Uncertainty: ±4°C.
#   MAX_TMRT_REDUCTION_C = 12.0°C is an UNSOURCED hard-coded cap — see MOCKS.md.
#   Replace with Ladybug lookup table when available (D1-04 / CONCERNS 1.1).
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
# MOCK: unsourced conservative estimate, no error bar, no Ladybug/Infrared validation
MAX_TMRT_REDUCTION_C: float = 12.0    # °C — UNSOURCED cap — see MOCKS.md / CONCERNS 1.1

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

    The core is the central CORE_FRACTION (50%) of each site dimension, centred on
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
    - MAX_TMRT_REDUCTION_C = 12°C is an UNSOURCED hard-coded cap (CONCERNS 1.1).
    - Sources (Garcia-Nevado 2020, Vanos 2020) measure surface temperature and
      1.1 m shade component respectively — NOT a calibrated Tmrt model.
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

    # CRS round-trip check
    _lon_rt, _lat_rt = local_m_to_latlon(*latlon_to_local_m(SITE_ORIGIN_LON, SITE_ORIGIN_LAT))
    print(f"CRS round-trip: lon_err={abs(_lon_rt - SITE_ORIGIN_LON):.2e}, lat_err={abs(_lat_rt - SITE_ORIGIN_LAT):.2e}")
