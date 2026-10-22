# CoolSpend

**3rd place — Infrared.city Buildathon 2026** (Tree Budget track). Solo entry.

CoolSpend answers a city heat officer's real question: **for this budget, where do we plant —
and what — to cool the most ground per euro, while installing a healthy urban ecosystem, not
just shade?**

Barcelona is the test bed. Every cooling number below is measured on the live Infrared.city
UTCI engine, not assumed.

## Two modes

- **Design (a site):** draw any polygon in Barcelona, set a budget. An NSGA-II optimiser
  places species-specific trees over real building and ground context; the result is
  **re-simulated on the live Infrared UTCI engine**. Headline KPI: **€ per m² of ground
  cooled ≥ 0.5 °C** — a footprint metric that does not saturate on already-hot sites.
- **Citywide (€1M):** ranks all **494 Barcelona grid cells** by heat × sealed surface and
  allocates the budget to the hottest cells first — district-scale triage.

Every proposed tree is clickable: species, crown, **the m² it actually shades**, cooling
score, and a full ecosystem profile (drought and heat tolerance, biodiversity, pollinator
value, allergenicity, pest risk, longevity, water, maintenance, native/invasive, mycorrhizae)
rolled into one ecosystem-health score.

## Measured result — Plaça dels Àngels

`backend=live`, 615 buildings fetched:

- **28 trees cool 4,268 m² by ≥ 0.5 °C at €30/m²**
- peak felt temperature **31.0 → 29.8 °C**
- cooling depth: 3,260 m² ≥ 1 °C, 1,716 m² ≥ 2 °C, 664 m² lifted out of heat stress
- species are **all non-invasive** — the optimiser excludes what Barcelona is phasing out
  (Robinia, Ligustrum lucidum, Ulmus pumila) per the *Pla Director de l'Arbrat de Barcelona*

Citywide demo: a €1,000,000 portfolio funded 90 trees across 6 separated sites, cooling
20,609 m² and serving 26,745 residents, zero invasive species.

## Try it

No API key needed for the default path — `mock` evaluates any drawn area offline, and the
plaza view loads a **cached live** showcase (real Infrared UTCI, replayed).

```bash
# 1) Python deps for the API tier
pip install -r requirements-api.txt

# 2) Backend  (mock = instant, no key; see .env.example)
INFRARED_BACKEND=mock python -m uvicorn coolspend.api_server:app --port 8000

# 3) Web app
cd web && npm ci && npm run dev        # http://localhost:5173
```

Python 3.11+. `VITE_MAPBOX_TOKEN` in `web/.env.local` gives you the satellite basemap; without
it the app still runs, the basemap just degrades. `VITE_CESIUM_ION_TOKEN` is optional and
disabled by default.

To regenerate the live showcase you need `INFRARED_BACKEND=live` plus `INFRARED_API_KEY` in
the environment or a gitignored `.env` — then `python -m coolspend.export_web`. The key is
never committed; there is no key in this repository or in its history.

## Tests

Measured on a clean clone, not estimated:

- **Python:** `pytest` → **398 passed, 1 skipped** with the full dev set
  (`pip install -r requirements-dev.txt`). The API tier alone (`requirements-api.txt`) runs
  394 and skips the legacy Gradio UI tests, which opt out when Gradio is absent.
- **Web:** `cd web && npm test` → **39 passed**; `npm run build` → production build succeeds.

CI runs both on every push and pull request.

## Repository layout

```
coolspend/        Python backend — optimiser, spatial surrogate, Infrared client,
                  ecology/cost models, FastAPI server (api_server.py), tests/
  docs/           Literature-anchored method notes (planting, species, costs)
web/              Primary deliverable — Vite + React + deck.gl decision UI
video/            Remotion explainer film
L1_INGEST_data/   Real input data: BCN climate (EPW), scored grid (494 cells),
                  intervention costs, biodiversity and carbon references
tools/            One-off utilities (report build, portfolio precompute, transcribe)
nature_metrics.py EPW-derived UTCI-hours KPIs (calibration study)
PAPER.md          Full method + results writeup (the canonical explanation)
MOCKS.md          Provenance ledger: what is measured vs heuristic vs unsourced
DATA_SOURCES.md   Origin and licence of every input dataset
```

## How it works

```
Browser (web/): Mapbox basemap + deck.gl
  ├─ UTCI heatmap (cropped to site) + canopy trees + click-inspect ecosystem panel
  └─ Design mode (draw → evaluate)  |  Citywide mode (494-cell €1M heatmap)
        │ HTTP /api/*
FastAPI (coolspend/api_server.py)
  ├─ /api/evaluate   → run_decision → export_web_bundle → /eval_bundle/*
  └─ /api/citywide/* → scan / allocate over scored_grid (494 cells)
```

- `optimizer.py` — NSGA-II (pymoo), species gene, palette excludes invasives
- `spatial_engine.py` — `delta_tmrt_surrogate`: the hot-path proxy, zero SDK calls
- `sdk_client.py` — mock | cached | live Infrared UTCI, with `cooled_footprint_m2`
- `cost_model.py` — itemised €/tree → € per m²-cooled KPI
- `export_web.py` — writes the web bundle consumed by `web/`

The optimiser's hot path uses only the analytical surrogate; the Top-3 picks are then
re-simulated on real Infrared UTCI under a `SimBudget` guard. **The headline number is the
measured grid difference, not the surrogate.**

## Honesty and provenance

This project's defining constraint is that no number is allowed to look better than it is.

- The headline is a **real live Infrared UTCI** result; the cached replay reproduces it offline.
- Per-species cooling and the ecosystem-health composite are **labelled heuristics** for
  ranking only, literature-anchored and cited in
  [docs/bcn_planting_strategy.md](coolspend/docs/bcn_planting_strategy.md) and
  [docs/species_ecology_traits.md](coolspend/docs/species_ecology_traits.md). The cooling
  magnitude itself is the Infrared simulation's.
- The surrogate's 12 °C ΔTmrt cap is unsourced (REQUIRES_VERIFICATION) and only ranks
  candidates, which are then re-simulated. Cost constants are itemised and Barcelona-anchored
  where verified. Full ledger: [MOCKS.md](MOCKS.md).
- The three backend tiers are server-side and explicit, so a synthetic preview cannot be
  mistaken for a measured result.

## Out of scope

Geometric feasibility, **not** engineering siting sign-off: subsurface utilities, soil volume,
irrigation, sightlines, solar access to façades, and root-vs-pavement conflict are not
modelled. All placements need municipal engineering and arboriculture review.

## Credits and licence

Built solo for the Infrared.city Buildathon 2026. Thanks to Infrared.city for the UTCI engine
and the organisers for the Tree Budget track.

Data: Open Data BCN (arbrat viari inventory, population register, climate), ICGC/CREAF LiDAR
canopy height, OpenStreetMap geometry, Barcelona EPW (TMYx), and Infrared.city UTCI results
produced during the event. Per-dataset licence notes are in [DATA_SOURCES.md](DATA_SOURCES.md).

Code: MIT — see [LICENSE](LICENSE).
