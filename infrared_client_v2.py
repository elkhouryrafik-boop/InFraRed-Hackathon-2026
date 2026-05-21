"""
Infrared.city API client — T2.6 mock-first implementation.

DEPRECATED 2026-05-19. The real Infrared SDK is now wired directly via
`from infrared_sdk import InfraredClient` (see scripts/sim/run_infrared_utci_angels*.py
and the /rerun_intervention_utci endpoint in demo_app.py). This file remains
in the tree only to power the legacy `/infrared_json` route used by the old
NG3D viewer at `/`. New code MUST NOT import from this module.

When NG3D is retired, this file can be deleted.

Original docstring follows for history:

This client returned realistic-shaped CFD field stubs so the rest of the platform
could integrate against the contract before the real API key landed. Once the
key arrived (2026-05-19), the supersession path was direct SDK use, not flipping
INFRARED_BACKEND=live on this client.

Mocked endpoints (matched to the documented Infrared capabilities — wind
comfort, UTCI, Tmrt, solar radiation, daylight, SVF):
    simulate_wind(geometry, climate) -> WindResponse
    simulate_utci(geometry, climate) -> UTCIResponse
    simulate_tmrt(geometry, climate) -> TmrtResponse

Each response carries:
    - field: 2-D grid of scalar values (covers the site polygon)
    - scalar_summary: site-mean, p10, p90, max, min
    - run_metadata: backend, model_version, latency_ms, geometry_hash, cached_at

Backend selection (env-driven):
    INFRARED_BACKEND=mock      → deterministic stub fields (default)
    INFRARED_BACKEND=cached    → read from cache/infrared/{hash}.json
    INFRARED_BACKEND=live      → real HTTP API (requires INFRARED_API_KEY)

The mock fields are not random — they're hand-crafted to encode the physical
intuition for Plaça dels Àngels: shaded zones cooler, edges warmer, wind
accelerated through canopy gaps. Good enough to drive UI rendering and
acceptable as a demo placeholder. NEVER claim these as measured data.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Literal

BASE = Path(__file__).resolve().parent
CACHE_DIR = BASE / "cache" / "infrared"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

Backend = Literal["mock", "cached", "live"]


def _backend() -> Backend:
    return os.environ.get("INFRARED_BACKEND", "mock")  # type: ignore[return-value]


def _geometry_hash(geometry: dict) -> str:
    """Deterministic hash of geometry input — keys the cache."""
    blob = json.dumps(geometry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ── Response shapes ──────────────────────────────────────────────────────────


@dataclass
class FieldStats:
    mean: float
    p10: float
    p90: float
    min: float
    max: float
    unit: str


@dataclass
class RunMetadata:
    backend: str
    model_version: str
    latency_ms: int
    geometry_hash: str
    cached_at: str
    citation: str
    disclaimer: str


@dataclass
class CFDResponse:
    metric: str
    grid_rows: int
    grid_cols: int
    field: list[list[float]]
    stats: FieldStats
    metadata: RunMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "grid_rows": self.grid_rows,
            "grid_cols": self.grid_cols,
            "field": self.field,
            "stats": asdict(self.stats),
            "metadata": asdict(self.metadata),
        }


# ── Mock field generators ────────────────────────────────────────────────────


def _site_polygon_grid(rows: int = 24, cols: int = 24) -> list[tuple[int, int]]:
    """Return (row, col) inside the plaza polygon. Plaça dels Àngels is roughly
    rectangular for the demo — full grid coverage."""
    return [(r, c) for r in range(rows) for c in range(cols)]


def _canopy_mask(rows: int, cols: int, fired_patterns: list[str],
                  config_id: str = "C3") -> set[tuple[int, int]]:
    """Where the P01 textile canopy footprint sits.

    The footprint size + position varies per NSGA-II Top-3 configuration:
      C1 (max cooling)   → 50% of grid, centred — large canopy, max coverage
      C2 (min material)  → 25% of grid, centred — small canopy, minimal modules
      C3 (balanced)      → 35% of grid, centred — Pareto knee

    If P01 doesn't fire, returns empty set (no shaded zone).
    """
    if "P01" not in (fired_patterns or []):
        return set()
    if config_id == "C1":
        margin = 0.25       # canopy covers rows 25%..75% (50% width)
    elif config_id == "C2":
        margin = 0.375      # canopy covers rows 37.5%..62.5% (25% width)
    else:                   # C3 balanced
        margin = 0.325      # canopy covers rows 32.5%..67.5% (35% width)
    cr0, cr1 = int(rows * margin), int(rows * (1.0 - margin))
    cc0, cc1 = int(cols * margin), int(cols * (1.0 - margin))
    return {(r, c) for r in range(cr0, cr1) for c in range(cc0, cc1)}


def _green_wall_edge(rows: int, cols: int, fired_patterns: list[str]) -> set[tuple[int, int]]:
    """Where the P14 vertical green wall sits — east edge of the canopy.
    Adds local evapotranspiration cooling at ground-adjacent cells."""
    if "P14" not in (fired_patterns or []):
        return set()
    cc_east = int(cols * 0.68)
    cr0, cr1 = int(rows * 0.30), int(rows * 0.70)
    return {(r, cc_east) for r in range(cr0, cr1)}


def _mock_tmrt_field(geometry: dict, climate: dict) -> CFDResponse:
    """Mock Tmrt field at 1.1m pedestrian height, peak summer noon.

    Physical intuition encoded:
    - Bare granite (no canopy): 55-62 °C  (matches S0 = 58.2 °C from midterm)
    - Under-canopy: 37-44 °C   (matches r1 = 39.5 °C from midterm — ΔTmrt ~18.7)
    - Green-wall-adjacent: -1 to -2 °C additional ET cooling
    - Wind-corridor edges: -0.5 °C from convective mixing
    """
    fired = geometry.get("fired_patterns", []) or []
    config_id = (geometry.get("config_id") or "C3").upper()
    rows, cols = 24, 24
    canopy = _canopy_mask(rows, cols, fired, config_id)
    green_wall = _green_wall_edge(rows, cols, fired)

    base_open = 58.2  # °C — Garcia-Nevado + midterm S0
    base_canopy = 39.5  # °C — midterm r1
    field: list[list[float]] = []
    for r in range(rows):
        row_vals = []
        for c in range(cols):
            if (r, c) in canopy:
                val = base_canopy + (math.sin(r * 0.6) * 1.4) + (math.cos(c * 0.5) * 1.2)
            else:
                edge_dist = min(r, c, rows - 1 - r, cols - 1 - c)
                edge_warm = max(0.0, (3 - edge_dist)) * 0.8
                val = base_open + edge_warm + (math.sin((r + c) * 0.4) * 1.6)
            if (r, c) in green_wall:
                val -= 1.6
            row_vals.append(round(val, 2))
        field.append(row_vals)

    flat = [v for row in field for v in row]
    flat_sorted = sorted(flat)
    n = len(flat)
    stats = FieldStats(
        mean=round(sum(flat) / n, 2),
        p10=round(flat_sorted[n // 10], 2),
        p90=round(flat_sorted[9 * n // 10], 2),
        min=round(flat_sorted[0], 2),
        max=round(flat_sorted[-1], 2),
        unit="degC",
    )
    return CFDResponse(
        metric="tmrt_at_1.1m",
        grid_rows=rows, grid_cols=cols, field=field, stats=stats,
        metadata=_metadata(geometry, latency_ms=410),
    )


def _mock_utci_field(geometry: dict, climate: dict) -> CFDResponse:
    """Mock UTCI field — combines Tmrt, Ta, RH, wind into a felt-temperature
    classification (ISO 7726 / Bröde 2012).

    Classes: <26 No stress, 26-32 Moderate, 32-38 Strong, 38-46 Very strong.
    Encoded: open plaza → 38-44 (Strong/Very strong), under-canopy → 28-33
    (Moderate), edges & corridors → 31-36.
    """
    fired = geometry.get("fired_patterns", []) or []
    config_id = (geometry.get("config_id") or "C3").upper()
    rows, cols = 24, 24
    canopy = _canopy_mask(rows, cols, fired, config_id)
    mist = "P21" in fired or "P07" in fired

    base_open = 41.0
    base_canopy = 30.5
    field: list[list[float]] = []
    for r in range(rows):
        row_vals = []
        for c in range(cols):
            if (r, c) in canopy:
                val = base_canopy + (math.sin(r * 0.5) * 0.8) + (math.cos(c * 0.4) * 0.6)
            else:
                edge_dist = min(r, c, rows - 1 - r, cols - 1 - c)
                edge_cool = (3 - edge_dist) * -0.4 if edge_dist < 3 else 0.0
                val = base_open + edge_cool + (math.cos((r * c) * 0.05) * 0.9)
            if mist and r < 4:  # entry-zone misting
                val -= 1.8
            row_vals.append(round(val, 2))
        field.append(row_vals)

    flat = [v for row in field for v in row]
    flat_sorted = sorted(flat)
    n = len(flat)
    stats = FieldStats(
        mean=round(sum(flat) / n, 2),
        p10=round(flat_sorted[n // 10], 2),
        p90=round(flat_sorted[9 * n // 10], 2),
        min=round(flat_sorted[0], 2),
        max=round(flat_sorted[-1], 2),
        unit="degC_UTCI",
    )
    return CFDResponse(
        metric="utci_at_1.1m",
        grid_rows=rows, grid_cols=cols, field=field, stats=stats,
        metadata=_metadata(geometry, latency_ms=520),
    )


def _mock_wind_field(geometry: dict, climate: dict) -> CFDResponse:
    """Mock wind comfort field (Lawson criteria) — speed magnitude at 1.5m.

    Encoded: open plaza ~3.5-4.5 m/s (from EPW Barcelona July mean 4.2 m/s),
    under-canopy reduced to 1.8-2.6 m/s (sheltering by textile + scaffold).
    Edges accelerated slightly (corner streams)."""
    fired = geometry.get("fired_patterns", []) or []
    config_id = (geometry.get("config_id") or "C3").upper()
    rows, cols = 24, 24
    canopy = _canopy_mask(rows, cols, fired, config_id)

    base_open = 4.2
    base_canopy = 2.3
    field: list[list[float]] = []
    for r in range(rows):
        row_vals = []
        for c in range(cols):
            if (r, c) in canopy:
                val = base_canopy + (math.sin(r * 0.7) * 0.3)
            else:
                edge_dist = min(r, c, rows - 1 - r, cols - 1 - c)
                edge_accel = (2 - edge_dist) * 0.4 if edge_dist < 2 else 0.0
                val = base_open + edge_accel + (math.cos(r * 0.3) * 0.5)
            row_vals.append(round(val, 2))
        field.append(row_vals)

    flat = [v for row in field for v in row]
    flat_sorted = sorted(flat)
    n = len(flat)
    stats = FieldStats(
        mean=round(sum(flat) / n, 2),
        p10=round(flat_sorted[n // 10], 2),
        p90=round(flat_sorted[9 * n // 10], 2),
        min=round(flat_sorted[0], 2),
        max=round(flat_sorted[-1], 2),
        unit="m_s",
    )
    return CFDResponse(
        metric="wind_speed_at_1.5m",
        grid_rows=rows, grid_cols=cols, field=field, stats=stats,
        metadata=_metadata(geometry, latency_ms=380),
    )


def _metadata(geometry: dict, latency_ms: int) -> RunMetadata:
    return RunMetadata(
        backend=_backend(),
        model_version="infrared-mock-v0.1.0",
        latency_ms=latency_ms,
        geometry_hash=_geometry_hash(geometry),
        cached_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        citation=(
            "Mock field — NatureGooddest infrared_client.py. Swap to live "
            "Infrared.city API by setting INFRARED_BACKEND=live + INFRARED_API_KEY."
        ),
        disclaimer="NOT MEASURED DATA — synthetic field for UI integration only.",
    )


# ── Public API ───────────────────────────────────────────────────────────────


def simulate_tmrt(geometry: dict, climate: dict | None = None) -> dict[str, Any]:
    """Tmrt at 1.1m pedestrian height. Returns response dict."""
    return _dispatch("tmrt", _mock_tmrt_field, geometry, climate or {})


def simulate_utci(geometry: dict, climate: dict | None = None) -> dict[str, Any]:
    """UTCI felt-temperature classification. Returns response dict."""
    return _dispatch("utci", _mock_utci_field, geometry, climate or {})


def simulate_wind(geometry: dict, climate: dict | None = None) -> dict[str, Any]:
    """Wind speed magnitude at 1.5m. Returns response dict."""
    return _dispatch("wind", _mock_wind_field, geometry, climate or {})


def _dispatch(metric_key: str, mock_fn, geometry: dict, climate: dict) -> dict[str, Any]:
    backend = _backend()
    ghash = _geometry_hash(geometry)
    cache_file = CACHE_DIR / f"{metric_key}_{ghash}.json"

    if backend == "cached" and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    if backend == "live":
        raise NotImplementedError(
            "INFRARED_BACKEND=live not wired yet — set to 'mock' or 'cached'. "
            "Live wiring requires INFRARED_API_KEY + the OpenAPI spec from "
            "Rafik's teacher contact at infrared.city."
        )

    response = mock_fn(geometry, climate).to_dict()
    cache_file.write_text(json.dumps(response, indent=2), encoding="utf-8")
    return response


def simulate_all(geometry: dict, climate: dict | None = None) -> dict[str, Any]:
    """Convenience: run Tmrt + UTCI + Wind in one call. Returns a flat dict
    keyed by metric for easy frontend consumption."""
    return {
        "tmrt": simulate_tmrt(geometry, climate),
        "utci": simulate_utci(geometry, climate),
        "wind": simulate_wind(geometry, climate),
    }


if __name__ == "__main__":
    sample_geometry = {
        "site_id": "BCN-ANGELS-001",
        "polygon": [[0, 0], [60, 0], [60, 60], [0, 60]],
        "fired_patterns": ["P01", "P14", "P21", "P23"],
    }
    out = simulate_all(sample_geometry)
    for metric, resp in out.items():
        s = resp["stats"]
        print(f"  [{metric}] mean={s['mean']} {s['unit']} | p10={s['p10']} p90={s['p90']} | "
              f"latency={resp['metadata']['latency_ms']}ms | hash={resp['metadata']['geometry_hash']}")
