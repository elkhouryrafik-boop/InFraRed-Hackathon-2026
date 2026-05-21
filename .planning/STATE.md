---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
stopped_at: Roadmap created; REQUIREMENTS.md traceability updated; ready to run /gsd-plan-phase 1
last_updated: "2026-05-21T00:07:58.212Z"
last_activity: 2026-05-21 — Roadmap created; codebase concerns, architecture, and structure audited; port verdicts confirmed
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 3
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-21)

**Core value:** Given a polygon and a budget, output a defensible ranked tree-planting allocation maximizing UTCI relief per euro — proved with a real Infrared UTCI before/after on the top picks
**Current focus:** Phase 1 — Foundation & SDK Boundary

## Current Position

Phase: 1 of 4 (Foundation & SDK Boundary)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-05-21 — Roadmap created; codebase concerns, architecture, and structure audited; port verdicts confirmed

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Pre-build: Two identical Infrared mock files (infrared_client_v2.py / nature_infrared_client.py) must be collapsed to a single sdk_client.py — do not import either for live paths
- Pre-build: surrogate `delta_tmrt_surrogate()` porosity-squared bug fixed upstream (2026-05-20, audit C10) — port the fixed version only; add regression test
- Pre-build: F3 corridor objective degenerates under heritage-buffer y-clamp — ship as 2-objective (thermal + ecological) per PROJECT.md decision
- Pre-build: YAML P01 bounds loader must be replaced with hardcoded fallback bounds in optimizer.py — do not port cookbooks/ directory
- Pre-build: `INFRARED_BACKEND=live` must be unreachable from inside NSGA-II `_evaluate()` — SimBudget guard is a hard Phase 1 requirement
- Pre-build: ladybug/ladybug-rhino is a heavy install risk; consider inlining the UTCI equation (Bröde 2012) instead of taking the full dependency

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

Last session: 2026-05-21
Stopped at: Roadmap created; REQUIREMENTS.md traceability updated; ready to run /gsd-plan-phase 1
Resume file: None

**Planned Phase:** 1 (Foundation & SDK Boundary) — 3 plans — 2026-05-21T00:07:58.203Z
