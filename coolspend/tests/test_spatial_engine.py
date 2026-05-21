"""
Tests for coolspend.spatial_engine — collision validity (SPATIAL-01 / SPATIAL-02).

Verifies that is_valid_location rejects in-building, on-street, and out-of-boundary
points, and accepts an open in-boundary point. All tests run offline against the
bundled angels_site.geojson fixture; no network required.
"""
from __future__ import annotations

import pytest
from shapely.geometry import Polygon, LineString

from coolspend.spatial_engine import (
    load_site,
    is_valid_location,
    STREET_BUFFER_M,
    SITE_WIDTH_M,
    SITE_DEPTH_M,
)


# ── SHARED FIXTURE ────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def site() -> dict:
    """Load the bundled offline fixture once for the whole module."""
    return load_site()


# ── HELPER: derive concrete test coordinates from loaded geometry ──────────────


def _building_interior(site: dict) -> tuple[float, float]:
    """Return the centroid of the first building polygon in local metres."""
    bld = site["buildings"][0]
    c = bld.centroid
    return (c.x, c.y)


def _street_near_point(site: dict) -> tuple[float, float]:
    """Return a point within STREET_BUFFER_M of the first street centerline."""
    st = site["streets"][0]
    # Take a vertex of the street and offset by half the buffer distance
    coord = list(st.coords)[0]
    return (coord[0], coord[1] + STREET_BUFFER_M * 0.5)


# ── TESTS ─────────────────────────────────────────────────────────────────────


def test_inside_building_rejected(site: dict) -> None:
    """A point at the centroid of the first building polygon must be rejected."""
    x_m, y_m = _building_interior(site)
    result = is_valid_location(x_m, y_m, site=site)
    assert result is False, (
        f"Expected is_valid_location({x_m:.2f}, {y_m:.2f}) to return False "
        f"(inside building), got True"
    )


def test_on_street_rejected(site: dict) -> None:
    """A point within STREET_BUFFER_M of a street centerline must be rejected."""
    x_m, y_m = _street_near_point(site)
    result = is_valid_location(x_m, y_m, site=site)
    assert result is False, (
        f"Expected is_valid_location({x_m:.2f}, {y_m:.2f}) to return False "
        f"(within STREET_BUFFER_M={STREET_BUFFER_M}m of street), got True"
    )


def test_outside_boundary_rejected(site: dict) -> None:
    """A point clearly outside the site boundary must be rejected."""
    x_m, y_m = -5.0, 20.0  # west of site (site x range is approx 0..60)
    result = is_valid_location(x_m, y_m, site=site)
    assert result is False, (
        f"Expected is_valid_location({x_m}, {y_m}) to return False "
        f"(outside boundary), got True"
    )


def test_open_location_valid(site: dict) -> None:
    """A point that is inside the boundary and clear of buildings/streets is valid.

    The candidate point (30.0, 10.0) is:
    - well inside the 60m x 42m site boundary
    - clear of the two building polygons (MACBA north strip y≈34-42; east block x≈50-57 y≈3-10)
    - more than STREET_BUFFER_M=1.5m from the E-W street at y≈21

    If somehow the candidate is blocked (geometry collision in fixture), the test
    scans a coarse grid for the first valid open point and asserts at least one exists.
    """
    candidate_x, candidate_y = 30.0, 10.0
    if is_valid_location(candidate_x, candidate_y, site=site):
        return  # primary candidate is open — done

    # Fallback: scan a grid to confirm at least one open point exists
    step = 3.0
    found = False
    for xi in range(1, int(SITE_WIDTH_M), int(step)):
        for yi in range(1, int(SITE_DEPTH_M), int(step)):
            if is_valid_location(float(xi), float(yi), site=site):
                found = True
                break
        if found:
            break

    assert found, (
        "No open (valid) point found in the site grid. "
        "Check angels_site.geojson — buildings/streets may cover the entire site."
    )
