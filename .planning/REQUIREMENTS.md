# Requirements — CoolSpend

Scope for the infrared.city Buildathon (Tree Budget track). v1 = what we demo May 31.

## v1 Requirements

### SDK Boundary
- [x] **SDK-01**: A single `sdk_client` exposes `mock | cached | live` backends selected by `INFRARED_BACKEND`; `live` reads `INFRARED_API_KEY`.
- [x] **SDK-02**: The app runs end-to-end offline on the `mock`/`cached` backend (no key required before May 27).
- [x] **SDK-03**: A `SimBudget` guard caps the number of real (`live`) UTCI calls per run and logs each call.

### Spatial Engine
- [x] **SPATIAL-01
**: Load a site as OSM/GeoJSON (buildings, streets, site boundary).
- [x] **SPATIAL-02
**: `is_valid_location(x, y)` rejects points inside buildings, on street centerlines, or outside the site boundary.
- [x] **SPATIAL-03
**: Coordinates handled consistently (document EPSG:4326 ↔ plaza-local-meters conversion at one boundary).

### Rules Engine
- [x] **RULES-01
**: Minimum-spacing penalty (trees too close are penalized).
- [x] **RULES-02
**: Species-diversity score (rewards a resilient mix; e.g. simple Shannon/count).

### Cost Model
- [x] **COST-01
**: Per-tree cost = CapEx (planting) + OpEx (maintenance) with documented assumptions.
- [x] **COST-02
**: Compute the headline KPI: °C of UTCI relief per euro for a configuration.

### Optimizer
- [ ] **OPT-01**: NSGA-II (pymoo) over a fixed-length vector of tree coordinates, 2 objectives (thermal relief + ecological coherence) under a budget constraint.
- [x] **OPT-02
**: Fitness uses the fast `delta_tmrt_surrogate` inside the loop — no live SDK call per chromosome.
- [ ] **OPT-03**: Validate the Top-3 Pareto configurations with real (or cached) Infrared UTCI; rank by €-per-°C.

### Decision Artifact
- [ ] **DEC-01**: Emit a ranked allocation (which locations to plant, in priority order, within budget).
- [ ] **DEC-02**: Emit a before/after comparison (baseline UTCI vs chosen intervention) with the headline delta.

### Web App
- [ ] **APP-01**: Gradio app takes a polygon + budget and returns the allocation table + before/after map.
- [ ] **APP-02**: Deployable to Hugging Face Spaces; real API calls visible/loggable in the demo.

### Ship
- [ ] **SHIP-01**: `requirements.txt` pinning pymoo 0.6.1, shapely, geojson, numpy, infrared-sdk, gradio.
- [ ] **SHIP-02**: README with architecture diagram + a MOCKS ledger documenting the surrogate and any unverified data/citations.
- [ ] **SHIP-03**: 2.5–3 min demo video (live app, real call visible) + short submission description.

## v2 / Deferred

- Cool-roof and shade-structure interventions (trees-only in v1)
- Multi-site / district triage ranking
- Live "re-run optimizer from a user edit" interaction
- Pollinator/3rd ecological objective (currently degenerate)

## Out of Scope

- NatureGooddest 6-layer platform (SPARQL/cookbook/Neo4j/Flask/Three.js) — not needed to ship the decision
- ML / learned coherence — ruled out (data + latency)
- Satellite segmentation / cool-routing — other tracks

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SDK-01 | Phase 1 — Foundation & SDK Boundary | Complete (01-01) |
| SDK-02 | Phase 1 — Foundation & SDK Boundary | Complete (01-01) |
| SDK-03 | Phase 1 — Foundation & SDK Boundary | Complete (01-01) |
| SPATIAL-01 | Phase 1 — Foundation & SDK Boundary | Complete |
| SPATIAL-02 | Phase 1 — Foundation & SDK Boundary | Complete |
| SPATIAL-03 | Phase 1 — Foundation & SDK Boundary | Complete |
| COST-01 | Phase 1 — Foundation & SDK Boundary | Complete |
| COST-02 | Phase 1 — Foundation & SDK Boundary | Complete |
| RULES-01 | Phase 2 — Optimizer Core | Pending |
| RULES-02 | Phase 2 — Optimizer Core | Pending |
| OPT-01 | Phase 2 — Optimizer Core | Pending |
| OPT-02 | Phase 2 — Optimizer Core | Pending |
| OPT-03 | Phase 2 — Optimizer Core | Pending |
| DEC-01 | Phase 2 — Optimizer Core | Pending |
| DEC-02 | Phase 2 — Optimizer Core | Pending |
| APP-01 | Phase 3 — Web App & Decision UI | Pending |
| APP-02 | Phase 3 — Web App & Decision UI | Pending |
| SHIP-01 | Phase 4 — Ship | Pending |
| SHIP-02 | Phase 4 — Ship | Pending |
| SHIP-03 | Phase 4 — Ship | Pending |
