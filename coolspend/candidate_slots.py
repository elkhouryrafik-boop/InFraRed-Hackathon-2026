"""coolspend.candidate_slots — building-aware candidate planting slots (Phase 1).

The decision space for the measured-fitness search: only places where a tree can
REALLY go. A slot is valid ONLY if it passes EVERY exclusion:

  1. inside the site boundary polygon
  2. NOT inside any building footprint, and clear of facades by CROWN_CLEARANCE_M
  3. NOT within STREET_BUFFER_M of a street centerline
  4. NOT within MIN_SPACING_M of an existing tree (no double-planting)
  5. NOT within MIN_SPACING_M of another accepted slot (canopy spacing)

Coordinates are site-local metres (SW UTM corner = (0,0)), same frame as
spatial_engine. Real building footprints + streets come from the site dict
(Infrared/OSM fetch); existing trees come from the BCN inventory (bcn_data),
projected to local metres via the single CRS boundary.

HONESTY BOUNDARY (stated, not faked): these exclusions use the best available
open data — buildings, streets, existing trees. They do NOT encode underground
utilities, sidewalk-width adequacy, sightlines, or ownership, which open data does
not provide. "Valid slot" = best-available-data plantable, NOT survey-grade siting.
Final siting requires a utility + sidewalk survey. See validate_slots() for the
hard invariant enforced in tests.
"""
from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import Point

from coolspend import spatial_engine as se

# ── Slot constraints (DECLARED arboricultural guidelines — REQUIRES_VERIFICATION
# against Barcelona municipal planting code; see MOCKS.md ecological-rules row). ──
MIN_SPACING_M: float = 8.0
"""Minimum centre-to-centre spacing between trees (existing or proposed), metres.

8 m is the urban-design street-tree interval where three independent guidelines
converge: NACTO street trees 6–9 m o.c. (street-design), climate-responsive
"trees at 8–10 m create continuous canopy at maturity" (climate-responsive-design,
Mediterranean), and de-paving practice default 6–10 m (depaving_practice.md). 5 m
(the old value) packed canopies into overlapping clumps — too crowded, not an allée."""

GRID_STEP_M: float = 4.0
"""Candidate-grid pitch. Finer = more slots = finer search, more sim cost."""

# ── PLACEMENT MODE — the real-feasibility fork (user decision 2026-05-29) ──────
# PLANTER: tree in a large planter ON the pavement. Roots contained → NO foundation
#   risk → may sit near a building (only needs physical clearance from the wall).
#   No depaving. Capped mature crown (limited root volume). Higher watering OpEx.
# IN_GROUND: depaved pit, roots in soil → can damage foundations → must keep a
#   FOUNDATION_SETBACK_M from any building. Full mature crown. Depaving cost.
PLANTER: str = "planter"
IN_GROUND: str = "in_ground"

PLANTER_WALL_CLEARANCE_M: float = 0.6
"""Planter: physical clearance from a facade (planter body must not touch the wall)."""

FOUNDATION_SETBACK_M: float = 6.0
"""In-ground: min distance from a building so roots don't reach foundations.
Conservative single value for large street species — REQUIRES_VERIFICATION against
species-specific root-spread / municipal setback code. Planters bypass this entirely."""


def _building_clearance_for(mode: str) -> float:
    """Required facade clearance for a placement mode (planter vs in-ground)."""
    return PLANTER_WALL_CLEARANCE_M if mode == PLANTER else FOUNDATION_SETBACK_M


@dataclass(frozen=True)
class Slot:
    """One candidate planting location in site-local metres, with placement mode."""

    x_m: float
    y_m: float
    mode: str = PLANTER


def _buildings_clearance_ok(p: Point, site: dict, clearance_m: float) -> bool:
    """True if p is outside every building AND at least clearance_m from each facade."""
    for b in site.get("buildings", []):
        if b.contains(p) or b.distance(p) < clearance_m:
            return False
    return True


def generate_slots(
    site: dict,
    existing_trees_m: list[tuple[float, float]] | None = None,
    *,
    placement_mode: str = PLANTER,
    grid_step_m: float = GRID_STEP_M,
    min_spacing_m: float = MIN_SPACING_M,
) -> list[Slot]:
    """Generate building-aware candidate planting slots over the site.

    Greedy lattice scan: walk a grid_step_m grid over the site bbox, accept a cell
    only if it clears boundary, buildings (+facade clearance), streets, existing
    trees, and already-accepted slots (all by min_spacing_m). Deterministic order
    (row-major) so the slot set is reproducible for a given site.

    Args:
        site:            {"boundary": Polygon, "buildings": [...], "streets": [...]}
                         in site-local metres (from spatial_engine.load_site or
                         an open_square_site augmented with real footprints).
        existing_trees_m: existing tree positions in local metres (lon/lat projected
                         via spatial_engine.latlon_to_local_m). None -> none.
        placement_mode:  PLANTER (small wall clearance, no foundation setback) or
                         IN_GROUND (FOUNDATION_SETBACK_M from buildings — root safety).
        grid_step_m:     candidate grid pitch.
        min_spacing_m:   min centre-to-centre spacing to existing/accepted trees.

    Returns:
        List of accepted Slot(x_m, y_m, mode). Empty if nothing is plantable.
    """
    existing = list(existing_trees_m or [])
    clearance_m = _building_clearance_for(placement_mode)
    minx, miny, maxx, maxy = site["boundary"].bounds

    accepted: list[Slot] = []
    accepted_pts: list[Point] = []
    existing_pts = [Point(x, y) for x, y in existing]

    # Row-major lattice walk (deterministic).
    y = miny
    while y <= maxy:
        x = minx
        while x <= maxx:
            p = Point(x, y)
            if (
                se.is_valid_location(x, y, site=site)              # boundary + buildings + streets
                and _buildings_clearance_ok(p, site, clearance_m)  # mode-aware facade/foundation clearance
                and all(p.distance(e) >= min_spacing_m for e in existing_pts)
                and all(p.distance(a) >= min_spacing_m for a in accepted_pts)
            ):
                accepted.append(Slot(round(x, 3), round(y, 3), placement_mode))
                accepted_pts.append(p)
            x += grid_step_m
        y += grid_step_m
    return accepted


def validate_slots(
    slots: list[Slot],
    site: dict,
    existing_trees_m: list[tuple[float, float]] | None = None,
    *,
    min_spacing_m: float = MIN_SPACING_M,
) -> None:
    """Hard invariant: raise AssertionError if ANY slot violates ANY exclusion.

    This is the enforcement the placement "must be perfect" requirement demands —
    called in tests so the build fails if a single slot lands on a building, in a
    street buffer, too close to an existing/another tree, or closer to a facade than
    its own placement mode allows (in-ground needs FOUNDATION_SETBACK_M; a planter
    only needs PLANTER_WALL_CLEARANCE_M).
    """
    existing_pts = [Point(x, y) for x, y in (existing_trees_m or [])]
    pts = [Point(s.x_m, s.y_m) for s in slots]

    for s, p in zip(slots, pts):
        clearance_m = _building_clearance_for(s.mode)
        assert site["boundary"].contains(p), f"slot {s} outside boundary"
        for b in site.get("buildings", []):
            assert not b.contains(p), f"slot {s} inside a building"
            assert b.distance(p) >= clearance_m, (
                f"slot {s} too close to a facade for mode {s.mode} (<{clearance_m} m)"
            )
        for st in site.get("streets", []):
            assert st.distance(p) > se.STREET_BUFFER_M, f"slot {s} in street buffer"
        for e in existing_pts:
            assert p.distance(e) >= min_spacing_m, f"slot {s} too close to an existing tree"

    # Pairwise spacing among accepted slots.
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            assert pts[i].distance(pts[j]) >= min_spacing_m, (
                f"slots {slots[i]} and {slots[j]} closer than {min_spacing_m} m"
            )
