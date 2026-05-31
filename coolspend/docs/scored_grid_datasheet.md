# Datasheet — `scored_grid.geojson` (Barcelona heat-vulnerability grid)

*Closes PAPER.md Limitation #1. Format follows Gebru et al., "Datasheets for Datasets" (2021).*

## Summary

`scored_grid.geojson` is the city-wide heat-vulnerability surface that drives
CoolSpend's **site prioritisation** (which cells to fund). It is **not** a UTCI
field — it answers *where to look*, not *how much cooling a plan delivers*.

**Reproduction status (the headline correction to the paper):** the composite
ranking signal `composite_score_B` is **exactly reproducible from the file
itself** — not "ρ≈0.99," not "external/irreproducible." A least-squares fit over
all 494 cells recovers a single constant weight vector that reconstructs the
published value to floating-point epsilon. Run:

```bash
python -m coolspend.provenance
# → n_cells: 494, max_abs_residual: 0.0, r2: 1.0,
#   recovered_weights == documented weights
```

## Motivation & composition

- **What:** 494 grid cells covering Barcelona, ~400 m × 400 m (≈160,000 m²) each,
  projection EPSG:25831 (UTM 31N).
- **Per cell:** five remote-sensing sub-scores, the composite, administrative
  attributes (`district`, `barri`), existing-tree counts/species, and an
  `intervention_profile` (de-paving / cooling / planting / multi-strategy /
  species-replacement contribution %).

## The composite — exact formula

```
composite_score_B = 0.45·s1_sealed
                  + 0.20·s2_lst_anomaly
                  + 0.15·s3_inverted_ndvi
                  + 0.05·s4_mismatch
                  + 0.15·prpi
```

The weights form a convex combination (sum = 1.0). They are **recoverable from
the data** by ordinary least squares (`coolspend.provenance.verify_scored_grid`
returns `recovered_weights`), so they are documented contract, not assertion.
The per-cell `sN_contribution_pct` fields are the per-cell decomposition
`wᵢ·sᵢ / B · 100` (they equal the `intervention_profile` percentages).

| Sub-score | Weight | Sensor / origin | Reproduction status |
|---|---|---|---|
| `s1_sealed` | **0.45** | Sentinel-1 C-band SAR | composite reproduced; **SAR→sealed classifier upstream** (residual gap) |
| `s2_lst_anomaly` | 0.20 | Landsat 8/9 TIRS thermal | composite reproduced; **anomaly baseline upstream** (residual gap) |
| `s3_inverted_ndvi` | 0.15 | Sentinel-2 MSI optical | (1 − NDVI); documented |
| `s4_mismatch` | 0.05 | Inventory + ecology model | smallest weight; residual gap |
| `prpi` | 0.15 | Derived index | planting-receptivity/permeability; residual gap |

The dominant signal is **sealed surface (45%)**: the top-priority cells are
those that are simultaneously most paved and hottest, exactly the de-paving +
planting use case.

## What is reproduced vs. the residual gap

- **Reproduced exactly (in-repo, zero external data):** the composite formula and
  its weights — i.e. *how the five signals combine into the ranking*. Verified by
  `coolspend/tests/test_provenance.py` (asserts residual < 1e-9 over all cells).
- **Residual provenance gap (honest):** how three of the five sub-scores were
  derived from *raw imagery* — the Sentinel-1 SAR→sealed classifier and its
  training data, the Landsat LST-anomaly baseline definition, and the `s4`/`prpi`
  index formulas — live in an upstream ingestion pipeline (`L1_INGEST_data`) not
  fully documented in this codebase. Closing this requires the ingestion source,
  not a re-run of CoolSpend.

## Recommended uses / out-of-scope

- **Use for:** ranking where in Barcelona to act (relative priority).
- **Do not use for:** absolute cooling magnitude (that is the UTCI sim), or
  outside Barcelona (single-city, single-vintage).

## Maintenance

`coolspend.provenance` is the executable record. If `scored_grid.geojson` is
regenerated, re-run `python -m coolspend.provenance`; a non-zero residual means
the composite formula changed and this datasheet must be updated.
