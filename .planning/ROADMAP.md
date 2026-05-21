# Roadmap: CoolSpend — Tree Budget Optimizer

## Overview

Four phases deliver a live hackathon demo: stand up a clean, offline-testable skeleton with a validated SDK boundary (Phase 1), wire the optimizer core and produce the ranked decision artifact (Phase 2), wrap everything in a Gradio app and deploy to Hugging Face Spaces (Phase 3), then finalize the repo, MOCKS ledger, and demo video for submission (Phase 4). Phases 1–2 can start and complete before the API key arrives on May 27; Phase 3 wires live calls; Phase 4 ships.

## Phases

- [x] **Phase 1: Foundation & SDK Boundary** - Clean repo skeleton, deduplicated SDK client (mock/cached/live + SimBudget), spatial engine, and cost model — all offline-testable before May 27 (completed 2026-05-21)
- [ ] **Phase 2: Optimizer Core** - NSGA-II on the surrogate, Top-3 Pareto validation with real/cached UTCI, ranked allocation artifact (requires May 27 API key for live validation path)
- [ ] **Phase 3: Web App & Decision UI** - Gradio app (polygon + budget in → before/after map + allocation table out), deployed to Hugging Face Spaces with visible API calls
- [ ] **Phase 4: Ship** - requirements.txt, README with architecture diagram, MOCKS ledger, demo video and submission description

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

**Plans:** 5 plans

Plans:
- [x] 02-01-PLAN.md — rules_engine: min-spacing penalty (RULES-01) + species-diversity score (RULES-02), pure/offline (completed 2026-05-21)
- [ ] 02-02-PLAN.md — thermal surrogate in spatial_engine (OPT-02): fixed delta_tmrt_surrogate (porosity bug pinned) + thermal_relief
- [ ] 02-03-PLAN.md — wire real live Infrared backend in sdk_client (OPT-03 live path), live→cache, key-from-env, mock default
- [ ] 02-04-PLAN.md — optimizer: NSGA-II 2-objective + budget constraint (OPT-01), select_top3 + validate_top3_with_infrared (OPT-03)
- [ ] 02-05-PLAN.md — decision artifact: TOPSIS €/°C ranking + top3_configurations.json (DEC-01) + before/after (DEC-02) + main.py CLI

### Phase 3: Web App & Decision UI
**Goal**: A user can open a URL, submit a site polygon and budget, and receive an interactive before/after map with a ranked allocation table — all within a running Gradio app on Hugging Face Spaces
**Depends on**: Phase 2
**Requirements**: APP-01, APP-02

**Success Criteria** (what must be TRUE):
  1. A browser at the Hugging Face Spaces URL shows the Gradio interface with polygon input, budget slider, and TOPSIS weight sliders
  2. Submitting the default Plaça dels Àngels polygon and a sample budget triggers the full pipeline and returns the allocation table and before/after UTCI map within 120 seconds
  3. Live Infrared SDK calls are visible in the Gradio log output during the Top-3 validation step (not hidden or batched silently)
  4. The app runs correctly with `INFRARED_BACKEND=mock` (no API key) so the deployed space can be demonstrated offline if the live key is unavailable

**Plans**: TBD
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

**Plans**: TBD

## Progress

**Execution Order:** 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & SDK Boundary | 3/3 | Complete    | 2026-05-21 |
| 2. Optimizer Core | 1/5 | In progress | - |
| 3. Web App & Decision UI | 0/TBD | Not started | - |
| 4. Ship | 0/TBD | Not started | - |
