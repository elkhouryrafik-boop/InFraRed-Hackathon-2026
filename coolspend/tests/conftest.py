"""Shared pytest fixtures for the coolspend test suite.

Provides deterministic test isolation for the per-site UTM CRS origin state
introduced in Phase 5 (05-01). `spatial_engine` stores the active site's origin
and extents (SITE_WIDTH_M / SITE_DEPTH_M / _SITE_ORIGIN_E/N) as module globals.
Tests that call set_site_origin_from_polygon (or load_site with a non-default
polygon) mutate that shared state; without a reset, the mutated extents leak into
later tests and silently corrupt the optimizer/surrogate geometry frame
(observed: order-dependent failures in test_optimizer / test_surrogate).

The autouse fixture below resets that state before every test, so each test starts
from the same clean slate — the first coordinate conversion lazily re-loads the
default angels_site.geojson, matching single-test (isolated) behavior.
"""
from __future__ import annotations

import pytest

from coolspend import spatial_engine


@pytest.fixture(autouse=True)
def _reset_site_origin():
    """Reset spatial_engine's per-site UTM origin state before (and after) each test."""
    spatial_engine.reset_site_origin()
    yield
    spatial_engine.reset_site_origin()
