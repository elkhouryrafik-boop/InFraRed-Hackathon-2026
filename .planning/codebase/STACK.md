# Technology Stack

**Analysis Date:** 2026-05-21
**Source context:** NatureGooddest reference code extracted for coolspend hackathon port.
All files below are PORT-FROM references, not the new app's code.

---

## Languages

**Primary:**
- Python 3.10+ — all computation, optimization, metrics, SDK wrappers
  - Uses `from __future__ import annotations`, `list[dict]`, `dict | None` union syntax (3.10+ required)
  - `match`/`case` not used; lower bound is effectively 3.10 due to union type hints in signatures

**Secondary:**
- None detected (no JS/TS in the reference files; Three.js/HTML is in `demo_app.py` which is NOT in scope)

---

## Runtime

**Environment:**
- CPython 3.10+
- Runs headless (no browser required for optimizer or metrics)

**Package Manager:**
- No `requirements.txt`, `pyproject.toml`, or `setup.py` found in the Hackathon workspace
- Dependencies inferred entirely from import statements in the three reference files
- Lockfile: **absent** — must be created fresh for coolspend

---

## Frameworks

**Optimization:**
- `pymoo` **0.6.1** — NSGA-II multi-objective optimizer
  - Hardcoded in JSON output metadata: `"algorithm": "NSGA-II (pymoo 0.6.1)"` (`nature_nsga2_coolstock.py` line 529)
  - API used: `ElementwiseProblem`, `NSGA2`, `SBX`, `PM`, `FloatRandomSampling`, `get_termination`, `minimize`
  - Port verdict: **KEEP** — same algorithm needed for coolspend tree optimizer

**Thermal Comfort / Climate:**
- `ladybug-comfort` **0.18** — referenced in source comment: `"ladybug-comfort 0.18 universal_thermal_climate_index"` (`nature_metrics.py` line 204)
  - Import: `from ladybug_comfort.utci import universal_thermal_climate_index`
  - Used to compute UTCI from (dry_bulb, tmrt, wind_speed, rel_humidity) tuples
  - Port verdict: **KEEP** — `utci_hours_above()` and histogram functions are directly reusable for the €/°C cost model

- `ladybug` — EPW file reader
  - Import: `from ladybug.epw import EPW`
  - Used to load 8,760-hour Barcelona TMYx climate arrays (dry_bulb, rel_humidity, wind_speed, GHI)
  - Port verdict: **KEEP IF** coolspend uses EPW climate input; **LEAVE BEHIND** if Infrared SDK provides climate data directly

**Geometry:**
- `shapely` — imported in `plaza_shaded_fraction()` (`nature_metrics.py` lines 554-578)
  - Import: `from shapely.geometry import Polygon, MultiPoint` (lazy import inside function)
  - Used for canopy + cast-shadow polygon intersection against site boundary
  - Port verdict: **KEEP** — needed for `SpatialEngine` collision detection (Task 1 in V2 plan)

**Numerical:**
- `numpy` — throughout `nature_nsga2_coolstock.py` and `nature_metrics.py`
  - Used for: bounds arrays, Pareto front matrix ops, TOPSIS normalisation (`np.linalg.norm`)
  - No version pin detected in source
  - Port verdict: **KEEP**

**Visualization:**
- `matplotlib` — Pareto front plot in `nature_nsga2_coolstock.py`
  - Backend forced to `"Agg"` (headless PNG output, no display required)
  - Port verdict: **OPTIONAL** — useful for hackathon demo output; easy to drop

**Configuration:**
- `pyyaml` — loads P01 pattern bounds from `cookbooks/urban-cooling/patterns/P01_sun_path_canopy.yaml`
  - Import: `import yaml` (`nature_nsga2_coolstock.py` line 31)
  - Port verdict: **LEAVE BEHIND** — coolspend uses a simple Python config dict, not a YAML cookbook system

**Infrared SDK:**
- `infrared-sdk` — the real SDK (NOT the mock client files in this workspace)
  - Install: `pip install infrared-sdk`
  - Import pattern from hackathon docs: `from infrared_sdk import InfraredClient`
  - Version: not pinned in reference code (SDK was accessed post-2026-05-19 when key arrived)
  - Port verdict: **KEEP** — this is the primary new dependency for coolspend; replaces the surrogate entirely

**Demo/UI (NatureGooddest only, not ported):**
- `gradio` — mentioned in hackathon `infrared_hackathon.md` as a "Gradio recipe" starter
  - NOT imported in any reference file; used by NatureGooddest's `demo_app.py` (Flask)
  - Port verdict: **NEW ADDITION** for coolspend if Hugging Face Spaces demo is desired; not in reference code

---

## Key Dependencies (summary table)

| Package | Version known | Source file | Port verdict |
|---|---|---|---|
| `pymoo` | **0.6.1** (hardcoded string) | `nature_nsga2_coolstock.py:529` | KEEP |
| `ladybug-comfort` | **0.18** (comment) | `nature_metrics.py:204` | KEEP |
| `ladybug` | unknown | `nature_metrics.py:34` | KEEP IF EPW needed |
| `numpy` | unknown | both optimizer + metrics | KEEP |
| `shapely` | unknown | `nature_metrics.py:554` | KEEP |
| `pyyaml` | unknown | `nature_nsga2_coolstock.py:31` | LEAVE BEHIND |
| `matplotlib` | unknown | `nature_nsga2_coolstock.py:34-36` | OPTIONAL |
| `infrared-sdk` | unknown (latest) | hackathon docs | KEEP (new) |
| `gradio` | unknown | hackathon docs only | NEW ADDITION (optional) |
| `geojson` | not imported | V2 plan only | NEW ADDITION |

---

## NSGA-II Run Parameters (from `nature_nsga2_coolstock.py`)

Used as defaults in `run_optimisation()` (line 252) and `__main__` (line 632):

| Parameter | Value |
|---|---|
| `n_gen` | 100 |
| `pop_size` | 100 |
| `seed` | 42 |
| `crossover` | SBX(prob=0.9, eta=15) |
| `mutation` | PM(eta=20) |
| `sampling` | FloatRandomSampling |
| `eliminate_duplicates` | True |

For coolspend hackathon: reduce to `n_gen=50, pop_size=50` for fast iteration; use `seed=42` for reproducibility.

---

## Configuration

**Environment variables:**
- `INFRARED_BACKEND` — `mock` | `cached` | `live` (default: `mock`)
  - Consumed by `infrared_client_v2.py` and `nature_infrared_client.py`
  - NOT consumed by the real SDK path (`infrared_sdk.InfraredClient`)
  - Port verdict: keep the pattern but it only controls the legacy mock client
- `INFRARED_API_KEY` — API key for live Infrared SDK calls
  - Read by the real `infrared_sdk.InfraredClient` (not visible in reference files — SDK handles it)
  - **API key issues May 27** — coolspend must run fully offline until then

**Build / config files in workspace:**
- No `requirements.txt`, `Makefile`, `Dockerfile`, or `pyproject.toml` present
- `docs/plans/2026-05-20-tree-budget-optimizer-v2.md` — implementation blueprint
- `CONCEPT_REPORT.md` — conceptual framing

---

## Platform Requirements

**Development:**
- Python 3.10+
- Windows (current workspace: `C:\Users\Rafik\OneDrive\Python Resources\Hackathon`)
- No virtual environment detected

**Production / Demo:**
- Hackathon deadline: **Sun May 31 24:00 CET**
- Target: GitHub repo + demo (Hugging Face Spaces via Gradio is the suggested path per hackathon docs)
- The Infrared API key activates **May 27**; until then all simulation must run via `INFRARED_BACKEND=mock` or `INFRARED_BACKEND=cached`

---

*Stack analysis: 2026-05-21*
