"""Cheapest real-UTCI proof: baseline (0 trees) vs exactly 1 tree, LIVE Infrared.

Validates the whole real-cooling path end-to-end and produces the measured
per-tree number. ~2 live sims. Loads .env so INFRARED_API_KEY is picked up.

Run: python tools/proof_one_tree.py
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
os.environ["INFRARED_BACKEND"] = "live"

import numpy as np

from coolspend import spatial_engine as se
from coolspend.sdk_client import (
    get_baseline_utci, get_intervention_utci, cooled_footprint_m2,
)
from coolspend.bcn_species import get_species
from coolspend.sites import default_site

# Locked hero site: Plaça dels Països Catalans (depavement hero — barren hot asphalt).
_S = default_site()
CENTER_LON, CENTER_LAT = _S.lon, _S.lat
SIDE_M = _S.side_m
SPECIES = "Platanus x acerifolia"  # Barcelona's #1 street tree


def main() -> None:
    if not os.environ.get("INFRARED_API_KEY"):
        raise SystemExit("INFRARED_API_KEY not loaded from .env")

    # Retarget the local frame to this real polygon.
    ring = se.square_ring_lonlat(CENTER_LON, CENTER_LAT, SIDE_M)
    w, d = se.set_site_origin_from_polygon([(p[0], p[1]) for p in ring])
    print(f"Site: {_S.name} ~{w:.0f}x{d:.0f} m  | species: {SPECIES}")

    polygon_lonlat = [list(se.local_m_to_latlon(x, y)) for x, y in
                      [(0, 0), (w, 0), (w, d), (0, d), (0, 0)]]

    # One tree dead-centre, on the open plaza.
    cx, cy = w / 2.0, d / 2.0
    lon, lat = se.local_m_to_latlon(cx, cy)
    sp = get_species(SPECIES)
    print(f"Tree crown {sp.crown_diameter_m} m, height {sp.height_m} m at plaza centre\n")

    baseline_geom = {
        "width_m": 0.0, "coverage_fraction": 0.0, "tree_count": 0,
        "polygon_lonlat": polygon_lonlat, "trees_lonlat": [],
    }
    one_tree_geom = {
        "width_m": sp.crown_diameter_m, "coverage_fraction": 0.0, "tree_count": 1,
        "polygon_lonlat": polygon_lonlat,
        "trees_lonlat": [{"lon": round(lon, 8), "lat": round(lat, 8), "species": SPECIES}],
    }

    t0 = time.perf_counter()
    print("Running baseline (0 trees) — live Infrared UTCI…")
    base = get_baseline_utci(baseline_geom)
    t1 = time.perf_counter()
    print(f"  baseline mean {base.utci_c} °C | peak(p90) {base.utci_peak_c} °C "
          f"| {base.grid_cells_total} cells | {t1 - t0:.0f}s\n")

    print("Running 1 tree — live Infrared UTCI…")
    one = get_intervention_utci(one_tree_geom)
    t2 = time.perf_counter()
    print(f"  1-tree   mean {one.utci_c} °C | peak(p90) {one.utci_peak_c} °C | {t2 - t1:.0f}s\n")

    b = np.asarray(base.merged_grid, dtype=float)
    i = np.asarray(one.merged_grid, dtype=float)
    drop = b - i
    cooled_m2 = cooled_footprint_m2(base.merged_grid, one.merged_grid)
    max_drop = float(np.nanmax(drop))
    mean_delta = round(base.utci_c - one.utci_c, 3)
    peak_delta = (round(base.utci_peak_c - one.utci_peak_c, 3)
                  if base.utci_peak_c and one.utci_peak_c else None)

    print("=" * 56)
    print("ONE TREE — MEASURED COOLING (live Infrared, Plaça dels Àngels)")
    print("=" * 56)
    print(f"  Site-mean cooling:        {mean_delta} °C")
    print(f"  Peak-cell (p90) cooling:  {peak_delta} °C")
    print(f"  Hottest-cell relief:      {max_drop:.2f} °C  (best under-canopy spot)")
    print(f"  Cooled footprint:         {cooled_m2:.0f} m² (cells cooled ≥0.5 °C)")
    print(f"  Sim latency:              baseline {t1 - t0:.0f}s, tree {t2 - t1:.0f}s")
    print("=" * 56)


if __name__ == "__main__":
    main()
