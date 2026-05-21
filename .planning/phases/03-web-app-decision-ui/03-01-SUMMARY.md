---
phase: 03-web-app-decision-ui
plan: "01"
subsystem: app_pipeline + app_viz
tags: [pipeline, visualization, geojson, matplotlib, sdk-call-log, honesty]
dependency_graph:
  requires:
    - coolspend.optimizer (run_optimisation, select_top3, validate_top3_with_infrared, topsis_rank)
    - coolspend.sdk_client (SimBudget, coolspend.sdk_client logger)
    - coolspend.spatial_engine (load_site, DEFAULT_SITE, SITE_WIDTH_M, SITE_DEPTH_M)
  provides:
    - coolspend.app_pipeline.run_decision (UI-agnostic pipeline wrapper)
    - coolspend.app_pipeline.parse_site_geojson (safe GeoJSON parse, no eval)
    - coolspend.app_viz.render_before_after (headless matplotlib before/after PNG)
  affects:
    - Phase 03-02 (Gradio app wires these contracts to UI components)
tech_stack:
  added: [matplotlib Agg backend, tempfile, logging.Handler subclass]
  patterns:
    - TDD (RED/GREEN commits for each task)
    - Logging capture handler attached to named logger for observable SDK calls
    - Environment variable flip+restore in finally block (INFRARED_BACKEND isolation)
    - GeoJSON parse via json.loads only (T-03-01 security boundary)
key_files:
  created:
    - coolspend/app_pipeline.py
    - coolspend/app_viz.py
    - coolspend/tests/test_app_pipeline.py
    - coolspend/tests/test_app_viz.py
  modified: []
decisions:
  - "Logger level temporarily set to INFO on coolspend.sdk_client for capture handler (root logger at WARNING suppressed INFO otherwise — Rule 1 auto-fix)"
  - "render_before_after accepts before_after dict keys chosen_validated_utci_c and headline_delta_utci_c matching run_decision contract"
  - "parse_site_geojson raises ValueError on invalid input (caller catches and sets error field) — clean separation of concerns"
metrics:
  duration_minutes: 5
  completed_date: "2026-05-21"
  tasks_completed: 2
  files_created: 4
  tests_added: 16
  tests_total_after: 99
---

# Phase 3 Plan 01: app_pipeline.run_decision + app_viz.render_before_after Summary

**One-liner:** UI-agnostic pipeline wrapper with safe GeoJSON parse, SDK call-log capture via logging handler, and headless matplotlib before/after UTCI site map.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for run_decision | 0cdb1a4 | coolspend/tests/test_app_pipeline.py |
| 1 (GREEN) | Implement app_pipeline.run_decision | 098f1e3 | coolspend/app_pipeline.py |
| 2 (RED) | Failing tests for render_before_after | 7e6dc16 | coolspend/tests/test_app_viz.py |
| 2 (GREEN) | Implement app_viz.render_before_after | 67fbb17 | coolspend/app_viz.py |

## Verification

```
python -m pytest coolspend/tests/test_app_pipeline.py coolspend/tests/test_app_viz.py -q
# 16 passed

python -m pytest coolspend/tests -q --ignore=coolspend/tests/test_sdk_client_live.py
# 99 passed, 0 failed

python -c "from coolspend.app_pipeline import run_decision; r=run_decision(); print(len(r['configurations']), len(r['call_log']), r['backend'])"
# 3 3 mock
```

## Success Criteria Status

- [x] run_decision() runs full pipeline offline on mock, no API key, returns documented dict
- [x] GeoJSON paste parsed safely (json.loads only); bad input -> error string + default fixture, no crash
- [x] Infrared SDK calls captured into call_log (>=3 entries for mock run — proves visible API calls)
- [x] render_before_after() produces headless PNG with baseline vs intervention UTCI + headline delta + honesty caption

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Logger level blocked INFO capture from SimBudget**
- **Found during:** Task 1 GREEN phase (8/10 tests passing, call_log was empty)
- **Issue:** `logging.getLogger("coolspend.sdk_client").getEffectiveLevel()` returned 30 (WARNING) because the root logger is at WARNING by default. SimBudget logs at INFO (20). Attaching a handler to the sdk_logger was insufficient — records were filtered before reaching the handler.
- **Fix:** Temporarily set `sdk_logger.setLevel(logging.INFO)` before attaching the capture handler; restore the original level (`prior_sdk_level`) in the `finally` block. This is minimal, scoped, and side-effect-free.
- **Files modified:** coolspend/app_pipeline.py
- **Commit:** 098f1e3 (included inline in GREEN commit)

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| Task 1 RED | 0cdb1a4 | PASS — all 10 tests failed with ModuleNotFoundError |
| Task 1 GREEN | 098f1e3 | PASS — all 10 tests pass after implementation |
| Task 2 RED | 7e6dc16 | PASS — all 6 tests failed with ModuleNotFoundError |
| Task 2 GREEN | 67fbb17 | PASS — all 6 tests pass after implementation |

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what the plan's threat model covers. parse_site_geojson uses json.loads only (T-03-01 mitigated). INFRARED_API_KEY never accessed (T-03-03 mitigated). SimBudget caps calls (T-03-02 mitigated). call_log contains only SimBudget labels, no secrets (T-03-04 accepted).

## Known Stubs

None — all values read directly from optimizer/SDK output fields. No placeholder text or hardcoded empty values flow to the UI layer.

## Self-Check: PASSED

Files created:
- coolspend/app_pipeline.py: EXISTS
- coolspend/app_viz.py: EXISTS
- coolspend/tests/test_app_pipeline.py: EXISTS
- coolspend/tests/test_app_viz.py: EXISTS

Commits verified:
- 0cdb1a4: test(03-01) RED app_pipeline
- 098f1e3: feat(03-01) GREEN app_pipeline
- 7e6dc16: test(03-01) RED app_viz
- 67fbb17: feat(03-01) GREEN app_viz
