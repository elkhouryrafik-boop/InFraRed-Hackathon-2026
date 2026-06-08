# Codebase Concerns

**Analysis Date:** 2026-06-01

This document enumerates known limitations, technical debt, and gaps for CoolSpend, grounded in `PAPER.md` Section 9, `MOCKS.md`, the `coolspend/` source, `web/public/citywide_plan.json`, and the git working tree. Every limitation is classed as **OPEN**, **REMEDIATED**, or **STALE-DOC** (a doc still describing a now-resolved state). The project's stated bar is "never report a number it did not compute, and label every preview as a preview" (`PAPER.md` §10); concerns below are measured against that bar.

---

## Methodological Limitations (from PAPER.md Section 9)

These are scientific scope limits, not code defects. Several were remediated this cycle; the residual is honest epistemic uncertainty, by design.

**1. Satellite-composite provenance** *(substantially remediated; residual OPEN).*
- Issue: The vulnerability composite *ranking formula* is exactly reproducible in-repo (least-squares fit recovers a constant weight vector reconstructing `composite_score_B` to R² = 1.0, regression-tested). The residual gap is the derivation of the three sub-scores from *raw imagery* — the Sentinel-1 SAR-to-sealed classifier and its training data, the Landsat LST-anomaly baseline, and the `mismatch`/`prpi` index definitions.
- Files: `coolspend/provenance.py`; `web/public/scored_grid.geojson`; source imagery pipeline lives in `L1_INGEST_data/` (external upstream, undocumented here).
- Impact: A reviewer can verify the ranking math but not trace each sub-score back to pixels.
- Fix approach: Obtain/document the upstream ingestion source; re-running CoolSpend does not close this.

**2. Coverage proxy versus measured cooling** *(remediated in the deployed engine).*
- Issue: Greedy placement weights each (slot, species)→cell pair by ray-cast **shade-gain** (fraction of sampled suns whose crown shadow lands on the cell), capped per cell so double-shading earns nothing; objective stays submodular, preserving the (1 − 1/e) guarantee. Shade-gain is a first-order direct-beam proxy used only for *placement order*; cooling *magnitude* always comes from live UTCI validation.
- Files: `coolspend/smart_placement.py`, `coolspend/shade_proxy.py`, `coolspend/cooling_estimator.py`.
- Impact: Residual is epistemic (placement-order proxy), not a magnitude error — by design.

**3. Synthetic cooling on non-live backends** *(remediated for the headline; OPEN for cheapest tier).*
- Issue: Headline €1,000,000 portfolio and single-site showcase use **live Infrared UTCI** (`cooling_source = "measured_utci"`, `cooling_is_measured = true` in `web/public/citywide_plan.json`), cached by geometry hash for offline replay. A three-tier `CoolingEstimator` provides geometry-grounded shade-proxy *estimates* for sim-free builds, with `is_measured` as the single honesty flag and a UI badge. Residual: the cheapest sim-free tier remains an estimate.
- Files: `coolspend/cooling_estimator.py` (`CoolingEstimate.is_measured` / `fidelity` / `label` fields; ladder Mock→ShadeProxy→Cached→Live), `coolspend/sdk_client.py`.
- Impact: Acceptable only because the estimate-vs-measured distinction is structurally enforced (one flag), not via scattered disclaimer strings.

**4. Surrogate thermal relief (NSGA-II alternative)** *(remediated; not in deployed path).*
- Issue: Former ±4 °C uncertainty replaced by an empirical **±0.78 °C** band (1.96 × RMSE from a live calibration study). Surrogate characterised honestly: R² = −0.946 (weak magnitude) but Spearman ρ = 0.69 (moderate ranking) — hence confined to *ranking* inside an alternative the production pipeline does not use. The `MAX_TMRT_REDUCTION_C = 12.0 °C` cap is an unsourced guard, non-binding (never reached in practice).
- Files: `coolspend/spatial_engine.py` (`MAX_TMRT_REDUCTION_C`, `delta_tmrt_surrogate`), `coolspend/optimizer.py` (`topsis_rank`), `coolspend/calibration.py`.
- Impact: Contained — production placement does not use the surrogate. The 12 °C cap remains unsourced (`MOCKS.md` row, `REQUIRES_VERIFICATION`).

**5. Unsurveyed sub-surface conditions** *(OPEN — flagged, not asserted clear).*
- Issue: Underground utilities and exact sidewalk widths are absent from open data. In-ground slots are flagged for a pre-dig utility survey rather than asserted clear; the 6 m foundation setback is a conservative placeholder pending species- and code-specific verification.
- Files: `coolspend/candidate_slots.py`, `coolspend/placement_inputs.py`, `coolspend/docs/placement_spatial_constraints.md`.
- Impact: Any committed plan requires a physical utility survey before digging; setback may be over- or under-conservative per species/code.

**6. Cost calibration** *(remediated; residual OPEN).*
- Issue: The `REQUIRES_VERIFICATION` UTCI-hours-above-32 °C constant (h removed per °C cooling) is now computed directly from the in-repo Barcelona TMYx EPW via ladybug UTCI (~47 h/°C, band-mean), replacing the prior hand-derived 200 h/°C; reported with its band (relationship is convex). Three of five CapEx lines (`tree_stock` €600, `pit_excavation` €500, `structural_soil` €600) remain `DECLARED` pending direct BCN tender unit-price extraction; two (`guarding` €200, `planting_labour` €300) and `annual_opex` (€60/yr) are `VERIFIED`.
- Files: `coolspend/cost_model.py` (`DEFAULT_COST_TABLE`), `coolspend/epw_weather.py`, `coolspend/tests/test_hours_per_degc.py`, `MOCKS.md` cost rows.
- Impact: Headline €/m²-cooled (single-site €30, portfolio €44) carries a CapEx band until tender prices land.

**7. Portfolio budget headroom** *(OPEN — deliberate, not a defect).*
- Issue: Committed plan spends **€900,000 of €1,000,000** (`web/public/citywide_plan.json`: `total_allocated_eur = 900000`, `remaining_eur = 100000`, `allocated_count = 6` sites, `total_trees = 90`). The remaining €100k is uncommitted because feasibility, population-weighting, and per-*barri* de-duplication filters exhausted the qualifying candidate pool before a 7th distinct site cleared every gate.
- Files: `coolspend/citywide.py`, `web/public/citywide_plan.json`.
- Impact: Reported as a conservative default. Demo narrative must own "€900k of €1M / 6 sites / ~26,745 served" as the honest number (per project memory: 6 sites/26k replaced an earlier inflated 8 sites/48k proxy count).
- Fix approach: Widen candidate pool (larger top-N) to commit the remainder across more sites.

**8. Single-city scope and static meteorology** *(OPEN — out of scope).*
- Issue: Data assembly, species palette, and cost figures are Barcelona-specific; UTCI window is a fixed July peak-heat period. Seasonal/inter-annual variation and transfer to other climates are out of scope.
- Files: `coolspend/bcn_data.py`, `coolspend/bcn_species.py`, `coolspend/epw_weather.py`, `coolspend/sites.py`.
- Impact: No claim of generality; results are a Barcelona case study.

---

## Honesty-Ledger Items (MOCKS.md)

`MOCKS.md` is the single ledger for every mock/surrogate/declared constant; the pre-merge rule is that each `# MOCK:`/`# SURROGATE:` code comment maps to a row.

**DECLARED modelling constants (OPEN — labelled, user-editable).**
- Ecological rules: `MIN_SPACING_M` (`rules_engine.py`, planting-guideline assumption, not BCN code), `SPECIES_PALETTE` (demo mix, not verified against Arbrat Viari recommended list).
- Canopy assumptions: `TREE_SHADE_FRACTION = 0.80`, `TREE_CANOPY_RADIUS_M = 3.0` (`spatial_engine.py`, not from surveyed inventory).
- Growth/discount: `GrowthDiscountParams` (ramp_years=25, initial_fraction=0.20, discount_rate=3.5% Green Book, horizon=40 yr) in `cost_model.py` — DECLARED, user-editable, not locally calibrated.
- TOPSIS weights (0.6 thermal / 0.4 ecological, `optimizer.py`) — developer judgment, not stakeholder-elicited.
- Impact: All carry `REQUIRES_VERIFICATION` and are surfaced as editable parameters; none enter the *measured* headline KPI path.

**STALE-DOC rows in MOCKS.md (resolve text; behaviour already correct).**
- "live UTCI result … WIRED — UNVERIFIED until real SDK confirmation (May 27)" and the `_live_utci` TODO about an unconfirmed `AnalysesName` enum member / `merged_grid` field: now resolved in code — `coolspend/sdk_client.py` uses concrete `AnalysesName.thermal_comfort_index` and `result.merged_grid`, and the live path has executed (273 cached measured runs in `coolspend/cache/infrared/`, `cooling_source = "measured_utci"`). The MOCKS.md row still reads "UNVERIFIED" and "never executed in this repository."
- Fix approach: Update the MOCKS.md live-UTCI and `_live_utci` rows to VERIFIED to match `sdk_client.py` and the cache.
- The `naive_baseline` / "88% vs naive" row is correctly kept as a tombstone (feature removed; do not reintroduce).

---

## Technical Debt & Working-Tree State

**Uncommitted working-tree changes (OPEN — risk of an unreviewed showcase).**
- `git status` shows modified, uncommitted: `web/src/components/Scene.tsx`, `FallbackScene.tsx`, `IntroVideoGate.tsx`, and the published single-site bundle `web/public/eval_bundle/{boundary.geojson,bounds.json,decision.json,scene.glb,trees.geojson}` (scene.glb shrank 2.09 MB → 1.16 MB), plus `web/tsconfig.app.tsbuildinfo`. `web/public/coolspend-explainer.mp4` is deleted (36 MB) in the tree.
- Impact: The deployed single-site showcase bundle (`eval_bundle/`) differs from `HEAD`; a build/demo from a clean checkout would not match local state. `decision.json` changed substantially (50 lines).
- Fix approach: Review and commit (or revert) the `eval_bundle/` and component changes before any demo build; confirm `decision.json` numbers still reconcile with `PAPER.md` §10 (single-site: 4,268 m² cooled, €30/m², 31.0→29.8 °C).

**Single-site showcase bundle freshness (WATCH).**
- The eval_bundle is a precomputed artifact, not regenerated at request time; the in-tree edits above mean the committed version may be stale relative to the current engine. Per memory, an earlier risk was a stale/mock bundle being published over the real one.
- Files: `web/public/eval_bundle/`, `coolspend/export_web.py`.
- Fix approach: Regenerate from `export_web.py` against the live/cached backend and commit, so the bundle provenance is reproducible.

**Default backend is `mock` (WATCH — correct but foot-gun).**
- `sdk_client.py` defaults `INFRARED_BACKEND` to `mock` (returns synthetic scalar UTCI carrying `MOCK_DISCLAIMER`). Headline artifacts must be produced under `live`/`cached`, not the default.
- Files: `coolspend/sdk_client.py` (`_backend()` line ~68).
- Impact: A fresh run without explicit backend selection yields NOT-MEASURED data; only the `is_measured` flag / disclaimer prevents misreporting. Keep that flag wired through to any new output surface.

---

## Security Considerations

**Secrets handling (mitigated; rotation OPEN per memory).**
- Risk: Infrared, Mapbox, and Cesium credentials.
- Mitigation in place: `.env` (project root) and `web/.env.local` are **git-ignored** (confirmed via `git check-ignore`); neither is tracked. `INFRARED_API_KEY` is read from environment (`README.md`); web tokens `VITE_MAPBOX_TOKEN` (required) and `VITE_CESIUM_ION_TOKEN` (optional, photoreal disabled by default) live in `web/.env.local`.
- Residual: Project memory (Swarm Audit 2026-05-30) flagged "rotate .env key" as an outstanding action. Whether the Infrared key has since been rotated is not verifiable from the repo (key is not in-tree, by design).
- Recommendation: Confirm the previously-exposed Infrared key was rotated; keep `.env*` out of git and out of any committed bundle.

---

## Test Coverage Gaps

**Calibration / cost constants are tested; some DECLARED constants are not behaviorally validated.**
- Covered: `coolspend/tests/test_cooling_estimator.py`, `test_hours_per_degc.py` (EPW-derived h/°C), provenance R²=1.0 regression test.
- Gap: DECLARED canopy/growth/spacing constants (`TREE_SHADE_FRACTION`, `MIN_SPACING_M`, growth ramp) have no empirical validation test — they are assumptions, not derived values, so tests assert wiring, not correctness.
- Risk: A wrong DECLARED constant would pass tests; only field/tender verification closes it.
- Priority: Medium (constants are clearly labelled and out of the measured headline path).

---

## Missing / Deferred Features

**Frontend multi-site citywide viz** *(REMEDIATED).*
- Project memory listed "frontend multi-site viz still TODO." It is now implemented: `web/src/components/CitywidePanel.tsx`, `ModeSwitch.tsx` (Design ↔ Citywide), `App.tsx` boots into the €1M citywide plan, all numbers sourced from `web/public/citywide_plan.json` (real, measured). No open multi-site-viz gap remains.

**Seventh portfolio site** *(deferred — see Limitation 7).*
- The €100k headroom / 7th-site commitment is the single most concrete deferred feature; future work per `PAPER.md` §10 is to widen the candidate pool.

---

*Concerns audit: 2026-06-01*
