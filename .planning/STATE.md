---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: ready_to_plan
stopped_at: Completed 02-05-PLAN.md — decision artifact, topsis_rank, save_outputs, main.py CLI, 88 tests green, DEC-01+DEC-02 satisfied
last_updated: "2026-05-21T10:00:00.000Z"
last_activity: 2026-05-21
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 8
  completed_plans: 8
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-21)

**Core value:** Given a polygon and a budget, output a defensible ranked tree-planting allocation maximizing UTCI relief per euro — proved with a real Infrared UTCI before/after on the top picks
**Current focus:** Phase --phase — 1

## Current Position

Phase: 03
Plan: Not started
Status: Ready to plan
Last activity: 2026-05-21

Progress: [██████████] 100% (Phase 02 complete)

## Performance Metrics

**Velocity:**

- Total plans completed: 8
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 3 | - | - |
| 2 | 5 | - | - |

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

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

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
- 01-03: DECLARED assumptions CAPEX_PER_TREE_EUR=350/OPEX_PER_TREE_YEAR_EUR=35/OPEX_HORIZON_YEARS=10 tagged REQUIRES_VERIFICATION — no fabricated citation
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
- 02-05: TOPSIS weights (0.6/0.4) adjustable developer judgment, NOT stakeholder-elicited (CONCERNS 1.6)
- 02-05: disclaimer injected by save_outputs if absent — T-02-15 never dependent on caller compliance
- 02-05: plot_pareto() wrapped — JSON pipeline never blocked by matplotlib failure (T-02-18)

### Pending Todos

None yet.

### Blockers/Concerns

- **API key (May 27):** `INFRARED_API_KEY` not issued until hackathon kickoff May 27 17:00 CET. All Phase 1 work and Phase 2 NSGA-II/rules work must run offline. Live Top-3 validation (OPT-03) and live app demo (APP-02) blocked until key arrives.
- **Coordinate system footgun (HIGH):** Three CRSes coexist. Must define and test ONE frame before the first Infrared API call or UTCI results will be spatially wrong with no warning.
- **Surrogate citation mismatch (honesty):** `MAX_TMRT_REDUCTION=12°C` is unsourced; Garcia-Nevado 2020 measures surface temp not Tmrt at 1.1m. Must be disclosed in MOCKS ledger and JSON output — not hidden.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v2 | Cool-roof / shade-structure interventions | Deferred | Init |
| v2 | Multi-site district triage ranking | Deferred | Init |
| v2 | Live re-run from user edit | Deferred | Init |
| v2 | Pollinator 3rd objective (degenerate) | Deferred | Init |

## Session Continuity

Last session: 2026-05-21T10:00:00.000Z
Stopped at: Completed 02-05-PLAN.md — decision artifact, topsis_rank, save_outputs, main.py CLI, 88 tests green, DEC-01+DEC-02 satisfied
Resume file: None

**Planned Phase:** 1 (Foundation & SDK Boundary) — 3 plans — 2026-05-21T00:07:58.203Z
