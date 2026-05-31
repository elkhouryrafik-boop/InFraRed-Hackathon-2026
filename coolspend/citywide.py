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


def _people_served_for_cell(cell: dict[str, Any], catchment_m: float = 300.0) -> int | None:
    """Residents within a 300 m walking catchment of the cell centroid (WHO 3-30-300).

    Real Padró population × barri density (coolspend.population). Returns None if the
    population data is unavailable — never fabricated, never breaks allocation.
    """
    try:
        from coolspend.population import served_for_centroid  # noqa: PLC0415
        return served_for_centroid(cell["centroid_lonlat"], catchment_m=catchment_m)["people_served"]
    except Exception as exc:  # noqa: BLE001 — population is optional context
        logger.warning("people_served lookup failed for a cell: %s", exc)
        return None


def allocate_citywide(
    cells: list[dict[str, Any]] | None = None,
    budget_eur: float = 1_000_000.0,
    top_n: int = 12,
    backend: str = "live",
    per_site_budget_eur: float = 150_000.0,
) -> dict[str, Any]:
    """Spread the TOTAL budget across MULTIPLE strategic sites (not one crowded site).

    The €1M is NOT dumped into a single plaza. Instead:
      1. Rank the 494 Barcelona cells by composite_score_B (real Landsat heat ×
         sealed surface) and take the top `top_n` as candidate sites.
      2. Plant each candidate at a capped PER-SITE budget (per_site_budget_eur →
         ~15 trees), via the building-aware urban-design greedy placement. A
         per-site cap is what keeps any one site from being over-planted/crowded.
      3. Fund the best candidates first — by measured €/m²-cooled when live, else by
         heat-vulnerability (composite_score_B) — until the TOTAL budget is spent.
         The number of funded sites falls out of the budget (≈ budget / per-site).

    backend: "live" gives measured per-site cooling (one sim per candidate — slow);
    "mock"/"cached" give building-aware valid placement with a synthetic per-site
    cooling estimate (no network), suitable for the citywide demo.

    Runtime: ~70 s per cell live; sub-second per cell on mock (placement only).
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
                budget_eur=per_site_budget_eur,  # PER-SITE cap → uncrowded site
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
            # Per-site placed trees (lon/lat + species + mode) so the frontend can
            # draw each funded site's planting, and so the last site can be trimmed
            # to the remaining budget. Greedy order = best-value first.
            "trees_lonlat": cfg.get("trees_lonlat", []),
            "plantable_area_m2": cfg.get("plantable_area_m2"),
            "delta_utci_c": cfg.get("delta_utci_c", 0.0),
            "baseline_utci_c": cfg.get("baseline_utci_c", 0.0),
            "validated_utci_c": cfg.get("validated_utci_c", 0.0),
            "heat_stress_area_m2": cfg.get("heat_stress_area_m2", 0),
            "cooled_footprint_m2": cfg.get("cooled_footprint_m2") or 0,
            "cost_per_m2_cooled": _eur_per_m2_cooled(cfg),
            "people_served": _people_served_for_cell(cell),
            "headline": result.get("headline", ""),
            "centroid_lonlat": cell["centroid_lonlat"],
            "eval_polygon": ring,
        })

        # Sim-free shade-proxy cooled-m² estimate (Limitation #2/#3 Tier 0), so
        # that even without a measured grid the funding order is driven by an
        # estimated cooled footprint rather than heat-vulnerability alone.
        try:
            from coolspend.cooling_estimator import estimate_site_cooling  # noqa: PLC0415

            est = estimate_site_cooling(cfg.get("trees_lonlat", []), ring, "proxy")
            results[-1]["cooled_m2_proxy"] = est.cooled_m2 or 0
            results[-1]["cooling_is_measured"] = bool((cfg.get("cooled_footprint_m2") or 0) > 0)
        except Exception as exc:  # noqa: BLE001 — proxy is best-effort
            logger.warning("shade-proxy estimate failed for %s: %s", cell_id, exc)
            results[-1]["cooled_m2_proxy"] = 0

    # Funding order. With measured cooling (live), fund cheapest €/m²-cooled first.
    # Without it (mock/cached have no per-cell grid → no real cooled m²), fall back
    # to heat-vulnerability: fund the hottest, most-sealed cells first (the real
    # Landsat-derived composite_score_B), which IS the strategic priority.
    have_cooling = any((r.get("cooled_footprint_m2") or 0) > 0 for r in results)
    have_proxy = any((r.get("cooled_m2_proxy") or 0) > 0 for r in results)
    if have_cooling:
        cooling_source = "measured_utci"  # live/cached: real cooled grid

        def _key(r: dict) -> float:
            cooled = r.get("cooled_footprint_m2", 0) or 0
            cost = r.get("cost_eur", 0) or 0
            return cost / cooled if (cooled > 0 and cost > 0) else float("inf")
        results.sort(key=_key)
    elif have_proxy:
        cooling_source = "shade_proxy_estimate"  # sim-free €/m² ordering (better than heat alone)

        def _key(r: dict) -> float:
            cooled = r.get("cooled_m2_proxy", 0) or 0
            cost = r.get("cost_eur", 0) or 0
            return cost / cooled if (cooled > 0 and cost > 0) else float("inf")
        results.sort(key=_key)
    else:
        cooling_source = "heat_vulnerability"  # composite_score_B fallback
        results.sort(key=lambda r: -(r.get("composite_score_B") or 0.0))

    # Greedy budget allocation across the sorted cells, with a GEOGRAPHIC-SPREAD
    # constraint: don't fund two sites closer than min_site_separation_m. The user
    # wants the €1M spread across DIFFERENT places, not two adjacent grid cells —
    # so a candidate too close to an already-funded site is skipped (held for the
    # unallocated list), letting the budget reach a genuinely distinct next site.
    import math as _math  # noqa: PLC0415
    min_site_separation_m = 500.0

    def _far_enough(r: dict, funded: list[dict]) -> bool:
        c = r.get("centroid_lonlat")
        if not c:
            return True
        for f in funded:
            fc = f.get("centroid_lonlat")
            if not fc:
                continue
            mlat = _math.radians((c[1] + fc[1]) / 2.0)
            dx = (c[0] - fc[0]) * _math.cos(mlat) * 111_320.0
            dy = (c[1] - fc[1]) * 110_540.0
            if (dx * dx + dy * dy) ** 0.5 < min_site_separation_m:
                return False
        return True

    remaining = budget_eur
    allocated_cells = []
    unallocated_cells = []
    for r in results:
        cost = r.get("cost_eur", 0) or 0
        trees = r.get("trees_lonlat", []) or []
        if remaining <= 0 or cost <= 0 or not _far_enough(r, allocated_cells):
            r["allocation_eur"] = 0.0
            unallocated_cells.append(r)
            continue
        if cost <= remaining:
            r["allocation_eur"] = cost
            remaining -= cost
            allocated_cells.append(r)
        elif trees:
            # PARTIAL fund: the budget can't cover this whole site, but we must spend
            # all the money — so plant only the prefix of (best-value-first) trees that
            # fits the remainder, and trim this site's cost/count to match.
            per_tree = cost / len(trees)
            k = max(1, int(remaining // per_tree)) if per_tree > 0 else 0
            if k >= 1:
                r["trees_lonlat"] = trees[:k]
                r["tree_count"] = k
                r["cost_eur"] = round(k * per_tree, 2)
                r["allocation_eur"] = r["cost_eur"]
                r["partial"] = True
                remaining -= r["cost_eur"]
                allocated_cells.append(r)
            else:
                r["allocation_eur"] = 0.0
                unallocated_cells.append(r)
        else:
            r["allocation_eur"] = 0.0
            unallocated_cells.append(r)

    total_allocated = budget_eur - remaining
    total_trees = sum(c.get("tree_count", 0) for c in allocated_cells)
    total_cooled = sum(c.get("cooled_footprint_m2", 0) or 0 for c in allocated_cells)
    total_cooled_proxy = round(sum(c.get("cooled_m2_proxy", 0) or 0 for c in allocated_cells), 1)

    # Portfolio population served (WHO 3-30-300): unique residents within 300 m of any
    # funded site, de-duplicating overlapping catchments. Real Padró data; degrades to
    # None if unavailable. Cheap — one geometric union over the funded centroids.
    total_people_served: int | None = None
    try:
        from coolspend.population import portfolio_people_served  # noqa: PLC0415
        centroids = [c["centroid_lonlat"] for c in allocated_cells if c.get("centroid_lonlat")]
        if centroids:
            total_people_served = portfolio_people_served(centroids, catchment_m=300.0).get(
                "total_people_served"
            )
    except Exception as exc:  # noqa: BLE001 — population is optional context
        logger.warning("portfolio people_served failed: %s", exc)

    # Urban-design metrics (from the urban-design skill audit): per-site canopy area
    # / cover% / est. ΔT, and portfolio canopy + per-euro + person-degrees (people ×
    # mean °C relief). Geometric crown estimates; the measured cooling is the UTCI sim.
    from coolspend.design_metrics import design_metrics, person_degrees  # noqa: PLC0415
    _sample_area = _CELL_SAMPLE_SIZE_M ** 2  # 200×200 m per-cell evaluation sample
    for c in allocated_cells:
        c["design_metrics"] = design_metrics(
            c.get("trees_lonlat", []), site_area_m2=_sample_area, cost_eur=c.get("cost_eur"),
            plantable_area_m2=c.get("plantable_area_m2"),
        )
    total_canopy_m2 = round(
        sum((c.get("design_metrics", {}).get("canopy_area_m2") or 0) for c in allocated_cells), 1
    )
    _mean_drop = (
        sum((c.get("delta_utci_c") or 0) for c in allocated_cells) / len(allocated_cells)
        if allocated_cells else None
    )
    total_person_degrees = person_degrees(total_people_served, _mean_drop)

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
        "total_cooled_m2_proxy": total_cooled_proxy,
        "cooling_source": cooling_source,
        "cooling_is_measured": cooling_source == "measured_utci",
        "total_people_served": total_people_served,
        "total_canopy_m2": total_canopy_m2,
        "total_canopy_m2_per_1000eur": round(total_canopy_m2 / (total_allocated / 1000.0), 1) if total_allocated else None,
        "total_person_degrees": total_person_degrees,
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
            "each cell's centroid. Funding order driven by "
            + {
                "measured_utci": "MEASURED Infrared UTCI €/m²-cooled.",
                "shade_proxy_estimate": "an ESTIMATED €/m²-cooled from the sim-free "
                "shade proxy (real sun geometry; NOT measured UTCI).",
                "heat_vulnerability": "heat-vulnerability (composite_score_B) — no "
                "cooling estimate available.",
            }[cooling_source]
            + " All in-ground trees tagged requires_utility_survey=True."
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
