"""
coolspend/ground_analysis.py — impervious-pavement (depave) targeting.

The hero narrative is "rip up asphalt, plant trees". This module turns that into
a measured, honest target: it fetches Infrared's real ground-material polygons
(asphalt + concrete = impervious), clips them to the user's drawn area, and
reports how much depaveable pavement is actually there — plus how much of it the
proposed canopy would shade ("depaved + cooled").

Everything is REAL data from Infrared's /ground-material service (Mapbox land
cover). No surface is invented; when the service has no data for a material the
corresponding area is simply 0.

CRS: Infrared returns the material polygons in WGS84 lon/lat. All area math is
done in UTM-31N metres (the single CRS boundary in spatial_engine), and clipped
geometry is returned in lon/lat for the map overlay.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("coolspend.ground_analysis")

# Depaveable impervious ground is defined by COMPLEMENT: the site area minus
# everything that is already permeable (vegetation, soil, water) or not ground at
# all (building). This is more honest than summing the 'asphalt'/'concrete' layers
# directly — Infrared fills unclassified ground with a default 'asphalt' bbox
# rectangle (id 'default_bb'), and concrete polygons overlap it, so a naive sum
# double-counts and can exceed the site area. The complement uses only the REAL
# detected permeable/built features and never exceeds the site.
NON_IMPERVIOUS_MATERIALS = ("vegetation", "soil", "water", "building")


def _utm_transformers():
    from coolspend.spatial_engine import _TO_UTM, _TO_WGS  # noqa: PLC0415
    return _TO_UTM, _TO_WGS


def _polys_to_utm(feature_collection: dict, to_utm) -> list:
    """Convert every Polygon/MultiPolygon feature in a FC to shapely UTM polygons."""
    from shapely.geometry import shape  # noqa: PLC0415
    from shapely.ops import transform as shp_transform  # noqa: PLC0415

    def _proj(x, y, z=None):
        e, n = to_utm.transform(x, y)
        return (e, n)

    out = []
    for feat in feature_collection.get("features", []):
        geom = feat.get("geometry")
        if not geom:
            continue
        try:
            g = shape(geom)
            if not g.is_valid:
                g = g.buffer(0)
            out.append(shp_transform(_proj, g))
        except Exception:  # noqa: BLE001 — skip any malformed feature
            continue
    return out


def analyze_impervious(ring_lonlat: list[list[float]], backend: str = "live") -> dict[str, Any]:
    """Fetch + clip impervious pavement inside the drawn polygon.

    Args:
        ring_lonlat: drawn selection ring, [[lon,lat], ...] (open or closed).
        backend:     only "live" fetches Infrared ground materials; otherwise we
                     return an empty (but well-formed) result so offline/mock runs
                     never hit the network.

    Returns dict:
        {
          "impervious_m2":  float,           # depaveable paved ground inside polygon
          "permeable_m2":   float,           # vegetation+soil+water inside polygon
          "site_area_m2":   float,
          "impervious_fraction": float,      # 0..1
          "geojson":        FeatureCollection (lon/lat) of the depaveable polygon(s),
          "available":      bool,            # False if no live data / fetch failed
        }
    """
    from shapely.geometry import Polygon, mapping  # noqa: PLC0415
    from shapely.ops import transform as shp_transform, unary_union  # noqa: PLC0415

    to_utm, to_wgs = _utm_transformers()
    ring = [[float(p[0]), float(p[1])] for p in ring_lonlat]
    if ring[0] != ring[-1]:
        ring.append(ring[0])

    site_utm = Polygon([to_utm.transform(lon, lat) for lon, lat in ring]).buffer(0)
    site_area_m2 = float(site_utm.area)

    empty = {
        "impervious_m2": 0.0, "permeable_m2": 0.0,
        "site_area_m2": round(site_area_m2, 1), "impervious_fraction": 0.0,
        "permeable_fraction": 0.0,
        "permeable_target_min": 0.40, "permeable_target_max": 0.50,
        "geojson": {"type": "FeatureCollection", "features": []},
        "buildings_geojson": {"type": "FeatureCollection", "features": []},
        "available": False,
    }
    if backend != "live":
        return empty

    # ── Fetch real ground materials (live only) ──────────────────────────────
    try:
        from infrared_sdk import InfraredClient  # noqa: PLC0415
        polygon = {"type": "Polygon", "coordinates": [ring]}
        with InfraredClient() as client:
            gm = client.ground_materials.get_area(polygon)
        layers = gm.layers
    except Exception as exc:  # noqa: BLE001 — depave overlay is optional
        logger.warning("ground_materials fetch failed (%s); no impervious overlay", type(exc).__name__)
        return empty

    def _proj_back(x, y, z=None):
        lon, lat = to_wgs.transform(x, y)
        return (lon, lat)

    # Union of all NON-impervious surfaces (permeable + buildings), clipped to site.
    non_imperv_parts = []
    for mat in NON_IMPERVIOUS_MATERIALS:
        for poly_utm in _polys_to_utm(layers.get(mat) or {"features": []}, to_utm):
            clip = poly_utm.intersection(site_utm)
            if not clip.is_empty and clip.area > 0:
                non_imperv_parts.append(clip)
    non_imperv = unary_union(non_imperv_parts) if non_imperv_parts else None

    # Permeable-only (exclude buildings) for the readout.
    permeable_parts = []
    for mat in ("vegetation", "soil", "water"):
        for poly_utm in _polys_to_utm(layers.get(mat) or {"features": []}, to_utm):
            clip = poly_utm.intersection(site_utm)
            if not clip.is_empty and clip.area > 0:
                permeable_parts.append(clip)
    permeable_m2 = float(unary_union(permeable_parts).area) if permeable_parts else 0.0

    # Building footprints (lon/lat) — used by smart placement for foundation
    # setback. These are the only building geometry available in the WGS84 frame
    # (the dotBIM meshes are in Infrared's own local frame and not georeferenced).
    building_features: list[dict] = []
    for poly_utm in _polys_to_utm(layers.get("building") or {"features": []}, to_utm):
        clip = poly_utm.intersection(site_utm)
        if not clip.is_empty and clip.area > 0:
            building_features.append({
                "type": "Feature",
                "properties": {"material": "building"},
                "geometry": mapping(shp_transform(_proj_back, clip)),
            })

    # Depaveable impervious = site MINUS everything permeable/built.
    impervious_geom = site_utm.difference(non_imperv) if non_imperv else site_utm
    impervious_m2 = float(impervious_geom.area)

    clipped_features: list[dict] = []
    if not impervious_geom.is_empty:
        geoms = getattr(impervious_geom, "geoms", [impervious_geom])
        for g in geoms:
            if g.area <= 0:
                continue
            clipped_features.append({
                "type": "Feature",
                "properties": {"material": "impervious"},
                "geometry": mapping(shp_transform(_proj_back, g)),
            })

    return {
        "impervious_m2": round(impervious_m2, 1),
        "permeable_m2": round(permeable_m2, 1),
        "site_area_m2": round(site_area_m2, 1),
        "impervious_fraction": round(impervious_m2 / site_area_m2, 3) if site_area_m2 else 0.0,
        # Climate-responsive-design target for Mediterranean/Csa is 40-50% permeable.
        "permeable_fraction": round(permeable_m2 / site_area_m2, 3) if site_area_m2 else 0.0,
        "permeable_target_min": 0.40, "permeable_target_max": 0.50,
        "geojson": {"type": "FeatureCollection", "features": clipped_features},
        "buildings_geojson": {"type": "FeatureCollection", "features": building_features},
        "available": bool(clipped_features),
    }


def _crown_m(tree: dict, default_crown_m: float) -> float:
    """Resolve a tree's crown diameter (m): explicit field, else species table, else default.

    trees_lonlat carries only {lon, lat, species} (optimizer._config_to_geometry),
    so the mature crown comes from the sourced Verd Urbà bands in bcn_species.
    """
    explicit = tree.get("crown_diameter_m")
    if explicit:
        return float(explicit)
    sp = tree.get("species")
    if sp:
        from coolspend.bcn_species import get_species  # noqa: PLC0415
        s = get_species(sp)
        if s is not None:
            return float(s.crown_diameter_m)
    return default_crown_m


def _canopy_union_utm(trees_lonlat: list[dict], to_utm, default_crown_m: float):
    """Shapely union of per-species canopy disks (UTM metres), or None if no trees."""
    from shapely.geometry import Point  # noqa: PLC0415
    from shapely.ops import unary_union  # noqa: PLC0415

    disks = []
    for t in trees_lonlat:
        lon, lat = t.get("lon"), t.get("lat")
        if lon is None or lat is None:
            continue
        e, n = to_utm.transform(lon, lat)
        disks.append(Point(e, n).buffer(_crown_m(t, default_crown_m) / 2.0))
    return unary_union(disks) if disks else None


def depaved_by_canopy(
    impervious_geojson: dict,
    trees_lonlat: list[dict],
    default_crown_m: float = 6.0,
) -> float:
    """m² of impervious pavement that proposed tree canopies would cover (depave+cool).

    Each tree is a canopy disk (per-species crown radius) centred at its location;
    the union of those disks intersected with the impervious polygons = the
    depaved-and-shaded footprint. All in UTM metres.
    """
    if not impervious_geojson.get("features") or not trees_lonlat:
        return 0.0
    from shapely.geometry import shape  # noqa: PLC0415
    from shapely.ops import transform as shp_transform, unary_union  # noqa: PLC0415

    to_utm, _ = _utm_transformers()

    def _proj(x, y, z=None):
        e, n = to_utm.transform(x, y)
        return (e, n)

    impervious = unary_union([
        shp_transform(_proj, shape(f["geometry"])).buffer(0)
        for f in impervious_geojson["features"]
    ])
    canopy = _canopy_union_utm(trees_lonlat, to_utm, default_crown_m)
    if canopy is None:
        return 0.0
    return round(float(canopy.intersection(impervious).area), 1)


def canopy_cover_fraction(
    ring_lonlat: list[list[float]],
    trees_lonlat: list[dict],
    default_crown_m: float = 6.0,
) -> dict[str, Any]:
    """Non-overlapping canopy cover of the site as a fraction, vs the 30-40% target.

    Climate-responsive-design target for Temperate/Mediterranean residential areas
    is 30-40% canopy cover. This reports the REAL placement-sensitive cover (union
    of per-species canopy disks clipped to the site / site area), so clustered trees
    correctly share canopy rather than double-counting.

    Returns {cover_fraction, canopy_m2, site_area_m2, target_min, target_max, in_band}.
    """
    from shapely.geometry import Polygon  # noqa: PLC0415

    to_utm, _ = _utm_transformers()
    ring = [[float(p[0]), float(p[1])] for p in ring_lonlat]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    site = Polygon([to_utm.transform(lon, lat) for lon, lat in ring]).buffer(0)
    site_area = float(site.area)

    canopy = _canopy_union_utm(trees_lonlat, to_utm, default_crown_m)
    canopy_m2 = float(canopy.intersection(site).area) if canopy is not None else 0.0
    frac = canopy_m2 / site_area if site_area else 0.0
    return {
        "cover_fraction": round(frac, 3),
        "canopy_m2": round(canopy_m2, 1),
        "site_area_m2": round(site_area, 1),
        "target_min": 0.30,
        "target_max": 0.40,
        "in_band": 0.30 <= frac <= 0.40,
    }
