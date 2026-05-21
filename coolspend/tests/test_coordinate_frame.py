"""
Tests for the UTM-31N (EPSG:32631) CRS boundary in coolspend.spatial_engine (SPATIAL-03).

Task 1 (D-06): Verifies UTM-31N projection via pyproj — citywide Barcelona accuracy,
per-site origin from polygon UTM bbox SW corner, [0,width]x[0,depth] local frame.

Task 2 (D-07): Verifies fail-closed round-trip guard (assert_crs_roundtrip + CRSConsistencyError)
fires before every live SDK call and aborts on coordinate mismatch (>=1 m error).

All tests run offline; no network required (pyproj uses bundled PROJ data).
"""
from __future__ import annotations

import math
import pytest

from coolspend.spatial_engine import (
    latlon_to_local_m,
    local_m_to_latlon,
    set_site_origin_from_polygon,
    SITE_ORIGIN_LON,
    SITE_ORIGIN_LAT,
    SITE_WIDTH_M,
    SITE_DEPTH_M,
    _TO_UTM,
    CRSConsistencyError,
    assert_crs_roundtrip,
)

# ── Task 1 Tests (UTM-31N CRS boundary, D-06) ────────────────────────────────

ROUND_TRIP_TOL_M = 1.0  # < 1 m in UTM metres (D-07 criterion)


def _utm_distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Euclidean UTM distance in metres between two WGS84 points."""
    e1, n1 = _TO_UTM.transform(lon1, lat1)
    e2, n2 = _TO_UTM.transform(lon2, lat2)
    return math.hypot(e1 - e2, n1 - n2)


def test_roundtrip_plaza_centroid() -> None:
    """UTM round-trip at plaza centroid recovers lon/lat within <1 m."""
    lon_in, lat_in = SITE_ORIGIN_LON, SITE_ORIGIN_LAT
    x_m, y_m = latlon_to_local_m(lon_in, lat_in)
    lon_out, lat_out = local_m_to_latlon(x_m, y_m)
    err_m = _utm_distance_m(lon_in, lat_in, lon_out, lat_out)
    assert err_m < ROUND_TRIP_TOL_M, (
        f"Round-trip error at plaza centroid: {err_m:.4f} m >= {ROUND_TRIP_TOL_M} m"
    )


def test_roundtrip_far_barcelona_point() -> None:
    """UTM round-trip at a far Barcelona point (Sagrada area) recovers lon/lat <1 m.

    This test FAILS with the old equirectangular (single-anchor) code because it is
    anchored at the plaza centroid and breaks for points >200 m away.
    With UTM-31N it must pass citywide.
    """
    # Sagrada Família area (~4.4 km from plaza)
    lon_in, lat_in = 2.1744, 41.4036
    x_m, y_m = latlon_to_local_m(lon_in, lat_in)
    lon_out, lat_out = local_m_to_latlon(x_m, y_m)
    err_m = _utm_distance_m(lon_in, lat_in, lon_out, lat_out)
    assert err_m < ROUND_TRIP_TOL_M, (
        f"Round-trip error at Sagrada area ({lon_in},{lat_in}): {err_m:.4f} m >= {ROUND_TRIP_TOL_M} m"
    )


def test_roundtrip_second_barcelona_site() -> None:
    """UTM round-trip at another Barcelona location (Eixample) is <1 m.

    Proves the single-anchor limitation is gone — any Barcelona polygon can be
    used as the site, not just the fixed plaza centroid.
    """
    # Eixample district (~1.5 km NE of plaza)
    lon_in, lat_in = 2.1574, 41.3914
    x_m, y_m = latlon_to_local_m(lon_in, lat_in)
    lon_out, lat_out = local_m_to_latlon(x_m, y_m)
    err_m = _utm_distance_m(lon_in, lat_in, lon_out, lat_out)
    assert err_m < ROUND_TRIP_TOL_M, (
        f"Round-trip error at Eixample ({lon_in},{lat_in}): {err_m:.4f} m >= {ROUND_TRIP_TOL_M} m"
    )


def test_per_site_origin_sw_corner_maps_to_zero() -> None:
    """After set_site_origin_from_polygon, the polygon's SW UTM corner maps to (0, 0).

    The SW corner is (min_easting, min_northing) of the polygon ring in UTM-31N.
    """
    # A small rectangle near Sagrada area (different from default plaza)
    ring = [
        (2.1740, 41.4030),
        (2.1750, 41.4030),
        (2.1750, 41.4040),
        (2.1740, 41.4040),
        (2.1740, 41.4030),
    ]
    width_m, depth_m = set_site_origin_from_polygon(ring)

    # The SW corner of this polygon in UTM:
    eastings = [_TO_UTM.transform(lon, lat)[0] for lon, lat in ring]
    northings = [_TO_UTM.transform(lon, lat)[1] for lon, lat in ring]
    sw_lon_approx, sw_lat_approx = min(lon for lon, lat in ring), min(lat for lon, lat in ring)

    # Convert the SW UTM corner to lon/lat for the round-trip check
    sw_e, sw_n = min(eastings), min(northings)
    sw_lon, sw_lat = _TO_UTM.__class__.from_crs("EPSG:32631", "EPSG:4326", always_xy=True).transform(sw_e, sw_n)

    x_m, y_m = latlon_to_local_m(sw_lon, sw_lat)
    assert abs(x_m) < 1.0, f"SW corner x_m={x_m:.4f} should be 0 (±1 m tolerance)"
    assert abs(y_m) < 1.0, f"SW corner y_m={y_m:.4f} should be 0 (±1 m tolerance)"

    # Width and depth should be positive
    assert width_m > 0, "set_site_origin_from_polygon should return positive width"
    assert depth_m > 0, "set_site_origin_from_polygon should return positive depth"


def test_site_width_depth_follow_polygon() -> None:
    """SITE_WIDTH_M and SITE_DEPTH_M are updated to match the polygon UTM extents."""
    # Wider rectangle
    ring = [
        (2.1660, 41.3820),
        (2.1700, 41.3820),   # ~300 m wide in lon
        (2.1700, 41.3830),
        (2.1660, 41.3830),
        (2.1660, 41.3820),
    ]
    width_m, depth_m = set_site_origin_from_polygon(ring)

    # Width should be ~300 m (0.004 deg lon at lat 41.38)
    assert 200.0 < width_m < 500.0, f"Unexpected width_m={width_m:.1f} for 0.004 deg lon span"
    assert 50.0 < depth_m < 200.0, f"Unexpected depth_m={depth_m:.1f} for 0.001 deg lat span"

    # SITE_WIDTH_M and SITE_DEPTH_M module constants should be updated
    from coolspend import spatial_engine
    assert abs(spatial_engine.SITE_WIDTH_M - width_m) < 0.01
    assert abs(spatial_engine.SITE_DEPTH_M - depth_m) < 0.01


def test_load_site_still_returns_valid_shapely_geoms() -> None:
    """load_site() of angels_site.geojson returns shapely geoms with positive area.

    Regression test: the UTM migration must not break the existing site loader.
    """
    from coolspend.spatial_engine import load_site
    site = load_site()

    assert site["boundary"].is_valid, "site boundary polygon is not valid"
    assert site["boundary"].area > 0, "site boundary area is zero or negative"
    assert len(site["buildings"]) >= 2, "expected at least 2 building polygons"
    for bld in site["buildings"]:
        assert bld.area > 0, f"building polygon area={bld.area:.4f} is not positive"
    assert len(site["streets"]) >= 1, "expected at least 1 street linestring"


def test_epsg_32631_present() -> None:
    """EPSG:32631 string literal is present in spatial_engine source (acceptance criterion)."""
    import inspect
    from coolspend import spatial_engine
    src = inspect.getsource(spatial_engine)
    assert "EPSG:32631" in src, "EPSG:32631 not found in spatial_engine — UTM migration incomplete"


def test_always_xy_true_present() -> None:
    """always_xy=True is used in the Transformer construction (acceptance criterion)."""
    import inspect
    from coolspend import spatial_engine
    src = inspect.getsource(spatial_engine)
    assert "always_xy=True" in src, "always_xy=True not found in spatial_engine"


def test_no_equirectangular_code() -> None:
    """No equirectangular projection code remains in spatial_engine (acceptance criterion)."""
    import inspect
    from coolspend import spatial_engine
    src = inspect.getsource(spatial_engine)
    assert "equirectangular" not in src, (
        "equirectangular code still present in spatial_engine — migration incomplete"
    )


# ── Task 2 Tests (Fail-closed round-trip guard, D-07) ────────────────────────

def test_assert_crs_roundtrip_passes_valid_ring() -> None:
    """assert_crs_roundtrip returns max error in metres for a valid Barcelona ring."""
    ring = [
        (2.1666408, 41.3824114),
        (2.1673592, 41.3824114),
        (2.1673592, 41.3827886),
        (2.1666408, 41.3827886),
        (2.1666408, 41.3824114),
    ]
    max_err = assert_crs_roundtrip(ring)
    assert isinstance(max_err, float), "assert_crs_roundtrip should return a float"
    assert max_err < 1.0, f"Valid Barcelona ring round-trip error {max_err:.4f} m >= 1.0 m"


def test_guard_fails_closed_on_bad_ring(monkeypatch) -> None:
    """assert_crs_roundtrip raises CRSConsistencyError when local_m_to_latlon returns wrong coords.

    Monkeypatches local_m_to_latlon to return a point ~10 km away from the real
    inverse, simulating a broken/drifted CRS boundary. The guard must detect this
    mismatch (>> 1 m in UTM metres) and raise CRSConsistencyError.
    """
    import coolspend.spatial_engine as se

    # Monkeypatch local_m_to_latlon to return a point 10 km away (simulates CRS drift)
    def _bad_inverse(x_m: float, y_m: float):
        # Return a point ~0.1 deg (~10 km) away — well above 1 m threshold
        return 2.1666 + 0.1, 41.3824 + 0.1

    monkeypatch.setattr(se, "local_m_to_latlon", _bad_inverse)

    ring = [(2.1666, 41.3824), (2.1674, 41.3824), (2.1674, 41.3828), (2.1666, 41.3828)]
    with pytest.raises(CRSConsistencyError) as exc_info:
        assert_crs_roundtrip(ring)
    # Error message should mention metres and D-07
    assert "m" in str(exc_info.value).lower() or "D-07" in str(exc_info.value)


def test_crs_consistency_error_message_names_worst_error(monkeypatch) -> None:
    """CRSConsistencyError message names the worst error in metres."""
    import re
    import coolspend.spatial_engine as se

    def _bad_inverse(x_m: float, y_m: float):
        return 2.1666 + 0.05, 41.3824 + 0.05  # ~7 km off

    monkeypatch.setattr(se, "local_m_to_latlon", _bad_inverse)

    bad_ring = [(2.1666, 41.3824), (2.1670, 41.3826)]
    with pytest.raises(CRSConsistencyError) as exc_info:
        assert_crs_roundtrip(bad_ring)
    msg = str(exc_info.value)
    # Message must contain a numeric error value (e.g. "7432.123 m")
    assert re.search(r"\d+\.\d+", msg), f"Error message should contain numeric error: {msg!r}"


def test_guard_blocks_sdk_call_on_bad_ring(monkeypatch) -> None:
    """_live_utci aborts — SDK unreachable past a guard failure.

    Monkeypatches InfraredClient so it raises AssertionError if reached.
    Monkeypatches local_m_to_latlon to return wrong coordinates so CRS guard triggers.
    The test asserts CRSConsistencyError is raised, not the SDK's AssertionError.
    """
    import sys
    from coolspend import spatial_engine as se
    from coolspend import sdk_client

    # Ensure live backend
    monkeypatch.setenv("INFRARED_BACKEND", "live")
    monkeypatch.setenv("INFRARED_API_KEY", "test-key-not-real")

    # Patch local_m_to_latlon to return a point far off so guard triggers
    def _bad_inverse(x_m: float, y_m: float):
        return 2.1666 + 0.1, 41.3824 + 0.1  # ~10 km away

    monkeypatch.setattr(se, "local_m_to_latlon", _bad_inverse)

    class _FakeSDK:
        def __enter__(self):
            raise AssertionError("InfraredClient was reached — guard did NOT abort the call!")
        def __exit__(self, *a):
            pass

    # geometry with a polygon_lonlat — the guard operates on this ring
    bad_geom = {
        "polygon_lonlat": [
            [2.1666, 41.3824],
            [2.1674, 41.3824],
            [2.1674, 41.3828],
            [2.1666, 41.3828],
            [2.1666, 41.3824],
        ]
    }

    # Monkeypatch InfraredClient so it fails if reached
    fake_infrared_sdk = type(sys)("infrared_sdk")
    fake_infrared_sdk.InfraredClient = _FakeSDK

    class _FakeAnalysesName:
        utci = "utci"
    fake_infrared_sdk.analyses = type(sys)("analyses")
    fake_infrared_sdk.analyses.types = type(sys)("types")
    fake_infrared_sdk.analyses.types.AnalysesName = _FakeAnalysesName

    monkeypatch.setitem(sys.modules, "infrared_sdk", fake_infrared_sdk)
    monkeypatch.setitem(sys.modules, "infrared_sdk.analyses", fake_infrared_sdk.analyses)
    monkeypatch.setitem(sys.modules, "infrared_sdk.analyses.types", fake_infrared_sdk.analyses.types)

    with pytest.raises(CRSConsistencyError):
        sdk_client._live_utci("utci_baseline", bad_geom)


def test_assert_crs_roundtrip_symbol_present() -> None:
    """assert_crs_roundtrip and CRSConsistencyError are importable from spatial_engine."""
    from coolspend.spatial_engine import assert_crs_roundtrip, CRSConsistencyError
    assert callable(assert_crs_roundtrip)
    assert issubclass(CRSConsistencyError, RuntimeError)
