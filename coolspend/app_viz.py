"""
coolspend/app_viz.py — Before/after site visualization for CoolSpend.

Provides render_before_after() — a headless matplotlib figure showing baseline
vs. intervention UTCI side-by-side with site geometry and tree placements.

Key contracts:
  - Headless-safe: matplotlib "Agg" backend forced BEFORE pyplot import
  - Standalone: does NOT import app_pipeline (importable without pipeline)
  - Honest: displays "NOT MEASURED DATA" caption when config is mock-validated
  - Robust: falls back to default site fixture if site_path is missing/invalid
  - Deterministic axes: both panels use fixed [0, SITE_WIDTH_M] x [0, SITE_DEPTH_M]

Public API:
  render_before_after(config, before_after, site_path=None, out_path=None) -> str
"""
from __future__ import annotations

import tempfile
from pathlib import Path

# ── Headless matplotlib setup (MUST be before pyplot import) ──────────────────
# Force Agg backend before any pyplot import to ensure headless-safe rendering
# (HF Spaces, CI, test environments without a display).

import matplotlib
matplotlib.use("Agg")  # noqa: E402  (must precede pyplot import)

import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402

from coolspend.spatial_engine import load_site, SITE_WIDTH_M, SITE_DEPTH_M  # noqa: E402


# ── Private helpers ───────────────────────────────────────────────────────────


def _draw_site(ax, site: dict) -> None:
    """Draw site geometry on an axes: boundary outline, buildings (grey fill), streets (dashed).

    Args:
        ax:   matplotlib Axes object to draw on.
        site: Site dict from load_site() — keys: "boundary" (Polygon),
              "buildings" (list[Polygon]), "streets" (list[LineString]).
    """
    # Site boundary outline
    boundary = site.get("boundary")
    if boundary is not None:
        bx, by = boundary.exterior.xy
        ax.plot(bx, by, color="black", linewidth=1.5, zorder=2)

    # Building footprints — filled grey
    for building in site.get("buildings", []):
        bx, by = building.exterior.xy
        ax.fill(bx, by, color="#999999", alpha=0.5, zorder=3)
        ax.plot(bx, by, color="#555555", linewidth=0.8, zorder=3)

    # Street centerlines — dashed
    for street in site.get("streets", []):
        sx, sy = street.xy
        ax.plot(sx, sy, color="#e07b20", linewidth=1.2, linestyle="--", alpha=0.7, zorder=2)


# ── Public API ────────────────────────────────────────────────────────────────


def render_before_after(
    config: dict,
    before_after: dict,
    site_path: str | None = None,
    out_path: str | None = None,
) -> str:
    """Render a side-by-side before/after site plot and write it to a PNG file.

    The figure has two panels:
      LEFT  "BEFORE — baseline {baseline_utci_c:.1f} degC"
            Site geometry only (boundary, buildings, streets). No trees.
      RIGHT "AFTER — {chosen_validated_utci_c:.1f} degC"
            Site geometry + active trees from config["trees"] as green dots.

    A figure suptitle shows "Cooling: -{headline_delta_utci_c:.2f} degC".
    A honesty caption (fig.text) displays "NOT MEASURED DATA" when
    config.validated_backend is "mock", else the validated_disclaimer.

    Args:
        config:       Rank-1 tree config dict (from topsis_rank output). Must
                      contain "trees" list and optionally "validated_backend",
                      "validated_disclaimer".
        before_after: Dict from run_decision["before_after"] or _build_before_after.
                      Keys used: "baseline_utci_c", "chosen_validated_utci_c",
                      "headline_delta_utci_c".
        site_path:    Optional path to a site GeoJSON file. Falls back to the
                      default bundled fixture (angels_site.geojson) on failure.
        out_path:     Optional output path for the PNG. If None, a temporary file
                      is created and its path is returned.

    Returns:
        Absolute path string to the written PNG file.
    """
    # ── Load site geometry (with fallback) ────────────────────────────────────
    site = _load_site_safe(site_path)

    # ── Determine output path ─────────────────────────────────────────────────
    if out_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        out_path = tmp.name

    out_path = str(out_path)

    # ── Extract values from dicts ─────────────────────────────────────────────
    baseline_utci = before_after.get("baseline_utci_c") or 0.0
    after_utci = before_after.get("chosen_validated_utci_c") or 0.0
    headline_delta = before_after.get("headline_delta_utci_c") or 0.0

    validated_backend = config.get("validated_backend", "mock")
    validated_disclaimer = config.get(
        "validated_disclaimer", "NOT MEASURED DATA — synthetic mock value."
    )

    # Honesty caption: "NOT MEASURED DATA" for mock; validated_disclaimer for others
    if validated_backend == "mock":
        honesty_text = f"NOT MEASURED DATA — {validated_disclaimer}"
    else:
        honesty_text = validated_disclaimer

    # Active tree positions for the AFTER panel
    active_trees = [
        t for t in config.get("trees", [])
        if t.get("active", True)
    ]

    # ── Build figure ──────────────────────────────────────────────────────────
    fig, (ax_before, ax_after) = plt.subplots(1, 2, figsize=(11, 5))

    # ── LEFT panel: BEFORE ────────────────────────────────────────────────────
    _draw_site(ax_before, site)
    ax_before.set_title(
        f"BEFORE\nbaseline {baseline_utci:.1f} degC",
        fontsize=10,
        pad=6,
    )
    ax_before.set_xlim(0, SITE_WIDTH_M)
    ax_before.set_ylim(0, SITE_DEPTH_M)
    ax_before.set_aspect("equal")
    ax_before.set_xlabel("x_m (East-West)")
    ax_before.set_ylabel("y_m (North-South)")

    # ── RIGHT panel: AFTER ────────────────────────────────────────────────────
    _draw_site(ax_after, site)

    # Plot active trees as green dots
    if active_trees:
        tree_xs = [t["x_m"] for t in active_trees]
        tree_ys = [t["y_m"] for t in active_trees]
        ax_after.scatter(
            tree_xs, tree_ys,
            c="#2ecc40",
            s=80,
            marker="o",
            zorder=5,
            label=f"{len(active_trees)} trees",
            edgecolors="#1a7a28",
            linewidths=0.8,
        )
        ax_after.legend(loc="lower right", fontsize=8)

    ax_after.set_title(
        f"AFTER\n{after_utci:.1f} degC",
        fontsize=10,
        pad=6,
    )
    ax_after.set_xlim(0, SITE_WIDTH_M)
    ax_after.set_ylim(0, SITE_DEPTH_M)
    ax_after.set_aspect("equal")
    ax_after.set_xlabel("x_m (East-West)")

    # ── Figure-level annotations ──────────────────────────────────────────────
    # Suptitle: headline cooling delta
    fig.suptitle(
        f"Cooling: -{headline_delta:.2f} degC",
        fontsize=13,
        fontweight="bold",
        y=1.01,
    )

    # Honesty caption at bottom of figure
    fig.text(
        0.5, -0.04,
        honesty_text,
        ha="center",
        va="top",
        fontsize=7,
        color="#aa3333",
        wrap=True,
    )

    # ── Save and close ────────────────────────────────────────────────────────
    fig.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)

    return str(out_path)


# ── Internal helpers ──────────────────────────────────────────────────────────


def _load_site_safe(site_path: str | None) -> dict:
    """Load site geometry, falling back to the default fixture on any failure.

    Args:
        site_path: Optional path string. None -> default fixture.

    Returns:
        Site dict from load_site() — always returns a valid site dict.
    """
    if site_path is not None:
        try:
            return load_site(site_path)
        except Exception:  # noqa: BLE001
            # Any error (FileNotFoundError, RuntimeError, etc.) -> fall back to default
            pass

    # Default fallback: bundled angels_site.geojson
    return load_site()
