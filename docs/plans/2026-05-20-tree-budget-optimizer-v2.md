# Tree Budget Optimizer: Disciplined Prototype Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a working Tree Budget Optimizer that maximizes UTCI relief while respecting hard urban constraints and explicit ecological rules.

**Architecture:**
- **Optimizer:** NSGA-II (Pymoo) with a fixed-length vector of tree coordinates.
- **Data Layer:** Local OSM GeoJSON (buildings/streets) for collision detection via `shapely`.
- **Fitness 1 (Thermal):** Real UTCI delta from Infrared SDK (Baseline vs. Intervention).
- **Fitness 2 (Ecological):** Diversity and spacing score (Permaculture Rules).
- **Hard Constraints:** Trees cannot be inside buildings or on street centerlines.

**Tech Stack:** Python, `infrared-sdk`, `pymoo`, `shapely`, `geojson`.

---

### Task 1: Spatial Context & Collision Engine

**Files:**
- Create: `spatial_engine.py`
- Create: `data/site_context.geojson` (Mock or fetched from NatureGooddest)

**Step 1: Write a collision detector using Shapely**

```python
from shapely.geometry import shape, Point
import json

class SpatialEngine:
    def __init__(self, geojson_path):
        with open(geojson_path) as f:
            self.data = json.load(f)
        self.buildings = [shape(f['geometry']) for f in self.data['features'] if f['properties'].get('type') == 'building']
        self.site_boundary = shape([f for f in self.data['features'] if f['properties'].get('type') == 'site'][0]['geometry'])

    def is_valid_location(self, x, y):
        p = Point(x, y)
        if not self.site_boundary.contains(p): return False
        for b in self.buildings:
            if b.contains(p): return False
        return True
```

**Step 2: Commit**

```bash
git add spatial_engine.py
git commit -m "feat: add spatial engine with collision detection"
```

### Task 2: Permaculture Rule Engine

**Files:**
- Create: `rules_engine.py`

**Step 1: Implement Spacing and Diversity Rules**

```python
def calculate_ecological_score(tree_coords, species_list):
    # Rule 1: Min spacing (e.g. 5m) - Penalty for overcrowding
    # Rule 2: Diversity (Shannon index or simple species count)
    # Rule 3: Proximity to existing green nodes (if available)
    score = 1.0 # Implement real math here
    return score
```

**Step 2: Commit**

```bash
git add rules_engine.py
git commit -m "feat: add permaculture rule engine"
```

### Task 3: The Optimizer (NSGA-II + Infrared)

**Files:**
- Create: `optimize_trees.py`

**Step 1: Setup NSGA-II with 2 objectives: Thermal Relief and Ecological Coherence.**
**Step 2: Use `spatial_engine.py` to filter/penalty invalid chromosome positions.**
**Step 3: Call `infrared_sdk` for the Thermal objective.**

**Step 4: Commit**

```bash
git add optimize_trees.py
git commit -m "feat: implement tree optimizer with thermal and eco objectives"
```

### Task 4: CLI Runner & Visualizer

**Files:**
- Create: `main.py`

**Step 1: Simple script to run 10 generations and print the Top-3 configurations.**

**Step 2: Commit**

```bash
git add main.py
git commit -m "feat: add main cli entry point"
```
