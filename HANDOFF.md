# Handoff — CoolSpend: anywhere-in-Barcelona, real data, live-validated tool

**Updated:** 2026-05-22. **Branch:** master. Buildathon May 27–31 2026.

## Goal
Win the infrared.city Buildathon. Win = demo + 3-min video + narrative on a clean,
**data-driven, honest** tree-placement tool (max cooling per euro), NOT building every phase.
Hard rule: real computation everywhere; per-species cooling stays a labelled heuristic, the
cooling number is the Infrared sim's. See memory: win-the-hackathon, no-mock-production-bar,
coolspend-direction-v3.

## Current state (this session's work — 5 commits, 267 tests pass, 1 skipped)
- **Live Infrared UTCI PROVEN** on real data. `coolspend/sdk_client._live_utci` rewritten:
  thermal-comfort-index + Location/TimePeriod/weather + placed trees as vegetation Points
  (real per-species crowns) + buildings/ground fetched per polygon (ground filtered to valid
  materials). 12 live UTCI sims run this session; all CACHED in `coolspend/cache/infrared/`.
- **API KEY REMOVED from .env** (user, 2026-05-22). Now CACHE-ONLY: use `INFRARED_BACKEND=cached`
  or `mock`. Live re-wires on May 27 (key reissued at kickoff). Do NOT attempt live calls.
- **Anywhere in Barcelona** (NOT a fixed site — user was emphatic). `run_decision(center_lonlat=(lon,lat),
  site_size_m=...)` builds a metric square there, retargets the optimizer, validates on real
  buildings/weather. `spatial_engine.square_ring_lonlat` + active-site override.
- **Cooled-footprint headline metric** (user-chosen): m² cooled >=0.5 °C, cell-wise grid diff
  (`sdk_client.cooled_footprint_m2`). Does NOT saturate. **VERIFIED LIVE at Glòries: €122,400 ->
  12 trees cool 2,130 m² (€58/m²)**; cached replay reproduces it offline as `cached:live`.
  (NOTE: that cached result is from the PRE-species-gene optimizer; the species-aware optimizer
  changes geometry, so re-validate live on May 27 for the species-aware number.)
- **Real Barcelona data.** `bcn_data.py`: arbrat-viari inventory (145,392 street trees, 287
  species, CC-BY, cached CSV). `bcn_species.py`: 12 real top species with Verd Urbà dim bands +
  cited cooling proxy. Wired into optimizer palette + live vegetation.
- **Species-aware placement.** Species is a decision variable (chromosome 3*N_TREES); optimizer
  CHOOSES species weighted by cooling_score vs ecological diversity. MAX_THERMAL concentrates
  Platanus/Tipuana (cooling 0.73); MAX_ECOLOGICAL diversifies (0.51).
- **ICGC+CREAF LiDAR canopy height** (`bcn_lidar.py`): measured existing-canopy SITE CONTEXT.
  Honest finding: forest-oriented 20 m product; urban targets = NoData=0 = "bare/high opportunity";
  WMS/vsicurl unusable, only local raster (gitignored, downloaded) works.
- **earn-the-data** discipline applied -> `phase-2/` (data-inventory, 4 data-sheets, profiling-plan,
  brief-revisit). Verdict: sources earn placement + SIMULATED cooled-area-per-euro; per-species
  cooling stays a heuristic.

## Files (key)
- `coolspend/sdk_client.py` — live UTCI, cooled_footprint_m2, heat-stress area, caches.
- `coolspend/optimizer.py` — species-gene decode/Problem, validate_top3 (+cooled footprint).
- `coolspend/app_pipeline.py` — run_decision(center_lonlat,...), anywhere retarget, result geometry+canopy.
- `coolspend/spatial_engine.py` — square_ring_lonlat, set_active_site/open_square_site.
- `coolspend/bcn_data.py`, `bcn_species.py`, `bcn_lidar.py` — real data layers.
- `coolspend/app.py` — Gradio UI (OLD flow; does NOT yet show anywhere/cooled-footprint/real species).
- `DATA_SOURCES.md`, `phase-2/` — provenance + earn-the-data artifacts.

## What's NOT done (next, toward the win)
1. **Demo UI** — `app.py` still shows old flow (paste-GeoJSON, default Plaça, €/degC). Wire the
   anywhere lat/lon picker + real-species table + cooled-footprint headline + UTCI heatmap +
   measured-canopy context. This is what judges SEE. (User leaned LiDAR-first; UI is the clear next.)
2. **3-min video + narrative** — competitive wedge: optimize-then-validate, honest, anywhere, real species.
3. **Calibration study** (`coolspend/calibration.py`, ~11 live calls) — surrogate-vs-real RMSE band.
   Needs the key (May 27) + update for new grid/species. Deferred (cache-only now).
4. Optional: raw LIDARCAT3 for per-urban-tree dims (heavy; deferred).

## What we tried that didn't work
- Sequential executor agents only (no git-worktrees on Windows). Per prior handoff.
- ICGC LiDAR via WMS GetFeatureInfo (rendered RGB, all 0) and /vsicurl (striped TIFF -> 0): both
  UNUSABLE. Only the local 166 MB raster + rasterio gives real values.
- Heat-stress-area metric at >32 °C: empty (July-window aggregate maxes ~31 °C). At >26 °C it
  saturates on hot sites. -> use cooled-footprint instead.

## How to resume
Read this HANDOFF. Cache-only mode (no Infrared key until May 27): use INFRARED_BACKEND=cached/mock.
Run tests: `.venv\Scripts\python.exe -m pytest coolspend/tests/ -q`. Likely next: build the demo UI
(item 1) so the frontend shows the real anywhere + 2,130 m² + real-species work.
