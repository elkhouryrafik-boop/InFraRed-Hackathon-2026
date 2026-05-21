---
phase: 01-foundation-sdk-boundary
plan: "03"
subsystem: cost-model
tags: [cost-model, kpi, capex, opex, euro-per-degc, honesty-ledger, tdd, offline]
dependency_graph:
  requires: [01-01 (coolspend package)]
  provides: [cost_model, per_tree_cost, total_cost, cost_per_utci_degree, MOCKS.md-row-3]
  affects: [02-optimizer (reads EUR/degC KPI), 03-app (display cards read cost_per_utci_degree)]
tech_stack:
  added: []
  patterns: [standard-metric-dict, declared-assumption-constants, zero-delta-guard, honesty-ledger]
key_files:
  created:
    - coolspend/cost_model.py
    - coolspend/tests/test_cost_model.py
  modified:
    - MOCKS.md
decisions:
  - "DECLARED assumptions CAPEX_PER_TREE_EUR=350/OPEX_PER_TREE_YEAR_EUR=35/OPEX_HORIZON_YEARS=10 tagged REQUIRES_VERIFICATION — no fabricated citation"
  - "Surrogate delta_tmrt_c fallback yields LOW confidence, preserving honest framing"
  - "Non-positive delta returns value=None (not a crash, not a fabricated KPI) — T-01-10 mitigated"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-21T00:32:00Z"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
  commits: 4
---

# Phase 01 Plan 03: Cost Model Summary

**One-liner:** CapEx+OpEx per-tree cost model with documented DECLARED constants and a zero-delta-guarded EUR/degC KPI — the headline metric driving Phase 2 NSGA-II ranking.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | TDD failing RED-gate for cost_model | 63f751d | coolspend/tests/test_cost_model_red.py (temp) |
| 1 (GREEN) | Implement cost_model.py — CapEx/OpEx constants and EUR/degC KPI | 78b7dd1 | coolspend/cost_model.py, MOCKS.md |
| 2 (GREEN) | Full cost-model test suite — 10 offline deterministic tests | 35db482 | coolspend/tests/test_cost_model.py |
| cleanup | Remove temporary RED-gate test file | 75aac80 | (deleted test_cost_model_red.py) |

## Verification Results

- `python -c "from coolspend import cost_model"` — PASS
- `python -m pytest coolspend/tests/test_cost_model.py -q` — PASS (10 passed)
- `python -m pytest -q` (full suite) — PASS (22 passed)
- `grep -Eq "CAPEX_PER_TREE_EUR|OPEX_PER_TREE_YEAR_EUR|OPEX_HORIZON_YEARS" coolspend/cost_model.py` — PASS
- `grep -q "def cost_per_utci_degree" coolspend/cost_model.py` — PASS
- `grep -q "REQUIRES_VERIFICATION" coolspend/cost_model.py` — PASS
- `grep -q "CapEx/OpEx" MOCKS.md` — PASS

## What Was Built

### `coolspend/cost_model.py` (183 lines)

Per-tree cost model with three public functions:

**Module-level DECLARED constants (COST-01):**
- `CAPEX_PER_TREE_EUR = 350.0` — planting: nursery stock + labour + initial irrigation
- `OPEX_PER_TREE_YEAR_EUR = 35.0` — annual maintenance: watering, pruning, inspection
- `OPEX_HORIZON_YEARS = 10` — amortisation horizon for OpEx in headline KPI
- Each tagged `# SOURCE: REQUIRES_VERIFICATION` — no fabricated citation

**`per_tree_cost(horizon_years: int = OPEX_HORIZON_YEARS) -> float`:**
Returns `CAPEX_PER_TREE_EUR + OPEX_PER_TREE_YEAR_EUR * horizon_years`.
With `horizon_years=0` returns CapEx only (350 EUR).

**`total_cost(config: dict) -> float`:**
Returns `tree_count * per_tree_cost()`. Returns 0.0 for non-positive tree_count.

**`cost_per_utci_degree(config: dict) -> dict`** (COST-02):
Computes headline EUR/degC KPI. Delta preference order:
1. `delta_utci_c` — validated UTCI delta → confidence MED
2. `delta_tmrt_c` — surrogate Tmrt proxy → confidence LOW + surrogate note
3. Missing or delta <= 0 → `value=None`, confidence LOW, explanatory note (T-01-10)

Always returns the standard metric dict: `{value, unit, confidence, sources, note, metric_id}`.

**`__main__` smoke block:** prints per_tree_cost(), total_cost(), cost_per_utci_degree()
for sample config `{"tree_count": 20, "delta_utci_c": 0.42}` and demonstrates zero-delta guard.

### `coolspend/tests/test_cost_model.py` (105 lines)

Ten offline deterministic pytest tests:

| Test | What it asserts |
|------|----------------|
| `test_per_tree_cost_capex_only` | per_tree_cost(0) == CAPEX_PER_TREE_EUR |
| `test_per_tree_cost_includes_opex` | per_tree_cost() > CAPEX_PER_TREE_EUR; exact CapEx+OpEx*horizon |
| `test_total_cost_scales[0]` | total_cost(0 trees) == 0.0 |
| `test_total_cost_scales[1]` | total_cost(1 tree) == per_tree_cost() |
| `test_total_cost_scales[25]` | total_cost(25 trees) == 25 * per_tree_cost() |
| `test_cost_per_degree_value` | value == total_cost/delta, unit "EUR/degC", confidence in {MED,HIGH} |
| `test_surrogate_fallback_flagged` | delta_tmrt_c fallback → LOW confidence, "surrogate" in note |
| `test_nonpositive_delta_guarded_zero` | delta=0.0 → value=None, no exception, LOW confidence |
| `test_nonpositive_delta_guarded_negative` | delta=-0.3 → value=None, no exception, LOW confidence |
| `test_returns_standard_metric_dict` | all required keys: value, unit, confidence, sources, note, metric_id |

### `MOCKS.md` (appended row)

New row for `CapEx/OpEx tree cost constants` — status `DECLARED`, reason explains all three
constants are unsourced midrange assumptions; replacement path points to verified municipal data.

## Deviations from Plan

None — plan executed exactly as written.

**TDD note:** Task 2 has `tdd="true"` but the implementation (Task 1) preceded it.
The RED test file (`test_cost_model_red.py`) was committed before `cost_model.py` existed
and correctly failed with `ModuleNotFoundError` (RED gate confirmed). Once GREEN was committed,
Task 2's full test file was written and all 10 tests passed immediately. The temporary RED-gate
file was removed in a follow-up cleanup commit. TDD gate sequence is intact.

## TDD Gate Compliance

- RED gate: commit `63f751d` — `test(01-03): add failing RED-gate tests for cost_model (ImportError expected)` — tests failed with ModuleNotFoundError before implementation
- GREEN gate: commit `78b7dd1` — `feat(01-03): implement cost_model.py ...` — all RED tests pass
- Task 2 GREEN: commit `35db482` — `feat(01-03): add cost-model test suite` — 10 tests pass
- REFACTOR gate: not needed (implementation was clean on first pass)

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| CAPEX_PER_TREE_EUR=350 | coolspend/cost_model.py | 38 | DECLARED assumption; no municipal procurement data confirmed yet — MOCKS.md row added |
| OPEX_PER_TREE_YEAR_EUR=35 | coolspend/cost_model.py | 43 | DECLARED assumption; same sourcing gap |
| OPEX_HORIZON_YEARS=10 | coolspend/cost_model.py | 47 | DECLARED assumption; same sourcing gap |

These stubs are intentional and explicitly documented per the honesty contract.
They do not block Phase 2 ranking (the KPI is structurally correct; the constants need
verified sourcing before the final demo claims defensibility).

## Threat Flags

T-01-09 (unsourced cost constants presented as fact): **mitigated** — constants are visible,
tagged REQUIRES_VERIFICATION, commented as DECLARED assumptions, and logged in MOCKS.md.

T-01-10 (divide-by-zero / NaN KPI from bad delta): **mitigated** — non-positive or missing
delta returns `value=None` with LOW confidence rather than raising or fabricating a number.

T-01-11 (information disclosure): **accepted** — module performs no IO, network, or secret
handling; pure arithmetic only.

## Self-Check: PASSED

All created/modified files exist:
- FOUND: coolspend/cost_model.py
- FOUND: coolspend/tests/test_cost_model.py
- FOUND: MOCKS.md (CapEx/OpEx row appended)
- FOUND: .planning/phases/01-foundation-sdk-boundary/01-03-SUMMARY.md

All commits verified:
- FOUND: 63f751d (Task 1 RED — failing tests)
- FOUND: 78b7dd1 (Task 1 GREEN — cost_model.py + MOCKS.md)
- FOUND: 35db482 (Task 2 — full test suite)
- FOUND: 75aac80 (cleanup — remove temp RED file)
