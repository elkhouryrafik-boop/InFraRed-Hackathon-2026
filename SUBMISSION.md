# CoolSpend — Infrared.city Buildathon 2026 Submission

Copy-paste each field into the submission form. Notes/flags are marked `>` or `⚠️` and should **not** be pasted.

---

## 1 · Video & images

- **Demo video** — upload the 2-min cut (or paste a Loom/YouTube link of it). A ~10-min Remotion explainer also exists.
- **Screenshots (up to 5)** — suggested set:
  1. Draw-polygon mode
  2. Single-site UTCI heatmap + canopy discs
  3. Click-inspector with per-species ecology
  4. Citywide €1M 6-site panel
  5. 3D cinematic scene
- **Sketches / PDF** — attach `PAPER.md` exported to PDF (lets judges audit every number).

---

## 2 · Your project

### Project name
```
CoolSpend
```

### One-liner description (139 / 140 chars)
```
CoolSpend tells Barcelona where to plant street trees, measures the cooling on live UTCI, and spends a fixed budget where heat hurts most.
```

### Challenge track
> Dropdown options not visible to me. Pick the closest to **Climate / Urban Heat / Sustainability**.

### Tags (press Enter between each)
```
urban-heat
UTCI
thermal-comfort
street-trees
GIS
budget-optimization
decision-support
Barcelona
```

### Problem

Cities know trees cool streets. But the decisions that actually matter — which species, where, how much cooling per euro — still get made without a model that respects real geometry and a real budget. Heat is one of the deadliest climate hazards, and it lands hardest on the most sealed, least green, often densest blocks. Two questions stay unanswered: where does a planted tree actually cut outdoor thermal stress given the buildings and streets around it, and how should a fixed budget be split across a city to cool the most vulnerable people first?

### Solution

CoolSpend fuses four real datasets (satellite heat and imperviousness, OpenStreetMap geometry, Barcelona's tree inventory, and the population register) into a 494-cell vulnerability grid. It treats placement as budgeted weighted maximum coverage over a building- and street-aware lattice of validated planting slots, solved by a cost-benefit greedy that carries the classical (1−1/e)≈63% optimality guarantee. An ecology gate drops invasive and over-represented species, leaving an 8-species plantable palette. Cooling numbers come from a live Infrared.city UTCI field, not an assumption. At Plaça dels Àngels, 28 trees cooled a measured 4,268 m² at €30/m². A €1,000,000 portfolio funded 90 trees across 6 separated sites, cooling 20,609 m² and serving 26,745 residents, with zero invasive species.

### Technical implementation

A Python computational core behind a FastAPI/Uvicorn service, with a React 18 / TypeScript 5.6 web client (deck.gl 9.1, mapbox-gl 3.9, Vite 6). One pipeline runs it: generate validated candidate slots on a 4 m lattice (building, street, furniture, and 8 m-spacing exclusions from OSM), build a weighted demand field, place trees with a cost-benefit greedy max-coverage algorithm (shade-gain objective, anti-monoculture cap, stopped on a real `stop_reason` rather than an iteration count), then validate the layout on the Infrared.city engine. The Infrared backend has three tiers (mock, cached, live) chosen server-side by the `INFRARED_BACKEND` env var, so a synthetic preview can't be mistaken for a measured result. A `SimBudget` guard caps live calls at 3 per run. Libraries: FastAPI, numpy, shapely, pyproj, pymoo (the NSGA-II benchmark alternative), matplotlib; deck.gl 9, mapbox-gl, Vite 6. The SDK imports lazily, so the offline path needs none of it.

### Target group

City climate-adaptation and urban-forestry teams who have to defend where every planting euro goes, and the residents of dense, heat-vulnerable blocks those decisions protect. It also fits planning consultancies and researchers who need outdoor-comfort estimates grounded in measured simulation rather than rules of thumb.

---

## 3 · Team & links

### Team name
```
Team Heat
```
> Prefilled. Keep or change to your handle.

### Team members
```
Rafik El Khoury
```
> Solo (PAPER.md is single-author CRediT). Confirm before submit.

### GitHub URL
```
https://github.com/elkhouryrafik-boop/InFraRed-Hackathon-2026
```

### Live demo URL
> **Needs confirm.** A Hugging Face Space (Gradio `coolspend/app.py`) is referenced in the README front-matter. Paste its URL only if it is live and public right now; otherwise leave blank. Note: the Space serves the legacy Gradio UI, not the new deck.gl web client.

---

## 4 · APIs, feedback & prize

### Which Infrared SDK analyses did you use?

UTCI / thermal comfort is the headline, used twice per single-site run in a measured before/after design. A baseline UTCI simulation (no trees) returns a 512×512 grid that builds the demand field: a cell becomes demand only where `UTCI > 26 °C ∧ impervious ∧ not-already-shaded ∧ ¬NaN`, weighted by `UTCI − 26`. After greedy placement, an intervention UTCI simulation (with the trees) runs, and we report the measured grid difference `ΔUTCI = baseline − intervention`. Every reported cooling figure (cooled m² by band, €/m² cooled, peak-felt drop) comes from those two measured grids, not the placement proxy. We also fetch building footprints live from Infrared and union them with OpenStreetMap so both the simulation and the placement are building-aware. Calls use a fixed July 09:00–17:00 peak-heat window at 1.1 m pedestrian height via `run_area_and_wait`.

> ⚠️ Verified: TCS (`_live_tcs`) exists in `sdk_client.py` but no shipped pipeline calls it. Shipped = UTCI + live buildings only. Do not claim TCS — it would contradict the project's honesty architecture.

### How was the Infrared SDK? (optional)

Usable end-to-end. Building, ground, and weather context plus `run_area_and_wait` gave us a real before/after UTCI proof point. Three things tripped us up, all fixable. The weather endpoint started returning HTTP 500, so we added an EPW (Barcelona TMYx) fallback behind an `INFRARED_WEATHER_SOURCE=epw` toggle. The 512×512 UTCI grid spans a square bigger than the drawn polygon with the valid cells in one corner, so we had to crop to the non-NaN bounding box, or demand scattered to the wrong coordinates and placement returned zero trees. And the building layer is live-only, which pushed us to an OSM-buildings fallback for offline runs. Clearer grid-extent and CRS docs, a built-in EPW toggle, and offline building footprints would have helped most.

### Prize account email
```
elkhouryrafik@gmail.com
```

---

## Before you submit — 3 open items

1. **Challenge track** — pick the real dropdown option (Climate / Heat / Sustainability family).
2. **Live demo URL** — confirm whether the HF Space is live; paste or leave blank.
3. **Team members** — confirm solo vs. add names.

*Numbers are exact from PAPER.md (Section 6) and `web/public/citywide_plan.json`. All cooling figures are measured on live Infrared UTCI, cached by geometry hash.*
