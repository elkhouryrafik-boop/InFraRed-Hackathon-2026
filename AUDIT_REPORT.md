# CoolSpend — Code Audit & Fix Report (2026-05-29)

Audit run by 4 parallel specialist agents (optimizer/spatial, sdk/cost/calibration,
app/pipeline/3D/viz, data/tests/CLI) + manual verification. All fixes below are
applied and the full test suite is green: **267 passed, 1 skipped** (was 264 / 3 failed).

## The "trees with no context" problem — ROOT CAUSE & FIX

You saw proposed trees floating with no surrounding buildings or existing canopy.
It was **not** a coordinate-frame problem — Infrared returns building meshes in the
same SW-corner metric frame as the proposed trees. Two real bugs:

1. **Buildings dropped 100% of the time.** `get_buildings_for_polygon()` returns a
   `Dict[str, DotBimMesh]` (Pydantic objects), but `app_3d.py` iterated it as a
   `list[dict]` and called `.get()` on each → `AttributeError` on every building →
   swallowed by a bare `except` → every building silently skipped, every run.
2. **Existing street trees never added** to the 3D scene at all.

**Fixed:**
- `sdk_client._normalize_buildings()` coerces the dict-of-models into
  `[{coordinates, indices}, ...]`; `get_buildings_for_polygon` returns that.
- `app._load_existing_context_trees()` loads real BCN inventory trees inside the
  site box, projects lon/lat → local metres via the single CRS boundary
  (`spatial_engine.latlon_to_local_m`), and sizes crowns from the species table.
- `build_glb_scene` / `build_cooling_diff_glb` now render buildings + a muted
  grey-green existing-canopy layer + species-coloured proposed trees.
- Building-drop failures now log at WARNING (a silent drop can't hide again).

**Verified live with real Infrared data:**
- Plaça Catalunya area: **623 real building meshes** in the scene (was 0).
- Eixample: **623+ buildings + 40 existing street trees + 64 proposed trees**.
- Hero artifacts: `outputs/live_demo/eixample_scene.glb` (553 meshes),
  `eixample_cooling_diff.glb`, `eixample_before_after.png`.
- Headline (real UTCI): "64 trees cool 3,682 m² of ground by ≥0.5 °C (€80/m²)."

**You do NOT need new SfM data.** The built-environment context (Infrared footprints
+ heights), the existing canopy (145k-tree BCN inventory), and LiDAR canopy height
were all already available — they just weren't being assembled into the GLB.

## CRITICAL bugs fixed

- **Mock backend was not offline.** The 3D path called `get_buildings_for_polygon`,
  which built a real `InfraredClient` and hit api.infrared.city *regardless of
  backend* (burning quota on "mock"). Now gated on `INFRARED_BACKEND=live`.
- **Species join broken for Barcelona's #1 tree.** Code keyed `Platanus x acerifolia`
  (ASCII x); the inventory uses `Platanus × acerifolia` (U+00D7) → the most-planted
  street species (~28% of all trees) silently got the neutral 0.5 cooling score
  instead of its true top score (1.0). Added `_norm_key` normalisation (× ↔ x, case,
  whitespace) on both sides of the join.
- **3 stale tests** (asserted a 4-tuple; `on_submit` now returns 6) — updated.
- **`select_top3` crash on a 1-row Pareto front** — `X = np.atleast_2d(result.X)`.
- **Cache replay could build `utci_c=None`** from a truncated cache file and crash
  far away — now only the later-added spatial fields are optional; required fields
  raise a clear `ValueError` on a corrupt cache.

## Honesty / readability fixes

- SimBudget log label "live UTCI call" → "UTCI sim call" (it fires for mock too;
  must not claim "live" under mock).
- Cost-model doc drift corrected: CapEx €3,000 → **€2,200/tree**, OpEx €180 → **€60/tree/yr**
  (now matches `cost_config.json`).
- `CORE_FRACTION` docstring 50% → 34% (matches the 0.34 value).
- Removed dead `_lonlat_to_local` flat-earth helper in `app_3d.py`; corrected the
  misleading "matches spatial_engine.py / 120×120" comment.
- Pipeline error dict now has the same keys as the success dict (shape parity).

## Verified-good (no change needed)

- CRS round-trip `local_m_to_latlon ∘ latlon_to_local_m`: max error ~9e-10 m.
- NSGA-II seed 42 fully deterministic.
- Coverage math never negative / never exceeds the cap.
- Non-positive `delta_utci_c` is already guarded in `cost_per_utci_degree`
  (returns value=None → ranked last); TOPSIS is only a tie-break, so a warming
  config cannot rank #1.
- Mock CLI pipeline output coherent: 41.0 → 36.56 °C, €13,751/°C.

## UTCI accuracy investigation (2026-05-29)

Question raised: the live felt-temperature read ~28–31°C, which looked too low for
Barcelona summer — is solar/radiation being applied, is the weather file right, are
we reading the right statistic?

Investigated with the Infrared SDK directly (skill `use-infrared`). Findings:

- **Weather file is correct and complete.** Station = `ESP_CT_Barcelona.081800_TMYx`.
  A July 15:00 sample: air temp 26.1°C, **DNI 652 W/m²** (strong direct sun), DHI 119,
  GHI 505, horizontal IR 375, RH 60%, **wind 4.3 m/s**. All 7 UTCI fields present;
  `from_weatherfile_payload` pulls them automatically.
- **Solar/MRT IS applied.** UTCI sits 2–4°C above air temp, and within a single grid
  the sunniest cell (~31°C) is ~7°C hotter than the shadiest (~24°C) — exactly the
  sun/shade spread the model should produce.
- **The moderate value is real, not a bug.** Same-site A/B across three windows:
  | Window | air temp | UTCI mean | UTCI p90 | UTCI max |
  |---|---|---|---|---|
  | 09–17 all-day | 26.6 | 28.7 | 30.9 | 31.1 |
  | 14–15 peak | 26.6 | 28.0 | 30.3 | 30.4 |
  | 13–16 afternoon | 26.7 | 28.0 | 30.2 | 30.4 |
  Coastal Barcelona TMYx July air temp is only ~26.6°C and the 4.3 m/s sea breeze
  lowers UTCI — net ~28–31°C = "moderate heat stress" on the official scale. The
  "feels like 40°C" intuition is inland Spain (Madrid/Sevilla), not coastal Barcelona.
- **Peak-hour windowing does NOT raise it** (it slightly lowers the mean). A peak-hour
  experiment was tried and reverted; the 09–17 window is kept.

Reporting recommendation (NOT yet applied): surface the **p90/peak cell (~31°C)**, not
just the site mean (28.7, diluted by shaded cells), so the headline reflects the hot
sun-exposed spots where shade actually matters.

## Flagged for your call (NOT changed — would risk the green suite or need a decision)

- **Secondary KPI unit mismatch (€/UTCI-hour):** numerator is present-value lifetime
  cost, denominator is one year of UTCI-hours, and its uncertainty band is undiscounted
  while the primary €/°C band is discounted. Documented as intentional in-code, but the
  two intervals null out at different thresholds. Decide the intended horizon before a
  judge asks. Primary €/°C is internally consistent.
- **Pre-calibration band (±4 °C)** dwarfs the discounted ~0.27 °C deltas, so the
  headline €/°C upper bound is usually unbounded (one-sided interval) until a real
  empirical `band_c` is supplied.
- `N_TREES` module global is mutated per run — works because run→select→validate is
  sequential, but it's a foot-gun if site state ever changes mid-sequence.
- `_live_utci` / `_live_tcs` duplicate ~80 lines of context/weather/vegetation setup —
  extract a shared helper when there's time.
- `bcn_data` / `bcn_lidar` network paths have no test coverage (ran here only off the
  30-day disk cache).
