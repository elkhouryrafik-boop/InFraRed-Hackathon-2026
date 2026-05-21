# CoolSpend — Changelog

A heat-mitigation budget decision-support tool: polygon + budget in, ranked tree-planting allocation + before/after UTCI map out, proved with real Infrared SDK validation on the Top-3 configurations.

---

## Phase 1 — Foundation & SDK Boundary

*Plans 01–03: sdk_client, spatial_engine, cost_model*

- **sdk_client.py** — clean mock | cached | live Infrared SDK dispatch deduped from two reference files into one canonical client. `UTCIResult` dataclass, `SimBudget` live-call guard (raises `RuntimeError` past cap), deterministic geometry hash, lazy import of `infrared_sdk` so the module imports offline with no API key. Every mock result carries an explicit "NOT MEASURED DATA" disclaimer.
- **spatial_engine.py** — GeoJSON site loader (`load_site`), single documented CRS boundary (`latlon_to_local_m` / `local_m_to_latlon`, equirectangular + cos-latitude correction), shapely collision gate (`is_valid_location` rejects in-building, near-street, and out-of-boundary placements), module-level path cache to avoid repeated disk reads in the NSGA-II loop.
- **coolspend/data/angels_site.geojson** — hand-authored offline site fixture for Plaça dels Àngels, Barcelona (60 m × 42 m, EPSG:4326). Documented in MOCKS.md as a MOCK fixture with replacement path to real OSM export.
- **cost_model.py** — per-tree CapEx + OpEx cost model (`per_tree_cost`, `total_cost`, `cost_per_utci_degree`). DECLARED constants: CAPEX_PER_TREE_EUR=350, OPEX_PER_TREE_YEAR_EUR=35, OPEX_HORIZON_YEARS=10 — each tagged REQUIRES_VERIFICATION. Zero-delta guard returns `value=None` rather than crashing or fabricating a KPI.
- **MOCKS.md** seeded with honesty ledger rows for mock UTCI delta, GeoJSON fixture, and all DECLARED cost constants.
- Test suite bootstrapped: 22 deterministic offline tests covering backend dispatch, SimBudget guard, CRS round-trip, collision gate, and cost KPI.

---

## Phase 2 — Optimizer Core

*Plans 01–05: rules_engine, thermal surrogate, live backend wiring, NSGA-II + Top-3, decision artifact + CLI*

- **rules_engine.py** — two ecological-coherence objectives for NSGA-II. `spacing_penalty`: pairwise O(n²) linear violation depth (MIN_SPACING_M=4.0, DECLARED). `species_diversity_score`: normalised Shannon index (monoculture=0.0, balanced N-species=1.0). `ecological_score` combines them 50/50. Pollinator-corridor objective explicitly excluded (reference code constant — documented, not silently omitted). 31 deterministic offline tests.
- **Thermal surrogate** (`delta_tmrt_surrogate`, `shade_efficiency`, `thermal_relief` in `spatial_engine.py`) — ported with the porosity-squared bug fixed. Regression test pins the fix. MAX_TMRT_REDUCTION_C=12.0°C cap is UNSOURCED (no validated citation found); disclosed in MOCKS.md and in-source comment. ±4°C uncertainty documented. Zero SDK calls in the surrogate path.
- **Live Infrared backend** (`_live_utci` in `sdk_client.py`) — real `InfraredClient.run_area_and_wait` UTCI call, lazy SDK import (offline-importable), key-from-env only (never logged or embedded), live→cache write so a subsequent `INFRARED_BACKEND=cached` run replays offline. Full offline test coverage via monkeypatched fake SDK module.
- **optimizer.py** — `TreeBudgetProblem` (pymoo NSGA-II `ElementwiseProblem`): 24-float chromosome, 2 objectives (thermal relief + ecological coherence), 1 budget inequality constraint. `run_optimisation`: SBX + PM crossover/mutation, seed-42 determinism, ~60-point Pareto front in <0.5s offline. `select_top3`: three distinct Pareto representatives labelled MAX_THERMAL_RELIEF, MAX_ECOLOGICAL, BALANCED. `validate_top3_with_infrared`: SimBudget(3)-guarded real UTCI validation for each Top-3 config. Hot path confirmed SDK-free by monkeypatch test.
- **Decision artifact** — `topsis_rank`: vector-norm TOPSIS primary sort by EUR/°C ascending, TOPSIS closeness tie-break, weights (0.6/0.4) documented as developer judgment (Adjustable/MOCKS.md). `save_outputs`: writes `outputs/top3_configurations.json` (ranked allocation, before/after UTCI record, run_metadata, per-config disclaimers) and `outputs/audit_record.json` provenance trail. `plot_pareto`: best-effort Pareto scatter PNG (never blocks the JSON pipeline). `write_audit_record`: surrogate flags, TOPSIS weights, backend tags.
- **main.py** CLI (`python -m coolspend.main`) — end-to-end 5-stage pipeline with progress log and decision summary block. Offline by default; live with `INFRARED_BACKEND=live INFRARED_API_KEY=<key>`.
- Total tests at phase end: 88 deterministic offline tests.

---

## Phase 3 — Web App & Decision UI

*Plans 01–03: app_pipeline, app_viz, Gradio UI, HF Spaces deployability*

- **app_pipeline.py** — `run_decision()` UI-agnostic pipeline wrapper: safe GeoJSON parse (`json.loads` only, no eval), baseline UTCI fetch, NSGA-II run, Top-3 validation, TOPSIS ranking, SDK call-log capture via logging handler (INFO level temporarily set on sdk_client logger, restored in finally block). Returns a documented dict: `configurations`, `before_after`, `call_log`, `backend`, `banner`.
- **app_viz.py** — `render_before_after()`: headless matplotlib Agg before/after UTCI site map. Accepts the `before_after` dict from `run_decision()`, renders two side-by-side axes with baseline vs. intervention UTCI and the headline delta, writes to a temp PNG for Gradio display.
- **app.py** — Gradio Blocks UI (`build_demo()` factory): polygon textarea (pre-filled Plaça dels Àngels default), budget slider, TOPSIS weight sliders, backend radio. `on_submit()` callback: exception-guarded (never shows traceback to user), returns banner, before/after image, ranked table (3 rows + per-row Provenance column), and SDK call-log text. Module-level `demo` for `python -m coolspend.app` and HF Spaces entry point. NOT MEASURED DATA banner in mock mode.
- **requirements.txt** — pinned dependency set for HF Spaces: pymoo==0.6.1, gradio==4.44.1, huggingface_hub==0.36.2 (gradio 4.x HfFolder compatibility), shapely>=2.0, numpy>=1.26<2.0, matplotlib>=3.7, geojson>=3.0, infrared-sdk (lazy import). Clean-venv verified.
- **README.md** — Gradio Spaces YAML front-matter (`sdk: gradio`, `sdk_version: 4.44.1`, `app_file: coolspend/app.py`), run/deploy/live instructions, mermaid architecture flowchart, how-it-works prose, project-structure tree, honesty contract paragraph.
- Total tests at phase end: 122 deterministic offline tests, 1 infrastructure skip (Gradio launch smoke on Windows).

---

## Phase 4 — Ship

*Plans 01–02: documentation finalization, submission assets*

- **README.md** augmented with `## Architecture` (mermaid flowchart of all 6 modules + pipeline stages), `## How it works` with honesty caveats, `## Project structure` annotated module tree. MOCKS link corrected.
- **MOCKS.md** audited: all shipped constants have grep-verifiable rows — UTCI_BASELINE_OPEN_C/UTCI_UNDER_CANOPY_C (mock), MAX_TMRT_REDUCTION_C (UNSOURCED), TREE_SHADE_FRACTION/TREE_CANOPY_RADIUS_M (DECLARED), MIN_SPACING_M/SPECIES_PALETTE (DECLARED), CAPEX/OPEX/HORIZON (DECLARED), TOPSIS weights (Adjustable), angels_site.geojson (MOCK), live _live_utci (VERIFIED/live), surrogate top3_configurations.json outputs (MOCK/SURROGATE).
- **DEMO_SCRIPT.md** — shot-by-shot ~3-min screencast script with named persona Maria (Chief Heat Officer), hook open, shot list with timecodes, both recording commands (mock safe take + PowerShell live take), visible-real-API-call beat, EUR/°C headline close, and explicit user-records-video note. No API key embedded.
- **SUBMISSION.md** — short project description hitting all four judging axes (Technical depth, Creativity, Real-world impact, Presentation), honesty note, and GitHub / HF Space / demo video link placeholders.
- **CHANGELOG.md** — this file.

---

## Test coverage

Per project records: the offline pytest suite under `coolspend/tests/` reaches 122 tests passing, 1 skipped (infrastructure skip on Windows Gradio launch smoke test) as of Phase 3 completion. All tests are deterministic and offline-capable with no API key required. The test suite covers: SDK dispatch and SimBudget guard, CRS round-trip, shapely collision gate, cost model and KPI, spacing penalty and species diversity, thermal surrogate (including porosity-bug regression pin), live backend via monkeypatched fake SDK, NSGA-II hot-path SDK isolation, Top-3 selection and SimBudget enforcement, TOPSIS ranking, decision artifact JSON schema, pipeline wrapper, before/after map renderer, Gradio Blocks construction, and requirements drift guard.
