---
phase: 04-ship
plan: "02"
subsystem: submission-assets
tags: [ship, demo, submission, changelog, honesty, presentation]
dependency_graph:
  requires: [04-01 (docs finalisation), 03-03 (deployability), 02-05 (decision artifact)]
  provides: [DEMO_SCRIPT.md, SUBMISSION.md, CHANGELOG.md]
  affects: [hackathon submission form, demo video recording]
tech_stack:
  added: []
  patterns: [shot-by-shot-script, judging-axes-coverage, phase-summary-derived-changelog]
key_files:
  created:
    - DEMO_SCRIPT.md
    - SUBMISSION.md
    - CHANGELOG.md
decisions:
  - "mock numbers quoted in DEMO_SCRIPT for safe take; live take instructs reading real values off screen to prevent stale hardcoded fake figures"
  - "EUR/degC headline (~5957 EUR/degC from mock artifact) framed as illustrative with explicit REQUIRES_VERIFICATION caveat"
  - "TOPSIS weights and CHANGELOG test counts phrased as per-project-records to avoid fabricating figures"
  - "SUBMISSION.md links section uses <FILL IN> placeholders — GitHub repo and HF Space URLs not known until kickoff/push"
metrics:
  duration: "~3 minutes"
  completed: "2026-05-21T02:15:37Z"
  tasks_completed: 3
  files_created: 3
  files_modified: 0
  commits: 3
---

# Phase 04 Plan 02: Submission Assets Summary

**One-liner:** Shot-by-shot 3-min screencast script (named persona Maria, hook, visible-real-API-call beat, EUR/°C close, both recording commands), SUBMISSION.md hitting all four judging axes with honesty note, and CHANGELOG.md derived from phase SUMMARYs — no secrets, no overclaiming.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write DEMO_SCRIPT.md — shot-by-shot 3-min screencast + exact recording commands | 4884643 | DEMO_SCRIPT.md |
| 2 | Write SUBMISSION.md — short description hitting all four judging axes | 64d6d5d | SUBMISSION.md |
| 3 | Write CHANGELOG.md — per-phase what-we-built from phase SUMMARYs | 92c08f6 | CHANGELOG.md |

## Verification Results

### DEMO_SCRIPT.md
- Contains "Maria" and "Chief Heat Officer" — PASS
- Has a hook section, shot list, and EUR/°C close — PASS
- Contains `python -m coolspend.app` (mock command) — PASS
- Contains `$env:INFRARED_BACKEND="live"` (PowerShell live command) — PASS
- States mock data is NOT MEASURED DATA — PASS
- Explicitly names video capture as the USER's final manual step — PASS
- No literal API key value (placeholder `<your-key>` only) — PASS
- PowerShell verification: DEMO-OK

### SUBMISSION.md
- Contains all four axis headings: `## Technical depth`, `## Creativity`, `## Real-world impact`, `## Presentation` — PASS
- Has a one-line pitch section — PASS
- Links section includes GitHub repo + Hugging Face Space + demo video placeholders — PASS
- Honesty note present (NOT MEASURED DATA, DECLARED constants, REQUIRES_VERIFICATION) — PASS
- Links to MOCKS.md — PASS
- No literal API key/secret string — PASS
- PowerShell verification: SUBMISSION-OK

### CHANGELOG.md
- Contains `## Phase 1`, `## Phase 2`, `## Phase 3` sections — PASS
- References sdk_client, NSGA-II, Gradio — PASS
- No scaffold-module or 3-objective claims — PASS
- Test-coverage note phrased per project records, no fabricated counts — PASS
- No secrets — PASS
- PowerShell verification: CHANGELOG-OK

## What Was Built

### DEMO_SCRIPT.md (119 lines)

Shot-by-shot ~3-min screencast script structured as: The Hook (0:00–0:20), Shot List (8 numbered shots with timecodes, on-screen description, narrator lines, and click instructions), The Close (2:20–3:00), Recording Commands (SAFE TAKE mock + LIVE TAKE PowerShell), and Final Manual Step.

Key narrative beats:
- Hook: Maria's decision problem stated in 20 seconds (where do 12 trees buy the most cooling per euro?)
- Shot 5: Expand SDK call log accordion — point at the three SimBudget entries — visible real API call
- Shot 8: Point at cost-per-degree cell, read ~5957 EUR/°C from mock, instruct reading live figure off screen
- Close: Vision — district-scale triage, any city polygon
- Safe take instructs presenter to say "NOT MEASURED DATA" explicitly before clicking Run
- Live take commands use `<your-key>` placeholder; instructs reading real number off screen

### SUBMISSION.md (57 lines)

Short project description with one-line pitch + What it is + four explicitly-headed judging axis sections + Honesty note + Links. Each axis section references shipped code by module name (sdk_client, optimizer.py, pymoo 0.6.1, SimBudget, TOPSIS, MOCKS.md) to give technical reviewers concrete verification points. The Honesty note explicitly states: surrogate-in-loop with ±4°C uncertainty, NOT MEASURED DATA, DECLARED constants REQUIRE_VERIFICATION, and directs readers to MOCKS.md.

### CHANGELOG.md (61 lines)

Per-phase what-we-built summary derived from all 11 phase SUMMARYs (Phases 1–3, three plans each) plus Phase 4 plans 01–02. Organised as Phase 1 (foundation), Phase 2 (optimizer), Phase 3 (web app), Phase 4 (ship). Each phase lists real shipped modules and artifacts with accurate descriptions. Test-coverage note phrased "Per project records: 122 tests passing, 1 skipped" — no fabricated counts. 2-objective NSGA-II stated correctly; no pollinator/3rd-objective claim.

## Deviations from Plan

None — plan executed exactly as written.

All three files were written in a single pass, verified against plan acceptance criteria PowerShell checks, and committed individually. No auto-fix deviations were needed.

## Threat Surface Scan

All three files are world-readable submission assets. Threats mitigated as planned:
- T-04-04 (API key disclosure): `<your-key>` placeholder only; no literal key pattern in any file. PowerShell regex check `INFRARED_API_KEY="[A-Za-z0-9]{8,}"` returns no match in DEMO_SCRIPT.md.
- T-04-05 (Honesty / overclaiming): Mock = NOT MEASURED DATA in both DEMO_SCRIPT and SUBMISSION; surrogate-in-loop + real-SDK-Top-3-validation stated; EUR/°C constants DECLARED; no fabricated live numbers.
- T-04-06 (Fake "live" numbers): Script instructs reading real numbers off screen on the live take; mock figures quoted only for the safe take and explicitly labelled as mock.

## Known Stubs

| Stub | File | Location | Reason |
|------|------|----------|--------|
| `<FILL IN>` GitHub repo URL | SUBMISSION.md | Links section | Repo URL unknown until user creates/pushes |
| `<FILL IN — created at kickoff>` HF Space URL | SUBMISSION.md | Links section | Space URL known only after kickoff May 27 |
| `<FILL IN after recording>` Demo video URL | SUBMISSION.md | Links section | Video not yet recorded — user's final step |

These stubs are intentional and clearly marked. They do not prevent the plan's goal (submission assets ready for the 5-minute final job). The user fills them in after kickoff.

## Self-Check: PASSED

Files created:
- DEMO_SCRIPT.md: EXISTS
- SUBMISSION.md: EXISTS
- CHANGELOG.md: EXISTS
- .planning/phases/04-ship/04-02-SUMMARY.md: THIS FILE

Commits verified:
- 4884643: feat(04-02) DEMO_SCRIPT.md
- 64d6d5d: feat(04-02) SUBMISSION.md
- 92c08f6: feat(04-02) CHANGELOG.md
