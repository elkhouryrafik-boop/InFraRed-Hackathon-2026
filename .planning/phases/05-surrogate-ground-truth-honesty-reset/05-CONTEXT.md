# Phase 5: Surrogate Ground-Truth & Honesty Reset - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Quantitatively validate the ΔTmrt surrogate against **real Infrared UTCI**, make the
headline KPI report true UTCI as an **uncertainty interval** over **one UTM-31N CRS**,
and **relabel all external claims down** to what is actually proven.

This is the existential keystone: if surrogate rankings don't hold against measured
UTCI, the rest of v2.0 is built on sand. Scope is validation + honesty only — no new
product capabilities (cost model, multi-site, multi-intervention, export, grants all
belong to Phases 6–9).

**Carried-forward locked constraints (from PROJECT.md / REQUIREMENTS.md):**
- Optimize-on-surrogate, validate-Top-3-with-real-UTCI architecture — convert
  inputs/outputs, do NOT re-architect.
- SimBudget guards every live call; never call live per optimizer evaluation.
- Single CRS conversion boundary (one module owns all coordinate transforms).
- Honesty contract: no fabricated/inferred DOIs; unverified refs tagged PENDING.
- Ship as 2 objectives (thermal + ecological). ML stays ruled out.

</domain>

<decisions>
## Implementation Decisions

### Calibration Study (VALID-01, VALID-03)
- **D-01:** Backend = **live Infrared, recorded to cache**. Run the study live once
  (the API key is available), record every response to cached fixtures so the
  RMSE/R² fit is reproducible offline and CI never burns the key.
- **D-02:** **10 configs, coverage-swept** — span the canopy coverage range
  (low→high tree_count / placement spread) so the fit covers the surrogate's whole
  operating band. (Roadmap allows 5–10; take the upper bound for the tightest band.)
- **D-03:** Calibration uses a **separate study SimBudget** (cap ≈ n_configs + baseline),
  distinct from the Top-3 validation cap of 3. The headline "3 live calls" guarantee
  for the decision artifact stays intact.
- **D-04:** Study output = RMSE + R² + error band quantifying how well surrogate ΔTmrt
  (routed to UTCI, see D-08) tracks real Infrared UTCI across the 10 configs.
- **D-05:** Ranking stability (VALID-03) reported **both ways**: (a) set-overlap headline
  — which of the surrogate Top-3 stayed Top-3 under real UTCI, with any rank swaps named
  explicitly (e.g. "rank 1↔2"); plus (b) a rank-correlation coefficient (Spearman/Kendall τ)
  over the full config set as statistical backing.

### CRS Migration (VALID-05)
- **D-06:** Adopt **pyproj UTM-31N (EPSG:32631)** as the real projected metric CRS.
  **Driving requirement:** the site can be placed *anywhere in Barcelona*, not just the
  fixed Plaça dels Àngels centroid — the current equirectangular cos-lat approx is
  anchored to one point (±200 m validity) and breaks citywide. UTM-31N covers all of
  Barcelona with sub-meter distortion.
  - The single CRS boundary (`spatial_engine`) does WGS84 ↔ UTM-31N properly via pyproj.
  - Site origin is set **per-site** from the chosen polygon's UTM bounds — NOT hardcoded
    to `SITE_ORIGIN_LON/LAT`.
  - Keep the SW-corner local-meters frame **derived per-site from UTM offsets** so the
    optimizer keeps working in `[0, width]×[0, depth]` meters — no rewrite of NSGA-II
    bounds or shapely collision. (Optimizer does NOT move to raw UTM eastings/northings.)
- **D-07:** **Round-trip consistency assertion** (WGS84→UTM→WGS84 and m↔lonlat) within
  **< 1 m**, fired as a guard **immediately before every live SDK call** — the exact
  danger point for the coordinate footgun.

### KPI: Tmrt→UTCI Conversion + Uncertainty (VALID-02, VALID-04)
> Not user-selected as a discussion area — captured here from the one coupled question.
- **D-08:** Route surrogate ΔTmrt through the existing `nature_metrics.py::utci_hours_above()`
  path **before** forming the €/°C KPI — the KPI reports UTCI, never raw Tmrt.
- **D-09:** **Report both units:** primary headline **€/°C** (UTCI-hours-above-threshold
  reduction converted to an equivalent mean-UTCI °C drop, preserving the v1 framing and
  the roadmap's "€/°C KPI") **plus** a secondary **€ per UTCI-hour reduced** (annual hours
  above 32 °C avoided). Both must stay internally consistent and honestly labelled.
- **D-10:** Uncertainty band sourced from the **empirical calibration RMSE** (D-04),
  propagated to the KPI and reported as an interval **[lo, hi]** — never a bare point
  estimate. (Claude's discretion fill: before a calibration artifact exists, the KPI band
  is labelled "pre-calibration, assumed ±4 °C" rather than implying empirical grounding.)

### Honesty Reset (HONEST-01/02/03/04)
- **D-11:** Scrub overclaim/false copy from **all four surfaces**: `CONCEPT_REPORT.md`
  (align down to `MOCKS.md` — remove "professional-grade CFD", "permaculture engine",
  "energy exchange"); **README + demo script** ("validated with Infrared" → "final picks
  re-simulated with Infrared UTCI"); **app UI strings** (Gradio labels/cards/disclaimers);
  **audit/artifact JSON** (disclaimer strings + surrogate flags).
- **D-12:** `improvement_vs_naive_pct` — **remove entirely**: delete the computation
  (`_build_naive_baseline`, `naive_baseline_config`, the `improvement_vs_naive_pct` field)
  and every reference. It is mock-vs-mock and the "88% vs naive" figure must not survive
  anywhere.
- **D-13:** Citation re-anchor (HONEST-02): cite **Schrodi 2023 + Rahman 2022** as the
  tree/pedestrian-Tmrt anchor for the surrogate ceiling; **demote Garcia-Nevado** to a
  shade-structure/surface-temp analogue; record the change in `MOCKS.md`. No fabricated
  DOIs — any unverified ref tagged PENDING. Apply to code docstrings, MOCKS.md, and prose.
- **D-14:** (HONEST-04) Add an explicit **out-of-scope exclusions** list to the external
  docs: subsurface utilities, soil volume, irrigation/water demand, sightlines, solar
  access to buildings, root-vs-pavement. Frame as "geometric feasibility, not engineering
  siting sign-off."

### Production Bar (milestone-wide directive, applies from Phase 5)
- **D-15:** No mocks, hardcodes, or unsourced assumptions may survive into shipped output —
  the product must deliver **data-driven results from real computation**. The only
  acceptable external stand-in is the real Infrared API itself (live key available).
  In Phase 5 this means: calibration runs **live** (D-01, cached-from-live counts as real,
  not mock); the surrogate's unsourced 12 °C cap and the mock-vs-mock naive figure (D-12)
  are removed/re-anchored; the KPI is formed from real converted UTCI (D-08), not raw
  surrogate proxy. Remaining mock surfaces outside this phase's scope (hand-authored site
  fixture → Phase 7; hardcoded cost constants → Phase 6) must be **flagged** by the planner
  as known mock debt with a phase owner, never silently accepted. Default the SDK to a
  real backend path; `mock` is for offline dev only, not demo/production results.

### Claude's Discretion
- Exact KPI math for converting UTCI-hours-above-threshold reduction → equivalent mean
  °C drop (D-09), and how [lo, hi] propagates through the division (D-10).
- pyproj transformer caching / API shape; how per-site UTM origin is computed from the
  polygon bounds (D-06).
- Calibration config-generation mechanism (seeded sweep vs deterministic grid over the
  coverage range) given D-02's "coverage-swept" intent.
- File/format details of the calibration artifact (RMSE/R²/band, rank-stability report).
- Pre-calibration band wording (D-10).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Direction & requirements
- `.planning/ROADMAP.md` §"Phase 5" — phase goal + 5 success criteria (the must-pass bar)
- `.planning/REQUIREMENTS.md` §"Validation & Scientific Credibility", §"Honesty Relabeling"
  — VALID-01..05, HONEST-01..04 acceptance criteria
- `docs/review/SYNTHESIS-market-ready.md` — 3-review convergence; §"Where All 3 Reviewers
  Converge" (items 1, 2) and §"Honesty / Relabeling" are the source of this phase

### Code to modify (source of truth for current behavior)
- `coolspend/spatial_engine.py` — current single CRS boundary (`latlon_to_local_m` /
  `local_m_to_latlon`, equirectangular cos-lat); `delta_tmrt_surrogate`, `thermal_relief`;
  `SITE_ORIGIN_LON/LAT` hardcode to replace (D-06)
- `coolspend/optimizer.py` — `validate_top3_with_infrared` (Top-3 / SimBudget pattern to
  mirror for calibration), `_build_naive_baseline` / `naive_baseline_config` /
  `improvement_vs_naive_pct` (DELETE per D-12), `topsis_rank`, `save_outputs`/`write_audit_record`
- `coolspend/cost_model.py` — `cost_per_utci_degree` (KPI to extend per D-08/09/10)
- `coolspend/sdk_client.py` — `get_baseline_utci`, `get_intervention_utci`, `SimBudget`
  (`mock|cached|live` boundary; calibration recording target for D-01)
- `nature_metrics.py` §`utci_hours_above` (line 125) + `_derive_hourly_tmrt` — the UTCI
  conversion path for D-08

### Honesty surfaces to scrub (D-11)
- `CONCEPT_REPORT.md`, `MOCKS.md`, `README.md` (+ demo script), `coolspend/app.py` /
  `coolspend/app_viz.py` (UI strings)

### Citations (D-13)
- Schrodi et al. 2023 (NeurIPS CCAI, tree/pedestrian-Tmrt) — anchor (verify DOI; tag PENDING if unconfirmed)
- Rahman et al. 2022 — supporting tree-Tmrt anchor
- Garcia-Nevado 2020 — DEMOTE to shade-structure/surface-temp analogue

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `validate_top3_with_infrared(top3, budget)` in `optimizer.py` — the exact
  per-config baseline-then-intervention SDK pattern the calibration study mirrors;
  reuse `_config_to_geometry` / `_build_baseline_geometry`.
- `SimBudget(max_live_calls=...)` in `sdk_client.py` — instantiate a second one for the
  study (D-03).
- `utci_hours_above(threshold_c, coverage_fraction)` in `nature_metrics.py` — already
  computes annual UTCI-hours-above via ladybug `universal_thermal_climate_index`; this is
  the ~80%-built conversion the Tmrt→UTCI fix routes through (D-08).
- `cost_per_utci_degree(config)` in `cost_model.py` — already prefers validated
  `delta_utci_c` over surrogate; extend it to emit both units + [lo, hi] band.

### Established Patterns
- SDK is imported **inside functions only** (never module-top) to keep the optimizer hot
  path SDK-free — calibration code MUST follow this (`# noqa: PLC0415` local imports).
- Every emitted config carries a non-empty `disclaimer`; honesty strings are explicit and
  centralized — extend, don't bypass.
- Seed-pinned determinism (SEED=42) — calibration config generation should be deterministic.

### Integration Points
- `spatial_engine` is the ONLY CRS module — the UTM swap is contained there; callers
  (`optimizer._config_to_geometry`, `_build_baseline_geometry`) import the two conversion
  functions and must keep working unchanged if the local-meters frame is preserved (D-06).
- `app.py` / `app_pipeline.py` / `app_viz.py` consume optimizer outputs — UI string scrub
  (D-11) and the new band/units (D-09) surface here.

</code_context>

<specifics>
## Specific Ideas

- "I have the key" — live Infrared is genuinely available; the calibration study runs real
  ground-truth, not mock-vs-mock. This is what makes the keystone meaningful.
- "The [site] can be set anywhere in Barcelona" — the operative reason UTM-31N is mandatory
  rather than a nicety; the single-anchor cos-lat approx cannot serve a citywide site picker.

</specifics>

<deferred>
## Deferred Ideas

- Cost-model credibility (€350/€35 → fully-loaded sourced lifecycle, per-city editable,
  growth-horizon discount) — **Phase 6** (COST-03/04/05). The KPI denominator fix here
  (D-08/09/10) is unit-correctness; the *magnitude* fix is Phase 6.
- Real OSM/cadastre ingestion + N-site data model — **Phase 7** (GEO-01/02/03). Phase 5's
  "anywhere in Barcelona" CRS work (D-06) is the projection foundation that ingestion builds on.
- Multi-intervention / portfolio triage — **Phase 8**. Audit manifest + stakeholder weights — **Phase 9**.

None of these were pulled into Phase 5 scope — discussion stayed within validation + honesty.

</deferred>

---

*Phase: 05-surrogate-ground-truth-honesty-reset*
*Context gathered: 2026-05-21*
