# CoolSpend — Tree Budget Optimizer

## What This Is

CoolSpend is a heat-mitigation budget decision-support tool for the infrared.city SDK Buildathon (Tree Budget track). A user — modeled on a city Chief Heat Officer — provides a city polygon and a fixed planting budget. CoolSpend runs a baseline UTCI thermal-comfort simulation, finds the hottest, most sun-exposed street locations, and uses a multi-objective optimizer (NSGA-II) to propose where to plant trees so that each euro buys the most degrees of street-level comfort relief. It returns a ranked budget **allocation** and a before/after map — a decision, not just a heatmap.

It is a clean extraction of the proven optimization + simulation pieces from a parent project ("NatureGooddest"), rebuilt as a small, self-contained, demoable app.

## Core Value

Given a polygon and a budget, output a defensible **ranked tree-planting allocation maximizing UTCI relief per euro** — and prove it with a real Infrared UTCI before/after on the top picks. If everything else fails, this must work.

## Current Milestone: v2.0 Market-Ready CoolSpend

**Goal:** Convert the hackathon prototype from a credible *framework* into a defensible *product* — ground-truth the model, fix the cost denominator, ingest real multi-site geometry, and reframe from "trees only" to a multi-intervention urban-heat **budget allocator** positioned as an optimization + grant-compliance layer on top of city GIS.

**Why now (3-review synthesis, 2026-05-21):** Three independent reviews (market, product, science — see `docs/review/`) converged: the headline KPI is currently *assumption ÷ assumption*; the surrogate optimizes ΔTmrt but sells "UTCI relief" (unit substitution); the cost model is ~10× too low; and the trees-only framing competes with free incumbents (i-Tree, Boston Right-Place-Right-Tree). The durable moat is the honesty contract + the surrogate-optimize-then-validate loop. Full direction in `docs/review/SYNTHESIS-market-ready.md`.

**Target features:**
- **Validation (keystone):** surrogate-vs-Infrared calibration study across varied configs; Tmrt→UTCI conversion; €/°C as an uncertainty interval; single CRS end-to-end.
- **Cost credibility:** fully-loaded, sourced, per-city-configurable lifecycle cost with growth-horizon discounting.
- **Real geometry & multi-site:** OSM/cadastre ingestion; footprint/footway collision; N-site data model.
- **Multi-intervention allocator:** intervention type as a parameter (trees + cool roofs as the v2 proof pair); allocate one budget across types by €/°C.
- **District/portfolio triage:** rank N sites citywide; equity weighting for heat-vulnerable areas.
- **Workflow integration:** GeoPackage/Shapefile + procurement-cost export; GIS layer interop.
- **Grant-compliance packaging:** allocation appendix mapped to EU LIFE / European Urban Initiative reporting.
- **Defensibility:** per-run audit manifest; stakeholder-elicited weights; honesty relabeling (align CONCEPT_REPORT down, re-anchor citations, scope-out unmodeled siting constraints).

**Keystone first:** the surrogate ground-truth study (VALID-01/02/03) is the existential test — if surrogate rankings don't hold against measured UTCI, the product is wrong. Everything else is downstream.

## Requirements

### Validated

<!-- Proven to work in the NatureGooddest reference code; to be ported clean. -->

- ✓ NSGA-II multi-objective optimization over tree/canopy coordinates — `nature_nsga2_coolstock.py` (pymoo 0.6.1, seed-pinned, ~30s/run)
- ✓ Fast thermal surrogate (`delta_tmrt_surrogate()`) used *inside* the optimization loop, avoiding per-chromosome live SDK calls
- ✓ UTCI / thermal-comfort metric functions — `nature_metrics.py`
- ✓ Infrared SDK client with `mock | cached | live` backend boundary — `infrared_client_v2.py` (offline-capable via mock/cached)
- ✓ Real Infrared UTCI run on a real site (Plaça dels Àngels, measured 28.08°C → 27.81°C)

### Active

<!-- The coolspend build. Hypotheses until shipped. -->

- [ ] Clean `sdk_client.py` with `mock|cached|live` boundary (one client; dedupe the two identical reference files)
- [ ] `spatial_engine.py` — load OSM/GeoJSON, shapely collision (no trees in buildings / on street centerlines / outside site)
- [ ] `rules_engine.py` — ecological penalties: minimum spacing + species diversity (capped at 2 simple rules)
- [ ] `cost_model.py` — per-tree CapEx + OpEx → €-per-°C-relief KPI
- [ ] `optimizer.py` — NSGA-II on the surrogate (thermal + ecological objectives, budget constraint), then validate Top-3 with real UTCI
- [ ] Decision artifact — ranked allocation table + before/after comparison
- [ ] `app.py` — Gradio web app (polygon + budget in → map + allocation out), deployable to Hugging Face Spaces
- [ ] `requirements.txt`, README with architecture diagram, MOCKS ledger
- [ ] 2.5–3 min demo video (live app, real API calls visible)

### Out of Scope

- Full NatureGooddest 6-layer platform (SPARQL/cookbook/Neo4j/Flask demo/Three.js viewer) — parent-project baggage; not needed to ship the decision
- ML / "learned urban coherence" — ruled out last session (data unavailability + 3-day latency); **do not retry**
- "Permaculture engine" beyond 2 simple penalties — scope-creep risk flagged in concerns map
- 3rd (pollinator) objective — degenerates to a constant in reference code; ship as 2-objective, don't claim 3
- Satellite tree segmentation / cool-routing — different tracks; out of scope
- Cool-roof / shade-structure interventions in v1 — trees only for the demo; generalize later if time

## Context

- **Hackathon:** infrared.city SDK Buildathon, online, **May 27–31 2026** (kickoff May 27 17:00 CET; deadline May 31 24:00 CET; winners Jun 2). Solo/small team. Prize €5K/€2K/€1K credits. Judged: technical depth, creativity, real-world impact, presentation. Deliverable = GitHub repo + demo + short description.
- **Prior work:** parent project "NatureGooddest" (Barcelona urban cooling). Reference modules copied into this dir; full port verdicts in `.planning/codebase/`. Prior plan: `docs/plans/2026-05-20-tree-budget-optimizer-v2.md` (this supersedes it by adding the web/demo layer).
- **Research:** session deep-research (`.planning/research/` if generated) confirmed direction independently and supplied competitor positioning (ENVI-met/Forma/SimScale/Cool Walks), the Chief Heat Officer persona, and hackathon winning patterns (decision > visualization; live web app + 3-min narrative; reserve half of final day for the video).
- **Demo site default:** Plaça dels Àngels, Barcelona (real data already on hand from parent project).

## Constraints

- **Timeline**: 3-day effective build (May 27–31) — scope must stay shippable; ≤3 headline features; working demo over feature count.
- **Dependency / API key**: hackathon `INFRARED_API_KEY` issued **only at kickoff May 27**. Until then, build & test offline against the `mock`/`cached` backend. Keep the SDK behind a clean interface boundary so live wiring is a one-line swap. Keys auto-deactivate after Jun 3.
- **Compute / sim budget**: NSGA-II ≈ gen×pop evaluations (10k at full settings) — **never** call live Infrared per evaluation. Optimize on the surrogate; validate only Top-3 with real UTCI. Add a `SimBudget` guard on real calls.
- **Tech stack**: Python; `pymoo` 0.6.1, `shapely`, `geojson`, `numpy`, `infrared-sdk`, `gradio`.
- **Integrity (honesty contract)**: every mock/surrogate documented in a MOCKS ledger; data sources tagged VERIFIED/PENDING/DECLARED; no fabricated/inferred citations (deep-research agents have hallucinated DOIs here before); the surrogate's unsourced 12°C cap + citation-mismatch must be disclosed, not hidden.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build "Tree Budget / CoolSpend" track | Deep-research: highest feasibility×impact, lowest risk; converged with prior session's pick | — Pending |
| Clean extraction into new `coolspend/` repo | Judged GitHub repo + honesty contract; avoid parent-project baggage | — Pending |
| Optimize on surrogate, validate Top-3 with real UTCI | Sim-budget constraint; pattern already proven in reference code | — Pending |
| Add Gradio web app + demo video (supersede Plan V2's CLI) | Research: judges reward live app + narrative; CLI loses presentation/impact | — Pending |
| Map codebase before planning | Brownfield discipline; got port verdicts + honesty flags before coding | ✓ Good |
| Ship as 2-objective (thermal + ecological) | Reference 3rd objective degenerates to constant; stay honest | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-21 — milestone v2.0 (Market-Ready CoolSpend) started*
