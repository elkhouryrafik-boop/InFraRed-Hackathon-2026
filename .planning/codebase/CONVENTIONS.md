# Coding Conventions

**Analysis Date:** 2026-06-01

The Python backend lives in `coolspend/` (flat package, ~40 modules + `coolspend/tests/`). The web client lives in `web/` (Vite + React + TypeScript). The defining discipline of this codebase is its **honesty architecture**: every number is tagged by how it was produced (measured vs synthetic) and every cost constant carries a confidence tag (`VERIFIED` / `DECLARED` / `PENDING`). Treat that discipline as a hard convention, not a nicety — it is enforced by tests and is the project's core value proposition.

## Naming Patterns

**Files:**
- Python modules: lowercase `snake_case`, one domain per module — `cost_model.py`, `spatial_engine.py`, `placement_audit.py`, `cooling_estimator.py`, `provenance.py`, `citywide.py`.
- Test modules: `test_<module>.py` co-located in `coolspend/tests/` mirroring the module under test (`cost_model.py` → `tests/test_cost_model.py`).
- Config: `cost_config.json` (editable cost ledger), GeoJSON/JSON artifacts under `coolspend/cache/` and `web/public/`.

**Functions:**
- `snake_case`, verb-first — `audit_trees`, `load_cost_table`, `cost_per_utci_degree`, `reproduce_composite_b`, `verify_scored_grid`, `growth_cooling_fraction`, `discounted_lifetime_degc`, `set_site_origin_from_polygon`, `reset_site_origin`.
- Internal helpers prefixed `_` — `_project`, `_haversine_m`, `_default_dict`, `_reset_site_origin`.

**Variables:**
- `snake_case` locals; physical quantities carry their unit in the name — `facade_setback_m`, `min_spacing_m`, `bbox_margin_m`, `spacing_floor`, `delta_utci_c`, `coverage_fraction`, `ramp_years`, `horizon_years`, `discount_rate`.

**Constants:**
- Module-level `UPPER_SNAKE_CASE` — `DEFAULT_COST_TABLE`, `DEFAULT_GROWTH_DISCOUNT`, `COMPOSITE_B_WEIGHTS`, `SUBSCORE_KEYS`, `SIGNAL_SOURCES`, `HOURS_PER_DEGC_REF`, `PRE_CALIBRATION_BAND_C`, `CAPEX_PER_TREE_EUR`, `OPEX_PER_TREE_YEAR_EUR`, `OPEX_HORIZON_YEARS`.
- Confidence-tag sentinels are themselves named constants in `coolspend/cost_model.py`: `VERIFIED = "VERIFIED"`, `DECLARED = "DECLARED"`, `PENDING = "PENDING"`. Import these by name; do not hardcode the literal strings elsewhere.

**Types:**
- `PascalCase` for dataclasses — `CostLine`, `CostTable`, `GrowthDiscountParams`, `SignalSource`, `TreeViolation`, `AuditReport`.

## Code Style

**Formatting:**
- No `black`/`ruff`/`flake8` config file is committed (no `.ruff.toml`, `setup.cfg`, or `pyproject.toml` formatter section was found). Style is hand-maintained and consistent: 4-space indent, ~88–100 col soft wrap.
- Module headers use section-divider comment bars: `# ── Section name ──────────`. Match this style when adding sections.
- Inline `# noqa:` codes appear (e.g. `# noqa: PLC0415`, `# noqa: BLE001`), implying ruff *can* be run ad hoc with those rule names even though no config is committed. Preserve existing `noqa` annotations.

**Linting (web):**
- `web/` is TypeScript. The gate is the compiler, not a separate linter: `npm run typecheck` (`tsc -b --noEmit`) and `npm run build` (`tsc -b && vite build`). Keep the build type-clean — the paper claims "the web client type-checks and builds clean" as part of the reproducibility posture.

## Module Structure

Every Python module opens with a substantial module docstring that states **purpose, provenance, and modelling choices** — these docstrings are part of the documentation surface, not decoration. Examples:
- `coolspend/cost_model.py` docstring documents every constant's derivation and confidence (CapEx ≈ €2,200/tree, OpEx ≈ €60/tree/yr, horizon = 40 yr) and warns: constants are *derived* from `DEFAULT_COST_TABLE` (single source of truth, "D-15") and must not be redefined independently.
- `coolspend/placement_audit.py` docstring explains *why the audit is a verification, not a retry loop* (placement is valid by construction; the audit re-checks with an independent OSM fetch and never loops). This is the CCA-F P1/P2 discipline (loop completion by structural guarantee, not iteration cap) baked into prose.
- `coolspend/provenance.py` docstring records the exact reproduction of `composite_score_B` (R²=1.0, max abs residual ~2e-16 over 494 grid cells).

**When adding a module, write a docstring in this same register:** what it computes, where each input comes from, and which modelling choices are auditable simplifications.

## Imports

- `from __future__ import annotations` at the top of nearly every module and test (postponed evaluation of annotations is the standard).
- Standard library first (`json`, `os`, `math`, `tempfile`, `dataclasses`, `pathlib`), then third-party, then `from coolspend import ...` / `from coolspend.<mod> import ...`.
- **Lazy/local imports inside functions** are used deliberately to keep optional heavy deps (shapely, numpy, OSM fetchers) from being hard import-time requirements — see `audit_trees` in `coolspend/placement_audit.py` importing `shapely.geometry`, `shapely.ops`, `coolspend.osm_buildings` inside a `try`. Follow this when a dependency is optional; tag with `# noqa: PLC0415`.

## Error Handling — Fail-Open Discipline

The dominant pattern is **fail-open to documented defaults, never crash the pipeline**:
- `load_cost_table()` returns `DEFAULT_COST_TABLE` on a missing path, invalid JSON, or a non-dict JSON root — verified by `TestLoadCostTableFailOpen` in `coolspend/tests/test_cost_config.py`.
- Per-line validation in `cost_table_from_dict`: a non-positive value, an invalid confidence tag, or a missing required key falls back to the default line (or is skipped) rather than raising.
- `audit_trees` catches optional-dependency import failure and OSM-fetch failure and returns an `AuditReport` with a `note` explaining the degradation, instead of throwing.
- Broad `except Exception` is allowed *only* where it is a deliberate degrade-gracefully boundary, and is annotated `# noqa: BLE001`.

This means callers can rely on these functions returning a usable, well-typed result. When you add a loader or external-fetch function, follow the same contract: validate, fall back to a labelled default, attach a `note`.

## Constants & Cost Config (`cost_config.json`)

`coolspend/cost_config.json` is the **editable single source of truth** for the cost model. Each cost line is an object with: `key`, `label`, `value`, `unit`, `kind` (`capex` | `opex`), `source` (a prose provenance string), and `confidence`. A `growth_discount` block holds `ramp_years` (25), `initial_fraction` (0.20), `discount_rate` (0.035), `horizon_years` (40).

**Confidence tags (mandatory on every cost line):**
- `VERIFIED` — cited and independently confirmed (e.g. `annual_opex` €60/tree/yr = BCN IMPJ Activity 0214 2023: €12,658,229 / 206,556 street trees; `guarding` and `planting_labour` from the Diputació de Barcelona replacement grant).
- `DECLARED` — named source anchor + reasonable magnitude, not locally verified (e.g. `tree_stock` €600, `pit_excavation` €500, `structural_soil` €600 — BCN-tender-consistent, "PENDING direct tender unit-price extraction").
- `PENDING` — source identified but unconfirmed/paywalled/region-mismatched (used in `cost_model.py` prose for lifecycle-cost literature).

`REQUIRES_VERIFICATION` appears in `cost_model.py` as the banner over **DECLARED modelling choices** (e.g. the linear growth ramp, the annual-summation discount) — auditable simplifications chosen for inspectability over a closed-form integral. When you introduce a new constant, classify it into exactly one of these buckets and write the source string.

`coolspend/cost_model.py` mirrors the JSON ledger in a comment table and re-derives the legacy module constants from `DEFAULT_COST_TABLE`. Never redefine `CAPEX_PER_TREE_EUR` etc. independently — edit the table/JSON and let them derive.

## Honesty Architecture — measured vs synthetic

The single most important convention. Numbers that reach the user must carry their fidelity:
- `coolspend/cooling_estimator.py` defines a result type whose `is_measured: bool` field is "the single source of truth for the measured-vs-estimate" distinction — `True` only for `cached_utci` / `live_utci` (real Infrared simulation), `False` for the synthetic-scalar surrogate fallback. Alongside it: `fidelity` and `label` fields.
- `coolspend/citywide.py` propagates this as `cooling_is_measured` per site (`cooling_source == "measured_utci"`).
- `coolspend/provenance.py` is the executable record that the citywide composite score is reproducible in-repo, and tags each sub-score's status as `"reproduced"` | `"documented"` | `"residual-gap"` (the residual gap = raw-imagery derivation living in the upstream ingestion pipeline, honestly flagged rather than hidden).

**Rule for new code:** if a value can be either measured or estimated, carry an `is_measured` (or `*_is_measured`) flag with it and never silently present an estimate as a measurement. Provenance/source strings travel with the data, not in side comments.

## Web (TypeScript / React)

- Vite + React 18 + TypeScript 5.6; deck.gl 9 + Mapbox/Cesium for 3D Barcelona viz. Components in `web/src/components/` use `PascalCase.tsx` (`Scene.tsx`, `FallbackScene.tsx`, `IntroVideoGate.tsx`).
- Tests via Vitest (`web/vitest.config.ts`), but the enforced quality gate is the type-check + build.

---

*Convention analysis: 2026-06-01*
