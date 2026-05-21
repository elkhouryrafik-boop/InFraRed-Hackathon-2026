"""
Tests for the single EPSG:4326 <-> plaza-local-metres CRS boundary (SPATIAL-03).

Verifies that:
1. latlon_to_local_m -> local_m_to_latlon round-trips within 1e-6 deg tolerance.
2. The EPSG:4326 site origin maps into the local-metre rectangle [0,SITE_WIDTH_M] x [0,SITE_DEPTH_M].

All tests run offline; no network required.
"""
from __future__ import annotations

import math

from coolspend.spatial_engine import (
    latlon_to_local_m,
    local_m_to_latlon,
    SITE_ORIGIN_LON,
    SITE_ORIGIN_LAT,
    SITE_WIDTH_M,
    SITE_DEPTH_M,
)

ROUND_TRIP_TOL_DEG = 1e-6


def test_roundtrip() -> None:
    """latlon_to_local_m then local_m_to_latlon recovers lon/lat within 1e-6 deg.

    Tested for:
    - The exact plaza centroid (SITE_ORIGIN_LON, SITE_ORIGIN_LAT)
    - An offset point 0.0005 deg east and 0.0003 deg north of the centroid
    """
    test_points = [
        (SITE_ORIGIN_LON, SITE_ORIGIN_LAT),
        (SITE_ORIGIN_LON + 0.0005, SITE_ORIGIN_LAT + 0.0003),
    ]
    for lon_in, lat_in in test_points:
        x_m, y_m = latlon_to_local_m(lon_in, lat_in)
        lon_out, lat_out = local_m_to_latlon(x_m, y_m)
        assert abs(lon_out - lon_in) < ROUND_TRIP_TOL_DEG, (
            f"Round-trip lon error {abs(lon_out - lon_in):.2e} deg exceeds tolerance "
            f"{ROUND_TRIP_TOL_DEG} for input lon={lon_in}"
        )
        assert abs(lat_out - lat_in) < ROUND_TRIP_TOL_DEG, (
            f"Round-trip lat error {abs(lat_out - lat_in):.2e} deg exceeds tolerance "
            f"{ROUND_TRIP_TOL_DEG} for input lat={lat_in}"
        )


def test_origin_maps_into_site() -> None:
    """The EPSG:4326 site origin maps to a local-metre point inside the site rectangle.

    The centroid (SITE_ORIGIN_LON, SITE_ORIGIN_LAT) should map to the centre of the
    [0, SITE_WIDTH_M] x [0, SITE_DEPTH_M] rectangle, i.e. (SITE_WIDTH_M/2, SITE_DEPTH_M/2).
    """
    x_m, y_m = latlon_to_local_m(SITE_ORIGIN_LON, SITE_ORIGIN_LAT)
    assert 0.0 <= x_m <= SITE_WIDTH_M, (
        f"Origin x_m={x_m:.4f} is outside [0, {SITE_WIDTH_M}]"
    )
    assert 0.0 <= y_m <= SITE_DEPTH_M, (
        f"Origin y_m={y_m:.4f} is outside [0, {SITE_DEPTH_M}]"
    )
    # The centroid anchor should map near the centre of the rectangle
    assert abs(x_m - SITE_WIDTH_M / 2) < 0.01, (
        f"Origin x_m={x_m:.4f} should be at the centre ({SITE_WIDTH_M/2})"
    )
    assert abs(y_m - SITE_DEPTH_M / 2) < 0.01, (
        f"Origin y_m={y_m:.4f} should be at the centre ({SITE_DEPTH_M/2})"
    )
