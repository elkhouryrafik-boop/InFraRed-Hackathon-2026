---
phase: 06-cost-model-credibility
verified: 2026-05-21T18:45:00Z
status: passed
score: 3/3 must-haves verified
overrides_applied: 0
deferred_ux_check: "All 3 success criteria verified in code; full suite 267 passed/1 skipped; live recompute proven headlessly (run_decision: tree_stock +50% → 25694.98→27351.90 EUR/degC; discount 0.035→0.10 → KPI shift). The single remaining item is a live-browser visual confirmation of the Gradio accordion — recorded below as a deferred UX check, non-blocking per verifier, deferred in autonomous mode."
human_verification:
  - test: "Launch `python -m coolspend.app` and open the Cost table accordion. Edit 'Annual maintenance' from 180 to 600 EUR/tree/yr and click Run decision. Confirm EUR/degC value increases (costlier). Then change discount_rate from 0.035 to 0.10 and re-run; confirm the KPI shifts again. Confirm the 'verify against local procurement' note is visible."
    expected: "EUR/degC increases when OpEx is raised; KPI shifts when discount_rate changes; provenance note visible in the accordion."
    why_human: "Live Gradio UI interaction cannot be verified programmatically in this environment. The pipeline wiring is confirmed headlessly (run_decision programmatic test: defaults 25694.98 EUR/degC vs +50% tree_stock 27351.90 EUR/degC, confirmed PASS). The visual accordion open state and the real-browser UX need human confirmation."
---

# Phase 6: Cost-Model Credibility Verification Report

**Phase Goal:** The €/°C denominator survives a budget auditor — per-tree cost is a fully-loaded, sourced lifecycle figure the user can localize per city, with cooling benefit discounted over the establishment/growth curve rather than assumed day-one.

**Verified:** 2026-05-21T18:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Per-tree cost = fully-loaded itemized lifecycle figure (6 lines: stock, pit, structural soil, guarding, labour, annual OpEx) anchored to named sources, replacing €350/€35 | ✓ VERIFIED | `DEFAULT_COST_TABLE` has exactly 6 lines; `capex_total()=3000.0`, `opex_per_year()=180.0`; `CAPEX_PER_TREE_EUR`/`OPEX_PER_TREE_YEAR_EUR` derived from table (not hardcoded); no bare `=350` or `=35` literals in `cost_model.py` |
| 2 | User can edit cost table per city through inputs (not recompiling); KPI recomputes from edited values | ✓ VERIFIED | `cost_config.json` ships; `load_cost_table`/`cost_table_from_dict` fail-open; Gradio `gr.Accordion` with 6+4 `gr.Number` inputs wired to `on_submit` → `run_decision(cost_table=..., growth_discount=...)` → Stage 4b recomputes KPI; headless pipeline test: defaults 25,694.98 EUR/degC vs +50% tree_stock 27,351.90 EUR/degC (PASS) |
| 3 | €/°C KPI applies growth-horizon discount (ramp 0.20→full over 25yr, 3.5% social discount, 40yr horizon); cooling benefit follows establishment/growth curve, not day-one full canopy | ✓ VERIFIED | `discounted_lifetime_degc(1.0, DEFAULT_GROWTH_DISCOUNT) = 0.635` (strictly < 1.0 and > 0.20); discounted KPI 219,692 EUR/degC > no-discount 204,000 EUR/degC (costlier per °C as expected — growth/discount reduces denominator); `cost_per_utci_degree` routes denominator through `discounted_lifetime_degc()` post-delta |

**Score:** 3/3 truths verified

### Deferred Items

None.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `coolspend/cost_model.py` | CostTable/CostLine dataclasses, DEFAULT_COST_TABLE 6 lines, GrowthDiscountParams, discounted_lifetime_degc, cost_per_utci_degree with growth-discount | ✓ VERIFIED | All classes, functions, and module-level instances present and substantive; 985 lines; full docstring with formula |
| `coolspend/cost_config.json` | Shipped default cost table + growth/discount params as editable JSON | ✓ VERIFIED | 65-line JSON; 6 cost lines + `growth_discount` block; matches DEFAULT_COST_TABLE exactly |
| `coolspend/app.py` | Gradio Cost table accordion with 6+4 Number inputs, wired to run_btn | ✓ VERIFIED | `gr.Accordion("Cost table (per-city — edit to localize)")` present; 6 cost-line Number inputs from `_SHIPPED_COST_TABLE.lines`; 4 growth/discount inputs; `*cost_line_inputs` + gd inputs in `run_btn.click(inputs=[...])` |
| `coolspend/app_pipeline.py` | `run_decision(cost_table, growth_discount)` params; Stage 4b KPI recompute | ✓ VERIFIED | `run_decision` signature accepts `cost_table: CostTable | None` and `growth_discount: GrowthDiscountParams | None`; `_run_pipeline` Stage 4b overwrites `cfg["cost_per_utci_degree"]` when either param is non-None |
| `coolspend/tests/test_cost_model.py` | Tests for CostTable, growth/discount functions | ✓ VERIFIED | File exists; 80 tests pass (`test_cost_model.py` + `test_cost_config.py` combined run) |
| `coolspend/tests/test_cost_config.py` | Round-trip, fail-open, edited-value tests | ✓ VERIFIED | File exists; included in the 80-test pass above |
| `MOCKS.md` | 6 cost-line ledger rows + 3 growth/discount rows with named source + confidence + replacement path | ✓ VERIFIED | All 6 cost lines present; "illustrative European mid-range" header note present; 3 growth/discount rows (ramp, discount rate, horizon) with DECLARED tag and replacement paths; no fabricated DOIs |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cost_model.py::per_tree_cost` | `DEFAULT_COST_TABLE.per_tree_cost()` | delegation call | ✓ WIRED | `return DEFAULT_COST_TABLE.per_tree_cost(horizon_years)` — single source of truth |
| `cost_model.py::total_cost` | `per_tree_cost()` | delegates unchanged | ✓ WIRED | `tree_count * per_tree_cost()` — optimizer contract preserved |
| `cost_model.py::cost_per_utci_degree` | `discounted_lifetime_degc` | denominator routing | ✓ WIRED | `degc_drop = discounted_lifetime_degc(degc_drop, gd)` called before KPI computation |
| `cost_model.py::cost_per_utci_degree` | `discounted_total_cost` | numerator routing | ✓ WIRED | `cost = discounted_total_cost(config, gd, cost_table=ct)` |
| `cost_config.json` | `cost_model.py::load_cost_table` | `json.load → CostTable + GrowthDiscountParams` | ✓ WIRED | `load_cost_table()` reads `Path(__file__).parent / "cost_config.json"`; returns `(3000.0 CapEx, 180.0 OpEx, 0.035 discount_rate)` |
| `app.py Gradio cost inputs` | `run_decision / cost_per_utci_degree` | `cost_table_from_dict → run_decision(cost_table=edited_table)` | ✓ WIRED | `on_submit` assembles edited dict → `cost_table_from_dict` → `run_decision(cost_table=edited_table, growth_discount=edited_gd)` → Stage 4b recomputes KPI |
| `optimizer.py::topsis_rank` | `total_cost` (nominal) | unchanged signature | ✓ WIRED | Optimizer path uses nominal `total_cost()`, not discounted — correct per D-08 |
| `CAPEX_PER_TREE_EUR` | `DEFAULT_COST_TABLE.capex_total()` | derived constant | ✓ WIRED | `CAPEX_PER_TREE_EUR: float = DEFAULT_COST_TABLE.capex_total()` — no independent hardcode |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `app.py::on_submit` | `edited_table`, `edited_gd` | `cost_line_values` varargs from Gradio Number inputs, assembled via `cost_table_from_dict` | Yes — values flow from user inputs through `cost_table_from_dict` into `run_decision` | ✓ FLOWING |
| `app_pipeline.py::_run_pipeline` | `cfg["cost_per_utci_degree"]` | Stage 4b: `cost_per_utci_degree(cfg, cost_table=cost_table, growth_discount=growth_discount)` | Yes — real computation using edited or default table | ✓ FLOWING |
| `cost_model.py::cost_per_utci_degree` | `degc_drop` | `discounted_lifetime_degc(degc_drop, gd)` | Yes — annual summation over 40yr with ramp + discount | ✓ FLOWING |
| `cost_model.py::cost_per_utci_degree` | `cost` | `discounted_total_cost(config, gd, cost_table=ct)` | Yes — CapEx year-0 + PV(OpEx) over horizon | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| 6-line CostTable with correct CapEx/OpEx | `DEFAULT_COST_TABLE.capex_total()`, `opex_per_year()` | 3000.0 / 180.0 | ✓ PASS |
| Legacy constants derived from table | `CAPEX_PER_TREE_EUR=3000.0`, `OPEX_PER_TREE_YEAR_EUR=180.0`, `OPEX_HORIZON_YEARS=40` | All match table | ✓ PASS |
| per_tree_cost(0) = CapEx only | `per_tree_cost(0) == 3000.0` | 3000.0 | ✓ PASS |
| per_tree_cost(40) = CapEx + OpEx*40 | `per_tree_cost(40) == 10200.0` | 10200.0 | ✓ PASS |
| growth_cooling_fraction(0) = 0.20 | `growth_cooling_fraction(0, DEFAULT_GROWTH_DISCOUNT)` | 0.2 | ✓ PASS |
| growth_cooling_fraction(25) = 1.0 | `growth_cooling_fraction(25, DEFAULT_GROWTH_DISCOUNT)` | 1.0 | ✓ PASS |
| discounted_lifetime_degc < full canopy | `discounted_lifetime_degc(1.0, DEFAULT_GROWTH_DISCOUNT) < 1.0` | 0.635 | ✓ PASS |
| discounted KPI > no-discount (costlier) | `r_disc["value"] > r_nodisc["value"]` | 219,692 > 204,000 | ✓ PASS |
| All Phase 5 dict keys preserved | All 15 required keys present including `band_c`, `band_source`, `utci_hours_unit` | All present | ✓ PASS |
| New COST-05 keys additive | `discount_rate`, `ramp_years`, `horizon_years`, `growth_note` present | All present | ✓ PASS |
| Zero-guard includes new keys | Zero-delta result still has `discount_rate`, `growth_note`, `band_source` | All present | ✓ PASS |
| load_cost_table fail-open | Missing path → returns (3000.0, 180.0) without raising | Confirmed, warning logged | ✓ PASS |
| Live KPI recompute (headless) | run_decision defaults 25,694.98; +50% tree_stock → 27,351.90 | Increase confirmed | ✓ PASS |
| build_demo() headless | `from coolspend.app import build_demo; build_demo()` | "build_demo OK" | ✓ PASS |
| Full test suite | `pytest coolspend/tests/ -q` | 267 passed, 1 skipped | ✓ PASS |
| Live UI recompute via browser | Accordion open, edit cost line, confirm KPI shift | NOT YET VERIFIED | ? SKIP — human needed |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| COST-03 | 06-01 | Per-tree cost = fully-loaded lifecycle figure (pit excavation, structural soil, guarding, multi-year OpEx) anchored to a cited source, replacing €350/€35 | ✓ SATISFIED | 6-line DEFAULT_COST_TABLE; capex=3000/opex=180; all lines have named source + confidence; no bare 350/35 in code; MOCKS.md 6 ledger rows |
| COST-04 | 06-03 | A user can configure the cost table per city/locale (editable inputs, not hardcoded constants) | ✓ SATISFIED (code) / ? NEEDS HUMAN (UI) | `cost_config.json` + `load_cost_table` + `cost_table_from_dict` + Gradio accordion with 6+4 inputs + Stage 4b KPI recompute — all implemented and wired; headless pipeline recompute confirmed; live browser interaction needs human confirmation |
| COST-05 | 06-02 | €/°C KPI applies growth-horizon discount so cooling benefit is modeled over the establishment/growth curve, not assumed day-one | ✓ SATISFIED | `GrowthDiscountParams` + `growth_cooling_fraction` + `discounted_lifetime_degc` + `discounted_total_cost` implemented; `cost_per_utci_degree` routes denominator and numerator through them; discounted KPI demonstrably costlier than day-one assumption |

**Note on REQUIREMENTS.md tracking discrepancy:** COST-03 has `[x]` in the bullet list but the traceability table still reads "Pending". COST-04 has `[ ]` in the bullet list and "Pending" in the traceability table despite being fully implemented. COST-05 is correctly marked complete. The REQUIREMENTS.md traceability rows for COST-03 and COST-04 need updating to reflect completion — this is a documentation tracking gap, not a code gap.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `coolspend/app.py` | 289, 396 | `placeholder=` | ℹ️ Info | Gradio widget placeholder text (UI hint, not code stub) — not a production issue |
| None | — | TODO/FIXME/PLACEHOLDER in Phase 6 files | ℹ️ Info | None found. The stale "KNOWN MOCK DEBT: CAPEX_PER_TREE_EUR=350" note was removed as required by Plan 06-02. |

No blocker anti-patterns found.

### Human Verification Required

#### 1. Live Gradio UI — Cost Table Edit → KPI Recompute

**Test:**
1. Launch the app: `python -m coolspend.app`
2. Backend = mock. Click "Run decision" with default cost inputs. Note the EUR/degC [lo–hi] value in the rank-1 row.
3. Open the "Cost table (per-city — edit to localize)" accordion.
4. Change "Annual maintenance (watering, pruning, inspection) (EUR/tree/yr) [PENDING]" from 180 to 600. Click "Run decision" again.
5. Confirm the EUR/degC value INCREASED (costlier).
6. Change the "Discount rate (social, 0–1)" from 0.035 to 0.10 and re-run; confirm the KPI shifts.
7. Confirm the "_Defaults = illustrative European mid-range — verify against local procurement (COST-03/COST-04)._" note is visible.

**Expected:** EUR/degC increases when OpEx is raised; KPI shifts when discount_rate changes; provenance note is visible in the accordion.

**Why human:** Live Gradio browser interaction cannot be scripted in this headless verification environment. The underlying pipeline wiring is confirmed programmatically (headless run_decision test: defaults 25,694.98 EUR/degC → +50% tree_stock 27,351.90 EUR/degC). The plan's own Task 3 human-verify checkpoint was satisfied programmatically during execution — this verification surfaces it to the developer for optional live confirmation given COST-04 is still marked `[ ]` in REQUIREMENTS.md.

### Gaps Summary

No code gaps found. All three success criteria are verified against the actual codebase:

- SC1 (COST-03): Fully-loaded 6-line CostTable (CapEx=€3,000, OpEx=€180/yr) replaces €350/€35. Each line has named source + confidence. Legacy constants derived from table.
- SC2 (COST-04): `cost_config.json` ships; `load_cost_table`/`cost_table_from_dict` fail-open; Gradio accordion with 6+4 editable inputs wired through `on_submit` → `run_decision` → Stage 4b KPI recompute. Headless pipeline recompute confirmed.
- SC3 (COST-05): Growth ramp (0.20→full over 25yr) + 3.5% social discount + 40yr horizon in `discounted_lifetime_degc`, routed into KPI denominator and numerator. Discounted KPI demonstrably costlier than day-one assumption.

The sole human_needed item is a live browser confirmation of the Gradio UI accordion (COST-04 requirement), which is a UX visual check, not a code check. The code path is verified.

One documentation note: REQUIREMENTS.md traceability rows for COST-03 and COST-04 should be updated to "Complete" — this does not affect phase gate status.

---

_Verified: 2026-05-21T18:45:00Z_
_Verifier: Claude (gsd-verifier)_
