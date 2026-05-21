---
phase: 03-web-app-decision-ui
plan: "03"
subsystem: deployability
tags: [hf-spaces, gradio, requirements, readme, dependency-contract]
dependency_graph:
  requires: [03-01, 03-02]
  provides: [APP-02, SHIP-01-forward-compatible]
  affects: [coolspend/tests/, requirements.txt, README.md]
tech_stack:
  added: [geojson>=3.0,<4.0, huggingface_hub==0.36.2]
  patterns: [HF Spaces YAML front-matter, dependency-contract test, clean-venv verification]
key_files:
  created:
    - requirements.txt
    - README.md
    - coolspend/tests/test_requirements.py
  modified: []
decisions:
  - "huggingface_hub==0.36.2 pin required: gradio 4.44.1 imports HfFolder which was removed in huggingface_hub 1.x — adding the pin to requirements.txt fixes clean-venv install"
  - "app_file: coolspend/app.py in Spaces header — no root shim needed; HF Spaces resolves module path from the header directly"
  - "geojson not installed in dev env but listed in requirements.txt per PROJECT.md SHIP-01 — clean-venv install confirms it resolves correctly"
  - "numpy>=1.26,<2.0 constraint retained per plan spec for broad HF Spaces compatibility — pymoo 0.6.1 works with numpy 1.26.x confirmed in clean venv"
metrics:
  duration: 8m
  completed: 2026-05-21
  tasks: 2
  files: 3
---

# Phase 03 Plan 03: HF Spaces Deployability Summary

Pinned requirements.txt (pymoo 0.6.1 + gradio 4.44.1 + huggingface_hub 0.36.2 + shapely/numpy/matplotlib/geojson/infrared-sdk) with clean-venv verification; README with Gradio Spaces YAML front-matter (sdk: gradio, sdk_version: 4.44.1, app_file: coolspend/app.py) + deploy instructions + mock/live distinction; and a 15-test dependency-contract suite that guards against drift between the gradio pin and sdk_version.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | requirements.txt — pin HF-Spaces dependency set | 4ffac59 | requirements.txt |
| 2 | README Spaces header + deploy steps + test_requirements.py | 0d5be3a | README.md, coolspend/tests/test_requirements.py |

## Verification Results

- Clean venv install: all packages resolve without conflict (`pymoo 0.6.1`, `numpy 1.26.4`, `gradio 4.44.1`)
- `python -m pytest coolspend/tests/test_requirements.py -q`: **15 passed**
- Full suite `python -m pytest coolspend/tests/ -q`: **122 passed, 1 skipped** (launch smoke skips on Windows — expected)
- README.md opens with YAML `---` header; contains `sdk: gradio`, `app_file: coolspend/app.py`, `sdk_version: 4.44.1`

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| huggingface_hub==0.36.2 added to requirements.txt | gradio 4.44.1 imports `HfFolder` removed in huggingface_hub 1.x — same pin already in STATE.md from 03-02 |
| No root-level app.py shim created | HF Spaces supports `app_file: coolspend/app.py` directly; no shim needed |
| numpy>=1.26,<2.0 constraint | Broad HF Spaces compatibility; pymoo 0.6.1 runs cleanly with numpy 1.26.x in clean venv |
| geojson>=3.0,<4.0 pinned | Listed per PROJECT.md/SHIP-01 even though no `import geojson` in codebase (GeoJSON parsed via `json`); installs cleanly |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical dependency] huggingface_hub==0.36.2 pin added**
- **Found during:** Task 1 — clean venv verification
- **Issue:** gradio 4.44.1 imports `HfFolder` from `huggingface_hub`, which was removed in 1.x; clean venv installed 1.6.0 and raised `ImportError`
- **Fix:** Added `huggingface_hub==0.36.2` to requirements.txt (consistent with decision already in STATE.md from plan 03-02)
- **Files modified:** requirements.txt
- **Commit:** 4ffac59

## Known Stubs

None. requirements.txt, README.md, and test_requirements.py are complete and functional. The live deploy (public HF Space + INFRARED_API_KEY) is documented as the user's final step — not a stub.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: info-disclosure | README.md | Public README instructs users to set INFRARED_API_KEY as a Space Secret — mitigated by explicit "Never commit the key" instruction (T-03-09) |

T-03-10 (dependency tampering) mitigated by pinned versions + drift-guard test.
T-03-11 (mock vs live repudiation) mitigated by explicit "mock = NOT MEASURED DATA / live = real" language in README.

## Self-Check: PASSED

- requirements.txt: EXISTS at repo root
- README.md: EXISTS at repo root, starts with `---`, contains `sdk: gradio`, `app_file: coolspend/app.py`, `sdk_version: 4.44.1`
- coolspend/tests/test_requirements.py: EXISTS, 15 tests pass
- Commit 4ffac59: FOUND in git log
- Commit 0d5be3a: FOUND in git log
