# External Integrations

**Analysis Date:** 2026-06-01

CoolSpend integrates one paid simulation engine (Infrared.city), several free no-auth open-data REST sources (OpenStreetMap, Barcelona Open Data CKAN, ICGC), and two browser map-tile providers (Mapbox, Cesium Ion). The design principle throughout: **network fetches are disk-cached, and every external call degrades gracefully** (logged warning, never faked data) so the offline/mock path always works.

## APIs & External Services

**Urban-climate simulation (the ground-truth engine):**
- **Infrared.city** — UTCI (thermal-comfort-index) and TCS (thermal-comfort-statistics) area simulations
  - SDK/Client: `infrared-sdk` Python package (`InfraredClient`, `UtciModelRequest`, `TcsModelRequest`, `TimePeriod`, `Location` from `infrared_sdk.models`/`.analyses.types`)
  - Boundary module: `coolspend/sdk_client.py` (the ONLY place the SDK is imported, and only lazily inside `_live_utci` / `_live_tcs` / `get_buildings_for_polygon`)
  - Calls used: `client.buildings.get_area(polygon)`, `client.ground_materials.get_area(polygon)`, `client.weather.get_weather_file_from_location` + `filter_weather_data`, `client.run_area_and_wait(payload, polygon, buildings=, vegetation=, ground_materials=)`
  - Auth: `INFRARED_API_KEY` env var, read by the SDK from the environment; presence validated in `_live_utci`, never logged/embedded/returned (security note in `coolspend/api_server.py` and `sdk_client.py`)
  - Backend modes (`INFRARED_BACKEND` env): `mock` (deterministic synthetic scalar, labelled "NOT MEASURED DATA"), `cached` (disk replay, raises `FileNotFoundError` on miss — never falls through to mock), `live` (real metered run, result written to cache for offline replay)
  - Rate guard: `SimBudget` (`coolspend/sdk_client.py`) caps live UTCI calls so the NSGA-II hot path cannot reach the SDK; live calls only after Top-3 selection
  - Run window: fixed single-month July 09:00–17:00 (`UTCI_TIME_PERIOD`)
  - Known issue + fallback: Infrared weather endpoint returns HTTP 500 server-side (since 2026-05-29); `_resolve_weather_data` falls back to a measured EPW file (`coolspend/epw_weather.py`) controlled by `INFRARED_WEATHER_SOURCE` (auto/epw/infrared)

**Geospatial context (free, no auth):**
- **OpenStreetMap — Overpass API** — building footprints, road carriageways, and street-furniture exclusions for tree placement
  - Endpoints: `https://overpass-api.de/api/interpreter` (primary) and `https://overpass.kumi.systems/api/interpreter` (fallback), in `coolspend/osm_roads.py`
  - Modules: `coolspend/osm_buildings.py` (footprints — most important placement exclusion, unioned with Infrared buildings when live), `coolspend/osm_roads.py` (vehicle carriageways only; plazas/footways stay plantable), `coolspend/osm_features.py` (hydrants, crossings, bus stops, lamps, signals, manholes, overhead power lines with per-feature keep-out radii)
  - Auth: none. License: © OpenStreetMap contributors (ODbL)
  - Caching: one Overpass query per bbox, cached to `coolspend/cache/osm_*/`. Network failure -> "no exclusion" + logged warning

**Map tiles (browser-side, deck.gl/Mapbox):**
- **Mapbox GL** — basemap (satellite `mapbox/satellite-v9` default; `mapbox/light-v11` when 3D tiles active) and terrain DEM elevation
  - Used in `web/src/components/Scene.tsx`; terrain tiles in `web/src/lib/elevation.ts` (`api.mapbox.com/v4/mapbox.mapbox-terrain-dem-v1/...`)
  - Auth: `VITE_MAPBOX_TOKEN` (public `pk.` token via `import.meta.env`). Absent -> app routes to `web/src/components/FallbackScene.tsx` (flat dark map, overlays still render)
- **Cesium Ion** — proxies Google Photorealistic 3D Tiles (asset id `2275207`)
  - `web/src/lib/cesium.ts`: `GET https://api.cesium.com/v1/assets/2275207/endpoint` with `Authorization: Bearer <token>`, then loads the tileset via `@loaders.gl/3d-tiles`
  - Auth: `VITE_CESIUM_ION_TOKEN` (`eyJ...`). Optional — absent or rejected -> Mapbox basemap + overlays, no photoreal 3D (currently disabled by default per `README.md`)

## Data Storage

**Databases:**
- None. No SQL/NoSQL database. State is files: JSON/GeoJSON bundles + on-disk caches.

**File storage / on-disk caches (all under `coolspend/cache/`, gitignored):**
- `cache/infrared/{metric}_{ghash}.json` — UTCI/TCS sim results (mock and live), keyed by 16-char SHA-256 of geometry (`coolspend/sdk_client.py`)
- `cache/bcn_data/` — Barcelona tree-inventory CSVs + CKAN resolve responses (30-day TTL)
- `cache/population/` — Padró barri-population aggregation (30-day TTL)
- `cache/osm_roads/`, `cache/osm_features/`, `cache/osm_buildings/` — Overpass results per bbox
- `cache/bcn_lidar/hmitjana_2016_2017.tif` — ICGC LiDAR canopy-height raster (~166 MB, downloaded once)
- Curated web bundles served statically: `web/public/web_bundle/` (default showcase), `web/public/eval_bundle/` (runtime `/api/evaluate` output) — written by `coolspend/export_web.py`
- Precomputed citywide plan: `web/public/citywide_plan.json`; scored grid input under `L1_INGEST_data/`

**Caching:** In-process caches too — `_AREA_CTX_CACHE` (buildings+ground per polygon hash) and `_WEATHER_CACHE` (per lat,lon) in `coolspend/sdk_client.py` ensure Infrared site context + weather are fetched once per run.

## Authentication & Identity

- No end-user auth / login. The app is a single-tenant decision tool.
- Service auth only: `INFRARED_API_KEY` (server-side env), `VITE_MAPBOX_TOKEN` + `VITE_CESIUM_ION_TOKEN` (browser public tokens).

## Open-Data Sources (REST, no API key)

- **Barcelona Open Data — CKAN** (`https://opendata-ajuntament.barcelona.cat/data/api/3/action`), License CC-BY 4.0:
  - **Street-tree inventory** — `package_show?id=arbrat-viari` (street trees, ~145,391 trees / 218 species), also `arbrat-zona`, `arbrat-parcs`. Resolved via `package_show` because resource UUIDs rotate (slugs are stable). No datastore/SQL API — CSV download. `coolspend/bcn_data.py`. Coords `latitud`/`longitud` are WGS84; species via `cat_nom_cientific`. No per-tree dimensions (removed 2021) — dimensions come from the species table.
  - **Population (Padró municipal d'habitants)** — slug `pad_mdbas`, latest annual CSV `<YEAR>_pad_mdbas.csv`, aggregated to `{codi_barri: population}` for the WHO/3-30-300 "300 m catchment" population-served metric. `coolspend/population.py`.
  - User-Agent: `CoolSpend-Buildathon/2.0 (mailto:elkhouryrafik@gmail.com)`
- **Species dimensions — Verd Urbà (Diputació de Barcelona)** (`https://verd-urba.diba.cat`): categorical height/crown/leaf-cycle/shade-density bands for ~248 species. HTML-only, no API — scraped offline into the species table (`coolspend/bcn_species.py`); see `DATA_SOURCES.md` §B honesty flags.
- **ICGC + CREAF LiDAR canopy height** (`https://datacloud.icgc.cat/.../variables-biofisiques-arbrat-...tif`): 20 m mean tree-height raster, EPSG:25831, 2016–2017, CC-BY 4.0, no key. Downloaded once and sampled locally with rasterio (`coolspend/bcn_lidar.py`); WMS/`/vsicurl` paths verified unusable.

## Satellite / Remote-Sensing Layers (citywide heat scoring)

The 494-cell Barcelona heat-vulnerability grid (`scored_grid.geojson`, consumed by `coolspend/citywide.py` and `/api/citywide/*`) is built from remote-sensing sub-scores (see `coolspend/docs/scored_grid_datasheet.md`):
- `s1_sealed` (0.45 weight) — **Sentinel-1 C-band SAR**
- `s2_lst_anomaly` (0.20) — **Landsat 8/9 TIRS** thermal land-surface-temperature anomaly
- `s3_inverted_ndvi` (0.15) — **Sentinel-2 MSI** optical (1 − NDVI)
- `s4_mismatch` (0.05) + `prpi` (0.15) — derived indices
- Honesty: the composite *formula* is exactly reproducible in-repo (`python -m coolspend.provenance`, residual < 1e-9 over 494 cells); the raw SAR/LST classifiers live in an upstream `L1_INGEST_data` pipeline not fully documented here.

## Monitoring & Observability

**Error Tracking:** None (no Sentry/etc.). Failures are handled via `logging` warnings and graceful degradation throughout `coolspend/` (each logger named `coolspend.<module>`).

**Logs:** Python `logging` (e.g. `logging.getLogger("coolspend.api_server")`); `coolspend/api_server.py` `__main__` sets `basicConfig(level=INFO)`. `SimBudget.record` logs every metered UTCI sim call for audit.

## CI/CD & Deployment

**Hosting:** Hugging Face Spaces (Gradio SDK, `README.md` front-matter `app_file: coolspend/app.py`); `huggingface_hub` used to publish. The deck.gl web client is the primary deliverable and can be served by the FastAPI app from `web/dist`.

**CI Pipeline:** None detected in repo root.

## Environment Configuration

**Required / used env vars:**
- Backend: `INFRARED_API_KEY` (live only), `INFRARED_BACKEND`, `INFRARED_WEATHER_SOURCE`, `COOLSPEND_API_PORT`
- Frontend: `VITE_MAPBOX_TOKEN` (required for full scene), `VITE_CESIUM_ION_TOKEN` (optional)

**Secrets location:**
- Backend: gitignored `.env` at repo root (loaded via python-dotenv)
- Frontend: gitignored `web/.env.local` (template `web/.env.local.example`)
- Never committed; `INFRARED_API_KEY` never logged or returned over HTTP.

## Webhooks & Callbacks

**Incoming:** None.

**Outgoing:** None (no event push; all integration is request/response or one-shot file download).

## HTTP API Surface (consumed by the web client)

Served by `coolspend/api_server.py` (CORS-restricted to Vite dev origins):
- `GET  /api/health` -> `{status, backend}`
- `POST /api/buildings` `{polygon}` -> area, context building count, impervious-pavement preview (fast)
- `POST /api/evaluate` `{polygon, budget_eur, w_thermal, w_ecological}` -> web bundle (decision/boundary/trees/bounds + UTCI PNGs); polygon size-capped server-side (400 m²–62,500 m²); falls back to `mock` backend on any live fault so a draw never 500s
- `GET  /api/citywide/scan` and `POST /api/citywide/allocate` -> 494-cell ranking / €-budget allocation

---

*Integration audit: 2026-06-01*
