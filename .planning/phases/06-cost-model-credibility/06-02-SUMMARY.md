---
phase: 06-cost-model-credibility
plan: "02"
subsystem: cost_model
tags: [cost-model, kpi, growth-discount, utci, tdd]
dependency_graph:
  requires: [06-01]
  provides: [GrowthDiscountParams, growth_cooling_fraction, discounted_lifetime_degc, discounted_total_cost, cost_per_utci_degree-growth-routed]
  affects: [cost_model.py, MOCKS.md, test_cost_model.py]
tech_stack:
  added: []
  patterns: [TDD RED/GREEN, growth-ramp linear model, social-discount-rate annual summation, KPI interval propagation]
key_files:
  created: []
  modified:
    - coolspend/cost_model.py
    - MOCKS.md
decisions:
  - "cost_per_utci_degree routes denominator through discounted_lifetime_degc() (equivalent steady-state degC) and numerator through discounted_total_cost() (PV of OpEx); optimizer total_cost() path unchanged"
  - "growth_discount=None default uses DEFAULT_GROWTH_DISCOUNT — existing callers (optimizer.topsis_rank) work unchanged"
  - "New param-echo keys (discount_rate, ramp_years, horizon_years, growth_note) are additive — no Phase 5 key removed"
  - "Zero/negative guard return also includes new param-echo keys (test_guard_result_still_has_new_keys)"
  - "Stale 'KNOWN MOCK DEBT: CAPEX_PER_TREE_EUR=350' note removed from cost_per_utci_degree — debt paid by Plan 06-01"
metrics:
  duration: "~20 min (continuation after prior executor interruption)"
  completed: "2026-05-21"
  tasks_completed: 2
  files_modified: 2
---

# Phase 06 Plan 02: Growth-Horizon Discount for €/°C KPI Summary

**One-liner:** Discounted-lifetime €/°C KPI — denominator routes through a 25yr linear growth ramp + 3.5% social discount rate over 40yr horizon; numerator uses PV of OpEx; all Phase 5 keys preserved.

## What Was Built

### Task 2 GREEN — KPI routing through growth+discount (c1a7a7a → 2377110)

`cost_per_utci_degree` in `coolspend/cost_model.py` was re-routed:

**Signature change (backward-compatible):**
```python
def cost_per_utci_degree(config, band_c=None, growth_discount=None) -> dict
```
`growth_discount=None` defaults to `DEFAULT_GROWTH_DISCOUNT` — all existing callers continue to work unchanged.

**Denominator change (D-07/D-10):**
After `degc_drop` is determined (prefer-measured or UTCI-hours path), it is passed through:
```python
degc_drop = discounted_lifetime_degc(degc_drop, gd)
```
This produces the equivalent discounted-lifetime °C drop (not day-one full canopy). Band propagation, interval math, dual-unit `cost_per_utci_hour`, and the zero-guard are structurally identical — only magnitudes change.

**Numerator change (D-08):**
```python
cost = discounted_total_cost(config, gd)   # PV of CapEx + OpEx
```
The optimizer's NSGA-II budget constraint continues to use `total_cost()` (nominal) — not changed.

**New param-echo keys (additive):**
`discount_rate`, `ramp_years`, `horizon_years`, `growth_note` — present in both positive-value and zero/negative guard returns. No Phase 5 key removed.

### Task 3 — MOCKS.md rows for growth/discount assumptions (9af4049)

Three new DECLARED rows added covering:
- Growth curve (ramp_years=25, initial_fraction=0.20, linear) — replacement: i-Tree / arboricultural data
- Discount rate 3.5%/yr — EU/UK Green Book; replacement: locale-specific municipal finance guidance
- Horizon 40 yr — urban sealed-site lifespan; replacement: local tree-survival data

All three noted as user-editable via Gradio inputs (Plan 06-03 / COST-04).

## Commits (this plan, in order)

| Commit | Type | Description |
|--------|------|-------------|
| c304061 | test (RED) | Failing tests for growth curve + discount functions |
| 5417114 | feat (GREEN) | GrowthDiscountParams + growth_cooling_fraction + discounted_lifetime_degc + discounted_total_cost |
| c1a7a7a | test (RED) | Failing tests for KPI routing through growth+discount |
| 2377110 | feat (GREEN) | Route cost_per_utci_degree through growth+discount |
| 9af4049 | docs | MOCKS.md rows for growth-curve + discount assumptions |

## TDD Gate Compliance

- RED gate (test commit c304061, c1a7a7a): confirmed — tests written before implementation
- GREEN gate (feat commit 5417114, 2377110): confirmed — tests pass after implementation
- REFACTOR gate: not needed — code was clean on first GREEN pass

## Deviations from Plan

None — plan executed exactly as written. The prior executor was interrupted mid-plan (API error) after committing the Task 1 GREEN functions and the Task 2 RED tests. This continuation committed only the remaining GREEN work and docs.

## Verification Results

**Full regression gate (final run):**
```
75 passed in 14.64s
(coolspend/tests/test_cost_model.py + test_optimizer.py + test_decision_artifact.py)
```

**Plan verification commands:**
```
growth_cooling_fraction(0, p) = 0.2   growth_cooling_fraction(25, p) = 1.0  ✓
discount_rate=0.035, ramp_years=25.0, unit=EUR/degC, value is not None         ✓
growth/discount MOCKS rows OK                                                   ✓
```

## Known Stubs

None introduced in this plan. The growth/discount parameters are DECLARED (not MOCK) — they carry source anchors and REQUIRES_VERIFICATION tags, and are user-editable via Plan 06-03.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. Threat mitigations T-06-04 through T-06-06 confirmed addressed:
- T-06-04 (contract break): all Phase 5 keys + guard + interval + dual units preserved; 75-test gate green
- T-06-05 (false precision): all three params DECLARED + REQUIRES_VERIFICATION in MOCKS.md and editable
- T-06-06 (divide-by-zero): `sum(disc_year) > 0` guard present; zero/negative degc_drop guard preserved

## Self-Check: PASSED

- `coolspend/cost_model.py` — modified, committed at 2377110
- `MOCKS.md` — modified, committed at 9af4049
- Commits 2377110, 9af4049 — confirmed in `git log`
- 75 tests passed in final regression gate run
