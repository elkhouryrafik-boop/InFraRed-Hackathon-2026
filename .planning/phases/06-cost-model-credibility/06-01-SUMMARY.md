---
phase: 06-cost-model-credibility
plan: "01"
subsystem: cost-model
tags: [cost-model, dataclass, lifecycle-cost, CostTable, CostLine, DECLARED, PENDING, audit-trail, backward-compat]

# Dependency graph
requires:
  - phase: 05-surrogate-ground-truth-honesty-reset
    provides: "cost_per_utci_degree dual-unit KPI + interval [lo,hi] + HOURS_PER_DEGC_REF contract"
provides:
  - "CostLine frozen dataclass with key/label/value/unit/kind/source/confidence fields"
  - "CostTable dataclass with capex_total/opex_per_year/per_tree_cost methods"
  - "DEFAULT_COST_TABLE: 6-line itemized lifecycle cost (5 CapEx + 1 OpEx)"
  - "CAPEX_PER_TREE_EUR=3000.0 / OPEX_PER_TREE_YEAR_EUR=180.0 / OPEX_HORIZON_YEARS=40 (derived from CostTable)"
  - "MOCKS.md: 6 cost-line ledger rows with source anchors + confidence + replacement paths"
  - "VERIFIED/DECLARED/PENDING confidence tag constants"
affects:
  - 06-02 (COST-05 growth/discount)
  - 06-03 (COST-04 editable cost table UI)
  - optimizer (total_cost signature unchanged, magnitude changed)
  - app (cost KPI display magnitude updated)

# Tech tracking
tech-stack:
  added: ["dataclasses (stdlib, frozen CostLine + mutable CostTable)"]
  patterns:
    - "Single source of truth: legacy constants derived from CostTable (no dual definition)"
    - "Confidence tagging: VERIFIED/DECLARED/PENDING per cost line (D-04)"
    - "Named source anchors without fabricated DOIs (D-03)"

key-files:
  created: []
  modified:
    - coolspend/cost_model.py
    - coolspend/tests/test_cost_model.py
    - MOCKS.md

key-decisions:
  - "D-15 backward-compat: CAPEX_PER_TREE_EUR/OPEX_PER_TREE_YEAR_EUR derived from DEFAULT_COST_TABLE.capex_total()/opex_per_year() — single source of truth, no dual definition"
  - "OPEX_HORIZON_YEARS changed from 10 to 40 yr per D-09 (tree functional lifespan, urban sealed-site context)"
  - "DEFAULT_COST_TABLE default: CapEx=3000 EUR/tree (5 lines), OpEx=180 EUR/tree/yr (1 line); label='illustrative European mid-range — verify locally'"
  - "US-anchored lines (pit_excavation, annual_opex) tagged PENDING; EU-anchored lines tagged DECLARED — no overclaim"
  - "German 5-city LCC (Riegel/ScienceDirect 2025) cited as venue-only context in module docstring (paywalled, PENDING)"

patterns-established:
  - "CostTable pattern: editable dataclass whose capex_total()/opex_per_year() methods derive the module constants — Plan 06-03 loads/edits it"
  - "Cost-line audit trail: every default value traceable to a named literature anchor in MOCKS.md"

requirements-completed: [COST-03]

# Metrics
duration: 4min
completed: 2026-05-21
---

# Phase 06 Plan 01: Cost Model Credibility — CostTable Itemization Summary

**Six-line itemized lifecycle CostTable (CapEx=3000 EUR/tree, OpEx=180 EUR/tree/yr) replaces flat €350/€35 placeholders with DECLARED/PENDING-tagged, source-anchored defaults; all existing callers unbroken.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-21T17:43:01Z
- **Completed:** 2026-05-21T17:47:15Z
- **Tasks:** 3 (TDD Task 1 + Task 2 + Task 3)
- **Files modified:** 3

## Accomplishments

- `CostLine` (frozen dataclass) and `CostTable` (mutable dataclass with `capex_total`/`opex_per_year`/`per_tree_cost`) added to `cost_model.py`
- `DEFAULT_COST_TABLE` with exactly 6 sourced lines: `tree_stock` (900, DECLARED), `pit_excavation` (450, PENDING), `structural_soil` (750, DECLARED), `guarding` (300, DECLARED), `planting_labour` (600, DECLARED), `annual_opex` (180/yr, PENDING) — sums: CapEx=3000.0, OpEx=180.0
- `CAPEX_PER_TREE_EUR`/`OPEX_PER_TREE_YEAR_EUR` now derived from `DEFAULT_COST_TABLE` (D-15 single source of truth); `OPEX_HORIZON_YEARS` updated to 40 yr per D-09
- `per_tree_cost()` delegates to `DEFAULT_COST_TABLE.per_tree_cost()`; `total_cost()` signature unchanged
- 14 new TDD tests for CostTable behavior; full regression gate (50 tests: cost_model + optimizer + decision_artifact) green
- MOCKS.md updated with 6 itemized cost-line ledger rows, header note, confidence tags, and replacement paths

## Task Commits

Each task was committed atomically:

1. **Task 1 (TDD): CostLine/CostTable dataclasses + DEFAULT_COST_TABLE + per_tree_cost re-wire** - `458a907` (feat)
2. **Task 2: Re-wire backward-compat constants** - included in `458a907` (per_tree_cost delegation + derived constants implemented together with CostTable)
3. **Task 3: MOCKS.md itemized ledger** - `1bf4201` (feat)

## Files Created/Modified

- `coolspend/cost_model.py` - Added `CostLine`/`CostTable`/`DEFAULT_COST_TABLE`; `VERIFIED`/`DECLARED`/`PENDING` constants; derived `CAPEX_PER_TREE_EUR`/`OPEX_PER_TREE_YEAR_EUR`; `OPEX_HORIZON_YEARS=40`; `per_tree_cost` delegates to CostTable; updated `_COST_SOURCE` tag and KPI note text
- `coolspend/tests/test_cost_model.py` - Added `TestCostLineDataclass` and `TestDefaultCostTable` test classes (14 new tests); total 30 tests pass
- `MOCKS.md` - Replaced single "CapEx/OpEx tree cost constants" row with 6 itemized cost-line rows + header note ("illustrative European mid-range — verify locally", German 5-city LCC context)

## Decisions Made

- Tasks 1 and 2 share the same two files and the implementation was naturally atomic: the CostTable definition, derived constants, and `per_tree_cost` delegation were written together in a single coherent edit. Committed as one feat commit.
- `OPEX_HORIZON_YEARS` changed from 10 to 40 to match D-09 (tree functional lifespan, urban sealed-site context), which materially changes `per_tree_cost()` default output from 700 EUR to 10200 EUR — this is the intended correction.
- US-region sources (NYC CapEx anchor, Boston OpEx anchor) tagged `PENDING` per D-03 instruction; all source strings match the plan's verbatim text, no DOIs fabricated.

## Deviations from Plan

None — plan executed exactly as written. Task 1 and Task 2 were committed together (same files, naturally atomic implementation) rather than as separate commits, but this is a commit granularity choice with no functional impact.

## Issues Encountered

None.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. CostTable is a pure dataclass with no I/O. The `_COST_SOURCE` string in `cost_per_utci_degree` was updated to reflect the itemized table — mitigates T-06-01 (Information disclosure / overclaim) per plan threat register.

## Known Stubs

None. All 6 cost lines carry real (if DECLARED/PENDING) source anchors; no hardcoded empty values or placeholder text flows to UI rendering. `DEFAULT_COST_TABLE.label = "illustrative European mid-range — verify locally"` is intentional provenance labeling, not a stub.

## Next Phase Readiness

- Plan 06-02 (COST-05: growth/discount) can import `DEFAULT_COST_TABLE.per_tree_cost(horizon)` to build the discounted lifecycle integral
- Plan 06-03 (COST-04: editable cost table UI) can expose `CostTable.lines` via Gradio inputs; `per_tree_cost()/total_cost()` recompute live
- Optimizer, app, and all existing tests are unbroken (regression gate: 50/50 green)

---

*Phase: 06-cost-model-credibility*
*Completed: 2026-05-21*
