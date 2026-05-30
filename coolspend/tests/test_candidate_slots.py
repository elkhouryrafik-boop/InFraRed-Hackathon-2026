"""Tests for coolspend.candidate_slots — the building-aware slot engine.

The placement "must be perfect": these tests are the hard invariant — if any
generated slot lands on a building, in a street buffer, too close to a facade (per
its placement mode), or too close to an existing/another tree, the build fails.
"""
from __future__ import annotations

from shapely.geometry import Point

from coolspend import spatial_engine as se
from coolspend.candidate_slots import (
    generate_slots, validate_slots, MIN_SPACING_M,
    PLANTER, IN_GROUND, PLANTER_WALL_CLEARANCE_M, FOUNDATION_SETBACK_M,
    _building_clearance_for,
)


def test_planter_slots_respect_all_exclusions_on_real_fixture():
    """Every planter slot on the bundled Plaça dels Àngels fixture passes every rule."""
    site = se.load_site()  # real fixture: boundary + 2 buildings + 1 street
    slots = generate_slots(site, placement_mode=PLANTER)
    assert len(slots) > 0, "expected plantable planter slots on the plaza"
    assert all(s.mode == PLANTER for s in slots)
    validate_slots(slots, site)  # hard invariant


def test_in_ground_slots_respect_foundation_setback():
    """In-ground slots clear the larger FOUNDATION_SETBACK_M from every building."""
    site = se.load_site()
    slots = generate_slots(site, placement_mode=IN_GROUND)
    assert all(s.mode == IN_GROUND for s in slots)
    validate_slots(slots, site)  # hard invariant (mode-aware clearance)
    for s in slots:
        p = Point(s.x_m, s.y_m)
        for b in site["buildings"]:
            assert b.distance(p) >= FOUNDATION_SETBACK_M


def test_in_ground_is_stricter_than_planter():
    """Foundation setback >> planter clearance, so in-ground yields <= planter slots."""
    assert FOUNDATION_SETBACK_M > PLANTER_WALL_CLEARANCE_M
    site = se.load_site()
    planter = generate_slots(site, placement_mode=PLANTER)
    in_ground = generate_slots(site, placement_mode=IN_GROUND)
    assert len(in_ground) <= len(planter)


def test_existing_trees_block_their_neighbourhood():
    """A slot is rejected when an existing tree sits within MIN_SPACING_M."""
    site = se.load_site()
    base = generate_slots(site, placement_mode=PLANTER)
    assert base, "fixture should yield slots"
    occupied = (base[0].x_m, base[0].y_m)
    with_tree = generate_slots(site, existing_trees_m=[occupied], placement_mode=PLANTER)
    coords = {(s.x_m, s.y_m) for s in with_tree}
    assert occupied not in coords, "slot on top of an existing tree must be excluded"
    validate_slots(with_tree, site, existing_trees_m=[occupied])


def test_pairwise_spacing_holds():
    """No two accepted slots are closer than MIN_SPACING_M."""
    site = se.load_site()
    slots = generate_slots(site, placement_mode=PLANTER)
    pts = [Point(s.x_m, s.y_m) for s in slots]
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            assert pts[i].distance(pts[j]) >= MIN_SPACING_M


def test_clearance_helper_matches_mode():
    assert _building_clearance_for(PLANTER) == PLANTER_WALL_CLEARANCE_M
    assert _building_clearance_for(IN_GROUND) == FOUNDATION_SETBACK_M
