"""
coolspend/app_viz.py — Before/after site visualization with real UTCI heatmaps.

Renders:
  1. BEFORE panel: site geometry + baseline UTCI heatmap overlay
  2. AFTER panel:  site geometry + intervention UTCI heatmap + tree placements
  3. DIFF panel:   cooling map (baseline − intervention) cell by cell

Public API:
  render_before_after(config, before_after, site_path=None, out_path=None) -> str
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from coolspend.spatial_engine import load_site, SITE_WIDTH_M, SITE_DEPTH_M

# Per-species color palette (deterministic, colorblind-friendly)
_SPECIES_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78",
]

# UTCI colormap range
_UTCI_VMIN, _UTCI_VMAX = 24.0, 32.0


def _draw_site(ax, site: dict) -> None:
    """Draw site geometry: boundary outline, buildings (grey fill), streets (dashed)."""
    boundary = site.get("boundary")
    if boundary is not None:
        bx, by = boundary.exterior.xy
        ax.plot(bx, by, color="black", linewidth=1.5, zorder=10)

    for building in site.get("buildings", []):
        bx, by = building.exterior.xy
        ax.fill(bx, by, color="#999999", alpha=0.5, zorder=3)
        ax.plot(bx, by, color="#555555", linewidth=0.8, zorder=3)

    for street in site.get("streets", []):
        sx, sy = street.xy
        ax.plot(sx, sy, color="#e07b20", linewidth=1.2, linestyle="--", alpha=0.7, zorder=2)


def _render_utci_heatmap(ax, grid: list | None, width_m: float, depth_m: float) -> None:
    """Render a UTCI grid as a heatmap on the given axes.

    Grid is [rows, cols] with rows = north→south, cols = west→east.
    NaN cells (outside polygon) are left transparent.
    """
    if grid is None:
        return
    arr = np.asarray(grid, dtype=float)
    rows, cols = arr.shape
    # imshow origin='upper' → row 0 at top (north)
    im = ax.imshow(
        arr,
        extent=[0, width_m, 0, depth_m],
        origin="upper",
        cmap="RdYlBu_r",
        vmin=_UTCI_VMIN,
        vmax=_UTCI_VMAX,
        alpha=0.85,
        zorder=1,
        aspect="auto",
    )
    return im


def _render_cooling_diff(ax, baseline_grid, intervention_grid, width_m, depth_m):
    """Render cell-wise cooling (baseline − intervention) as a heatmap.

    Blue = strong cooling. White = no change. NaN = outside polygon.
    """
    if baseline_grid is None or intervention_grid is None:
        return None
    b = np.asarray(baseline_grid, dtype=float)
    i = np.asarray(intervention_grid, dtype=float)
    if b.shape != i.shape:
        return None
    diff = b - i  # positive = cooling
    # Mask NaN
    diff_masked = np.ma.masked_where(np.isnan(diff), diff)
    im = ax.imshow(
        diff_masked,
        extent=[0, width_m, 0, depth_m],
        origin="upper",
        cmap="Blues",
        vmin=0.0,
        vmax=max(2.0, float(np.nanmax(diff))),
        alpha=0.85,
        zorder=1,
        aspect="auto",
    )
    return im


def _draw_trees(ax, active_trees: list[dict]) -> None:
    """Draw tree canopy circles at true crown diameter with species-colored markers."""
    if not active_trees:
        return

    species_list = sorted(set(t.get("species", "?") for t in active_trees))
    sp_color_map = {}
    for i, sp_name in enumerate(species_list):
        sp_color_map[sp_name] = _SPECIES_COLORS[i % len(_SPECIES_COLORS)]

    for sp_name in species_list:
        sp_trees = [t for t in active_trees if t.get("species") == sp_name]
        xs = [t["x_m"] for t in sp_trees]
        ys = [t["y_m"] for t in sp_trees]
        # Crown radius → marker size (s = area in points², rough scaling)
        radii = [t.get("crown_diameter_m", 6.0) / 2.0 for t in sp_trees]
        sizes = [max((r / 0.12) ** 2, 20) for r in radii]

        parts = sp_name.split()
        label = "".join(p[:3] for p in parts) if parts else sp_name[:6]

        ax.scatter(
            xs, ys,
            c=sp_color_map[sp_name],
            s=sizes,
            marker="o",
            zorder=5,
            label=label,
            edgecolors="#333333",
            linewidths=0.6,
            alpha=0.85,
        )
    ax.legend(loc="lower right", fontsize=6, title="species", title_fontsize=7,
              framealpha=0.8)


# ── Public API ────────────────────────────────────────────────────────────────


def render_before_after(
    config: dict,
    before_after: dict,
    site_path: str | None = None,
    out_path: str | None = None,
) -> str:
    """Render a 3-panel before/after/diff site plot with UTCI heatmaps.

    Panels:
      LEFT   "BEFORE — baseline {utci:.1f} °C"
             Site geometry + baseline UTCI heatmap
      CENTER "AFTER — {utci:.1f} °C"
             Intervention UTCI heatmap + tree canopy markers
      RIGHT  "COOLING DIFF"
             Cell-wise baseline − intervention (blue = cooler)

    Args:
        config:       Rank-1 tree config dict with "trees" list.
        before_after: Dict from run_decision["before_after"]. May contain
                      "baseline_utci_grid" and "intervention_utci_grid".
        site_path:    Optional path to site GeoJSON. Falls back to default.
        out_path:     Optional output PNG path. Temp file if None.

    Returns:
        Absolute path to the written PNG file.
    """
    site = _load_site_safe(site_path)

    if out_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        out_path = tmp.name
    out_path = str(out_path)

    baseline_utci = before_after.get("baseline_utci_c") or 0.0
    after_utci = before_after.get("chosen_validated_utci_c") or 0.0
    headline_delta = before_after.get("headline_delta_utci_c") or 0.0

    validated_backend = config.get("validated_backend", "mock")
    validated_disclaimer = config.get(
        "validated_disclaimer", "NOT MEASURED DATA — synthetic mock value."
    )

    if validated_backend == "mock":
        honesty_text = f"NOT MEASURED DATA — {validated_disclaimer}"
    else:
        honesty_text = validated_disclaimer

    active_trees = [
        t for t in config.get("trees", [])
        if t.get("active", True)
    ]

    # Grids for heatmap rendering
    baseline_grid = before_after.get("baseline_utci_grid")
    intervention_grid = before_after.get("intervention_utci_grid")
    has_grids = baseline_grid is not None and intervention_grid is not None

    # ── Build figure: 3 panels ──────────────────────────────────────────────
    if has_grids:
        fig, (ax_before, ax_after, ax_diff) = plt.subplots(1, 3, figsize=(17, 5))
    else:
        fig, (ax_before, ax_after) = plt.subplots(1, 2, figsize=(11, 5))
        ax_diff = None

    # ── LEFT: BEFORE ────────────────────────────────────────────────────────
    if has_grids:
        _render_utci_heatmap(ax_before, baseline_grid, SITE_WIDTH_M, SITE_DEPTH_M)
    _draw_site(ax_before, site)
    ax_before.set_title(
        f"BEFORE\nbaseline {baseline_utci:.1f} °C",
        fontsize=10, pad=6,
    )
    ax_before.set_xlim(0, SITE_WIDTH_M)
    ax_before.set_ylim(0, SITE_DEPTH_M)
    ax_before.set_aspect("equal")
    ax_before.set_xlabel("x_m (East-West)")
    ax_before.set_ylabel("y_m (North-South)")

    # ── CENTER: AFTER ───────────────────────────────────────────────────────
    if has_grids:
        _render_utci_heatmap(ax_after, intervention_grid, SITE_WIDTH_M, SITE_DEPTH_M)
    _draw_site(ax_after, site)
    _draw_trees(ax_after, active_trees)

    cooled = before_after.get("cooled_footprint_m2")
    eur_m2 = before_after.get("eur_per_m2_cooled")
    if cooled:
        annotation = f"{cooled:,.0f} m² cooled ≥0.5°C"
        if eur_m2 is not None:
            annotation += f" (EUR {eur_m2:,.0f}/m²)"
        ax_after.text(
            0.02, 0.98, annotation,
            transform=ax_after.transAxes,
            fontsize=7, verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85),
        )

    ax_after.set_title(
        f"AFTER\n{after_utci:.1f} °C",
        fontsize=10, pad=6,
    )
    ax_after.set_xlim(0, SITE_WIDTH_M)
    ax_after.set_ylim(0, SITE_DEPTH_M)
    ax_after.set_aspect("equal")
    ax_after.set_xlabel("x_m (East-West)")

    # ── RIGHT: COOLING DIFF ─────────────────────────────────────────────────
    if ax_diff is not None and has_grids:
        im = _render_cooling_diff(
            ax_diff, baseline_grid, intervention_grid,
            SITE_WIDTH_M, SITE_DEPTH_M,
        )
        _draw_site(ax_diff, site)
        _draw_trees(ax_diff, active_trees)
        if im is not None:
            cbar = fig.colorbar(im, ax=ax_diff, fraction=0.046, pad=0.04)
            cbar.set_label("Cooling (°C)", fontsize=7)
        ax_diff.set_title(
            f"COOLING\n{headline_delta:.2f} °C mean drop",
            fontsize=10, pad=6,
        )
        ax_diff.set_xlim(0, SITE_WIDTH_M)
        ax_diff.set_ylim(0, SITE_DEPTH_M)
        ax_diff.set_aspect("equal")
        ax_diff.set_xlabel("x_m (East-West)")

    # ── Figure-level annotations ────────────────────────────────────────────
    fig.suptitle(
        f"CoolSpend: {headline_delta:.2f} °C cooling from {len(active_trees)} trees",
        fontsize=13, fontweight="bold", y=1.01,
    )

    fig.text(
        0.5, -0.04,
        honesty_text,
        ha="center", va="top",
        fontsize=7, color="#aa3333", wrap=True,
    )

    fig.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)

    return str(out_path)


def _load_site_safe(site_path: str | None) -> dict:
    """Load site geometry, falling back to the default fixture on any failure."""
    if site_path is not None:
        try:
            return load_site(site_path)
        except Exception:
            pass
    return load_site()
