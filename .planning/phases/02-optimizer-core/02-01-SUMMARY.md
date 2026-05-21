---
phase: 02-optimizer-core
plan: "01"
subsystem: rules-engine
tags: [rules-engine, ecology, spacing, diversity, shannon-index, tdd, offline, honesty-ledger]
dependency_graph:
  requires: [01-01 (coolspend package), 01-02 (spatial_engine.py with SITE constants)]
  provides: [rules_engine, spacing_penalty, species_diversity_score, ecological_score, MOCKS.md-row-4]
  affects: [02-03 optimizer (ecological_score is the NSGA-II 2nd objective), 02-04 serialisation (config dict contract)]
tech_stack:
  added: []
  patterns: [pure-deterministic-offline, shannon-index-normalised, tdd-red-green, declared-assumption-constants, honesty-ledger]
key_files:
  created:
    - coolspend/rules_engine.py
    - coolspend/tests/test_rules_engine.py
  modified:
    - MOCKS.md
decisions:
  - "RULES-01 min-spacing penalty uses linear violation depth (min_spacing_m - dist) / min_spacing_m — smooth gradient for NSGA-II"
  - "RULES-02 Shannon index normalised by ln(n_distinct) — monoculture=0.0, balanced N-species=1.0 exactly"
  - "ecological_score combines 50% spacing coherence + 50% diversity — equal weight by design, no calibration data to justify asymmetry"
  - "Pollinator corridor objective explicitly excluded (CONCERNS 1.2) — documented in module docstring, not silently omitted"
  - "MIN_SPACING_M=4.0 and SPECIES_PALETTE tagged SOURCE: DECLARED + REQUIRES_VERIFICATION — no fabricated citation"
metrics:
  duration: "~3 minutes"
  completed: "2026-05-21T00:45:42Z"
  tasks_completed: 1
  files_created: 2
  files_modified: 1
  commits: 2
---

# Phase 02 Plan 01: Rules Engine Summary

**One-liner:** Pure offline ecological-coherence scoring module implementing RULES-01 (min-spacing penalty, linear violation depth) and RULES-02 (normalised Shannon species-diversity index), forming the NSGA-II second objective — with declared constants, pollinator exclusion documented, and 31 deterministic tests green.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | TDD failing tests for spacing_penalty + species_diversity_score | 027aca5 | coolspend/tests/test_rules_engine.py |
| 1 (GREEN) | Implement rules_engine.py — spacing penalty + species diversity + MOCKS.md | 3c89523 | coolspend/rules_engine.py, MOCKS.md |

## Verification Results

- `python -m pytest coolspend/tests/test_rules_engine.py -q` — PASS (31 passed, 0.15s)
- `python -m pytest -q` (full suite) — PASS (53 passed, 0.16s)
- `grep -q "def spacing_penalty" coolspend/rules_engine.py` — PASS
- `grep -q "def species_diversity_score" coolspend/rules_engine.py` — PASS
- `grep -q "CONCERNS 1.2" coolspend/rules_engine.py` — PASS
- `python -m coolspend.rules_engine` smoke test — PASS (close monoculture=0.0833, spaced diverse=1.0000)
- No `import infrared` / `import requests` / `import httpx` in rules_engine.py — CONFIRMED

## What Was Built

### `coolspend/rules_engine.py` (262 lines)

Pure deterministic offline module. No SDK import, no network calls, no file IO.

**Module-level DECLARED constants:**
- `MIN_SPACING_M: float = 4.0` — minimum crown-clearance between street trees, metres. SOURCE: DECLARED — REQUIRES_VERIFICATION against Barcelona municipal tree-planting code
- `SPECIES_PALETTE: tuple = ("platanus", "celtis", "tilia", "quercus")` — demo resilient species mix. SOURCE: DECLARED — REQUIRES_VERIFICATION against Barcelona Arbrat Viari recommended-species list

**`_active_trees(config: dict) -> list[dict]`:**
Returns `[t for t in config.get("trees", []) if t.get("active", True)]`. Trees without an `"active"` key default to active; `"active": False` slots are excluded (NSGA-II vector convention).

**`spacing_penalty(config: dict, min_spacing_m: float = MIN_SPACING_M) -> float`** (RULES-01):
Pairwise O(n²) Euclidean distance over active trees. For each pair closer than `min_spacing_m` adds `(min_spacing_m - dist) / min_spacing_m` (linear violation depth, clamped to 0). Returns total penalty >= 0.0. 0 or 1 trees → 0.0. Guard: pairs at exact `min_spacing_m` yield 0.0 (max(0.0, ...) clamp). Smoke: 3-tree 0.5m-apart cluster → 2.5 penalty.

**`species_diversity_score(config: dict) -> float`** (RULES-02):
Shannon index H = -sum(p_i * ln(p_i)), normalised by H_max = ln(n_distinct). Monoculture → 0.0 exactly. Balanced N-species mix → 1.0 exactly. Guards: n_distinct < 2 returns 0.0 before the division (ln(1)=0 guard), p_i=0 is structurally impossible (only nonzero counts in dict). Smoke: 4 distinct species, 1 each → score = 1.0.

**`ecological_score(config: dict) -> float`:**
Combined coherence = 0.5 * (1 - min(1.0, spacing_penalty/n_pairs)) + 0.5 * species_diversity_score(config). Returns `round(clamped, 4)`. 0/1 tree → 0.0. This is the NSGA-II second objective passed to Plan 02-03 optimizer.

**`__main__` smoke block:** Compares close-packed monoculture (3 trees, 0.5m apart, all platanus → 0.0833) against well-spaced diverse mix (4 species, 10m apart → 1.0000). Prints all constants with sourcing notes.

### `coolspend/tests/test_rules_engine.py` (321 lines, 31 tests)

31 offline deterministic pytest tests across 5 classes:

| Class | Tests | What is tested |
|-------|-------|----------------|
| TestSpacingPenalty | 11 | positive penalty for close pair, zero for far, monotonicity (twice), zero/one trees, inactive exclusion, formula verification, exact-MIN boundary, custom override |
| TestSpeciesDiversityScore | 8 | monoculture=0, diverse>0, diverse>monoculture, empty=0, single=0, balanced=1, bounded [0,1], unequal 2-species in (0,1) |
| TestEcologicalScore | 6 | finite float, bounded [0,1], deterministic, diverse+spaced > close monoculture, empty=0, rounded to 4dp |
| TestActiveTreesHelper | 3 | default active, inactive excluded, empty config |
| TestModuleConstants | 3 | MIN_SPACING_M=4.0, SPECIES_PALETTE contains required 4 species, no network imports |

### `MOCKS.md` (appended row)

New row for `ecological rules (MIN_SPACING_M, SPECIES_PALETTE)` — status `DECLARED`, explains both constants are unsourced demo assumptions; replacement path points to Barcelona municipal code + Arbrat Viari list.

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED gate: commit `027aca5` — `test(02-01): add failing tests for spacing_penalty + species_diversity_score (RED)` — import failed with `ModuleNotFoundError: No module named 'coolspend.rules_engine'` (confirmed)
- GREEN gate: commit `3c89523` — `feat(02-01): implement rules_engine.py ...` — 31/31 tests pass, 53/53 full suite pass
- REFACTOR gate: not needed (implementation was clean on first pass)

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| MIN_SPACING_M=4.0 | coolspend/rules_engine.py | 52 | DECLARED assumption; no Barcelona municipal spacing code confirmed — MOCKS.md row added |
| SPECIES_PALETTE=("platanus","celtis","tilia","quercus") | coolspend/rules_engine.py | 57 | DECLARED demo mix; not verified against Arbrat Viari recommended list — MOCKS.md row added |

These stubs are intentional and documented per the honesty contract. They do not block Phase 2 optimization (ecological_score is structurally correct; constants need verified sourcing before the final demo claims ecological defensibility).

## Threat Flags

T-02-01 (Tampering — rules_engine inputs): **mitigated** — pure arithmetic; divide-by-zero guards applied (max(1, n_pairs) in ecological_score, n_distinct<2 guard in diversity, max(0.0,...) in spacing). No eval, no string interpolation.

T-02-02 (Information disclosure): **accepted** — no IO, no network, no secrets; pure function module.

T-02-03 (DoS via O(n²) spacing): **accepted** — tree count bounded by NSGA-II vector length (~tens); pairwise loop is negligible.

## Self-Check: PASSED

All created/modified files exist:
- FOUND: coolspend/rules_engine.py
- FOUND: coolspend/tests/test_rules_engine.py
- FOUND: MOCKS.md (ecological rules row appended)
- FOUND: .planning/phases/02-optimizer-core/02-01-SUMMARY.md

All commits verified:
- FOUND: 027aca5 (Task 1 RED — failing tests)
- FOUND: 3c89523 (Task 1 GREEN — rules_engine.py + MOCKS.md)
