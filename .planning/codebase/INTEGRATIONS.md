# External Integrations

**Analysis Date:** 2026-05-27

> This document covers ALL external data sources, APIs, and inter-module contracts
> in the current CoolSpend codebase. Every env var, endpoint, cache path, and
> function signature is sourced from the actual code, not reference archives.

---

## External APIs

### Infrared SDK (MICROCLIMATE SIMULATION)

**Service:** infrared.city SDK — urban microclimate simulation (UTCI felt-temperature at 1.1m).

**Entry point:** `coolspend/sdk_client.py`

**Authentication:**
- Env var: `INFRARED_API_KEY` (validated at `sdk_client.py:362`)
- Key read internally by `infrared_sdk.InfraredClient` — never logged or stored by CoolSpend
- Raises `EnvironmentError` if `INFRARED_BACKEND=live` and key is missing

**Backend modes** (controlled by `INFRARED_BACKEND` env var, evaluated at dispatch time, not import):

| Mode | Env value | Behaviour | Network |
|---|---|---|---|
| **mock** | `INFRARED_BACKEND=mock` (default) | Returns deterministic scalar UTCI: baseline=41.0°C, intervention=30.5°C (canopy at full coverage). Scalar only — no grid. | None |
| **cached** | `INFRARED_BACKEND=cached` | Reads from `coolspend/cache/infrared/{metric_key}_{hash16}.json`. Raises `FileNotFoundError` on cache miss — does NOT fall through to mock. | None |
| **live** | `INFRARED_BACKEND=live` | Calls real Infrared API via `InfraredClient.run_area_and_wait`. Writes result to cache on success. | Yes |

**API endpoints used** (via `infrared_sdk`):

| Endpoint | Called At | Purpose |
|---|---|---|
| `client.buildings.get_area(polygon)` | `sdk_client.py:422` | Fetch building footprints for site polygon (from OSM via Infrared) |
| `client.ground_materials.get_area(polygon)` | `sdk_client.py:424` | Fetch ground material layers (OPTIONAL — degrades gracefully) |
| `client.weather.get_weather_file_from_location(lat, lon, radius=50)` | `sdk_client.py:440` | Find nearest weather station within 50 km |
| `client.weather.filter_weather_data(identifier, time_period)` | `sdk_client.py:447` | Filter weather to single-month daytime window |
| `client.run_area_and_wait(payload, polygon, buildings, vegetation, ground_materials)` | `sdk_client.py:465` | Run UTCI simulation and wait for result. Returns `merged_grid` (numpy array). |

**Simulation window** (hardcoded in `sdk_client.py:216`):
```python
UTCI_TIME_PERIOD = {
    "start_month": 7, "start_day": 1, "start_hour": 9,
    "end_month": 7, "end_day": 31, "end_hour": 17,
}
```
Single-month July 09:00-17:00 (Barcelona peak-heat daytime). IMPORTANT: the server requires a single-month `TimePeriod` — multi-month windows are not supported.

**Vegetation injection** (`sdk_client.py:_trees_to_vegetation()` line 289):
Converts placed trees to GeoJSON Point Features with `natural: "tree"`, `species`, `height`, `diameter_crown` properties. Empty input (`trees_lonlat=[]`) means bare site (baseline). Per-species crown+height sourced from `coolspend/bcn_species.py` (Verd Urba bands).

**Ground materials filter** (`sdk_client.py:222`):
Only these Infrared material names reach the simulation:
`{"asphalt", "concrete", "soil", "vegetation", "water"}`
Extra keys from the API (e.g. `"building"`) are stripped.

**Rate limits / Guarding:**
- `SimBudget` class (`sdk_client.py:121`) caps live UTCI calls per run (default `max_live_calls=3`)
- Raises `RuntimeError` if exceeded — designed to prevent NSGA-II hot path from making API calls
- Used in `optimizer.validate_top3_with_infrared()` and `calibration.run_calibration_study()` (separate budgets)
- No per-IP or per-session rate limiting at the application level (noted in README.md as pre-production limitation)

**Public API functions** (`sdk_client.py`):
- `get_baseline_utci(geometry: dict) -> UTCIResult` — baseline (bare polygon)
- `get_intervention_utci(geometry: dict) -> UTCIResult` — post-intervention (with trees)

**UTCIResult dataclass** (`sdk_client.py:85`):
Fields: `utci_c`, `metric` ("utci_at_1.1m"), `backend` ("mock"|"cached"|"live"|"cached:mock"|"cached:live"), `geometry_hash`, `disclaimer`, `source`, `heat_stress_area_m2` (optional), `grid_cells_total` (optional), `merged_grid` (optional).

**Key computed values:**
- `cooled_footprint_m2()` (`sdk_client.py:245`): cells where `baseline_grid - intervention_grid >= 0.5` degC (perceptible comfort change threshold). 1 m pitch = 1 m^2/cell.
- `UTCI_HEAT_STRESS_C = 26.0` — moderate heat stress threshold (uses window-mean aggregate, not instantaneous peaks)
- `COOLED_MIN_DROP_C = 0.5` — minimum perceptible cooling per cell

---

### Barcelona Open Data (CKAN) — Tree Inventory

**Service:** Open Data BCN CKAN — municipal street tree inventory.

**Entry point:** `coolspend/bcn_data.py`

**Authentication:** None (public CC-BY 4.0 data, no-auth JSON/CSV CKAN).

**CKAN base URL:** `https://opendata-ajuntament.barcelona.cat/data/api/3/action`

**API endpoints used:**

| Endpoint | Called At | Purpose |
|---|---|---|
| `package_show?id={slug}` | `bcn_data.py:69` | Resolve stable dataset slug to current CSV resource UUID (UUIDs rotate; slugs are stable) |
| Raw CSV download via `resource.url` | `bcn_data.py:98` | Download actual inventory CSV (~MBs) |

**Dataset slugs:**
```python
INVENTORY_SLUGS = ("arbrat-viari", "arbrat-zona", "arbrat-parcs")
DEFAULT_SLUG = "arbrat-viari"  # street trees — relevant for street planting
```

**Public API:**
- `resolve_resource(slug) -> dict` — get current CSV resource info (cached 30 days)
- `download_inventory(slug) -> Path` — download CSV to cache (cached 30 days)
- `load_trees(slug, bbox) -> list[dict]` — real existing trees with `{lon, lat, species, species_id, district}`
- `species_frequency(slug) -> dict[str, int]` — `{scientific_name: count}` over whole inventory

**Data schema** (from CKAN CSV columns: `latitud`/`longitud` WGS84, `cat_nom_cientific` scientific name, `cat_especie_id`, `nom_districte`):
- Coordinates are WGS84 (EPSG:4326) — NOT projected
- No per-tree height or crown diameter (removed from inventory in 2021)
- License: CC-BY 4.0 (Ajuntament de Barcelona)
- User-Agent: `CoolSpend-Buildathon/2.0 (mailto:elkhouryrafik@gmail.com)`

**Cache:** `coolspend/cache/bcn_data/` — 30-day TTL (`CACHE_TTL_SEC = 30 * 24 * 3600`)

---

### ICGC + CREAF LiDAR Canopy Height

**Service:** ICGC (Institut Cartografic i Geologic de Catalunya) + CREAF — "Variables biofisiques de l'arbrat de Catalunya" mean tree height raster.

**Entry point:** `coolspend/bcn_lidar.py`

**Authentication:** None (CC-BY 4.0, no API key).

**Raster source:**
```
URL: https://datacloud.icgc.cat/datacloud/variables-biofisiques-arbrat/tif_unzip/
     variables-biofisiques-arbrat-v1r1-hmitjana-2016-2017.tif
Size: ~166 MB
CRS:  EPSG:25831 (ETRS89 / UTM zone 31N)
Resolution: 20 m pixel
Vintage: 2016-2017
Product: LiDAR + forest-inventory calibrated mean tree height (m)
License: CC-BY 4.0 (credit ICGC and CREAF)
```

**Access method (critical):**
- WMS GetFeatureInfo returns only rendered RGB (all 0) — unusable
- GDAL /vsicurl remote sampling returns 0 (striped TIFF, not COG) — unusable
- The ONLY reliable path is local raster + rasterio sampling
- Module downloads the full raster ONCE into cache (~166 MB)

**Public API:**
- `ensure_raster(auto_download=True) -> bool` — download raster if absent
- `canopy_height_m(lon, lat, auto_download=True) -> float | None` — measured canopy height at WGS84 point
  - Returns None for NoData=0 (dense urban = no measured canopy = high planting opportunity)
  - Point-level cache: `coolspend/cache/bcn_lidar/pt_{lat}_{lon}.json`
- `site_canopy_context(lon, lat) -> dict` — `{measured_canopy_height_m, interpretation, source}`

**Honesty:** Dense urban Barcelona (Glories, Eixample, Ciutadella) is largely NoData=0 — the product was built for forest stands, not isolated street trees. For CoolSpend this is useful as site context: 0 = "bare, high planting opportunity".

---

## Data Sources (File-Based)

### Barcelona Species Table

**Entry point:** `coolspend/bcn_species.py`

**Source:** In-code `SPECIES_TABLE` tuple of 12 `Species` dataclasses (hardcoded, not fetched).

**Provenance:**
- Scientific names from top species in `arbrat-viari` (145k trees)
- Dimensions (crown_diameter_m, height_m) from Verd Urba band midpoints (Diputacio de Barcelona)
- Shade density and leaf cycle from Verd Urba + standard arboricultural references
- `cooling_score` in [0,1] is a literature-backed PROXY (Rahman et al. 2020 Int J Biometeorol) — ranking only, not measured cooling

**Species dataclass** (`bcn_species.py:34`):
```python
@dataclass(frozen=True)
class Species:
    scientific: str          # join key (matches arbrat-viari cat_nom_cientific)
    common: str              # English common name
    height_m: float          # Verd Urba band midpoint
    crown_diameter_m: float  # Verd Urba band midpoint
    leaf_cycle: str          # "deciduous" | "evergreen"
    shade_density: str       # "dense" | "medium" | "light"
    height_band: str         # auditable band label
    crown_band: str          # auditable band label
```

**Public API:**
- `get_species(scientific) -> Species | None` — lookup by scientific name
- `cooling_score(sp) -> float` — normalized [0,1] cooling proxy
- `cooling_score_by_name(scientific) -> float` — species lookup with fallback (0.5 for unknown)
- `palette(top_n=None) -> tuple[Species]` — full or top-N sorted palette

### Default Site GeoJSON

**File:** `coolspend/data/angels_site.geojson`

**Status:** MOCK — hand-authored fixture (Placa dels Angels, Barcelona). NOT surveyed OSM data. See MOCKS.md.

**Loaded by:** `coolspend/spatial_engine.py:load_site()`

### Cost Model Constants

**Entry point:** `coolspend/cost_model.py`

**Status:** DECLARED assumptions (REQUIRES_VERIFICATION). Full itemized `DEFAULT_COST_TABLE` replaces old hardcoded CAPEX_PER_TREE_EUR=350.
- CapEx: ~3,000 EUR/tree (fully loaded — vs old 350 which was ~10x too low)
- OpEx: ~180 EUR/tree/yr
- Horizon: 40 yr (urban sealed-site context)
- See MOCKS.md cost-line ledger for per-line source tags

---

## File System: Cache Directory

### Structure

```
coolspend/cache/
  infrared/                   # UTCI simulation cache
    utci_baseline_{hash16}.json     # Baseline UTCI results
    utci_intervention_{hash16}.json # Intervention UTCI results
    (metric_key = "utci_baseline" | "utci_intervention")
    (hash16 = first 16 chars of SHA-256 of geometry dict JSON, sorted keys)
  bcn_data/                   # Barcelona Open Data tree inventory cache
    resolve_{slug}.json             # CKAN resource metadata (30-day TTL)
    {slug}.csv                      # Raw inventory CSV (30-day TTL)
  bcn_lidar/                  # ICGC+CREAF canopy height cache
    hmitjana_2016_2017.tif         # Full raster (~166 MB, gitignored)
    pt_{lat}_{lon}.json             # Per-point sampled heights
```

**Cache naming:** JSON cache files use SHA-256(geometry_dict, sort_keys=True) hex digest, first 16 characters.

**Cache behaviour by backend:**
- `mock`: writes to cache on every call (so a subsequent `cached` run replays it)
- `live`: writes live result to cache on every call
- `cached`: reads only -- raises FileNotFoundError on miss (never falls through to mock)

**Git:** Entire `coolspend/cache/` directory is gitignored (see `.gitignore` line 6).

### Outputs Directory

```
outputs/
  top3_configurations.json    # Decision artifact (DEC-01 + DEC-02)
  audit_record.json           # Provenance record with surrogate flags
  pareto_front.png            # Pareto front visualization
```

**Written by:** `coolspend/optimizer.py:save_outputs()` (line ~185 from full file)

---

## Inter-Module Contracts

### Module Dependency Graph

```
app_pipeline.py
  ├── optimizer.py
  │     ├── spatial_engine.py  (thermal_relief, is_valid_location, local_m_to_latlon, ...)
  │     ├── rules_engine.py    (ecological_score)
  │     ├── cost_model.py      (total_cost)
  │     ├── bcn_species.py     (SPECIES palette for optimizer's species gene)
  │     └── sdk_client.py      (LAZILY inside validate_top3_with_infrared only)
  ├── cost_model.py            (cost_per_utci_degree, CostTable, GrowthDiscountParams)
  └── sdk_client.py            (SimBudget, UTCIResult)

main.py → optimizer.py (all pipeline stages)

app.py → app_pipeline.py (Gradio UI calls run_decision)

spatial_engine.py
  ← also used by bcn_lidar.py (assert_crs_roundtrip from sdk_client)

bcn_species.py
  ← used by sdk_client.py (_trees_to_vegetation calls get_species)
  ← used by optimizer.py (SPECIES palette for species gene pool)

calibration.py (standalone study)
  ├── optimizer.py (calibration doesn't need full optimizer, but references sdk_client)
  └── sdk_client.py (SimBudget, get_intervention_utci)
```

### Key Data Contracts

**config dict** (optimizer decision variable):
```python
config = {
    "trees": [
        {"x_m": float, "y_m": float, "species": str, "active": bool},
        # ... up to 12 trees (N_TREES)
    ],
}
```
- Coordinates are site-local metres (SW corner origin, via `spatial_engine.py:local_m_to_latlon()`)
- `active: False` means the tree slot is unused (allows <12 tree configurations)
- Shared across: `optimizer.py`, `spatial_engine.py`, `rules_engine.py`, `cost_model.py`, `sdk_client.py`

**geometry dict** (SDK client input):
```python
geometry = {
    "polygon_lonlat": [[lon, lat], ...],  # WGS84 ring (required for live backend)
    "trees_lonlat": [                      # placed trees (empty = baseline)
        {"lon": float, "lat": float, "species": str},
    ],
    # mock only:
    "width_m": float,       # site width (for mock coverage fraction)
    "coverage_fraction": float,  # canopy coverage proportion (mock only)
}
```

**UTCIResult dataclass** (SDK output):
```python
@dataclass
class UTCIResult:
    utci_c: float
    metric: str = "utci_at_1.1m"
    backend: str           # "mock" | "cached" | "live" | "cached:mock" | "cached:live"
    geometry_hash: str     # 16-char SHA-256 prefix
    disclaimer: str        # "NOT MEASURED DATA..." for mock/cached
    source: str            # human-readable provenance
    heat_stress_area_m2: float | None = None  # grid metric (live only)
    grid_cells_total: int | None = None
    merged_grid: list | None = None           # 2D UTCI grid (live only)
```

**Top-3 config dict** (ranked output, passed from optimizer to cost model to UI):
```python
{
    "rank": int,              # 1-3
    "label": str,             # "MAX_THERMAL_RELIEF" | "BALANCED" | "MAX_ECOLOGICAL"
    "trees": [...],           # same config dict shape
    "tree_count": int,
    "delta_tmrt_c": float,    # surrogate (analytical proxy)
    "delta_tmrt_uncertainty_c": float (4.0),
    "ecological_score": float,
    "topsis_score": float,
    "baseline_utci_c": float,
    "validated_utci_c": float, # mock | cached | live
    "delta_utci_c": float,
    "validated_backend": str,
    "cost_eur": float,
    "cost_per_utci_degree": {
        "value": float, "unit": "EUR/degC",
        "confidence": str, "sources": [str]
    },
    "disclaimer": str,
}
```

### CRS Contract (SPATIAL-03)

**Single authoritative CRS conversion** in `coolspend/spatial_engine.py`:
```python
_TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32631", always_xy=True)  # lon,lat -> easting,northing
_TO_WGS = Transformer.from_crs("EPSG:32631", "EPSG:4326", always_xy=True)  # easting,northing -> lon,lat
```
- No other module may convert CRS (`spatial_engine.py` docstring, line 27)
- `assert_crs_roundtrip(ring)` enforces <1m round-trip tolerance, raising `CRSConsistencyError` on failure (D-07)
- Functions: `latlon_to_local_m(lon, lat)` and `local_m_to_latlon(x, y)` for site-local frame
- Site origin is mutable module state (`SITE_ORIGIN_LON/LAT`, `SITE_WIDTH_M`, `SITE_DEPTH_M`), reset by `reset_site_origin()` per test

---

## Output Formats

| Format | Produced By | Contents |
|---|---|---|
| JSON | `optimizer.py:save_outputs()` | `outputs/top3_configurations.json` — ranked decision artifact with full tree placements, metrics, KPI |
| JSON | `optimizer.py:write_audit_record()` | `outputs/audit_record.json` — provenance flags, surrogate status, TOPSIS weights |
| PNG | `optimizer.py:plot_pareto()` | `outputs/pareto_front.png` — 2D Pareto front (thermal vs ecological) |
| PNG | `app_viz.py:render_before_after()` | Temporary file — side-by-side baseline vs intervention UTCI heatmap with site geometry + tree placements |
| JSON | `sdk_client.py:_dispatch()` | `coolspend/cache/infrared/{metric}_{hash16}.json` — cached UTCI simulation results |
| CSV | `bcn_data.py:download_inventory()` | `coolspend/cache/bcn_data/{slug}.csv` — downloaded Barcelona tree inventory |

---

## Environment Variables Summary

| Variable | Required For | Default | Read In |
|---|---|---|---|
| `INFRARED_BACKEND` | SDK dispatch | `"mock"` | `sdk_client.py:68` |
| `INFRARED_API_KEY` | Live Infrared SDK | None (raises Error if live) | `sdk_client.py:362` |

**Secrets location:** `.env` file at project root (existence noted; contents NEVER read or logged). File is gitignored.

---

## Webhooks & Callbacks

**Incoming:** None. All data is fetched via pull (HTTP GET) or loaded from local files.

**Outgoing:** None. Infrared SDK uses synchronous polling (`run_area_and_wait`) — no webhook registration.

---

*Integration audit: 2026-05-27*
