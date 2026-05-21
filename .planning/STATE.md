---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: — Market-Ready CoolSpend
status: executing
stopped_at: "Completed 06-03: editable per-city cost table via Gradio inputs + live KPI recompute (COST-04)"
last_updated: "2026-05-21T19:00:00.000Z"
last_activity: 2026-05-21 -- Phase --phase execution started
progress:
  total_phases: 9
  completed_phases: 5
  total_plans: 21
  completed_plans: 21
  percent: 95
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-21)

**Core value:** Given a polygon and a budget, output a defensible ranked tree-planting allocation maximizing UTCI relief per euro — proved with a real Infrared UTCI before/after on the top picks
**Current focus:** Phase --phase — 6

## Current Position

Phase: --phase (6) — EXECUTING
Plan: 1 of --name
Status: Executing Phase --phase
Last activity: 2026-05-21 -- Phase --phase execution started

Progress: [████████░░] 78%

## Performance Metrics

**Velocity:**

- Total plans completed: 18
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 3 | - | - |
| 2 | 5 | - | - |
| 3 | 3 | - | - |
| 4 | 2 | - | - |
| 5 | 5 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01-foundation-sdk-boundary P01-02 | 5m | 3 tasks | 4 files |
| Phase 01-foundation-sdk-boundary P01-03 | 10m | 2 tasks | 3 files |
| Phase 02-optimizer-core P02-01 | 3m | 1 tasks | 3 files |
| Phase 02-optimizer-core P02-02 | 5m | 1 tasks | 3 files |
| Phase 02-optimizer-core P02-03 | 15m | 2 tasks | 3 files |
| Phase 02-optimizer-core P02-04 | 25m | 3 tasks | 2 files |
| Phase 02-optimizer-core P02-05 | 25m | 3 tasks | 6 files |
| Phase 03-web-app-decision-ui P03-01 | 5m | 2 tasks | 4 files |
| Phase 03-web-app-decision-ui P03-02 | 4m | 2 tasks | 2 files |
| Phase 03-web-app-decision-ui P03-03 | 8m | 2 tasks | 3 files |
| Phase 04-ship P04-01 | 15m | 3 tasks | 2 files |
| Phase 04-ship P04-02 | 3m | 3 tasks | 3 files |
| Phase 05-surrogate-ground-truth-honesty-reset P01 | 15m | 2 tasks | 4 files |
| Phase 05-surrogate-ground-truth-honesty-reset P02 | 25m | 2 tasks | 2 files |
| Phase 05-surrogate-ground-truth-honesty-reset P03 | 25m | 2 tasks | 2 files |
| Phase 05 P04 | 5m | 2 tasks | 5 files |
| Phase 05-surrogate-ground-truth-honesty-reset P05 | 8m | 2 tasks | 7 files |
| Phase 06-cost-model-credibility P01 | 4 | 3 tasks | 3 files |
| Phase 06-cost-model-credibility P02 | 20m | 2 tasks | 2 files |
| Phase 06-cost-model-credibility P03 | 20m | 3 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v2.0 roadmap: Validation (VALID-* + HONEST-*) is the keystone Phase 5 — if surrogate rankings don't hold against measured UTCI, the rest of v2.0 is invalid; everything downstream of it
- v2.0 roadmap: HONEST-* relabeling folded into Phase 5 (keystone) — low-effort doc edits that gate external credibility and belong with the validation reset
- v2.0 roadmap: Phases 6 (cost) and 7 (geometry) both depend only on Phase 5 and can run in parallel; Phase 8 (multi-intervention + triage) requires both
- v2.0 roadmap: Phase 9 (export/grant/audit) is the go-to-market/defensibility layer — last, after the product pivot is real
- 01-01: mock backend returns scalar UTCI delta (not field grid) — coolspend needs a scalar, not NatureGooddest's 24x24 grid
- 01-01: cached miss raises FileNotFoundError, no silent fallthrough — CONCERNS 6.1 stale-cache risk mitigated
- 01-01: SimBudget RuntimeError guards NSGA-II hot path from live Infrared calls
- Pre-build: Two identical Infrared mock files (infrared_client_v2.py / nature_infrared_client.py) must be collapsed to a single sdk_client.py — do not import either for live paths
- Pre-build: surrogate `delta_tmrt_surrogate()` porosity-squared bug fixed upstream (2026-05-20, audit C10) — port the fixed version only; add regression test
- Pre-build: F3 corridor objective degenerates under heritage-buffer y-clamp — ship as 2-objective (thermal + ecological) per PROJECT.md decision
- Pre-build: YAML P01 bounds loader must be replaced with hardcoded fallback bounds in optimizer.py — do not port cookbooks/ directory
- Pre-build: `INFRARED_BACKEND=live` must be unreachable from inside NSGA-II `_evaluate()` — SimBudget guard is a hard Phase 1 requirement
- Pre-build: ladybug/ladybug-rhino is a heavy install risk; consider inlining the UTCI equation (Bröde 2012) instead of taking the full dependency
- equirectangular + cos-latitude correction for CRS conversion — accurate within +/-200m of plaza centroid, no geodesy dep
- STREET_BUFFER_M=1.5m rejection radius around street centerlines — prevents tree placement on pavement edge
- load_site() caches by resolved path in _SITE_CACHE — avoids repeated disk reads in NSGA-II hot path
- 01-03: DECLARED assumptions CAPEX_PER_TREE_EUR=350/OPEX_PER_TREE_YEAR_EUR=35/OPEX_HORIZON_YEARS=10 tagged REQUIRES_VERIFICATION — no fabricated citation (REPLACED in Phase 6 COST-03)
- 01-03: Non-positive delta returns value=None (T-01-10 mitigated) — zero-delta guard in cost_per_utci_degree
- RULES-01 min-spacing penalty uses linear violation depth (min_spacing_m - dist) / min_spacing_m — smooth gradient for NSGA-II
- RULES-02 Shannon index normalised by ln(n_distinct) — monoculture=0.0, balanced N-species=1.0 exactly
- Pollinator corridor objective explicitly excluded (CONCERNS 1.2) — documented in module docstring
- MIN_SPACING_M=4.0 and SPECIES_PALETTE tagged SOURCE: DECLARED + REQUIRES_VERIFICATION — no fabricated citation
- 02-02: delta_tmrt_surrogate uses math (not numpy) to keep spatial_engine numpy-light for NSGA-II hot path
- 02-02: porosity_pct retained in signature for call-site compatibility but intentionally unused in body (CONCERNS 4.2)
- 02-02: thermal_relief site-coverage capped at 0.90 — prevents unrealistic 100% canopy scenario
- 02-02: TREE_SHADE_FRACTION=0.80 and TREE_CANOPY_RADIUS_M=3.0 tagged DECLARED/REQUIRES_VERIFICATION — no fabricated citation
- 02-03: lazy import of infrared_sdk inside _live_utci() only — module importable offline without SDK installed
- 02-03: INFRARED_API_KEY validated present before SDK usage; never logged or embedded in any string
- 02-03: live result written to CACHE_DIR for INFRARED_BACKEND=cached offline replay
- 02-03: AnalysesName.utci member name left as TODO for May-27 SDK confirmation (one-line change)
- 02-04: N_TREES=12 fixed chromosome length (24 vars); decode() maps to tree config with is_valid_location gating
- 02-04: validate_top3_with_infrared: baseline called once (no budget record); 3 budget slots for interventions
- 02-04: select_top3 deduplication via utopia-point sorted fallback ensures 3 distinct indices always
- 02-05: primary ranking by EUR/degC (not TOPSIS closeness) — cheapest-per-degree always rank-1 (DEC-01 defensibility)
- 02-05: TOPSIS weights (0.6/0.4) adjustable developer judgment, NOT stakeholder-elicited (CONCERNS 1.6) — REPLACED in Phase 9 AUDIT-02
- 02-05: disclaimer injected by save_outputs if absent — T-02-15 never dependent on caller compliance
- 02-05: plot_pareto() wrapped — JSON pipeline never blocked by matplotlib failure (T-02-18)
- 03-01: sdk_client logger level temporarily set to INFO for call-log capture (root logger at WARNING suppresses INFO by default)
- 03-01: parse_site_geojson raises ValueError on invalid input; run_decision catches and sets error field (clean separation)
- 03-01: render_before_after accepts before_after dict with chosen_validated_utci_c and headline_delta_utci_c matching run_decision contract
- 03-02: build_demo() factory separates Blocks construction from launch — tests import without side effects
- 03-02: gradio 4.44.1 requires huggingface_hub <1.0 (HfFolder removed in 1.x) — pinned to 0.36.2
- 03-02: test_headless_launch_smoke skips on httpx.ConnectError (Gradio 4.x health-check ping fails on Windows with server_port=0)
- 03-03: huggingface_hub==0.36.2 pin required for gradio 4.44.1 (HfFolder removed in 1.x)
- 03-03: app_file: coolspend/app.py in HF Spaces header — no root shim needed
- D-06: pyproj UTM-31N (EPSG:32631) with always_xy=True, per-site SW UTM corner origin from polygon bbox, [0,width]x[0,depth] local frame preserved
- D-07: assert_crs_roundtrip measures UTM metres euclidean distance, raises CRSConsistencyError >= 1m, wired in _live_utci before InfraredClient call — fail-closed
- D-08/D-09/D-10: HOURS_PER_DEGC_REF=200.0 (Barcelona EPW strong heat stress mean UTCI excess ~3°C; 600h/yr / 3°C = 200h/°C); cost_per_utci_degree now routes through utci_hours_above — never raw Tmrt; reports both EUR/degC and EUR/UTCI-hour; always interval [lo,hi] with PRE_CALIBRATION_BAND_C=4.0 until Plan 05-03 RMSE available
- D-12: naive_baseline_config/_build_naive_baseline/improvement_vs_naive_pct deleted from optimizer.py — mock-vs-mock overclaim removed
- D-13: surrogate ceiling re-anchored to Schrodi 2023 (arXiv:2310.05691, venue PENDING, ML magnitude only) + Rahman 2022 (DOI PENDING); Garcia-Nevado 2020 demoted to surface-temp analogue; 12C cap REQUIRES_VERIFICATION preserved
- D-11/D-15: app.py table shows EUR/degC KPI as [lo,hi] interval + EUR/UTCI-hr secondary unit + Band source label, all read from cost_per_utci_degree dict; never a bare point estimate
- D-13 docs: MOCKS.md re-anchored to Schrodi 2023 (arXiv:2310.05691, venue PENDING) + Rahman 2022 (DOI PENDING); Garcia-Nevado 2020 demoted to surface-temp analogue; naive row tombstoned REMOVED; no fabricated DOIs
- D-14: out-of-scope exclusions list (subsurface utilities, soil volume, irrigation/water demand, sightlines, solar access, root-vs-pavement) added to README.md and CONCEPT_REPORT.md with geometric feasibility framing
- D-15 backward-compat: CAPEX_PER_TREE_EUR/OPEX_PER_TREE_YEAR_EUR derived from DEFAULT_COST_TABLE (single source of truth — no dual definition)
- OPEX_HORIZON_YEARS changed 10->40 yr per D-09 (urban sealed-site functional lifespan)
- DEFAULT_COST_TABLE: CapEx=3000 EUR/tree (5 itemized lines), OpEx=180 EUR/tree/yr; label='illustrative European mid-range — verify locally'
- 06-02: cost_per_utci_degree routes denominator through discounted_lifetime_degc() (25yr linear ramp, 3.5% discount, 40yr horizon) and numerator through discounted_total_cost() (PV of OpEx); growth_discount=None default preserves backward compat; optimizer total_cost() path unchanged
- 06-02: new param-echo keys (discount_rate, ramp_years, horizon_years, growth_note) additive — no Phase 5 key removed from result dict
- 06-03: load_cost_table/cost_table_from_dict fail-open to DEFAULT_* on missing/invalid JSON; on_submit receives cost+gd inputs as *varargs; Stage 4b in _run_pipeline recomputes KPI post-topsis_rank when non-None; optimizer total_cost() path unchanged

### Pending Todos

None yet.

### Blockers/Concerns

- **Surrogate validity (v2.0 EXISTENTIAL):** The headline KPI is currently assumption ÷ assumption. Until the ΔTmrt surrogate is ground-truthed against real Infrared UTCI across varied configs (Phase 5 / VALID-01), the rankings — the whole product — may be wrong. Phase 5 must answer this before any downstream phase is worth building.
- **Tmrt ≠ UTCI (KPI unit substitution):** Optimizer maximizes ΔTmrt (capped 12°C) but the product sells "UTCI relief"; a 12°C Tmrt drop ≈ only ~3–5°C UTCI. Fix is ~80% built (route through `nature_metrics.py::utci_hours_above()`) — Phase 5 / VALID-02.
- **Cost model ~10× too low + unsourced:** €350 CapEx / €35/yr OpEx vs NYC ~$3,300 fully-loaded CapEx + Boston ~$900/tree/yr. A 10×-low denominator can invert the trees-vs-alternatives ranking — the exact error an auditor catches. Phase 6 / COST-03.
- **Coordinate system footgun (HIGH):** Three CRSes coexist. Must define and test ONE frame (UTM 31N) end-to-end before the first Infrared API call or UTCI results will be spatially wrong with no warning. Phase 5 / VALID-05.
- **Surrogate citation mismatch (honesty):** `MAX_TMRT_REDUCTION=12°C` is unsourced; Garcia-Nevado 2020 measures surface temp not Tmrt at 1.1m. Re-anchor to Schrodi 2023 / Rahman 2022; disclose in MOCKS + JSON output. Phase 5 / HONEST-02.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| post-v2.0 | Water-feature & shade-structure interventions (beyond trees + cool roofs) | Deferred | v2.0 roadmap |
| post-v2.0 | Per-species cooling coefficients, soil-volume constraint, irrigation objective | Deferred | v2.0 roadmap |
| post-v2.0 | SaaS hardening (multi-tenancy, auth, rate limiting) | Deferred | v2.0 roadmap |
| post-v2.0 | Pricing & packaging; 5+ Chief-Heat-Officer discovery interviews | Deferred | v2.0 roadmap |
| post-v2.0 | Live re-run from user edit | Deferred | Init |
| post-v2.0 | Pollinator 3rd objective (degenerate) | Deferred | Init |

## Session Continuity

Last session: 2026-05-21T19:00:00.000Z
Stopped at: Completed 06-03: editable per-city cost table via Gradio inputs + live KPI recompute (COST-04)
Resume file: None

**Planned Phase:** 6 (Cost-Model Credibility) — 3 plans — 2026-05-21T17:42:27.847Z
