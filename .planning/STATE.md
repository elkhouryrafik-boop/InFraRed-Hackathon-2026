---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: — Market-Ready CoolSpend
status: planning
stopped_at: Phase 5 context gathered
last_updated: "2026-05-21T15:55:29.974Z"
last_activity: 2026-05-21 — v2.0 roadmap created (Phases 5–9, 25 requirements mapped)
progress:
  total_phases: 9
  completed_phases: 4
  total_plans: 13
  completed_plans: 13
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-21)

**Core value:** Given a polygon and a budget, output a defensible ranked tree-planting allocation maximizing UTCI relief per euro — proved with a real Infrared UTCI before/after on the top picks
**Current focus:** Milestone v2.0 — Market-Ready CoolSpend (roadmap complete → plan Phase 5, the validation keystone)

## Current Position

Phase: 5 — Surrogate Ground-Truth & Honesty Reset (not started)
Plan: —
Status: Roadmap complete; ready to plan Phase 5
Last activity: 2026-05-21 — v2.0 roadmap created (Phases 5–9, 25 requirements mapped)

Progress: v1.0 complete (4 phases / 13 plans, hackathon submission shipped). v2.0 roadmapped into 5 phases (5–9). Phase 5 is the existential keystone — surrogate ground-truth + honesty reset — and gates the entire milestone. Execution order: 5 → {6, 7} → 8 → 9.

## Performance Metrics

**Velocity:**

- Total plans completed: 13
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 3 | - | - |
| 2 | 5 | - | - |
| 3 | 3 | - | - |
| 4 | 2 | - | - |

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

Last session: --stopped-at
Stopped at: Phase 5 context gathered
Resume file: --resume-file

**Planned Phase:** 5 (Surrogate Ground-Truth & Honesty Reset) — keystone — next: `/gsd-plan-phase 5`
