# Phase 6: Cost-Model Credibility - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the €/°C KPI's **cost denominator** survive a budget auditor. Replace the
€350 CapEx / €35-OpEx placeholders with a **fully-loaded, itemized, sourced lifecycle
cost** per tree; let the user **localize the cost table per city** through editable inputs
(KPI recomputes live); and **discount the cooling benefit over the establishment/growth
curve** instead of assuming full canopy on day one.

Scope = cost realism only (COST-03/04/05). Phase 5 fixed the KPI's *unit*; this fixes its
*number*. Geometry ingestion (Phase 7), multi-intervention (Phase 8), audit/export (Phase 9)
are out of scope.

**Carried-forward locked constraints:**
- [[no-mock-production-bar]] (D-15): no arbitrary hardcodes survive — every cost figure is
  either VERIFIED (cited), or DECLARED with a named source anchor + PENDING tag. User-editable.
- Honesty contract: no fabricated DOIs/figures; tag estimates honestly.
- KPI shape from Phase 5 stays: dual units (€/°C + €/UTCI-hour), [lo,hi] interval. The cost
  fix changes magnitude, not the KPI's structure.

</domain>

<decisions>
## Implementation Decisions

### Cost Anchor & Itemization (COST-03)
- **D-01:** Replace the single €350 CapEx / €35/yr OpEx constants with an **itemized
  fully-loaded lifecycle cost**, broken into named line items, each carrying its own
  value + source tag + confidence:
  - Tree stock (nursery, large-caliper street tree)
  - Pit excavation
  - Structural soil / soil cells
  - Guarding / staking / irrigation rig
  - Planting labour
  - Annual maintenance OpEx (watering, pruning, inspection)
- **D-02:** Default magnitude anchored to the cost literature (European-leaning mid-range):
  **CapEx ≈ €3,000/tree** fully loaded (vs the old €350, which only covered stock+labour and
  was ~10× low as a fully-loaded figure); **OpEx ≈ €180/tree/yr**. These are DECLARED defaults
  with named source anchors — NOT presented as verified Barcelona procurement.
- **D-03:** Source tags (no fabricated figures):
  - Whole-life range: Australian street-tree lifetime cost models (€/$2,800–5,300/tree).
  - Fully-loaded CapEx anchor: NYC ~$3,300; OpEx anchor: Boston ~$900/tree/yr (cited via the
    3-review synthesis — tag as reviewer-cited, region US, PENDING EU confirmation).
  - Structural soil ~$79.5/yd³ installed; pruning = 28–30% of municipal tree budgets.
  - European LCC context: German 5-city life-cycle study (Riegel/ScienceDirect 2025) —
    sealed-pit payback ~34 yrs, discount-rate-sensitive (tag PENDING — paywalled, cite venue only).
  - Exact **Barcelona procurement figures = PENDING** — the user supplies them via the editable
    table (D-04); defaults are explicitly labelled "illustrative European mid-range, verify locally".
- **D-04:** Each cost line records `value`, `unit`, `source`, `confidence` (VERIFIED | DECLARED |
  PENDING) so the audit trail and MOCKS.md show exactly what is grounded vs estimated.

### Per-City Configurability (COST-04)
- **D-05:** Cost table is an **editable dataclass + JSON config** (e.g. `coolspend/cost_config.json`
  / a `CostTable` dataclass) — NOT hardcoded module constants. A city/locale loads its own table.
- **D-06:** Gradio **inputs** expose the line items so a user edits them in-product; the €/°C +
  €/UTCI-hour KPI **recomputes live** from the edited values (no recompile). Defaults populate from
  the shipped config; edits override per session.

### Growth-Horizon Discount (COST-05)
- **D-07:** Cooling benefit is **not** assumed full on day one. Model a **canopy growth curve**:
  effective cooling fraction ramps from ~20% at planting toward full canopy over ~**25 years**
  (establishment→maturity). The €/°C KPI integrates benefit over this curve, not a step function.
- **D-08:** Apply a **3.5% social discount rate** (EU / UK Green Book convention) to future
  cooling benefit (and to OpEx) over the horizon. Discount rate is a documented, editable parameter.
- **D-09:** **Horizon = tree functional lifespan ≈ 40 years** (urban sealed-site context). Editable.
- **D-10:** The discounted/ramped benefit flows into the KPI denominator/numerator consistently with
  Phase 5's UTCI routing — the headline becomes € per discounted-lifetime-°C (or €/UTCI-hour),
  carrying the [lo,hi] band. Document the formula.

### Claude's Discretion
- Exact dataclass/config schema + file layout for the cost table (D-05).
- Precise growth-curve functional form (linear ramp vs logistic) given D-07's intent.
- How the discount integral is computed (closed-form vs annual summation).
- Gradio input widget layout (D-06).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `coolspend/cost_model.py` — `CAPEX_PER_TREE_EUR=350`, `OPEX_PER_TREE_YEAR_EUR=35`,
  `OPEX_HORIZON_YEARS=10`, `per_tree_cost()`, `total_cost()`, `cost_per_utci_degree()`
  (Phase 5 already routes through UTCI + dual units + [lo,hi]; extend, don't break its shape).
- `HOURS_PER_DEGC_REF`, `PRE_CALIBRATION_BAND_C` (Phase 5) — keep.
- `coolspend/app*.py` — UI already surfaces the KPI dict (Phase 5); add the editable cost inputs here.
- `MOCKS.md` — the ledger where each cost line's source tag must be recorded.

### Established Patterns
- Standard metric dict shape (`value`/`unit`/`confidence`/`sources`/`note`) — reuse for cost lines.
- Confidence tags VERIFIED | DECLARED | PENDING already used across the codebase.

### Integration Points
- `cost_model.cost_per_utci_degree` is consumed by `optimizer.topsis_rank` / `save_outputs` and
  the app — changing the magnitude flows through automatically; the growth/discount changes the
  per-tree number these read.

</code_context>

<specifics>
## Specific Ideas

- The whole point: a budget auditor must not be able to dismiss the €/°C as "10× too good
  because the denominator is 10× too small." Fully-loaded + sourced + discounted is the fix.
- Defaults must be honestly labelled "illustrative European mid-range — verify against local
  procurement"; the editable table is how a real city makes it defensible.

</specifics>

<deferred>
## Deferred Ideas

- Real Barcelona/Spain procurement figures to replace the PENDING default — user-supplied via the
  editable table; obtaining them is a data-gathering task, not code (could be a future data PR).
- Per-species cost differentiation — currently one cost table; species-specific costs are post-v2.0.
- None pulled into Phase 6 scope beyond COST-03/04/05.

</deferred>

---

*Phase: 06-cost-model-credibility*
*Context gathered: 2026-05-21 via autonomous smart-discuss*
