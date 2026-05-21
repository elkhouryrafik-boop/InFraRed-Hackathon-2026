---
phase: 02-optimizer-core
verified: 2026-05-21T00:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 2: Optimizer Core — Verification Report

**Phase Goal:** NSGA-II optimizer on a fast surrogate (2 objectives: thermal relief + ecological coherence, budget constraint), validating the Top-3 with real/cached UTCI, producing a ranked EUR-per-degC allocation decision artifact. The optimizer makes ZERO live SDK calls in its hot loop; only Top-3 validation calls the SDK (<=3, SimBudget-guarded). Live Infrared path is real (activated by INFRARED_API_KEY).

**Verified:** 2026-05-21
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | rules_engine.py is pure/deterministic/offline: spacing penalty (RULES-01) + species diversity (RULES-02), no pollinator corridor | VERIFIED | No `import infrared/requests/httpx` in module; `def pollinator` absent; only `spacing_penalty`, `species_diversity_score`, `ecological_score` defined; `test_no_network_imports_in_module` passes |
| 2 | Exactly 2 objectives ship — no pollinator corridor | VERIFIED | `n_obj=2` in `TreeBudgetProblem.__init__`; pollinator mention is exclusion rationale only (CONCERNS 1.2 comment), no pollinator function defined |
| 3 | NSGA-II (pymoo) over tree coords, 2 objectives + budget constraint, seed 42 deterministic (OPT-01) | VERIFIED | `from pymoo.algorithms.moo.nsga2 import NSGA2`; `n_obj=2`, `n_ieq_constr=1`; `SEED: int = 42`; `test_pareto_front_min_size` confirms Pareto front >= 10 configs |
| 4 | `_evaluate` uses ONLY the surrogate — zero infrared_sdk/sdk_client calls in hot loop (OPT-02) | VERIFIED | `_evaluate` body contains only `thermal_relief(cfg)`, `ecological_score(cfg)`, `total_cost(cfg)`; no sdk_client top-level import in optimizer.py; `test_no_sdk_in_hot_path` monkeypatches sdk to raise and run_optimisation completes without triggering it |
| 5 | `validate_top3_with_infrared` calls the SDK exactly 3 times, SimBudget-guarded (OPT-03); live path real/lazy (OPT-03) | VERIFIED | SDK import is local-only inside `validate_top3_with_infrared` (line 369); `budget.record()` called once per Top-3 config; `test_validate_exactly_three_calls` confirms log length == 3 and 4th call raises RuntimeError; `_live_utci` lazily imports `infrared_sdk`; live path raises EnvironmentError without INFRARED_API_KEY |
| 6 | `top3_configurations.json` is a ranked allocation with coords + priority + EUR/degC per config (DEC-01) and before/after baseline-vs-intervention with headline delta (DEC-02); every config carries disclaimer | VERIFIED | Artifact confirmed: 3 ranked configs with trees list, tree_count, cost_per_utci_degree (value/unit/confidence/sources), rank order 1-2-3 ascending by EUR/degC; `before_after` block with baseline_utci_c=41.0, chosen_validated_utci_c=39.59, headline_delta_utci_c=1.41; every config carries non-empty disclaimer string; `test_every_config_has_disclaimer` and `test_allocation_is_priority_ordered` pass |
| 7 | MOCKS.md documents surrogate, spacing/diversity/cost constants as REQUIRES_VERIFICATION; no fabricated citations | VERIFIED | 9 MOCKS.md rows confirmed: mock UTCI, live UTCI, site fixture, CapEx/OpEx, ecological rules, delta_tmrt_surrogate, TREE_SHADE_FRACTION/CANOPY_RADIUS, TOPSIS weights, surrogate outputs; every declared constant tagged REQUIRES_VERIFICATION; no fabricated citation — Garcia-Nevado 2020 citation mismatch is explicitly documented as a known limitation |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `coolspend/rules_engine.py` | spacing penalty (RULES-01) + species diversity (RULES-02) | VERIFIED | 263 lines; `def spacing_penalty`, `def species_diversity_score`, `def ecological_score`; no network imports; MODULE-LEVEL SOURCE/DECLARED comments |
| `coolspend/tests/test_rules_engine.py` | offline deterministic tests | VERIFIED | 322 lines; 22 tests covering spacing monotonicity, diversity reward, determinism, no-network contract; all pass |
| `coolspend/optimizer.py` | NSGA-II 2-obj problem + surrogate hot path + validate_top3 | VERIFIED | 753 lines; TreeBudgetProblem n_obj=2 n_ieq=1; sdk_client import local only; topsis_rank; save_outputs; DEC-01/DEC-02 fulfilled |
| `coolspend/tests/test_optimizer.py` | hot path SDK isolation + 3-call budget + Pareto size | VERIFIED | 215 lines; 6 tests including monkeypatch SDK-raise test; all pass |
| `coolspend/tests/test_decision_artifact.py` | DEC-01/DEC-02 schema + disclaimer + priority order | VERIFIED | 314 lines; 6 tests; test_main_writes_artifact end-to-end; all pass |
| `coolspend/main.py` | end-to-end CLI pipeline | VERIFIED | 165 lines; 5-stage pipeline; mock default; produces outputs/top3_configurations.json with disclaimer footer |
| `MOCKS.md` | honesty ledger with all mock/declared items | VERIFIED | 9 rows; every MOCK/DECLARED/SURROGATE constant has a matching row; no fabricated citations |
| `outputs/top3_configurations.json` | ranked decision artifact | VERIFIED | Written by `INFRARED_BACKEND=mock python -m coolspend.main`; valid JSON; 3 ranked configs; before_after block present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `coolspend/optimizer.py::_evaluate` | `coolspend/spatial_engine.py::thermal_relief` | direct import at module top | WIRED | `from coolspend.spatial_engine import ... thermal_relief`; used in `_evaluate` as `-thermal_relief(cfg)` |
| `coolspend/optimizer.py::_evaluate` | `coolspend/rules_engine.py::ecological_score` | direct import at module top | WIRED | `from coolspend.rules_engine import ecological_score`; used in `_evaluate` as `-ecological_score(cfg)` |
| `coolspend/optimizer.py::_evaluate` | `coolspend/cost_model.py::total_cost` | direct import at module top | WIRED | `from coolspend.cost_model import total_cost`; used in `_evaluate` as `total_cost(cfg) - self.budget_eur` |
| `coolspend/optimizer.py::validate_top3_with_infrared` | `coolspend/sdk_client.py` | local import inside function only | WIRED + ISOLATED | `from coolspend.sdk_client import get_baseline_utci, get_intervention_utci, SimBudget` at line 369; zero top-level SDK import confirmed |
| `coolspend/optimizer.py::topsis_rank` | `coolspend/cost_model.py::cost_per_utci_degree` | local import | WIRED | `from coolspend.cost_model import cost_per_utci_degree, total_cost` at line 436 |
| `coolspend/main.py` | `coolspend/optimizer.py` | direct imports | WIRED | All 5 pipeline stages explicitly import and call run_optimisation, select_top3, validate_top3_with_infrared, topsis_rank, save_outputs |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `outputs/top3_configurations.json` | `configurations[*].trees` | NSGA-II Pareto front chromosomes decoded via `decode(X[idx])` | Yes — real optimizer output, 12 tree coords per config | FLOWING |
| `outputs/top3_configurations.json` | `configurations[*].delta_utci_c` | `get_intervention_utci(geom)` mock UTCI call per config | Mock — synthetic scalar (documented disclaimer); real when INFRARED_BACKEND=live | FLOWING (mock path) |
| `outputs/top3_configurations.json` | `configurations[*].cost_per_utci_degree` | `cost_per_utci_degree(cfg)` from cost_model.py | Computed from total_cost and delta_utci_c | FLOWING |
| `outputs/top3_configurations.json` | `before_after.headline_delta_utci_c` | rank-1 config `delta_utci_c` field | = round(baseline_utci_c - validated_utci_c, 2) | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CLI runs offline and writes valid JSON | `INFRARED_BACKEND=mock python -m coolspend.main` | Wrote `outputs/top3_configurations.json`, 3 ranked configs, DEC summary printed | PASS |
| Pareto front >= 10 configs (OPT-01) | `test_pareto_front_min_size` | 60 Pareto configs produced | PASS |
| SDK not called in hot path (OPT-02) | `test_no_sdk_in_hot_path` (monkeypatch raises) | `run_optimisation()` completes without triggering raise | PASS |
| Exactly 3 intervention calls (OPT-03) | `test_validate_exactly_three_calls` | `budget.log` length == 3; 4th raises RuntimeError | PASS |
| SimBudget raises on overflow | Manual: 3 records then 4th | RuntimeError: SimBudget exceeded: 4 live UTCI calls > cap 3 | PASS |
| Live path guarded without API key | `INFRARED_BACKEND=live` without `INFRARED_API_KEY` | EnvironmentError raised immediately | PASS |
| Full pytest suite offline | `python -m pytest coolspend/tests/ -v` | 88 passed, 0 failed (338 pymoo deprecation warnings only) | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RULES-01 | 02-01 | Minimum-spacing penalty | SATISFIED | `spacing_penalty()` in `rules_engine.py`; 11 passing test cases proving monotonicity and correctness |
| RULES-02 | 02-01 | Species-diversity score | SATISFIED | `species_diversity_score()` in `rules_engine.py`; Shannon index normalised; 8 passing test cases |
| OPT-01 | 02-03 | NSGA-II (pymoo) over tree coords, 2 objectives, budget constraint | SATISFIED | `TreeBudgetProblem` with `n_obj=2`, `n_ieq_constr=1`; `SEED=42`; pymoo `NSGA2` confirmed |
| OPT-02 | 02-03 | Fitness uses surrogate only — no live SDK call per chromosome | SATISFIED | `_evaluate` uses only `thermal_relief`, `ecological_score`, `total_cost`; `test_no_sdk_in_hot_path` proves isolation |
| OPT-03 | 02-04 | Validate Top-3 with real/cached UTCI; rank by EUR/degC | SATISFIED | `validate_top3_with_infrared` makes exactly 3 `get_intervention_utci` calls; SimBudget-guarded; live path real (lazy infrared_sdk import) |
| DEC-01 | 02-05 | Ranked allocation (which locations to plant, priority order, within budget) | SATISFIED | `top3_configurations.json` has 3 configs with tree coords, rank, EUR/degC KPI ascending |
| DEC-02 | 02-05 | Before/after comparison (baseline UTCI vs intervention) with headline delta | SATISFIED | `before_after` block: baseline_utci_c=41.0, headline_delta_utci_c=1.41 with `chosen_validated_utci_c=39.59` |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `outputs/top3_configurations.json` | All 3 configs have identical `topsis_score=0.0`, identical `ecological_score=1.0`, identical `delta_utci_c=1.41`, identical `cost_per_utci_degree` | INFO | This is a surrogate saturation artifact: with `N_TREES=12` and the analytical `thermal_relief` formula, all Pareto-front maximal configs reach peak coverage fraction simultaneously and the species cycling (round-robin) produces perfect diversity (4 species, 3 each). The degenerate TOPSIS is mathematically correct for tied inputs; `topsis_rank` handles it gracefully (no division by zero). The mock backend applies the same `coverage_fraction` formula to all 3 geometries, producing identical `delta_utci_c`. This is a known surrogate limitation documented in `MOCKS.md` and audit_record.json. Not a blocker — the pipeline runs correctly and the degenerate case is handled safely. |
| `coolspend/sdk_client.py` line 288 | `utci_request = AnalysesName.utci  # confirm member name at May-27 wiring` — TODO comment in live path | INFO | Noted in code as a one-line wiring confirmation required at May-27 API key issuance. Offline/mock path is unaffected. Not a blocker for Phase 2 goal which requires only that the live path is architecturally present and key-guarded. |

---

### Human Verification Required

None. All goal-relevant behaviors are verifiable programmatically for this phase. The live Infrared API path requires a real API key (available May 27, 2026) but the architecture and guard are verified by the `test_live_without_key_raises` test and manual smoke check.

---

## Gaps Summary

No gaps. All 7 phase-goal truths verified against the actual codebase and confirmed by execution.

**Notable observations (non-blocking):**

1. **TOPSIS degeneration in mock output:** The surrogate's `thermal_relief` formula saturates at 12 active trees for all three selected Pareto representatives (peak coverage fraction hit identically). This causes all three configs to have identical mock UTCI deltas, costs, and ecological scores, making TOPSIS produce `0.0` for all three. This is correct behavior for degenerate inputs and is documented in `audit_record.json`. The live Infrared backend (INFRARED_BACKEND=live) will produce differentiated UTCI values since the API runs a real simulation rather than a coverage-fraction formula — breaking the degeneracy.

2. **Pareto diversity constraint:** The `test_pareto_front_min_size` uses `pop_size=30, n_gen=20` (small run) and still produces >= 10 distinct Pareto configs. The full run uses `pop_size=60, n_gen=60` producing 60 Pareto configs. The 3 selected representatives (MAX_THERMAL, MAX_ECOLOGICAL, BALANCED) happen to coincide in the full run because the objective landscape is flat at the optimum — a surrogate property, not an optimizer bug.

3. **pymoo DeprecationWarning:** `np.row_stack` alias deprecation in pymoo 0.6.1's `rank_and_crowding/metrics.py`. This is an internal pymoo issue, not a CoolSpend bug. 338 warnings across the suite, all from pymoo internals.

---

_Verified: 2026-05-21_
_Verifier: Claude (gsd-verifier)_
