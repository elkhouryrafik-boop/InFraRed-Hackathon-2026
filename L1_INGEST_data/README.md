# `L1_INGEST_data/` — Level-1 ingested data artifacts

These are **produced data artifacts**, not raw sources. They are emitted by a shared
upstream ingestion pipeline (the sibling **`data_for_all`** project) and copied here as
the inputs CoolSpend's runtime actually reads. The app needs the *artifact*, not the
pipeline — so a snapshot lives in-repo and the code references it by relative path.

Full source provenance (publishers, CKAN slugs, UUIDs, licenses, CRS) is in
[`../DATA_SOURCES.md`](../DATA_SOURCES.md); the scientific description is PAPER.md §3.

| File | What it is | Origin / how it's produced | Read by |
|------|-----------|----------------------------|---------|
| `data_for_all/scored_grid.geojson` | 494-cell Barcelona heat-vulnerability grid (~400 m cells, EPSG:25831). Per cell: `mean_lst_celsius`, `lst_anomaly`, `mean_sealed`, `mean_ndvi`, `composite_score_B`, district/barri, existing-tree counts. | Satellite-derived by the upstream `data_for_all` pipeline: **Landsat** thermal LST + **Sentinel-1** SAR sealed-surface + **Sentinel-2** NDVI, fused into `composite_score_B` (hot × sealed). The composite *weights* are exactly reproducible in-repo (`coolspend/provenance.py`); the raw-imagery sub-score derivation lives in that external pipeline (PAPER.md §3.1, §9 item 1). | `coolspend/citywide.py` (citywide €1M scan + allocate), `coolspend/provenance.py` |
| `data_for_all/intervention_costs.json` | Itemised per-tree cost inputs (stock, pit, soil, guarding, labour, OpEx). | Compiled by the `data_for_all` pipeline from Barcelona municipal figures (IMPJ Arbrat Viari OpEx; Diputació de Barcelona planting/guarding) — see PAPER.md §4.7. | `coolspend/placement_inputs.py` |
| `data_for_all/priority_zones.csv` | Pre-ranked priority zones (legacy). | `data_for_all` pipeline. | *(currently unused by the runtime — kept for reference)* |
| `climate/Barcelona_TMYx_2011-2025.epw` | Real Barcelona typical-meteorological-year hourly weather. | **climate.onebuilding.org** TMYx 2011–2025 (EnergyPlus EPW). NOT a mock. | `coolspend/epw_weather.py` → `coolspend/cost_model.py` (`hours_per_degc`) |
| `climate/x4_raval_uhi_validation.json` | El Raval urban-heat-island validation reference. | Validation reference dataset. | validation / calibration |

**CRS note:** `scored_grid.geojson` geometry is EPSG:25831 (ETRS89 / UTM 31N); the code
reprojects to WGS84 where it draws on the map.

**Regenerating:** these come from the upstream `data_for_all` ingestion run, not this repo.
To refresh, re-run that pipeline and copy its outputs here (the file names/paths above are
what the code expects).
