---
phase: 02-optimizer-core
plan: "05"
subsystem: optimizer/decision-artifact
tags: [decision-artifact, topsis, json, before-after, audit, cli, provenance]
requirements: [DEC-01, DEC-02]

dependency_graph:
  requires:
    - 02-04: run_optimisation, select_top3, validate_top3_with_infrared
    - 02-01: cost_model (cost_per_utci_degree, total_cost)
    - 02-02: sdk_client (SimBudget, get_baseline_utci, get_intervention_utci)
  provides:
    - topsis_rank(): validated Top-3 ranked by EUR/degC, TOPSIS tie-break
    - save_outputs(): writes top3_configurations.json (DEC-01+DEC-02), audit_record.json, pareto_front.png
    - coolspend/main.py: end-to-end CLI (offline mock + live with API key)
  affects:
    - Phase 3 (app.py Gradio): reads top3_configurations.json schema

tech_stack:
  added:
    - matplotlib (Agg backend, best-effort Pareto PNG — pipeline never blocked by absence)
  patterns:
    - TOPSIS (Hwang & Yoon 1981): vector-norm normalise, weight, ideal best/worst, relative closeness
    - Primary ranking: ascending EUR/degC; TOPSIS closeness as tie-break
    - Best-effort guard: plot_pareto() catches all exceptions so JSON is always written (T-02-18)

key_files:
  created:
    - coolspend/main.py: end-to-end CLI orchestrating full 5-stage pipeline
    - coolspend/tests/test_decision_artifact.py: 6 offline tests (DEC-01, DEC-02, honesty)
  modified:
    - coolspend/optimizer.py: appended topsis_rank, _build_before_after, save_outputs, write_audit_record, plot_pareto
    - MOCKS.md: two new rows (TOPSIS weights adjustable; surrogate JSON outputs)
    - .gitignore: added outputs/ exclusion

decisions:
  - "Primary ranking by EUR/degC (not by TOPSIS closeness) — TOPSIS used as tie-break only; this ensures the cheapest-per-degree config is always rank-1 (DEC-01 defensibility)"
  - "TOPSIS weights (0.6 thermal / 0.4 ecological) documented as adjustable developer judgment, NOT stakeholder-elicited constants (ARCHITECTURE.md Known Issues #3 / CONCERNS 1.6)"
  - "Disclaimer injected by save_outputs if missing — ensures honesty T-02-15 is never dependent on caller compliance"
  - "plot_pareto() wrapped in broad exception handler + matplotlib absence guard — JSON artifact pipeline never blocked by rendering failure (T-02-18)"
  - "outputs/ added to .gitignore — generated artifacts should not be committed to source control"

metrics:
  duration: "~25 minutes"
  completed: "2026-05-21"
  tasks_completed: 3
  tests_added: 6
  total_tests_passing: 88
  files_created: 2
  files_modified: 4
---

# Phase 02 Plan 05: Decision Artifact Summary

**One-liner:** TOPSIS EUR/degC ranking with top3_configurations.json DEC-01 ranked allocation, DEC-02 before/after record, audit trail, Pareto PNG, and offline-capable main.py CLI.

---

## What Was Built

### DEC-01: Ranked Allocation (top3_configurations.json)

`outputs/top3_configurations.json` contains 3 within-budget tree configurations ranked in ascending EUR/degC order (rank-1 = cheapest per degree of UTCI relief). Each configuration lists all 12 tree slots with their `x_m`, `y_m`, `species`, and `active` fields. The file includes full `run_metadata` and every config carries a non-empty `disclaimer` key.

### DEC-02: Before/After Record

The `before_after` block in the artifact records:
- `baseline_utci_c`: 41.0 °C (open-site mock baseline)
- `chosen_label`: rank-1 config label
- `chosen_validated_utci_c`: post-intervention UTCI (mock: 39.59 °C)
- `headline_delta_utci_c`: 1.41 °C comfort improvement
- `source`: validated_disclaimer from the backend

### Functions Added to optimizer.py

| Function | Role |
|----------|------|
| `topsis_rank(top3, weights=(0.6, 0.4))` | Vector-norm TOPSIS; primary sort EUR/degC ascending; TOPSIS tie-break |
| `_build_before_after(top3)` | DEC-02 record from rank-1 config |
| `save_outputs(top3, result, out_dir, budget_eur)` | Writes JSON+audit+PNG; disclaimer guaranteed on all configs |
| `write_audit_record(top3, result, out_dir)` | Provenance trail: surrogate flags, TOPSIS weights echoed, backend tags |
| `plot_pareto(result, out_path)` | Best-effort Pareto scatter (matplotlib Agg); never blocks pipeline |

### CLI: coolspend/main.py

```
python -m coolspend.main                             # offline (mock default)
INFRARED_BACKEND=live INFRARED_API_KEY=<key> python -m coolspend.main   # live (post-May 27)
```

Prints a 5-stage pipeline progress log and a decision summary block showing baseline UTCI, rank-1 UTCI, headline delta, and EUR/degC KPI. Mock backend prints a prominent "NOT MEASURED DATA" disclaimer.

---

## Verification

- `python -m pytest coolspend/tests/test_decision_artifact.py -q` — 6/6 PASS
- `python -m pytest coolspend/tests -q` — 88/88 PASS (full suite)
- `python -m coolspend.main` — runs offline, writes `outputs/top3_configurations.json`, `outputs/audit_record.json`, `outputs/pareto_front.png`
- JSON has 3 ranked within-budget configs (DEC-01), `before_after` block (DEC-02), disclaimer on every config (honesty)

---

## Deviations from Plan

### None — plan executed exactly as written.

Minor adaptations (not deviations):
- Print strings use ASCII-only characters (no Unicode euro/degree signs) for Windows cp1252 console compatibility; the JSON artifact itself uses UTF-8 with proper symbols.
- `run_metadata.population` uses the module-level `POP_SIZE` constant (the pymoo Result object does not expose pop_size directly); this is correct for seed-42 deterministic runs.

---

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes at trust boundaries beyond what was planned.

Threats mitigated as designed:
- T-02-15: Every config carries a `disclaimer` key (injected by `save_outputs` if absent from caller)
- T-02-16: JSON written via `json.dump` only; deterministic seed-42 run is reproducible
- T-02-17: API key never reaches `optimizer.py` or `main.py` (stays in `sdk_client` live branch)
- T-02-18: `plot_pareto` wrapped — JSON written even if matplotlib fails

---

## Known Stubs

None that block plan goals. The mock UTCI delta (1.41 °C, synthetic) is documented with a disclaimer and will be replaced by real Infrared SDK values when `INFRARED_BACKEND=live` is used after May 27.

---

## Self-Check: PASSED

- `coolspend/optimizer.py` contains `def topsis_rank`: YES
- `coolspend/optimizer.py` contains `def save_outputs`: YES
- `coolspend/optimizer.py` contains `before_after`: YES (in `_build_before_after` and `save_outputs`)
- `coolspend/main.py` contains `def main`: YES
- `coolspend/main.py` contains `validate_top3_with_infrared`: YES
- `outputs/top3_configurations.json` exists and parses: YES (3 configs, before_after, disclaimers)
- `outputs/audit_record.json` exists: YES
- `outputs/pareto_front.png` exists: YES
- All 88 tests pass: YES
- Commits 353796d, a6e849f, 1c8972a, 1bd70a4 exist: YES
