# Product Review — CoolSpend / Tree Budget Optimizer

**Reviewer:** Alex (Product Manager)
**Lens:** Product / market-readiness gap analysis
**Date:** 2026-05-21
**Artifact under review:** v1.0 hackathon submission (PROJECT.md, STATE.md, SUBMISSION.md, README.md, MOCKS.md, CONCEPT_REPORT.md + code spot-check)

---

## Verdict

**As a hackathon submission: strong. As a commercial product: not yet a product — it's a credible architecture wrapped around an unvalidated model.**

The engineering discipline here is genuinely impressive and rare: a clean `mock|cached|live` SDK boundary, a SimBudget guard that keeps live calls off the NSGA-II hot path, deterministic seed-pinned tests, and — most importantly — an honesty ledger (MOCKS.md) that refuses to fabricate citations or hide the unsourced 12°C cap. That integrity is the single most valuable asset in this repo and it is exactly what a municipal buyer's procurement and technical-review staff will respect. Most "AI for cities" demos lie by omission. This one doesn't. Keep that.

But I have to be direct about the gap between the pitch and the build, because the whole commercial thesis depends on a number that does not currently exist as measured data. The headline claim — "the most degrees of UTCI relief per euro" — rests on a chain where **every link is currently a declared assumption or surrogate**: the site geometry is hand-authored (not OSM), the thermal model is an unsourced analytical proxy with ±4°C uncertainty, the cost constants are unverified, the "88% better than naive" figure is mock-vs-mock, and even the live SDK path has never executed against the real API. The €/°C number — the entire reason a Chief Heat Officer would open this tool — is, today, synthetic times synthetic divided by assumed.

That is fine for May 31. It is disqualifying for a sale. The roadmap from here is not "add features." It is "convert the four mocked layers into validated layers, one at a time, and earn the right to put a euro figure in front of a budget committee." Until the surrogate is ground-truthed against real Infrared UTCI on real geometry, this is a decision-support *framework*, not a decision-support *product*.

**Confidence: ~85%.** I'm reviewing from docs and a code spot-check, not a running instance against the live API (which doesn't exist yet by design). If the May-27 live run confirms the surrogate tracks real UTCI within a tight band, several of my P0s soften considerably.

---

## Value Prop Reality-Check (Claim vs Current Build)

The core framing is excellent and I would not change it: **reframe "where is it hot?" into "where does each euro buy the most cooling?"** That is a real reframe from visualization to decision, and it's the right wedge. The problem is purely in the evidence chain behind the headline number.

| Claim (SUBMISSION/README) | Current Build Reality | Gap Severity |
|---|---|---|
| "Most degrees of UTCI relief per euro" — defensible to a budget committee | Numerator (°C relief) = unsourced surrogate, ±4°C, 12°C cap with no citation. Denominator (€) = declared CapEx/OpEx, unverified. The committee number is assumption ÷ assumption. | **Critical** |
| "Real Infrared UTCI before/after on the top picks" | Live SDK wiring is *implemented but never executed against the real API*. Exact `AnalysesName` enum + `merged_grid` field are TODOs pending May 27. The one "real" run cited in PROJECT.md (Plaça dels Àngels 28.08→27.81°C) is from the *parent* project, not this build. | **Critical** |
| "Given a polygon and a budget" — generalises to any city | Spatial engine is anchored to one hardcoded centroid (lon 2.1670, lat 41.3826), a hand-authored 60×42m rectangle, and an equirectangular CRS approximation valid only "within ±200m of the plaza." Not OSM-fed. One site, not "any polygon." | **High** |
| "88% improvement in cost efficiency vs naive grid" (EUR 1,700 vs 14,737/°C) | Mock-backend vs mock-backend. Both numbers are synthetic. The *delta* is an artifact of the surrogate's core-weighting tuning (CORE_BLEND etc. — themselves declared to make the Pareto front non-degenerate). | **High — do not lead with this number externally** |
| "Validated with Infrared UTCI" | "Validated" here means "the live code path calls the SDK," not "the surrogate's prediction was checked against ground truth." Two different meanings of validation; the marketing one isn't true yet. | **High — word it carefully** |
| Ecological coherence objective | Two sensible rules (spacing + Shannon diversity), but MIN_SPACING_M=4.0 and the species palette are declared, not from Barcelona's Arbrat Viari code. | Medium |

**The honest one-liner the product can defend today:** "A reproducible optimization *framework* that, given site geometry and cost inputs, ranks tree-planting layouts by modeled cooling-per-euro — with an explicit ledger of every assumption." Everything stronger than that requires the validation work below.

---

## JTBD & Adoption Barriers

**The job Maria (Chief Heat Officer) is actually hiring this for is not "optimize tree placement."** That's the feature. The job-to-be-done is: **"Help me defend my heat budget to people who control my budget, and not get blamed when a planting decision is questioned."** It's a *defensibility and accountability* job at least as much as an optimization job. She's hiring a tool to be her expert witness in a budget hearing and her cover when an alderman asks "why this block and not mine?"

That reframing changes what "trust and adopt" requires:

1. **Defensibility > accuracy, at first.** She doesn't need the model to be perfect; she needs to be able to *explain and source* every input when challenged. The honesty ledger is actually a feature here — but right now the answer to "where does 12°C come from?" is "nowhere, it's capped arbitrarily." That's a career risk for her, not just a model caveat. **This is the #1 adoption blocker.**
2. **It must speak procurement, not just thermodynamics.** Her output isn't a Pareto front; it's a line item she can put in a capital plan and an answer to "what did we get for last year's money." The €/°C KPI is the right instinct, but it needs to map to *her* cost categories and her local tree prices, not 350/35/10 placeholders.
3. **It has to plug into how planting actually happens** — GIS handoff to landscape architects, procurement specs, the existing tree inventory/cadastre. A JSON artifact and a Gradio screenshot do not enter a municipal workflow. Where's the shapefile/GeoPackage export?
4. **Someone has to own the recommendation when it's wrong.** A trees-in-buildings collision-gate bug or a CRS error that puts a tree in the wrong spot is a public, physical, expensive mistake. She needs an audit trail (you have `audit_record.json` — good) *and* a validation track record before she'll stake her name on it.
5. **It must survive a technical review by her staff or consultants.** Municipal teams have ecologists and GIS analysts who will poke at MIN_SPACING_M and the species palette. Hardcoded Barcelona-only assumptions break the moment the tool meets a real arborist in another city.

**Bottom line on JTBD:** the product is currently optimized for the *optimization* job (and does it well) but under-built for the *defensibility and integration* job, which is the one that actually closes a deal.

---

## Top Product Gaps (Prioritized)

### P0 — Blocks any credible commercial claim

- **P0.1 Ground-truth the thermal surrogate.** Until ΔTmrt-surrogate is validated against real Infrared UTCI (and ideally field/literature) across a range of geometries, the headline KPI is fiction. Need a published error band ("surrogate predicts UTCI relief within ±X°C of Infrared across N test sites") and a calibration step. *This is the keystone — most other P0s exist because this one is open.*
- **P0.2 Confirm the live path actually works end-to-end.** The whole "real before/after" claim is vapor until the May-27 run confirms `AnalysesName.utci` + `merged_grid` and produces a real delta in *this* repo. Until then, do not say "validated with Infrared" in any external-facing copy.
- **P0.3 Real geometry ingestion (OSM/cadastre).** One hand-authored rectangle anchored to a single centroid is not "any polygon." Need robust OSM/GeoJSON ingestion + a proper projected CRS (UTM/local EPSG, not the ±200m equirectangular hack) before this touches a second city.
- **P0.4 Verify the cost model against real procurement data.** 350/35/10 are placeholders. The €/°C number is meaningless until CapEx/OpEx come from actual municipal tree-cost figures, and ideally are user-configurable per city.

### P1 — Required before a paid pilot

- **P1.1 Export to planning workflows.** GeoPackage/Shapefile/QGIS-compatible output of the recommended layout + a procurement-ready cost summary (PDF/CSV). The JSON artifact is for engineers, not planners.
- **P1.2 Reproducibility & audit trail as a first-class feature.** You have the bones (`audit_record.json`, seed-pinning). Productize it: every run stamped with inputs, model version, surrogate version, data-source tags, and a re-runnable manifest. This is the defensibility job made concrete.
- **P1.3 Localize the ecological + cost assumptions.** Spacing, species palette, costs, and the core-weighting all need to be config-driven and sourced per jurisdiction (Barcelona Arbrat Viari first, as the reference implementation).
- **P1.4 Stakeholder weight elicitation, not developer-default TOPSIS weights.** The 0.6/0.4 thermal/ecological split is "developer judgment." For a real decision, the weights must come from the customer and be recorded as part of the audit trail.

### P2 — Required to scale beyond a single design-partner deployment

- **P2.1 Multi-tenancy + auth.** No tenancy, no auth, no per-customer data isolation today. Required the moment two cities use it.
- **P2.2 Live-call abuse protection.** Already flagged in README (Security M1): a public Space makes 4 live SDK calls per run with no rate limit. Fine for a private demo, unacceptable for an open product.
- **P2.3 Multi-site / district triage.** Currently deferred to v2 — but PROJECT.md itself names "which blocks get trees first" as the direct application. This is likely the *real* enterprise value (portfolio allocation across a city), and single-plaza optimization is the demo, not the deal.
- **P2.4 Pricing & packaging.** Undefined. (See MVP section.)

---

## Smallest Credible Commercial MVP

Not "v1.0 plus features." The smallest thing you can *sell* (or run a paid pilot on) is a **single-city validated deployment with one design partner**, scoped as:

1. **One real city, real geometry.** OSM/cadastre ingestion for that city + proper projected CRS. (Closes P0.3 for one city.)
2. **Surrogate validated against real Infrared UTCI on that city's sites**, with a published error band shown in-product. (Closes P0.1/P0.2 for one city.)
3. **Cost model populated from that city's actual procurement data**, user-editable. (Closes P0.4.)
4. **Localized ecological rules** sourced from that city's planting code. (P1.3.)
5. **Planner-grade export** — GeoPackage layout + procurement cost PDF. (P1.1.)
6. **Audit manifest per run** so every recommendation is reproducible and challengeable. (P1.2.)
7. **District-level triage view** — rank N sites by €/°C, not just trees within one site. *This is what makes it worth paying for; single-plaza is the unit, the city is the product.*

Crucially, the MVP can keep the surrogate-then-validate architecture intact — that design is sound and the SimBudget discipline is a genuine differentiator. The MVP is about converting the *inputs and outputs* from mock to real and from one site to a portfolio, **not** re-architecting.

**Packaging hypothesis (to validate, ~50% confidence):** annual SaaS per-city license tiered by population/canopy-program budget, sold into the climate-resilience / sustainability office, with a paid validation onboarding (the surrogate-calibration + cost-localization work *is* billable services, not free setup). Land with one district program, expand to citywide portfolio triage.

---

## What Must Be True

For this to become a real product, each of these must move from assumption to evidence:

1. **The surrogate tracks real UTCI within a tight, published band.** If the May-27 live run shows the surrogate and Infrared diverge wildly, the optimizer's *rankings* (not just the absolute numbers) may be wrong — and ranking is the whole product. **This is the existential test.** Run it first, on real geometry, across several layouts — not just confirm "the call returns a number."
2. **The optimizer's ranking is robust** — i.e., the Top-3 it picks on the surrogate are still the Top-3 (or close) when each is validated with real UTCI. The current build validates Top-3 but doesn't yet *test ranking stability* against the surrogate's choices.
3. **A Chief Heat Officer will actually stake a budget defense on a €/°C figure** — validate via interviews (you have the persona; do you have the conversations? PROJECT.md cites research-derived persona, not primary interviews). I'd want 5+ real heat-office / urban-forestry interviews confirming the €/°C framing is the number they fight budgets with.
4. **The output enters the real planting workflow** — confirm with a landscape architect / GIS lead what export format and fields make it usable downstream.
5. **Real per-city cost data is obtainable** — if procurement costs are opaque or wildly variable, the €/°C denominator stays soft and the whole KPI weakens.
6. **The market reachable from one persona is big enough** — how many cities have a Chief Heat Officer (or equivalent) with a discretionary canopy budget *and* willingness to buy software? This is a narrow, emerging role; size it before betting the company on it.

---

## Recommended Cuts / Refocus

- **Cut the "88% better than naive" headline from external materials** until it's real-vs-real. Mock-vs-mock improvement numbers are the fastest way to lose technical credibility with a municipal reviewer. Keep it as an internal sanity check only.
- **Cut "validated with Infrared" phrasing** until the surrogate is ground-truthed. Say "the final picks are re-simulated with Infrared UTCI" — accurate — not "validated," which implies the model was checked. Two different claims.
- **Refocus the CONCEPT_REPORT.** It oversells: "professional-grade CFD," "deterministic path," "rigorous evolutionary optimization," "permaculture engine," "energy exchange." The build is honestly 2 simple ecological penalties + an unsourced thermal proxy. The CONCEPT_REPORT and the (excellent, honest) MOCKS.md describe two different products. Align the concept doc *down* to match the honesty ledger, not the ledger up to match the concept. The understatement *is* the moat with this buyer.
- **De-emphasize single-plaza optimization as the product; lead with district/portfolio triage.** The interactive single-plaza demo is a beautiful explainer, but the *commercial* value is "allocate my whole canopy budget across the city." Move multi-site triage from "deferred v2" to "the actual MVP" (see above).
- **Keep and double down on:** the SDK boundary, SimBudget discipline, the honesty ledger, the audit record, and the €/°C reframe. These are the durable assets. Don't let feature pressure erode the integrity contract — it's your differentiator with exactly the buyer you're targeting.
- **Don't re-add the 3rd (pollinator) objective or the ML "learned coherence" path.** Both correctly cut. Resist the temptation; they add scope and degeneracy risk for no validated demand.

---

*Filed by Alex, PM. Happy to pressure-test any of the P0 calls — especially P0.1 — once there's a real May-27 live run to look at. The single most important thing this team can do post-hackathon is the surrogate-vs-Infrared ground-truth study. Everything else is downstream of that one answer.*
