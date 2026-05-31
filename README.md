---
title: CoolSpend Tree Budget Optimizer
emoji: 🌳
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 4.44.1
app_file: coolspend/app.py
pinned: false
---

## CoolSpend — cooling per euro, validated, as an ecosystem

Built for the infrared.city SDK Buildathon (Tree Budget track). CoolSpend answers a city
heat officer's real question: **for this budget, where do we plant — and what — to cool the
most ground per euro, while installing a healthy urban ecosystem, not just shade?**

Two modes:

- **Design (a site):** draw any polygon in Barcelona, set a budget. An NSGA-II optimiser
  places species-specific trees over real building/ground context; the result is
  **re-simulated on the live Infrared UTCI engine**. Headline KPI: **€ per m² of ground
  cooled ≥0.5 °C** (a footprint metric that doesn't saturate on already-hot sites).
- **Citywide (€1M):** ranks all **494 Barcelona grid cells** by heat × sealed-surface and
  allocates a budget to the hottest cells first — district-scale triage.

Every proposed tree is clickable: species, crown, **the m² it actually shades**, cooling
score, and a full **ecosystem profile** (drought/heat tolerance, biodiversity, pollinator
value, allergenicity, pest/disease risk, longevity, water, maintenance, native/invasive,
mycorrhizae) rolled into one ecosystem-health score.

### Live result (Plaça dels Àngels — real Infrared UTCI, building-aware)

`backend=live`, 615 buildings fetched: **28 trees cool 4,268 m² by ≥0.5 °C at €30/m²**;
peak felt temperature **31.0 → 29.8 °C**; cooling depth 3,260 m² ≥1 °C / 1,716 m² ≥2 °C /
664 m² lifted out of heat stress. Species chosen are **all non-invasive** — the optimiser
excludes the species Barcelona is phasing out (Robinia, Ligustrum lucidum, Ulmus pumila)
per the *Pla Director de l'Arbrat de Barcelona*.

## Run locally

**Tokens** (web/.env.local): `VITE_MAPBOX_TOKEN` (basemap, required);
`VITE_CESIUM_ION_TOKEN` (optional — photoreal 3D, currently disabled by default).

```bash
# Python deps
pip install -r requirements.txt

# 1) Backend API (drawing + citywide). mock = evaluate ANY drawn area instantly.
INFRARED_BACKEND=mock python -m uvicorn coolspend.api_server:app --port 8000

# 2) Web app
cd web && npm install && npm run dev          # http://localhost:5173
```

The default plaza view loads the **cached live** showcase (real Infrared UTCI). Drawing a
new area evaluates on the mock backend (a labelled synthetic preview); the live backend
handles new areas when an API key is present.

**Regenerate the live showcase** (one real run): set `INFRARED_BACKEND=live` and
`INFRARED_API_KEY=<your infrared.city key>` (read from the environment / a gitignored
`.env`, never committed), then `python -m coolspend.export_web`. Mock/cached need no key.

**Tests:** `python -m pytest coolspend/tests -q` (341 offline, deterministic) · `cd web && npm test` (vitest) · `npm run build` (production).

A legacy Gradio UI (`coolspend/app.py`, the HF-Space `app_file` above) still exists as a
fallback; the deck.gl web app in `web/` is the primary deliverable.

## Architecture

```
Browser (web/): Mapbox satellite + deck.gl
  ├─ UTCI heatmap (cropped to site) + canopy-disk trees + click-inspect ecosystem panel
  └─ Design mode (draw→evaluate)  |  Citywide mode (494-cell €1M heatmap)
        │ HTTP /api/*
FastAPI (coolspend/api_server.py)
  ├─ /api/evaluate   → run_decision → export_web_bundle → /eval_bundle/*
  └─ /api/citywide/* → scan / allocate over scored_grid (494 cells)

coolspend/
  optimizer.py     — NSGA-II (pymoo); species gene; palette EXCLUDES invasives (ecology)
  spatial_engine.py— delta_tmrt_surrogate (hot-path proxy; no SDK calls)
  sdk_client.py    — mock|cached|live Infrared UTCI; cooled_footprint_m2 + profile
  ecology.py       — per-species ecosystem profile + composite (benefits−penalties−invasive)
  bcn_species.py   — real BCN palette + species_public() (web join point)
  bcn_data.py      — arbrat-viari inventory (145k trees) ; citywide.py — 494-cell allocation
  cost_model.py    — itemised €/tree → € per m²-cooled KPI
  export_web.py    — writes the web bundle (decision/trees/boundary/bounds/heatmap PNGs)
```

The NSGA-II hot path uses only the analytical surrogate (zero SDK calls); the Top-3 picks
are re-simulated on real Infrared UTCI (`SimBudget`-guarded). The headline number is the
**measured** grid difference, not the surrogate.

## Honesty / provenance

- The headline is a **real live Infrared UTCI** result (cached replay reproduces it offline).
- Per-species cooling and the ecosystem-health composite are **labelled heuristics** for
  selection/ranking, literature-anchored and cited
  ([docs/bcn_planting_strategy.md](coolspend/docs/bcn_planting_strategy.md),
  [docs/species_ecology_traits.md](coolspend/docs/species_ecology_traits.md)); the cooling
  magnitude itself is the Infrared sim's.
- The surrogate's 12 °C ΔTmrt cap is unsourced (REQUIRES_VERIFICATION) and only ranks
  candidates, which are then re-simulated on real UTCI. Cost constants are itemised and
  Barcelona-anchored where verified. Full ledger: [MOCKS.md](MOCKS.md).

## Out of scope (not modelled)

Geometric feasibility, **not** engineering siting sign-off: subsurface utilities, soil
volume, irrigation, sightlines, solar access to façades, and root-vs-pavement conflict are
not modelled. All placements need municipal engineering + arboriculture review.
