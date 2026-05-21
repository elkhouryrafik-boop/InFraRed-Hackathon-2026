# Requirements — CoolSpend

Scope for the infrared.city Buildathon (Tree Budget track). v1 = what we demo May 31.
**v2.0 (Market-Ready CoolSpend)** requirements are in the dedicated section below — these are the active milestone. v1.0 requirements are retained as completed history.

## Milestone v2.0 Requirements — Market-Ready CoolSpend

Derived from the 3-review synthesis (`docs/review/SYNTHESIS-market-ready.md`). Goal: convert the credible framework into a defensible product. Keystone = scientific validation (VALID-*); everything else is downstream of it.

### Validation & Scientific Credibility (keystone)
- [ ] **VALID-01**: A user can run a surrogate-vs-Infrared calibration study across 5–10 deliberately varied configurations (not just Top-3) and get an RMSE/R² fit + error band quantifying surrogate accuracy.
- [ ] **VALID-02**: The optimizer's ΔTmrt surrogate is converted to a true UTCI-hours delta (via the existing `utci_hours_above()` / ladybug path) before the €/°C KPI is formed — the KPI reports UTCI, not raw Tmrt.
- [ ] **VALID-03**: A user can verify ranking stability — the Top-3 picks chosen on the surrogate remain the Top-3 (or report rank shift) when each is re-simulated with real Infrared UTCI.
- [ ] **VALID-04**: The €/°C KPI is reported as an uncertainty interval (surrogate ±band propagated), never a bare point estimate.
- [ ] **VALID-05**: Geometry is handled in one projected metric CRS (UTM 31N) end-to-end, with a round-trip consistency assertion before any live SDK call.

### Cost Model Credibility
- [ ] **COST-03**: Per-tree cost is a fully-loaded lifecycle figure (pit excavation, structural soil, guarding, multi-year establishment OpEx) anchored to a cited procurement source — replacing the €350/€35 placeholders.
- [ ] **COST-04**: A user can configure the cost table per city/locale (editable inputs, not hardcoded constants).
- [ ] **COST-05**: The €/°C KPI applies a growth-horizon discount so cooling benefit is modeled over the establishment/growth curve, not assumed day-one.

### Real Geometry & Multi-Site Ingestion
- [ ] **GEO-01**: A user can load arbitrary city geometry from OSM/cadastre for any site (not a hand-authored fixture).
- [ ] **GEO-02**: Collision rejection uses building footprints + carriageway/footway polygons (not street-centreline buffers).
- [ ] **GEO-03**: The data model supports N candidate sites within one project.

### Multi-Intervention Allocation
- [ ] **MULTI-01**: Intervention type is a parameter (trees + cool roofs as the v2 proof pair), not a hardcoded tree assumption.
- [ ] **MULTI-02**: A user can allocate one fixed budget across competing intervention types ranked by €/°C.

### District / Portfolio Triage
- [ ] **TRIAGE-01**: A user can rank N sites by €/°C and receive a citywide budget allocation across sites (not just within one plaza).
- [ ] **TRIAGE-02**: The allocation can be equity-weighted to prioritize heat-vulnerable / overburdened areas.

### Workflow Integration & Export
- [ ] **EXPORT-01**: A user can export the recommended layout as GeoPackage/Shapefile for GIS use.
- [ ] **EXPORT-02**: A user can export a procurement-ready cost summary (PDF/CSV) with line items.
- [ ] **EXPORT-03**: A user can import existing city GIS layers (canopy/heat/LST, e.g. ArcGIS/QGIS/i-Tree) as inputs.

### Grant-Compliance Packaging
- [ ] **GRANT-01**: A user can generate an allocation appendix mapped to a grant reporting template (EU LIFE / European Urban Initiative).

### Defensibility & Audit
- [ ] **AUDIT-01**: Every run emits a reproducible audit manifest (inputs, model + surrogate version, data-source tags, re-run command).
- [ ] **AUDIT-02**: Objective weights are stakeholder-elicited and recorded in the audit trail (replacing developer-default TOPSIS 0.6/0.4).

### Honesty Relabeling
- [ ] **HONEST-01**: `CONCEPT_REPORT.md` is aligned down to match `MOCKS.md` — overclaims removed ("professional-grade CFD", "permaculture engine", "energy exchange").
- [ ] **HONEST-02**: The surrogate's Tmrt ceiling is re-anchored to a tree + pedestrian-Tmrt source (Schrodi 2023 / Rahman 2022); Garcia-Nevado demoted to a shade-structure/surface-temp analogue.
- [ ] **HONEST-03**: "Validated with Infrared" and the "88% vs naive" figure are removed from external copy and replaced with accurate phrasing ("final picks re-simulated with Infrared UTCI").
- [ ] **HONEST-04**: Unmodeled siting constraints (subsurface utilities, soil volume, irrigation/water demand, sightlines, solar access to buildings, root-vs-pavement) are documented as explicit out-of-scope exclusions.

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
- [x] **OPT-01**: NSGA-II (pymoo) over a fixed-length vector of tree coordinates, 2 objectives (thermal relief + ecological coherence) under a budget constraint.
- [x] **OPT-02
**: Fitness uses the fast `delta_tmrt_surrogate` inside the loop — no live SDK call per chromosome.
- [x] **OPT-03
**: Validate the Top-3 Pareto configurations with real (or cached) Infrared UTCI; rank by €-per-°C.

### Decision Artifact
- [x] **DEC-01**: Emit a ranked allocation (which locations to plant, in priority order, within budget).
- [x] **DEC-02**: Emit a before/after comparison (baseline UTCI vs chosen intervention) with the headline delta.

### Web App
- [x] **APP-01**: Gradio app takes a polygon + budget and returns the allocation table + before/after map.
- [x] **APP-02
**: Deployable to Hugging Face Spaces; real API calls visible/loggable in the demo.

### Ship
- [x] **SHIP-01**: `requirements.txt` pinning pymoo 0.6.1, shapely, geojson, numpy, infrared-sdk, gradio.
- [x] **SHIP-02**: README with architecture diagram + a MOCKS ledger documenting the surrogate and any unverified data/citations.
- [x] **SHIP-03**: 2.5–3 min demo video script (live app, real call visible) + short submission description + changelog.

## Future Requirements (post-v2.0)

- Water-feature and shade-structure interventions (v2.0 proves the multi-intervention architecture with trees + cool roofs; add the rest once thermal models exist)
- Per-species cooling coefficients (crown size / leaf-area / density-dependent), soil-volume constraint modeling, irrigation/water-budget objective
- Multi-tenancy, authentication, per-customer data isolation, live-call rate limiting (SaaS hardening — required the moment two cities use it)
- Pricing & packaging (annual per-city license + paid validation onboarding — hypothesis to validate)
- Primary Chief-Heat-Officer discovery interviews (5+) to confirm the €/°C framing and market size before betting on it
- Live "re-run optimizer from a user edit" interaction
- Pollinator/3rd ecological objective (currently degenerate — do not resurrect without validated demand)

## Out of Scope

- NatureGooddest 6-layer platform (SPARQL/cookbook/Neo4j/Flask/Three.js) — not needed to ship the decision
- ML / learned coherence — ruled out (data + latency)
- Satellite segmentation / cool-routing — other tracks
- Full siting due-diligence (utilities, soil volume, sightlines, solar access) — explicitly scoped out and documented per HONEST-04; the tool provides geometric feasibility, not engineering siting sign-off

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
| RULES-01 | Phase 2 — Optimizer Core | Complete |
| RULES-02 | Phase 2 — Optimizer Core | Complete |
| OPT-01 | Phase 2 — Optimizer Core | Complete |
| OPT-02 | Phase 2 — Optimizer Core | Complete |
| OPT-03 | Phase 2 — Optimizer Core | Complete |
| DEC-01 | Phase 2 — Optimizer Core | Complete (02-05) |
| DEC-02 | Phase 2 — Optimizer Core | Complete (02-05) |
| APP-01 | Phase 3 — Web App & Decision UI | Complete (03-02) |
| APP-02 | Phase 3 — Web App & Decision UI | Complete |
| SHIP-01 | Phase 4 — Ship | Complete (04-01) |
| SHIP-02 | Phase 4 — Ship | Complete (04-01) |
| SHIP-03 | Phase 4 — Ship | Complete (04-02) |
| VALID-01 | Phase 5 — Surrogate Ground-Truth & Honesty Reset | Pending |
| VALID-02 | Phase 5 — Surrogate Ground-Truth & Honesty Reset | Pending |
| VALID-03 | Phase 5 — Surrogate Ground-Truth & Honesty Reset | Pending |
| VALID-04 | Phase 5 — Surrogate Ground-Truth & Honesty Reset | Pending |
| VALID-05 | Phase 5 — Surrogate Ground-Truth & Honesty Reset | Pending |
| HONEST-01 | Phase 5 — Surrogate Ground-Truth & Honesty Reset | Pending |
| HONEST-02 | Phase 5 — Surrogate Ground-Truth & Honesty Reset | Pending |
| HONEST-03 | Phase 5 — Surrogate Ground-Truth & Honesty Reset | Pending |
| HONEST-04 | Phase 5 — Surrogate Ground-Truth & Honesty Reset | Pending |
| COST-03 | Phase 6 — Cost-Model Credibility | Pending |
| COST-04 | Phase 6 — Cost-Model Credibility | Pending |
| COST-05 | Phase 6 — Cost-Model Credibility | Pending |
| GEO-01 | Phase 7 — Real Geometry & Multi-Site Ingestion | Pending |
| GEO-02 | Phase 7 — Real Geometry & Multi-Site Ingestion | Pending |
| GEO-03 | Phase 7 — Real Geometry & Multi-Site Ingestion | Pending |
| MULTI-01 | Phase 8 — Multi-Intervention & Portfolio Triage | Pending |
| MULTI-02 | Phase 8 — Multi-Intervention & Portfolio Triage | Pending |
| TRIAGE-01 | Phase 8 — Multi-Intervention & Portfolio Triage | Pending |
| TRIAGE-02 | Phase 8 — Multi-Intervention & Portfolio Triage | Pending |
| EXPORT-01 | Phase 9 — Workflow, Grant Packaging & Audit | Pending |
| EXPORT-02 | Phase 9 — Workflow, Grant Packaging & Audit | Pending |
| EXPORT-03 | Phase 9 — Workflow, Grant Packaging & Audit | Pending |
| GRANT-01 | Phase 9 — Workflow, Grant Packaging & Audit | Pending |
| AUDIT-01 | Phase 9 — Workflow, Grant Packaging & Audit | Pending |
| AUDIT-02 | Phase 9 — Workflow, Grant Packaging & Audit | Pending |
