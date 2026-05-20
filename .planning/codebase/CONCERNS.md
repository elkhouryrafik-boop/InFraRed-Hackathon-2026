# Codebase Concerns — coolspend Hackathon Port

**Analysis Date:** 2026-05-21
**Context:** Porting selected logic from NatureGooddest parent project into a new
`coolspend` app for the Infrared City Hackathon (3-day build, May 27–31 2026).
Source files analysed: `nature_nsga2_coolstock.py`, `nature_metrics.py`,
`infrared_client_v2.py`, `nature_infrared_client.py`, `nature_architecture.md`,
`HANDOFF.md`, `CONCEPT_REPORT.md`.

---

## 1. Mocks / Unverified Data

Per the NatureGooddest honesty contract: every mock, surrogate, or DECLARED data
source must be tracked and must not be presented as measured data. All items below
carry over to coolspend unless explicitly replaced.

### 1.1 `delta_tmrt_surrogate()` — primary thermal model

- **Status:** MOCK / analytical proxy. Explicitly marked `DEPRECATED 2026-05-19`
  in parent; kept only to serve the legacy `demo_app.py /surrogate` POST route.
  The parent project's own production path **does not use this function** for
  reported results — it uses cached Infrared SDK UTCI runs.
- **File:** `nature_nsga2_coolstock.py` lines 106–155
- **What it is:** Linear interpolation between two literature ceilings
  (Garcia-Nevado 2020 surface-temp proxy + Vanos 2020 shade-component lower bound).
  `MAX_TMRT_REDUCTION = 12.0 °C` is an **unsourced hard-coded cap** with no error
  bar and no validation against any Ladybug or Infrared simulation.
- **Known bug (fixed upstream, NOT yet reflected in cached outputs):** The
  porosity penalty was applied twice (squared). Fixed 2026-05-20 (audit C10) but
  all existing `top3_configurations.csv/json`, `audit_record.json`, and
  `placement_*.geojson` files in the parent project are stale relative to the fix.
  If coolspend copies any of those cached outputs, the ΔTmrt figures are biased
  ~12–15% low.
- **Citation mismatch:** Garcia-Nevado 2020 measures infrared thermography of
  pavement surface temperature, NOT mean radiant temperature at 1.1 m pedestrian
  height. The function's docstring acknowledges this explicitly.
- **Replacement path for coolspend:** Do NOT port this as a truth-producing model.
  Use it offline only (NSGA-II surrogate loop); validate the top-3 outputs with
  real Infrared SDK UTCI calls. Uncertainty must be quoted as ±4 °C per the parent
  audit record.
- **Severity:** HIGH — using this function's output as a Tmrt prediction without
  a disclaimer is a honesty violation and will fail jury scrutiny.

### 1.2 `pollinator_corridor_score()` — third NSGA-II objective (F3)

- **Status:** DEGENERATE in practice. Documented audit finding 2026-05-20 (C10 /
  09 C-1) in `nature_nsga2_coolstock.py` lines 169–180.
- **File:** `nature_nsga2_coolstock.py` lines 158–193
- **What it is:** Because `_evaluate()` hard-clamps `y_m = max(y_m, HERITAGE_BUFFER_M)`,
  solutions pinned to the buffer dominate the Pareto front and all return a
  `north_score` ≈ 1.0. The third objective is effectively constant — the stated
  3-objective problem degenerates to 2-objective (cooling vs. material).
- **Impact for coolspend:** If the tree-budget app keeps an ecology objective,
  port the concept but re-implement the scoring without the y-clamp collapse. If
  not porting ecology, this can simply be dropped.
- **Severity:** MEDIUM — misleading if presented as a genuine tri-objective
  optimisation. Low severity if coolspend drops ecology objective entirely.

### 1.3 Infrared mock backend — `infrared_client_v2.py` / `nature_infrared_client.py`

- **Status:** MOCK. Both files are identical content (see §2.1 for the duplicate
  concern). The `_mock_tmrt_field()`, `_mock_utci_field()`, and `_mock_wind_field()`
  functions return deterministic synthetic grids built from `math.sin/cos`
  oscillations anchored to hand-crafted base values:
  - Bare plaza Tmrt: 58.2 °C (`base_open`) — sourced from Garcia-Nevado midterm S0
  - Under-canopy Tmrt: 39.5 °C (`base_canopy`) — sourced from midterm r1 (ΔTmrt ~18.7)
  - Open UTCI: 41.0 °C; under-canopy UTCI: 30.5 °C
  - Wind speed open plaza: 4.2 m/s (EPW Barcelona July mean)
- **File:** `infrared_client_v2.py` lines 155–295 (identical in
  `nature_infrared_client.py`)
- **Critical:** `INFRARED_BACKEND=live` raises `NotImplementedError` in both files
  (line 343): `"INFRARED_BACKEND=live not wired yet"`. The live path was never
  wired inside this module — the parent project went directly to the Infrared SDK
  (`from infrared_sdk import InfraredClient`) in a separate script, bypassing this
  module entirely.
- **For coolspend:** Import only if you need a mock backend for offline dev.
  The live path in these files is a dead stub — wire the Infrared SDK directly
  as coolspend's `infrared_runner.py` (do not resurrect the `INFRARED_BACKEND`
  env-var dispatch).
- **Severity:** HIGH if mock fields are inadvertently used in demo output and
  not labelled. Low if used strictly as an offline stand-in with an explicit
  "MOCK DATA" label (the parent project overlaid a hatch in the UI).

### 1.4 ULMA scaffold inventory — declared, not verified

- **Status:** `DECLARED` (partner data, not independently verified).
- **File:** `nature_nsga2_coolstock.py` line 79: `ULMA_STOCK = 500 # ulma_inventory_mock.json`
- **What it is:** The NSGA-II constraint `G1: modules ≤ 500` comes from a mock
  JSON file, not a verified ULMA inventory. Named `ulma_inventory_mock.json`
  in the comment.
- **For coolspend:** This constraint is irrelevant (coolspend is tree-placement,
  not scaffold). Drop entirely.
- **Severity:** LOW for coolspend (out of scope).

### 1.5 Girbau LAB / Almeria HDPE material quantities

- **Status:** DECLARED (partner/literature data, quantities are placeholders).
- **File:** `nature_nsga2_coolstock.py` lines 344–347:
  `"upcycled_material_kg": 0.0  # placeholder — Girbau LAB declared available`
- **For coolspend:** Not relevant to tree-placement. Drop.
- **Severity:** LOW for coolspend (out of scope).

### 1.6 TOPSIS weights — arbitrary, not elicited

- **Status:** Undocumented assumption. Author acknowledges in code comment
  (lines 370–380) that weights `(0.5, 0.3, 0.2)` are "not derived from a
  stakeholder survey, AHP pairwise comparison, or any documented elicitation."
- **File:** `nature_nsga2_coolstock.py` lines 361–408
- **For coolspend:** Port the TOPSIS method (canonical Hwang & Yoon 1981
  implementation is correct). Present weights as a jury-adjustable slider, not
  as a derived constant. The code comment itself says this.
- **Severity:** MEDIUM — low technical risk, high presentation risk if weights
  are framed as objective.

### 1.7 `utci_hours_above()` Tmrt derivation — SOLWEIG-style proxy

- **Status:** Approximation, not a simulation. Confidence rated MED in the code
  unless `x4_raval_uhi_validation.json` is present.
- **File:** `nature_metrics.py` lines 93–122
- **What it is:** `Tmrt ≈ Tdb + k * (GHI/1000) * (1 - shade_fraction)` where
  `k = 25.0 °C` is calibrated against Garcia-Nevado 2020 peak (58 °C). Used to
  estimate 8,760 hourly UTCI values without a CFD simulation.
- **For coolspend:** This is the cheapest pre-key offline UTCI estimate available.
  It is acceptable for the NSGA-II surrogate loop (same role as
  `delta_tmrt_surrogate`). Must be replaced or labelled when presenting to jury
  after the real API key arrives.
- **Severity:** MEDIUM — acceptable in surrogate loop; deceptive if quoted as
  Infrared SDK output.

### 1.8 `carbon_headroom_kgco2e()` — historical fabricated citation (now fixed upstream)

- **Status:** Fixed in parent (commit 4f3d2a9, 2026-05-17), but the fix history
  is important context. The original function claimed a "Pla Clima 300 kgCO2e/m²
  target" that does not exist in the document. A second attempted fix re-cited
  LETI Climate Emergency Design Guide (buildings only — wrong domain). Both were
  wrong. Current implementation drops the % budget framing and reports absolute
  kgCO2e + per-capita comparison.
- **File:** `nature_metrics.py` lines 441–534
- **For coolspend:** Port the corrected version only. Do NOT port the headroom/
  budget framing. The ÖKOBAUDAT steel coefficient (`oekobaudat_coolstock_materials.json`)
  must be present at the path `L1_INGEST_data/carbon/oekobaudat_coolstock_materials.json`
  or the function returns `LOW` confidence with a null value.
- **Severity:** LOW now that upstream is fixed — but flag if the JSON data file
  is not copied into the coolspend workspace.

### 1.9 `avoided_heat_mortality()` — Iungman 2023 column attribution inferred

- **Status:** MED confidence. Coefficient extracted from PDF page 29 by pattern
  inference; cross-check against supplementary appendix is open work per the
  code comment.
- **File:** `nature_metrics.py` lines 316–369
- **For coolspend:** HIGH-RISK for jury scrutiny — a mortality claim based on
  inferred PDF column attribution is easy to challenge. Either omit this metric
  or label it explicitly as policy-framing (city-wide extrapolation, not a
  per-plaza claim). The `honest_per_plaza_framing` key in the source JSON was
  built precisely for this framing guard.
- **Severity:** MEDIUM-HIGH — reputational risk if challenged.

---

## 2. Port Hazards

### 2.1 Duplicate files: `infrared_client_v2.py` vs `nature_infrared_client.py`

- **Issue:** Both files have byte-for-byte identical content (same docstring,
  same class definitions, same mock functions, same `INFRARED_BACKEND=live` dead
  stub). The names differ only in prefix convention.
- **Files:** `infrared_client_v2.py`, `nature_infrared_client.py`
- **Which to keep for coolspend:** Neither as a live-path client. If offline
  mock backend is needed during days 1–2 (pre-API key), keep **one file** renamed
  `mock_infrared_client.py`. Delete the other. Never import from either for
  production paths.
- **Risk:** Accidentally importing the wrong one. Both default to
  `INFRARED_BACKEND=mock`, so a missing env var silently returns fake data.
- **Severity:** MEDIUM — confusing at import time; high risk of silent mock
  data leaking into demo if the env var is not set before the demo run.

### 2.2 Parent-project coupling to leave behind

The following modules and layers exist in the NatureGooddest parent and must NOT
be ported to coolspend. Porting them would add dead weight and coupling with no
hackathon value.

| Layer / Module | Why Not Needed |
|---|---|
| `evaluator.py` + `HARD_BLOCK` gate | Full 27-pattern provenance gate; way beyond coolspend scope. Port only the data-labelling concept (confidence tiers). |
| `sparql_engine.py` + rdflib SPARQL | Pattern firing via OWL/TTL + in-memory RDF graph. coolspend has no pattern library. |
| `cookbooks/` YAML pattern library | 22-pattern cookbook, P01–P29 YAMLs. Not needed. |
| Neo4j / `populate_neo4j.py` | Optional scale-out store; not on any demo path. Adds install complexity for zero benefit. |
| `demo_app.py` Flask app (parent's) | Full multi-route Flask app serving NG3D viewer, `/run`, `/audit_json`, etc. Build a new minimal Flask/CLI for coolspend. |
| Three.js NG3D viewer (`/` route) | WebGL 3D scene for the parent's 3D canopy drag-editor. Out of scope. |
| `bcn_opendata.py` CKAN connector | Runtime Open Data BCN fetch. Only relevant if coolspend uses the same Barcelona site. |
| `generate_june_pitch_deck.py` | Slide generator that imports `evaluator`. Not needed. |
| `firing_trace.py` | Pattern firing trace utility. Not needed. |
| `cookbook_runner.py` | Cookbook execution orchestrator. Not needed. |
| `scripts/kg/` (OWL TTL emitter) | Knowledge-graph tooling. Not needed. |
| ML / permaculture "urban coherence" scorer | Explicitly ruled out in `HANDOFF.md` "what didn't work": `"Do not retry ML for the core optimizer."` |

### 2.3 Field-name mismatch: `x_m`/`y_m` vs `x_position_m`/`y_position_m`

- **Issue:** `nature_nsga2_coolstock.py` uses `x_m` and `y_m` as internal
  variable names (lines 13–14, 205, 291). The parent architecture doc notes that
  the YAML pattern P01 uses `x_position_m` and `y_position_m` as the canonical
  names (`VAR_ORDER` at line 48). The parent added fallback handling in JS
  (commit `d0c181c`, 2026-05-16) but a third name variant would proliferate the
  problem.
- **Files:** `nature_nsga2_coolstock.py` (uses `x_m`/`y_m` internally),
  `cookbooks/urban-cooling/patterns/P01_sun_path_canopy.yaml` (uses `x_position_m`).
- **For coolspend:** Choose ONE naming convention at the start and use it
  everywhere. Recommended: `x_m`/`y_m` (shorter, used in the Python core). Do
  not import the P01 YAML — `load_pattern_bounds()` at line 41 will fail unless
  `cookbooks/` is also ported (it should not be). Use the `FALLBACK_XL`/`FALLBACK_XU`
  arrays directly (lines 50–51).
- **Severity:** MEDIUM — silent wrong bounds if YAML load fails and fallback
  silently activates without log visibility.

### 2.4 Coordinate-system footgun: EPSG:4326 vs plaza-local metres

- **Issue:** Three coordinate systems coexist in the parent (per `nature_architecture.md`
  § Coordinate systems):
  1. EPSG:4326 (WGS84 lat/lon) — raw OSM / GBIF inputs
  2. Plaza-local metres — NSGA-II `x_m`/`y_m` with plaza SW corner at origin
  3. EPSG:25831 (UTM 31N) — Spanish cadastre headers only, not used at runtime
  Additionally, the 3D scene's plaza is centred at `(0, 0)` with SW corner at
  `(-30, -30)`, so NSGA-II `(x_m=30, y_m=5)` maps to 3D `(0, -25)` — a
  non-obvious offset documented only in `drawPlanView()`.
- **Files:** `nature_nsga2_coolstock.py` (plaza-local), `nature_metrics.py`
  (`plaza_shaded_fraction()` line 560–578 uses a second local origin with
  `SITE_HALF = 30` and a `cz = cfg.y_m - SITE_HALF + w/2` calculation).
- **For coolspend:** Define ONE coordinate frame at project start. The cleanest
  choice for a tree optimizer is projected metres (e.g. UTM 31N or a local
  metre grid). Whatever you choose, document the origin explicitly in code
  constants and test that OSM geometries and optimizer outputs share the same
  frame before the first Infrared API call.
- **Severity:** HIGH — a coordinate mismatch produces plausible-looking but
  wrong geometry in the Infrared API payload. Silent failure: the API accepts
  any polygon and returns valid-looking UTCI numbers that are spatially wrong.

### 2.5 `load_pattern_bounds()` YAML dependency

- **Issue:** `COOLSTOCKProblem.__init__()` calls `load_pattern_bounds(P01_YAML)`
  at line 201. `P01_YAML` resolves to `cookbooks/urban-cooling/patterns/P01_sun_path_canopy.yaml`
  relative to the source file's parent (line 38). If coolspend does not copy
  the cookbooks directory, this silently falls back to `FALLBACK_XL/FALLBACK_XU`
  with only a `print()` warning (no exception raised, no flag in output JSON).
- **File:** `nature_nsga2_coolstock.py` lines 38–63
- **Mitigation:** Remove the YAML load entirely in the ported version. Hardcode
  the bounds for coolspend's tree-placement variables directly in the Problem
  class. This also removes the `yaml` import dependency.
- **Severity:** LOW severity (fallback is correct for hackathon bounds) but
  HIGH confusion risk — developers may not notice the fallback was triggered.

---

## 3. Hackathon-Specific Risks

### 3.1 Simulation budget: NSGA-II × 10k evals cannot call live Infrared

- **Issue:** NSGA-II with `pop_size=100, n_gen=100` produces 10,000 evaluations
  (100 × 100, accounting for duplicates slightly fewer). The Infrared SDK performs
  CFD-level UTCI computation, which takes seconds to tens of seconds per call.
  At even 5 s per call, 10k evaluations = ~14 hours. The hackathon has 3 days
  total, with the API key not available until May 27.
- **Reference code check:** The parent project DOES follow the correct pattern.
  `nature_nsga2_coolstock.py`'s `delta_tmrt_surrogate()` is the hot path inside
  `_evaluate()`. The Infrared SDK is called ONLY in
  `scripts/sim/run_infrared_utci_angels.py` (separate, offline script) for the
  top-3 validation. The audit record labels results `"demo_version": "v1-surrogate"`.
  coolspend MUST replicate this two-phase pattern:
  - Phase A: full NSGA-II run on analytical surrogate (Ladybug UTCI proxy or
    SOLWEIG-style proxy from `nature_metrics.py`) — no live API calls
  - Phase B: post-optimisation, call Infrared SDK for top-3 configs only (~3 calls)
- **Mitigation:** Implement a `SimBudget` guard at the top of `_evaluate()` that
  raises an error if called with `backend=live`. The live path must be a separate
  function `validate_top3_with_infrared()` called explicitly after NSGA-II
  terminates.
- **Severity:** CRITICAL — if the live API is wired into `_evaluate()` the run
  will either time out or exhaust any API quota within minutes.

### 3.2 API key not available until May 27 — offline test coverage

- **Issue:** The `INFRARED_API_KEY` is not issued until the hackathon opens
  (May 27). Any code path that imports or calls `infrared_sdk.InfraredClient`
  directly will fail before that date. All days-1-2 development and testing must
  run against the mock backend.
- **Affected files:** Any coolspend module that imports from `infrared_sdk`.
  The parent's `infrared_client_v2.py` / `nature_infrared_client.py` mocks provide
  a usable contract (`simulate_tmrt()`, `simulate_utci()`, `simulate_wind()` with
  `INFRARED_BACKEND=mock|cached`).
- **Mitigation:**
  1. Gate all SDK imports behind a try/except or `INFRARED_AVAILABLE` flag read
     from the environment: `INFRARED_AVAILABLE = os.getenv("INFRARED_API_KEY") is not None`.
  2. Write all integration tests against the mock backend so the full pipeline
     can be validated before May 27.
  3. On May 27 morning, run `scripts/validate_infrared_connection.py` (to be
     created) that calls the real API with a single test geometry and asserts
     the response shape matches the mock contract.
- **Severity:** HIGH — unprotected SDK import breaks `pytest` and every CI run
  before May 27.

### 3.3 Plan V2 ends at CLI — no web demo (presentation risk)

- **Issue:** `HANDOFF.md` describes a Plan V2 that delivers results as CLI
  output (CSV + JSON + PNG pareto plot). The parent project's demo was a full
  Flask app with an interactive Three.js viewer. At a hackathon judged on
  presentation, a CLI output is a significant disadvantage versus teams with
  interactive demos.
- **Evidence:** `nature_nsga2_coolstock.py`'s `save_outputs()` (lines 499–546)
  saves `pareto_front.png`, `top3_configurations.csv`, `top3_configurations.json`,
  and `audit_record.json` to `L1_INGEST_data/nsga2_output/`. There is no web
  server in the port plan.
- **Mitigation options (in order of build effort):**
  1. Minimal: serve the PNG + JSON via a 30-line Flask route with an HTML wrapper.
     The pareto PNG is already generated — just serve it as `<img>`.
  2. Better: a single-page Jinja2 template that renders the top-3 configs as
     cards with the UTCI values and a site plan SVG (port `drawPlanView()` from
     the parent's `demo_app.py`).
  3. Do NOT attempt to port the full Three.js NG3D viewer — 3D scene setup alone
     took the parent project multiple sessions.
- **Address in:** Day 3 (May 29/30), after NSGA-II + Infrared validation are
  working.
- **Severity:** MEDIUM-HIGH — does not affect correctness but directly affects
  jury scoring. Most hackathon judges will not read JSON files.

### 3.4 Scope creep — parent project's 6-layer architecture

- **Issue:** The NatureGooddest parent has 6 layers (L1–L6): INGEST, COOKBOOK,
  GENERATE, SIMULATE, DEFEND, MONITOR. The coolspend port is intended to be
  layers L3 (NSGA-II) + L4 (Infrared) + a lightweight L1 (OSM geometry) only.
  Layers L2 (SPARQL/cookbook), L5 (evaluator `HARD_BLOCK`), and L6 (MOCKS.md
  audit ledger) are explicitly out of scope per the HANDOFF and the scope decision
  that rejected ML/permaculture.
- **Specific out-of-scope items confirmed by HANDOFF.md "what didn't work":**
  - ML-based "urban coherence" scorer → ruled out
  - Full permaculture guild logic → ruled out in favour of rule-based scoring
  - `evaluator.py` provenance gate → too complex for 3-day build
- **Risk trigger:** The `CONCEPT_REPORT.md` §3.3 still describes a "Rule-Based
  Permaculture Engine" with minimum spacing + diversity index. These are
  lightweight fitness penalties, not the full cookbook — but the language invites
  scope expansion. If the ecology rule-set grows beyond 2–3 simple penalties,
  it will consume day-2 time needed for Infrared integration.
- **Mitigation:** Cap the ecology/permaculture rules at exactly two penalties:
  (1) minimum tree spacing (collision detection via `shapely`), and (2) a simple
  species-diversity bonus (at most a lookup table). If either penalty takes
  more than 2 hours to implement, cut it and use a single-species model.
- **Severity:** MEDIUM — the risk is time loss, not correctness.

### 3.5 NSGA-II run time on hackathon hardware

- **Issue:** The parent project clocks NSGA-II at ~30 s on a 2024 laptop
  (`nature_architecture.md` § Performance characteristics). That is for 100 pop
  × 100 gen with a pure-Python analytical surrogate. For coolspend, if the
  SOLWEIG-style `_derive_hourly_tmrt()` from `nature_metrics.py` (8,760-iteration
  inner loop) is placed inside `_evaluate()`, each evaluation costs ~0.1 s, making
  10k evaluations ~17 minutes — too slow for an interactive demo.
- **File:** `nature_metrics.py` lines 93–122 (`_derive_hourly_tmrt`)
- **Mitigation:**
  1. Pre-compute the baseline UTCI array once (as `nature_metrics.py` does via
     `_EPW_CACHE`) and pass it to `_evaluate()` as a read-only array.
  2. Keep the NSGA-II surrogate as a simple analytical function (the
     `delta_tmrt_surrogate` pattern) and reserve `utci_hours_above()` for
     post-selection reporting only.
  3. Reduce pop/gen for demo runs: `pop_size=50, n_gen=50` gives the same
     qualitative Pareto shape in ~8 s and is sufficient for a live demo.
- **Severity:** MEDIUM — missed only if UTCI loop is placed inside the hot path.

---

## 4. Test Coverage Gaps

### 4.1 No tests exist in the hackathon workspace

- **What's not tested:** The entire coolspend codebase (no files yet).
- **Files:** None yet — workspace is pre-implementation.
- **Risk:** With a 3-day build, untested code at the boundary between NSGA-II
  outputs and Infrared API inputs is the highest risk point. A coordinate or
  field-name error in the geometry payload will produce plausible but spatially
  wrong UTCI results with no warning.
- **Priority:** HIGH
- **Minimum recommended coverage:**
  1. `test_coordinate_frame.py` — assert that a known plaza polygon in OSM
     coordinates converts to the correct local-metre frame before being passed
     to the Infrared SDK.
  2. `test_nsga2_surrogate.py` — smoke-test that `COOLSTOCKProblem._evaluate()`
     returns finite, bounded values for edge-case inputs (zero width, max tilt).
  3. `test_mock_backend.py` — assert that mock infrared fields have the expected
     `metadata.disclaimer` and are never passed to `save_outputs()` without
     the surrogate label.

### 4.2 `delta_tmrt_surrogate()` post-fix not regression-tested

- **What's not tested:** The porosity-squared-bug fix (audit C10, 2026-05-20)
  has no regression test in the parent. If coolspend ports this function and
  someone changes the `shade_fraction` calculation in the caller, the bug can
  silently re-appear.
- **Files:** `nature_nsga2_coolstock.py` lines 106–155
- **Risk:** Silent ΔTmrt understatement of ~12–20% at typical porosity values.
- **Priority:** HIGH
- **Fix:** Add a `test_delta_tmrt_no_double_porosity()` assertion:
  `assert abs(delta_tmrt_surrogate(0.85, 15.0, 0, 3.75) - delta_tmrt_surrogate(0.88, 12.0, 0, 3.75)) < 3.0`
  and a direct check that `delta_tmrt_surrogate(shade_fraction=0.85, porosity_pct=15.0, ...)
  != delta_tmrt_surrogate(shade_fraction=0.85**2, porosity_pct=15.0, ...)`.

---

## 5. Dependencies at Risk

### 5.1 `ladybug` / `ladybug_comfort` — heavy install

- **Risk:** `nature_metrics.py` line 34 imports `from ladybug_comfort.utci import
  universal_thermal_climate_index` and `from ladybug.epw import EPW`. The
  `ladybug-rhino` ecosystem is large and has platform-specific wheels. On a clean
  hackathon laptop it may fail to install or conflict with the `infrared_sdk`
  environment.
- **Impact:** `utci_hours_above()`, `utci_hourly_histogram()`, and
  `avoided_heat_mortality()` all depend on this import. If unavailable, M1
  metric is broken.
- **Migration plan:** `ladybug_comfort.utci.universal_thermal_climate_index` is
  a pure-Python function. For coolspend, consider copying just the UTCI equation
  (Bröde 2012, freely published) as a standalone function rather than taking
  the full `ladybug` dependency. This removes ~200 MB of install weight.
- **Severity:** MEDIUM — risk is environment setup time lost on day 1.

### 5.2 `pymoo` version pin

- **Risk:** The parent pins `pymoo 0.6.1` (visible in `nature_nsga2_coolstock.py`
  line 529 JSON metadata). The `NSGA2`, `SBX`, `PM`, `FloatRandomSampling`
  import paths changed between pymoo 0.5.x and 0.6.x. If a different version
  is installed, imports fail silently or with opaque errors.
- **Files:** `nature_nsga2_coolstock.py` lines 65–70
- **Migration plan:** Pin `pymoo==0.6.1` in `requirements.txt`. Test imports on
  day 1 before writing any Problem subclass.
- **Severity:** LOW — straightforward to fix if caught early.

### 5.3 `shapely` — required for `plaza_shaded_fraction()`

- **Risk:** `nature_metrics.py` line 555 imports `from shapely.geometry import
  Polygon, MultiPoint` inside the function body (lazy import). If `shapely` is
  not installed, this silently returns `{"value": 0.0, "confidence": "LOW"}` due
  to the `if not cfg: return ...` guard — the actual `ImportError` is not caught
  and will raise at runtime.
- **File:** `nature_metrics.py` lines 553–619
- **Migration plan:** Add `shapely` to `requirements.txt`. Add an explicit try/
  except ImportError around the lazy import with a clear error message.
- **Severity:** LOW — easy fix, but the silent fallback to 0.0 with LOW confidence
  masks the missing dependency.

---

## 6. Fragile Areas

### 6.1 Dual-path Infrared client state

- **Issue:** The `_dispatch()` function in both `infrared_client_v2.py` and
  `nature_infrared_client.py` writes cached responses to `cache/infrared/{hash}.json`
  on every mock call (lines 346–347). If the cache directory is pre-populated with
  stale mock data from the parent project and `INFRARED_BACKEND=cached` is set
  by accident, the demo will serve stale data silently.
- **Safe modification:** Always start with `INFRARED_BACKEND=mock` (the default)
  during development. Only switch to `cached` intentionally after verifying the
  cache was generated by the current version of the mock.
- **Severity:** LOW — deterministic hash keying means geometry changes bust the
  cache, but the risk remains for identical geometry inputs.

### 6.2 NSGA-II seed pinning vs. demo reproducibility

- **Issue:** `run_optimisation(seed=42)` produces a deterministic Pareto front.
  This is intentional and correct for a reproducible demo. However, if the problem
  bounds change (e.g. different site, different variable ranges) the seed-42 result
  will be a different Pareto front — it will not crash, but the top-3 configs will
  change, invalidating any hardcoded demo talking points built around the old
  front.
- **File:** `nature_nsga2_coolstock.py` line 252
- **Safe modification:** Treat the seed as a demo-time constant. Run a fresh
  `n_gen=50, pop_size=50` on the first day with the actual coolspend bounds, then
  lock in the top-3 outputs as reference values for the demo script.
- **Severity:** LOW.

---

*Concerns audit: 2026-05-21*
