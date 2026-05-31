"""
coolspend/sdk_client.py — Infrared SDK boundary for CoolSpend tree-budget optimizer.

Project: CoolSpend — urban heat-mitigation budget decision tool (infrared.city Buildathon).
Site context: Plaça dels Àngels, Barcelona (demo default).

Mock / real status:
  - INFRARED_BACKEND=mock (default): returns a deterministic SCALAR UTCI delta;
    NOT MEASURED DATA — see MOCKS.md and disclaimer field on every UTCIResult.
  - INFRARED_BACKEND=cached: reads from coolspend/cache/infrared/{metric}_{hash}.json;
    raises FileNotFoundError on cache miss (never falls through to mock — CONCERNS 6.1).
  - INFRARED_BACKEND=live: raises EnvironmentError if INFRARED_API_KEY unset; calls the
    real infrared_sdk (InfraredClient.run_area_and_wait) and caches the result to disk
    so a subsequent INFRARED_BACKEND=cached run replays it offline. Requires infrared-sdk
    package installed (pip install infrared-sdk) — imported LAZILY inside _live_utci only
    so the module is importable offline without the SDK.

Mock base values ported from CONCERNS.md 1.3 (via infrared_client_v2.py line 219-220):
  baseline open UTCI  = 41.0 °C  (Plaça dels Àngels open plaza, summer noon)
  under-canopy UTCI   = 30.5 °C  (under textile canopy, same conditions)

SimBudget guard (SDK-03): caps live Infrared UTCI calls so INFRARED_BACKEND=live is
unreachable from inside the Phase 2 NSGA-II _evaluate() hot path.

Public API:
  get_baseline_utci(geometry) -> UTCIResult
  get_intervention_utci(geometry) -> UTCIResult
  SimBudget
  UTCIResult

Do NOT import infrared_sdk at module level; use the lazy import inside _live_utci only.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Literal

# ── Logging ───────────────────────────────────────────────────────────────────

logger = logging.getLogger("coolspend.sdk_client")

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent
CACHE_DIR = BASE / "cache" / "infrared"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Backend selection ─────────────────────────────────────────────────────────

Backend = Literal["mock", "cached", "live"]

# MOCK: base UTCI values — synthetic scalar, NOT from live Infrared API.
# Source: CONCERNS.md 1.3 base values (ported from infrared_client_v2.py:219-220).
# MOCKS.md entry: "mock UTCI delta" row.
UTCI_BASELINE_OPEN_C = 41.0    # °C — open plaza UTCI, summer design day
UTCI_UNDER_CANOPY_C = 30.5     # °C — under-canopy UTCI, same conditions
MOCK_DISCLAIMER = "NOT MEASURED DATA — synthetic field for UI integration only."


def _backend() -> Backend:
    """Read backend mode from environment at dispatch time, never at import."""
    return os.environ.get("INFRARED_BACKEND", "mock")  # type: ignore[return-value]


def _geometry_hash(geometry: dict) -> str:
    """Deterministic 16-char hex hash of geometry dict — keys the disk cache.

    Key order is canonicalised via sort_keys so identical dicts with different
    insertion order produce the same hash.
    """
    blob = json.dumps(geometry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ── Data types ────────────────────────────────────────────────────────────────


@dataclass
class UTCIResult:
    """Single UTCI scalar result from the mock or live Infrared backend.

    utci_c: UTCI felt-temperature in degrees Celsius at 1.1m pedestrian height.
    metric: stable metric ID, e.g. "utci_at_1.1m".
    backend: which backend produced this value ("mock", "cached", "live").
    geometry_hash: first 16 chars of SHA-256 of the input geometry JSON.
    disclaimer: honesty string; always "NOT MEASURED DATA ..." for mock/cached.
    source: human-readable provenance note.
    """

    utci_c: float
    metric: str
    backend: str
    geometry_hash: str
    disclaimer: str
    source: str
    # Spatial value primitives (live grid only; None for mock/scalar backends).
    # heat_stress_area_m2: ground area (m², 1 m²/cell) above the moderate-heat-stress
    #   threshold (UTCI_HEAT_STRESS_C) — conservative, official-boundary metric.
    # merged_grid: the full UTCI grid (rounded, NaN outside polygon) so a caller can
    #   diff baseline vs intervention CELL-WISE for the cooled-footprint headline
    #   (cooled_footprint_m2). Kept on the result + cache so cached replay reproduces
    #   the footprint offline. Not propagated into the public result dict.
    heat_stress_area_m2: float | None = None
    grid_cells_total: int | None = None  # non-NaN cells in the merged grid
    merged_grid: list | None = None      # 2D list of UTCI °C (None outside polygon)
    # Peak felt-temperature: the 90th-percentile cell (sun-exposed hotspots where
    # shade matters most), NOT the site mean which is diluted by already-shaded cells.
    # None for mock/scalar backends. See AUDIT_REPORT.md "UTCI accuracy investigation".
    utci_peak_c: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dict."""
        return asdict(self)


# ── SimBudget guard (SDK-03) ──────────────────────────────────────────────────


class SimBudget:
    """Guard that caps the number of live Infrared UTCI calls per optimizer run.

    Purpose: INFRARED_BACKEND=live must be unreachable from inside the Phase 2
    NSGA-II _evaluate() hot path (which runs ~10,000 chromosomes per run). Live
    SDK calls are only permitted in an explicit validate_top3_with_infrared()
    function that runs AFTER the optimizer selects its Top-3 candidates. This
    guard enforces that contract at runtime and logs each live call for audit.

    Usage:
        budget = SimBudget(max_live_calls=3)
        budget.record("baseline BCN-001")   # logs + increments counter
        budget.record("intervention C1")    # logs + increments counter
        budget.record("intervention C2")    # logs + increments counter
        budget.record("overflow")           # raises RuntimeError
    """

    def __init__(self, max_live_calls: int = 3) -> None:
        self.max_live_calls = max_live_calls
        self.calls: int = 0
        self.log: list[str] = []

    def record(self, label: str) -> None:
        """Record one UTCI validation call against the budget. Raises RuntimeError past cap.

        label: short description of the call (e.g. geometry ID + variant).
        Logs at INFO level via coolspend.sdk_client logger. Wording is backend-neutral
        ("UTCI sim call") on purpose — this counter fires for mock/cached/live alike,
        so it must not claim a call was "live" when the backend is mock.
        """
        self.calls += 1
        entry = f"UTCI sim call #{self.calls}: {label}"
        self.log.append(entry)
        logger.info(entry)
        if self.calls > self.max_live_calls:
            raise RuntimeError(
                f"SimBudget exceeded: {self.calls} live UTCI calls > cap {self.max_live_calls}"
            )


# ── Mock UTCI model ───────────────────────────────────────────────────────────


def _mock_baseline_utci(geometry: dict) -> UTCIResult:
    """Return mock baseline UTCI for an open (un-shaded) geometry.

    # MOCK: deterministic scalar, NOT from live Infrared API. See MOCKS.md.
    Base value = 41.0 °C (open plaza, summer design day — CONCERNS.md 1.3).
    """
    ghash = _geometry_hash(geometry)
    return UTCIResult(
        utci_c=round(UTCI_BASELINE_OPEN_C, 2),
        metric="utci_at_1.1m",
        backend="mock",
        geometry_hash=ghash,
        disclaimer=MOCK_DISCLAIMER,
        source="coolspend mock scalar UTCI (CONCERNS.md 1.3 base values)",
    )


def _mock_intervention_utci(geometry: dict) -> UTCIResult:
    """Return mock post-intervention UTCI for a geometry with canopy coverage.

    # MOCK: deterministic scalar, NOT from live Infrared API. See MOCKS.md.
    If geometry has width_m > 0, a cooling delta is applied proportional to
    coverage_fraction (default 0.3). Formula:
        utci_c = 41.0 - (41.0 - 30.5) * min(coverage_fraction, 1.0)
    For zero-width geometry returns baseline (41.0 °C) — no canopy, no cooling.
    """
    ghash = _geometry_hash(geometry)
    width_m: float = geometry.get("width_m", 0.0)

    if width_m > 0:
        coverage_fraction: float = float(geometry.get("coverage_fraction", 0.3))
        utci_c = UTCI_BASELINE_OPEN_C - (
            (UTCI_BASELINE_OPEN_C - UTCI_UNDER_CANOPY_C) * min(coverage_fraction, 1.0)
        )
    else:
        utci_c = UTCI_BASELINE_OPEN_C

    return UTCIResult(
        utci_c=round(utci_c, 2),
        metric="utci_at_1.1m",
        backend="mock",
        geometry_hash=ghash,
        disclaimer=MOCK_DISCLAIMER,
        source="coolspend mock scalar UTCI (CONCERNS.md 1.3 base values)",
    )


# ── Live Infrared backend ─────────────────────────────────────────────────────

# Single-month July daytime window for the UTCI run. UTCI/TCS require a single-month
# TimePeriod (server sun_vectors generator does not honour multi-month windows —
# see skill 03-time-period.md). July 09:00–17:00 = Barcelona peak-heat daytime.
#
# WINDOW VERIFIED (2026-05-29): same-site A/B across 09-17, 13-16, and 14-15 windows
# gave UTCI mean 28.7 / 28.0 / 28.0 °C and max 31.1 / 30.4 / 30.4 °C respectively.
# Narrowing to the "peak hour" does NOT raise the felt temperature — it slightly
# lowers it — so the all-day window is kept. The moderate ~28-31 °C values are REAL
# and correct for coastal Barcelona: TMYx July air temp is only ~26.6 °C and the
# 4.3 m/s sea breeze lowers UTCI. Solar/MRT IS applied (UTCI sits 2-4 °C above air
# temp; sunniest cell ~31 vs shaded ~24). Not a bug — Barcelona just runs milder
# than inland Spain. See AUDIT_REPORT.md "UTCI accuracy investigation".
UTCI_TIME_PERIOD: dict[str, int] = {
    "start_month": 7, "start_day": 1, "start_hour": 9,
    "end_month": 7, "end_day": 31, "end_hour": 17,
}

# Valid Infrared ground-material names (byo-inputs.md). The fetch may return
# extra keys (e.g. 'building') that are NOT materials; only these reach the run.
_VALID_GROUND_MATERIALS: frozenset[str] = frozenset(
    {"asphalt", "concrete", "soil", "vegetation", "water"}
)

# Heat-stress threshold for the live AREA metric, on the official UTCI assessment
# scale (>26 = moderate, >32 = strong heat stress). We use 26 °C (moderate) here
# because the Infrared UTCI map is AGGREGATED over the July 09–17 window — a
# window-mean surface that compresses instantaneous peaks (empirically maxes
# ~31 °C on a sun-exposed Barcelona block), so a >32 area is ~0 and useless as a
# metric. heat_stress_area_m2 therefore = ground area in AT-LEAST-MODERATE heat
# stress on the aggregate map. HONEST DIVERGENCE: the surrogate objective is
# instantaneous hours>32 °C (EPW, nature_metrics.utci_hours_above); the truly
# dimensionally-matched live validation is the TCS (thermal-comfort-statistics)
# per-cell hour count — documented as the rigorous upgrade (MOCKS.md).
UTCI_HEAT_STRESS_C: float = 26.0

# Minimum per-cell UTCI drop (°C) counted as "meaningfully cooled" for the
# cooled-footprint headline metric. 0.5 °C is a perceptible comfort change and
# is well above the model's numerical noise. Threshold-independent of absolute
# UTCI, so it does NOT saturate on already-hot sites (unlike heat_stress_area).
COOLED_MIN_DROP_C: float = 0.5


def cooled_footprint_m2(
    baseline_grid: list | None,
    intervention_grid: list | None,
    min_drop_c: float = COOLED_MIN_DROP_C,
) -> float | None:
    """m² of ground the trees measurably cool: cells where baseline − intervention
    >= min_drop_c. 1 m pitch -> 1 m²/cell. Returns None if either grid is missing
    (mock/scalar backend) or shapes differ.

    The headline value metric: 'these trees cool N m² of ground by >= min_drop_c'.
    Robust on hot sites where every cell is already in heat stress.
    """
    if baseline_grid is None or intervention_grid is None:
        return None
    try:
        import numpy as np  # noqa: PLC0415
    except ImportError:
        return None
    b = np.asarray(baseline_grid, dtype=float)
    i = np.asarray(intervention_grid, dtype=float)
    if b.shape != i.shape:
        return None
    drop = b - i  # positive where the intervention is cooler
    # NaN (outside polygon) propagates to NaN in drop; (NaN >= x) is False -> excluded.
    cooled_cells = int(np.count_nonzero(drop >= min_drop_c))
    return float(cooled_cells)  # 1 m²/cell


# Multi-threshold cooled-area bands (°C). The headline uses COOLED_MIN_DROP_C
# (0.5); the deeper bands show how concentrated the cooling is — a site that
# cools 1000 m² by >=2 °C is a stronger intervention than one that cools the
# same area by a marginal 0.5 °C, even though the headline footprint matches.
COOLED_BANDS_C: tuple[float, ...] = (0.5, 1.0, 2.0)


def cooled_footprint_profile(
    baseline_grid: list | None,
    intervention_grid: list | None,
    bands_c: tuple[float, ...] = COOLED_BANDS_C,
    heat_stress_c: float = UTCI_HEAT_STRESS_C,
) -> dict | None:
    """Richer per-cell analysis of the SAME two real UTCI grids the headline uses.

    Returns a dict with, all derived from real measured cells (1 m²/cell):
      - cooled_m2_by_band:   {band_c: m² cooled by >= band_c}  (0.5/1.0/2.0 default)
      - mean_drop_c:         mean ΔUTCI over the headline-cooled (>=0.5 °C) zone
      - peak_drop_c:         max ΔUTCI of any cell
      - cooled_fraction:     headline-cooled cells ÷ valid (non-NaN) grid cells
      - heat_stress_relieved_m2: cells that were in heat stress (baseline >= 26 °C)
                             and are brought below it by the intervention
      - valid_cells_m2:      count of valid (in-polygon, non-NaN) grid cells

    Returns None if either grid is missing (mock/scalar backend) or shapes differ.
    This is a pure-analysis layer: it never re-runs a sim, only extracts more
    signal from grids that were already measured.
    """
    if baseline_grid is None or intervention_grid is None:
        return None
    try:
        import numpy as np  # noqa: PLC0415
    except ImportError:
        return None
    b = np.asarray(baseline_grid, dtype=float)
    i = np.asarray(intervention_grid, dtype=float)
    if b.shape != i.shape:
        return None

    drop = b - i
    valid = ~np.isnan(drop)
    valid_count = int(np.count_nonzero(valid))
    if valid_count == 0:
        return None

    cooled_by_band = {
        f"{band:g}": int(np.count_nonzero(drop >= band)) for band in bands_c
    }
    headline_mask = drop >= COOLED_MIN_DROP_C
    headline_count = int(np.count_nonzero(headline_mask))
    cooled_drops = drop[headline_mask]
    mean_drop = float(np.nanmean(cooled_drops)) if headline_count else 0.0
    peak_drop = float(np.nanmax(drop)) if valid_count else 0.0
    # Measured dispersion of the cooling over the cooled zone — the honest
    # uncertainty of the headline ΔUTCI (the grid's own spread, not a surrogate
    # band borrowed from calibration). p10/p90 bracket the typical relief.
    std_drop = float(np.nanstd(cooled_drops)) if headline_count else 0.0
    p10_drop = float(np.nanpercentile(cooled_drops, 10)) if headline_count else 0.0
    p90_drop = float(np.nanpercentile(cooled_drops, 90)) if headline_count else 0.0

    # Heat-stress relief: was at/above the stress threshold, now below it.
    was_stressed = valid & (b >= heat_stress_c)
    now_relieved = was_stressed & (i < heat_stress_c)
    heat_stress_relieved = int(np.count_nonzero(now_relieved))

    # Spatial contiguity: a connected shade corridor is worth more than the same
    # area scattered across the site. Largest connected cooled patch (4-conn) and
    # the patch count. Optional — needs scipy; omitted (None) if unavailable.
    largest_patch = None
    n_patches = None
    try:
        from scipy import ndimage  # noqa: PLC0415
        labelled, n_patches_int = ndimage.label(headline_mask)
        n_patches = int(n_patches_int)
        if n_patches:
            # bincount index 0 is the background (non-cooled); ignore it.
            sizes = np.bincount(labelled.ravel())[1:]
            largest_patch = float(int(sizes.max())) if sizes.size else 0.0
        else:
            largest_patch = 0.0
    except Exception:  # noqa: BLE001 — contiguity is a bonus metric
        pass

    return {
        "cooled_m2_by_band": cooled_by_band,
        "mean_drop_c": round(mean_drop, 3),
        "std_drop_c": round(std_drop, 3),
        "p10_drop_c": round(p10_drop, 3),
        "p90_drop_c": round(p90_drop, 3),
        "peak_drop_c": round(peak_drop, 3),
        "cooled_fraction": round(headline_count / valid_count, 4),
        "heat_stress_relieved_m2": float(heat_stress_relieved),
        "heat_stress_threshold_c": heat_stress_c,
        "largest_cooled_patch_m2": largest_patch,
        "n_cooled_patches": n_patches,
        "valid_cells_m2": float(valid_count),
        "bands_c": list(bands_c),
    }

# Fallback crown diameter (m) when a tree's species is not in the BCN species
# table — pinned to 2 × TREE_CANOPY_RADIUS_M (surrogate's representative footprint).
def _fallback_crown_diameter_m() -> float:
    from coolspend.spatial_engine import TREE_CANOPY_RADIUS_M  # noqa: PLC0415
    return 2.0 * float(TREE_CANOPY_RADIUS_M)

_DEFAULT_SPECIES_HEIGHT_M: float = 12.0

# In-process fetch caches (one live calibration run = one process). Keyed so the
# site context (buildings, ground materials) and weather are fetched ONCE and
# reused across every config in the run — they are identical for a fixed site.
# These hold network-fetched INPUTS only; the metered UTCI sim output is cached
# to disk separately via _dispatch.
_AREA_CTX_CACHE: dict[str, tuple] = {}   # polygon-hash -> (buildings, ground_layers)
_WEATHER_CACHE: dict[str, tuple] = {}    # "lat,lon" -> (weather_data list, source_tag)


def _resolve_weather_data(client, lat: float, lon: float, tp, weather_key: str):
    """Return (weather_data, source_tag) for the UTCI/TCS run, with EPW fallback.

    Infrared's weather endpoint (get_weather_file_from_location + filter_weather_data)
    has been returning HTTP 500 server-side (2026-05-29 onward). It is the only hard
    blocker on a live run, so when it fails we fall back to a real measured EPW
    (coolspend.epw_weather) — same WeatherDataPoint payload the SDK would have built.

    Mode via INFRARED_WEATHER_SOURCE env var:
        "auto"     (default) try Infrared, fall back to EPW on any failure
        "epw"      skip Infrared entirely, use EPW (deterministic, offline weather)
        "infrared" require Infrared, never fall back (re-raise on failure)

    Both sources feed from_weatherfile_payload identically; only the provenance
    string differs. Result caching is per (lat,lon) so a site fetches weather once.
    """
    if weather_key in _WEATHER_CACHE:
        return _WEATHER_CACHE[weather_key]

    mode = os.environ.get("INFRARED_WEATHER_SOURCE", "auto").lower()
    weather_data = None
    source_tag = "Infrared weather file"

    if mode != "epw":
        try:
            stations = client.weather.get_weather_file_from_location(
                lat=lat, lon=lon, radius=50,
            )
            if not stations:
                raise RuntimeError(f"No Infrared weather station within 50 km of ({weather_key}).")
            weather_data = client.weather.filter_weather_data(
                identifier=stations[0]["uuid"], time_period=tp,
            )
        except Exception as exc:
            if mode == "infrared":
                raise
            logger.warning(
                "Infrared weather endpoint failed (%s); falling back to EPW. "
                "Set INFRARED_WEATHER_SOURCE=infrared to disable fallback.",
                type(exc).__name__,
            )
            weather_data = None

    if weather_data is None:
        from coolspend.epw_weather import load_weather_data, provenance_note  # noqa: PLC0415
        weather_data = load_weather_data(tp)
        source_tag = provenance_note()

    _WEATHER_CACHE[weather_key] = (weather_data, source_tag)
    return weather_data, source_tag


def _trees_to_vegetation(trees_lonlat: list[dict]) -> dict[str, dict]:
    """Convert placed trees to Infrared vegetation Features (GeoJSON Points).

    Each tree dict has lon, lat, species (scientific name). Properties use the SAME
    keys real OSM trees carry (natural, species, height, diameter_crown) so the
    inference layer dimensions the crown correctly (byo-inputs.md). Per-species crown
    + height come from the REAL Barcelona species table (bcn_species, Verd Urbà
    bands) — so each species has its real footprint, not a single guess. Unknown
    species fall back to the surrogate's representative crown. Empty input -> {}
    (skip injection = bare baseline).
    """
    from coolspend.bcn_species import get_species  # noqa: PLC0415

    fallback_crown = _fallback_crown_diameter_m()
    veg: dict[str, dict] = {}
    for i, t in enumerate(trees_lonlat):
        sp_name = t.get("species") or ""
        sp = get_species(sp_name)
        if sp is not None:
            crown_d = sp.crown_diameter_m
            height = sp.height_m
            sci = sp.scientific
        else:
            crown_d = fallback_crown
            height = _DEFAULT_SPECIES_HEIGHT_M
            sci = sp_name or "Platanus x acerifolia"
        veg[f"placed_{i}"] = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [t["lon"], t["lat"]]},
            "properties": {
                "natural": "tree",
                "species": sci,
                "height": round(float(height), 1),
                "diameter_crown": round(float(crown_d), 2),
            },
        }
    return veg


def _live_utci(metric_key: str, geometry: dict) -> "UTCIResult":
    """Call the real Infrared UTCI (thermal-comfort-index) API and return a UTCIResult.

    Imports infrared_sdk LAZILY (inside this function only) so importing
    coolspend.sdk_client never requires the SDK to be installed — the offline
    mock/cached paths remain available without it (CONCERNS 3.2).

    Security (T-02-07): INFRARED_API_KEY is read by the SDK from the environment
    internally; we validate its presence here but NEVER log it, include it in any
    string, or write it to disk.

    METHOD (the measurement that gives each placement its value):
      baseline geometry  (trees_lonlat == []) -> vegetation={} (bare site)
      intervention       (trees_lonlat != []) -> placed trees injected as vegetation
    Buildings + ground materials + weather are IDENTICAL for both (same site),
    fetched once and cached, so the UTCI delta isolates the cooling of the trees.

    Coordinate policy (SPATIAL-03): polygon + tree coords are WGS84 lon/lat.
    geometry must carry 'polygon_lonlat'; trees in 'trees_lonlat' (lon/lat + species).

    Args:
        metric_key: stable metric identifier ("utci_baseline" or "utci_intervention").
        geometry:   dict with polygon_lonlat + trees_lonlat (see coordinate policy).

    Returns:
        UTCIResult with backend="live".

    Raises:
        EnvironmentError: if INFRARED_API_KEY is not set.
        RuntimeError: if infrared_sdk / numpy not installed.
        ValueError: if geometry lacks polygon_lonlat.
    """
    # ── Key check (T-02-07) ───────────────────────────────────────────────────
    api_key = os.environ.get("INFRARED_API_KEY")
    if api_key is None:
        raise EnvironmentError(
            "INFRARED_BACKEND=live requires INFRARED_API_KEY. "
            "Set INFRARED_API_KEY in your environment or .env file."
        )
    # NEVER log, format, or embed api_key in any string after this point.

    # ── Build WGS84 polygon (SPATIAL-03) — no SDK needed ─────────────────────
    if "polygon_lonlat" not in geometry:
        raise ValueError(
            "geometry must contain 'polygon_lonlat' (list of [lon, lat] pairs) "
            "to call the live Infrared SDK."
        )
    ring = [list(pair) for pair in geometry["polygon_lonlat"]]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    polygon = {"type": "Polygon", "coordinates": [ring]}

    # ── CRS round-trip guard (D-07): fails CLOSED before any SDK import or ────
    # network call. Runs first so a bad ring is rejected even when the SDK is
    # absent — the live call is genuinely unreachable past a coordinate mismatch.
    from coolspend.spatial_engine import assert_crs_roundtrip  # noqa: PLC0415
    assert_crs_roundtrip(ring)

    # ── Lazy imports (CONCERNS 3.2 — module importable offline) ──────────────
    try:
        from infrared_sdk import InfraredClient  # noqa: PLC0415
        from infrared_sdk.analyses.types import (  # noqa: PLC0415
            UtciModelRequest,
            UtciModelBaseRequest,
            AnalysesName,
        )
        from infrared_sdk.models import TimePeriod, Location  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "infrared_sdk not installed — run `pip install infrared-sdk` "
            "before using INFRARED_BACKEND=live."
        ) from exc

    try:
        import numpy as np  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "numpy not installed — run `pip install numpy`."
        ) from exc

    # ── Location = polygon centroid (drives sun position + nearest weather) ──
    lons = [p[0] for p in ring[:-1]]
    lats = [p[1] for p in ring[:-1]]
    centroid_lon = sum(lons) / len(lons)
    centroid_lat = sum(lats) / len(lats)

    poly_hash = _geometry_hash({"ring": ring})
    weather_key = f"{round(centroid_lat, 5)},{round(centroid_lon, 5)}"

    tp = TimePeriod(**UTCI_TIME_PERIOD)

    with InfraredClient() as client:
        # ── Site context: fetch ONCE per polygon, reuse across configs ────────
        if poly_hash not in _AREA_CTX_CACHE:
            area = client.buildings.get_area(polygon)
            try:
                gm = client.ground_materials.get_area(polygon)
                # Keep ONLY valid Infrared material names. The fetch can return
                # extra keys (e.g. 'building') that are not recognised materials;
                # passing them through corrupts the UTCI surface energy balance
                # (server warning: "unrecognised material names"). byo-inputs.md.
                ground_layers = {
                    k: v for k, v in gm.layers.items() if k in _VALID_GROUND_MATERIALS
                }
            except Exception as exc:  # ground materials optional — degrade, don't fail
                logger.warning("ground_materials.get_area failed (%s); proceeding without", type(exc).__name__)
                ground_layers = {}
            _AREA_CTX_CACHE[poly_hash] = (area.buildings, ground_layers)
        buildings, ground_layers = _AREA_CTX_CACHE[poly_hash]

        # ── Weather: Infrared endpoint with EPW fallback (server 500), once ───
        weather_data, weather_src = _resolve_weather_data(
            client, centroid_lat, centroid_lon, tp, weather_key,
        )

        # ── Vegetation: placed trees (intervention) or none (baseline) ────────
        vegetation = _trees_to_vegetation(geometry.get("trees_lonlat", []))

        # ── UTCI payload + run (single tile auto-detected for small sites) ────
        payload = UtciModelRequest.from_weatherfile_payload(
            payload=UtciModelBaseRequest(
                analysis_type=AnalysesName.thermal_comfort_index,
            ),
            location=Location(latitude=centroid_lat, longitude=centroid_lon),
            time_period=tp,
            weather_data=weather_data,
        )
        result = client.run_area_and_wait(
            payload,
            polygon,
            buildings=buildings,
            vegetation=vegetation,           # {} for baseline -> skipped
            ground_materials=ground_layers,  # {} if fetch failed -> skipped
        )

    # Reduce the merged grid. Cells outside the polygon are NaN.
    #   utci_c              = site-mean felt temperature (conservative scalar)
    #   heat_stress_area_m2 = ground area above the strong-heat-stress threshold;
    #                         1 m pitch -> 1 m² per cell, so it is just the count.
    grid = np.asarray(result.merged_grid, dtype=float)
    utci_c = float(np.nanmean(grid))
    valid = ~np.isnan(grid)
    grid_cells_total = int(valid.sum())
    # Peak felt-temp = 90th-percentile cell (sun-exposed hotspots), not the diluted
    # site mean. p90 (not max) avoids a single outlier cell driving the headline.
    utci_peak_c = float(np.nanpercentile(grid, 90)) if grid_cells_total else None
    # (grid > thresh) is False on NaN, so this counts only real cells above it.
    heat_stress_cells = int(np.count_nonzero(grid > UTCI_HEAT_STRESS_C))
    heat_stress_area_m2 = float(heat_stress_cells)  # 1 m²/cell

    n_trees = len(geometry.get("trees_lonlat", []))
    return UTCIResult(
        utci_c=round(utci_c, 2),
        metric="utci_at_1.1m",
        backend="live",
        geometry_hash=_geometry_hash(geometry),
        disclaimer="LIVE Infrared SDK result (thermal-comfort-index, July 09-17 window).",
        source=(
            f"infrared.city run_area_and_wait UTCI; {n_trees} trees as vegetation; "
            f"buildings+ground fetched from Infrared/OSM for site polygon; {weather_src}."
        ),
        heat_stress_area_m2=round(heat_stress_area_m2, 1),
        grid_cells_total=grid_cells_total,
        utci_peak_c=round(utci_peak_c, 2) if utci_peak_c is not None else None,
        # Rounded grid for the cooled-footprint diff (NaN preserved; our cache
        # round-trips NaN via json allow_nan). Cheap for single-tile sites.
        merged_grid=np.round(grid, 2).tolist(),
    )


# ── Dispatch ──────────────────────────────────────────────────────────────────


def _dispatch(metric_key: str, mock_fn, geometry: dict) -> UTCIResult:
    """Route to mock, cached-disk, or live backend based on INFRARED_BACKEND env var.

    cached: reads from CACHE_DIR/{metric_key}_{ghash}.json; raises FileNotFoundError
            on miss — does NOT fall through to mock (CONCERNS 6.1 / T-01-02 stale-cache risk).
    live:   raises EnvironmentError if INFRARED_API_KEY absent; calls _live_utci and
            writes the result to cache_file so INFRARED_BACKEND=cached replays it offline.
    mock:   calls mock_fn(geometry), writes result to cache for future cached reads.
    """
    backend = _backend()
    ghash = _geometry_hash(geometry)
    cache_file = CACHE_DIR / f"{metric_key}_{ghash}.json"

    if backend == "cached":
        if cache_file.exists():
            raw = json.loads(cache_file.read_text(encoding="utf-8"))
            # Required fields must be present — a cache file missing utci_c should
            # fail loudly here, not silently build utci_c=None that crashes far away
            # in delta arithmetic (audit M1). Only the LATER-ADDED spatial fields are
            # optional, so .get() them (older cache files predate those keys).
            _OPTIONAL = {"heat_stress_area_m2", "grid_cells_total", "merged_grid", "utci_peak_c"}
            try:
                result = UTCIResult(**{
                    k: (raw.get(k) if k in _OPTIONAL else raw[k])
                    for k in UTCIResult.__dataclass_fields__
                })
            except KeyError as exc:
                raise ValueError(
                    f"Corrupt cache file {cache_file.name}: missing required field {exc}"
                ) from exc
            # Audit fix (H-2): label the replayed result as "cached" so provenance
            # is unambiguous in call logs and UI. Preserve the original backend in
            # `source` so the origin (mock or live) is still auditable.
            original_backend = result.backend  # "mock" or "live"
            result.backend = f"cached:{original_backend}"
            # Retain "NOT MEASURED DATA" for originally-mock results; add replay note.
            if "NOT MEASURED DATA" in result.disclaimer:
                result.disclaimer = (
                    f"NOT MEASURED DATA — replayed from cache (origin: {original_backend}). "
                    "Cached mock result; NOT a live measurement."
                )
            else:
                result.disclaimer = (
                    f"replayed from cache (origin: {original_backend}). "
                    f"{result.disclaimer}"
                )
            result.source = f"cached replay of {original_backend} result — {result.source}"
            return result
        raise FileNotFoundError(
            f"INFRARED_BACKEND=cached but no cache at {cache_file}"
        )

    if backend == "live":
        result = _live_utci(metric_key, geometry)
        # Write live result to cache so INFRARED_BACKEND=cached can replay offline.
        cache_file.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        return result

    # mock path (default)
    result = mock_fn(geometry)
    cache_file.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return result


# ── Public API ────────────────────────────────────────────────────────────────


def get_baseline_utci(geometry: dict) -> UTCIResult:
    """Return baseline UTCI for an unmodified site polygon.

    Dispatches via INFRARED_BACKEND (mock default, cached, or live).
    See module docstring for backend behaviour and error contract.
    """
    return _dispatch("utci_baseline", _mock_baseline_utci, geometry)


def get_intervention_utci(geometry: dict) -> UTCIResult:
    """Return post-intervention UTCI for a geometry with canopy coverage.

    geometry should include width_m and coverage_fraction keys; missing keys
    treated as zero (no canopy — returns baseline value).
    Dispatches via INFRARED_BACKEND (mock default, cached, or live).
    """
    return _dispatch("utci_intervention", _mock_intervention_utci, geometry)


# ── TCS: Thermal Comfort Statistics ───────────────────────────────────────────

# TCS per-cell unit: hours in the July 09–17 daytime window that exceed the
# moderate heat-stress UTCI threshold (>26 °C). This is a more expressive
# metric than aggregate mean UTCI — a cell going from 80 h to 20 h of heat
# stress is a tangible 60-hour comfort gain, while mean UTCI might only drop
# 0.3 °C. The per-cell grid enables "comfort-hours × m²" as a headline metric.

TCS_HEAT_STRESS_THRESHOLD_C: float = 26.0  # moderate, same as UTCI_HEAT_STRESS_C


def cooled_heatstress_hours_m2(
    baseline_tcs_grid: list | None,
    intervention_tcs_grid: list | None,
) -> float | None:
    """Sum of (baseline_hours − intervention_hours) over all cells where it improved.

    Returns total comfort-hour·m² gained (dimensionally hours × area).
    None if either grid is missing or shapes differ.
    """
    if baseline_tcs_grid is None or intervention_tcs_grid is None:
        return None
    try:
        import numpy as np  # noqa: PLC0415
    except ImportError:
        return None
    b = np.asarray(baseline_tcs_grid, dtype=float)
    i = np.asarray(intervention_tcs_grid, dtype=float)
    if b.shape != i.shape:
        return None
    gain = b - i  # positive = fewer heat-stress hours with trees
    gain = np.where(gain > 0, gain, 0.0)  # only count improvement
    total = float(np.nansum(gain))
    return total if total > 0 else None


def _mock_tcs_baseline(geometry: dict) -> UTCIResult:
    """Mock TCS baseline: 80 h of heat stress per cell (representative July window)."""
    ghash = _geometry_hash(geometry)
    return UTCIResult(
        utci_c=80.0,
        metric="tcs_heat_stress_hours",
        backend="mock",
        geometry_hash=ghash,
        disclaimer=MOCK_DISCLAIMER,
        source="coolspend mock TCS (80 h baseline — representative Barcelona July daytime)",
    )


def _mock_tcs_intervention(geometry: dict) -> UTCIResult:
    """Mock TCS intervention: 60 h under partial canopy (25% reduction)."""
    ghash = _geometry_hash(geometry)
    n_trees = len(geometry.get("trees_lonlat", []))
    reduction = min(n_trees * 2.0, 40.0)  # ~2h reduction per tree, cap at 40h
    hours = max(80.0 - reduction, 30.0)
    return UTCIResult(
        utci_c=hours,
        metric="tcs_heat_stress_hours",
        backend="mock",
        geometry_hash=ghash,
        disclaimer=MOCK_DISCLAIMER,
        source=f"coolspend mock TCS ({hours:.0f} h — {n_trees} trees, {reduction:.0f} h reduction)",
    )


def _live_tcs(metric_key: str, geometry: dict) -> "UTCIResult":
    """Call Infrared TCS (thermal-comfort-statistics, heat-stress subtype).

    Returns per-cell hour counts above moderate heat-stress threshold (>26 °C)
    across the July 09–17 daytime window. Same coordinate policy and caching
    as _live_utci.
    """
    api_key = os.environ.get("INFRARED_API_KEY")
    if api_key is None:
        raise EnvironmentError(
            "INFRARED_BACKEND=live requires INFRARED_API_KEY."
        )

    if "polygon_lonlat" not in geometry:
        raise ValueError("geometry must contain 'polygon_lonlat'")

    ring = [list(pair) for pair in geometry["polygon_lonlat"]]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    polygon = {"type": "Polygon", "coordinates": [ring]}

    from coolspend.spatial_engine import assert_crs_roundtrip  # noqa: PLC0415
    assert_crs_roundtrip(ring)

    try:
        from infrared_sdk import InfraredClient  # noqa: PLC0415
        from infrared_sdk.analyses.types import (  # noqa: PLC0415
            TcsModelRequest,
            TcsModelBaseRequest,
            AnalysesName,
            TcsSubtype,
        )
        from infrared_sdk.models import TimePeriod, Location  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("infrared_sdk not installed.") from exc

    try:
        import numpy as np  # noqa: PLC0415
    except ImportError:
        raise RuntimeError("numpy not installed.")

    lons = [p[0] for p in ring[:-1]]
    lats = [p[1] for p in ring[:-1]]
    centroid_lon = sum(lons) / len(lons)
    centroid_lat = sum(lats) / len(lats)

    poly_hash = _geometry_hash({"ring": ring})
    weather_key = f"{round(centroid_lat, 5)},{round(centroid_lon, 5)}"
    tp = TimePeriod(**UTCI_TIME_PERIOD)

    with InfraredClient() as client:
        if poly_hash not in _AREA_CTX_CACHE:
            area = client.buildings.get_area(polygon)
            try:
                gm = client.ground_materials.get_area(polygon)
                ground_layers = {
                    k: v for k, v in gm.layers.items() if k in _VALID_GROUND_MATERIALS
                }
            except Exception as exc:
                logger.warning("ground_materials.get_area failed (%s)", type(exc).__name__)
                ground_layers = {}
            _AREA_CTX_CACHE[poly_hash] = (area.buildings, ground_layers)
        buildings, ground_layers = _AREA_CTX_CACHE[poly_hash]

        weather_data, weather_src = _resolve_weather_data(
            client, centroid_lat, centroid_lon, tp, weather_key,
        )

        vegetation = _trees_to_vegetation(geometry.get("trees_lonlat", []))

        payload = TcsModelRequest.from_weatherfile_payload(
            payload=TcsModelBaseRequest(
                analysis_type=AnalysesName.thermal_comfort_statistics,
                subtype=TcsSubtype.heat_stress,
            ),
            location=Location(latitude=centroid_lat, longitude=centroid_lon),
            time_period=tp,
            weather_data=weather_data,
        )
        result = client.run_area_and_wait(
            payload,
            polygon,
            buildings=buildings,
            vegetation=vegetation,
            ground_materials=ground_layers,
        )

    grid = np.asarray(result.merged_grid, dtype=float)
    mean_hours = float(np.nanmean(grid))
    n_trees = len(geometry.get("trees_lonlat", []))

    return UTCIResult(
        utci_c=round(mean_hours, 2),  # reusing field: now means hours, not °C
        metric="tcs_heat_stress_hours",
        backend="live",
        geometry_hash=_geometry_hash(geometry),
        disclaimer="LIVE Infrared TCS result (thermal-comfort-statistics heat-stress, July 09-17).",
        source=(
            f"infrared.city run_area_and_wait TCS heat-stress; {n_trees} trees; "
            f"per-cell hours >26 °C UTCI; {weather_src}."
        ),
        merged_grid=np.round(grid, 2).tolist(),
    )


def get_tcs_baseline(geometry: dict) -> UTCIResult:
    """Return baseline TCS heat-stress hours for an unmodified site."""
    return _dispatch("tcs_baseline", _mock_tcs_baseline, geometry)


def get_tcs_intervention(geometry: dict) -> UTCIResult:
    """Return post-intervention TCS heat-stress hours with canopy coverage."""
    return _dispatch("tcs_intervention", _mock_tcs_intervention, geometry)


def _normalize_buildings(buildings) -> list[dict]:
    """Coerce Infrared buildings into a list of plain dicts with coordinates/indices.

    ``client.buildings.get_area().buildings`` is a ``Dict[str, DotBimMesh]`` of frozen
    Pydantic models — NOT a ``list[dict]``. The 3D exporter iterates and calls ``.get()``
    on each item, so the dict-of-models form was silently dropping every building
    (audit: 3D scene had zero context). Normalise to ``[{"coordinates", "indices"}, ...]``.
    """
    if not buildings:
        return []
    items = buildings.values() if isinstance(buildings, dict) else buildings
    out: list[dict] = []
    for m in items:
        if isinstance(m, dict):
            out.append(m)
        elif hasattr(m, "model_dump"):
            out.append(m.model_dump())
        else:  # last-resort attribute read
            out.append({
                "coordinates": getattr(m, "coordinates", []),
                "indices": getattr(m, "indices", None),
            })
    return out


def get_buildings_for_polygon(polygon_lonlat: list) -> list[dict]:
    """Return building meshes (list of dicts with coordinates/indices) for a polygon.

    Cache-first. Network fetch ONLY when INFRARED_BACKEND=live — fetching buildings
    requires a real InfraredClient call, so doing it under mock/cached would violate
    the "mock is fully offline" contract and silently spend API quota (audit C1).
    Returns [] when no data is available rather than raising.
    """
    ring = [list(pair) for pair in polygon_lonlat]
    if len(ring) > 0 and ring[0] != ring[-1]:
        ring.append(ring[0])
    polygon = {"type": "Polygon", "coordinates": [ring]}
    poly_hash = _geometry_hash({"ring": ring})

    # Serve from the in-process context cache regardless of backend (a prior live
    # run may have populated it); the cache stores the SDK-native form for the live
    # sim, so normalise on the way out.
    if poly_hash in _AREA_CTX_CACHE:
        return _normalize_buildings(_AREA_CTX_CACHE[poly_hash][0])

    if _backend() != "live":
        return []
    api_key = os.environ.get("INFRARED_API_KEY")
    if api_key is None:
        return []
    try:
        from infrared_sdk import InfraredClient  # noqa: PLC0415
        with InfraredClient() as client:
            area = client.buildings.get_area(polygon)
            _AREA_CTX_CACHE[poly_hash] = (area.buildings, {})
            return _normalize_buildings(area.buildings)
    except Exception:
        logger.debug("get_buildings_for_polygon fetch failed", exc_info=True)
        return []


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os as _os

    _os.environ.pop("INFRARED_BACKEND", None)
    _os.environ.pop("INFRARED_API_KEY", None)

    sample_geometry = {"width_m": 30.0, "coverage_fraction": 0.35}

    baseline = get_baseline_utci(sample_geometry)
    intervention = get_intervention_utci(sample_geometry)

    print("Baseline UTCI:")
    print(f"  utci_c          = {baseline.utci_c} °C")
    print(f"  backend         = {baseline.backend}")
    print(f"  geometry_hash   = {baseline.geometry_hash}")
    print(f"  disclaimer      = {baseline.disclaimer}")
    print(f"  source          = {baseline.source}")
    print()
    print("Intervention UTCI:")
    print(f"  utci_c          = {intervention.utci_c} °C")
    print(f"  delta vs base   = {round(intervention.utci_c - baseline.utci_c, 2)} °C")
    print(f"  backend         = {intervention.backend}")
    print(f"  geometry_hash   = {intervention.geometry_hash}")
    print(f"  disclaimer      = {intervention.disclaimer}")
