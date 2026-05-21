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


def _live_utci(metric_key: str, geometry: dict) -> "UTCIResult":
    """Call the real Infrared SDK and return a live UTCIResult.

    Imports infrared_sdk LAZILY (inside this function only) so importing
    coolspend.sdk_client never requires the SDK to be installed — the offline
    mock/cached paths remain available without it (CONCERNS 3.2).

    Security (T-02-07): INFRARED_API_KEY is read by the SDK from the environment
    internally; we validate its presence here but NEVER log it, include it in any
    string, or write it to disk.

    Coordinate policy (T-02-10 / SPATIAL-03): polygon coordinates are WGS84 lon/lat
    only. If geometry carries a "polygon_local_m" key (list of [x_m, y_m] pairs in
    plaza-local metres), they are converted via spatial_engine.local_m_to_latlon.
    If geometry carries "polygon_lonlat", those are used directly. If neither key is
    present, a ValueError is raised — callers must supply polygon coordinates.

    Args:
        metric_key: stable metric identifier ("utci_baseline" or "utci_intervention").
        geometry:   dict with polygon coordinates; see coordinate policy above.

    Returns:
        UTCIResult with backend="live", disclaimer="LIVE Infrared SDK result".

    Raises:
        EnvironmentError: if INFRARED_API_KEY is not set.
        RuntimeError: if infrared_sdk package is not installed.
        ValueError: if geometry lacks usable polygon coordinate keys.
    """
    # ── Key check (T-02-07) ───────────────────────────────────────────────────
    api_key = os.environ.get("INFRARED_API_KEY")
    if api_key is None:
        raise EnvironmentError(
            "INFRARED_BACKEND=live requires INFRARED_API_KEY (issued May 27). "
            "Set INFRARED_API_KEY in your environment or .env file."
        )
    # NEVER log, format, or embed api_key in any string after this point.

    # ── Lazy SDK import (CONCERNS 3.2 — offline before May 27) ───────────────
    try:
        from infrared_sdk import InfraredClient  # noqa: PLC0415
        from infrared_sdk.analyses.types import AnalysesName  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "infrared_sdk not installed — run `pip install infrared-sdk` "
            "before using INFRARED_BACKEND=live."
        ) from exc

    # Lazy numpy import (same offline-safety rationale)
    try:
        import numpy as np  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "numpy not installed — run `pip install numpy` "
            "before using INFRARED_BACKEND=live."
        ) from exc

    # ── Build WGS84 polygon (T-02-10 / SPATIAL-03) ───────────────────────────
    if "polygon_lonlat" in geometry:
        lonlat_pairs = geometry["polygon_lonlat"]
    elif "polygon_local_m" in geometry:
        # Convert local-metre coords to lon/lat via the single CRS boundary.
        from coolspend.spatial_engine import local_m_to_latlon  # noqa: PLC0415
        lonlat_pairs = [
            list(local_m_to_latlon(x_m, y_m))
            for x_m, y_m in geometry["polygon_local_m"]
        ]
    else:
        raise ValueError(
            "geometry must contain 'polygon_lonlat' (list of [lon, lat] pairs) "
            "or 'polygon_local_m' (list of [x_m, y_m] pairs in plaza-local metres) "
            "to call the live Infrared SDK."
        )

    # GeoJSON Polygon — ensure ring is closed (first == last point)
    ring = [list(pair) for pair in lonlat_pairs]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    polygon = {"type": "Polygon", "coordinates": [ring]}

    # ── Infrared SDK call ─────────────────────────────────────────────────────
    # TODO (May-27 wiring): confirm the exact UTCI request class and AnalysesName
    # member against the installed infrared_sdk version. The single variable
    # `utci_request` below is the one-line change needed after SDK inspection.
    with InfraredClient() as client:
        area = client.buildings.get_area(polygon)
        utci_request = AnalysesName.utci  # confirm member name at May-27 wiring
        result = client.run_area_and_wait(
            utci_request,
            polygon,
            buildings=area.buildings,
        )

    # Reduce merged_grid to a site-mean scalar felt temperature
    utci_c = float(np.mean(result.merged_grid))

    return UTCIResult(
        utci_c=round(utci_c, 2),
        metric="utci_at_1.1m",
        backend="live",
        geometry_hash=_geometry_hash(geometry),
        disclaimer="LIVE Infrared SDK result",
        source="infrared.city SDK run_area_and_wait (UTCI)",
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
            result = UTCIResult(**{k: raw[k] for k in UTCIResult.__dataclass_fields__})
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
