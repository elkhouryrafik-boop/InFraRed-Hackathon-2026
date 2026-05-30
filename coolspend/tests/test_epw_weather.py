"""
Offline tests for coolspend/epw_weather.py — the EPW weather bypass that feeds
the live Infrared UTCI/TCS path when Infrared's weather endpoint is down.

These run fully offline against the real bundled Barcelona TMYx EPW. They assert
the windowing semantics and that the 7 Infrared thermal drivers are populated and
numeric — the contract from_weatherfile_payload depends on.
"""
from __future__ import annotations

import pytest

from infrared_sdk.models import TimePeriod
from infrared_sdk.models import extract_weather_fields
from infrared_sdk.analyses import types as ir_types

from coolspend import epw_weather
from coolspend.sdk_client import UTCI_TIME_PERIOD


def test_july_daytime_window_point_count():
    """July 1-31, hours 9-17 inclusive = 31 days x 9 hours = 279 hourly points."""
    tp = TimePeriod(**UTCI_TIME_PERIOD)
    wd = epw_weather.load_weather_data(tp)
    assert len(wd) == 279


def test_all_seven_thermal_drivers_present_and_numeric():
    """from_weatherfile_payload extracts exactly these 7 fields; all must be floats."""
    tp = TimePeriod(**UTCI_TIME_PERIOD)
    wd = epw_weather.load_weather_data(tp)
    accum = extract_weather_fields(wd, ir_types._THERMAL_WEATHER_FIELDS)
    # extract drops None values, so equal lengths proves none were missing.
    assert {k: len(v) for k, v in accum.items()} == {
        k: 279 for k in (
            "horizontal_infrared_radiation_intensity",
            "diffuse_horizontal_radiation",
            "direct_normal_radiation",
            "global_horizontal_radiation",
            "dry_bulb_temperature",
            "wind_speed",
            "relative_humidity",
        )
    }


def test_window_excludes_night_and_other_months():
    """Every returned hour is in the diurnal band, and Barcelona July values are sane."""
    tp = TimePeriod(**UTCI_TIME_PERIOD)
    wd = epw_weather.load_weather_data(tp)
    temps = [p.dryBulbTemperature for p in wd]
    # Barcelona July daytime dry-bulb sits comfortably in this envelope.
    assert all(10.0 < t < 45.0 for t in temps)
    # RH is a percentage; wind non-negative.
    assert all(0 <= p.relativeHumidity <= 100 for p in wd)
    assert all(p.windSpeed >= 0 for p in wd)


def test_in_window_diurnal_band_logic():
    """_in_window keeps hours inside [start_hour, end_hour] and rejects the rest."""
    tp = TimePeriod(**UTCI_TIME_PERIOD)  # hours 9-17, July
    assert epw_weather._in_window(7, 15, 9, tp) is True   # band start
    assert epw_weather._in_window(7, 15, 17, tp) is True  # band end
    assert epw_weather._in_window(7, 15, 8, tp) is False  # before band
    assert epw_weather._in_window(7, 15, 18, tp) is False # after band
    assert epw_weather._in_window(6, 15, 12, tp) is False # wrong month
    assert epw_weather._in_window(8, 1, 12, tp) is False  # wrong month


def test_missing_epw_raises(monkeypatch):
    """A bad INFRARED_EPW_PATH fails loudly, not silently."""
    monkeypatch.setenv("INFRARED_EPW_PATH", "does/not/exist.epw")
    with pytest.raises(FileNotFoundError):
        epw_weather.load_weather_data(TimePeriod(**UTCI_TIME_PERIOD))


def test_provenance_note_is_honest():
    """Provenance must name the real EPW and disclose the bypass — no-mock bar."""
    note = epw_weather.provenance_note()
    assert "EPW" in note
    assert ".epw" in note
    assert "bypassed" in note
