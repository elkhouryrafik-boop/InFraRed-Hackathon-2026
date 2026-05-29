# Technology Stack

**Analysis Date:** 2026-05-27

## Languages

**Primary:**
- Python 3.11+ — all computation, optimization, SDK wrappers, Gradio UI
  - Uses `from __future__ import annotations`, `list[dict]`, `dict | None` union syntax (3.10+ required)
  - `match`/`case` not used; effective lower bound is 3.10 due to union type hints in signatures

**Secondary:**
- None detected (no JS/TS/CSS; all rendering is Gradio server-side)

## Runtime

**Environment:**
- CPython 3.11.15 (confirmed installed)
- Runs headless (matplotlib "Agg" backend forced in `coolspend/app_viz.py` line 27)
- No display required for optimizer, CLI, or tests

**Package Manager:**
- pip (no lockfile)
- Dependencies declared in `requirements.txt` (project root)
- `.venv/` virtual environment present (gitignored)
- Hugging Face Spaces auto-installs from `requirements.txt`

## Frameworks

**Core Application:**
- Gradio **4.44.1** — web UI framework (Blocks API)
  - Entry point: `coolspend/app.py`
  - Hugging Face Space SDK: `sdk: gradio` in `README.md` YAML header
  - Known compatibility: `gradio-client==1.3.0` (must match 4.44.1), `fastapi==0.112.4` (avoids starlette>=1.0 TemplateResponse breakage), `starlette==0.37.2` (pinned for `"unhashable type: dict"` bug in gradio 4.44.1)

**Optimization:**
- pymoo **0.6.1** — NSGA-II multi-objective optimizer
  - API used: `ElementwiseProblem`, `NSGA2`, `SBX`, `PM`, `FloatRandomSampling`, `get_termination`, `minimize`
  - Located in `coolspend/optimizer.py`
  - 2 objectives (thermal relief, ecological coherence), 1 budget constraint
  - Default: POP_SIZE=60, N_GEN=60, SEED=42, N_TREES=12

**Geospatial:**
- Shapely **>=2.0,<3.0** — geometry operations (Polygon, Point, LineString, unary_union)
  - Located in `coolspend/spatial_engine.py` (site loader, collision detection, CRS conversion)
- pyproj **>=3.6,<4** — CRS transformations (EPSG:4326 <-> EPSG:32631 UTM-31N)
  - Single authoritative pair: `_TO_UTM` and `_TO_WGS` at module level in `coolspend/spatial_engine.py`
- rasterio **>=1.3** — OPTIONAL: ICGC LiDAR canopy-height raster sampling
  - Used in `coolspend/bcn_lidar.py` line 89; absence degrades gracefully (canopy context -> None)
- GeoJSON — site polygon format, parsed via `json.loads` only (no eval/exec)
  - Default site fixture: `coolspend/data/angels_site.geojson`

**Numerical / Science:**
- numpy **>=1.26,<2.0** — array ops throughout optimizer, spatial engine, cost model
- matplotlib **>=3.7,<4.0** — headless Pareto front plots + before/after heatmap panels
  - Located in `coolspend/app_viz.py` (Agg backend forced)

**Infrared SDK:**
- `infrared-sdk` (latest) — declared in `requirements.txt`
  - LAZILY imported inside `coolspend/sdk_client.py:_live_utci()` (line 388)
  - Module importable without the SDK installed (offline-safe)
  - Classes used: `InfraredClient`, `UtciModelRequest`, `UtciModelBaseRequest`, `AnalysesName`, `TimePeriod`, `Location`

**HTTP / Data Fetching:**
- `requests>=2.31` — all outbound HTTP: CKAN inventory fetch (`coolspend/bcn_data.py`), ICGC raster download (`coolspend/bcn_lidar.py`)
- `huggingface_hub==0.36.2` — HF Spaces integration

**CLI:**
- typer **0.12.5** — CLI runner (pinned: typer>=0.13 breaks with gradio 4.44.1's click 8.1.7 dependency)

**Testing:**
- pytest — no version pinned; config absent (no pytest.ini/pyproject.toml override)
  - 17 test files in `coolspend/tests/`
  - conftest.py provides `_reset_site_origin` autouse fixture

## Key Dependencies Summary

| Package | Version (pinned) | Located In | Purpose |
|---|---|---|---|
| pymoo | 0.6.1 | `optimizer.py` | NSGA-II multi-objective optimizer |
| gradio | 4.44.1 | `app.py` | Web UI / Hugging Face Spaces |
| gradio-client | 1.3.0 | transitive | Gradio schema parsing (bug workaround) |
| fastapi | 0.112.4 | transitive | Gradio server (pinned for starlette compat) |
| starlette | 0.37.2 | transitive | Gradio server (pinned for TemplateResponse fix) |
| infrared-sdk | latest | `sdk_client.py` | Live Infrared UTCI API |
| shapely | >=2.0,<3.0 | `spatial_engine.py` | Geometry operations |
| pyproj | >=3.6,<4 | `spatial_engine.py` | CRS conversion (EPSG:4326 <-> 32631) |
| numpy | >=1.26,<2.0 | multiple modules | Numerical operations |
| matplotlib | >=3.7,<4.0 | `app_viz.py`, `optimizer.py` | Visualization (headless Agg) |
| requests | >=2.31 | `bcn_data.py`, `bcn_lidar.py` | HTTP data fetching |
| rasterio | >=1.3 | `bcn_lidar.py` | GeoTIFF sampling (OPTIONAL) |
| huggingface_hub | 0.36.2 | `app.py` | Hugging Face Spaces integration |
| typer | 0.12.5 | `main.py` | CLI entry point |

## NSGA-II Run Parameters

Used as defaults in `coolspend/optimizer.py`:

| Parameter | Value |
|---|---|
| N_TREES | 12 (24 decision vars: x_m, y_m per tree) |
| N_GEN | 60 |
| POP_SIZE | 60 |
| SEED | 42 |
| Budget | 1,000,000 EUR (default) |
| Crossover | SBX(prob=0.9, eta=15) |
| Mutation | PM(eta=20) |
| Objectives | F1 = -thermal_relief(), F2 = -ecological_score() |

## Configuration

**Environment variables:**
- `INFRARED_BACKEND` — `mock` | `cached` | `live` (default: `mock`)
  - Consumed by `coolspend/sdk_client.py:_backend()` line 68
- `INFRARED_API_KEY` — API key for live Infrared SDK calls
  - Validated in `coolspend/sdk_client.py:_live_utci()` line 362
  - NEVER logged, formatted, or included in any string (T-02-07)

**Build / config files:**
- `requirements.txt` — single source of truth for dependencies
- No `pyproject.toml`, `setup.py`, `setup.cfg`, `Makefile`, or `Dockerfile`
- `.gitignore` excludes: `.env`, `__pycache__/`, `*.pyc`, `coolspend/cache/`, `outputs/`, `.venv/`

## Platform Requirements

**Development:**
- Python 3.10+ (tested on 3.11.15 Windows)
- Windows (current workspace)
- No platform-specific dependencies detected

**Production / Demo:**
- Hugging Face Spaces (Gradio SDK)
- Auto-deploys from `README.md` YAML header: `sdk: gradio`, `app_file: coolspend/app.py`
- Requires Space Secrets for live mode: `INFRARED_BACKEND=live`, `INFRARED_API_KEY=<key>`

## Data Formats

| Format | Used By | Purpose |
|---|---|---|
| GeoJSON | `spatial_engine.py`, `sdk_client.py` | Site polygon (WGS84), tree placements |
| JSON | `sdk_client.py`, `bcn_data.py`, `bcn_species.py` | Cache files, decision artifacts, species table |
| CSV | `bcn_data.py` | Barcelona tree inventory (Open Data BCN CKAN) |
| TIFF | `bcn_lidar.py` | ICGC+CREAF canopy-height raster (~166 MB) |
| PNG | `app_viz.py`, `optimizer.py` | Pareto front plot, before/after heatmap |

---

*Stack analysis: 2026-05-27*
