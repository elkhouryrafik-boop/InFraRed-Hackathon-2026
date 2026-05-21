# ARCHITECTURE.md — NatureGooddest deep technical overview

Audience: engineers who want to understand the system end-to-end before contributing.

For the 90-second product-level overview, read [`README.md`](README.md). This document is the *how*, not the *what*.

---

## The six-layer architecture

```
                           ┌──────────────────────────┐
                           │  L6 MONITOR              │
                           │  MOCKS.md  audit_record  │
                           │  field-deployment ledger │
                           └────────────▲─────────────┘
                                        │ writes per-run audit
┌─────────────┐  ┌──────────────┐  ┌────┴───────┐  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  L1 INGEST  │→ │  L2 COOKBOOK │→ │ L3 GENER. │→ │ L4 SIMULATE  │→ │ L5 DEFEND        │→ │  Spatial output  │
│  data_      │  │  YAML        │  │ NSGA-II   │  │ Infrared     │  │ evaluator        │  │  /results_json   │
│  manifest   │  │  patterns    │  │ pymoo     │  │ Ladybug      │  │ HARD_BLOCK gate  │  │  /scene_json     │
│  GBIF       │  │  → OWL TTL   │  │ Pareto    │  │ surrogate    │  │ 3-citation block │  │  Plan/Section/3D │
│  Sentinel   │  │  → Neo4j     │  │ Top-3     │  │              │  │ audit trail JSON │  │                  │
│  EPW OSM    │  │              │  │           │  │              │  │                  │  │                  │
└─────────────┘  └──────────────┘  └───────────┘  └──────────────┘  └──────────────────┘  └──────────────────┘
```

### L1 INGEST — verified data sources

**Location:** [`L1_INGEST_data/`](L1_INGEST_data/)
**Authoritative manifest:** [`L1_INGEST_data/data_manifest.yaml`](L1_INGEST_data/data_manifest.yaml)
**Live connectors:** [`bcn_opendata.py`](bcn_opendata.py) (CKAN, runtime-fetched, not file-backed)

The manifest declares every data source with status `VERIFIED` / `PENDING` / `DECLARED`. The two-tier honesty gate `evaluator.check_data_verification()` reads this manifest at runtime: **`PENDING` or missing sources hard-block** (raise `RuntimeError` under `HARD_BLOCK`); **`DECLARED` partner feeds fire but are flagged** — every fired pattern carries `honesty_status` (`VERIFIED` / `DECLARED_INPUTS` / `UNVERIFIED`) so the UI + `/audit_json` surface unverified inputs. The gate does not pretend a DECLARED source is verified. (Resolved 2026-05-20, audit C1.)

Real data on disk:
- `sentinel/angels_canopy_cover.json` (ESA WorldCover 10 m, CC-BY 4.0)
- `climate/Barcelona_TMYx_2011-2025.epw` (Climate.OneBuilding)
- `biodiversity/angels_gbif_pollinators.json` (GBIF API, CC0)
- `geometry/angels_buildings.geojson` (746 buildings, OSM ODbL 1.0)
- `geometry/angels_open_spaces.geojson` (42 polygons)
- `geometry/angels_streets.geojson` (1,429 line segments)
- `supply/` — material supplier inventories (some declared as mocks)

Open Data BCN: served at runtime via `bcn_opendata.py` → `/opendata_bcn_json` Flask route, fetched fresh from CKAN on every demo load. CC-BY 4.0.

### L2 COOKBOOK — pattern library

**Location:** [`cookbooks/`](cookbooks/) — see [`cookbooks/README.md`](cookbooks/README.md)
**Manifest:** `cookbooks/urban-cooling/cookbook.json` — **22 entries (20 published + 2 suppressed) as of 2026-05-19**. Disk has 29 YAMLs (P01–P29); P23–P29 are authored but not yet entered in the manifest (see `audit/07_reality_check.md` claim 8).
**Authoring format:** YAML (one file per pattern in `patterns/`)
**Runtime format:** OWL Turtle (auto-emitted by `scripts/kg/generate_owl_ttl.py`)
**Runtime store:** in-memory rdflib graph, rebuilt per evaluation from L1 site data (see `sparql_engine.py`). This is what executes pattern firing.
**Optional scale-out store:** Neo4j (loaded offline by `scripts/kg/populate_neo4j.py` for Cypher-based exploration). **NOT on the demo's runtime path** — `demo_app.py` + `evaluator.py` contain zero `neo4j`/`GraphDatabase` calls. The demo runs fully without it. (Audit 2026-05-19 finding: do not pitch Neo4j as a live runtime dependency until a route actually queries it.)

Pattern YAMLs follow Christopher Alexander's IF/THEN/DELIVERS/CITES format. Every pattern has:
- `id` — `Pxx`
- `theory.doi` — CrossRef-verified primary citation (or honest placeholder `REQUIRES_VERIFICATION` / `NONE_PEER_REVIEWED`)
- `theory.supporting[]` — additional theory citations
- `data_sources[]` — connector_id references to `L1_INGEST_data/data_manifest.yaml`
- `records[]` — field/community/elder records (the third citation)
- `sparql_filter` — the firing condition (evaluated by `evaluator.safe_eval_filter()` via AST walk, no `eval()`)
- `delivers.primary.metric` + `range` — the headline impact
- `mechanism_edges[]` — how this pattern interacts with others (`enables`, `requires`, `competes_with`, `enhances`)
- `lifecycle` — `published` / `suppressed` / `draft`

The two algorithms:
1. **Recipe → Pattern Compiler** — LLM-driven, internal Wizard-of-Oz for v1. Author articulates a recipe in natural language; the compiler produces a YAML draft for human refinement. Not shipped as a public surface in v1.
2. **Pattern → Site Executor** — NSGA-II + evaluator at runtime. The shipped, deterministic path.

### L3 GENERATE — rule-based composer (current) + NSGA-II (legacy)

**Current user-facing path (2026-05-19):** rule-based cell-first v3 composer at [`scripts/sim/compose_rule_based.py`](scripts/sim/compose_rule_based.py) + [`scripts/place_composition.py`](scripts/place_composition.py). Emits a single composition with priority order derived from each pattern's YAML; magic-number caveats documented in `audit/01_architect.md` C3.

**Legacy path (still wired):** [`nsga2_coolstock.py`](nsga2_coolstock.py) — NSGA-II Pareto Top-3, served on `/` (legacy NG3D viewer) and `/run`. Scheduled for decommission. See `audit/07_reality_check.md` claim 10b.

**Library:** pymoo 0.6.1 (NSGA-II only)
**Trigger:** `python demo_app.py` → `/run` Flask route → NSGA-II subprocess (legacy); `/design` page → rule-based composer artifacts on disk

The L3 layer formulates urban-cooling shelter design as a multi-objective optimisation:

- **Variables:** `x_m`, `y_m`, `width_m`, `height_m`, `tilt_deg`, `porosity_pct` (canopy geometry on plaza-local meters)
- **Objectives:** minimise ΔTmrt-site (maximise cooling) + minimise material (scaffold module count)
- **Constraints:** plaza geometry, building exclusion zones, structural feasibility
- **Surrogate:** `delta_tmrt_surrogate()` in `nsga2_coolstock.py` — linear interpolation between Garcia-Nevado 2020 + Vanos 2020 measurements. **Mock until Juan D1-04 lands.** Listed in `MOCKS.md` §1.2.
- **Run parameters:** 100 generations × 100 population, seed 42 (deterministic)
- **Output:** `L1_INGEST_data/nsga2_output/`:
  - `pareto_front.png` — 100-point Pareto front
  - `top3_configurations.json` — `MAX_TMRT_REDUCTION` / `MIN_MATERIAL` / `BALANCED`
  - `cookbook_run.json` — fired patterns + provenance per run
  - `audit_record.json` — per-run audit (gitignored, regenerates every run)

### L4 SIMULATE — CFD field rendering

**Current live path (2026-05-19):** [`scripts/sim/run_infrared_utci_angels.py`](scripts/sim/run_infrared_utci_angels.py) + `_intervention.py` — call the Infrared.city SDK to compute UTCI baseline + intervention on the real Plaça dels Àngels polygon. Results cached to disk so `/rerun_intervention_utci` performs no live call on demo path. Measured 2026-05-19: 28.08 °C → 27.81 °C UTCI delta.

**Legacy mock path (still wired for `/`):** [`infrared_client.py`](infrared_client.py). Now a deprecation banner — `simulate_tmrt()`, `simulate_utci()`, `simulate_wind()` still serve the legacy `/infrared_json` route consumed by the NG3D viewer on `/`. Returns deterministic synthetic fields; demo overlays a "MOCK DATA" hatch when `metadata.backend === 'mock'`. Scheduled for decommission alongside NSGA-II.

**Env vars:** `INFRARED_BACKEND=mock|cached|live` selects the legacy stub backend; `INFRARED_API_KEY` is read by the live SDK path. See `audit/07_reality_check.md` claim 24 for the hybrid state.

### L5 DEFEND — audit + provenance gate

**Module:** [`evaluator.py`](evaluator.py)
**Provenance gate:** [`evaluator.check_data_verification()`](evaluator.py) — called by `evaluate_site()`, which raises `RuntimeError` under `HARD_BLOCK` when any connector is `PENDING` or missing. `DECLARED` partner feeds fire but are flagged `honesty_status="DECLARED_INPUTS"` (two-tier honest gate, resolved 2026-05-20). See `audit/07_reality_check.md` claim 6 + `audit/01_architect.md` C1.
**Firing engine (SPARQL):** `sparql_engine.site_fires_sparql()` — **real rdflib SPARQL** as of 2026-05-20. Each pattern's `if.binds` maps every `?variable` to an ontology property; the engine builds an in-memory RDF graph (one typed triple per bound variable, from L1 site data) and runs the pattern's `sparql_filter` as a genuine `ASK` query through rdflib. This is the default (`FIRING_ENGINE="sparql"` in `evaluator.py`). Proven behaviour-identical to the legacy path via `scripts/sparql_shadow_compare.py` (27/27 agree, 18 fire); locked by `tests/test_sparql_engine.py`.
**Legacy fallback parser:** `evaluator.safe_eval_filter()` — Python AST walk, no `eval()`. Retained as automatic fallback if rdflib is unavailable or a query fails to parse (`FIRING_ENGINE="ast"`).

The L5 layer is what makes the platform defensible. Every per-pattern audit trail is downloadable from the demo's `/audit_json` route:

```json
{
  "site": "Plaça dels Àngels",
  "patterns_fired": ["P01", "P02", "P04", ...],
  "patterns_suppressed": ["P03", "P05"],
  "citation_chain": {
    "P01": {
      "C1_theory": "10.1016/j.scs.2020.102458",
      "C2_data": [{"connector_id": "sentinel_worldcover_angels", "retrieved": "2026-05-12"}],
      "C3_records": [{"site": "Sevilla toldo network 2019", "delivered": "..."}]
    },
    ...
  },
  "hardblock_passes": 18,
  "hardblock_fails": 0
}
```

A reviewer can audit the entire chain from this JSON. No clicks, no guessing, no hallucinated DOIs.

### L6 MONITOR — honesty + feedback

**Manifest:** [`MOCKS.md`](MOCKS.md) (53 items)
**Per-run audit:** `L1_INGEST_data/nsga2_output/audit_record.json` (gitignored, regenerated every run)
**Field deployments:** [`ledger/field_deployments.json`](ledger/field_deployments.json)

The L6 layer documents the current honesty surface. Every entry in `MOCKS.md` has location + reason + concrete replacement path. Pre-merge grep on `mock | MOCK | DECLARED | PENDING | REQUIRES_VERIFICATION | heuristic` must match an entry. New mocks must be added in the same commit.

The ledger captures real-world deployment outcomes (currently empty — no pilot deployed yet; will populate after the first Refugis Climàtics install).

---

## The Stage 1 → 2 → 3 visualisation roadmap

The 3D / spatial-output surface evolves in three stages. We are currently at **Stage 2 v0.1**.

### Stage 1 — SVG plan + section (legacy, still active)

Inline SVG in `demo_app.py` HTML. `drawPlanView(cfg)` + `drawSection(cfg)` consume the active NSGA-II config and redraw on tab switch. Cheap, browser-native, no plugin. Limited to top-down + side-view 2D.

### Stage 2 — WebGL 3D editor in browser (in progress)

**v0.1 (shipped 2026-05-16, commit `463a75c`)** — Three.js scene rendering plaza + 246 OSM-projected buildings + NSGA-II canopy with OrbitControls. Read-only. `/scene_json` route serves projected geometry; module-private state exposed via `window.NG3D_*`.

**v0.2 (next)** — TransformControls on the canopy mesh. New `/surrogate` POST endpoint exposes `nsga2_coolstock` surrogate functions for ad-hoc geometry. Drag-end → recompute ΔTmrt + modules + coverage → cfg cards update live.

**v0.3** — "Re-run NSGA-II from this edit" button. Take user-edited geometry as a constrained starting region; run new NSGA-II; new Top-3.

**v0.4** — Pattern palette. Click P02 → climber strip mesh appears as a child of the canopy. Spatial rules (P25 requires P01, P14 attaches to a building edge) enforced visually.

### Stage 3 — Native-tool bridges (deferred until post-pitch)

Three candidate bridges, all production-grade in AEC:

- **Speckle** (Apache 2.0, self-hostable) — push from Rhino / Grasshopper / SketchUp / Revit → COOLSTOCK reads → recomputes → returns. Architecturally coherent with our open-core + on-prem positioning.
- **Rhino.Inside / Rhino Compute** — Grasshopper definition calls COOLSTOCK as a remote service from inside Rhino.
- **IFC.js / OpenBIM** — read/write IFC in browser, exchange with any BIM tool.

**Atlas Studio was deep-dived 2026-05-16 and ruled out** — see [`phase-2/atlas_studio_integration_assessment_2026_05_16.md`](phase-2/atlas_studio_integration_assessment_2026_05_16.md). Wrong vertical (games not AEC), wrong determinism profile (generative AI), wrong deployment shape (cloud-only Google Cloud, no on-prem).

---

## Coordinate systems

Three CRSes in active use. Conversion happens at well-defined boundaries.

| Where | CRS | Why |
|---|---|---|
| OSM / GBIF / Open Data BCN | EPSG:4326 (WGS84 lat/lon) | Standard for raw geospatial APIs |
| NSGA-II + plan-view SVG + 3D scene | Plaza-local metres | The `x_m / y_m` field names in `top3_configurations.json` — local frame with SW corner of plaza rectangle at origin |
| Spanish cadastre | EPSG:25831 (ETRS89 / UTM zone 31N) | Stated in headers for documentation purposes; not used for computation in v1 |

**Projection in `/scene_json`:** equirectangular with cos-latitude correction. Plaza centroid at `(2.1670, 41.3826)` is the local origin. Accurate within the ±200 m radius the demo cares about; degrades at longer ranges.

Critical: NSGA-II's `x_m / y_m` use a different origin than the 3D scene origin. The 3D scene's plaza is centred at `(0, 0)` with SW corner at `(-30, -30)`. NSGA-II's `(x_m=30, y_m=5)` maps to 3D `(0, 5-30) = (0, -25)` after subtracting half-plaza. Captured in `drawPlanView()` and the `_buildCanopyFor()` Three.js helper.

---

## The honesty contract in 5 bullets

1. Every silently-wrong thing is documented in `MOCKS.md`. If you can't find an entry for a fake thing in the code, that's a bug — open a finding.
2. Every DOI is CrossRef-verified before citation. The deep-research agent has hallucinated. Never trust agent-produced DOIs.
3. Every data source has a `data_manifest.yaml` entry with `status: VERIFIED | PENDING | DECLARED` and a named verifier.
4. Every fired pattern has all three citation slots filled (theory + data + field). Confidence is auto-computed from citation count, never self-rated.
5. Every per-run audit dumps to `audit_record.json` with the full provenance chain.

---

## What lives where (file map)

See [`README.md` § What's in this repo](README.md#whats-in-this-repo-folder-by-folder) for the folder map.

The 8 runtime modules at repo root:

| Module | Layer | What |
|---|---|---|
| `demo_app.py` | L5 + UX | Flask app — single file serving the entire demo HTML + all routes |
| `evaluator.py` | L5 | Per-pattern audit + provenance gate (`evaluate_site()` raises under `HARD_BLOCK`) |
| `nsga2_coolstock.py` | L3 | NSGA-II runner; called as subprocess by `/run` |
| `infrared_client.py` | L4 | CFD client (mock until API key) |
| `bcn_opendata.py` | L1 | Open Data BCN CKAN connector (live, runtime-fetched) |
| `cookbook_runner.py` | L2 + L3 | Cookbook execution orchestrator |
| `firing_trace.py` | L5 | Pattern firing trace utility |
| `generate_june_pitch_deck.py` | non-runtime | Slide generator; stays at root because it imports `evaluator` |

Everything else is in subfolders. See [`scripts/README.md`](scripts/README.md) for the non-runtime utilities.

---

## Performance characteristics

- **NSGA-II run:** ~30 s on a 2024 laptop (100 gen × 100 pop, seed-pinned)
- **Demo cold start:** ~3 s (Flask boot + initial fetches)
- **`/scene_json` first call:** ~80 ms (with 246-building extrusion). Subsequent calls cached by geojson mtime — instant.
- **3D viewer frame budget:** 60 fps stable on integrated graphics with 246 buildings + 1 canopy. Increases linearly with TransformControls drag-recompute load (v0.2).
- **HARD_BLOCK provenance gate:** runs once per pattern per evaluation cycle; <1 ms total for the full 27-pattern cookbook.
- **Open Data BCN fetch:** ~600 ms cold, ~120 ms warm. Cached per session.

---

## Where the architecture is fragile

Honest list of things that would break if you pulled the wrong thread:

1. **The `from evaluator import ...` chain.** `nsga2_coolstock.py` + `demo_app.py` + `cookbook_runner.py` + `firing_trace.py` + `generate_june_pitch_deck.py` all import from `evaluator`. Moving `evaluator.py` out of root breaks all of them.
2. **The `top3_configurations.json` field-name mismatches.** Historical: the JSON used `x_m / y_m`; the JS used `x_position_m / y_position_m`. We've added fallback handling 2026-05-16 (commit `d0c181c`) but adding a third field name would proliferate the problem.
3. **The Three.js scene's `_canopies[]` cache.** Modifying canopies between `NG3D_init()` and `NG3D_refresh()` calls without going through `NG3D_setActiveCfg()` desyncs the cached state from what's rendered.
4. **MOCKS.md `audit_record.json` exclusion.** Gitignored 2026-05-16 to stop noise — but if a reviewer expects to find a per-run audit they may be confused. The audit IS produced, just not committed.
5. **The SPARQL filter AST walk.** `evaluator.safe_eval_filter()` (the legacy fallback path) uses Python AST to evaluate filters safely. Adding new operator types requires updating the AST whitelist in `_walk()`; otherwise the filter silently fails to match. The default path is now `sparql_engine.site_fires_sparql()` — rdflib ASK queries — so this footgun is less likely to be hit.

---

## Glossary

See [`README.md` § Glossary](README.md#glossary-for-teammates-new-to-the-projects-jargon).
