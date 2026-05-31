"""Provenance + reproducibility for the citywide heat-vulnerability grid.

PAPER Limitation #1 said the derivation of ``composite_score_B`` was external
and not reproducible from this codebase. That was too pessimistic. Each of the
494 cells in ``scored_grid.geojson`` stores its five sub-scores AND a per-cell
contribution breakdown, and a least-squares fit over all cells recovers a single
constant weight vector that reconstructs ``composite_score_B`` to floating-point
epsilon (R^2 = 1.0, max abs residual ~2e-16). So the COMPOSITE is exactly
reproducible in-repo; the only residual provenance gap is how each individual
sub-score was derived from raw satellite imagery (the SAR->sealed classifier,
the LST-anomaly baseline, the NDVI inversion).

This module is the executable record of that reproduction:
    * COMPOSITE_B_WEIGHTS  — the recovered global weights (documented, not magic).
    * SIGNAL_SOURCES       — each sub-score's remote-sensing origin + status.
    * reproduce_composite_b(props) — recompute B for one cell from its sub-scores.
    * verify_scored_grid()  — recompute B for ALL cells, return fidelity stats.

The weights are recoverable from the data alone (see verify_scored_grid's
``recovered_weights``); we hard-code them here as the documented contract and
let the verifier prove they still hold.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

# ── The reproduced composite ──────────────────────────────────────────────────
# composite_score_B = Σ wᵢ·sᵢ over the five sub-scores below. Recovered by
# least-squares over all 494 cells (exact: R²=1.0). Order matters — it matches
# SUBSCORE_KEYS.
SUBSCORE_KEYS: tuple[str, ...] = (
    "s1_sealed",         # Sentinel-1 SAR impervious/sealed fraction (0–1)
    "s2_lst_anomaly",    # Landsat thermal land-surface-temperature anomaly (rescaled 0–1)
    "s3_inverted_ndvi",  # Sentinel-2 (1 − NDVI): low-vegetation signal (0–1)
    "s4_mismatch",       # ecological/mycorrhizal species-mismatch sub-score (0–1)
    "prpi",              # planting-receptivity / permeability-potential index (0–1)
)

COMPOSITE_B_WEIGHTS: dict[str, float] = {
    "s1_sealed": 0.45,
    "s2_lst_anomaly": 0.20,
    "s3_inverted_ndvi": 0.15,
    "s4_mismatch": 0.05,
    "prpi": 0.15,
}
# Sanity: weights sum to 1.0 (a convex combination).
assert abs(sum(COMPOSITE_B_WEIGHTS.values()) - 1.0) < 1e-9


@dataclass(frozen=True)
class SignalSource:
    key: str
    weight: float
    sensor: str
    description: str
    status: str  # "reproduced" | "documented" | "residual-gap"


# Per-signal provenance. The COMPOSITE is reproduced exactly; the per-signal raw
# derivation from imagery is the residual gap honestly flagged in the datasheet.
SIGNAL_SOURCES: tuple[SignalSource, ...] = (
    SignalSource(
        "s1_sealed", 0.45, "Sentinel-1 C-band SAR",
        "Impervious/sealed-surface fraction. Dominant weight: hottest priority "
        "is hot AND paved.",
        "residual-gap",  # SAR→sealed classifier + training data live upstream
    ),
    SignalSource(
        "s2_lst_anomaly", 0.20, "Landsat 8/9 TIRS (thermal)",
        "Land-surface-temperature anomaly vs the city background, rescaled to 0–1.",
        "residual-gap",  # anomaly baseline definition lives upstream
    ),
    SignalSource(
        "s3_inverted_ndvi", 0.15, "Sentinel-2 MSI (optical)",
        "(1 − NDVI): low existing vegetation = higher need.",
        "documented",
    ),
    SignalSource(
        "s4_mismatch", 0.05, "Municipal inventory + ecology model",
        "Species/mycorrhizal mismatch sub-score (smallest weight).",
        "residual-gap",
    ),
    SignalSource(
        "prpi", 0.15, "Derived index",
        "Planting-receptivity / permeability-potential index.",
        "residual-gap",
    ),
)


def _scored_grid_path() -> str | None:
    """Locate scored_grid.geojson across known repo locations."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    candidates = [
        os.path.join(root, "L1_INGEST_data", "data_for_all", "scored_grid.geojson"),
        os.path.join(root, "web", "public", "scored_grid.geojson"),
        os.path.join(root, "web", "dist", "scored_grid.geojson"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def reproduce_composite_b(props: dict) -> float:
    """Recompute composite_score_B for one cell from its stored sub-scores.

    Returns Σ wᵢ·sᵢ. Equals the stored ``composite_score_B`` to float epsilon.
    """
    total = 0.0
    for key in SUBSCORE_KEYS:
        v = props.get(key)
        total += COMPOSITE_B_WEIGHTS[key] * (float(v) if v is not None else 0.0)
    return total


def verify_scored_grid(path: str | None = None) -> dict:
    """Recompute B for every cell; return fidelity stats + recovered weights.

    Proves the documented weights still reconstruct the published composite. If
    NumPy is available it also re-derives the weights by least squares (showing
    they are recoverable from the data, not asserted). Pure-Python fallback only
    reports the residual.
    """
    path = path or _scored_grid_path()
    if path is None:
        return {"available": False, "reason": "scored_grid.geojson not found"}

    with open(path, encoding="utf-8") as fh:
        feats = [f["properties"] for f in json.load(fh)["features"]]

    residuals = []
    for p in feats:
        b = p.get("composite_score_B")
        if b is None:
            continue
        residuals.append(abs(reproduce_composite_b(p) - float(b)))

    out: dict = {
        "available": True,
        "path": path,
        "n_cells": len(residuals),
        "max_abs_residual": max(residuals) if residuals else None,
        "mean_abs_residual": (sum(residuals) / len(residuals)) if residuals else None,
        "weights": dict(COMPOSITE_B_WEIGHTS),
    }

    try:
        import numpy as np  # noqa: PLC0415

        S = np.array(
            [[float(p.get(k) or 0.0) for k in SUBSCORE_KEYS] for p in feats]
        )
        B = np.array([float(p.get("composite_score_B") or 0.0) for p in feats])
        w_ls, *_ = np.linalg.lstsq(S, B, rcond=None)
        ss_res = float(np.sum((B - S @ w_ls) ** 2))
        ss_tot = float(np.sum((B - B.mean()) ** 2))
        out["recovered_weights"] = {
            k: round(float(w), 6) for k, w in zip(SUBSCORE_KEYS, w_ls)
        }
        out["r2"] = 1.0 - ss_res / ss_tot if ss_tot else None
    except ImportError:
        out["recovered_weights"] = None
        out["r2"] = None

    return out


if __name__ == "__main__":  # pragma: no cover
    import pprint

    pprint.pprint(verify_scored_grid())
