# Prompt for Claude (design) — CoolSpend presentation

Copy everything below the line into Claude with this codebase connected. Edit the
bracketed choices first (config to feature, audience, slide count).

---

You are my presentation designer. Build a clean, confident slide deck for **CoolSpend**,
an urban-heat tree-budget decision tool I built for the infrared.city Buildathon. Use the
REAL artifacts in this repo — do not invent numbers, and keep the honesty framing intact.

## What CoolSpend is (one line)
Given a site polygon and a planting budget, it finds the tree placement that delivers the
most measured cooling per euro — validated against real Infrared City UTCI simulations.

## The story arc (use this as the spine)
1. **Problem** — cities spend on street trees with no way to know which placement actually
   cools the most per euro. Urban heat is a health issue; budgets are finite.
2. **Approach** — multi-objective optimizer (NSGA-II) explores tree placements on a fast
   analytical surrogate, then the Top-3 candidates are validated with the REAL Infrared
   UTCI model (felt temperature: air + radiant + wind + humidity). Rank by €/°C and by
   m² of ground meaningfully cooled.
3. **Real data, end to end** — Open Data BCN street-tree inventory (~145k trees), per-species
   crown/height from Diputació de Barcelona "Verd Urbà" bands, ICGC LiDAR canopy height,
   and live Infrared City building footprints + ground materials + weather (TMYx EPW).
4. **Result** — at Plaça dels Àngels (MACBA plaza, Barcelona) the tool's best-value plan
   and the measured cooling, shown on photorealistic 3D Barcelona.
5. **Honesty** — what's measured vs surrogate, and why the felt-temp reads moderate.

## The real numbers (from outputs/web_bundle/decision.json — re-read it, don't trust my paste)
Site: Plaça dels Àngels, Barcelona — the REAL plaza polygon (~4,600 m², irregular 53-vertex
shape, not a square).
Best-value (rank-1) config: **[31 trees, €142,600, cools 3,940 m² of ground by ≥0.5 °C,
€36/m²]**. Felt-temp at sun-exposed spots: **30.98 °C → 30.64 °C**; site-mean UTCI ~28.7 → ~27.7 °C.
[OPTIONAL: also show the MAX_THERMAL_RELIEF config from decision.json — more trees, larger
cooled area — if I tell you to feature impact over cost-efficiency.]

## Honesty framing (MUST keep — it's a strength, not a weakness)
- Felt temperature is real **UTCI** from Infrared, July 09–17 window. Barcelona reads
  moderate (~28–31 °C, "moderate heat stress") because it's coastal + breezy, not because
  the model is wrong — inland Spain would read hotter. (See AUDIT_REPORT.md.)
- The optimizer's ΔTmrt objective is a surrogate with ±4 °C uncertainty; the live Infrared
  UTCI is the ground truth used for the headline.
- Costs are Barcelona-anchored (OpEx verified BCN IMPJ 2023; CapEx declared Diputació grant):
  ~€2,200/tree CapEx, €60/tree/yr OpEx, 40-yr horizon, discounted.

## Assets to embed (paths in this repo)
- `angels_trees_closer.png` — HERO shot: tree sprites standing in the real Plaça dels Àngels
  plaza in front of MACBA, on photorealistic 3D Barcelona. Title/result hero.
- `angels_zoom2.png` — the clean KPI/HUD panel (numbers, species chips, UTCI legend). Use it
  as the "result dashboard" visual or to lift exact KPI styling.
- `outputs/web_bundle/utci_baseline.png` and `utci_intervention.png` — UTCI heatmaps
  (colour scale 20–40 °C; blue = cooler). Show side-by-side as before/after.
- `outputs/web_bundle/decision.json` — pull KPIs + the Top-3 table from here (single source
  of truth — re-read it; the rank-1 config is MAX_THERMAL_RELIEF, 31 trees).
- `outputs/web_bundle/scene.glb` — 3D scene (buildings + existing + proposed trees) if the
  deck supports embedding/inline 3D; else render a still.
- `outputs/pareto_front.png` — the optimizer's Pareto front (thermal vs ecological).
- `AUDIT_REPORT.md`, `HOW_TO_DEMO.md` — background for speaker notes.

## Title-slide elevator line (use or paraphrase)
"CoolSpend turns a planting budget into the tree placement that buys the most measured
cooling per euro — optimized, then validated against real Infrared City microclimate
simulations, on the real Plaça dels Àngels."

## Slides (target ~[8] slides; adjust)
1. Title — name, one-line value prop, hero shot (`angels_final.png`).
2. Problem — urban heat + blind tree spending.
3. How it works — pipeline diagram: site+budget → NSGA-II surrogate → Top-3 → real Infrared
   UTCI → rank by €/°C + cooled m².
4. Real data — the four sources (BCN inventory, Verd Urbà species, ICGC LiDAR, Infrared).
5. Result — Plaça dels Àngels KPIs + before/after UTCI heatmaps.
6. See it in 3D — photoreal Barcelona with the scenario (hero again / GLB).
7. Honesty & rigour — measured vs surrogate, coastal-Barcelona felt-temp, cost basis,
   267 passing tests.
8. Close — what it unlocks (any Barcelona site, any budget) + ask.

## Design direction
Clean, technical, confident. Cool palette (blues/teals) with a warm accent for "heat".
Big numbers, minimal text, real imagery over clipart. Speaker notes per slide. Audience =
[hackathon judges]. Output format = [Google Slides / PDF / Gamma — your pick].

Re-read decision.json and the PNGs before finalizing so every figure on the slide matches
the artifact exactly.
