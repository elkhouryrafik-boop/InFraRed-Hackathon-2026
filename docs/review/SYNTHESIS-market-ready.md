# CoolSpend — Concept Review Synthesis & Market-Ready Direction

**Date:** 2026-05-21
**Inputs:** 3 independent reviews — [market/trend](REVIEW-market-trend.md), [product/PM](REVIEW-product-pm.md), [science/geographer](REVIEW-science-geographer.md)
**Purpose:** consolidate findings into one direction; seed the market-ready milestone plan.

---

## Where We Are

v1.0 hackathon submission (CoolSpend / Tree Budget Optimizer) is **complete and shippable**. Engineering discipline is the standout asset: clean `mock|cached|live` SDK boundary, SimBudget guard, seed-pinned determinism, and an honesty ledger (MOCKS.md) that refuses fabricated citations. All three reviewers independently flagged that **the honesty contract is the real moat** with a municipal buyer — keep it, don't erode it.

The gap: it is a credible *framework* wrapped around an *unvalidated model*. The headline KPI ("most UTCI relief per euro") is currently **assumption ÷ assumption**.

## Where All 3 Reviewers Converge (do these)

1. **Surrogate ground-truthing is the existential keystone.** Until ΔTmrt-surrogate is validated against real Infrared UTCI across *varied* configs (not just Top-3), the rankings — the whole product — may be wrong. Run the calibration study FIRST; nearly everything else is downstream. *(PM P0.1, Geographer Fix #4, Market gap #2)*

2. **Tmrt ≠ UTCI — a unit substitution that voids the KPI.** Optimizer maximizes ΔTmrt (capped 12°C) but product sells "UTCI relief." A 12°C Tmrt drop ≈ only ~3–5°C UTCI. **Fix is cheap and ~80% built:** route surrogate ΔTmrt through existing `nature_metrics.py::utci_hours_above()` before forming €/°C. *(Geographer Critical Fix #1)*

3. **Cost model is ~10× too low and unsourced.** €350 CapEx / €35/yr OpEx vs NYC ~$3,300 fully-loaded CapEx + Boston ~$900/tree/yr OpEx. A 10×-low denominator makes €/°C look 10× too good — the exact error a budget auditor catches, and it can *invert* the trees-vs-alternatives ranking. *(all three)*

4. **The product pivot: multi-intervention heat-budget allocator, not "trees only."** "CoolSpend" already promises this. 2025 research converges on "no single best intervention — a tailored mix wins" (trees + cool roofs + shade + water). Allocating ONE budget across competing intervention types by €/°C is genuinely under-served and beats every trees-only incumbent. Make intervention type a *parameter*, not a hardcode. *(Market pivot #1, PM refocus)*

5. **District / portfolio triage IS the MVP; single-plaza is the explainer.** The commercial value is "allocate my whole city's canopy/heat budget across N sites," not optimizing one plaza. Move multi-site triage from "deferred v2" to the core. *(PM P2.3 + refocus, Market pivot #2)*

6. **Go-to-market through grant compliance, not cold municipal procurement.** 88% of cities have no dedicated heat budget; real check-writers are programs — EU LIFE / European Urban Initiative (€60M, deadline 15 Jun 2026, Barcelona-aligned) / Rockefeller Cool Cities. Sell "the allocation appendix that wins your adaptation grant." *(Market — who pays)*

7. **Differentiation is the optimization loop, not "data-driven planting."** Incumbents (i-Tree Landscape, Boston Right-Place-Right-Tree, Azavea/USDA toolkit) already do cost-aware prioritization. The narrow, real edge is **surrogate-optimize-then-validate** (NSGA-II on a fast proxy, physics-grade UTCI only on Top-3) — i-Tree can't optimize placement, ENVI-met is too slow to put in a loop. Pitch that. *(Market positioning)*

8. **No GIS integration = no distribution.** ArcGIS is in ~80% of large cities. Standalone Gradio app is a demo. Need GeoPackage/Shapefile export + ArcGIS/QGIS/i-Tree interop. *(Market gap #4, PM P1.1)*

## Honesty / Relabeling (do before any external claim)

- Drop "validated with Infrared" → "final picks re-simulated with Infrared UTCI" (until surrogate is ground-truthed, "validated" is false).
- Drop the "88% better than naive" figure from external copy (mock-vs-mock).
- Align `CONCEPT_REPORT.md` *down* to match `MOCKS.md` (it oversells "professional-grade CFD," "permaculture engine," "energy exchange"). Understatement is the moat.
- Re-anchor the surrogate ceiling to a *tree + pedestrian-Tmrt* source (Schrodi et al. 2023, NeurIPS CCAI — near-direct analogue; Rahman et al. 2022). Demote Garcia-Nevado (it measures sun-sails surface temp, not trees — wrong intervention AND wrong variable).

## Science gaps to scope honestly (out-of-scope list, not silent omissions)

Soil volume (#1 real constraint), irrigation/water demand (determines if cooling materializes on hot days), species-specific cooling, growth-horizon discounting, subsurface utilities, sightlines, solar access to buildings, root-vs-pavement. Single CRS (UTM 31N) end-to-end + geometry round-trip test to kill the HIGH-severity coordinate footgun.

## Smallest Credible Commercial MVP (PM)

Single-city **validated** deployment with one design partner: (1) real OSM/cadastre geometry + projected CRS; (2) surrogate validated vs real UTCI with published error band shown in-product; (3) cost model from that city's real procurement, user-editable; (4) localized ecological rules; (5) planner-grade GeoPackage + procurement-cost export; (6) per-run audit manifest; (7) **district-level triage view**. Keep the surrogate-then-validate architecture — convert *inputs/outputs* mock→real and one-site→portfolio; don't re-architect.

## Two-Track Recommendation

- **Hackathon (May 27–31):** ship v1.0 exactly as scoped. Add one competitive-landscape slide (name i-Tree/ENVI-met/Forma, state the optimization-layer wedge). Lean pitch on the loop, not "data-driven planting." Hold the honesty line.
- **Product (post-hackathon = this new milestone):** multi-intervention, grant-compliance, optimization-layer-on-top-of-GIS. Surrogate ground-truth study is task #1. Fix cost model + Tmrt→UTCI before any audit-facing number.

## What Must Be True (validate before betting)

Surrogate tracks real UTCI in a tight band · ranking is stable surrogate-vs-truth · a Chief Heat Officer will actually defend a budget on €/°C (5+ real interviews — currently persona is research-derived, not primary) · output enters real planting workflow · per-city cost data is obtainable · the Chief-Heat-Officer-with-budget market is big enough.
