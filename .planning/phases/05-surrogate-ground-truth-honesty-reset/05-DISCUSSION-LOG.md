# Phase 5: Surrogate Ground-Truth & Honesty Reset - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-21
**Phase:** 05-surrogate-ground-truth-honesty-reset
**Areas discussed:** Calibration study + ranking stability, KPI (Tmrt→UTCI + uncertainty), CRS migration to UTM 31N, Honesty reset scope

---

## Gray Area Selection

| Option | Selected |
|--------|----------|
| Calibration study + ranking stability | ✓ |
| CRS migration to UTM 31N | ✓ |
| KPI: Tmrt→UTCI + uncertainty band | (not selected — handled via one coupled question) |
| Honesty reset scope | ✓ |

**User note:** "I have the key btw lol" → live Infrared available; calibration runs real ground-truth.

---

## Calibration Study + Ranking Stability

| Question | Choice |
|----------|--------|
| Calibration backend | **Live, then cache the run** (reproducible offline afterward) |
| Config count / variation | **10, coverage-swept** |
| SimBudget | **Separate study budget** (distinct from Top-3 cap of 3) |
| Ranking stability metric | **Both** (set-overlap headline + Spearman/Kendall correlation) |

---

## KPI: Tmrt→UTCI + Uncertainty Band

| Question | Choice |
|----------|--------|
| KPI denominator after utci_hours_above() | **Report both** — €/°C headline (mean-UTCI °C delta) + € per UTCI-hour reduced |
| Uncertainty band source/format | **Empirical calibration RMSE, as [lo, hi]** |

---

## CRS Migration to UTM 31N

| Question | Choice |
|----------|--------|
| Migration depth | **(free text)** "the [site] can be set anywhere in barcelona" → interpreted as: pyproj UTM-31N mandatory (single-anchor cos-lat approx breaks citywide); per-site origin from polygon UTM bounds; keep local-meters frame derived from UTM (optimizer unchanged). User did not object to interpretation. |
| Round-trip assertion | **Sub-meter (<1 m), before every live call** |

**Notes:** The "anywhere in Barcelona" requirement is the decisive reason — the current
equirectangular cos-lat projection is anchored to the plaza centroid (±200 m validity).

---

## Honesty Reset Scope

| Question | Choice |
|----------|--------|
| Surfaces to scrub | **All four** — CONCEPT_REPORT.md, README + demo script, App UI strings, Audit/artifact JSON |
| improvement_vs_naive_pct fate | **Remove entirely** (delete computation + all references) |
| Citation re-anchoring | **Re-anchor (Schrodi 2023 + Rahman 2022) + demote Garcia-Nevado, update MOCKS** |

**HONEST-04** (out-of-scope exclusions list) captured as mechanical decision D-14 without a
separate question — subsurface utilities, soil volume, irrigation, sightlines, solar access,
root-vs-pavement.

## Claude's Discretion

- KPI conversion math + band propagation details
- pyproj transformer shape + per-site UTM origin computation
- Calibration config-generation mechanism
- Calibration artifact file format
- Pre-calibration band wording

## Deferred Ideas

- Cost magnitude fix → Phase 6 · Real geometry ingestion → Phase 7 · Multi-intervention/triage → Phase 8 · Audit/weights → Phase 9
