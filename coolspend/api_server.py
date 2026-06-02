"""
coolspend/api_server.py — thin HTTP backend for the interactive deck.gl frontend.

The frontend (web/) was a static web-bundle viewer. This server makes it
interactive: the user draws a polygon anywhere in Barcelona, we report the
buildings detected inside it, then on "Evaluate" we run the REAL pipeline
(run_decision -> export_web_bundle) and hand back a fresh bundle to render.

Endpoints
---------
GET  /api/health                     -> {status, backend}
POST /api/buildings  {polygon}       -> {building_count, polygon_area_m2,
                                          built_footprint_m2_approx, ...}  (fast)
POST /api/evaluate   {polygon,...}   -> web-bundle JSON (decision+boundary+
                                          trees+bounds+image urls)         (slow)

The bundle files are written under web/public/web_bundle/ so the existing
frontend loader (and vite dev server) serve them unchanged at /web_bundle/*.

Security
--------
- INFRARED_API_KEY is read by the SDK from the environment only; never logged,
  never accepted over HTTP, never returned.
- Polygons are size-capped server-side (MAX_AREA_M2) — a defensive mirror of the
  frontend cap — so a giant polygon cannot trigger a runaway live-tile fan-out.
- Backend mode comes from INFRARED_BACKEND env (mock|cached|live), NOT the request.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path so `coolspend.*` imports resolve
# whether this file is run as `python coolspend/api_server.py` or as
# `python -m coolspend.api_server`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

logger = logging.getLogger("coolspend.api_server")

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WEB_PUBLIC = _REPO_ROOT / "web" / "public"
_WEB_DIST = _REPO_ROOT / "web" / "dist"
_BUNDLE_DIR = _WEB_PUBLIC / "web_bundle"   # CURATED default showcase (served at /web_bundle/*)
# Live /api/evaluate output goes here, NOT into the curated showcase — otherwise a
# user drawing+evaluating an area would overwrite the demo's default plaza result on
# disk (it reloads from there). Served at /eval_bundle/*.
_EVAL_DIR = _WEB_PUBLIC / "eval_bundle"

# Defensive server-side selection cap. 250 m x 250 m = 62 500 m^2 is already a
# large urban block; beyond this a live run fans out to many tiles and stalls a
# demo. The frontend enforces the same number for instant feedback.
MAX_AREA_M2 = 62_500.0
MIN_AREA_M2 = 400.0   # 20 m x 20 m — below this there is nothing to evaluate.

DEFAULT_BUDGET_EUR = 500_000.0


# ── Request models ──────────────────────────────────────────────────────────

class PolygonRequest(BaseModel):
    """A drawn selection: a lon/lat ring (open or closed)."""
    polygon: list[list[float]] = Field(..., min_length=3,
                                        description="[[lon,lat], ...] ring")


class EvaluateRequest(PolygonRequest):
    """Body of POST /api/evaluate: the drawn ring plus budget and KPI weights."""
    budget_eur: float = Field(DEFAULT_BUDGET_EUR, gt=0)
    w_thermal: float = Field(0.6, ge=0, le=1)
    w_ecological: float = Field(0.4, ge=0, le=1)


class SaveRunRequest(BaseModel):
    """Body of POST /api/runs: persist an evaluated run so the app remembers it.

    `payload` is the /api/evaluate response the client already holds (decision +
    boundary + trees + bounds + image URLs + impervious/canopy/growth). The server
    snapshots the heatmap PNGs out of the shared eval bundle into the run's own
    blob dir, so a later evaluate cannot corrupt this saved run.
    """
    name: str = Field(..., min_length=1, max_length=120)
    polygon: list[list[float]] = Field(..., min_length=3)
    budget_eur: float = Field(DEFAULT_BUDGET_EUR, gt=0)
    w_thermal: float = Field(0.6, ge=0, le=1)
    w_ecological: float = Field(0.4, ge=0, le=1)
    payload: dict[str, Any] = Field(..., description="The /api/evaluate response to persist")


# ── Geometry helpers (UTM-31N via the single CRS boundary in spatial_engine) ──

def _ring_closed(polygon: list[list[float]]) -> list[list[float]]:
    pts = [[float(p[0]), float(p[1])] for p in polygon]
    # Drop consecutive duplicate vertices: a repeated point (common from
    # click-drawn polygons) makes a degenerate ring that can collapse the
    # candidate-slot geometry to empty even where there is plantable space.
    ring: list[list[float]] = [pts[0]]
    for p in pts[1:]:
        if p != ring[-1]:
            ring.append(p)
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def _polygon_area_m2(ring_lonlat: list[list[float]]) -> float:
    """Geodesic-ish polygon area via UTM-31N projection + shoelace (m^2)."""
    from coolspend.spatial_engine import _TO_UTM  # noqa: PLC0415
    pts = [_TO_UTM.transform(lon, lat) for lon, lat in ring_lonlat]
    area2 = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        area2 += x1 * y2 - x2 * y1
    return abs(area2) / 2.0


def _validate_area(ring: list[list[float]]) -> float:
    area = _polygon_area_m2(ring)
    if area > MAX_AREA_M2:
        raise HTTPException(
            status_code=422,
            detail=f"Selection too large: {area:,.0f} m² > {MAX_AREA_M2:,.0f} m² cap. "
                   "Draw a smaller area.",
        )
    if area < MIN_AREA_M2:
        raise HTTPException(
            status_code=422,
            detail=f"Selection too small: {area:,.0f} m² < {MIN_AREA_M2:,.0f} m² minimum.",
        )
    return area


# ── App ───────────────────────────────────────────────────────────────────

def _backend_mode() -> str:
    return os.environ.get("INFRARED_BACKEND", "mock")


def create_app() -> FastAPI:
    """Build and return the CoolSpend FastAPI app (routes, CORS, .env loading).

    Registers the interactive endpoints (/api/health, /api/buildings,
    /api/evaluate, /api/citywide/*) and wires the three-tier Infrared backend via
    the INFRARED_BACKEND env var. Called at import time and by the test client.
    """
    # Load .env (INFRARED_API_KEY) regardless of how the app is launched, so a
    # live backend always has its key — not only via the __main__ block.
    try:
        from dotenv import load_dotenv  # noqa: PLC0415
        load_dotenv(_REPO_ROOT / ".env")
    except Exception:  # noqa: BLE001
        pass

    app = FastAPI(title="CoolSpend API", version="1.0")

    # Persistence ("make it remember"): create the runs table on boot so the
    # save/load endpoints work on a fresh deploy with no manual migration step.
    from coolspend import store  # noqa: PLC0415
    store.init_db()

    # Vite dev server runs on a different origin; allow local dev origins. In a
    # split production deploy (frontend on Vercel, backend on Render) the frontend
    # is yet another origin, so CORS_ORIGINS (comma-separated) appends the deployed
    # web URL(s) — without it the browser would block the cross-origin /api fetch.
    _origins = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://127.0.0.1:4173",
    ]
    _extra = os.environ.get("CORS_ORIGINS", "")
    _origins += [o.strip() for o in _extra.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "backend": _backend_mode()}

    @app.post("/api/buildings")
    def buildings(req: PolygonRequest) -> dict[str, Any]:
        """Fast preview: validated polygon area + surrounding-tile building context.

        HONESTY NOTE: Infrared returns buildings per map TILE, and the dotBIM mesh
        coordinates are in Infrared's own local frame (not our georeferenced one),
        so we cannot reliably clip the count to the exact drawn polygon. We therefore
        report ``context_building_count`` (buildings in the fetched tile around the
        selection) — clearly labelled — rather than an over-stated per-polygon count.
        The buildings render exactly, in the right place, in the 3D scene after Evaluate.
        """
        ring = _ring_closed(req.polygon)
        area_m2 = _validate_area(ring)

        from coolspend.spatial_engine import set_site_origin_from_polygon  # noqa: PLC0415
        from coolspend.sdk_client import get_buildings_for_polygon  # noqa: PLC0415

        # Set the per-site frame so a subsequent evaluate reuses the same origin.
        set_site_origin_from_polygon([(p[0], p[1]) for p in ring])
        try:
            bldgs = get_buildings_for_polygon(ring)
            context_count = len(bldgs)
            buildings_available = context_count > 0
        except Exception as exc:  # noqa: BLE001 — preview must never hard-fail
            logger.warning("buildings preview fetch failed (%s)", type(exc).__name__)
            context_count = 0
            buildings_available = False

        # Impervious-pavement (depave) targeting: real ground-material complement.
        from coolspend.ground_analysis import analyze_impervious  # noqa: PLC0415
        impervious = analyze_impervious(ring, backend=_backend_mode())

        return {
            "polygon_area_m2": round(area_m2, 1),
            "context_building_count": context_count,
            "buildings_available": buildings_available,
            "impervious": impervious,
            "backend": _backend_mode(),
            "note": (
                "Context building count is for the fetched map tile around your "
                "selection. Buildings render exactly inside the area in the 3D scene "
                "after Evaluate; their shadows are already in the cooling simulation."
            ),
        }

    @app.post("/api/evaluate")
    def evaluate(req: EvaluateRequest) -> dict[str, Any]:
        """Run the real pipeline on the drawn polygon and return a web bundle."""
        ring = _ring_closed(req.polygon)
        _validate_area(ring)

        from coolspend.app_pipeline import smart_evaluate  # noqa: PLC0415
        from coolspend.export_web import export_web_bundle  # noqa: PLC0415

        poly_geojson = json.dumps({"type": "Polygon", "coordinates": [ring]})
        configured = _backend_mode()
        logger.info("Evaluate: backend=%s area=%.0f m² budget=%.0f",
                    configured, _polygon_area_m2(ring), req.budget_eur)

        # Building-aware greedy placement on EVERY backend. We try the configured
        # backend first; if it throws (e.g. live Infrared unreachable / no key) or
        # yields no configurations, we fall back to `mock` — real placement with a
        # clearly-labelled synthetic cooling estimate — so a drawn area NEVER 500s
        # on a backend hiccup. Only a genuinely unplantable area returns an empty
        # (still 200) result the UI can explain.
        result: dict[str, Any] | None = None
        backend = configured
        attempts: list[str] = []
        for be in dict.fromkeys([configured, "mock"]):
            try:
                r = smart_evaluate(
                    geojson_text=poly_geojson, budget_eur=req.budget_eur, backend=be,
                )
            except Exception as exc:  # noqa: BLE001 — never let a backend fault 500 the draw flow
                logger.warning("evaluate: backend=%s raised: %s", be, exc)
                attempts.append(f"{be}: {exc}")
                continue
            if r.get("error") or not r.get("configurations"):
                attempts.append(f"{be}: {r.get('error') or 'no configurations'}")
                result = r  # keep the graceful empty payload from the last attempt
                continue
            result, backend = r, be
            break

        # No backend produced a plantable plan → return a clean, explainable 200
        # (the area is genuinely unplantable, or every backend faulted), NOT a 500.
        if result is None or result.get("error") or not result.get("configurations"):
            base = result or {}
            return {
                "empty": True,
                "backend": backend,
                "headline": base.get("headline")
                or "No plantable spots found in this area. Try a larger or less built-up block.",
                "disclaimer": base.get("disclaimer")
                or "Zero validated tree slots after removing buildings, roads and spacing.",
                "reason": base.get("error") or "no plantable slots",
                "attempts": attempts,
                "site_polygon_lonlat": ring,
                "configurations": [],
            }

        _EVAL_DIR.mkdir(parents=True, exist_ok=True)
        export_web_bundle(result, out_dir=_EVAL_DIR, boundary_override_lonlat=ring)

        payload = _read_bundle_payload(_EVAL_DIR, "/eval_bundle")

        # Depave targeting: real impervious pavement + how much of it the proposed
        # rank-1 canopy would shade ("depaved & cooled"). Best-effort: a fault here
        # must not sink an otherwise-valid result.
        from coolspend.ground_analysis import (  # noqa: PLC0415
            analyze_impervious, depaved_by_canopy, canopy_cover_fraction,
        )
        try:
            impervious = analyze_impervious(ring, backend=backend)
            rank1_trees = (result["configurations"][0] or {}).get("trees_lonlat", [])
            depaved = depaved_by_canopy(impervious["geojson"], rank1_trees)
            impervious["depaved_cooled_m2"] = depaved
            # #2: permeable fraction if the pavement under the new canopy is depaved.
            site_m2 = impervious.get("site_area_m2") or 0.0
            if site_m2:
                permeable_after = impervious.get("permeable_m2", 0.0) + depaved
                impervious["permeable_fraction_if_depaved"] = round(permeable_after / site_m2, 3)
            payload["impervious"] = impervious
            # #1: real canopy-cover fraction vs the 30-40% climate-responsive target.
            payload["canopy"] = canopy_cover_fraction(ring, rank1_trees)
        except Exception as exc:  # noqa: BLE001 — secondary analysis is best-effort
            logger.warning("evaluate: ground analysis failed (non-fatal): %s", exc)

        # Growth/establishment ramp params (cost_model single source of truth) so
        # the frontend age slider uses the SAME sourced curve, not a new invention.
        from coolspend.cost_model import DEFAULT_GROWTH_DISCOUNT as _G  # noqa: PLC0415
        payload["growth"] = {
            "ramp_years": _G.ramp_years,
            "initial_fraction": _G.initial_fraction,
            "horizon_years": _G.horizon_years,
        }

        # Return the bundle contents inline so the frontend can render without a
        # second round-trip; image URLs point at the served static files.
        return payload

    # ── Mode 2: citywide allocation ─────────────────────────────────────────

    @app.get("/api/citywide/scan")
    def citywide_scan(top_n: int = 20, budget_eur: float = DEFAULT_BUDGET_EUR) -> dict[str, Any]:
        """Fast citywide scan: rank all 494 cells by hot×sealed, estimate tree cost.

        No live API calls — cell properties only. Returns ranked list with estimated
        tree counts, costs, and cooling proxy. Use for a citywide heatmap.
        Runtime: < 1 second.
        """
        from coolspend.citywide import load_scored_grid, scan_cells  # noqa: PLC0415
        cells = load_scored_grid()
        return scan_cells(cells, top_n=min(top_n, 100), budget_eur=budget_eur)

    @app.post("/api/citywide/allocate")
    def citywide_allocate(top_n: int = 5, budget_eur: float = DEFAULT_BUDGET_EUR) -> dict[str, Any]:
        """Full citywide allocation: run smart_evaluate on top-N hot×sealed cells.

        Each cell is evaluated with the full Mode-1 chain (baseline UTCI → greedy
        placement → live intervention UTCI). Cells are then sorted by €/m²-cooled
        and the budget is allocated greedily.

        Runtime: ~70 s per cell with live backend (top_n=5 → ~6 min). Use scan
        first for a fast overview, then allocate on a shortlist.
        """
        backend = _backend_mode()
        # mock/cached are allowed: placement is real (building-aware urban-design),
        # per-site cooling is a labelled synthetic estimate and site PRIORITY uses the
        # real Landsat heat × sealed ranking. live adds measured per-site cooling.
        from coolspend.citywide import load_scored_grid, allocate_citywide  # noqa: PLC0415
        cells = load_scored_grid()
        return allocate_citywide(cells, budget_eur=budget_eur, top_n=min(top_n, 20), backend=backend)

    # ── Saved runs: make it remember (Day-2 slides, Part 2) ──────────────────

    @app.post("/api/runs")
    def save_run(req: SaveRunRequest) -> dict[str, Any]:
        """Persist an evaluated run (metadata row + heatmap blobs). Returns {id}.

        The heatmaps are snapshotted out of the shared eval bundle (_EVAL_DIR,
        still present from the just-finished evaluate) into the run's own blob dir.
        """
        run_id = store.save_run(
            name=req.name,
            polygon=req.polygon,
            params={
                "budget_eur": req.budget_eur,
                "w_thermal": req.w_thermal,
                "w_ecological": req.w_ecological,
                "backend": _backend_mode(),
            },
            payload=req.payload,
            eval_dir=_EVAL_DIR,
        )
        return {"id": run_id}

    @app.get("/api/runs")
    def list_runs() -> list[dict[str, Any]]:
        """List saved runs (newest first) with headline KPIs for the gallery."""
        return store.list_runs()

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: int) -> dict[str, Any]:
        """Return a saved run as an evaluate-shaped payload the frontend re-renders."""
        run = store.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"No saved run #{run_id}.")
        return run

    # Serve the blob store (saved-run heatmaps) so a reloaded run's PNGs resolve.
    # Mounted BEFORE the catch-all "/" below, mirroring the /eval_bundle mount.
    _blob_url, _blob_path = store.blob_mount()
    app.mount(_blob_url, StaticFiles(directory=str(_blob_path)), name="blobs")

    # Serve the runtime-written evaluate bundle so its PNGs resolve in BOTH dev and
    # a built deploy. In dev vite serves web/public/eval_bundle; in production the
    # catch-all "/" mount below serves web/dist (which never receives runtime files),
    # so we mount _EVAL_DIR explicitly at /eval_bundle BEFORE the catch-all.
    _EVAL_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/eval_bundle", StaticFiles(directory=str(_EVAL_DIR)), name="eval_bundle")

    # Serve the built frontend (production) if present. In dev, vite serves it.
    if _WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=str(_WEB_DIST), html=True), name="web")

    return app


def _read_bundle_payload(bundle_dir: Path, url_base: str) -> dict[str, Any]:
    """Read a written bundle dir into a single JSON payload for the client.

    url_base is the path the static server exposes that dir at (e.g. /eval_bundle).
    """
    def _load(name: str) -> Any:
        p = bundle_dir / name
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    bundle: dict[str, Any] = {
        "decision": _load("decision.json"),
        "boundary": _load("boundary.geojson"),
        "trees": _load("trees.geojson"),
        "bounds": _load("bounds.json"),
    }
    # PNGs are served statically by vite/StaticFiles from the public dir.
    for key, fname in (("baselineImageUrl", "utci_baseline.png"),
                       ("interventionImageUrl", "utci_intervention.png")):
        bundle[key] = f"{url_base}/{fname}" if (bundle_dir / fname).is_file() else None
    return bundle


app = create_app()


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        from dotenv import load_dotenv  # noqa: PLC0415
        load_dotenv(_REPO_ROOT / ".env")
    except Exception:  # noqa: BLE001
        pass
    os.environ.setdefault("INFRARED_BACKEND", "live")
    port = int(os.environ.get("COOLSPEND_API_PORT", "8000"))
    logger.info("CoolSpend API on http://127.0.0.1:%d (backend=%s)", port, _backend_mode())
    uvicorn.run(app, host="127.0.0.1", port=port)
