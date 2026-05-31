"""
coolspend/citywide.py — Mode 2 citywide allocation engine.

Loads the data-for-all scored_grid.geojson (494 Barcelona cells, EPSG:25831),
ranks them by composite_score_B (hot×sealed priority), and either fast-scans
(lightweight — cell properties only, no live API) or full-allocates (runs
smart_evaluate on top-N cells).

Strategy
--------
Cells are ~400 m × 400 m in UTM-31N (≈ 160 000 m²), which exceeds the live-
evaluate cap (62 500 m²). For each cell we therefore create a centred sub-polygon
(default 200 m × 200 m = 40 000 m²) that fits comfortably inside the cap while
still sampling the cell's urban fabric.

Scan (fast, ~1 s):
  - Rank all 494 cells by composite_score_B.
  - Estimate tree count from cell area × sealed fraction ÷ per-tree footprint.
  - Estimate budget from tree count × cost-per-tree.
  - No network calls. Good for a citywide heatmap.

Allocate (slow, ~70 s per cell, live API):
  - Run smart_evaluate on the top-N centroid polygons.
  - Collect ΔUTCI, €/m²-cooled, tree count, cost per cell.
  - Sort by €/m²-cooled (ascending — best value first).
  - Allocate the total budget across cells until exhausted.

The output is a GeoJSON FeatureCollection with per-cell scores and (after
allocation) a rank + allocation map.
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

logger = logging.getLogger("coolspend.citywide")

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCORED_GRID = _REPO_ROOT / "L1_INGEST_data" / "data_for_all" / "scored_grid.geojson"

# Sub-polygon size for per-cell evaluation (metres, local UTM).
# 200 m × 200 m = 40 000 m² — safely under the 62 500 m² cap.
_CELL_SAMPLE_SIZE_M = 200.0

# Estimated per-tree footprint (m²) for the fast-scan rough budget.
# Based on 5 m minimum spacing → ~25 m² per tree, but with real-world
# exclusion zones it's more like 150-250 m²/tree. Conservative default.
_EST_M2_PER_TREE = 200.0

# Default cost per tree (EUR) for fast-scan budget estimates.
_EST_COST_PER_TREE_EUR = 1_000.0  # Rough planting-only estimate for fast scan (real cost varies by species + soil)


# ── Loading ──────────────────────────────────────────────────────────────────

def load_scored_grid(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load scored_grid.geojson → list of {properties, geometry_lonlat, centroid_lonlat, ...}.

    Each returned dict has:
      - properties:   original feature properties (cell_id, composite_score_B, mean_sealed, ...)
      - geometry_utm: original Polygon in EPSG:25831
      - centroid_lonlat: (lon, lat) of the cell centroid
      - bbox_utm: (minx, miny, maxx, maxy) in metres
      - cell_area_m2: approximate cell area
    """
    src = Path(path) if path else _SCORED_GRID
    with open(src, encoding="utf-8") as fh:
        geojson = json.load(fh)

    cells: list[dict[str, Any]] = []
    for feat in geojson["features"]:
        props = feat["properties"]
        geom = feat["geometry"]
        coords = geom["coordinates"][0]  # outer ring, UTM

        # Centroid in UTM. Drop the closing vertex of the ring before averaging —
        # a closed ring repeats its first point as its last, and including that
        # duplicate biases the mean toward that corner (here ~57 m SE per cell).
        ring_pts = coords[:-1] if len(coords) > 1 and coords[0] == coords[-1] else coords
        xs = [p[0] for p in ring_pts]
        ys = [p[1] for p in ring_pts]
        cx_utm = sum(xs) / len(xs)
        cy_utm = sum(ys) / len(ys)

        # Reproject to lon/lat
        lon, lat = _utm_to_lonlat(cx_utm, cy_utm)

        # Approximate area via shoelace (UTM — metres)
        area2 = 0.0
        for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
            area2 += x1 * y2 - x2 * y1
        cell_area_m2 = abs(area2) / 2.0

        cells.append({
            "properties": props,
            "geometry_utm": coords,
            "centroid_lonlat": (lon, lat),
            "centroid_utm": (cx_utm, cy_utm),
            "bbox_utm": (min(xs), min(ys), max(xs), max(ys)),
            "cell_area_m2": round(cell_area_m2, 1),
        })

    logger.info("Loaded %d cells from %s", len(cells), src.name)
    return cells


# ── Ranking ───────────────────────────────────────────────────────────────────

def rank_cells(
    cells: list[dict[str, Any]],
    sort_by: str = "composite_score_B",
    descending: bool = True,
) -> list[dict[str, Any]]:
    """Return cells sorted by a property key (default: composite_score_B)."""
    return sorted(
        cells,
        key=lambda c: c["properties"].get(sort_by, 0.0),
        reverse=descending,
    )


# ── Per-cell evaluation polygon ──────────────────────────────────────────────

def cell_eval_polygon(
    cell: dict[str, Any],
    size_m: float = _CELL_SAMPLE_SIZE_M,
) -> list[list[float]]:
    """Build a lon/lat polygon centred on the cell centroid, ``size_m`` metres square.

    Returns a closed ring [[lon, lat], ...] ready for smart_evaluate.
    """
    cx, cy = cell["centroid_utm"]
    half = size_m / 2.0

    # Square in UTM, then reproject corners to lon/lat.
    corners_utm = [
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
    ]
    ring = [_utm_to_lonlat(x, y) for x, y in corners_utm]
    ring.append(ring[0])  # close
    return ring


# ── Fast scan (no live API) ───────────────────────────────────────────────────

def scan_cells(
    cells: list[dict[str, Any]] | None = None,
    top_n: int = 20,
    budget_eur: float = 1_000_000.0,
) -> dict[str, Any]:
    """Lightweight citywide scan — cell properties only, no live API calls.

    Returns a dict with ranked cells + estimated metrics suitable for a heatmap.
    Runtime: < 1 second.
    """
    if cells is None:
        cells = load_scored_grid()

    ranked = rank_cells(cells, "composite_score_B")

    results = []
    cumulative_cost = 0.0
    for rank_idx, cell in enumerate(ranked[:top_n], start=1):
        props = cell["properties"]
        sealed = props.get("mean_sealed", 0.5)
        lst = props.get("mean_lst_celsius", 30.0)
        cell_area = cell["cell_area_m2"]

        # Sample area within the cell
        sample_area = _CELL_SAMPLE_SIZE_M ** 2
        impervious_area = sample_area * sealed

        # Rough tree count estimate
        est_trees = max(1, int(impervious_area / _EST_M2_PER_TREE))
        est_cost = est_trees * _EST_COST_PER_TREE_EUR

        # Simple cooling proxy: LST anomaly × sealed fraction
        lst_anomaly = props.get("lst_anomaly", 0.0)
        cooling_proxy = max(0.0, lst_anomaly) * sealed

        allocated = 0.0
        if cumulative_cost + est_cost <= budget_eur:
            allocated = est_cost
            cumulative_cost += est_cost

        results.append({
            "rank": rank_idx,
            "cell_id": props["cell_id"],
            "district": props.get("district", ""),
            "barri": props.get("barri", ""),
            "composite_score_B": props["composite_score_B"],
            "mean_sealed": sealed,
            "mean_lst_celsius": lst,
            "lst_anomaly": lst_anomaly,
            "cooling_proxy": round(cooling_proxy, 4),
            "sample_area_m2": sample_area,
            "impervious_area_m2": round(impervious_area, 1),
            "est_trees": est_trees,
            "est_cost_eur": round(est_cost),
            "allocated_eur": round(allocated),
            "centroid_lonlat": cell["centroid_lonlat"],
            "eval_polygon": cell_eval_polygon(cell),
        })

    return {
        "mode": "scan",
        "total_cells": len(cells),
        "ranked_count": len(results),
        "budget_eur": budget_eur,
        "cumulative_allocated_eur": round(cumulative_cost),
        "cells": results,
        "note": "Fast scan — estimated from cell properties, no live UTCI. Run /api/citywide/allocate for validated results.",
    }


# ── Full allocation (live smart_evaluate per cell) ────────────────────────────

def _eur_per_m2_cooled(cfg: dict[str, Any]) -> float | None:
    """Extract a scalar €/m²-cooled from a smart_evaluate configuration.

    smart_evaluate may expose this as a bare ``eur_per_m2`` number, as a
    ``cost_per_utci_degree`` metadata dict ``{"value": ..., "unit": ...}``, or
    not at all — in which case fall back to cost ÷ cooled footprint.
    """
    direct = cfg.get("eur_per_m2")
    if isinstance(direct, (int, float)):
        return float(direct)
    cpd = cfg.get("cost_per_utci_degree")
    if isinstance(cpd, dict) and isinstance(cpd.get("value"), (int, float)):
        return float(cpd["value"])
    if isinstance(cpd, (int, float)):
        return float(cpd)
    cooled = cfg.get("cooled_footprint_m2") or 0
    cost = cfg.get("cost_eur") or 0
    if cooled > 0 and cost > 0:
        return round(cost / cooled, 2)
    return None


def allocate_citywide(
    cells: list[dict[str, Any]] | None = None,
    budget_eur: float = 1_000_000.0,
    top_n: int = 5,
    backend: str = "live",
) -> dict[str, Any]:
    """Run smart_evaluate on the top-N cells, sort by €/m²-cooled, allocate budget.

    Each cell gets its centroid sub-polygon evaluated with the full Mode-1 chain:
    baseline UTCI → greedy placement → live intervention UTCI → ΔUTCI + €/m²-cooled.

    Cells are then sorted by €/m²-cooled (ascending — cheapest cooling wins) and
    the budget is allocated greedily until exhausted.

    Runtime: ~70 s per cell with live backend (top_n=5 → ~6 min).
    """
    from coolspend.app_pipeline import smart_evaluate  # noqa: PLC0415

    if cells is None:
        cells = load_scored_grid()

    ranked = rank_cells(cells, "composite_score_B")[:top_n]

    results = []
    for rank_idx, cell in enumerate(ranked, start=1):
        props = cell["properties"]
        cell_id = props["cell_id"]
        ring = cell_eval_polygon(cell)
        geojson_text = json.dumps({"type": "Polygon", "coordinates": [ring]})

        logger.info(
            "Citywide allocate [%d/%d] cell %s (%s, %s) — composite=%.3f",
            rank_idx, top_n, cell_id, props.get("district", ""),
            props.get("barri", ""), props["composite_score_B"],
        )

        try:
            result = smart_evaluate(
                geojson_text=geojson_text,
                budget_eur=budget_eur,
                backend=backend,
            )
        except Exception as exc:  # noqa: BLE001 — one cell fails, keep going
            logger.error("Cell %s failed: %s", cell_id, exc)
            results.append({
                "rank": rank_idx,
                "cell_id": cell_id,
                "district": props.get("district", ""),
                "barri": props.get("barri", ""),
                "composite_score_B": props["composite_score_B"],
                "error": str(exc),
            })
            continue

        cfgs = result.get("configurations", [])
        cfg = cfgs[0] if cfgs else {}

        results.append({
            "rank": rank_idx,
            "cell_id": cell_id,
            "district": props.get("district", ""),
            "barri": props.get("barri", ""),
            "composite_score_B": props["composite_score_B"],
            "mean_sealed": props.get("mean_sealed", 0.0),
            "mean_lst_celsius": props.get("mean_lst_celsius", 0.0),
            "tree_count": cfg.get("tree_count", 0),
            "cost_eur": cfg.get("cost_eur", 0),
            "delta_utci_c": cfg.get("delta_utci_c", 0.0),
            "baseline_utci_c": cfg.get("baseline_utci_c", 0.0),
            "validated_utci_c": cfg.get("validated_utci_c", 0.0),
            "heat_stress_area_m2": cfg.get("heat_stress_area_m2", 0),
            "cooled_footprint_m2": cfg.get("cooled_footprint_m2") or 0,
            "cost_per_m2_cooled": _eur_per_m2_cooled(cfg),
            "headline": result.get("headline", ""),
            "centroid_lonlat": cell["centroid_lonlat"],
            "eval_polygon": ring,
        })

    # Sort by €/m²-cooled (ascending — best value first).
    # Cells with 0 cooled footprint sort last (no measurable cooling).
    def _cooling_value(r: dict) -> float:
        cooled = r.get("cooled_footprint_m2", 0) or 0
        cost = r.get("cost_eur", 0) or 0
        if cooled <= 0 or cost <= 0:
            return float("inf")
        return cost / cooled

    results.sort(key=_cooling_value)

    # Greedy budget allocation across the sorted cells.
    remaining = budget_eur
    allocated_cells = []
    unallocated_cells = []
    for r in results:
        cost = r.get("cost_eur", 0) or 0
        if cost <= remaining and cost > 0:
            r["allocation_eur"] = cost
            remaining -= cost
            allocated_cells.append(r)
        else:
            r["allocation_eur"] = 0.0
            unallocated_cells.append(r)

    total_allocated = budget_eur - remaining
    total_trees = sum(c.get("tree_count", 0) for c in allocated_cells)
    total_cooled = sum(c.get("cooled_footprint_m2", 0) or 0 for c in allocated_cells)

    return {
        "mode": "allocate",
        "total_cells_scanned": len(cells),
        "evaluated_count": len(results),
        "allocated_count": len(allocated_cells),
        "budget_eur": budget_eur,
        "total_allocated_eur": round(total_allocated),
        "remaining_eur": round(remaining),
        "total_trees": total_trees,
        "total_cooled_footprint_m2": total_cooled,
        "avg_cost_per_m2_cooled": round(total_allocated / total_cooled) if total_cooled > 0 else None,
        "allocated_cells": allocated_cells,
        "unallocated_cells": unallocated_cells,
        "headline": (
            f"{len(allocated_cells)} sites, {total_trees} trees, "
            f"{total_cooled:,.0f} m² cooled, "
            f"€{total_allocated:,.0f} of €{budget_eur:,.0f} allocated"
        ),
        "disclaimer": (
            "Per-cell evaluation uses a 200 m × 200 m sample polygon centred on "
            "each cell's centroid. Real per-cell cooling may differ from full-cell "
            "coverage. All in-ground trees tagged requires_utility_survey=True."
        ),
    }


# ── CRS helper ────────────────────────────────────────────────────────────────

# EPSG:25831 (UTM zone 31N) → EPSG:4326 (WGS84 lon/lat).
# Lazily initialised so pyproj is only imported when needed.
_TRANSFORMER = None


def _get_transformer():
    global _TRANSFORMER
    if _TRANSFORMER is None:
        from pyproj import Transformer  # noqa: PLC0415
        _TRANSFORMER = Transformer.from_crs("EPSG:25831", "EPSG:4326", always_xy=True)
    return _TRANSFORMER


def _utm_to_lonlat(x: float, y: float) -> tuple[float, float]:
    """Convert a single UTM-31N coordinate to lon/lat."""
    t = _get_transformer()
    lon, lat = t.transform(x, y)
    return (lon, lat)
