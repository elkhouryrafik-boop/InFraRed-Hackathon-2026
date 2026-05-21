# Handoff — Tree Budget Optimizer

**Created:** 2026-05-20 23:55 by Claude Code session
**Branch:** N/A (Manual file sync from NatureGooddest)
**Last commit:** N/A

## Goal
Build a tree-placement optimizer for the Infrared City Hackathon that maximizes "Carbon of Stress Relief" (UTCI relief per Euro). The system uses NSGA-II to find optimal tree coordinates while respecting hard urban constraints (buildings/streets) and ecological rules (spacing/diversity).

## Current state
- **Research Complete:** Analyzed Infrared Hackathon requirements and extracted relevant logic from the previous project (NatureGooddest).
- **Architecture Defined:** Disciplined NSGA-II approach using `pymoo`, `infrared-sdk`, and `shapely`. Dropped speculative ML/Permaculture scope creep in favor of a ship-able rule-based prototype.
- **Project Assets Copied:** Core NatureGooddest files (`nsga2_coolstock.py`, `metrics.py`, `infrared_client.py`) are in the hackathon workspace for reference.
- **Implementation Plan V2:** Saved to `docs/plans/2026-05-20-tree-budget-optimizer-v2.md`.
- **Concept Report:** Saved to `CONCEPT_REPORT.md`.

## Files in flight
- `docs/plans/2026-05-20-tree-budget-optimizer-v2.md` — The blueprint for the next session.
- `CONCEPT_REPORT.md` — Detailed conceptual and financial rationale.
- `nature_nsga2_coolstock.py` — Reference for the evolutionary algorithm setup.
- `nature_metrics.py` — Reference for UTCI and carbon calculations.

## What changed this session
- Scraped the Infrared Hackathon website to define the "Tree Budget" challenge.
- Researched NatureGooddest project to identify reusable optimization and climate simulation code.
- Successfully pivoted from a vague "ML/Permaculture" vision to a concrete "Rule-Based Optimizer" architecture.
- Drafted a Task-by-Task implementation plan.
- Addressed the financial aspect of the challenge (CapEx/OpEx balancing).

## What we tried that didn't work
- **Vague Scope:** Initial discussion on using ML to learn "urban coherence" was ruled out due to data unavailability and 3-day hackathon latency constraints. **Do not retry ML for the core optimizer.**
- **Outside Workspace Access:** Attempted to read NatureGooddest files directly; failed because they were outside the allowed directory. Fixed by copying relevant files into the current workspace.

## Open questions / decisions pending
- **Infrared API Key:** The next session must verify the `INFRARED_API_KEY` is in `.env` to run Task 1 of the implementation plan.
- **Site Selection:** Which specific plaza/street in Spain (or Barcelona) will be the demo site? (Plaça dels Àngels from NatureGooddest is the current default).

## Next steps
1.  Initialize the workspace as a Git repository (since current work was done without one).
2.  Implement `spatial_engine.py` (Task 1 in Plan V2) using `shapely` and local OSM GeoJSON.
3.  Implement `rules_engine.py` (Task 2) to encode the "Permaculture Rules" as fitness penalties.
4.  Wire the `infrared-sdk` into `optimize_trees.py` (Task 3) to enable real thermal feedback.
5.  Run a 10-generation pilot and verify results.

## How to resume
> Read `HANDOFF.md` and `docs/plans/2026-05-20-tree-budget-optimizer-v2.md`. Begin execution with Task 1 of the V2 plan. Use `nature_nsga2_coolstock.py` as your primary code reference for the NSGA-II implementation.
