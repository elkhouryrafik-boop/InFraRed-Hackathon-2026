# Tree Budget Optimizer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a tree-placement optimizer that maximizes UTCI cooling relief per tree planted (the "carbon of stress relief"), utilizing the Infrared SDK for real-world simulation and NatureGooddest's NSGA-II logic.

**Architecture:** We will adapt the NSGA-II evolutionary algorithm to optimize a variable-length list of tree coordinates. The "fitness" will be determined by calling the Infrared SDK's UTCI analysis on the baseline vs. the intervention (the new trees).

**Tech Stack:** Python, `infrared-sdk`, `pymoo` (NSGA-II), `shapely` (geometry).

---

### Task 1: Environment Setup & SDK Verification

**Files:**
- Create: `verify_sdk.py`
- Create: `.env`

**Step 1: Create a simple verification script**

```python
from infrared_sdk import InfraredClient
from infrared_sdk.analyses.types import UTCIModelRequest, AnalysesName
import os

polygon = {"type": "Polygon", "coordinates": [[[11.57, 48.19], [11.58, 48.19], [11.58, 48.20], [11.57, 48.20], [11.57, 48.19]]]}

def test_connection():
    with InfraredClient() as client:
        area = client.buildings.get_area(polygon)
        print(f"Connected. Found {len(area.buildings)} buildings.")

if __name__ == "__main__":
    test_connection()
```

**Step 2: Run verification script**

Run: `python verify_sdk.py`
Expected: Success message or API key error (to be resolved by user).

**Step 3: Commit**

```bash
git add verify_sdk.py
git commit -m "chore: setup sdk verification"
```

### Task 2: Core Tree-Placement Problem Definition

**Files:**
- Create: `tree_optimizer.py`

**Step 1: Define the NSGA-II Problem class for Trees**

```python
import numpy as np
from pymoo.core.problem import ElementwiseProblem

class TreePlacementProblem(ElementwiseProblem):
    def __init__(self, n_trees=5, site_polygon=None):
        self.n_trees = n_trees
        self.site_polygon = site_polygon
        # 2 variables per tree: x, y
        xl = np.zeros(n_trees * 2)
        xu = np.ones(n_trees * 2) # Normalized [0, 1] relative to bounding box
        super().__init__(n_var=n_trees * 2, n_obj=2, xl=xl, xu=xu)

    def _evaluate(self, x, out, *args, **kwargs):
        # Placeholder: f1 = cooling, f2 = cost (always n_trees for now)
        out["F"] = [np.random.random(), self.n_trees]
```

**Step 2: Create a minimal runner**

```python
if __name__ == "__main__":
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.optimize import minimize
    problem = TreePlacementProblem()
    res = minimize(problem, NSGA2(), ("n_gen", 5), seed=1)
    print("Optimization finished.")
```

**Step 3: Run and verify**

Run: `python tree_optimizer.py`
Expected: "Optimization finished."

**Step 4: Commit**

```bash
git add tree_optimizer.py
git commit -m "feat: initial tree placement problem definition"
```

### Task 3: Infrared SDK Integration (The Fitness Function)

**Files:**
- Modify: `tree_optimizer.py`

**Step 1: Implement the Infrared SDK call in `_evaluate`**

```python
from infrared_sdk import InfraredClient
from infrared_sdk.analyses.types import UTCIModelRequest, AnalysesName

def get_utci_delta(site_poly, trees_geom):
    with InfraredClient() as client:
        # 1. Run Baseline
        baseline = client.run_area_and_wait(UTCIModelRequest(), site_poly)
        # 2. Run Intervention (with trees)
        # NOTE: Trees need to be formatted as 'trees' parameter in SDK
        intervention = client.run_area_and_wait(UTCIModelRequest(), site_poly, trees=trees_geom)
        
        delta = np.mean(baseline.merged_grid) - np.mean(intervention.merged_grid)
        return delta
```

**Step 2: Integrate into `_evaluate`**

**Step 3: Commit**

```bash
git add tree_optimizer.py
git commit -m "feat: integrate infrared sdk for fitness evaluation"
```

### Task 4: Visualization and Reporting

**Files:**
- Create: `report_gen.py`

**Step 1: Generate a summary of the best tree placements**

**Step 2: Commit**

```bash
git add report_gen.py
git commit -m "feat: add report generation"
```
