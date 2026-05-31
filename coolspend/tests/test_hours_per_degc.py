"""Closes PAPER limitation #6: the UTCI-hours→°C conversion is computed from the
in-repo Barcelona EPW, not a hand-derived REQUIRES_VERIFICATION constant.
"""
from __future__ import annotations

import pytest

from coolspend.cost_model import HOURS_PER_DEGC_REF, hours_per_degc


def test_hours_per_degc_returns_a_float_in_sane_band():
    v = hours_per_degc()
    assert isinstance(v, float)
    # EPW-derived (~47) OR the 200 fallback if ladybug/EPW absent — both sane.
    assert 20.0 <= v <= 250.0


def test_hours_per_degc_is_cached_and_stable():
    assert hours_per_degc() == hours_per_degc()


def test_fallback_constant_present_for_offline():
    # Literal must remain importable by name (calibration / back-compat contract).
    assert HOURS_PER_DEGC_REF == 200.0


def test_epw_value_supersedes_fallback_when_available():
    pytest.importorskip("ladybug_comfort")
    try:
        from nature_metrics import hours_per_degc_uniform_shift
    except Exception:  # noqa: BLE001
        pytest.skip("nature_metrics/EPW unavailable")
    r = hours_per_degc_uniform_shift(32.0)
    if not r.get("value"):
        pytest.skip("EPW not present")
    # When the EPW resolves, the live value is used (not the 200 literal) and
    # is materially smaller — the documented correction.
    assert hours_per_degc() == pytest.approx(float(r["value"]), abs=0.05)
    assert hours_per_degc() < HOURS_PER_DEGC_REF
