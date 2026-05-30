"""
EPW-backed weather source for the live Infrared UTCI/TCS path.

WHY THIS EXISTS
---------------
Infrared's weather services (``/v2/utils/weather`` — both
``get_weather_file_from_location`` and ``filter_weather_data``) returned
HTTP 500 server-side for every coordinate worldwide during the Buildathon
(2026-05-29 onward). Those calls are the ONLY hard blocker on a live UTCI run:
buildings fetch fine, and ground-materials already degrade gracefully.

``UtciModelRequest.from_weatherfile_payload`` does not need Infrared's weather
endpoint — it only needs a ``list[WeatherDataPoint]`` carrying the seven thermal
drivers (see ``_THERMAL_WEATHER_FIELDS`` in infrared_sdk). A standard EPW file
holds exactly those columns. So we parse a real, measured EPW and hand the SDK
the same payload it would have built from its own weather file — bypassing the
dead endpoint entirely.

NO-MOCK BAR
-----------
This is NOT a mock. The default file is the real Barcelona TMYx 2011-2025 typical
meteorological year (NCEI ISD / ERA5, distributed by climate.onebuilding.org),
the canonical building-science weather dataset for the city. Values flow into the
real Infrared solver unchanged. The only modeling choice is which hours define the
analysis window (see ``load_weather_data``), which is documented and matches the
TimePeriod the live path already uses.

EPW COLUMN MAP (0-based, EnergyPlus Weather format)
---------------------------------------------------
  1 month   2 day   3 hour
  6 dry-bulb °C            7 dew-point °C        8 relative humidity %
  9 atmospheric pressure Pa
 12 horizontal IR intensity W/m^2
 13 global horizontal radiation Wh/m^2
 14 direct normal radiation Wh/m^2
 15 diffuse horizontal radiation Wh/m^2
 20 wind direction °       21 wind speed m/s
The seven Infrared thermal drivers are columns 6, 8, 12, 13, 14, 15, 21.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid importing the SDK at module import time
    from infrared_sdk.models import TimePeriod, WeatherDataPoint

logger = logging.getLogger("coolspend.epw_weather")

# Default EPW: real Barcelona TMYx (climate.onebuilding.org). Override with
# INFRARED_EPW_PATH to point at any EnergyPlus-format .epw for another city.
_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EPW_PATH = _REPO_ROOT / "L1_INGEST_data" / "climate" / "Barcelona_TMYx_2011-2025.epw"

_EPW_HEADER_LINES = 8  # 8 metadata lines precede the 8760 hourly data rows

# EPW value index -> WeatherDataPoint camelCase field. Only fields the Infrared
# UTCI/TCS solver consumes (plus the cheap, always-present met fields).
_COL = {
    "dryBulbTemperature": 6,
    "dewPointTemperature": 7,
    "relativeHumidity": 8,
    "atmosphericStationPressure": 9,
    "horizontalInfraredRadiationIntensity": 12,
    "globalHorizontalRadiation": 13,
    "directNormalRadiation": 14,
    "diffuseHorizontalRadiation": 15,
    "windDirection": 20,
    "windSpeed": 21,
}


def _epw_path() -> Path:
    """Resolve the EPW path (env override wins). Raise if missing."""
    p = Path(os.environ.get("INFRARED_EPW_PATH", DEFAULT_EPW_PATH))
    if not p.is_file():
        raise FileNotFoundError(
            f"EPW weather file not found at {p}. Set INFRARED_EPW_PATH to a valid "
            "EnergyPlus .epw, or restore the default Barcelona TMYx file."
        )
    return p


def _in_window(month: int, day: int, hour: int, tp: "TimePeriod") -> bool:
    """True if (month, day, hour) falls in the analysis window.

    Window semantics match how Infrared's TimePeriod reads for an aggregated
    comfort map: a DIURNAL BAND (start_hour..end_hour inclusive) applied to every
    calendar day inside the [start date .. end date] range. For the project's
    standard period (July 1-31, hours 9-17) this yields the daytime hours of each
    July day — the sun-exposed comfort window the headline metric targets.
    """
    if not (tp.start_hour <= hour <= tp.end_hour):
        return False
    # Date range as (month, day) tuples — correct for same-year, single or
    # multi-month spans. The project uses a single month (start==end), but this
    # stays correct if the TimePeriod is widened later.
    return (tp.start_month, tp.start_day) <= (month, day) <= (tp.end_month, tp.end_day)


def load_weather_data(tp: "TimePeriod") -> "list[WeatherDataPoint]":
    """Parse the EPW and return the windowed ``list[WeatherDataPoint]``.

    Pure + offline: no network, no Infrared weather endpoint. The returned list is
    a drop-in replacement for ``client.weather.filter_weather_data(...)`` and feeds
    straight into ``UtciModelRequest/TcsModelRequest.from_weatherfile_payload``.

    Raises:
        FileNotFoundError: EPW file missing.
        RuntimeError: infrared_sdk not installed, or EPW yielded zero rows in window.
    """
    try:
        from infrared_sdk.models import WeatherDataPoint  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - SDK present in live runs
        raise RuntimeError(
            "infrared_sdk not installed — EPW weather payload needs WeatherDataPoint."
        ) from exc

    path = _epw_path()
    points: list[WeatherDataPoint] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for _ in range(_EPW_HEADER_LINES):
            next(fh, None)
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cols = line.split(",")
            if len(cols) <= _COL["windSpeed"]:
                continue  # malformed/short row — skip
            try:
                month = int(cols[1])
                day = int(cols[2])
                hour = int(cols[3])
            except ValueError:
                continue
            if not _in_window(month, day, hour, tp):
                continue
            try:
                fields = {name: float(cols[idx]) for name, idx in _COL.items()}
            except ValueError:
                continue  # a required column was non-numeric — skip the row
            points.append(WeatherDataPoint(**fields))

    if not points:
        raise RuntimeError(
            f"EPW {path.name} produced 0 weather points for the requested window "
            f"(months {tp.start_month}-{tp.end_month}, hours {tp.start_hour}-{tp.end_hour}). "
            "Check the TimePeriod and that the EPW covers the period."
        )

    logger.info(
        "EPW weather loaded: %d hourly points from %s (window months %d-%d, hours %d-%d)",
        len(points), path.name, tp.start_month, tp.end_month, tp.start_hour, tp.end_hour,
    )
    return points


def provenance_note() -> str:
    """One-line, honest provenance string for result disclaimers."""
    return (
        f"weather from real EPW ({_epw_path().name}, measured TMY; "
        "Infrared weather endpoint bypassed - server 500)"
    )
