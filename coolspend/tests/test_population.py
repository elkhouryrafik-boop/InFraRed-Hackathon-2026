"""Offline tests for coolspend/population.py.

These run against the on-disk cache populated on a prior fetch
(coolspend/cache/population/). If the cache is absent AND the network is
unavailable, the data-dependent tests skip — so CI without network still passes
(the module's own graceful-degradation contract is still asserted).
"""
from __future__ import annotations

import pytest

from coolspend import population as P


def _data_available() -> bool:
    """True if both population and barri geometry resolve (from cache or network)."""
    try:
        return P.barri_population() is not None and P._barri_area_m2() is not None
    except Exception:  # noqa: BLE001
        return False


_HAVE_DATA = _data_available()
_needs_data = pytest.mark.skipif(
    not _HAVE_DATA,
    reason="Barcelona population/barri data unavailable (no cache + no network).",
)

# A known dense central Barcelona point — Plaça de Catalunya.
_CENTRAL_LON, _CENTRAL_LAT = 2.1700, 41.3870


# ── Graceful-degradation contract (always runs, no data needed) ──────────────────

def test_people_served_returns_dict_shape():
    """Result is always a dict with the documented keys, even when data is missing."""
    r = P.people_served(_CENTRAL_LON, _CENTRAL_LAT, 300.0)
    for key in ("people_served", "density_basis", "catchment_m", "method", "source"):
        assert key in r, f"missing key {key!r}"
    assert r["catchment_m"] == 300.0
    # people_served is either a non-negative int or None (never fabricated/negative).
    assert r["people_served"] is None or (
        isinstance(r["people_served"], int) and r["people_served"] >= 0
    )


def test_unavailable_is_flagged_not_fabricated(monkeypatch):
    """When both datasets are unavailable, people_served is None and method says so."""
    monkeypatch.setattr(P, "barri_density_per_m2", lambda: None)
    monkeypatch.setattr(P, "_load_population_payload", lambda: None)
    r = P.people_served(_CENTRAL_LON, _CENTRAL_LAT, 300.0)
    assert r["people_served"] is None
    assert r["method"] == "unavailable"
    assert r["source"] == "unavailable"
    assert r["barris"] == []


# ── Data-backed tests (skip if no cache + no network) ────────────────────────────

@_needs_data
def test_barri_population_total_sane():
    """73 barris, total registered residents in the ~1.6-1.75 M Barcelona range."""
    pop = P.barri_population()
    assert pop is not None
    assert len(pop) == 73
    total = sum(pop.values())
    assert 1_500_000 < total < 1_800_000, f"Barcelona total {total} out of expected range"
    # Codes are zero-padded "01".."73".
    assert "01" in pop and "73" in pop
    # Every barri has a positive registered population.
    assert all(v > 0 for v in pop.values())


@_needs_data
def test_density_is_persons_per_m2_realistic():
    """Density (persons/m²) → persons/ha should be realistic for Barcelona barris."""
    dens = P.barri_density_per_m2()
    assert dens is not None
    assert len(dens) == 73
    per_ha = [v * 1e4 for v in dens.values()]
    # Dense Eixample/Gràcia barris exceed 400 persons/ha; forest barris are tiny.
    assert max(per_ha) > 300
    assert min(per_ha) >= 0
    # Median Barcelona barri density is on the order of a few hundred persons/ha.
    per_ha.sort()
    median = per_ha[len(per_ha) // 2]
    assert 50 < median < 800, f"median density {median:.0f}/ha implausible"


@_needs_data
def test_people_served_positive_int_central():
    """A dense central point serves a positive number of residents within 300 m."""
    r = P.people_served(_CENTRAL_LON, _CENTRAL_LAT, 300.0)
    assert isinstance(r["people_served"], int)
    assert r["people_served"] > 0
    assert r["method"] in (
        "area_weighted_intersection",
        "point_density_fallback",
        "city_mean_density_fallback",
    )
    # Plausible upper bound: 28.3 ha at even Barcelona's densest (~600/ha) < 25k.
    assert r["people_served"] < 25_000


@_needs_data
def test_people_served_scales_with_catchment():
    """A larger catchment serves more residents (monotonic in radius)."""
    small = P.people_served(_CENTRAL_LON, _CENTRAL_LAT, 150.0)["people_served"]
    big = P.people_served(_CENTRAL_LON, _CENTRAL_LAT, 600.0)["people_served"]
    assert small is not None and big is not None
    assert big > small
    # Roughly area-scaling: 600 m circle is 16× the 150 m circle's area; expect a
    # substantial (≥ 4×) increase even allowing for density gradients/edge effects.
    assert big >= 4 * small


@_needs_data
def test_point_outside_city_serves_zero():
    """A point in the sea (no barri intersected) serves 0 residents, not an error."""
    r = P.people_served(2.30, 41.30, 300.0)  # offshore SE of the city
    assert r["people_served"] == 0
    assert r["barris"] == []


@_needs_data
def test_served_for_centroid_matches_people_served():
    """The citywide helper returns the same estimate as people_served."""
    direct = P.people_served(_CENTRAL_LON, _CENTRAL_LAT, 300.0)["people_served"]
    via = P.served_for_centroid((_CENTRAL_LON, _CENTRAL_LAT), 300.0)["people_served"]
    assert direct == via
