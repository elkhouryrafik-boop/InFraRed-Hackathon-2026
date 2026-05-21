# REMEDIATION SUMMARY — Optimizer Degeneracy (Option A)

Branch: `remediation/optimizer-degeneracy`

## Root cause

The NSGA-II Pareto front collapsed to a **single point** (`np.unique(F, axis=0).shape[0] == 1`),
so the "Top-3" allocations were identical in every metric and the €/°C ranking was
meaningless — three labels on one config.

Fix 1 (commit `b4597c8`) had already made `thermal_relief` placement-sensitive via a
non-overlapping canopy union. It was kept, but it did **not** fix the degeneracy. The
deeper cause: the **thermal and ecological objectives were correlated**. Both were
maximised by the *same* layout — 12 well-spread, non-overlapping, 4-species trees:

- Ecological score saturates at **1.0** for any layout where trees are ≥ `MIN_SPACING_M`
  (4 m) apart and species-diverse.
- Because the ecological min-spacing (4 m) is *smaller* than 2× canopy radius (6 m),
  trees could simultaneously be well-spaced (eco = 1.0) **and** cover the site densely
  (max thermal). The thermal optimum therefore also achieved eco = 1.0 and dominated
  everything → single Pareto point.

There was simply **no trade-off** for NSGA-II to spread a front along.

## Decision — Option A: core-weighted thermal coverage

Implemented `core_weighted_coverage_fraction` in `coolspend/spatial_engine.py`, shared
by **both** `thermal_relief` (objective F1) and `optimizer._config_to_geometry` (the
mock-UTCI geometry payload), so the surrogate objective and the mock UTCI stay consistent.

It blends two pure-geometry, deterministic terms:

- **SPREAD term** — non-overlapping canopy union ∩ site, ÷ site area. Maximised by
  dispersing trees (aligned with ecology).
- **CORE-CONCENTRATION term** — a radial, *overlap-counting* sum of each tree's canopy
  area weighted by closeness to the plaza centre (decays to 0 at `CORE_RADIUS_M` = 6 m,
  normalised by `N_CORE_REF` = 6 canopies on-centre). Maximised by **clustering canopy at
  the centre**.

`coverage = (1 - CORE_BLEND)·spread + CORE_BLEND·core_concentration`, `CORE_BLEND = 0.6`.

Because pushing thermal higher means stacking trees near the centre — which drives them
closer than the 4 m ecological min-spacing and lowers the ecological score — the two
objectives now **genuinely compete**. The Pareto front spreads and the €/°C ranking
becomes real on the mock backend.

Constants are DECLARED (REQUIRES_VERIFICATION) and recorded in `MOCKS.md`. No SDK calls
in the hot path; core-weighting is pure shapely/arithmetic geometry.

## Other fixes completed

- **Fix 2 (finalised):** `_config_to_geometry.coverage_fraction` now uses the same
  `core_weighted_coverage_fraction` (placement-sensitive AND consistent with F1).
- **Fix 3 — naive baseline:** `naive_baseline_config` (deterministic evenly-spaced grid,
  valid via `is_valid_location`) + `_build_naive_baseline`; `save_outputs` writes a
  `baseline_naive` block and `improvement_vs_naive_pct` on rank-1; `main.py` prints both.
- **Fix 4 — `select_top3`:** guarantees exactly 3 entries, padding deterministically with
  a distinct `*_DUP` relabel + `padding_note` when the unique front is < 3.
- **Fix 5 — dead expression:** `_result_pop_size(result)` replaces
  `int(getattr(result, "algorithm", None) and 0 or POP_SIZE)` (which always returned
  `POP_SIZE` via short-circuit).
- **Fix 6 — tests:** front-diversity (`np.unique(F).shape[0] > 1`), Top-3 distinct
  delta/€per°C, true seed determinism (seed 42 twice → identical F & X; seed 7 → different),
  naive-baseline present + finite improvement, `select_top3` always-3, and surrogate-level
  core-weighting tests. Double-porosity regression stays green.
- **Fix 7 — MOCKS.md:** rows for the core-weighting constants, changed coverage model, and
  naive baseline. No fabricated citations.

## Before / after

| | Before (degenerate) | After (Option A) |
|---|---|---|
| `np.unique(F, axis=0).shape[0]` (seed 42, pop 60, gen 60) | **1** | **59** |
| Top-3 thermal (ΔTmrt surrogate) | 1.303 / 1.303 / 1.303 | 4.56 / 2.43 / 3.72 |
| Top-3 ecological score | 1.0 / 1.0 / 1.0 | 0.9650 / 1.0000 / 0.9859 |
| Top-3 €/°C | identical | **1,700 / 2,084 / 3,194** (distinct) |
| Naive grid baseline €/°C | (none) | 14,737 (8 trees) |
| Improvement vs naive | (none) | **+88.46%** |

## Verification

- `python -m pytest coolspend/tests/ -q` → **132 passed, 1 skipped** (the skip is the
  live-SDK test requiring an API key), fully offline (mock default).
- `python -m coolspend.main` (mock) decision summary — verbatim:

```
------------------------------------------------------------
DECISION SUMMARY (DEC-01 + DEC-02)
------------------------------------------------------------
  Before (baseline UTCI):  41.0 degC
  After  (rank-1 UTCI):    36.06 degC  (delta = 4.94 degC)
  Best allocation:         MAX_THERMAL_RELIEF (12 trees)
  EUR/degC KPI:            EUR 1,700/degC
  Naive grid baseline:     EUR 14,737/degC (8 trees, delta_utci=0.38 degC)
  Improvement vs naive:    +88.46% cheaper per degC (optimizer vs evenly-spaced grid, same backend)

DISCLAIMER: all surrogate metrics (delta_tmrt_c, topsis_score) carry +/-4 degC uncertainty.
  validated_utci_c is a MOCK synthetic value - NOT MEASURED DATA.
  Use INFRARED_BACKEND=live INFRARED_API_KEY=<key> after May 27 for real UTCI.
------------------------------------------------------------
```

The Stage-4 ranking shows the three distinct €/°C tiers:

```
Stage 4/5  Ranking by EUR/degC KPI (TOPSIS tie-break)...
           Rank 1: MAX_THERMAL_RELIEF    cost=EUR 1,700/degC  topsis=0.9607  trees=12
           Rank 2: BALANCED              cost=EUR 2,084/degC  topsis=0.6060  trees=12
           Rank 3: MAX_ECOLOGICAL        cost=EUR 3,194/degC  topsis=0.0393  trees=12
```

## Honesty note

All thermal/coverage values are analytical surrogates (±4 °C). `validated_utci_c` is the
mock backend (NOT MEASURED DATA) until `INFRARED_BACKEND=live`. The core-weighting premise
(centre worth more than perimeter) is a DECLARED modelling choice, not surveyed data —
see `MOCKS.md`.
