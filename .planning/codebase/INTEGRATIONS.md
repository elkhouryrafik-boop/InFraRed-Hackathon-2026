# External Integrations

**Analysis Date:** 2026-05-21
**Source context:** NatureGooddest reference code. All paths below are in the reference workspace
`C:\Users\Rafik\OneDrive\Python Resources\Hackathon\`.

---

## Infrared SDK (PRIMARY — the new integration)

**What it is:** Urban CFD simulation API — wind, UTCI, Tmrt, solar radiation, daylight, sky-view factor.
**Hackathon role:** The fitness oracle for the NSGA-II thermal objective (Tree Budget challenge).

### Backend boundary — three modes

The reference mock clients (`infrared_client_v2.py` and `nature_infrared_client.py`) implement a
three-way dispatch controlled by the `INFRARED_BACKEND` environment variable:

| Mode | Env value | Behaviour | Offline? |
|---|---|---|---|
| **mock** | `INFRARED_BACKEND=mock` (default) | Returns deterministic hand-crafted 24×24 synthetic fields. No network call. Fields are physically plausible (not random) but explicitly labelled `NOT MEASURED DATA`. | YES |
| **cached** | `INFRARED_BACKEND=cached` | Reads from `cache/infrared/{metric}_{hash16}.json` on disk. Falls through to mock if file absent. No network call. | YES |
| **live** | `INFRARED_BACKEND=live` | Was `NotImplementedError` in the mock clients (these clients never wired live). The real SDK path is `from infrared_sdk import InfraredClient` — used directly in `scripts/sim/run_infrared_utci_angels*.py` in NatureGooddest (NOT copied here). | NO — requires key |

**Critical timing constraint:** The Infrared hackathon API key issues **May 27, 2026** (kickoff).
coolspend must be architecturally offline-capable until then. Use `INFRARED_BACKEND=mock` or
pre-populate `cache/infrared/` with reference runs.

### Two client files — confirmed identical

`infrared_client_v2.py` and `nature_infrared_client.py` are **byte-for-byte identical** (confirmed
by reading both). Both carry the same `DEPRECATED 2026-05-19` banner. The duplication is a copy
artifact — only one file needs to be ported.

### Mock client public methods (from `infrared_client_v2.py`)

```python
simulate_tmrt(geometry: dict, climate: dict | None = None) -> dict
    # Tmrt at 1.1m pedestrian height. 24×24 grid.
    # mock base: open=58.2°C, under-canopy=39.5°C

simulate_utci(geometry: dict, climate: dict | None = None) -> dict
    # UTCI felt-temperature. 24×24 grid.
    # mock base: open=41.0°C, under-canopy=30.5°C

simulate_wind(geometry: dict, climate: dict | None = None) -> dict
    # Wind speed magnitude at 1.5m. 24×24 grid.
    # mock base: open=4.2 m/s, under-canopy=2.3 m/s

simulate_all(geometry: dict, climate: dict | None = None) -> dict
    # Convenience: {"tmrt": ..., "utci": ..., "wind": ...}
```

**geometry dict contract:**
```python
{
    "site_id": str,          # e.g. "BCN-ANGELS-001"
    "polygon": list[list],   # [[x,y], ...] in local metres
    "fired_patterns": list,  # e.g. ["P01", "P14"] — drives canopy mask logic
    "config_id": str,        # "C1"|"C2"|"C3" — drives mock canopy size
}
```

**Response dict shape:**
```python
{
    "metric": str,           # "tmrt_at_1.1m" | "utci_at_1.1m" | "wind_speed_at_1.5m"
    "grid_rows": int,        # 24
    "grid_cols": int,        # 24
    "field": list[list[float]],
    "stats": {
        "mean": float, "p10": float, "p90": float,
        "min": float, "max": float, "unit": str
    },
    "metadata": {
        "backend": str,      # "mock"|"cached"|"live"
        "model_version": str,
        "latency_ms": int,
        "geometry_hash": str,  # first 16 chars of SHA-256 of geometry JSON
        "cached_at": str,
        "citation": str,
        "disclaimer": str    # "NOT MEASURED DATA — synthetic field for UI integration only."
    }
}
```

### Real SDK path (for live mode after May 27)

From `infrared_hackathon.md` (the hackathon landing page scraped into the workspace):
```python
from infrared_sdk import InfraredClient
from infrared_sdk.analyses.types import WindModelRequest, AnalysesName

polygon = {"type": "Polygon", "coordinates": [...]}  # WGS84 GeoJSON
with InfraredClient() as client:
    area = client.buildings.get_area(polygon)
    result = client.run_area_and_wait(
        WindModelRequest(analysis_type=AnalysesName.wind_speed, wind_speed=15, wind_direction=180),
        polygon, buildings=area.buildings,
    )
print(result.merged_grid)  # numpy array
```
- Install: `pip install infrared-sdk`
- Auth: `INFRARED_API_KEY` env var (read by SDK internally)
- Returns `result.merged_grid` as a numpy array
- 8 analysis types: wind, UTCI, Tmrt, solar radiation, daylight, sky-view, direct sun hours (per hackathon docs)
- Average simulation time: `< 1 min` per polygon (per hackathon landing page)

### Offline strategy for coolspend

The optimizer must NOT call the live SDK per chromosome — that would require ~10,000 API calls
per run (100 gen × 100 pop). NatureGooddest solved this identically:

**`nature_nsga2_coolstock.py` uses the surrogate — NOT the SDK — inside the NSGA-II loop.**
Specifically, `COOLSTOCKProblem._evaluate()` (line 204) calls `delta_tmrt_surrogate()` (line 107)
which is pure math — no network call. The Infrared SDK is called separately, offline, to compute
pre-cached baselines and a small set of interventions. The optimizer then reads from those cached
values.

For coolspend tree optimizer, the same pattern applies:
1. Call Infrared SDK once per baseline polygon → cache to disk
2. Call Infrared SDK for a small number of representative interventions (e.g. 10–50 pre-placed tree configurations) → cache to disk
3. NSGA-II fitness evaluates against those cached values or uses a fast surrogate (SOLWEIG-style Tmrt proxy from `nature_metrics.py`)

**Cache location pattern:** `cache/infrared/{metric}_{geometry_hash16}.json`

---

## OSM / GeoJSON Data

**What:** Building footprints, street centrelines, open-space polygons for collision detection
and site boundary.

**Source in NatureGooddest:**
- `L1_INGEST_data/geometry/angels_buildings.geojson` — 746 buildings, OSM ODbL 1.0
- `L1_INGEST_data/geometry/angels_open_spaces.geojson` — 42 polygons
- `L1_INGEST_data/geometry/angels_streets.geojson` — 1,429 line segments
- Retrieved 2026-05-12 via Overpass API

**License:** OpenStreetMap ODbL 1.0 (open, attribution required)

**For coolspend:** These files are NOT copied into the hackathon workspace. New GeoJSON
must be fetched for the demo site (could reuse Plaça dels Àngels per `HANDOFF.md` open question,
or pick a new site). The V2 plan (`docs/plans/2026-05-20-tree-budget-optimizer-v2.md`) calls
for creating `data/site_context.geojson`.

**Overpass API query pattern** used in NatureGooddest (inferred from `nature_architecture.md`):
```
[out:json][timeout:25];
(way["building"](around:300, 41.3826, 2.1670););
out body; >; out skel qt;
```

**Honesty status:** VERIFIED (OSM ODbL 1.0, retrieved date documented in `audit_record.json`).

---

## EPW Climate Data

**What:** EnergyPlus Weather file — 8,760-hour TMY (Typical Meteorological Year) with hourly
dry_bulb, relative_humidity, wind_speed, global_horizontal_radiation.

**Source in NatureGooddest:**
- File: `L1_INGEST_data/climate/Barcelona_TMYx_2011-2025.epw`
- Provider: climate.onebuilding.org (open data)
- WMO station: 081810 (Barcelona airport, ~10 km from Plaça dels Àngels)
- UHI note from `nature_metrics.py` (line 141-193): X4 El Raval urban canyon station (153 m
  from plaza) cross-validation shows +0.44°C delta vs airport EPW for daytime summer — within
  EPW interannual variability; no correction applied for UTCI > 32°C metric.

**Consumed by:** `nature_metrics.py` via `ladybug.epw.EPW` (loaded once, cached in `_EPW_CACHE`)

**For coolspend:** NOT copied to hackathon workspace. If EPW-based baseline UTCI is needed,
fetch from climate.onebuilding.org for the demo site. Alternatively, let Infrared SDK provide
the climate baseline entirely (SDK uses its own climate data source).

**Honesty flag:** Confidence = HIGH after X4 cross-validation (documented in
`L1_INGEST_data/climate/x4_raval_uhi_validation.json` in NatureGooddest).

---

## GBIF Biodiversity Data

**What:** Species occurrence records for pollinators in El Raval (Barcelona).

**Source in NatureGooddest:**
- File: `L1_INGEST_data/biodiversity/angels_gbif_pollinators.json`
- GBIF taxonKeys: 4334, 6920 — 38 species, 266 records
- License: CC0 (public domain)
- Retrieved: 2026-05-13

**Consumed by:** `nature_nsga2_coolstock.py` — `pollinator_corridor_score()` function (line 158)
references "GBIF El Raval data" but the function itself is pure geometry (distance from green
anchor nodes); it does not read the JSON at runtime. The JSON is referenced for scoring provenance
only.

**For coolspend:** LEAVE BEHIND unless pollinator corridor is a desired objective. The V2 plan
focuses on thermal + ecological spacing objectives only.

**Honesty flag:** Data is real GBIF records but the scoring function that cites it contains a
known audit finding (C10 / 09 C-1) — the y_m clamp causes F3 to be effectively constant across
the Pareto front. The corridor score is **not a meaningful optimization signal** in the current form.

---

## Barcelona Open Data (BCN CKAN)

**What:** Real-time municipal open data — used by `bcn_opendata.py` in NatureGooddest.

**Source:** `bcn_opendata.py` (NOT copied to hackathon workspace)
- Runtime-fetched from CKAN endpoint on each demo load
- License: CC-BY 4.0

**For coolspend:** NOT ported. Not relevant to the tree budget optimizer.

---

## ESA WorldCover / Sentinel Canopy Data

**What:** 10m resolution land-cover layer for canopy cover percentage.

**Source in NatureGooddest:**
- File: `L1_INGEST_data/sentinel/angels_canopy_cover.json`
- DOI: ESA WorldCover 2021 v200 (CC-BY 4.0)
- Value used: canopy_cover_pct = 0% for Plaça dels Àngels (paved plaza, no trees)

**For coolspend:** LEAVE BEHIND unless initial canopy coverage is a constraint input.

---

## ÖKOBAUDAT (Embodied Carbon)

**What:** German lifecycle assessment database for construction materials.

**Source in NatureGooddest:**
- File: `L1_INGEST_data/carbon/oekobaudat_coolstock_materials.json`
- Entry used: `steel_scaffold` — GWP 2.491 kgCO2e/kg, A1-A3, EN 15804+A2, unit verified as "kg"
- Used in `carbon_headroom_kgco2e()` in `nature_metrics.py` (line 441)

**For coolspend tree optimizer:** LEAVE BEHIND (trees have different embodied carbon math;
CapEx/OpEx model from CONCEPT_REPORT.md is cost-based not carbon-based).

---

## Iungman 2023 Lancet (Heat Mortality)

**What:** City-level heat mortality avoidance coefficients for Barcelona.

**Source in NatureGooddest:**
- File: `L1_INGEST_data/health/isglobal_heat_mortality_bcn.json`
- DOI: 10.1016/S0140-6736(22)02585-5
- Used in `avoided_heat_mortality()` in `nature_metrics.py` (line 317)

**For coolspend:** OPTIONAL — could power a headline "lives saved at city scale" metric but
requires the JSON file to be present and the citywide-policy framing to be honest.
See the `honest_per_plaza_framing` caveat in `nature_metrics.py:368`.

---

## Webhooks & Callbacks

**Incoming:** None in reference code.
**Outgoing:** None in reference code. Infrared SDK uses polling (`run_area_and_wait`) not webhooks.

---

## Environment Variables Summary

| Variable | Required for | Default | Where read |
|---|---|---|---|
| `INFRARED_BACKEND` | Mock client dispatch | `"mock"` | `infrared_client_v2.py:59` |
| `INFRARED_API_KEY` | Live Infrared SDK | None (crashes if unset) | `infrared_sdk.InfraredClient` internals |

**Secrets location:** `.env` file at project root (referenced in `HANDOFF.md:36`). File not
present in the hackathon workspace — must be created before live runs.

---

## Mock / Unverified Data Flags

Per NatureGooddest's honesty contract, the following are explicitly mocked or unverified
and must NOT be cited as measured data in coolspend:

| Data / Function | Status | Location | Notes |
|---|---|---|---|
| `simulate_tmrt/utci/wind()` mock fields | MOCK | `infrared_client_v2.py` | Synthetic fields, "NOT MEASURED DATA" label in `metadata.disclaimer` |
| `delta_tmrt_surrogate()` | UNVALIDATED surrogate | `nature_nsga2_coolstock.py:107` | Analytical proxy — porosity-penalty bug fixed 2026-05-20, but underlying model is Garcia-Nevado 2020 surface temp (not 1.1m Tmrt). Marked DEPRECATED. |
| `pollinator_corridor_score()` F3 objective | DEGENERATE | `nature_nsga2_coolstock.py:158` | y_m clamp causes score ≈ 1.0 for all Pareto solutions. Not a valid optimization signal. |
| ULMA scaffold inventory | MOCK | `nature_nsga2_coolstock.py:79` | `ulma_inventory_mock.json` — declared mock in NatureGooddest MOCKS.md |
| Girbau LAB upcycled textile data | DECLARED | `nature_nsga2_coolstock.py:347` | Partner-declared, not independently verified |

---

*Integration audit: 2026-05-21*
