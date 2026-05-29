"""
coolspend/app_3d.py — 3D scene exporter for CoolSpend tree-budget results.

Generates .glb (glTF binary) files from real Infrared building meshes,
tree placements with species-specific canopies, and UTCI heatmap ground overlay.

Exports:
  build_glb_scene(...) -> path to .glb file

Requires: trimesh, pygltflib (pip install trimesh pygltflib)
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("coolspend.app_3d")

# ── Constants ──────────────────────────────────────────────────────────────────

# Fallback site dimensions (meters), used ONLY if a caller does not pass explicit
# site_width_m / site_depth_m. app.py always passes the real per-site dimensions
# (spatial_engine.SITE_WIDTH_M / SITE_DEPTH_M), so these defaults are a safety net.
SITE_WIDTH_M = 120
SITE_DEPTH_M = 120

# Ground elevation offset (m) — trees sit ON the ground, buildings rise from here
GROUND_Z = 0.0

# Tree trunk cylinder radius (m) — thin brown cylinder under canopy
TRUNK_RADIUS_M = 0.15

# Colors (RGBA floats 0-1)
COLOR_BUILDING = [0.55, 0.55, 0.55, 0.85]  # grey
COLOR_GROUND = [0.85, 0.85, 0.80, 1.0]  # light earth
COLOR_TRUNK = [0.40, 0.25, 0.15, 1.0]  # brown
COLOR_CANOPY = [0.15, 0.60, 0.25, 0.75]  # green, translucent
# Existing (already-on-the-ground) street trees — muted grey-green so they read as
# CONTEXT and never get confused with the species-coloured proposed plantings.
COLOR_EXISTING_CANOPY = [0.45, 0.55, 0.42, 0.55]  # desaturated olive, translucent

# Species canopy color palette (deterministic, colorblind-friendly)
_SPECIES_CANOPY_COLORS = [
    [0.12, 0.47, 0.71, 0.75],  # blue
    [1.00, 0.50, 0.05, 0.75],  # orange
    [0.17, 0.63, 0.17, 0.75],  # green
    [0.84, 0.15, 0.16, 0.75],  # red
    [0.58, 0.40, 0.74, 0.75],  # purple
    [0.55, 0.34, 0.16, 0.75],  # brown
    [0.89, 0.47, 0.76, 0.75],  # pink
    [0.50, 0.50, 0.50, 0.75],  # grey
    [0.74, 0.74, 0.13, 0.75],  # yellow
    [0.09, 0.75, 0.81, 0.75],  # cyan
    [0.68, 0.82, 0.90, 0.75],  # light blue
    [1.00, 0.73, 0.47, 0.75],  # peach
]

# UTCI colormap — blue (cool) to red (hot), 256 stops
_UTCI_CMAP = None  # lazy init


def _utci_colormap():
    """Blue (cool) → cyan → yellow → orange → red (hot) colormap."""
    global _UTCI_CMAP
    if _UTCI_CMAP is not None:
        return _UTCI_CMAP
    from matplotlib import cm
    _UTCI_CMAP = cm.get_cmap("RdYlBu_r", 256)
    return _UTCI_CMAP


# NOTE: WGS84→local-metre conversion is NOT done here. The single CRS boundary is
# spatial_engine.latlon_to_local_m (SPATIAL-03). app.py converts existing-tree
# lon/lat there and hands this module pre-projected x_m/y_m, so the 3D scene shares
# exactly one frame with the optimizer. Do not add a projection here.


# ── 3D mesh builders ──────────────────────────────────────────────────────────


def _make_ground_plane(
    width: float, depth: float, subdiv: int = 2
) -> "trimesh.Trimesh":
    """Flat ground quad at z=0, subdivided for vertex coloring."""
    import trimesh
    # Simple triangulated quad
    verts = np.array([
        [0, 0, 0], [width, 0, 0], [width, depth, 0], [0, depth, 0],
    ], dtype=float)
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=int)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    # Subdivide for smoother heatmap
    if subdiv > 0:
        for _ in range(subdiv):
            mesh = mesh.subdivide()
    return mesh


def _make_building_mesh(coordinates: list[float], indices: list[int] | None) -> "trimesh.Trimesh":
    """Convert Infrared DotBimMesh (flat coords + triangle indices) to trimesh."""
    import trimesh
    verts = np.array(coordinates, dtype=float).reshape(-1, 3)
    if indices:
        faces = np.array(indices, dtype=int).reshape(-1, 3)
    else:
        faces = np.arange(len(verts), dtype=int).reshape(-1, 3)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    mesh.visual.face_colors = [int(c * 255) for c in COLOR_BUILDING]
    return mesh


def _make_tree_sphere(
    x: float, y: float, z: float,
    crown_radius: float, trunk_height: float,
    color: list[float] = COLOR_CANOPY,
) -> "trimesh.Trimesh":
    """Create a tree as a trunk cylinder + canopy sphere."""
    import trimesh
    # Trunk: thin cylinder from ground to crown base
    trunk = trimesh.creation.cylinder(
        radius=TRUNK_RADIUS_M,
        height=trunk_height,
        sections=8,
    )
    trunk.apply_translation([x, y, z + trunk_height / 2])
    trunk.visual.face_colors = [int(c * 255) for c in COLOR_TRUNK]

    # Canopy: sphere at crown center
    canopy = trimesh.creation.icosphere(
        radius=crown_radius,
        subdivisions=2,
    )
    canopy.apply_translation([x, y, z + trunk_height + crown_radius * 0.6])
    canopy.visual.face_colors = [int(c * 255) for c in color]

    return trimesh.util.concatenate([trunk, canopy])


# ── Grid overlay on ground ─────────────────────────────────────────────────────


def _apply_utci_to_ground(
    ground: "trimesh.Trimesh",
    utci_grid: list[list[float]] | None,
    width: float, depth: float,
) -> None:
    """Paint UTCI values onto ground plane vertices."""
    if utci_grid is None:
        ground.visual.face_colors = [int(c * 255) for c in COLOR_GROUND]
        return

    grid = np.asarray(utci_grid, dtype=float)
    rows, cols = grid.shape
    cmap = _utci_colormap()

    # Map vertex (x, y) → nearest grid cell → UTCI → color
    verts = ground.vertices
    colors = np.zeros((len(verts), 4), dtype=np.uint8)
    for i, v in enumerate(verts):
        col_idx = int(np.clip(v[0] / width * cols, 0, cols - 1))
        row_idx = int(np.clip((1.0 - v[1] / depth) * rows, 0, rows - 1))
        val = grid[row_idx, col_idx]
        if np.isnan(val):
            colors[i] = [180, 180, 170, 255]  # earth for NaN
        else:
            # Normalize to 23–34 °C range for visual spread
            norm = np.clip((val - 23.0) / (34.0 - 23.0), 0.0, 1.0)
            rgba = cmap(norm)
            colors[i] = [int(c * 255) for c in rgba]
    ground.visual.vertex_colors = colors


# ── Public API ─────────────────────────────────────────────────────────────────


def build_glb_scene(
    config: dict,
    before_after: dict,
    buildings: list[dict] | None = None,
    baseline_grid: list[list[float]] | None = None,
    intervention_grid: list[list[float]] | None = None,
    out_path: str | None = None,
    site_width_m: float = SITE_WIDTH_M,
    site_depth_m: float = SITE_DEPTH_M,
    existing_trees: list[dict] | None = None,
) -> str:
    """Build a 3D .glb scene from CoolSpend run data.

    Scene layers:
      1. Ground plane with UTCI intervention heatmap (vertex-colored)
      2. Building meshes (grey, from Infrared DotBimMesh) — built-environment context
      3. Existing street trees (muted grey-green) — existing-canopy context
      4. Proposed tree canopies at placed positions (species-colored spheres)

    Args:
        config: Rank-1 tree config dict, containing "trees" list with
                x_m, y_m, species, crown_diameter_m, height_m.
        before_after: dict from run_decision, with baseline_utci_c,
                      chosen_validated_utci_c, headline_delta_utci_c.
        buildings: list of building dicts with "coordinates" and "indices".
        baseline_grid: 2D list of baseline UTCI values (optional).
        intervention_grid: 2D list of intervention UTCI values (optional).
        out_path: output .glb path (temp file if None).
        site_width_m: site width in meters.
        site_depth_m: site depth in meters.
        existing_trees: list of already-present trees in the SAME local-meter frame
                        ({x_m, y_m, crown_diameter_m?, height_m?}). Rendered as muted
                        context so the proposed plantings have surroundings.

    Returns:
        Absolute path to the .glb file.
    """
    import trimesh

    if out_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".glb", delete=False)
        tmp.close()
        out_path = tmp.name
    out_path = str(out_path)

    meshes: list[trimesh.Trimesh] = []

    # ── 1. Ground plane with UTCI heatmap ────────────────────────────────────
    ground = _make_ground_plane(site_width_m, site_depth_m, subdiv=3)
    _apply_utci_to_ground(
        ground,
        intervention_grid or baseline_grid,
        site_width_m, site_depth_m,
    )
    meshes.append(ground)

    # ── 2. Building meshes (built-environment context) ───────────────────────
    n_buildings = 0
    if buildings:
        for bld in buildings:
            try:
                bmesh = _make_building_mesh(
                    bld.get("coordinates", []),
                    bld.get("indices"),
                )
                meshes.append(bmesh)
                n_buildings += 1
            except Exception:
                # WARNING (not debug): a silent drop here is exactly how the whole
                # building layer disappeared before — keep this visible.
                logger.warning("Skipping building mesh — bad geometry", exc_info=True)
    logger.info("3D scene: %d building meshes added", n_buildings)

    # ── 3. Existing street trees (existing-canopy context) ───────────────────
    if existing_trees:
        for t in existing_trees:
            try:
                x = float(t.get("x_m", 0))
                y = float(t.get("y_m", 0))
                crown_r = float(t.get("crown_diameter_m", 5.0)) / 2.0
                height = float(t.get("height_m", 8.0))
                tree_mesh = _make_tree_sphere(
                    x, y, GROUND_Z, crown_r, height * 0.5, COLOR_EXISTING_CANOPY
                )
                meshes.append(tree_mesh)
            except Exception:
                logger.debug("Skipping existing-tree mesh", exc_info=True)
        logger.info("3D scene: %d existing context trees added", len(existing_trees))

    # ── 4. Proposed tree canopies ────────────────────────────────────────────
    active_trees = [t for t in config.get("trees", []) if t.get("active", True)]
    species_list = sorted(set(t.get("species", "?") for t in active_trees))
    sp_color_map = {}
    for i, sp_name in enumerate(species_list):
        sp_color_map[sp_name] = _SPECIES_CANOPY_COLORS[i % len(_SPECIES_CANOPY_COLORS)]

    for t in active_trees:
        try:
            x = float(t.get("x_m", 0))
            y = float(t.get("y_m", 0))
            sp = t.get("species", "")
            crown_r = float(t.get("crown_diameter_m", 6.0)) / 2.0
            height = float(t.get("height_m", 10.0))
            trunk_h = height * 0.5  # trunk to half tree height
            color = sp_color_map.get(sp, COLOR_CANOPY)
            tree_mesh = _make_tree_sphere(x, y, GROUND_Z, crown_r, trunk_h, color)
            meshes.append(tree_mesh)
        except Exception:
            logger.debug("Skipping tree mesh", exc_info=True)

    # ── 5. Merge and export ──────────────────────────────────────────────────
    if not meshes:
        raise RuntimeError("No geometry to export — empty scene.")

    scene = trimesh.Scene()
    for i, m in enumerate(meshes):
        scene.add_geometry(m, node_name=f"layer_{i}")

    # Set scene metadata
    headline = before_after.get("headline_delta_utci_c", 0.0)
    scene.metadata = {
        "generator": "CoolSpend / Infrared SDK",
        "headline_delta_utci_c": str(headline),
        "cooled_footprint_m2": str(before_after.get("cooled_footprint_m2", "N/A")),
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    scene.export(file_obj=out_path, file_type="glb")
    logger.info("Exported 3D scene to %s (%d meshes)", out_path, len(meshes))

    return str(out_path)


def build_cooling_diff_glb(
    config: dict,
    before_after: dict,
    buildings: list[dict] | None = None,
    baseline_grid: list[list[float]] | None = None,
    intervention_grid: list[list[float]] | None = None,
    out_path: str | None = None,
    site_width_m: float = SITE_WIDTH_M,
    site_depth_m: float = SITE_DEPTH_M,
    existing_trees: list[dict] | None = None,
) -> str:
    """Build a .glb showing the COOLING DIFF (baseline − intervention) on ground.

    Blue = more cooling. Red = minimal/no cooling. Building and tree layers
    same as build_glb_scene (existing_trees rendered as muted context).
    """
    import trimesh

    if out_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".glb", delete=False)
        tmp.close()
        out_path = tmp.name
    out_path = str(out_path)

    meshes: list[trimesh.Trimesh] = []

    # ── Ground with diff overlay ─────────────────────────────────────────────
    ground = _make_ground_plane(site_width_m, site_depth_m, subdiv=3)

    if baseline_grid is not None and intervention_grid is not None:
        b = np.asarray(baseline_grid, dtype=float)
        i = np.asarray(intervention_grid, dtype=float)
        diff = b - i  # positive = cooling

        verts = ground.vertices
        rows, cols = diff.shape
        colors = np.zeros((len(verts), 4), dtype=np.uint8)
        from matplotlib import cm
        cmap = cm.get_cmap("YlOrRd", 256)  # reversed: cool(blue) via custom

        for vi, v in enumerate(verts):
            col_idx = int(np.clip(v[0] / site_width_m * cols, 0, cols - 1))
            row_idx = int(np.clip((1.0 - v[1] / site_depth_m) * rows, 0, rows - 1))
            val = diff[row_idx, col_idx]
            if np.isnan(val):
                colors[vi] = [180, 180, 170, 255]
            else:
                # Map 0→1°C cooling onto 0→1
                norm = np.clip(val / 2.0, 0.0, 1.0)  # 2°C = max
                # Blue (cool) → white → red (no cooling)
                r = int(255 * (1.0 - norm))
                g = int(255 * (1.0 - abs(norm - 0.5) * 2.0))
                b_val = int(255 * norm)
                colors[vi] = [r, g, b_val, 255]
        ground.visual.vertex_colors = colors
    else:
        ground.visual.face_colors = [int(c * 255) for c in COLOR_GROUND]

    meshes.append(ground)

    # ── Buildings ────────────────────────────────────────────────────────────
    if buildings:
        for bld in buildings:
            try:
                meshes.append(_make_building_mesh(
                    bld.get("coordinates", []), bld.get("indices"),
                ))
            except Exception:
                pass

    # ── Existing context trees (muted) ───────────────────────────────────────
    if existing_trees:
        for t in existing_trees:
            try:
                x = float(t.get("x_m", 0))
                y = float(t.get("y_m", 0))
                crown_r = float(t.get("crown_diameter_m", 5.0)) / 2.0
                height = float(t.get("height_m", 8.0))
                meshes.append(_make_tree_sphere(
                    x, y, GROUND_Z, crown_r, height * 0.5, COLOR_EXISTING_CANOPY
                ))
            except Exception:
                pass

    # ── Proposed trees ───────────────────────────────────────────────────────
    active_trees = [t for t in config.get("trees", []) if t.get("active", True)]
    for t in active_trees:
        try:
            x = float(t.get("x_m", 0))
            y = float(t.get("y_m", 0))
            crown_r = float(t.get("crown_diameter_m", 6.0)) / 2.0
            height = float(t.get("height_m", 10.0))
            meshes.append(_make_tree_sphere(x, y, GROUND_Z, crown_r, height * 0.5))
        except Exception:
            pass

    # ── Export ───────────────────────────────────────────────────────────────
    scene = trimesh.Scene()
    for i, m in enumerate(meshes):
        scene.add_geometry(m, node_name=f"layer_{i}")

    scene.metadata = {
        "generator": "CoolSpend / Infrared SDK",
        "type": "cooling_diff",
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    scene.export(file_obj=out_path, file_type="glb")
    logger.info("Exported cooling diff 3D scene to %s", out_path)

    return str(out_path)
