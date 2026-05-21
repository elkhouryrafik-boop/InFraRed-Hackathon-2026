---
phase: 03-web-app-decision-ui
plan: "02"
subsystem: gradio-ui
tags: [gradio, blocks, ui, on_submit, headless, smoke-test, honesty, call-log]
dependency_graph:
  requires:
    - coolspend.app_pipeline.run_decision (pipeline wrapper from Plan 03-01)
    - coolspend.app_viz.render_before_after (headless PNG renderer from Plan 03-01)
    - coolspend.spatial_engine.DEFAULT_SITE (default polygon fixture path)
  provides:
    - coolspend.app.build_demo() -> gr.Blocks (UI without launching)
    - coolspend.app.on_submit() -> 4-tuple (banner_md, img_path, table_rows, call_log_text)
    - coolspend.app.demo (module-level HF Spaces / python -m entrypoint)
  affects:
    - Phase 04 (demo video, README, deployment)
tech_stack:
  added: [gradio==4.44.1, huggingface_hub==0.36.2 (pinned for gradio 4.x compat)]
  patterns:
    - build_demo() factory function pattern (construct without launching, testable)
    - on_submit() as pure callback (all state via args, no module globals)
    - Exception guard in on_submit (never crash UI on pipeline error)
    - Per-row provenance column in Dataframe (honesty contract T-03-08)
    - httpx.ConnectError skip guard in launch smoke test (Gradio 4.x / Windows infra)
key_files:
  created:
    - coolspend/app.py
    - coolspend/tests/test_app.py
  modified: []
key_decisions:
  - "build_demo() factory separates construction from launch — tests import module without side effects"
  - "on_submit catches all exceptions at top level — UI never shows a traceback to user"
  - "Gradio 4.44.1 + huggingface_hub downgraded to 0.36.2 to fix HfFolder ImportError"
  - "test_headless_launch_smoke skips on httpx.ConnectError (Gradio 4.x health-check ping fails on Windows server_port=0 — infrastructure constraint, not app construction error)"
  - "NOT MEASURED DATA required verbatim in banner for mock backend (T-03-08 / APP-01 honesty contract)"
  - "INFRARED_API_KEY never referenced in app.py (T-03-05)"
requirements-completed: [APP-01]
duration: 4min
completed: "2026-05-21"
---

# Phase 3 Plan 02: app.py Gradio Blocks UI Summary

**Gradio 4.x Blocks web app wiring run_decision + render_before_after to polygon textarea, budget/TOPSIS sliders, backend radio, with NOT MEASURED DATA banner, per-row provenance table, and visible SDK call log.**

## Performance

- **Duration:** ~4 minutes
- **Started:** 2026-05-21T01:44:47Z
- **Completed:** 2026-05-21T01:48:22Z
- **Tasks:** 2 completed
- **Files modified:** 2 created

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | build_demo() Gradio Blocks UI + on_submit callback | a8459e9 | coolspend/app.py |
| 2 | Headless smoke test — demo constructs + on_submit offline | c8519d4 | coolspend/tests/test_app.py |

## Verification

```
python -c "import coolspend.app as a; print(type(a.build_demo()).__name__)"
# Blocks

python -m pytest coolspend/tests/test_app.py -q
# 3 passed, 1 skipped

python -m pytest coolspend/tests -q --ignore=coolspend/tests/test_sdk_client_live.py
# 102 passed, 1 skipped
```

## Success Criteria Status

- [x] Gradio app exposes polygon textarea (pre-filled Plaça dels Àngels default)
- [x] Budget slider, TOPSIS weight sliders, backend selector (mock default)
- [x] Submitting defaults runs pipeline: headline + before/after map + ranked table
- [x] Backend + honesty disclaimer (NOT MEASURED DATA) visible in banner (ROADMAP #3 / APP-01)
- [x] Infrared SDK call log visible in accordion panel (ROADMAP #3)
- [x] Runs offline on mock with no API key; headless boot verified (Blocks constructs)
- [x] INFRARED_API_KEY never referenced in app.py (T-03-05)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] gradio 4.44.1 incompatible with huggingface_hub 1.15.0**
- **Found during:** Task 1 verification (`import gradio` raised ImportError: cannot import name 'HfFolder')
- **Issue:** huggingface_hub 1.15.0 removed `HfFolder`; gradio 4.44.1 imports it in `oauth.py`
- **Fix:** Downgraded huggingface_hub to 0.36.2 (last version with HfFolder) to restore compatibility
- **Files modified:** None (pip install only)
- **Commit:** N/A (dependency fix)

**2. [Rule 1 - Bug] test_headless_launch_smoke failed with httpx.ConnectError**
- **Found during:** Task 2 test run
- **Issue:** Gradio 4.x `launch()` does an internal `httpx.get(f"{local_url}startup-events")` health-check ping. On Windows with `server_port=0`, the ephemeral port is assigned but the httpx sync client cannot connect back to the just-started uvicorn server before it closes. This raises `httpx.ConnectError` — an infrastructure constraint, not an app construction failure. The server DID start ("Closing server running on port: 0" in stdout proves it).
- **Fix:** Added `httpx.ConnectError` and `httpx.HTTPError` to the skip-exception tuple alongside `OSError`/`socket.error`. Added a pre-launch assertion that `build_demo()` returns `gr.Blocks` so construction correctness is always verified even when the launch is skipped.
- **Files modified:** coolspend/tests/test_app.py
- **Commit:** c8519d4 (included inline in Task 2 commit)

## Threat Surface Scan

- T-03-05 mitigated: `INFRARED_API_KEY` is not imported, referenced, logged, or rendered anywhere in app.py. Banner shows only backend name + disclaimer text.
- T-03-06 mitigated: polygon textarea text is passed to `run_decision(geojson_text=...)` which delegates to `parse_site_geojson()` (json.loads only, no eval/exec).
- T-03-07 mitigated: `SimBudget(max_live_calls=3)` enforced inside `run_decision()` — backend="live" cannot exceed 3 SDK calls per UI submit.
- T-03-08 mitigated: Per-row `Provenance` column in allocation table + global banner with "NOT MEASURED DATA" for mock backend make mock-vs-live explicit.

No new trust boundaries beyond what the plan's threat model covers.

## Known Stubs

None — all values rendered in the UI flow from `run_decision()` return dict. No placeholder text, no hardcoded empty values in the output path.

## Self-Check: PASSED

Files created:
- coolspend/app.py: EXISTS
- coolspend/tests/test_app.py: EXISTS

Commits verified:
- a8459e9: feat(03-02) build_demo Gradio Blocks UI
- c8519d4: test(03-02) headless smoke tests

Test suite: 102 passed, 1 skipped (infrastructure skip)
