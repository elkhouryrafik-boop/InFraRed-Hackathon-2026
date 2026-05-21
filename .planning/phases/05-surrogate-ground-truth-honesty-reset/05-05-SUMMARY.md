---
phase: 05-surrogate-ground-truth-honesty-reset
plan: "05"
subsystem: docs, ui
tags: [honesty, overclaim-scrub, UTCI, KPI, citations, out-of-scope]

# Dependency graph
requires:
  - phase: 05-surrogate-ground-truth-honesty-reset
    provides: "Plans 02/04 — cost_per_utci_degree with value_lo/value_hi/band_source, naive-baseline deletion (D-12), code-side citation re-anchor (D-13)"

provides:
  - "All four prose surfaces scrubbed: CONCEPT_REPORT.md, README.md, DEMO_SCRIPT.md, SUBMISSION.md"
  - "MOCKS.md re-anchored: Schrodi 2023 (arXiv:2310.05691, venue PENDING) + Rahman 2022 (DOI PENDING); naive row tombstoned (REMOVED); no fabricated DOIs"
  - "Out-of-scope exclusions list (six items + geometric feasibility framing) in README.md and CONCEPT_REPORT.md (HONEST-04/D-14)"
  - "app.py table surfaces dual-unit interval KPI: EUR/degC [lo-hi] + EUR/UTCI-hr + Band source (D-15/D-09/D-10)"
  - "typer==0.12.5 pin fixes pre-existing test infrastructure breakage (all 20 app tests passing)"

affects: [phase-06-cost, phase-07-geometry, external-reviewers, judges]

# Tech tracking
tech-stack:
  added: ["typer==0.12.5 pin (requirements.txt)"]
  patterns: ["KPI always displayed as [lo, hi] interval with band_source label — never bare point estimate (D-15)"]

key-files:
  created: [".planning/phases/05-surrogate-ground-truth-honesty-reset/05-05-SUMMARY.md"]
  modified:
    - "CONCEPT_REPORT.md"
    - "README.md"
    - "DEMO_SCRIPT.md"
    - "SUBMISSION.md"
    - "MOCKS.md"
    - "coolspend/app.py"
    - "requirements.txt"

key-decisions:
  - "D-11 app surface: app.py table columns expanded to 10 (added EUR/UTCI-hr, Band source, [lo-hi] interval) — reads from KPI dict, never hardcoded"
  - "D-13 docs: MOCKS.md row updated with Schrodi arXiv ID + PENDING tags; Garcia-Nevado demoted; no fabricated DOIs"
  - "D-14: Out-of-scope exclusions list added verbatim to both README.md and CONCEPT_REPORT.md"
  - "Rule 3 auto-fix: pinned typer==0.12.5 to resolve pre-existing click 8.1.7 incompatibility that was blocking test suite"

patterns-established:
  - "KPI interval pattern: always read value_lo/value_hi/band_source from cost dict; format as 'X.XX [lo-hi]'"
  - "Out-of-scope exclusions canonical list maintained in README.md; mirrored in CONCEPT_REPORT.md"

requirements-completed: [HONEST-01, HONEST-02, HONEST-03, HONEST-04]

# Metrics
duration: 8min
completed: 2026-05-21
---

# Phase 5 Plan 05: Prose Overclaim Scrub + Honesty UI Summary

**Scrubbed CFD/permaculture/88%-naive overclaims from all four prose surfaces, re-anchored MOCKS.md to Schrodi 2023 (arXiv:2310.05691), added six-item out-of-scope list, and surfaced the EUR/degC [lo-hi] interval + EUR/UTCI-hr dual-unit KPI in the Gradio table.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-21T16:55:03Z
- **Completed:** 2026-05-21T17:00:46Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- CONCEPT_REPORT.md aligned down to MOCKS.md: removed "professional-grade CFD", "permaculture engine", "energy exchange"; Infrared described as "fast urban microclimate API"; final picks framed as "re-simulated with Infrared UTCI" (HONEST-01/03)
- MOCKS.md surrogate row re-anchored to Schrodi 2023 (arXiv:2310.05691, venue PENDING) + Rahman 2022 (DOI PENDING) with Garcia-Nevado 2020 demoted to surface-temp analogue; naive-baseline row tombstoned as REMOVED (D-12/D-13); no fabricated DOIs
- README.md, DEMO_SCRIPT.md, SUBMISSION.md: "88% vs naive" figure and "validated with Infrared" phrasing removed entirely; replaced with honest interval KPI + "re-simulated with Infrared UTCI" framing (HONEST-03, D-12)
- Out-of-scope exclusions list (six items + "geometric feasibility, not engineering siting sign-off") added to both README.md and CONCEPT_REPORT.md (HONEST-04/D-14)
- app.py table expanded to 10 columns surfacing EUR/degC [lo-hi] interval, EUR/UTCI-hr secondary unit, and Band source label read from the KPI dict (D-15/D-09/D-10); no validated/88% strings in any app file

## Task Commits

1. **Task 1: Scrub prose overclaims + re-anchor MOCKS.md citation** - `eadc916` (docs)
2. **Task 2: Out-of-scope exclusions + app UI interval KPI + typer fix** - `9380ee8` (feat)

**Plan metadata:** (final commit below)

## Files Created/Modified

- `CONCEPT_REPORT.md` - Removed CFD/permaculture/energy-exchange overclaims; added out-of-scope section; aligned to MOCKS.md (HONEST-01)
- `README.md` - "validated" -> "re-simulated with Infrared UTCI"; added Out-of-Scope section with six items + geometric feasibility framing (HONEST-03/04)
- `DEMO_SCRIPT.md` - Removed "88% cheaper per degree than the naive" from shot 7 and The Close narration (D-12)
- `SUBMISSION.md` - Removed "88% improvement" / naive-grid comparison from real-world impact; updated one-line pitch (D-12/HONEST-03)
- `MOCKS.md` - Surrogate row: Schrodi 2023 arXiv:2310.05691 + Rahman 2022 (PENDING) anchor; Garcia-Nevado demoted; naive row tombstoned REMOVED (D-13/D-12)
- `coolspend/app.py` - Table headers expanded (10 cols); EUR/degC shown as "[lo-hi]" interval; EUR/UTCI-hr + Band source columns added; reads from KPI dict (D-15/D-09)
- `requirements.txt` - typer==0.12.5 pin (Rule 3: pre-existing breakage)

## Decisions Made

- Expanded app.py table to 10 columns rather than adding a separate panel — keeps the allocation table self-contained with full KPI provenance visible inline
- CONCEPT_REPORT.md restructured Section 3.3 (renamed from "Permaculture Engine" to "Rule-Based Ecological Scoring"), Section 5 renamed from "Conclusion" to accommodate new out-of-scope section, renumbered original conclusion as Section 6
- MOCKS.md naive row: kept as tombstone row (struck-through) rather than deleted, to preserve the audit trail of what was removed and why

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing typer/click incompatibility blocked test suite**
- **Found during:** Task 2 verification (pytest run)
- **Issue:** typer 0.25.1 uses `click.Choice[T]` generic subscript which is not supported in click 8.1.7 (pulled by gradio 4.44.1). This caused `TypeError: type 'Choice' is not subscriptable` at `import gradio`, making all three test_app*.py modules fail at collection time. This was pre-existing before any Task 2 changes.
- **Fix:** Installed typer==0.12.5 and pinned it in requirements.txt with an explanatory comment
- **Files modified:** `requirements.txt`
- **Verification:** All 20 tests pass (1 headless launch skipped on Windows — expected pre-existing behavior)
- **Committed in:** `9380ee8` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 3 blocking — pre-existing dependency incompatibility)
**Impact on plan:** Auto-fix was a direct blocker for the required test verification step. No scope creep — the typer pin is a maintenance fix enabling tests to run.

## Issues Encountered

None beyond the typer/click incompatibility documented above.

## Known Stubs

None introduced in this plan. All KPI interval fields (value_lo, value_hi, band_source) are read live from the cost_per_utci_degree() result dict, which correctly returns "pre-calibration, assumed ±4°C" as band_source until Plan 05-03 calibration RMSE is available. This is intentional and honest framing, not a stub.

## Threat Flags

No new network endpoints, auth paths, or schema changes introduced. Only documentation and UI display string changes.

## Self-Check

- CONCEPT_REPORT.md exists and contains "re-simulated with Infrared UTCI": confirmed
- README.md contains "out-of-scope" and "geometric feasibility, not engineering siting sign-off": confirmed
- MOCKS.md contains "Schrodi" and "arXiv:2310.05691": confirmed
- MOCKS.md contains no "doi.org/10" fabricated links: confirmed
- coolspend/app.py contains "value_lo", "cost_per_utci_hour", "band_source": confirmed
- All 20 app tests pass: confirmed
- Task 1 commit eadc916 exists: confirmed
- Task 2 commit 9380ee8 exists: confirmed

## Self-Check: PASSED

## Next Phase Readiness

Phase 5 honesty reset is now complete across all surfaces:
- Code side (Plans 02, 04): cost model, naive baseline deletion, citation re-anchor in docstrings
- Docs/UI side (Plan 05): CONCEPT_REPORT, README, DEMO_SCRIPT, SUBMISSION, MOCKS, app.py table
- External reviewers/judges will see no CFD/permaculture/88%-naive overclaims anywhere
- Phase 6 (cost model credibility), Phase 7 (geometry/OSM) can proceed with the honest foundation now established

---
*Phase: 05-surrogate-ground-truth-honesty-reset*
*Completed: 2026-05-21*
