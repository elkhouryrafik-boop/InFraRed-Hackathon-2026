# Data sheet — Infrared UTCI simulation (infrared.city) — the COOLING anchor

## 1. Motivation
The ONLY source in the stack that resolves cooling at the project's decision unit (1 m grid, per
placement). Every €/m²-cooled headline is earned here, not from any tree database.

## 2. Composition
Per-run `merged_grid`: 2D UTCI (°C) at 1 m pitch over the site polygon, aggregated over the
July 09–17 window. Inputs: real buildings (fetched OSM/Infrared), ground materials, nearest EPW
weather, and our placed trees as vegetation Points (crown Ø, height, species).

## 3. Collection
Physics/ML microclimate model served via SDK `run_area_and_wait` (thermal-comfort-index). MRT
computed internally from geometry + radiation. Baseline (no added trees) vs intervention (+trees)
→ cell-wise diff = cooled footprint (`coolspend.sdk_client.cooled_footprint_m2`).

## 4. Pre-processing
- nanmean for site-mean; cells outside polygon are NaN.
- Cooled footprint = count(baseline − intervention ≥ 0.5 °C) × 1 m². 0.5 °C > model noise.
- Filter ground materials to valid names {asphalt,concrete,soil,vegetation,water} (drop 'building').
- CRS: polygon + tree coords WGS84; fail-closed UTM round-trip guard before any call.

## 5. Uses
- **Should:** quantify per-placement cooling (cooled m², ΔUTCI) on real geometry; rank placements.
- **Should NOT:** be presented as field-measured UTCI — it is a SIMULATION. The surrogate-vs-sim
  calibration (RMSE band) is the honesty bridge; field validation is out of scope.

## 6. Distribution
Commercial SDK, API key (issued at Buildathon kickoff 2026-05-27). Results cached locally
(`coolspend/cache/infrared/`) → offline replay as `cached:live`, reproducible without the key.

## 7. Maintenance
infrared.city. Versioned SDK (0.4.7). Weather files + building fetch are upstream dependencies.

## 8. Limitations
- **It is a model (bias=1):** validity vs real Barbican-/Barcelona-measured UTCI is not independently
  established here; treat absolute °C as model output, deltas as the trustworthy quantity.
- Window-aggregate compresses peaks (maxes ~31 °C) → instantaneous >32 °C "strong heat stress" area is ~0;
  hence the cooled-footprint metric (threshold-independent) instead of an absolute-threshold area.
- Single nearest weather station per location (coarse climate input).
- Crown/height inputs inherit Verd Urbà band uncertainty (§ verd-urba sheet).
