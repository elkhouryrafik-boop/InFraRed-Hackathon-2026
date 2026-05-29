"""
coolspend/export_web.py — export a CoolSpend decision into a self-contained
"web bundle" the deck.gl frontend (and any presentation tool) can consume.

Bundle layout (written to out_dir, default outputs/web_bundle/):
  decision.json        — headline + KPIs for the Top-3 (with peak felt-temp)
  boundary.geojson     — site polygon ring (mask cutout + outline)
  trees.geojson        — proposed + existing trees as Points (lon/lat + color)
  utci_baseline.png    — colorized baseline UTCI raster (RGBA)
  utci_intervention.png— colorized intervention UTCI raster (RGBA)
  bounds.json          — { west, south, east, north } for the two rasters
  scene.glb            — 3D scene (ground + buildings + existing + proposed trees)

Everything here is derived from a run_decision() result — nothing is invented.
The UTCI rasters/bounds are present only for live/cached runs (mock has no grid).

Usage:
  from coolspend.export_web import export_web_bundle
  bundle = export_web_bundle(result)            # result from run_decision(...)
  # -> dict of written paths

CLI:
  python -m coolspend.export_web                # live run at default Eixample site
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("coolspend.export_web")

# Fixed UTCI color scale (°C) so baseline and intervention rasters are directly
# comparable frame-to-frame. 20–40 spans comfortable → strong heat stress.
UTCI_SCALE_MIN_C = 20.0
UTCI_SCALE_MAX_C = 40.0

DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "web_bundle"

# Proposed-tree species palette (RGB 0–255), matches app_3d canopy colours.
_SPECIES_RGB = [
    [31, 119, 180], [255, 127, 14], [44, 160, 44], [214, 39, 40],
    [148, 103, 189], [140, 86, 75], [227, 119, 194], [127, 127, 127],
    [188, 189, 34], [23, 190, 207], [174, 199, 232], [255, 187, 120],
]
_EXISTING_RGB = [115, 140, 107]  # muted olive — context, not proposal


def _bounds_from_ring(ring: list) -> dict[str, float]:
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return {
        "west": min(lons), "south": min(lats),
        "east": max(lons), "north": max(lats),
    }


def _colorize_utci_png(grid: list | None, out_path: Path) -> bool:
    """Write a colorized RGBA PNG of a UTCI grid (row 0 = north). Returns False if no grid."""
    if grid is None:
        return False
    try:
        import numpy as np  # noqa: PLC0415
        from matplotlib import cm  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        logger.warning("UTCI PNG export needs numpy+matplotlib+Pillow; skipping", exc_info=True)
        return False

    a = np.asarray(grid, dtype=float)
    norm = np.clip((a - UTCI_SCALE_MIN_C) / (UTCI_SCALE_MAX_C - UTCI_SCALE_MIN_C), 0.0, 1.0)
    try:
        cmap = cm.get_cmap("RdYlBu_r")
    except AttributeError:  # mpl >= 3.9 fallback
        import matplotlib  # noqa: PLC0415
        cmap = matplotlib.colormaps["RdYlBu_r"]

    rgba = cmap(norm)  # (rows, cols, 4) floats 0–1
    rgba = (rgba * 255).astype(np.uint8)
    # Transparent where the grid is NaN (outside the polygon).
    rgba[np.isnan(a), 3] = 0
    Image.fromarray(rgba, mode="RGBA").save(out_path)
    return True


def export_web_bundle(
    result: dict,
    out_dir: Path | str = DEFAULT_OUT_DIR,
    boundary_override_lonlat: list | None = None,
) -> dict[str, str]:
    """Export a run_decision() result into the web bundle. Returns written-path dict.

    boundary_override_lonlat: optional real site polygon ring ([lon,lat], …) to use
    for boundary.geojson + the map cutout INSTEAD of the pipeline's bbox rectangle.
    The UTCI raster bounds still use the bbox (that's the raster's true extent); only
    the displayed/cut boundary becomes the real shape. Trees are unaffected (they are
    already placed inside the real boundary by is_valid_location).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    if result.get("error") or not result.get("configurations"):
        raise ValueError(f"Cannot export: result has error or no configurations ({result.get('error')})")

    configs = result["configurations"]
    rank1 = configs[0]
    ba = result.get("before_after", {})
    ring = result.get("site_polygon_lonlat")  # bbox rectangle (raster extent)
    boundary_ring = boundary_override_lonlat or ring  # real shape for the outline/cutout

    # ── boundary.geojson ─────────────────────────────────────────────────────
    if boundary_ring:
        closed = [list(p) for p in boundary_ring]
        if closed and closed[0] != closed[-1]:
            closed.append(closed[0])
        boundary = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"kind": "site_boundary"},
                "geometry": {"type": "Polygon", "coordinates": [closed]},
            }],
        }
        p = out / "boundary.geojson"
        p.write_text(json.dumps(boundary), encoding="utf-8")
        written["boundary"] = str(p)

        bounds = _bounds_from_ring(ring)
        pb = out / "bounds.json"
        pb.write_text(json.dumps(bounds, indent=2), encoding="utf-8")
        written["bounds"] = str(pb)

    # ── trees.geojson (proposed rank-1 + existing context) ───────────────────
    features: list[dict] = []
    species_order: list[str] = []
    for t in rank1.get("trees_lonlat", []):
        sp = t.get("species", "")
        if sp not in species_order:
            species_order.append(sp)
        color = _SPECIES_RGB[species_order.index(sp) % len(_SPECIES_RGB)]
        from coolspend.bcn_species import get_species  # noqa: PLC0415
        spx = get_species(sp)
        features.append({
            "type": "Feature",
            "properties": {
                "kind": "proposed", "species": sp,
                "crown_diameter_m": spx.crown_diameter_m if spx else 6.0,
                "height_m": spx.height_m if spx else 10.0,
                "color": color,
            },
            "geometry": {"type": "Point", "coordinates": [t["lon"], t["lat"]]},
        })

    if ring:
        try:
            from coolspend.bcn_data import load_trees  # noqa: PLC0415
            from coolspend.bcn_species import get_species  # noqa: PLC0415
            b = _bounds_from_ring(ring)
            for tr in load_trees(bbox=(b["west"], b["south"], b["east"], b["north"])):
                spx = get_species(tr.get("species") or "")
                features.append({
                    "type": "Feature",
                    "properties": {
                        "kind": "existing", "species": tr.get("species") or "",
                        "crown_diameter_m": spx.crown_diameter_m if spx else 5.0,
                        "height_m": spx.height_m if spx else 8.0,
                        "color": _EXISTING_RGB,
                    },
                    "geometry": {"type": "Point", "coordinates": [tr["lon"], tr["lat"]]},
                })
        except Exception:  # noqa: BLE001 — existing trees are optional context
            logger.debug("existing-tree export skipped", exc_info=True)

    pt = out / "trees.geojson"
    pt.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    written["trees"] = str(pt)

    # ── UTCI rasters ─────────────────────────────────────────────────────────
    if _colorize_utci_png(ba.get("baseline_utci_grid"), out / "utci_baseline.png"):
        written["utci_baseline"] = str(out / "utci_baseline.png")
    if _colorize_utci_png(ba.get("intervention_utci_grid"), out / "utci_intervention.png"):
        written["utci_intervention"] = str(out / "utci_intervention.png")

    # ── scene.glb (reuse the 3D builder + building/existing context) ──────────
    try:
        from coolspend.app_3d import build_glb_scene  # noqa: PLC0415
        from coolspend.sdk_client import get_buildings_for_polygon  # noqa: PLC0415
        from coolspend.app import _load_existing_context_trees  # noqa: PLC0415
        sw = float(result.get("site_width_m") or 120.0)
        sd = float(result.get("site_depth_m") or 120.0)
        buildings = get_buildings_for_polygon(ring) if ring else None
        existing = _load_existing_context_trees(ring, sw, sd) if ring else None
        glb = build_glb_scene(
            rank1, ba,
            buildings=buildings or None,
            baseline_grid=ba.get("baseline_utci_grid"),
            intervention_grid=ba.get("intervention_utci_grid"),
            site_width_m=sw, site_depth_m=sd,
            existing_trees=existing or None,
            out_path=str(out / "scene.glb"),
        )
        written["scene"] = glb
    except Exception:  # noqa: BLE001 — GLB is optional
        logger.warning("scene.glb export failed", exc_info=True)

    # ── decision.json ────────────────────────────────────────────────────────
    def _cfg_summary(cfg: dict) -> dict:
        kpi = cfg.get("cost_per_utci_degree", {}) or {}
        species = []
        for t in cfg.get("trees", []):
            if t.get("active", True):
                from coolspend.bcn_species import get_species  # noqa: PLC0415
                spx = get_species(t.get("species", ""))
                species.append(spx.common if spx else t.get("species", "?"))
        cooled = cfg.get("cooled_footprint_m2")
        cost = cfg.get("cost_eur") or 0.0
        return {
            "rank": cfg.get("rank"),
            "label": cfg.get("label"),
            "tree_count": cfg.get("tree_count"),
            "cost_eur": round(cost, 0),
            "cooled_footprint_m2": cooled,
            "eur_per_m2": round(cost / cooled, 1) if cooled else None,
            "delta_utci_c": cfg.get("delta_utci_c"),
            "utci_baseline_mean": cfg.get("baseline_utci_c"),
            "utci_intervention_mean": cfg.get("validated_utci_c"),
            "utci_baseline_peak": cfg.get("baseline_utci_peak_c"),
            "utci_intervention_peak": cfg.get("validated_utci_peak_c"),
            "cost_per_utci_degree": kpi.get("value"),
            "species": sorted(set(species)),
        }

    # Site centre: use the explicit scan centre if given, else the polygon centroid
    # (the default-site path has center_lonlat=None — the web app still needs a centre
    # to position the camera, so never emit null here).
    center = result.get("center_lonlat")
    if not center and ring:
        center = [
            sum(p[0] for p in ring) / len(ring),
            sum(p[1] for p in ring) / len(ring),
        ]
    decision = {
        "headline": result.get("headline", ""),
        "backend": result.get("backend", ""),
        "disclaimer": result.get("disclaimer", ""),
        "site_center_lonlat": list(center) if center else None,
        "site_width_m": result.get("site_width_m"),
        "site_depth_m": result.get("site_depth_m"),
        "utci_scale_c": [UTCI_SCALE_MIN_C, UTCI_SCALE_MAX_C],
        "configurations": [_cfg_summary(c) for c in configs],
    }
    pd = out / "decision.json"
    pd.write_text(json.dumps(decision, indent=2), encoding="utf-8")
    written["decision"] = str(pd)

    logger.info("Web bundle written to %s (%d files)", out, len(written))
    return written


if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Load .env so INFRARED_API_KEY is available for a live export.
    try:
        from dotenv import load_dotenv  # noqa: PLC0415
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    except Exception:  # noqa: BLE001
        pass
    import json as _json
    from coolspend.app_pipeline import run_decision
    from coolspend.spatial_engine import load_site, set_active_site

    backend = os.environ.get("INFRARED_BACKEND", "live")

    # Demo site = the REAL Plaça dels Àngels plaza polygon (53-vertex irregular shape
    # from NatureGooddest/OSM), NOT a square. Load it as the active site so the
    # optimizer places trees inside the true plaza outline (is_valid_location), then
    # pass the same polygon as the boundary override so the web map shows/cuts the real
    # shape (the pipeline's own site_polygon_lonlat is only the bbox rectangle).
    plaza_path = Path(__file__).resolve().parent / "data" / "angels_plaza_site.geojson"
    site = load_site(str(plaza_path))           # sets per-site UTM origin + returns geoms
    set_active_site(site)                         # optimizer now uses the real plaza
    plaza_ring = _json.loads(plaza_path.read_text(encoding="utf-8"))[
        "features"][0]["geometry"]["coordinates"][0]

    res = run_decision(budget_eur=500_000.0, weights=(0.6, 0.4), backend=backend)
    paths = export_web_bundle(res, boundary_override_lonlat=plaza_ring)
    print("\nWeb bundle:")
    for k, v in paths.items():
        print(f"  {k:16s} {v}")
