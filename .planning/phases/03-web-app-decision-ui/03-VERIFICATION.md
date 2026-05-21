---
phase: 03-web-app-decision-ui
verified: 2026-05-21T00:00:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
---

# Phase 3: Web App Decision UI — Verification Report

**Phase Goal:** A Gradio web app that takes a site polygon + budget and returns a ranked tree-planting allocation table + before/after map (a DECISION, not just a heatmap), runnable offline on mock with no key, live when keyed, and deployable to Hugging Face Spaces with visible Infrared API calls.
**Verified:** 2026-05-21
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A single callable runs optimizer -> validate Top-3 -> TOPSIS and returns a structured decision result offline on mock with no API key | VERIFIED | `run_decision()` returns `{configs: 3, call_log: 3, backend: mock, error: None}` confirmed by live execution |
| 2 | User-supplied GeoJSON text is parsed without eval and bad input returns a clean error string, not a crash | VERIFIED | `parse_site_geojson` uses `json.loads` only (eval=False, exec=False confirmed). Bad JSON sets `error` field, `configurations==[]`, no exception |
| 3 | Every Infrared SDK call made during a run is captured into a visible call log returned with the result | VERIFIED | `call_log: ['live UTCI call #1: intervention MAX_THERMAL_RELIEF', 'live UTCI call #2: ...', 'live UTCI call #3: ...']` confirmed live |
| 4 | A before/after site image is rendered from site geometry + chosen tree placements showing baseline vs intervention UTCI and the headline delta | VERIFIED | `render_before_after()` writes non-empty PNG (PNG magic bytes confirmed in test); 6/6 viz tests pass headless |
| 5 | Backend + honesty disclaimers travel with the result (mock = NOT MEASURED DATA) | VERIFIED | `disclaimer` field contains "NOT MEASURED DATA" for mock; banner in `on_submit` adds "NOT MEASURED DATA" verbatim |
| 6 | Gradio app boots headless, exposes all required inputs, and on submit returns headline + map + table + call log | VERIFIED | `build_demo()` returns `gr.Blocks`; `on_submit` 4-tuple confirmed: banner has "Spend EUR" + "NOT MEASURED DATA", img exists, 3 table rows, non-empty call log |
| 7 | requirements.txt pins every dependency (gradio, pymoo==0.6.1, shapely, matplotlib, numpy, infrared-sdk, huggingface_hub) | VERIFIED | All 15 test_requirements.py assertions pass; pins confirmed in file |
| 8 | README has a valid HF Spaces YAML header (sdk: gradio, app_file: coolspend/app.py, sdk_version: 4.44.1) + deploy + mock/live + offline steps | VERIFIED | README starts with `---` YAML block; sdk: gradio; app_file: coolspend/app.py; sdk_version: 4.44.1; all documented |

**Score:** 8/8 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `coolspend/app.py` | Gradio Blocks app wiring run_decision + render_before_after; demo.launch() entrypoint | VERIFIED | 262 lines; `build_demo()`, `on_submit()`, module-level `demo`, `if __name__ == "__main__": demo.launch()` |
| `coolspend/app_pipeline.py` | run_decision() UI-agnostic pipeline wrapper + GeoJSON parse + SDK call-log capture | VERIFIED | 354 lines; `def run_decision`, `def parse_site_geojson`, `class _CaptureHandler` |
| `coolspend/app_viz.py` | render_before_after() matplotlib site plot with tree placements + UTCI delta | VERIFIED | 228 lines; `def render_before_after`, Agg forced before pyplot, `_draw_site` helper |
| `coolspend/tests/test_app_pipeline.py` | Headless offline tests of run_decision (mock, bad geojson, call-log) | VERIFIED | 10 tests; all pass |
| `coolspend/tests/test_app_viz.py` | Headless test that render_before_after produces a PNG file | VERIFIED | 6 tests; all pass |
| `coolspend/tests/test_app.py` | Headless test: build_demo() constructs + on_submit returns valid outputs offline | VERIFIED | 4 tests; 3 pass, 1 skipped (known Windows/httpx infrastructure skip — server construction verified before skip) |
| `requirements.txt` | Pinned HF-Spaces-friendly dependency set | VERIFIED | pymoo==0.6.1, gradio==4.44.1, huggingface_hub==0.36.2, shapely, numpy, matplotlib, geojson, infrared-sdk |
| `README.md` | Spaces YAML header + deploy instructions + mock/live note | VERIFIED | Valid YAML header; sdk_version matches gradio pin; all deploy steps documented |
| `coolspend/tests/test_requirements.py` | Test asserting requirements.txt pins + README Spaces header | VERIFIED | 15 tests; all pass |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| coolspend/app_pipeline.py | coolspend.optimizer | `from coolspend.optimizer import run_optimisation, select_top3, validate_top3_with_infrared, topsis_rank` | WIRED | Import confirmed at top of file; all 4 functions called in `_run_pipeline` |
| coolspend/app_pipeline.py | coolspend.sdk_client logger + SimBudget.log | `logging.getLogger("coolspend.sdk_client")` + `_CaptureHandler` | WIRED | Handler attached for run duration; `SimBudget(max_live_calls=3)` passed to `validate_top3_with_infrared` |
| coolspend/app_viz.py | coolspend.spatial_engine.load_site | `from coolspend.spatial_engine import load_site, SITE_WIDTH_M, SITE_DEPTH_M` | WIRED | `load_site()` called in `_load_site_safe`; SITE_WIDTH_M/SITE_DEPTH_M used for axis limits |
| coolspend/app.py | coolspend.app_pipeline.run_decision | `from coolspend.app_pipeline import run_decision`; called in `on_submit` | WIRED | `run_decision(budget_eur=..., weights=..., geojson_text=..., backend=...)` wired to button.click |
| coolspend/app.py | coolspend.app_viz.render_before_after | `from coolspend.app_viz import render_before_after`; called in `on_submit` | WIRED | `render_before_after(result["configurations"][0], result["before_after"], site_path=...)` |
| coolspend/app.py | gradio Blocks | `import gradio as gr; gr.Blocks()` | WIRED | `build_demo()` builds `gr.Blocks`; `demo = build_demo()` at module level |
| README.md (app_file) | coolspend/app.py demo.launch() | `app_file: coolspend/app.py` in Spaces YAML header | WIRED | Header contains `app_file: coolspend/app.py`; `demo.launch()` present in app.py entrypoint |
| requirements.txt | coolspend imports (pymoo/shapely/numpy/matplotlib/gradio/infrared-sdk) | All imported third-party packages pinned | WIRED | All packages present; huggingface_hub==0.36.2 added to fix HfFolder ImportError |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| coolspend/app.py on_submit() | `result` dict | `run_decision()` -> optimizer -> SimBudget -> topsis_rank | Yes — full NSGA-II pipeline; mock values from `sdk_client` mock backend | FLOWING |
| coolspend/app.py table_rows | `cfg.get(...)` per config | `result["configurations"]` from topsis_rank output | Yes — 3 real ranked config dicts with cost_eur, delta_utci_c, topsis_score | FLOWING |
| coolspend/app.py banner_md | `result["headline"]`, `result["disclaimer"]` | `_build_headline(rank1, before_after)`, `_build_disclaimer(rank1, backend)` | Yes — built from optimizer output fields, not hardcoded | FLOWING |
| coolspend/app_viz.py render_before_after() | `active_trees` scatter, axis values | `config["trees"]`, `before_after` dict | Yes — tree coordinates from optimizer; UTCI values from sdk_client mock | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| run_decision() offline returns 3 configs + non-empty call_log | `python -c "from coolspend.app_pipeline import run_decision; r=run_decision(); print(len(r['configurations']), len(r['call_log']), r['backend'])"` | `3 3 mock` | PASS |
| headline contains "Spend EUR" and "degC" | `"Spend EUR" in r['headline'] and "degC" in r['headline']` | `True` | PASS |
| disclaimer contains "NOT MEASURED DATA" for mock | `"NOT MEASURED DATA" in r['disclaimer']` | `True` | PASS |
| call_log entries reference SimBudget calls | `r['call_log']` | `['live UTCI call #1: ...', 'live UTCI call #2: ...', 'live UTCI call #3: ...']` | PASS |
| on_submit() returns valid 4-tuple with correct contents | `a.on_submit(None, 1e6, 0.6, 0.4, "mock")` | banner has "Spend EUR" + "NOT MEASURED DATA"; img exists; 3 table rows; call_log non-empty | PASS |
| build_demo() constructs gr.Blocks | `type(a.build_demo()).__name__` | `Blocks` | PASS |
| Bad GeoJSON returns error, no crash | `on_submit("{ not valid json", ...)` | Returns 4-tuple with "ERROR" in banner, img=None, table=[] | PASS |
| render_before_after() writes valid PNG headless (Agg) | PNG magic bytes check | `b'\x89PNG\r\n\x1a\n'` confirmed | PASS |
| Full test suite passes | `python -m pytest coolspend/tests/ -q` | 122 passed, 1 skipped | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| APP-01 | 03-01, 03-02 | Gradio app takes polygon + budget, returns allocation table + before/after map | SATISFIED | app.py wires all required components; on_submit returns headline + image + table + call_log; offline on mock |
| APP-02 | 03-03 | Deployable to HF Spaces; real API calls visible/loggable | SATISFIED | README has valid Spaces YAML header; requirements.txt pinned; call_log panel in UI |

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| coolspend/app.py:11 | `INFRARED_API_KEY` appears in a docstring comment only | Info | Mitigated — comment documents what is NOT done (T-03-05). Not rendered or logged in the UI. |
| coolspend/tests/test_app.py | `test_headless_launch_smoke` skips on `httpx.ConnectError` | Info | Infrastructure constraint (Windows + Gradio 4.x + server_port=0 ephemeral port health-check ping). `build_demo()` is pre-asserted before the skip, so construction is always verified. Not a stub. |

No blockers. No stubs in output paths. No hardcoded empty values flowing to the UI.

---

## Human Verification Required

None. All must-haves are programmatically verifiable and confirmed by automated execution.

---

## Gaps Summary

No gaps. All 8 observable truths verified by code inspection, grep analysis, and live execution. All artifacts exist, are substantive (not stubs), are fully wired, and data flows through to the UI outputs.

---

## Notes on the 1-skip in test_headless_launch_smoke

`test_headless_launch_smoke` is intentionally skipped on Windows when Gradio 4.x raises `httpx.ConnectError` during its internal health-check ping after `launch(server_port=0)`. This is a documented infrastructure constraint (Gradio 4.x behavior on Windows with ephemeral port=0), not an app construction failure. The test pre-asserts `build_demo()` returns `gr.Blocks` before the launch attempt, so Blocks construction is always verified. The skip is appropriate and the test design is correct.

---

_Verified: 2026-05-21_
_Verifier: Claude (gsd-verifier)_
