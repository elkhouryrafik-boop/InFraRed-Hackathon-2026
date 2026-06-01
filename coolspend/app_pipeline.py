"""
coolspend/app_pipeline.py — UI-agnostic pipeline wrapper for CoolSpend.

Provides run_decision() — a single callable that drives the full pipeline
(optimize -> validate Top-3 -> TOPSIS) and returns a structured result dict
suitable for any UI layer (Gradio, CLI, tests).

Key contracts:
  - Fully offline on INFRARED_BACKEND=mock (no API key required)
  - Safe GeoJSON parsing via json.loads ONLY (never eval/exec) — T-03-01
  - Every Infrared SDK call is captured into call_log via a logging.Handler
    attached to coolspend.sdk_client logger for the duration of the run
  - SimBudget(max_live_calls=3) caps live Infrared calls per run — T-03-02
  - INFRARED_API_KEY is never read, logged, or returned — T-03-03
  - Honesty: mock backend always surfaces "NOT MEASURED DATA" in disclaimer
  - Deterministic: seed 42 through the pipeline; identical args -> identical output

Public API:
  parse_site_geojson(text) -> str | None   (path to temp .geojson, or None)
  run_decision(...)        -> dict          (structured result)
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from coolspend.cost_model import (
    CostTable,
    GrowthDiscountParams,
    cost_per_utci_degree,
    load_cost_table,
    cost_table_from_dict,
)
from coolspend.optimizer import (
    DEFAULT_BUDGET_EUR,
    run_optimisation,
    select_top3,
    topsis_rank,
    validate_top3_with_infrared,
)
from coolspend.sdk_client import SimBudget
from coolspend.spatial_engine import DEFAULT_SITE

logger = logging.getLogger(__name__)


# ── Logging capture handler ───────────────────────────────────────────────────


class _CaptureHandler(logging.Handler):
    """Append each log record's message to a provided list (no formatting)."""

    def __init__(self, target_list: list[str]) -> None:
        super().__init__(level=logging.DEBUG)
        self._target = target_list

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        """Append the record's message to the target list; never raise (logging-safe)."""
        try:
            self._target.append(record.getMessage())
        except Exception:  # noqa: BLE001
            pass  # never let logging machinery crash the pipeline


# ── GeoJSON parsing ───────────────────────────────────────────────────────────


def parse_site_geojson(text: str | None) -> str | None:
    """Parse user-supplied GeoJSON text and write it to a temporary file.

    Accepts:
    - A FeatureCollection with a feature having properties.kind == "site_boundary"
    - A bare {"type": "Polygon", ...} geometry — wrapped into a minimal FeatureCollection

    On valid input: writes a temp .geojson and returns its path string.
    On invalid/empty input: returns None.

    SECURITY: uses json.loads ONLY — never eval or exec (T-03-01).

    Args:
        text: GeoJSON string from the user. None or empty returns None.

    Returns:
        Path string to a temporary .geojson file, or None if invalid/empty.

    Raises:
        ValueError: with a short human-readable message for truly unparseable input
                    so the caller can convert it to the error field.
    """
    if not text or not text.strip():
        return None

    try:
        data = json.loads(text)  # ONLY safe parse — NEVER eval/exec (T-03-01)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("GeoJSON must be a JSON object (dict)")

    geojson_type = data.get("type")

    if geojson_type == "FeatureCollection":
        # Validate that at least one feature has kind == "site_boundary"
        features = data.get("features", [])
        has_boundary = any(
            f.get("properties", {}).get("kind") == "site_boundary"
            for f in features
            if isinstance(f, dict)
        )
        if not has_boundary:
            raise ValueError(
                "GeoJSON FeatureCollection has no feature with properties.kind='site_boundary'"
            )
        fc = data

    elif geojson_type == "Polygon":
        # Wrap bare Polygon into a minimal FeatureCollection
        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "kind": "site_boundary",
                        "name": "User-supplied site boundary",
                        "note": "Wrapped from bare Polygon by app_pipeline.parse_site_geojson",
                    },
                    "geometry": data,
                }
            ],
        }

    else:
        raise ValueError(
            f"Unsupported GeoJSON type {geojson_type!r}. "
            "Expected 'FeatureCollection' or 'Polygon'."
        )

    # Write to a temp file; caller is responsible for cleanup if desired
    tmp = tempfile.NamedTemporaryFile(
        suffix=".geojson", mode="w", encoding="utf-8", delete=False
    )
    try:
        json.dump(fc, tmp, ensure_ascii=False)
        tmp.flush()
        return tmp.name
    finally:
        tmp.close()


# ── Pipeline ──────────────────────────────────────────────────────────────────


def run_decision(
    budget_eur: float = DEFAULT_BUDGET_EUR,
    weights: tuple[float, float] = (0.6, 0.4),
    geojson_text: str | None = None,
    backend: str = "mock",
    cost_table: "CostTable | None" = None,
    growth_discount: "GrowthDiscountParams | None" = None,
    center_lonlat: tuple[float, float] | None = None,
    site_size_m: float = 120.0,
) -> dict:
    """Drive the full CoolSpend pipeline and return a structured result dict.

    Pipeline: optimize (NSGA-II) -> validate Top-3 (mock/live) -> TOPSIS rank

    Args:
        budget_eur:       Planting budget in EUR (default: 1 000 000).
        weights:          TOPSIS weight tuple (w_thermal, w_ecological). These are
                          user-adjustable sliders per CONCERNS 1.6 / APP-01 — not
                          calibrated constants.
        geojson_text:     Optional GeoJSON string from user UI. None -> use default
                          bundled site fixture (angels_site.geojson).
        backend:          "mock" | "cached" | "live". Sets INFRARED_BACKEND env var
                          for the duration of this call only. Never reads/sets
                          INFRARED_API_KEY (T-03-03).
        cost_table:       Optional edited CostTable (COST-04 / D-05). When supplied,
                          the cost_per_utci_degree KPI is recomputed using this table
                          after TOPSIS rank. When None, falls back to DEFAULT_COST_TABLE.
        growth_discount:  Optional edited GrowthDiscountParams (COST-05 / D-07..D-09).
                          When supplied, the KPI is recomputed with these params.
                          When None, falls back to DEFAULT_GROWTH_DISCOUNT.

    Returns:
        {
          "configurations":  list[dict],   # ranked Top-3 from topsis_rank()
          "before_after":    dict,          # baseline/chosen/headline_delta_utci_c
          "headline":        str,           # human summary string
          "backend":         str,           # backend used ("mock"|"cached"|"live")
          "disclaimer":      str,           # honesty notice (NOT MEASURED DATA for mock)
          "call_log":        list[str],     # all SDK calls captured during this run
          "site_path":       str | None,    # path used for load_site (None = default)
          "error":           str | None,    # set iff pipeline failed; configs=[] then
        }

    Security:
        - T-03-01: GeoJSON parsed via json.loads only (no eval)
        - T-03-02: SimBudget(max_live_calls=3) caps live Infrared calls
        - T-03-03: INFRARED_API_KEY never accessed here
    """
    call_log: list[str] = []
    site_path: str | None = None

    # ── Step 0: Parse GeoJSON (if supplied) ──────────────────────────────────
    geojson_error: str | None = None
    if geojson_text is not None:
        try:
            site_path = parse_site_geojson(geojson_text)
        except ValueError as exc:
            geojson_error = str(exc)
        except Exception as exc:  # noqa: BLE001
            geojson_error = f"GeoJSON parse error: {exc}"

        if geojson_error is not None:
            return {
                "configurations": [],
                "before_after": {},
                "headline": "",
                "backend": backend,
                "disclaimer": "",
                "call_log": [],
                "site_path": None,
                "error": geojson_error,
            }

    # ── Step 1: Attach SDK call-log capture handler ──────────────────────────
    # SimBudget.record() logs at INFO level. The sdk_client logger inherits
    # from the root logger whose effective level may be WARNING (common default).
    # We temporarily lower sdk_logger's level to INFO so records propagate to
    # our capture handler, then restore the original level in the finally block.
    sdk_logger = logging.getLogger("coolspend.sdk_client")
    prior_sdk_level = sdk_logger.level   # may be NOTSET (0) — restore exactly
    sdk_logger.setLevel(logging.INFO)
    capture_handler = _CaptureHandler(call_log)
    sdk_logger.addHandler(capture_handler)

    # ── Step 2: Flip INFRARED_BACKEND for the duration of this call ──────────
    prior_backend = os.environ.get("INFRARED_BACKEND")
    os.environ["INFRARED_BACKEND"] = backend

    try:
        return _run_pipeline(
            budget_eur=budget_eur,
            weights=weights,
            site_path=site_path,
            backend=backend,
            call_log=call_log,
            cost_table=cost_table,
            growth_discount=growth_discount,
            center_lonlat=center_lonlat,
            site_size_m=site_size_m,
        )
    finally:
        # Always remove capture handler and restore logger level + env regardless of outcome
        sdk_logger.removeHandler(capture_handler)
        sdk_logger.setLevel(prior_sdk_level)  # restore (may set back to NOTSET)
        if prior_backend is None:
            os.environ.pop("INFRARED_BACKEND", None)
        else:
            os.environ["INFRARED_BACKEND"] = prior_backend
        # Reset per-site origin + active-site override so an "anywhere" run (either a
        # center+size scan or a drawn-polygon run) does not leak its frame into a
        # later default-site run in the same process.
        if center_lonlat is not None or site_path is not None:
            from coolspend.spatial_engine import reset_site_origin  # noqa: PLC0415
            reset_site_origin()


def _run_pipeline(
    budget_eur: float,
    weights: tuple[float, float],
    site_path: str | None,
    backend: str,
    call_log: list[str],
    cost_table: "CostTable | None" = None,
    growth_discount: "GrowthDiscountParams | None" = None,
    center_lonlat: tuple[float, float] | None = None,
    site_size_m: float = 120.0,
) -> dict:
    """Internal pipeline runner. Wrapped in try/except by run_decision caller.

    Returns the structured result dict on success, or an error dict on failure.
    Never raises (all exceptions are caught and returned as error strings).
    """
    try:
        # Stage 0: retarget to ANY Barcelona location (center_lonlat = (lon, lat)).
        # Builds a metric-square site there and points the optimizer's local frame
        # at it (set_site_origin_from_polygon). This is the "scan anywhere" path —
        # no hardcoded site. When None, the default site origin is used.
        if center_lonlat is not None:
            from coolspend.spatial_engine import (  # noqa: PLC0415
                square_ring_lonlat,
                set_site_origin_from_polygon,
                set_active_site,
                open_square_site,
            )
            lon, lat = center_lonlat
            ring = square_ring_lonlat(lon, lat, site_size_m)
            w, d = set_site_origin_from_polygon([(p[0], p[1]) for p in ring])
            # Use an open-ground site so is_valid_location does NOT reload the
            # bundled default fixture (which would clobber this origin).
            set_active_site(open_square_site(w, d))
        elif site_path is not None:
            # Drawn-polygon path (geojson_text): size the optimizer frame to the
            # user's ACTUAL polygon. FIX: site_path was previously parsed but never
            # loaded, so SITE_WIDTH/DEPTH stayed at the default → n_trees_for_site
            # floored at _MIN_N_TREES (12) regardless of drawn area, the budget
            # never bound, and the surrogate fell back to the default site frame.
            from shapely.geometry import Polygon  # noqa: PLC0415
            from coolspend.spatial_engine import (  # noqa: PLC0415
                set_site_origin_from_polygon,
                set_active_site,
                latlon_to_local_m,
            )
            with open(site_path, encoding="utf-8") as _fh:
                _fc = json.loads(_fh.read())
            _feats = _fc.get("features", [])
            _poly = next(
                (f for f in _feats if f.get("geometry", {}).get("type") == "Polygon"),
                _feats[0] if _feats else None,
            )
            ring_ll = _poly["geometry"]["coordinates"][0]
            set_site_origin_from_polygon([(p[0], p[1]) for p in ring_ll])
            # Use the REAL drawn shape as the active boundary (not just its bbox) so
            # is_valid_location rejects slots outside the polygon. Buildings/streets
            # are empty here; the LIVE Infrared UTCI run still uses the real fetched
            # buildings, so measured cooling reflects true geometry.
            local_ring = [latlon_to_local_m(p[0], p[1]) for p in ring_ll]
            set_active_site({"boundary": Polygon(local_ring), "buildings": [], "streets": []})

        # Stage 1: NSGA-II on surrogate (seed 42, zero live SDK calls)
        result = run_optimisation(budget_eur=budget_eur)

        # Stage 2: Select Top-3 Pareto representatives
        top3 = select_top3(result)

        # Stage 3: Validate Top-3 with Infrared SDK (SimBudget-capped at 3 calls)
        budget = SimBudget(max_live_calls=3)
        top3 = validate_top3_with_infrared(top3, budget=budget)

        # Stage 4: TOPSIS rank by EUR/degC KPI
        top3 = topsis_rank(top3, weights=weights)

        # Stage 4b: Recompute cost_per_utci_degree with edited cost_table + growth_discount
        # (COST-04 / D-05 / D-06): when the user edits cost line items or growth/discount
        # params via Gradio, we overwrite each config's KPI dict with the recomputed values.
        # When both are None, behavior is unchanged (shipped defaults used everywhere).
        if cost_table is not None or growth_discount is not None:
            for cfg in top3:
                cfg["cost_per_utci_degree"] = cost_per_utci_degree(
                    cfg,
                    cost_table=cost_table,
                    growth_discount=growth_discount,
                )

        # Stage 4c: Capture WGS84 geometry in the CURRENT site frame (before any
        # post-run origin reset) so the result is self-contained for the map UI,
        # the live validation, and reproducibility. site_polygon_lonlat = the scanned
        # site boundary; each config gains trees_lonlat (per-tree lon/lat + species).
        from coolspend.optimizer import _config_to_geometry  # noqa: PLC0415
        site_polygon_lonlat = None
        for cfg in top3:
            geom = _config_to_geometry(cfg)
            cfg["trees_lonlat"] = geom["trees_lonlat"]
            site_polygon_lonlat = geom["polygon_lonlat"]

        # Stage 5: Build structured result
        rank1 = top3[0]  # best EUR/degC after topsis_rank

        before_after = _build_before_after(rank1)
        headline = _build_headline(rank1, before_after)
        disclaimer = _build_disclaimer(rank1, backend)

        # Measured existing-canopy context (ICGC+CREAF LiDAR) for an anywhere-run.
        # auto_download=False: never trigger the 166 MB raster fetch mid-pipeline —
        # use it only if already cached locally; otherwise degrade to None. Graceful.
        measured_site_canopy = None
        if center_lonlat is not None:
            try:
                from coolspend.bcn_lidar import canopy_height_m, ATTRIBUTION  # noqa: PLC0415
                lon, lat = center_lonlat
                h = canopy_height_m(lon, lat, auto_download=False)
                measured_site_canopy = {
                    "measured_canopy_height_m": h,
                    "interpretation": (
                        "no measured tree canopy at this 20 m cell (bare / high planting opportunity)"
                        if h is None else f"existing measured canopy ~{h:.0f} m at this locale"
                    ),
                    "source": ATTRIBUTION,
                }
            except Exception:  # noqa: BLE001 — optional context, never break the run
                measured_site_canopy = None

        from coolspend.spatial_engine import SITE_WIDTH_M, SITE_DEPTH_M  # noqa: PLC0415
        return {
            "configurations": top3,
            "before_after": before_after,
            "headline": headline,
            "backend": backend,
            "disclaimer": disclaimer,
            "call_log": list(call_log),  # snapshot of captured log entries
            "site_path": site_path,
            "site_polygon_lonlat": site_polygon_lonlat,
            "site_width_m": SITE_WIDTH_M,
            "site_depth_m": SITE_DEPTH_M,
            "center_lonlat": center_lonlat,
            "measured_site_canopy": measured_site_canopy,
            "error": None,
        }

    except Exception as exc:  # noqa: BLE001
        logger.exception("run_decision pipeline failed: %s", exc)
        return {
            "configurations": [],
            "before_after": {},
            "headline": "",
            "backend": backend,
            "disclaimer": "",
            "call_log": list(call_log),
            "site_path": site_path,
            # Keep the same keys as the success dict so consumers don't KeyError on
            # the error path (they currently use .get(), but shape parity is safer).
            "site_polygon_lonlat": None,
            "site_width_m": None,
            "site_depth_m": None,
            "center_lonlat": center_lonlat,
            "measured_site_canopy": None,
            "error": f"Pipeline error: {exc}",
        }


# ── Result builders ───────────────────────────────────────────────────────────


def _build_before_after(rank1: dict) -> dict:
    """Build the before/after comparison dict from the rank-1 config.

    All values read directly from validated config fields — nothing fabricated.
    """
    cooled = rank1.get("cooled_footprint_m2")
    cost_eur = rank1.get("cost_eur") or 0.0
    eur_per_m2_cooled = (
        round(cost_eur / cooled, 1) if cooled else None
    )
    return {
        "baseline_utci_c": rank1.get("baseline_utci_c"),
        "chosen_label": rank1.get("label"),
        "chosen_validated_utci_c": rank1.get("validated_utci_c"),
        "headline_delta_utci_c": rank1.get("delta_utci_c"),
        # Peak felt-temp (p90 sun-exposed cells) — for the honest "feels-like" headline
        "baseline_utci_peak_c": rank1.get("baseline_utci_peak_c"),
        "chosen_validated_utci_peak_c": rank1.get("validated_utci_peak_c"),
        "headline_delta_utci_peak_c": rank1.get("delta_utci_peak_c"),
        "cooled_footprint_m2": cooled,
        "eur_per_m2_cooled": eur_per_m2_cooled,
        "heat_stress_area_removed_m2": rank1.get("heat_stress_area_removed_m2"),
        "source": rank1.get("validated_disclaimer", rank1.get("validated_backend", "")),
        "note": "before = baseline UTCI; after = rank-1 intervention validated UTCI; "
                "cooled_footprint_m2 = ground cooled >=0.5C (cell-wise grid diff)",
        # Full UTCI grids for heatmap visualisation (512×512, NaN-safe, None for mock)
        "baseline_utci_grid": rank1.get("baseline_utci_grid"),
        "intervention_utci_grid": rank1.get("intervention_utci_grid"),
    }


def _build_headline(rank1: dict, before_after: dict) -> str:
    """Build the human-readable headline string from rank-1 config.

    Format: "Spend EUR {cost:,.0f} -> cools the plaza {delta:.2f} degC -- plant these {n} locations."

    If cost_per_utci_degree value is None, notes KPI unavailable but still
    renders the delta + tree count. Does not fabricate any value.
    """
    cost_eur = rank1.get("cost_eur", 0.0) or 0.0
    delta = before_after.get("headline_delta_utci_c") or 0.0
    n = rank1.get("tree_count", 0)
    kpi = rank1.get("cost_per_utci_degree", {}).get("value")
    cooled = before_after.get("cooled_footprint_m2")
    eur_m2 = before_after.get("eur_per_m2_cooled")

    # Live runs lead with the cooled-footprint headline (real m² cooled per euro);
    # mock/scalar runs fall back to the site-mean delta phrasing.
    if cooled:
        base = (
            f"Spend EUR {cost_eur:,.0f} -> {n} trees cool {cooled:,.0f} m2 of ground "
            f"by >=0.5C (EUR {eur_m2:,.0f}/m2), validated by real Infrared UTCI."
        )
        # Add the felt-temperature clause at sun-exposed hotspots when available
        # (p90 cell, the honest "feels-like" peak — not the shade-diluted mean).
        peak_base = before_after.get("baseline_utci_peak_c")
        peak_int = before_after.get("chosen_validated_utci_peak_c")
        if peak_base is not None and peak_int is not None:
            base += (
                f" At sun-exposed spots the felt temperature drops "
                f"{peak_base:.1f}C -> {peak_int:.1f}C."
            )
        return base
    base = f"Spend EUR {cost_eur:,.0f} -> cools the plaza {delta:.2f} degC -- plant these {n} locations."
    if kpi is None:
        base += " (KPI unavailable: non-positive delta)"
    return base


def _build_disclaimer(rank1: dict, backend: str) -> str:
    """Build the honesty disclaimer for the run result.

    For mock backend: always includes "NOT MEASURED DATA" verbatim (APP-01).
    For live backend: uses the validated_disclaimer from the rank-1 config.
    """
    if backend == "mock":
        return (
            "NOT MEASURED DATA — results are synthetic mock values for UI integration only. "
            "SURROGATE-DERIVED delta_tmrt with ±4°C uncertainty. "
            "Use INFRARED_BACKEND=live with a real API key for measured UTCI."
        )
    return rank1.get("validated_disclaimer", f"Backend: {backend}")


# ── SMART EVALUATE (Mode 1 — greedy submodular placement + live validation) ─

def smart_evaluate(
    geojson_text: str,
    budget_eur: float = 1_000_000.0,
    backend: str = "live",
) -> dict:
    """Single-site smart-placement + live-validate pipeline (Mode 1).

    Replaces NSGA-II surrogate scatter for the drawn-polygon path:
      baseline UTCI grid → demand (hot × impervious × unshaded) →
      greedy weighted-max-coverage within €budget →
      live Infrared intervention UTCI → real ΔUTCI + €/m²-cooled headline.

    Returns the same dict shape as run_decision() so the web bundle / frontend
    consume it unchanged. The key difference: configurations[0] is the single
    greedily-optimal layout, not one of three NSGA-II picks.

    Args:
        geojson_text: bare Polygon or FeatureCollection (same as run_decision).
        budget_eur:   total tree + depave spend cap.
        backend:      "live" only (mock doesn't support real measured demand;
                      the demand field comes from live UTCI, and ground materials).

    Returns:
        Dict matching run_decision contract: {configurations, before_after, headline,
        backend, disclaimer, site_polygon_lonlat, site_width_m, site_depth_m, error}.
    """
    import json as _json  # noqa: PLC0415
    from coolspend.spatial_engine import (  # noqa: PLC0415
        reset_site_origin, SITE_WIDTH_M, SITE_DEPTH_M,
    )
    from coolspend.placement_inputs import run_smart_placement  # noqa: PLC0415
    from coolspend.sdk_client import get_baseline_utci, get_intervention_utci, UTCI_HEAT_STRESS_C  # noqa: PLC0415
    from coolspend.optimizer import _build_baseline_geometry  # noqa: PLC0415

    # Clean the frame so /api/buildings' priming can't leak in.
    reset_site_origin()

    # Parse the drawn polygon.
    data = _json.loads(geojson_text)
    if data.get("type") == "FeatureCollection":
        poly = next(
            f for f in data["features"]
            if f.get("geometry", {}).get("type") == "Polygon"
        )
        ring = poly["geometry"]["coordinates"][0]
    else:
        ring = data["coordinates"][0]
    ring = [[float(p[0]), float(p[1])] for p in ring]
    if ring[0] != ring[-1]:
        ring.append(ring[0])

    geometry = {"polygon_lonlat": ring}

    # Stage 1 — smart placement (live baseline UTCI → demand → greedy trees).
    placement = run_smart_placement(geometry, budget_eur=budget_eur, backend=backend)
    trees_lonlat = placement["trees_lonlat"]
    tree_count = placement["tree_count"]
    cost_eur = placement["cost_eur"]
    coverage_fraction = placement["coverage_fraction"]
    demand_total = placement["demand_total"]
    covered_weight = placement["covered_weight"]

    if not trees_lonlat:
        return {
            "configurations": [],
            "before_after": {},
            "headline": "No plantable spots found for this budget in this area.",
            "backend": backend,
            "disclaimer": "Smart placement: zero trees placed (budget or site constraints).",
            "site_polygon_lonlat": ring,
            "site_width_m": SITE_WIDTH_M, "site_depth_m": SITE_DEPTH_M,
            "center_lonlat": None,
            "error": "no plantable slots",
        }

    # Stage 2 — live-validate the placed layout with Infrared UTCI.
    baseline_geom = {"polygon_lonlat": ring}  # no trees
    intervention_geom = {"polygon_lonlat": ring, "trees_lonlat": trees_lonlat}
    baseline = get_baseline_utci(baseline_geom)
    intervention = get_intervention_utci(intervention_geom)

    delta_utci = round(baseline.utci_c - intervention.utci_c, 2)

    # Build configuration dict (single, not top-3 — this IS the optimal layout).
    cfg = {
        "rank": 1,
        "label": "SMART_PLACEMENT",
        "tree_count": tree_count,
        "trees_lonlat": trees_lonlat,
        "cost_eur": cost_eur,
        "coverage_fraction": coverage_fraction,
        "plantable_area_m2": placement.get("plantable_area_m2"),
        "delta_utci_c": delta_utci,
        "baseline_utci_c": baseline.utci_c,
        "baseline_utci_peak_c": baseline.utci_peak_c,
        "validated_utci_c": intervention.utci_c,
        "validated_utci_peak_c": intervention.utci_peak_c,
        "heat_stress_area_m2": intervention.heat_stress_area_m2,
        "cooled_footprint_m2": None,  # computed below
        "cost_per_utci_degree": None,  # computed below after cooled_footprint
        "validated_disclaimer": (
            (
                f"LIVE Infrared UTCI — {tree_count} greedily-placed trees; "
                if backend in ("live", "cached")
                else (
                    f"PREVIEW (synthetic UTCI, NOT MEASURED) — placement is real "
                    f"(building-/street-aware, spaced), cooling is estimated until run live. "
                    f"{tree_count} greedily-placed trees; "
                )
            )
            + "budgeted weighted-max-coverage (submodular, 1-1/e bounded). "
            "Every in-ground tree requires a pre-dig utility survey (underground mains not in open data)."
        ),
        "species": sorted(set(t["species"] for t in trees_lonlat)),
        "trees": [{"species": t["species"], "active": True, "mode": t.get("mode", "in_ground")} for t in trees_lonlat],
    }
    # Cooled footprint + depth profile — SAME canonical definitions as the NSGA-II
    # path (sdk_client): m² cooled by >=0.5 °C, plus the multi-threshold bands /
    # measured dispersion / heat-stress relief. None on mock/scalar (no grid).
    from coolspend.sdk_client import (  # noqa: PLC0415
        cooled_footprint_m2 as _cooled_m2, cooled_footprint_profile as _cooled_profile,
    )
    cfg["cooled_footprint_m2"] = _cooled_m2(baseline.merged_grid, intervention.merged_grid)
    cfg["cooled_profile"] = _cooled_profile(baseline.merged_grid, intervention.merged_grid)

    # KPI: € per m² of ground actually cooled below heat-stress (the headline metric).
    cooled = cfg.get("cooled_footprint_m2")
    eur_per_m2_validated = round(cost_eur / cooled, 1) if cooled else None
    cfg["cost_per_utci_degree"] = {
        "value": eur_per_m2_validated,
        "unit": "EUR / m²-cooled",
        "note": (
            f"€{cost_eur:,.0f} / {cooled} m² of ground cooled below "
            f">{UTCI_HEAT_STRESS_C}°C UTCI (was hot → now comfortable)"
        ),
    }

    headline = (
        f"Smart placement: {tree_count} trees, €{cost_eur:,.0f}, "
        f"{delta_utci:.2f} °C mean UTCI drop, "
        f"covers {coverage_fraction*100:.0f}% of hot-paved demand. "
        f"Every in-ground tree requires a utility survey."
    )

    return {
        "configurations": [cfg],
        "before_after": {
            "baseline_utci_c": baseline.utci_c,
            "baseline_utci_peak_c": baseline.utci_peak_c,
            "intervention_utci_c": intervention.utci_c,
            "intervention_utci_peak_c": intervention.utci_peak_c,
            "delta_utci_c": delta_utci,
            "baseline_utci_grid": baseline.merged_grid,
            "intervention_utci_grid": intervention.merged_grid,
            "heat_stress_area_m2": intervention.heat_stress_area_m2,
        },
        "headline": headline,
        "backend": backend,
        "disclaimer": cfg["validated_disclaimer"],
        "site_polygon_lonlat": ring,
        "site_width_m": SITE_WIDTH_M,
        "site_depth_m": SITE_DEPTH_M,
        "center_lonlat": None,
        "error": None,
    }
