# Technology Stack

**Analysis Date:** 2026-06-01

CoolSpend is a two-runtime project: a **Python** decision-support backend (`coolspend/`, FastAPI + scientific stack) and a **React/TypeScript** web client (`web/`, Vite + deck.gl + Mapbox). A separate Remotion explainer film lives in `video/` (not analyzed here in depth).

## Languages

**Primary:**
- Python 3 (>=3.10 idioms: `from __future__ import annotations`, PEP 604 `X | None`, `list[...]`/`dict[...]` generics) — entire `coolspend/` backend, e.g. `coolspend/api_server.py`, `coolspend/sdk_client.py`
- TypeScript 5.6 - entire `web/src/` client, e.g. `web/src/App.tsx`, `web/src/components/Scene.tsx`, `web/src/lib/layers.ts`

**Secondary:**
- CSS (design tokens) - `web/src/styles/tokens.css` (loaded first in `web/src/main.tsx`)
- Markdown - canonical project docs at repo root: `PAPER.md`, `MOCKS.md`, `DATA_SOURCES.md`, `README.md`, plus method notes in `coolspend/docs/`

## Runtime

**Environment:**
- Python: server run via `uvicorn` (ASGI); also packaged as a Hugging Face Space (Gradio SDK 4.44.1, `app_file: coolspend/app.py` per `README.md` front-matter). Virtualenv present at `.venv/`.
- Node.js: Vite 6 dev server / build for the web client; ES modules (`"type": "module"` in `web/package.json`)

**Package Managers:**
- Python: `pip` + `requirements.txt` (no `pyproject.toml`/`setup.py` — flat requirements file)
- Web: `npm` + `web/package.json`; lockfile not committed in repo root listing (verify `web/package-lock.json`)

## Frameworks

**Backend (Python):**
- FastAPI 0.112.4 - HTTP API in `coolspend/api_server.py` (pinned for Gradio 4.44.1 compatibility; see requirements comments)
- Starlette 0.37.2 - pinned (newer Starlette removes the `TemplateResponse(name, context)` signature Gradio 4.44.1 calls)
- Uvicorn - ASGI server (imported in `coolspend/api_server.py` `__main__`)
- Pydantic - request models (`PolygonRequest`, `EvaluateRequest` in `coolspend/api_server.py`); also surfaces via Infrared SDK frozen models
- Gradio 4.44.1 + gradio-client 1.3.0 - legacy/fallback UI (`coolspend/app.py`), the Hugging Face Space entrypoint
- Typer 0.12.5 - CLI (pinned: typer>=0.13 breaks against click 8.1.7 from Gradio)

**Frontend (TypeScript):**
- React 18.3.1 + react-dom 18.3.1 - UI (`web/src/`)
- deck.gl 9.1 (`@deck.gl/core`, `/layers`, `/geo-layers`, `/mesh-layers` ^9.3.2, `/react`, `/mapbox`, `/extensions`) - WebGL data overlays (heatmap, canopy-disk trees, drawing)
- mapbox-gl 3.9 + react-map-gl 7.1.7 - basemap (`web/src/components/Scene.tsx`)
- @loaders.gl/3d-tiles 4.3 - Google Photorealistic 3D Tiles loader (`web/src/lib/layers.ts`, `web/src/lib/cesium.ts`)

**Optimization / scientific (Python):**
- pymoo 0.6.1 - NSGA-II multi-objective optimizer (`coolspend/optimizer.py`)
- numpy >=1.26,<2.0 - grid math, UTCI reductions (`coolspend/sdk_client.py`)
- shapely >=2.0,<3.0 - geometry / placement exclusions (`coolspend/osm_*.py`, `candidate_slots.py`)
- pyproj >=3.6,<4 - CRS transforms WGS84 <-> UTM-31N / ETRS89 (`coolspend/spatial_engine.py`)
- matplotlib >=3.7,<4.0 - UTCI heatmap PNG export (`coolspend/export_web.py`)
- geojson >=3.0,<4.0 - GeoJSON I/O
- rasterio >=1.3 - OPTIONAL; ICGC LiDAR canopy-height raster sampling (`coolspend/bcn_lidar.py`). Absent -> canopy context degrades to None, pipeline unaffected.
- scipy - OPTIONAL; connected-component cooled-patch analysis (`ndimage.label` in `coolspend/sdk_client.py`, guarded by try/except)

**Testing:**
- pytest - Python suite under `coolspend/tests/` (README: 341 offline, deterministic tests)
- Vitest 2.1.8 - web unit tests (`web/package.json` `test`/`test:watch`)

**Build/Dev:**
- Vite 6.0.5 - dev server + production bundler (`web/vite.config.ts`)
- @vitejs/plugin-react 4.3.4 - React Fast Refresh / JSX
- TypeScript 5.6.3 (`tsc -b`) - type-check + project-reference build (`web/tsconfig*.json`, `web/tsconfig.app.tsbuildinfo`)
- huggingface_hub 0.36.2 - Space publishing / artifact transfer

## Key Dependencies

**Critical:**
- infrared-sdk (unpinned in `requirements.txt`) - the live Infrared.city UTCI/TCS engine; imported LAZILY only inside `_live_utci`/`_live_tcs`/`get_buildings_for_polygon` in `coolspend/sdk_client.py` so the module imports offline without it. Required only when `INFRARED_BACKEND=live`.
- requests >=2.31 - all REST data fetches (BCN Open Data CKAN, OSM Overpass, ICGC; `coolspend/bcn_data.py`, `osm_roads.py`, `population.py`)
- python-dotenv - loads `.env` (INFRARED_API_KEY) in `coolspend/api_server.py` (imported defensively in try/except)

**Infrastructure:**
- @deck.gl/* + mapbox-gl - the entire visualization layer
- pymoo + numpy - the optimizer hot path

## Configuration

**Backend environment variables (read at dispatch time, never at import):**
- `INFRARED_BACKEND` - `mock` (default) | `cached` | `live`; selected server-side, NOT from any HTTP request (`coolspend/api_server.py` `_backend_mode`, `coolspend/sdk_client.py` `_backend`)
- `INFRARED_API_KEY` - required only for `live`; read by the SDK from the environment; never logged, never accepted over HTTP, never returned (`coolspend/sdk_client.py` `_live_utci`)
- `INFRARED_WEATHER_SOURCE` - `auto` (default) | `epw` | `infrared`; controls Infrared-weather vs EPW fallback (`coolspend/sdk_client.py` `_resolve_weather_data`)
- `COOLSPEND_API_PORT` - server port (default 8000)
- `.env` at repo root holds `INFRARED_API_KEY` (gitignored; contents never read here)

**Frontend environment (Vite `import.meta.env`):**
- `VITE_MAPBOX_TOKEN` - Mapbox basemap (required for the full scene; absent -> `FallbackScene`)
- `VITE_CESIUM_ION_TOKEN` - Cesium Ion (optional; absent -> no photoreal 3D tiles)
- Template at `web/.env.local.example`; real values in gitignored `web/.env.local`. Typed in `web/src/vite-env.d.ts`.

**Build config files:**
- `web/vite.config.ts`, `web/tsconfig.json` / `tsconfig.app.json` (project references)
- `requirements.txt` (heavily commented version-pin rationale)
- `coolspend/cost_config.json` - itemized €/tree cost constants

## Platform Requirements

**Development:**
- Python 3.10+ with `pip install -r requirements.txt`
- Node.js + npm for the web client
- Optional: rasterio (LiDAR), scipy (patch contiguity), infrared-sdk (live runs) — all degrade gracefully when absent

**Production / deployment:**
- Hugging Face Space (Gradio SDK 4.44.1) for the legacy Gradio app (`coolspend/app.py`)
- FastAPI app (`coolspend/api_server.py`) can serve the built web client: it mounts `web/dist` at `/` (catch-all) and the runtime eval bundle at `/eval_bundle` when present

## How to Run

```bash
# Python deps
pip install -r requirements.txt

# 1) Backend API (drawing + citywide). mock evaluates ANY drawn area instantly, offline.
INFRARED_BACKEND=mock python -m uvicorn coolspend.api_server:app --port 8000
#   (or: python -m coolspend.api_server  -> defaults INFRARED_BACKEND=live, port 8000)

# 2) Web app (Vite dev server)
cd web && npm install && npm run dev          # http://localhost:5173

# Production web build
cd web && npm run build                        # tsc -b && vite build -> web/dist
cd web && npm run preview                      # serve build at :4173

# Regenerate the live Infrared showcase bundle (one real metered run)
INFRARED_BACKEND=live INFRARED_API_KEY=<key> python -m coolspend.export_web
```

**Tests:**
```bash
python -m pytest coolspend/tests -q     # ~341 offline, deterministic Python tests
cd web && npm test                       # vitest (web/package.json "test": "vitest run")
cd web && npm run typecheck              # tsc -b --noEmit
```

CORS in `coolspend/api_server.py` allows the Vite dev origins `:5173` and the preview `:4173` (localhost + 127.0.0.1).

---

*Stack analysis: 2026-06-01*
