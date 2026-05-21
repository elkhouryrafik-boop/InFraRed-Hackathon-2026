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
    # Spatial value primitive (live grid only; None for mock/scalar backends).
    # heat_stress_area_m2: ground area (m², 1 m² per cell) where UTCI exceeds the
    # strong-heat-stress threshold (32 °C). Baseline minus intervention = the
    # m² of heat-stress pavement a placement removes — the headline value metric.
    heat_stress_area_m2: float | None = None
    grid_cells_total: int | None = None  # non-NaN cells in the merged grid

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
        """Record one live UTCI call. Raises RuntimeError past cap.

        label: short description of the call (e.g. geometry ID + variant).
        Logs at INFO level via coolspend.sdk_client logger.
        """
        self.calls += 1
        entry = f"live UTCI call #{self.calls}: {label}"
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

# Single-month daytime summer window for the UTCI run. UTCI/TCS require a
# single-month TimePeriod (server sun_vectors generator does not honour multi-
# month windows — see skill 03-time-period.md). July 09:00–17:00 = Barcelona
# peak-heat daytime, the window where shade matters for pedestrian comfort.
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
_WEATHER_CACHE: dict[str, list] = {}     # "lat,lon" -> weather_data list


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

        # ── Weather: nearest station, single-month window, fetch once ─────────
        if weather_key not in _WEATHER_CACHE:
            stations = client.weather.get_weather_file_from_location(
                lat=centroid_lat, lon=centroid_lon, radius=50,
            )
            if not stations:
                raise RuntimeError(
                    f"No Infrared weather station within 50 km of ({weather_key})."
                )
            weather_data = client.weather.filter_weather_data(
                identifier=stations[0]["uuid"], time_period=tp,
            )
            _WEATHER_CACHE[weather_key] = weather_data
        weather_data = _WEATHER_CACHE[weather_key]

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
            "buildings+ground fetched from Infrared/OSM for site polygon."
        ),
        heat_stress_area_m2=round(heat_stress_area_m2, 1),
        grid_cells_total=grid_cells_total,
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
            # .get(k) so optional fields added later (heat_stress_area_m2, ...)
            # don't KeyError when replaying cache files written before they existed.
            result = UTCIResult(**{k: raw.get(k) for k in UTCIResult.__dataclass_fields__})
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
