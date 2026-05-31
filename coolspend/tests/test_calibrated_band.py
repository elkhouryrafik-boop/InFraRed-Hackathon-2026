"""Closes PAPER limitation #4 (band): the surrogate uncertainty is the empirical
±band from the live calibration study, not the assumed ±4 °C.
"""
from __future__ import annotations

import json
from pathlib import Path

from coolspend.cost_model import calibrated_band_c, PRE_CALIBRATION_BAND_C

_SUMMARY = Path(__file__).resolve().parent.parent / "data" / "calibration_summary.json"


def test_calibration_summary_committed_and_sane():
    assert _SUMMARY.exists(), "calibration_summary.json must be committed"
    d = json.loads(_SUMMARY.read_text(encoding="utf-8"))
    assert d["backend"] == "live"
    assert 0 < d["band_c_95"] < 4.0  # tighter than the old assumed ±4
    assert d["rmse_c"] > 0


def test_calibrated_band_is_used_and_tighter_than_assumed():
    band = calibrated_band_c()
    assert band is not None
    assert band < PRE_CALIBRATION_BAND_C  # empirical band is tighter than assumed ±4


def test_band_source_reflects_empirical_calibration():
    from coolspend.cost_model import cost_per_utci_degree

    r = cost_per_utci_degree(
        {"trees": [{"active": True, "x_m": 10, "y_m": 10}], "delta_utci_c": 1.0,
         "cost_eur": 100000},
    )
    assert "empirical calibration" in r["band_source"]
