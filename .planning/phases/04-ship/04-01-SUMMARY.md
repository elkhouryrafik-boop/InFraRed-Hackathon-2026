---
phase: 04-ship
plan: "01"
subsystem: documentation
tags: [ship, docs, requirements, readme, mocks, architecture]
dependency_graph:
  requires: []
  provides: [verified-requirements, architecture-diagram, audited-mocks-ledger]
  affects: [README.md, MOCKS.md, requirements.txt]
tech_stack:
  added: []
  patterns: [mermaid-flowchart, honesty-ledger, pip-dry-run-verification]
key_files:
  modified:
    - README.md
    - MOCKS.md
decisions:
  - "requirements.txt verified clean via pip --dry-run; no changes needed (all SHIP-01 packages already pinned)"
  - "README augmented with ## Architecture (mermaid), ## How it works, ## Project structure; broken MOCKS link fixed"
  - "MOCKS.md mock UTCI row rewritten to name shipped constants UTCI_BASELINE_OPEN_C/UTCI_UNDER_CANOPY_C/MOCK_DISCLAIMER"
  - "MOCKS.md surrogate row item renamed to 'MAX_TMRT_REDUCTION_C surrogate' to match grep in spatial_engine.py"
metrics:
  duration: "~15 min"
  completed: "2026-05-21"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 2
---

# Phase 04 Plan 01: Ship Documentation Finalization Summary

One-liner: Verified requirements.txt clean install, augmented README with mermaid architecture diagram (6 modules, surrogate-optimize → validate-Top-3 → rank pipeline), fixed broken MOCKS link, and audited MOCKS.md so every shipped constant has a grep-verifiable row.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Verify requirements.txt installs clean (SHIP-01) | N/A (no file changes) | requirements.txt (verified, unchanged) |
| 2 | Augment README with architecture diagram, how-it-works, project structure, fix MOCKS link | b10b20d | README.md |
| 3 | Audit and finalize MOCKS.md against shipped code | 08c177f | MOCKS.md |

## Verification Results

### Task 1: requirements.txt (SHIP-01)

`pip install --dry-run -r requirements.txt` resolved with no conflicts. Output: "Would install geojson-3.2.0 infrared-sdk-0.4.7 numpy-1.26.4 validators-0.35.0" — no ERROR, no conflict lines. All SHIP-01 required packages confirmed present:
- `pymoo==0.6.1` — pinned
- `gradio==4.44.1` — pinned
- `shapely>=2.0,<3.0` — range-pinned
- `numpy>=1.26,<2.0` — range-pinned
- `geojson>=3.0,<4.0` — range-pinned
- `infrared-sdk` — unpinned (floated, lazy import)
- `matplotlib>=3.7,<4.0` — range-pinned
- `huggingface_hub==0.36.2` — pinned (gradio==4.44.1 constraint)

No INFRARED_API_KEY or secret string present. File unchanged.

### Task 2: README.md (SHIP-02)

All acceptance criteria verified via Python string checks:
- `## Architecture` heading present with ```mermaid fenced block
- `## How it works` heading present with honesty caveats (mock, surrogate, €/°C REQUIRES_VERIFICATION)
- `## Project structure` heading present with annotated 9-item tree
- All six shipped modules named in diagram: `sdk_client`, `spatial_engine`, `rules_engine`, `cost_model`, `optimizer`, `app`
- MOCKS link fixed: `[MOCKS.md](MOCKS.md)` (repo root); `coolspend/MOCKS.md` string absent
- HF Spaces YAML header (lines 1–10) intact
- Existing Run/Deploy/Live sections preserved (no duplication)
- `MAX_TMRT_REDUCTION` in existing honesty paragraph corrected to `MAX_TMRT_REDUCTION_C`
- No API key or secret string added

### Task 3: MOCKS.md (SHIP-02)

All acceptance criteria verified:
- `MAX_TMRT_REDUCTION_C` present (item column: "MAX_TMRT_REDUCTION_C surrogate") — matches `grep MAX_TMRT_REDUCTION_C coolspend/spatial_engine.py`
- `UTCI_BASELINE_OPEN_C=41.0`, `UTCI_UNDER_CANOPY_C=30.5`, `MOCK_DISCLAIMER` named in mock UTCI row item
- `TREE_SHADE_FRACTION`, `TREE_CANOPY_RADIUS_M` present (spatial_engine.py row)
- `MIN_SPACING_M`, `SPECIES_PALETTE` present (rules_engine.py row)
- `CAPEX_PER_TREE_EUR`, `OPEX_PER_TREE_YEAR_EUR`, `OPEX_HORIZON_YEARS` present (cost_model.py row)
- `TOPSIS` weights (0.6/0.4) present (optimizer.py row) — marked Adjustable
- `angels_site.geojson` MOCK row present
- live UTCI / `_live_utci` VERIFIED(live) row present
- surrogate outputs in top3_configurations.json MOCK/SURROGATE row present
- Table has 11 lines (header + separator + 9 data rows) — exceeds >= 10 requirement
- Honesty trio explicit: "±4 degC uncertainty", "UNSOURCED" cap, TOPSIS "Adjustable parameters"
- No fabricated citations; Garcia-Nevado/Vanos citation-mismatch disclosure preserved
- `REQUIRES_VERIFICATION` present (multiple rows)

### Full pytest suite

```
122 passed, 1 skipped in 23.15s
```

Suite is green. Doc-only changes do not affect runtime behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale MAX_TMRT_REDUCTION reference in existing README honesty paragraph**
- **Found during:** Task 2
- **Issue:** README honesty paragraph referred to `` `MAX_TMRT_REDUCTION` `` (missing `_C` suffix), inconsistent with shipped constant name `MAX_TMRT_REDUCTION_C` in `spatial_engine.py`
- **Fix:** Corrected to `` `MAX_TMRT_REDUCTION_C` `` in the existing paragraph
- **Files modified:** README.md
- **Commit:** b10b20d

None beyond the above minor name correction — plan executed as written.

## Known Stubs

None. This plan is documentation-only; no stubs introduced.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All three files (requirements.txt, README.md, MOCKS.md) confirmed free of API keys or secret strings. T-04-01 and T-04-02 mitigations applied.

## Self-Check: PASSED

- [x] `.planning/phases/04-ship/04-01-SUMMARY.md` created
- [x] Commit `b10b20d` exists (README augmentation)
- [x] Commit `08c177f` exists (MOCKS.md audit)
- [x] requirements.txt unchanged, dry-run clean
- [x] README passes all 12 acceptance criteria checks
- [x] MOCKS.md passes all 15 acceptance criteria checks
- [x] pytest: 122 passed, 1 skipped
