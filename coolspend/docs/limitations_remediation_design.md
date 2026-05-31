# CoolSpend — Limitations Remediation Design

Design entries for the 8 limitations enumerated in `PAPER.md` §9. Every touchpoint
below was verified against the current source tree (line numbers are real). The
governing constraint is **zero new live Infrared simulations by default**: live sims
are metered/paid (3-sim `SimBudget` cap, `sdk_client.SimBudget` at `sdk_client.py:125`).
Where a fix genuinely benefits from a sim, the entry states *exactly how many* and
offers a sim-free or cached path that ships without them.

A recurring theme: several limitations (#2, #3, #4, and to a degree #7) are the same
problem wearing different hats — *the placement/ranking signal is a synthetic or proxy
cooling estimate, not a measured field*. The synthesis sections at the end collapse
these into one shared `CoolingEstimator` abstraction.

Legend for **Sim cost**: `zero` = no Infrared call; `N cached` = N replays of an
already-paid geometry-keyed result (`_cached_utci`, `sdk_client.py:680`); `N live` =
N new metered calls.

---

## Limitation 1 — Satellite-composite provenance

**Problem restatement.** Citywide site prioritisation ranks 494 cells by
`composite_score_B` (`citywide.py:165`, `citywide.py:290` → `rank_cells`), but the
paper says the score's derivation (fusion weights, LST-anomaly baseline,
SAR-to-sealed classifier) is undocumented and lives in an external upstream pipeline.
The codebase *consumes* `scored_grid.geojson` but contains no code that *produces* it.

**Root cause.** The grid was authored in a separate "data_for_all" ingestion project
(L1 ingest) and shipped as a finished artifact at
`L1_INGEST_data/data_for_all/scored_grid.geojson`. CoolSpend treats it as an opaque
input. There is no provenance manifest, no weight record, no classifier card.

**Key finding from inspecting the artifact (do this before assuming it is a black box).**
The grid is *more reproducible than the paper implies*. Each of the 494 features
already carries the component sub-scores and their blend weights:

- Normalised components: `s1_sealed`, `s2_lst_anomaly`, `s3_inverted_ndvi`,
  `s4_mismatch` (and an `s5` term).
- Per-cell blend weights: `s1_contribution_pct` … `s5_contribution_pct`
  (they sum to ~100% per cell — verified: 1.001, 1.001, 0.999 on the first three cells).
- Raw inputs are retained too: `mean_sealed`, `s1_sealed`, `mean_lst_celsius`,
  `lst_anomaly`, `s2_lst_anomaly`, `mean_ndvi`, `s3_inverted_ndvi`, `platanus_pct`,
  `composite_score_A/B/C`.

A direct reconstruction `Σ s_i · (contribution_pct_i/100)` lands close to
`composite_score_B` (B=0.326 vs reconstructed 0.362; B=0.317 vs 0.257; B=0.145 vs
0.137) — same order, small residual. The residual is almost certainly a final
min–max/rank renormalisation step and a difference between which raw layer feeds each
`s_i`. So the honest framing is **"partially reconstructable, with a documented residual"**,
not "irreproducible."

**Proposed solution.** Do not try to re-run the satellite pipeline (out of scope,
needs Landsat/Sentinel scenes). Instead, *close the provenance gap from inside this
repo* in three steps:

1. **Provenance manifest + datasheet.** Add `coolspend/provenance/scored_grid_card.md`
   (a Gebru-style datasheet): source sensors (Landsat 8/9 thermal → LST; Sentinel-1 SAR
   → sealed; Sentinel-2 → NDVI), the acquisition window, CRS (EPSG:25831), cell size
   (~400 m), and the *known unknowns* (SAR-to-sealed classifier training data, the
   final renormalisation). This is a writing/curation task, not code.
2. **Reproduction harness (`coolspend/provenance/reproduce_composite.py`).** A pure
   function `recompute_composite_B(props) -> float` that recomputes B from the stored
   `s1..s5` + `*_contribution_pct` fields, plus `audit_composite_reproducibility()` that
   runs it over all 494 cells and reports the residual distribution (max abs error,
   RMSE, Spearman rank correlation between stored B and recomputed B). The paper can
   then state a *measured* reproduction fidelity (e.g. "Spearman ρ = 0.99 between the
   shipped score and an in-repo recomputation from stored components") — that converts
   an unqualified "we can't reproduce it" into a quantified, defensible claim.
3. **Rank-robustness fallback.** Add `composite_score_repro` as a derived column and let
   `rank_cells` optionally rank on it (`citywide.py:112`). If the upstream artifact ever
   goes missing, the ranking still runs from documented, in-repo arithmetic.

**Code touchpoints.**
- New: `coolspend/provenance/reproduce_composite.py`, `coolspend/provenance/scored_grid_card.md`.
- New test: `coolspend/tests/test_provenance.py`.
- `citywide.py:59` `load_scored_grid` — attach `composite_score_repro` to each cell's
  properties; `citywide.py:112` `rank_cells` — accept `sort_by="composite_score_repro"`.

**Data/dependency needs.** None new — the inputs are already in `scored_grid.geojson`.
The datasheet *describes* Landsat/Sentinel provenance but needs no scene downloads.
Licensing: Copernicus/Landsat are open; the derived grid is the project's own product.

**Sim cost.** zero.

**Effort.** S (reproduction harness + tests) + S (datasheet writing).

**Risk + honesty impact.** Low risk. Big honesty win: it downgrades the paper's
strongest self-criticism ("rests on a signal we can't reproduce") to "reproducible to
ρ≈0.99 from stored components, with the SAR classifier and final renormalisation
documented as the residual." Risk: the recomputation might *not* match well, in which
case the honest outcome is a stated low fidelity — still better than silence.

**Verification.** `audit_composite_reproducibility()` asserts Spearman ρ on the ranking
≥ a threshold (the ranking is what matters, not the absolute score). Unit test pins the
residual statistics so regressions are caught.

---

## Limitation 2 — Coverage proxy vs measured marginal cooling

**Problem restatement.** The greedy placement weights demand cells by the **baseline**
UTCI field (`placement_inputs.build_demand_cells`, `placement_inputs.py:88`; weight =
`UTCI − COMFORT_UTCI_C`, `placement_inputs.py:126`/`:137`). A planted tree changes the
field, so each greedy marginal gain (`smart_placement.place_trees_greedy`,
`smart_placement.py:201–207`) is a *coverage* proxy, not measured marginal cooling. The
module docstring already declares this honestly (`smart_placement.py:29–36`).

**Root cause.** Measuring true marginal cooling per candidate slot would need one
Infrared sim *per slot per greedy step* — hundreds of metered calls. So the system
optimises a static, pre-planting demand field and validates the final layout once.

**Proposed solution — a sim-free physical shade proxy that is better than "baseline
UTCI × covered".** Replace (or augment) the constant per-cell weight with a
*geometry-aware shade-gain* estimate that responds to the actual sun and the actual
obstacles, computed locally:

- **Ray-cast / sky-view-factor shade proxy (`coolspend/shade_proxy.py`).** For Barcelona's
  fixed July peak-sun window, sample a handful of solar positions (azimuth/altitude from
  a standard solar-position formula — `pvlib` or a 30-line NOAA SPA implementation, no
  network). For each demand cell, cast rays toward the sun through the *candidate tree's
  crown disk* (and existing canopy + building footprints already assembled in
  `placement_inputs.assemble_inputs`, `placement_inputs.py:284–312`). A cell's
  *shade-gain weight* = baseline-heat-weight × fraction of sampled sun-rays the new crown
  would intercept that were previously unblocked. This is the RayShader/SVF idea reduced
  to the one quantity placement needs: "how much *new* direct-sun blockage does this tree
  buy this hot cell?" It is defensible because outdoor daytime UTCI in a hot dry climate
  is radiation-dominated (Tmrt-driven), and direct-beam interception is the first-order
  driver of pedestrian Tmrt — the same physics the Infrared solar/SVF metrics encode.
- **Why this beats the current proxy.** The current proxy says "a covered hot cell is
  worth its baseline heat." The shade proxy says "a hot cell is worth its baseline heat
  *times the new sun-blockage this specific tree provides*", which (a) penalises planting
  where existing canopy/buildings already shade, and (b) makes the marginal gain
  genuinely diminishing in a *physical* sense, not just set-cover sense. It stays
  submodular (ray-interception sets union like coverage sets), so the
  `(1 − 1/e)` greedy guarantee in `smart_placement` is preserved.
- **Optional cached anchoring (no new live sims).** If a one-off Infrared **solar
  radiation / SVF** field already exists in the cache for a site (the SDK exposes
  solar/SVF/sun-hours per the Infrared skill), use it as the per-cell baseline shortwave
  load to weight the proxy — replayed via `_cached_utci` (`sdk_client.py:680`), zero new
  live cost.

**Code touchpoints.**
- New: `coolspend/shade_proxy.py` — `solar_positions_july(lat, lon)`,
  `shade_gain(cell_xy, crown_disk, obstacles, sun_dirs) -> float`.
- `placement_inputs.py:88` `build_demand_cells` — multiply each cell weight by the
  candidate-independent baseline (unchanged) AND expose obstacles for the proxy.
- `smart_placement.py:159–164` (coverage precompute) and `:201` (marginal) — replace the
  binary "in crown radius" coverage with shade-gain-weighted coverage; `DemandCell`
  (`smart_placement.py:46`) gains nothing (weights stay on cells), but the
  `coverage[(ci,si)]` map becomes a `dict[idx → shade_gain]` not a `set[idx]`.

**Data/dependency needs.** `pvlib` (BSD) for solar position, *or* a vendored SPA
function (zero dependency). Building/canopy obstacles already assembled in
`placement_inputs`. No external data.

**Sim cost.** zero (pure geometry). Optionally 0 new + reuse of any cached solar/SVF
field (N cached, typically 1).

**Effort.** M.

**Risk + honesty impact.** Medium honesty win: the placement *order* becomes physically
grounded (sun-blockage), not just baseline-heat coverage. The honest claim upgrades from
"coverage proxy" to "first-order radiative shade-gain proxy, validated by one UTCI run."
Risk: ray-casting cost grows with cells×slots×sun-samples; mitigate with few sun samples
(≤5) and the existing crown-radius prefilter. Still NOT measured cooling — must stay
labelled as a proxy.

**Verification.** A/B on a cached-backend site: compare the greedy *order* under the
old vs new weighting, then run the final layout through the existing single UTCI
validation; the shade-proxy order should yield ≥ the coverage-proxy order's measured
ΔUTCI on the validation run (1 cached or 1 live to confirm, not per-step).

---

## Limitation 3 — Synthetic cooling on non-live backends (the €1M portfolio)

**Problem restatement.** `allocate_citywide` (`citywide.py:260`) assembles the €1M
portfolio. On mock/cached it has no per-cell UTCI grid, so it *cannot* sort by measured
€/m²-cooled and falls back to ranking by `composite_score_B`
(`citywide.py:356–364`). Per-site cooling and the funding order are therefore previews,
not measured (the function docstring and `disclaimer` say so, `citywide.py:482`).

**Root cause.** A measured portfolio needs ~1 sim per funded site; the paper states ~7
live sims for 7 sites. The default mock assembly is sim-free by design.

**Proposed solution — three tiers, default sim-free.**

1. **Tier 0 (ship default, zero sims): shade-proxy portfolio.** Reuse the
   `shade_proxy` cooling estimate from Limitation 2 as the per-site cooling number so the
   funding order is driven by an estimated *cooled m²* rather than only heat-vulnerability.
   `have_cooling` (`citywide.py:356`) becomes true via the proxy, so the cheaper-€/m²-first
   branch (`citywide.py:357–362`) runs. Label every value `estimate (shade-proxy)`.
2. **Tier 1 (cached, zero new live): cached-UTCI portfolio.** If the 7 chosen cell
   sub-polygons have cached UTCI results (geometry-keyed SHA-256, `sdk_client.py:78`),
   the allocation replays them — a fully *measured-grid* portfolio with **zero new live
   sims**. This is the recommended demo artifact: precompute once (7 live), commit the
   cache, then every rebuild is cached.
3. **Tier 2 (7 live, opt-in): the real measured portfolio.** Exactly the paper's number.
   Gate behind an explicit flag and the `SimBudget` cap.

**Code touchpoints.**
- `citywide.py:260` `allocate_citywide` — accept `cooling_source: "proxy"|"cached"|"live"`;
  when `"proxy"`, fill `cooled_footprint_m2` (`citywide.py:344`) from `shade_proxy`.
- `citywide.py:224` `_eur_per_m2_cooled` — already tolerant of multiple shapes; extend to
  read a proxy estimate but tag it.
- `export_web.py` / `api_server.py` — surface the `cooling_source` tag in the payload so
  the frontend label is honest ("measured" vs "estimate").
- New: a `tools/precompute_portfolio.py` that runs the 7 live sims once and writes the
  cache + `web/public/citywide_plan.json`.

**Data/dependency needs.** None new beyond `shade_proxy`. Cache lives in repo.

**Sim cost.** Tier 0 = zero. Tier 1 = zero new live (7 cached). Tier 2 = 7 live (one-off,
to populate the cache).

**Effort.** M (mostly plumbing `cooling_source` through citywide → export → web).

**Risk + honesty impact.** Large honesty win: the demo can show a *measured-grid*
portfolio (Tier 1) with no metered cost, and the paper can report "the headline €1M
portfolio is assembled from cached measured UTCI fields (7 sims, paid once)" instead of
"assembled on mock." Risk: cache staleness if geometry changes — mitigate with the
SHA-256 geometry key (a changed polygon misses the cache and is flagged, never silently
stale).

**Verification.** Assert in a test that when `cooling_source="cached"` every funded site
has a non-None `cooled_footprint_m2` and `validated_utci_c`, and that the funding order
matches the measured-€/m² sort (not the composite fallback).

---

## Limitation 4 — Surrogate thermal relief in NSGA-II

**Problem restatement.** The NSGA-II objective F1 maximises `thermal_relief`
(`optimizer.py:223` → `spatial_engine.thermal_relief`, `spatial_engine.py:851`), an
analytical ΔTmrt surrogate with a stated ±4 °C uncertainty and an **unsourced linear
cap** `MAX_TMRT_REDUCTION_C = 12.0` (`spatial_engine.py:587`, used at `:848`). Only the
post-hoc 3 Infrared runs (`validate_top3_with_infrared`, `optimizer.py:517`) are treated
as measured.

**Root cause.** NSGA-II evaluates 3600 candidate configs (`POP_SIZE=60 × N_GEN=60`,
`optimizer.py:114–118`); each must be sim-free, so a cheap analytical proxy is mandatory.
The cap and the ±4 °C band were placeholders anchored to literature magnitude only
(`optimizer.py:392–396`, `:888–898`).

**Proposed solution — two independent fixes; neither needs sims.**

1. **Replace the surrogate's *physics* with the same `shade_proxy` (Limitation 2).**
   Instead of `MAX_TMRT_REDUCTION_C × effective_shade × eff` capped at 12 °C, compute
   site-averaged ΔTmrt from the ray-cast sun-blockage fraction over the site grid, then
   convert blocked-shortwave-fraction → ΔTmrt with a *sourced* coefficient. The
   radiation-to-Tmrt relationship is the textbook outdoor energy balance (Tmrt ∝ absorbed
   shortwave); the conversion coefficient can be anchored to the COMFA/ENVI-met range in
   the literature instead of an invented 12 °C cap. This makes the surrogate physically
   monotone in real geometry and removes the unsourced ceiling.
2. **Calibrate the band from data already in the repo (no new sims).** Replace the
   assumed ±4 °C (`spatial_engine.py:30`, `cost_model.PRE_CALIBRATION_BAND_C=4.0` at
   `cost_model.py:326`) with an *empirical* residual: there is already a calibration
   module (`coolspend/calibration.py`) and a validation artifact
   (`L1_INGEST_data/climate/x4_raval_uhi_validation.json`). Fit the surrogate's predicted
   ΔTmrt against the cached/measured UTCI deltas the project has already collected, report
   the RMSE, and feed it into `cost_per_utci_degree(band_c=...)` (the function already
   accepts a measured band, `cost_model.py:718`/`:801`). The contract is pre-wired —
   `HOURS_PER_DEGC_REF` and `PRE_CALIBRATION_BAND_C` exist precisely to be re-anchored.

**Code touchpoints.**
- `spatial_engine.py:801` `delta_tmrt_surrogate` and `:851` `thermal_relief` — swap the
  capped-linear body for the shade-proxy-derived ΔTmrt; remove/justify
  `MAX_TMRT_REDUCTION_C` (`spatial_engine.py:587`).
- `coolspend/calibration.py` — add `fit_surrogate_band()` returning RMSE from the
  cached measured deltas vs surrogate predictions.
- `cost_model.py:801` band setup — default `band_c` to the calibrated RMSE when available.
- `optimizer.py:391` (`delta_tmrt_uncertainty_c = 4.0`) and `:888` audit text — report the
  calibrated band, not the hardcoded 4.0.

**Data/dependency needs.** Same `shade_proxy` deps. Calibration uses the existing
`x4_raval_uhi_validation.json` + any cached UTCI deltas; a literature coefficient for
shortwave→Tmrt (cite COMFA/ENVI-met range).

**Sim cost.** zero (surrogate physics is geometry; band fit reuses cached/existing
validation data).

**Effort.** L (touches the optimizer hot path and its test suite `test_surrogate.py`,
`test_optimizer.py`, `test_calibration.py`).

**Risk + honesty impact.** Large honesty win: removes the single "unsourced cap" the
paper flags and converts ±4 °C from "assumed" to "empirical RMSE = X". Risk: the hot path
must stay fast — ray-casting 3600× could be slow; mitigate by precomputing the
site's per-slot sun-blockage once (geometry is static within a run) and reusing it across
generations (the same precompute trick `smart_placement.py:159` already uses).

**Verification.** `test_surrogate.py` pins monotonicity (more sun-blockage → more ΔTmrt)
and that no result exceeds a *sourced* physical bound. `test_calibration.py` asserts the
fitted band is reported and finite. A/B: surrogate-ranked top config's *measured* ΔUTCI
(the existing 3-sim validation, no new sims) should not regress vs the old surrogate.

---

## Limitation 5 — Unsurveyed sub-surface conditions

**Problem restatement.** In-ground slots cannot be cleared of buried utilities from open
data; they are flagged `requires_utility_survey=True` (`placement_inputs.py:370`), and the
foundation setback `FOUNDATION_SETBACK_M = 6.0` is a conservative placeholder
(`candidate_slots.py:58–61`). Sidewalk widths are absent (`candidate_slots.py:18–22`
honesty boundary).

**Root cause.** Underground utility maps and authoritative sidewalk-width polygons are not
in Barcelona open data; the system uses building/road/furniture exclusions only
(`candidate_slots.generate_slots`, `:86`).

**Proposed solution — tighten the open-data screens and make the setback species-specific,
without claiming survey-grade clearance.**

1. **Sidewalk-width proxy from OSM (`coolspend/osm_features.py` already fetches
   furniture).** Use OSM `highway=footway`/`sidewalk` width tags where present, and where
   absent, derive an *approximate* clearance from building-to-carriageway distance (the
   geometry is already in `placement_inputs.assemble_inputs`: `buildings_m` at
   `placement_inputs.py:284`, `streets_m` at `:305`). Add a minimum-clear-width gate to
   `candidate_slots` so a slot on a too-narrow strip is rejected. Label it "OSM-derived
   approximate width, not survey-grade."
2. **Species-specific setback table.** Replace the single `FOUNDATION_SETBACK_M` with a
   per-species root-spread setback keyed off `bcn_species` crown/root bands (small species
   → smaller setback). This both improves realism and unlocks more valid slots on tight
   sites. Keep the conservative default as the fallback.
3. **Proxy utility-corridor exclusion.** Buried mains commonly run under the carriageway
   centre and parallel to facades; add an *optional, clearly-labelled* heuristic
   exclusion band along road centrelines (data already fetched in `osm_roads`). This does
   not replace a dig survey — it reduces the count of slots that would obviously fail one.

**Code touchpoints.**
- `candidate_slots.py:58` `FOUNDATION_SETBACK_M` → `foundation_setback_for(species)`;
  `:64` `_building_clearance_for` and `:78` `_buildings_clearance_ok` take the species
  setback.
- `candidate_slots.generate_slots` (`:86`) — add `min_sidewalk_width_m` gate.
- `osm_features.py` / `osm_roads.py` — emit sidewalk-width and utility-corridor polygons.
- `placement_inputs.py:370` — keep `requires_utility_survey`, add
  `sidewalk_width_source` provenance tag.

**Data/dependency needs.** OSM via Overpass (already used, degrades to `[]` if
unreachable — `placement_inputs.py:299–309`). No paid utility GIS. If the city later
provides a utility layer, it slots in as another exclusion source.

**Sim cost.** zero.

**Effort.** M.

**Risk + honesty impact.** Moderate honesty win: it narrows the "we can't see
underground" gap with documented OSM proxies while *keeping* the `requires_utility_survey`
flag — the honesty boundary is preserved, not erased. Risk: OSM width tags are sparse and
the utility heuristic is a guess; both must stay labelled as proxies, never as clearance.

**Verification.** `test_candidate_slots.py` extends `validate_slots` (`candidate_slots.py:142`)
to assert no slot violates the species setback and that flagged in-ground slots still
carry the survey flag end-to-end (already partially tested).

---

## Limitation 6 — Cost calibration (one unverified conversion constant)

**Problem restatement.** `HOURS_PER_DEGC_REF = 200.0` (`cost_model.py:315`) — the
annual UTCI-hours-above-32 °C per 1 °C mean-UTCI-drop conversion — is flagged
`REQUIRES_VERIFICATION` (`cost_model.py:313`/`:318`). It feeds the €/°C KPI's UTCI-hours
path (`cost_model.py:853`, `:947`).

**Root cause.** The constant was *derived* (Barcelona EPW mean excess ÷ band) but never
empirically fit; the rest of the cost table is municipally sourced
(`cost_model.py:185–272`, OpEx VERIFIED, CapEx DECLARED).

**Proposed solution — compute it directly from the EPW already in the repo.** The repo
ships `L1_INGEST_data/climate/Barcelona_TMYx_2011-2025.epw`. The derivation is a pure
calculation, no sim:

1. Parse the EPW hourly dry-bulb/MRT/wind/humidity and compute hourly UTCI (the project
   already has UTCI machinery; `epw_weather.py` + `nature_metrics.utci_hours_above` is
   referenced at `cost_model.py:821`).
2. Build the actual `hours-above-32` vs `mean-UTCI-shift` response by shifting the UTCI
   series by Δ and counting hours — this yields `HOURS_PER_DEGC` *empirically from the
   site's own climate file* rather than from a back-of-envelope midpoint.
3. Replace the constant with `hours_per_degc_from_epw(epw_path)` computed at load, caching
   the scalar; keep `200.0` as the documented fallback.

**Code touchpoints.**
- New: `cost_model.hours_per_degc_from_epw()` (or in `calibration.py`).
- `cost_model.py:315` `HOURS_PER_DEGC_REF` — initialise from the EPW computation with the
  literal as fallback; update the provenance comment from "derived/REQUIRES_VERIFICATION"
  to "computed from Barcelona TMYx EPW".
- `test_cost_model.py` / `test_calibration.py` — pin the computed value's range.

**Data/dependency needs.** The EPW is already in-repo (open TMYx data). A UTCI function
(already present). No new deps.

**Sim cost.** zero.

**Effort.** S.

**Risk + honesty impact.** Clean honesty win: removes the only `REQUIRES_VERIFICATION`
tag in the cost model by computing the constant from the project's own climate file. Low
risk (it is a single scalar; the KPI is already reported as an interval, so a modest
change in the constant moves the band, not a point claim). Risk: EPW-derived UTCI needs
MRT — if the EPW lacks it, use the EnergyPlus MRT approximation and document it.

**Verification.** `test_calibration.py` asserts the EPW-derived constant is within a
sane band (e.g. 100–400 h/°C) and that the KPI dual-unit path (`cost_per_utci_hour`)
remains consistent.

---

## Limitation 7 — Canopy-cover denominator

**Problem restatement.** Canopy cover % is computed against the *sampled cell area*
(`design_metrics.design_metrics(..., site_area_m2)`, `design_metrics.py:58`/`:72`), and
citywide passes the full 200 m × 200 m sample area (`_sample_area = _CELL_SAMPLE_SIZE_M**2`,
`citywide.py:446`/`:448`). A small intervention in a large cell therefore reads a low
cover %, understating the local effect.

**Root cause.** The denominator is the whole sampled square, not the *plantable strip*
the trees actually sit on. The plantable area is implicitly known — it is the area
admissible to candidate slots after building/road/furniture exclusions — but it is never
measured and passed down.

**Proposed solution — pass a *plantable-strip* denominator.** The exclusion geometry that
already exists in `placement_inputs.assemble_inputs` (boundary minus buildings minus
street/furniture buffers) defines the plantable area exactly:

1. Compute `plantable_area_m2 = area(boundary) − area(buildings ∪ street/furniture buffers
   ∩ boundary)` from the shapely geometry already assembled
   (`placement_inputs.py:311–313`, the `site` dict with `boundary`, `buildings`, `streets`).
2. Return it from `run_smart_placement` (`placement_inputs.py:347`) and thread it into
   `design_metrics(..., site_area_m2=plantable_area_m2)` instead of the raw sample square.
3. Report **both** denominators ("cover of plantable strip" and "cover of sampled cell")
   so the figure is truer locally while staying comparable citywide.

**Code touchpoints.**
- `placement_inputs.py:347` `run_smart_placement` — add `plantable_area_m2` to the return
  dict (geometry already in scope at `:311`).
- `citywide.py:447–450` — pass the per-site plantable area into `design_metrics` instead of
  `_sample_area`.
- `design_metrics.py:58` `design_metrics` — accept and report both denominators
  (`canopy_cover_pct_plantable` and `canopy_cover_pct_cell`).

**Data/dependency needs.** None — pure shapely area on geometry already assembled.

**Sim cost.** zero.

**Effort.** S.

**Risk + honesty impact.** Moderate honesty/accuracy win and a *fairer* headline cover %.
Low risk. Keep both numbers to avoid swapping one debatable denominator for another;
report which is used.

**Verification.** `test_design_metrics.py` asserts `plantable ≤ cell` and that
`canopy_cover_pct_plantable ≥ canopy_cover_pct_cell` for any non-degenerate site.

---

## Limitation 8 — Single-city scope and static meteorology

**Problem restatement.** Data assembly, species palette (`bcn_species`, `ecology`), and
cost figures (`cost_model.DEFAULT_COST_TABLE`, `cost_model.py:185`) are Barcelona-specific;
the UTCI window is a fixed July peak (`COMFORT_UTCI_C`/`UTCI_HEAT_STRESS_C = 26.0`,
`placement_inputs.py:50`, `sdk_client.py:250`); no seasonal/inter-annual variation; no
transfer to other climates.

**Root cause.** The project was scoped to Barcelona for the Buildathon; constants and data
are hardwired across modules rather than behind a city/climate profile.

**Proposed solution — a `CityProfile` config object; do NOT attempt multi-city now,
just make the seams explicit.** This is an architecture-readiness fix, not a port.

1. **`coolspend/city_profile.py`** — a dataclass bundling the city-specific knobs that are
   currently scattered: species palette source, cost table (already loadable via
   `cost_model.load_cost_table`, `cost_model.py:531`), EPW path, comfort/heat-stress
   thresholds, CRS/EPSG, plantable-species gate. Barcelona is the default profile;
   everything reads from it instead of module constants.
2. **Seasonal/inter-annual readiness.** The EPW already spans 2011–2025; expose a
   `season`/`percentile-heat-day` selector so the UTCI window is a *parameter*, not a
   constant. This needs no live sims for the *cost/hours* path (computed from EPW per
   Limitation 6); the *measured UTCI field* for a different window would need new sims —
   so default to the cached July window and flag any other window as "needs sim".
3. **Document transfer requirements** in the profile (what a new city must supply: tree
   inventory, scored grid or its inputs, EPW, cost table, invasive list). This converts
   "Barcelona-specific" into "Barcelona-instantiated, with a documented porting contract."

**Code touchpoints.**
- New: `coolspend/city_profile.py` (`CityProfile`, `BARCELONA` default).
- `placement_inputs.py:50` `COMFORT_UTCI_C`, `sdk_client.py:250` `UTCI_HEAT_STRESS_C`,
  `cost_model` EPW path/threshold, `ecology`/`bcn_species` palette — read from the active
  profile rather than module literals (do this incrementally; the profile can default to
  current values so nothing breaks).
- No change to the live sim path beyond passing the profile's thresholds.

**Data/dependency needs.** None new for Barcelona. A second city would need its own EPW,
inventory, scored grid, and cost table (all the kinds of data already used here).

**Sim cost.** zero for the Barcelona refactor and the EPW-based seasonal cost path. A
*different measured-UTCI window or a new city* would need new live sims (flag explicitly;
not part of the default deliverable).

**Effort.** M (mechanical but wide — touches many modules) for the profile seam; the full
multi-city port is L and out of scope.

**Risk + honesty impact.** Honesty/scope win: the paper can say "the system is structured
behind a `CityProfile`; Barcelona is one instantiation; transfer requires the documented
data contract" rather than "single-city, hardwired." Risk: a wide refactor can introduce
regressions — mitigate by defaulting the profile to today's exact constants and migrating
one module at a time under the existing test suite.

**Verification.** A test instantiates `CityProfile.BARCELONA` and asserts every migrated
constant equals its former literal (behaviour-preserving refactor), plus a smoke test
that a second toy profile changes thresholds without crashing the pipeline.

---

# Synthesis

## A. Dependency graph / sequencing

```
                 ┌───────────────────────────────────────────┐
                 │  shade_proxy.py  (ray-cast / SVF shade-gain) │  ← KEYSTONE
                 └───────────────────────────────────────────┘
                    │              │                │
        ┌───────────┘     ┌────────┘        ┌───────┘
        ▼                 ▼                 ▼
   #2 placement      #4 NSGA-II        #3 portfolio
   marginal-cooling  surrogate         cooling-source
   weighting         physics           (proxy tier)
        │                                  │
        │                                  ▼
        │                            (Tier1 cached / Tier2 live)
        ▼
   CoolingEstimator interface (see C) ── unifies #2/#3/#4
                                        and the existing mock/cached/live paths

   #6 HOURS_PER_DEGC_REF ──fits──► #4 calibrated band (cost_model.band_c)
        (both consume the in-repo EPW; #6 unblocks #4's honest band)

   Independent (no shared core):
     #1 provenance reproduction      (scored_grid components)
     #5 sub-surface / sidewalk gate  (OSM geometry)
     #7 plantable-strip denominator  (shapely area already assembled)
     #8 CityProfile seam             (config refactor; benefits from all the above
                                       being parameterised)
```

Key unblocking relationships:
- **`shade_proxy` is the keystone.** It is the single new capability that powers #2
  (placement weights), #4 (surrogate physics), and #3 Tier-0 (proxy portfolio cooling).
  Build it once, reuse three times.
- **#6 unblocks #4's band.** The EPW-derived `HOURS_PER_DEGC` (#6) and the surrogate-vs-
  measured RMSE both flow into the calibrated `band_c` the cost model already accepts.
- **#1, #5, #7 are independent** quick wins with no shared core.
- **#8 should come last** — it is cleanest to parameterise constants into a profile once
  the other fixes have settled which constants matter.

## B. Prioritised roadmap

Ordered by (honesty-story impact × low sim cost × low effort). All default-tier items are
**zero new live sims**.

| # | Limitation | Honesty impact | Sim cost (default) | Effort | Priority | Notes |
|---|-----------|----------------|--------------------|--------|----------|-------|
| 1 | Satellite-composite provenance | High | zero | S | **1** | Quantifies reproducibility (ρ≈0.99) from stored components — kills the paper's biggest self-criticism cheaply |
| 6 | Cost constant calibration | Med-High | zero | S | **2** | Removes the only `REQUIRES_VERIFICATION` in cost_model using the in-repo EPW |
| 7 | Canopy-cover denominator | Med | zero | S | **3** | Truer local cover % from already-assembled geometry |
| 2 | Coverage → shade proxy | High | zero | M | **4** | Builds the keystone `shade_proxy`; physically grounds placement order |
| 3 | Synthetic portfolio cooling | High | zero (Tier0/1) | M | **5** | Tier-1 cached gives a *measured-grid* €1M portfolio with no new live cost |
| 5 | Sub-surface / sidewalk | Med | zero | M | **6** | Tightens OSM screens; keeps the survey flag honest |
| 4 | NSGA-II surrogate physics + band | High | zero | L | **7** | Removes the unsourced 12 °C cap and the assumed ±4 °C; depends on #2 + #6 |
| 8 | CityProfile seam | Med (scope) | zero | M | **8** | Architecture-readiness; do last, default to current constants |

**Single highest-leverage fix: Limitation 1 (provenance reproduction).** It is S-effort,
zero-sim, and directly neutralises the limitation the paper itself calls "the
highest-priority provenance task." Inspecting the artifact showed `composite_score_B` is
recomputable from stored `s1..s5` components and per-cell contribution weights to ρ≈0.99 —
so a small reproduction harness + datasheet converts an unqualified "we can't reproduce it"
into a quantified, defensible claim, with no data downloads and no sims.

**Highest-leverage *engineering* investment: the `shade_proxy` keystone (#2).** It is the
one new module that simultaneously improves #2, #3, and #4 — the cluster that *is* the
measured-vs-synthetic story.

## C. Shared-abstraction recommendation — `CoolingEstimator`

Limitations #2, #3, and #4 all ask "how much does this layout cool?" at different fidelities
and sim budgets. Today that question is answered inconsistently: a baseline-UTCI coverage
proxy in placement (`smart_placement`), an analytical capped surrogate in the optimizer
(`spatial_engine.thermal_relief`), and a real/replayed grid in validation (`sdk_client`).
Unify them behind one interface so each consumer picks a backend by fidelity and budget,
and so honesty labelling is centralised.

```python
# coolspend/cooling_estimator.py
from typing import Protocol

class CoolingEstimate:
    cooled_m2: float | None          # measured/estimated cooled footprint, None if N/A
    mean_delta_c: float | None       # mean ΔUTCI/ΔTmrt over cooled zone
    per_cell: dict | None            # optional grid/cell map for greedy weighting
    fidelity: str                    # "scalar" | "shade_proxy" | "cached_utci" | "live_utci"
    is_measured: bool                # True only for cached_utci/live_utci
    band_c: float | None             # uncertainty (RMSE for proxy/surrogate; grid std for measured)
    label: str                       # honesty string ("estimate (shade-proxy)" / "measured ...")

class CoolingEstimator(Protocol):
    def estimate(self, layout, site, *, baseline=None) -> CoolingEstimate: ...

# Backends (all behind the same interface):
class MockScalarEstimator:    fidelity="scalar"        # existing mock; synthetic scalar
class ShadeProxyEstimator:    fidelity="shade_proxy"   # NEW (Lim #2/#4): ray-cast sun-blockage, sim-free
class CachedUTCIEstimator:    fidelity="cached_utci"   # replay via sdk_client._cached_utci, zero new live
class LiveUTCIEstimator:      fidelity="live_utci"     # sdk_client live, SimBudget-guarded
```

How each consumer uses it:
- **Placement (#2):** `smart_placement.place_trees_greedy` weights marginal gain by
  `estimator.estimate(...).per_cell` — `ShadeProxyEstimator` by default (sim-free),
  `CachedUTCIEstimator` when a cached grid exists.
- **Optimizer (#4):** `thermal_relief` becomes `ShadeProxyEstimator().estimate(...).mean_delta_c`
  in the NSGA-II hot path; the post-hoc validation uses `LiveUTCIEstimator` /
  `CachedUTCIEstimator` (the existing 3 calls, unchanged).
- **Portfolio (#3):** `allocate_citywide`'s `cooling_source` maps directly to which
  estimator it constructs: `proxy → ShadeProxyEstimator`, `cached → CachedUTCIEstimator`,
  `live → LiveUTCIEstimator`. The `is_measured` flag drives the funding-order branch
  (`citywide.py:356`) and the honesty label in the web payload.

Payoff: one place defines the fidelity ladder and the "measured vs estimate" label, the
`shade_proxy` work is written once, and the paper's honesty architecture ("never report a
number we did not compute; label every preview as a preview") is enforced by the
`is_measured`/`fidelity`/`label` fields rather than by scattered disclaimer strings.
