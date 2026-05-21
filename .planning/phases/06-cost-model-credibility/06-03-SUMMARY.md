---
phase: "06-cost-model-credibility"
plan: "03"
subsystem: "cost-model / ui"
tags: [cost-model, gradio, kpi, configurable, COST-04]
dependency_graph:
  requires: [06-01, 06-02]
  provides: [cost_config.json, load_cost_table, cost_table_from_dict, gradio-cost-inputs, live-kpi-recompute]
  affects: [app.py, app_pipeline.py, cost_model.py]
tech_stack:
  added: []
  patterns: [fail-open config loading, varargs Gradio wiring, JSON cost-table serialization]
key_files:
  created:
    - coolspend/cost_config.json
    - coolspend/tests/test_cost_config.py
  modified:
    - coolspend/cost_model.py
    - coolspend/app.py
    - coolspend/app_pipeline.py
decisions:
  - "cost_table_from_dict / load_cost_table fail-open to DEFAULT_COST_TABLE + DEFAULT_GROWTH_DISCOUNT on missing/invalid JSON (never raises)"
  - "on_submit receives cost line + growth/discount inputs as *cost_line_values varargs; assembles CostTable via cost_table_from_dict and passes to run_decision"
  - "Stage 4b in _run_pipeline: KPI recomputed post-topsis_rank when cost_table or growth_discount is non-None; optimizer total_cost() path unchanged"
metrics:
  duration: "~20m (continuation after API interruption)"
  completed_date: "2026-05-21"
  tasks_completed: 3
  files_changed: 5
requirements_satisfied: [COST-04]
---

# Phase 06 Plan 03: Editable Per-City Cost Table via Gradio (COST-04) Summary

**One-liner:** JSON-backed cost table (cost_config.json) with load_cost_table/cost_table_from_dict helpers and 6+4 Gradio inputs that recompute the EUR/degC KPI live from edited values.

## What Was Built

### Task 1 (committed d7def58): cost_config.json + load_cost_table/cost_table_from_dict + cost_table param

- `coolspend/cost_config.json`: ships DEFAULT_COST_TABLE (6 cost lines: 5 CapEx + 1 OpEx) + DEFAULT_GROWTH_DISCOUNT params as editable JSON
- `cost_model.py::cost_table_from_dict(d)`: builds CostTable + GrowthDiscountParams from a parsed JSON dict; falls back to DEFAULT_* for any missing field; validates confidence in {VERIFIED, DECLARED, PENDING}
- `cost_model.py::load_cost_table(path=None)`: loads cost_config.json next to cost_model.py (or override path); fail-open — invalid/missing JSON logs a warning and returns DEFAULT_COST_TABLE/DEFAULT_GROWTH_DISCOUNT; never raises
- `cost_model.py::cost_per_utci_degree(config, ..., cost_table=None)`: optional cost_table param threads edited table into numerator; when None, uses DEFAULT_COST_TABLE
- `cost_model.py::discounted_total_cost(config, p, cost_table=None)`: uses edited table's per_tree_cost() when supplied
- `coolspend/tests/test_cost_config.py`: round-trip, fail-open, and edited-value tests

### Task 2 (committed 1270d8e): Gradio inputs + pipeline threading

- `app.py::build_demo()`: adds `gr.Accordion("Cost table (per-city — edit to localize)", open=False)` in the inputs column with:
  - 6 `gr.Number` inputs (one per cost line), pre-filled from `_SHIPPED_COST_TABLE.lines`; each labelled with label + unit + [CONFIDENCE]
  - Markdown note: "Defaults = illustrative European mid-range — verify against local procurement (COST-03/COST-04)"
  - 4 `gr.Number` inputs for ramp_years, initial_fraction, discount_rate, horizon_years
  - All 10 inputs appended to `run_btn.click(inputs=[...])` after the 5 existing core inputs
- `app.py::on_submit(...)`: extended with `*cost_line_values` varargs; assembles edited CostTable + GrowthDiscountParams via cost_table_from_dict and passes to run_decision
- `app_pipeline.py::run_decision(...)`: extended with optional `cost_table` and `growth_discount` params; threaded into `_run_pipeline`
- `app_pipeline.py::_run_pipeline(...)`: Stage 4b recomputes `cost_per_utci_degree` for each Top-3 config when cost_table or growth_discount is non-None (post-topsis_rank); optimizer total_cost() unchanged

### Task 3 (checkpoint:human-verify — satisfied PROGRAMMATICALLY)

Autonomous checkpoint evidence — three pipeline runs with assertions:

| Run | Edit | EUR/degC result | Assertion |
|-----|------|-----------------|-----------|
| Run 1 | Defaults (both None) | 25,694.98 | baseline |
| Run 2 | tree_stock +50% (900 -> 1350 EUR) | 27,351.90 | +1,656.92 EUR/degC (higher CapEx -> costlier KPI) PASS |
| Run 3 | discount_rate 0.035 -> 0.10 | 24,108.41 | -1,586.57 EUR/degC (heavier discount -> less PV benefit -> shift confirmed) PASS |

Live KPI recompute confirmed. The edited values flow through `cost_table_from_dict -> run_decision(cost_table=..., growth_discount=...) -> _run_pipeline Stage 4b -> cost_per_utci_degree`.

## Test Results

```
267 passed, 1 skipped, 15 warnings
```

Full suite green. All cost_config and cost_model tests pass. build_demo() constructs headlessly.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | d7def58 | feat(06-03): cost_config.json + load_cost_table/cost_table_from_dict + cost_table param (COST-04) |
| 2    | 1270d8e | feat(06-03): Gradio cost inputs + thread edits through run_decision into live KPI recompute |

## Deviations from Plan

None — plan executed exactly as written. Checkpoint Task 3 satisfied programmatically (autonomous mode) per the checkpoint_protocol: three headless pipeline calls with assertions proved live KPI recompute.

## Known Stubs

None. The cost inputs are wired to real data from cost_config.json and the KPI recompute is exercised by the test suite.

## Self-Check: PASSED

- coolspend/cost_config.json: FOUND (committed d7def58)
- coolspend/tests/test_cost_config.py: FOUND (committed d7def58)
- coolspend/app.py (cost accordion): FOUND (committed 1270d8e)
- coolspend/app_pipeline.py (cost_table param): FOUND (committed 1270d8e)
- 267 passed, 1 skipped — all tests green
- build_demo() headless: CONFIRMED
- Programmatic checkpoint: CONFIRMED (3 assertions passed)
- .planning/config.json NOT staged/committed: CONFIRMED
- 05-01-SUMMARY.md NOT staged/committed: CONFIRMED
