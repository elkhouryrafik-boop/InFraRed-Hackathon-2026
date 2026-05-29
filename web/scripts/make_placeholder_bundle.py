"""Generate a realistic PLACEHOLDER web_bundle so the app runs standalone.

The real bundle is produced by the project's Python exporter into
outputs/web_bundle/ and copied to web/public/web_bundle/. This script only
makes dev placeholders near Barcelona Eixample (2.1649, 41.3915).

Run:  python web/scripts/make_placeholder_bundle.py
"""
from __future__ import annotations

import json
import math
import os
import random

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "public", "web_bundle"))
os.makedirs(OUT, exist_ok=True)

# Site: a ~220 m square block in the Eixample grid.
CENTER_LON, CENTER_LAT = 2.1649, 41.3915
SITE_SIZE_M = 220.0

# metres -> degrees at this latitude
M_PER_DEG_LAT = 111_320.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(CENTER_LAT))

half_lon = (SITE_SIZE_M / 2) / M_PER_DEG_LON
half_lat = (SITE_SIZE_M / 2) / M_PER_DEG_LAT

WEST, EAST = CENTER_LON - half_lon, CENTER_LON + half_lon
SOUTH, NORTH = CENTER_LAT - half_lat, CENTER_LAT + half_lat


# ── UTCI colour ramp (mirrors src/lib/colorscale.ts) ────────────────────────
STOPS = [
    (18, (49, 54, 149)),
    (26, (69, 117, 180)),
    (32, (254, 224, 144)),
    (38, (253, 141, 60)),
    (46, (215, 48, 39)),
]


def utci_color(v: float) -> tuple[int, int, int]:
    v = max(STOPS[0][0], min(STOPS[-1][0], v))
    for (lo_v, lo_c), (hi_v, hi_c) in zip(STOPS, STOPS[1:]):
        if lo_v <= v <= hi_v:
            t = 0 if hi_v == lo_v else (v - lo_v) / (hi_v - lo_v)
            return tuple(int(round(a + (b - a) * t)) for a, b in zip(lo_c, hi_c))
    return STOPS[-1][1]


def render_utci(field: np.ndarray, path: str) -> None:
    h, w = field.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            r, g, b = utci_color(float(field[y, x]))
            rgba[y, x] = (r, g, b, 235)
    Image.fromarray(rgba, "RGBA").save(path)


def build_fields(size: int = 96):
    """Baseline = hot block; intervention = cooled patches under tree clusters."""
    ys, xs = np.mgrid[0:size, 0:size]
    cx = cy = size / 2
    # Hot core, cooler at edges (open streets).
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / (size / 2)
    baseline = 41.5 - 4.5 * dist  # 41.5 core -> ~37 edge
    baseline += np.random.RandomState(7).normal(0, 0.4, baseline.shape)

    # Intervention: subtract cooling bubbles around a few tree clusters.
    intervention = baseline.copy()
    rng = np.random.RandomState(11)
    for _ in range(7):
        tx, ty = rng.uniform(0.2, 0.8, 2) * size
        rr = np.sqrt((xs - tx) ** 2 + (ys - ty) ** 2)
        intervention -= 4.0 * np.exp(-(rr ** 2) / (2 * (size * 0.12) ** 2))
    intervention = np.clip(intervention, 24, 46)
    baseline = np.clip(baseline, 24, 46)
    return baseline, intervention


# ── Trees: a grid of proposed + a few existing, with per-species colour ─────
SPECIES = [
    ("Platanus x acerifolia", (60, 150, 70), 9.0, 14.0),
    ("Celtis australis", (88, 168, 96), 7.5, 11.0),
    ("Tilia tomentosa", (74, 158, 104), 8.0, 12.0),
    ("Jacaranda mimosifolia", (120, 150, 200), 6.5, 9.0),
]


def build_trees() -> dict:
    feats = []
    rng = random.Random(42)
    # Proposed: planted along an inner grid.
    n = 6
    for i in range(n):
        for j in range(n):
            lon = WEST + half_lon * 0.4 + (EAST - WEST) * 0.6 * (i / (n - 1))
            lat = SOUTH + half_lat * 0.4 + (NORTH - SOUTH) * 0.6 * (j / (n - 1))
            lon += rng.uniform(-1, 1) * half_lon * 0.05
            lat += rng.uniform(-1, 1) * half_lat * 0.05
            name, color, crown, height = rng.choice(SPECIES)
            feats.append({
                "type": "Feature",
                "properties": {
                    "kind": "proposed",
                    "species": name,
                    "crown_diameter_m": round(crown + rng.uniform(-1, 1), 1),
                    "height_m": round(height + rng.uniform(-2, 2), 1),
                    "color": list(color),
                },
                "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            })
    # A handful of existing trees near the edges.
    for _ in range(8):
        lon = rng.uniform(WEST, EAST)
        lat = rng.uniform(SOUTH, NORTH)
        feats.append({
            "type": "Feature",
            "properties": {
                "kind": "existing",
                "species": "Existing street tree",
                "crown_diameter_m": round(rng.uniform(4, 7), 1),
                "height_m": round(rng.uniform(6, 10), 1),
                "color": [115, 140, 107],
            },
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
        })
    return {"type": "FeatureCollection", "features": feats}


def main() -> None:
    np.random.seed(7)

    # decision.json
    decision = {
        "headline": "128 trees cool 12,450 m² of street for €96k",
        "backend": "Infrared SDK · UTCI thermal comfort (GPU) · placeholder data",
        "disclaimer": (
            "Placeholder dev data near Barcelona Eixample. Real results are "
            "produced by the Python exporter (outputs/web_bundle/) and copied "
            "into web/public/web_bundle/. UTCI from Infrared SDK simulation."
        ),
        "budget_eur": 100000,
        "site_center_lonlat": [CENTER_LON, CENTER_LAT],
        "site_size_m": SITE_SIZE_M,
        "generated_at": "2026-05-29T00:00:00Z",
        "configurations": [
            {
                "rank": 1,
                "label": "Balanced canopy",
                "tree_count": 128,
                "cost_eur": 96000,
                "cooled_footprint_m2": 12450,
                "eur_per_m2": 7.71,
                "delta_utci_c": -2.4,
                "utci_baseline_mean": 33.1,
                "utci_baseline_peak": 41.2,
                "utci_intervention_mean": 30.7,
                "utci_intervention_peak": 38.8,
                "species": ["Platanus x acerifolia", "Celtis australis", "Tilia tomentosa"],
            },
            {
                "rank": 2,
                "label": "Max shade",
                "tree_count": 156,
                "cost_eur": 99500,
                "cooled_footprint_m2": 13980,
                "eur_per_m2": 7.12,
                "delta_utci_c": -2.9,
                "utci_baseline_mean": 33.1,
                "utci_baseline_peak": 41.2,
                "utci_intervention_mean": 30.0,
                "utci_intervention_peak": 38.3,
                "species": ["Platanus x acerifolia", "Tilia tomentosa"],
            },
            {
                "rank": 3,
                "label": "Budget canopy",
                "tree_count": 84,
                "cost_eur": 63000,
                "cooled_footprint_m2": 8700,
                "eur_per_m2": 7.24,
                "delta_utci_c": -1.7,
                "utci_baseline_mean": 33.1,
                "utci_baseline_peak": 41.2,
                "utci_intervention_mean": 31.6,
                "utci_intervention_peak": 39.5,
                "species": ["Celtis australis", "Jacaranda mimosifolia"],
            },
        ],
    }
    with open(os.path.join(OUT, "decision.json"), "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2)

    # boundary.geojson (closed ring, [lon,lat])
    ring = [
        [WEST, SOUTH], [EAST, SOUTH], [EAST, NORTH], [WEST, NORTH], [WEST, SOUTH],
    ]
    boundary = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"kind": "site_boundary"},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        ],
    }
    with open(os.path.join(OUT, "boundary.geojson"), "w", encoding="utf-8") as f:
        json.dump(boundary, f, indent=2)

    # trees.geojson
    with open(os.path.join(OUT, "trees.geojson"), "w", encoding="utf-8") as f:
        json.dump(build_trees(), f, indent=2)

    # bounds.json
    bounds = {"west": WEST, "south": SOUTH, "east": EAST, "north": NORTH}
    with open(os.path.join(OUT, "bounds.json"), "w", encoding="utf-8") as f:
        json.dump(bounds, f, indent=2)

    # UTCI PNGs
    baseline, intervention = build_fields()
    render_utci(baseline, os.path.join(OUT, "utci_baseline.png"))
    render_utci(intervention, os.path.join(OUT, "utci_intervention.png"))

    print(f"Wrote placeholder bundle to {OUT}")
    for name in sorted(os.listdir(OUT)):
        print("  ", name)


if __name__ == "__main__":
    main()
