# Roadmap: CoolSpend — Tree Budget Optimizer

## Overview

Four phases deliver a live hackathon demo: stand up a clean, offline-testable skeleton with a validated SDK boundary (Phase 1), wire the optimizer core and produce the ranked decision artifact (Phase 2), wrap everything in a Gradio app and deploy to Hugging Face Spaces (Phase 3), then finalize the repo, MOCKS ledger, and demo video for submission (Phase 4). Phases 1–2 can start and complete before the API key arrives on May 27; Phase 3 wires live calls; Phase 4 ships.

**Milestone v2.0 — Market-Ready CoolSpend (Phases 5–9):** Convert the credible *framework* into a defensible *product*. Phase 5 is the existential keystone — ground-truth the surrogate against real Infrared UTCI and reset every external claim to honest phrasing; if surrogate rankings don't hold, the rest of the milestone is invalid. Phase 6 fixes the ~10×-low cost denominator so the €/°C KPI survives an auditor. Phase 7 replaces hand-authored fixtures with real OSM/cadastre geometry and an N-site data model. Phase 8 is the product pivot: allocate one budget across competing intervention types (trees + cool roofs) and across N city sites with equity weighting. Phase 9 is the go-to-market/defensibility layer: GIS interop, procurement and grant-compliance exports, and a reproducible per-run audit manifest. Execution is strictly downstream of Phase 5 — validate before betting.

## Phases

- [x] **Phase 1: Foundation & SDK Boundary** - Clean repo skeleton, deduplicated SDK client (mock/cached/live + SimBudget), spatial engine, and cost model — all offline-testable before May 27 (completed 2026-05-21)
- [x] **Phase 2: Optimizer Core** - NSGA-II on the surrogate, Top-3 Pareto validation with real/cached UTCI, ranked allocation artifact (requires May 27 API key for live validation path) (completed 2026-05-21)
- [x] **Phase 3: Web App & Decision UI** - Gradio app (polygon + budget in → before/after map + allocation table out), deployed to Hugging Face Spaces with visible API calls (completed 2026-05-21)
- [x] **Phase 4: Ship** - requirements.txt, README with architecture diagram, MOCKS ledger, demo video and submission description (completed 2026-05-21)
- [ ] **Phase 5: Surrogate Ground-Truth & Honesty Reset** - Validate the ΔTmrt surrogate against real Infrared UTCI across varied configs, convert to UTCI before the KPI, single CRS end-to-end, and relabel every overclaim down to what is actually proven (v2.0 keystone)
- [ ] **Phase 6: Cost-Model Credibility** - Replace placeholder per-tree costs with a fully-loaded, cited, per-city-configurable lifecycle figure with growth-horizon discounting
- [ ] **Phase 7: Real Geometry & Multi-Site Ingestion** - Load arbitrary OSM/cadastre geometry, reject collisions against real building/footway polygons, support N candidate sites per project
- [ ] **Phase 8: Multi-Intervention & Portfolio Triage** - Make intervention type a parameter (trees + cool roofs), allocate one budget across competing types and across N citywide sites with equity weighting
- [ ] **Phase 9: Workflow, Grant Packaging & Audit** - GIS layer import/export (GeoPackage/Shapefile), procurement and grant-compliance exports, stakeholder-elicited weights, and a reproducible per-run audit manifest

## Phase Details

### Phase 1: Foundation & SDK Boundary
**Goal**: Developers can run the full offline pipeline end-to-end (mock backend) and every module has a tested, clean interface boundary — no live key required
**Depends on**: Nothing (first phase)
**Requirements**: SDK-01, SDK-02, SDK-03, SPATIAL-01, SPATIAL-02, SPATIAL-03, COST-01, COST-02

**Build window note:** This phase is fully executable before May 27. Live-key validation (SDK-01 live path) is tested on May 27 morning only; the offline contract must pass first.

**Success Criteria** (what must be TRUE):
  1. Running `INFRARED_BACKEND=mock python optimizer.py` completes without error and produces `outputs/top3_configurations.json` with `disclaimer: "NOT MEASURED DATA"` in every config
  2. `is_valid_location(x, y)` rejects points inside hardcoded building footprints, on street centerlines, and outside the site boundary polygon — verified by a passing unit test
  3. `cost_per_utci_degree(cfg)` returns a finite `€/°C` value with documented CapEx + OpEx assumptions and the cost assumptions are visible as constants in `cost_model.py`
  4. `SimBudget` guard raises an error if `_evaluate()` (the NSGA-II hot path) is called with `INFRARED_BACKEND=live` — the live path is only reachable through the explicit `validate_top3_with_infrared()` function
  5. EPSG:4326 ↔ plaza-local-metres conversion is implemented at exactly one boundary and asserted by `test_coordinate_frame.py`

**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md — Package skeleton, dedup SDK client (mock|cached|live), SimBudget guard, MOCKS.md seed
- [x] 01-02-PLAN.md — Spatial engine: GeoJSON site load, is_valid_location collision, single CRS boundary
- [x] 01-03-PLAN.md — Cost model: CapEx+OpEx per-tree cost and €/°C KPI

### Phase 2: Optimizer Core
**Goal**: Given a site polygon and budget, the pipeline produces a ranked Top-3 Pareto allocation with real (or cached) Infrared UTCI validation and a before/after UTCI delta
**Depends on**: Phase 1
**Requirements**: RULES-01, RULES-02, OPT-01, OPT-02, OPT-03, DEC-01, DEC-02

**Build window note:** NSGA-II on the surrogate (OPT-01, OPT-02) and rules engine (RULES-01, RULES-02) can be built and smoke-tested before May 27 using `INFRARED_BACKEND=cached`. The live Top-3 validation (OPT-03) requires the May 27 API key.

**Success Criteria** (what must be TRUE):
  1. `run_optimisation()` completes in under 60 seconds on demo hardware and returns a Pareto front of at least 10 distinct configurations using only the analytical surrogate in the hot path (zero live SDK calls)
  2. Minimum-spacing and species-diversity penalties are active: a configuration that places two trees within the minimum spacing distance scores worse than one with adequately spaced trees
  3. `validate_top3_with_infrared()` calls the Infrared SDK exactly 3 times (Top-3 configs only), the `SimBudget` log confirms the call count, and each result replaces the surrogate estimate with a labelled real UTCI delta
  4. `outputs/top3_configurations.json` contains three ranked configs in `€/°C` order, each with `rank`, `label`, `delta_tmrt_c` (surrogate), `topsis_score`, and a real validated UTCI delta
  5. `outputs/pareto_front.png` renders and `outputs/audit_record.json` includes the honesty provenance trail (surrogate note, uncertainty ±4°C, data source tags)

**Plans:** 5/5 plans complete

Plans:
- [x] 02-01-PLAN.md — rules_engine: min-spacing penalty (RULES-01) + species-diversity score (RULES-02), pure/offline (completed 2026-05-21)
- [x] 02-02-PLAN.md — thermal surrogate in spatial_engine (OPT-02): fixed delta_tmrt_surrogate (porosity bug pinned) + thermal_relief (completed 2026-05-21)
- [x] 02-03-PLAN.md — wire real live Infrared backend in sdk_client (OPT-03 live path), live→cache, key-from-env, mock default (completed 2026-05-21)
- [x] 02-04-PLAN.md — optimizer: NSGA-II 2-objective + budget constraint (OPT-01), select_top3 + validate_top3_with_infrared (OPT-03) (completed 2026-05-21)
- [x] 02-05-PLAN.md — decision artifact: TOPSIS EUR/degC ranking + top3_configurations.json (DEC-01) + before/after (DEC-02) + main.py CLI (completed 2026-05-21)

### Phase 3: Web App & Decision UI
**Goal**: A user can open a URL, submit a site polygon and budget, and receive an interactive before/after map with a ranked allocation table — all within a running Gradio app on Hugging Face Spaces
**Depends on**: Phase 2
**Requirements**: APP-01, APP-02

**Success Criteria** (what must be TRUE):
  1. A browser at the Hugging Face Spaces URL shows the Gradio interface with polygon input, budget slider, and TOPSIS weight sliders
  2. Submitting the default Plaça dels Àngels polygon and a sample budget triggers the full pipeline and returns the allocation table and before/after UTCI map within 120 seconds
  3. Live Infrared SDK calls are visible in the Gradio log output during the Top-3 validation step (not hidden or batched silently)
  4. The app runs correctly with `INFRARED_BACKEND=mock` (no API key) so the deployed space can be demonstrated offline if the live key is unavailable

**Plans:** 3/3 plans complete

Plans:
- [x] 03-01-PLAN.md — app_pipeline.run_decision (UI-agnostic pipeline wrapper + safe GeoJSON parse + visible SDK call-log) and app_viz.render_before_after (headless matplotlib before/after map) (completed 2026-05-21)
- [x] 03-02-PLAN.md — app.py Gradio Blocks UI: polygon + budget + TOPSIS sliders + backend selector → headline + before/after map + allocation table + call log; headless launch smoke test (completed 2026-05-21)
- [x] 03-03-PLAN.md — HF Spaces deployability: pinned requirements.txt + README Spaces header + deploy/mock-vs-live steps + dependency-contract test (completed 2026-05-21)

**UI hint**: yes

### Phase 4: Ship
**Goal**: The GitHub repo is submission-ready: pinned dependencies, a self-contained README with architecture diagram, a MOCKS ledger documenting every surrogate and unverified assumption, and a 2.5–3 min demo video
**Depends on**: Phase 3
**Requirements**: SHIP-01, SHIP-02, SHIP-03

**Success Criteria** (what must be TRUE):
  1. `pip install -r requirements.txt` in a clean virtual environment installs all dependencies (pymoo==0.6.1, shapely, geojson, numpy, infrared-sdk, gradio) without conflicts
  2. README contains an architecture diagram that maps all six modules (sdk_client, spatial_engine, rules_engine, cost_model, optimizer, app) and explains the surrogate-optimize → validate-Top-3 → rank pipeline
  3. MOCKS ledger in README lists every surrogate, mock value, and DECLARED/PENDING data item (at minimum: `delta_tmrt_surrogate` ±4°C uncertainty, `MAX_TMRT_REDUCTION=12°C` unsourced cap, TOPSIS weights as user-adjustable)
  4. The demo video (2.5–3 min) shows the live Gradio app, a real Infrared API call completing visibly, and the ranked allocation output — uploaded and linked from the submission description

**Plans:** 2/2 plans complete

Plans:
- [x] 04-01-PLAN.md — Verify requirements.txt install (SHIP-01) + augment README with architecture diagram/how-it-works/structure & fix MOCKS link + audit MOCKS.md (SHIP-02) (completed 2026-05-21)
- [x] 04-02-PLAN.md — Submission assets: DEMO_SCRIPT.md (shot-by-shot screencast + commands), SUBMISSION.md (four judging axes + links), CHANGELOG.md (SHIP-03) (completed 2026-05-21)

---

## Milestone v2.0 — Market-Ready CoolSpend (Phases 5–9)

### Phase 5: Surrogate Ground-Truth & Honesty Reset
**Goal**: The headline KPI stops being assumption ÷ assumption — the surrogate is quantitatively validated against real Infrared UTCI, the KPI reports true UTCI (not raw Tmrt) as an uncertainty interval over one consistent CRS, and every external claim is relabeled down to what is actually proven. This is the existential keystone: if surrogate rankings don't hold against measured UTCI, the rest of v2.0 is built on sand.
**Depends on**: Phase 4 (v1.0 complete)
**Requirements**: VALID-01, VALID-02, VALID-03, VALID-04, VALID-05, HONEST-01, HONEST-02, HONEST-03, HONEST-04
**Success Criteria** (what must be TRUE):
  1. A user can run a calibration study across 5–10 deliberately varied configurations and read back an RMSE/R² fit with an error band quantifying how well the ΔTmrt surrogate tracks real Infrared UTCI
  2. The €/°C KPI is computed from a true UTCI-hours delta (surrogate ΔTmrt routed through `utci_hours_above()`), never from raw Tmrt, and is reported as an uncertainty interval — never a bare point estimate
  3. A user can see whether the Top-3 picks chosen on the surrogate stay the Top-3 when re-simulated with real Infrared UTCI, with any rank shift reported explicitly
  4. All geometry runs through one projected metric CRS (UTM 31N) end-to-end, and a round-trip consistency assertion fires before any live SDK call
  5. External copy contains no "validated with Infrared" or "88% vs naive" claims; `CONCEPT_REPORT.md` matches `MOCKS.md`; the surrogate ceiling cites a tree/pedestrian-Tmrt source (Schrodi 2023 / Rahman 2022) with Garcia-Nevado demoted; and unmodeled siting constraints are listed as explicit out-of-scope exclusions
**Plans:** 5 plans

Plans:
- [x] 05-01-PLAN.md — UTM-31N (EPSG:32631) CRS migration: per-site origin + <1m fail-closed round-trip guard before every live call (VALID-05) (completed 2026-05-21)
- [x] 05-02-PLAN.md — KPI routed through utci_hours_above (UTCI not raw Tmrt), dual units, [lo,hi] uncertainty interval (VALID-02, VALID-04) (completed 2026-05-21)
- [ ] 05-03-PLAN.md — Calibration study: 10-config coverage sweep, live-recorded RMSE/R²/band + ranking stability both ways, separate SimBudget (VALID-01, VALID-03)
- [ ] 05-04-PLAN.md — Honesty (code): delete naive-baseline/improvement_vs_naive, re-anchor surrogate citation (Schrodi/Rahman), fix artifact JSON phrasing (HONEST-02, HONEST-03)
- [ ] 05-05-PLAN.md — Honesty (docs+UI): scrub CONCEPT_REPORT/README/demo/MOCKS/app overclaims, out-of-scope exclusions list (HONEST-01, HONEST-02, HONEST-03, HONEST-04)

### Phase 6: Cost-Model Credibility
**Goal**: The €/°C denominator survives a budget auditor — per-tree cost is a fully-loaded, sourced lifecycle figure that the user can localize per city, with cooling benefit discounted over the establishment/growth curve rather than assumed day-one.
**Depends on**: Phase 5
**Requirements**: COST-03, COST-04, COST-05
**Success Criteria** (what must be TRUE):
  1. Per-tree cost reflects a fully-loaded lifecycle figure (pit excavation, structural soil, guarding, multi-year establishment OpEx) anchored to a cited procurement source, replacing the €350/€35 placeholders
  2. A user can edit the cost table per city/locale through inputs rather than recompiling hardcoded constants, and the KPI recomputes from the edited values
  3. The €/°C KPI applies a growth-horizon discount so the modeled cooling benefit follows the establishment/growth curve instead of assuming full canopy on day one
**Plans**: TBD

### Phase 7: Real Geometry & Multi-Site Ingestion
**Goal**: The pipeline runs on real-world geometry instead of hand-authored fixtures — a user can load any city site from OSM/cadastre, collisions are rejected against actual building and footway polygons, and the data model holds N candidate sites within one project.
**Depends on**: Phase 5
**Requirements**: GEO-01, GEO-02, GEO-03
**Success Criteria** (what must be TRUE):
  1. A user can load arbitrary city geometry from OSM/cadastre for a site that was never hand-authored, and the optimizer runs against it end-to-end
  2. Collision rejection uses building footprint and carriageway/footway polygons (not street-centreline buffers), so candidate placements respect real ground truth
  3. A single project can hold N candidate sites in its data model and the pipeline can iterate over all of them
**Plans**: TBD

### Phase 8: Multi-Intervention & Portfolio Triage
**Goal**: CoolSpend delivers on its name — intervention type becomes a parameter (trees + cool roofs as the proof pair), one fixed budget is allocated across competing intervention types by €/°C, and the allocation extends from a single plaza to a citywide portfolio of N sites with equity weighting for heat-vulnerable areas.
**Depends on**: Phase 6, Phase 7
**Requirements**: MULTI-01, MULTI-02, TRIAGE-01, TRIAGE-02
**Success Criteria** (what must be TRUE):
  1. A user can choose intervention type as a parameter (trees + cool roofs), with no hardcoded tree-only assumption left in the pipeline
  2. A user can allocate one fixed budget across competing intervention types and see them ranked by €/°C
  3. A user can rank N sites by €/°C and receive a citywide budget allocation across sites, not just within one plaza
  4. The citywide allocation can be equity-weighted to prioritize heat-vulnerable / overburdened areas, and the weighting visibly changes the allocation
**Plans**: TBD

### Phase 9: Workflow, Grant Packaging & Audit
**Goal**: CoolSpend enters real planning and funding workflows and can defend every number — outputs export to GIS and procurement formats, city GIS layers import as inputs, the allocation maps onto a grant reporting template, and every run emits a reproducible audit manifest with stakeholder-elicited weights.
**Depends on**: Phase 8
**Requirements**: EXPORT-01, EXPORT-02, EXPORT-03, GRANT-01, AUDIT-01, AUDIT-02
**Success Criteria** (what must be TRUE):
  1. A user can export the recommended layout as GeoPackage/Shapefile and open it in standard GIS, and import existing city GIS layers (canopy/heat/LST from ArcGIS/QGIS/i-Tree) as inputs
  2. A user can export a procurement-ready cost summary (PDF/CSV) with line items
  3. A user can generate an allocation appendix mapped to a grant reporting template (EU LIFE / European Urban Initiative)
  4. Every run emits a reproducible audit manifest (inputs, model + surrogate version, data-source tags, re-run command)
  5. Objective weights are stakeholder-elicited and recorded in the audit trail, replacing the developer-default TOPSIS 0.6/0.4
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:** 1 → 2 → 3 → 4 (v1.0 complete) → 5 → {6, 7} → 8 → 9 (v2.0)

**Note:** Phases 6 and 7 both depend only on Phase 5 and can proceed in parallel after the keystone validates; Phase 8 requires both.

### Milestone v1.0 (complete)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & SDK Boundary | 3/3 | Complete    | 2026-05-21 |
| 2. Optimizer Core | 5/5 | Complete    | 2026-05-21 |
| 3. Web App & Decision UI | 3/3 | Complete    | 2026-05-21 |
| 4. Ship | 2/2 | Complete    | 2026-05-21 |

### Milestone v2.0 — Market-Ready CoolSpend

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 5. Surrogate Ground-Truth & Honesty Reset | 2/5 | Executing | 2026-05-21 |
| 6. Cost-Model Credibility | 0/TBD | Not started | - |
| 7. Real Geometry & Multi-Site Ingestion | 0/TBD | Not started | - |
| 8. Multi-Intervention & Portfolio Triage | 0/TBD | Not started | - |
| 9. Workflow, Grant Packaging & Audit | 0/TBD | Not started | - |
