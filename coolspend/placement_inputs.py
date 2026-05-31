"""
coolspend/placement_inputs.py — assemble the REAL inputs for smart_placement.

Turns live signals into the demand field + candidate slots the greedy engine
consumes:

  demand cells  = grid cells that are HOT (live UTCI above comfort) AND IMPERVIOUS
                  (Infrared ground-material) AND NOT ALREADY SHADED (BCN inventory +
                  LiDAR canopy). weight = degrees of UTCI above the comfort threshold.
  candidates    = building-aware plantable slots (candidate_slots), using REAL building
                  footprints from the Infrared ground-material 'building' layer
                  (lon/lat — the correct frame, unlike the dotBIM meshes).

The numeric core (build_demand_cells) is PURE: membership + projection are injected
as callables, so it is fully unit-testable offline. The live wrapper
(assemble_inputs) supplies the real shapely / CRS / SDK predicates.

Coordinate frame: the caller MUST have set the site origin from the polygon
(spatial_engine.set_site_origin_from_polygon) before calling the live wrapper, so
local-metre coordinates are consistent across demand, candidates, and existing canopy.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

from coolspend.smart_placement import (
    DemandCell,
    SpeciesOption,
    CandidateSlot,
    PlacementResult,
    place_trees_greedy,
)

logger = logging.getLogger("coolspend.placement_inputs")

_REPO_ROOT = Path(__file__).resolve().parent.parent
_INTERVENTION_COSTS = _REPO_ROOT / "L1_INGEST_data" / "data_for_all" / "intervention_costs.json"

# Per in-ground tree, the de-paved + reconstructed pit footprint (m²). 3 m x 3 m is
# a conservative Barcelona structural tree-pit + permeable ring. DECLARED modelling
# choice; the €/m² it multiplies is the HIGH-confidence BIMSA figure.
DEPAVE_PIT_AREA_M2: float = 9.0

# Comfort threshold: UTCI at/above this is "hot" and worth shading. 26 °C is the
# official UTCI no-stress→moderate-heat-stress boundary, and matches the project's
# UTCI_HEAT_STRESS_C (sdk_client) so demand is consistent with the headline metric.
COMFORT_UTCI_C: float = 26.0


def grid_cell_lonlat(
    row: int, col: int, n_rows: int, n_cols: int, bounds: dict[str, float]
) -> tuple[float, float]:
    """Centre lon/lat of grid cell (row, col). Row 0 = NORTH (matches export_web)."""
    west, south = bounds["west"], bounds["south"]
    east, north = bounds["east"], bounds["north"]
    lon = west + (col + 0.5) / n_cols * (east - west)
    lat = north - (row + 0.5) / n_rows * (north - south)
    return lon, lat


def _crop_grid_to_valid(grid: list[list[float]]) -> list[list[float]]:
    """Crop a UTCI grid to its non-NaN bounding box.

    The SDK returns a square grid larger than the site polygon, with valid cells in
    a corner. Cropping to the valid bbox makes the returned grid span the polygon's
    own bbox, so build_demand_cells (which maps row/col over the polygon bounds)
    positions demand cells correctly. No-op if numpy is unavailable or all-valid.
    """
    try:
        import numpy as np  # noqa: PLC0415
    except ImportError:
        return grid
    a = np.asarray(grid, dtype=float)
    if a.ndim != 2:
        return grid
    valid = ~np.isnan(a)
    if not valid.any():
        return grid
    rows = np.where(valid.any(axis=1))[0]
    cols = np.where(valid.any(axis=0))[0]
    sub = a[rows.min(): rows.max() + 1, cols.min(): cols.max() + 1]
    return sub.tolist()


def build_demand_cells(
    grid: list[list[float]],
    bounds: dict[str, float],
    *,
    is_impervious: Callable[[float, float], bool],
    is_shaded: Callable[[float, float], bool],
    to_local_m: Callable[[float, float], tuple[float, float]],
    comfort_c: float = COMFORT_UTCI_C,
) -> list[DemandCell]:
    """Build weighted demand cells from a baseline UTCI grid (PURE — injected predicates).

    A cell becomes demand iff it is hotter than comfort_c, impervious, and not already
    shaded. Its weight is (UTCI − comfort_c): hotter ground is higher cooling priority.

    Args:
        grid:          2-D UTCI values (°C), row 0 = north. NaN cells (outside the
                       polygon) are skipped.
        bounds:        {west, south, east, north} lon/lat extent of the grid.
        is_impervious: (lon, lat) -> True if the cell is paved (depave candidate).
        is_shaded:     (lon, lat) -> True if already under existing canopy.
        to_local_m:    (lon, lat) -> (x_m, y_m) in the site-local frame.
        comfort_c:     UTCI comfort threshold.

    Returns:
        List of DemandCell in site-local metres.
    """
    n_rows = len(grid)
    if n_rows == 0:
        return []
    n_cols = len(grid[0])
    cells: list[DemandCell] = []
    for r in range(n_rows):
        rowvals = grid[r]
        for c in range(n_cols):
            v = rowvals[c]
            if v is None:
                continue
            try:
                heat = float(v) - comfort_c
            except (TypeError, ValueError):
                continue
            if heat <= 0 or heat != heat:  # not hot, or NaN
                continue
            lon, lat = grid_cell_lonlat(r, c, n_rows, n_cols, bounds)
            if not is_impervious(lon, lat):
                continue
            if is_shaded(lon, lat):
                continue
            x_m, y_m = to_local_m(lon, lat)
            cells.append(DemandCell(x_m, y_m, round(heat, 4)))
    return cells


def _depave_cost_per_tree() -> float:
    """Per in-ground tree de-pave cost = pit area × sourced BIMSA €/m² (central)."""
    try:
        d = json.loads(_INTERVENTION_COSTS.read_text(encoding="utf-8"))
        per_m2 = d["intervention_types"]["de-paving"]["cost_per_m2_eur"]["central"]
    except Exception:  # noqa: BLE001 — fall back to the documented central figure
        per_m2 = 600.0
    return float(per_m2) * DEPAVE_PIT_AREA_M2


def build_species_options() -> list[SpeciesOption]:
    """Plantable Barcelona palette → SpeciesOption (crown, lifecycle cost, cooling proxy).

    EXCLUDES the species Barcelona treats as exotic-invasive (Robinia, Ligustrum
    lucidum, Ulmus pumila) — same plantable set the NSGA-II path uses
    (coolspend.optimizer.SPECIES), so the greedy placement never recommends an
    invasive either. See coolspend.ecology.
    """
    from coolspend.bcn_species import SPECIES_TABLE, cooling_score  # noqa: PLC0415
    from coolspend.cost_model import DEFAULT_COST_TABLE, DEFAULT_GROWTH_DISCOUNT  # noqa: PLC0415
    from coolspend.ecology import is_plantable  # noqa: PLC0415

    tree_cost = DEFAULT_COST_TABLE.per_tree_cost(DEFAULT_GROWTH_DISCOUNT.horizon_years)
    return [
        SpeciesOption(
            name=s.scientific,
            crown_m=s.crown_diameter_m,
            tree_cost_eur=float(tree_cost),
            cooling_score=cooling_score(s),
        )
        for s in SPECIES_TABLE
        if is_plantable(s.scientific)
    ]


def assemble_inputs(geometry: dict, backend: str = "live"):
    """Fetch + build the REAL demand field and candidate slots for a polygon.

    Live: needs INFRARED_BACKEND=live (UTCI grid + ground materials). Sets the site
    origin from the polygon so all local-metre coordinates share one frame.

    Returns (demand_cells, candidate_slots, species_options) or raises on hard failure.
    """
    from shapely.geometry import Polygon, Point  # noqa: PLC0415
    from shapely.prepared import prep  # noqa: PLC0415
    from coolspend.spatial_engine import (  # noqa: PLC0415
        set_site_origin_from_polygon, set_active_site, latlon_to_local_m,
    )
    from coolspend.sdk_client import get_baseline_utci  # noqa: PLC0415
    from coolspend.ground_analysis import analyze_impervious, _utm_transformers, _polys_to_utm  # noqa: PLC0415
    from coolspend.bcn_data import load_trees  # noqa: PLC0415
    from coolspend.bcn_species import get_species  # noqa: PLC0415
    from coolspend.candidate_slots import generate_slots, IN_GROUND  # noqa: PLC0415

    ring = [[float(p[0]), float(p[1])] for p in geometry["polygon_lonlat"]]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    bounds = {"west": min(lons), "south": min(lats), "east": max(lons), "north": max(lats)}

    # One shared frame for demand + candidates + canopy.
    set_site_origin_from_polygon([(p[0], p[1]) for p in ring])

    # ── Baseline UTCI grid → heat signal (demand WEIGHTS) ─────────────────────
    # Live/cached: real per-cell UTCI grid → heat-weighted demand.
    # Mock/scalar (no grid): the cooling NUMBER is synthetic, but PLACEMENT must
    # still be valid. Fall back to a uniform proxy demand over the site so the
    # greedy spreads trees to cover the most plantable ground — the candidate
    # slots remain fully building-/street-/spacing-validated either way, so the
    # placement is real even when the cooling estimate is a labelled preview.
    baseline = get_baseline_utci({"polygon_lonlat": ring})
    grid = baseline.merged_grid
    proxy_demand = not grid
    if proxy_demand:
        n = 40  # ~uniform lattice over the bbox; cell pitch ≈ site_size / 40
        grid = [[COMFORT_UTCI_C + 1.0] * n for _ in range(n)]
    else:
        # The SDK returns a 512×512 grid spanning a square LARGER than the polygon,
        # with the polygon's valid (non-NaN) cells in a corner. build_demand_cells
        # maps grid (row,col) → lon/lat assuming the grid spans the polygon bbox, so
        # the full uncropped grid would scatter demand to the WRONG positions (the
        # exact registration bug fixed for the heatmap PNG) → demand misses every
        # candidate slot → zero trees. Crop to the non-NaN bounding box so the grid
        # we hand to build_demand_cells really does span the polygon bbox.
        grid = _crop_grid_to_valid(grid)

    # ── Impervious (depave candidates) — prepared lon/lat union for fast tests ─
    imperv = analyze_impervious(ring, backend=backend)
    to_utm, to_wgs = _utm_transformers()
    from shapely.geometry import shape  # noqa: PLC0415
    from shapely.ops import unary_union, transform as shp_transform  # noqa: PLC0415
    if imperv["geojson"]["features"]:
        imperv_ll = unary_union([shape(f["geometry"]).buffer(0) for f in imperv["geojson"]["features"]])
    else:
        imperv_ll = None
    prep_imperv = prep(imperv_ll) if imperv_ll is not None else None

    def is_impervious(lon: float, lat: float) -> bool:
        # No ground data → treat all as paveable (don't over-restrict demand).
        return True if prep_imperv is None else prep_imperv.contains(Point(lon, lat))

    # ── Existing canopy (already-shaded) — project trees to local m once ───────
    existing = load_trees(bbox=(bounds["west"], bounds["south"], bounds["east"], bounds["north"]))
    existing_m: list[tuple[float, float, float]] = []  # (x, y, crown_radius)
    for t in existing:
        sp = get_species(t.get("species") or "")
        crown = sp.crown_diameter_m if sp else 5.0
        x, y = latlon_to_local_m(t["lon"], t["lat"])
        existing_m.append((x, y, crown / 2.0))

    def is_shaded(lon: float, lat: float) -> bool:
        x, y = latlon_to_local_m(lon, lat)
        for ex, ey, er in existing_m:
            if (x - ex) ** 2 + (y - ey) ** 2 <= er * er:
                return True
        return False

    demand = build_demand_cells(
        grid, bounds,
        is_impervious=is_impervious, is_shaded=is_shaded, to_local_m=latlon_to_local_m,
    )
    # Robustness fallback: if the ground-material layer classified ~no impervious
    # surface inside the site (sparse/misclassified land cover — e.g. a paved plaza
    # tagged vegetation), the impervious filter would wipe out all demand and place
    # ZERO trees on a genuinely plantable site. When that happens, target ALL hot,
    # unshaded ground instead (drop only the impervious gate). Honest degradation:
    # we couldn't confirm pavement, so we shade the hottest unshaded ground we can.
    if not demand:
        logger.warning(
            "No impervious-classified demand in site; falling back to all hot, "
            "unshaded ground (ground-material layer too sparse to localise pavement)."
        )
        demand = build_demand_cells(
            grid, bounds,
            is_impervious=lambda lon, lat: True, is_shaded=is_shaded,
            to_local_m=latlon_to_local_m,
        )

    # ── Candidate slots: building-aware, using ground-material buildings (lon/lat) ─
    # Building footprints come from analyze_impervious' buildings_geojson (the only
    # georeferenced building geometry available); projected to local m they enforce
    # the in-ground foundation setback in candidate_slots.
    buildings_m = []
    for f in imperv.get("buildings_geojson", {}).get("features", []):
        try:
            g = shape(f["geometry"])
            buildings_m.append(shp_transform(lambda x, y, z=None: latlon_to_local_m(x, y), g).buffer(0))
        except Exception:  # noqa: BLE001 — skip a malformed footprint
            continue
    # OSM building footprints — backend-INDEPENDENT (free, no Infrared key). This is
    # what keeps a tree off a roof / clear of a facade on mock & cached, where the
    # Infrared building layer above is empty. Union of both = best available coverage.
    from coolspend.osm_buildings import buildings_local_m  # noqa: PLC0415
    buildings_m += buildings_local_m(bounds, latlon_to_local_m)
    # Spatial-layer exclusions (docs/placement_spatial_constraints.md), all OSM-derived,
    # all degrade to [] if Overpass is unreachable (logged, never faked):
    #   - road carriageways (vehicle only; plazas/footways stay plantable)
    #   - road-junction sight triangles
    #   - street furniture: hydrants, crossings, stops, lamps, signals, manholes, power lines
    from coolspend.osm_roads import (  # noqa: PLC0415
        road_exclusion_polygons_local_m, road_junction_exclusions_local_m,
    )
    from coolspend.osm_features import feature_exclusion_polygons_local_m  # noqa: PLC0415
    streets_m = (
        road_exclusion_polygons_local_m(bounds, latlon_to_local_m)
        + road_junction_exclusions_local_m(bounds, latlon_to_local_m)
        + feature_exclusion_polygons_local_m(bounds, latlon_to_local_m)
    )

    boundary_m = Polygon([latlon_to_local_m(p[0], p[1]) for p in ring])
    site = {"boundary": boundary_m, "buildings": buildings_m, "streets": streets_m}
    set_active_site(site)
    existing_xy = [(x, y) for (x, y, _) in existing_m]
    slots = generate_slots(site, existing_xy, placement_mode=IN_GROUND)

    # Species-to-site matching: cap each slot's crown by the available planting width
    # = 2 × distance to the nearest building / road-or-furniture exclusion. A wide
    # plaza slot can host a big plane; a tight strip only a small species.
    buildings_union = unary_union(buildings_m) if buildings_m else None

    def _max_crown(x: float, y: float) -> float:
        # Cap the mature crown by the distance to the nearest BUILDING FACADE only —
        # a canopy must not grow into a wall. Streets/sidewalks are deliberately NOT
        # a cap: a street tree's canopy SHOULD overhang the carriageway/footway (that
        # is the shade we are buying); the trunk is already kept out of the street
        # buffer by candidate_slots. Including streets here wrongly shrank the crown
        # below the smallest species (5 m) on tight sites and placed zero trees.
        if buildings_union is None:
            return float("inf")
        return max(5.0, 2.0 * buildings_union.distance(Point(x, y)))

    depave = _depave_cost_per_tree()
    candidates = [
        CandidateSlot(s.x_m, s.y_m, s.mode, depave_cost_eur=depave, max_crown_m=_max_crown(s.x_m, s.y_m))
        for s in slots
    ]

    species = build_species_options()

    # Plantable strip area (PAPER limitation #7): boundary minus the bits a tree
    # cannot occupy (buildings ∪ street/furniture buffers), clipped to the site.
    # This is the truer denominator for local canopy-cover % than the raw cell.
    try:
        blocked = unary_union([g for g in (buildings_m + streets_m) if g is not None])
        plantable_geom = boundary_m.difference(blocked) if not blocked.is_empty else boundary_m
        plantable_area_m2 = max(0.0, float(plantable_geom.area))
    except Exception:  # noqa: BLE001 — degrade to boundary area if geometry is messy
        plantable_area_m2 = float(boundary_m.area)

    logger.info(
        "placement inputs: %d demand cells, %d candidate slots, %d species "
        "(depave €%.0f/tree, plantable %.0f m²)",
        len(demand), len(candidates), len(species), depave, plantable_area_m2,
    )
    return demand, candidates, species, plantable_area_m2


def run_smart_placement(geometry: dict, budget_eur: float, backend: str = "live") -> dict:
    """End-to-end Mode 1: assemble real inputs → greedy placement → layout dict.

    Returns {trees_lonlat, placement_result, demand_total, coverage_fraction, cost_eur}.
    The returned trees_lonlat feeds the live UTCI validation (sdk_client) for the
    ground-truth ΔUTCI — this function itself does the placement, not the validation.
    """
    from coolspend.spatial_engine import local_m_to_latlon  # noqa: PLC0415

    demand, candidates, species, plantable_area_m2 = assemble_inputs(geometry, backend=backend)
    result: PlacementResult = place_trees_greedy(
        demand, candidates, species, budget_eur=budget_eur,
    )
    trees_lonlat = []
    for t in result.placed:
        lon, lat = local_m_to_latlon(t.x_m, t.y_m)
        trees_lonlat.append({
            "lon": round(lon, 8), "lat": round(lat, 8),
            "species": t.species, "mode": t.mode,
            # HONESTY (A9 gap): underground utilities are not in open data. An
            # in-ground (depave) pit cannot be cleared of buried mains from open
            # data alone, so flag it for a pre-dig utility survey rather than
            # asserting clearance we cannot see.
            "requires_utility_survey": t.mode == "in_ground",
        })
    return {
        "trees_lonlat": trees_lonlat,
        "tree_count": len(trees_lonlat),
        "cost_eur": result.total_cost_eur,
        "coverage_fraction": round(result.coverage_fraction, 4),
        "demand_total": round(result.total_demand_weight, 2),
        "covered_weight": round(result.covered_weight, 2),
        "stop_reason": result.stop_reason,
        "plantable_area_m2": round(plantable_area_m2, 1),
    }
