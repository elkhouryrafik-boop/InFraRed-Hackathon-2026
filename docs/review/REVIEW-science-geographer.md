# Scientific & Spatial-Methodology Review — CoolSpend / Tree Budget Optimizer

**Reviewer lens:** Physical/human geography + microclimate science (Tmrt/UTCI, urban forestry, GIS/CRS).
**Date:** 2026-05-21
**Scope reviewed:** `CONCEPT_REPORT.md`, `.planning/PROJECT.md`, `MOCKS.md`, `.planning/codebase/CONCERNS.md`, `nature_metrics.py`, `nature_architecture.md`.
**Citation policy:** Every external claim below is grounded in a real, retrievable source with a URL. Where I could not verify a number to the paper's own text, I wrote **needs verification** rather than inventing a figure. I did not fabricate any DOI.

---

## Verdict

**Conditional pass as a decision-support *prototype*; fail as a public-budget audit tool — in its current framing.**

The architecture is scientifically literate and unusually honest: the team has already self-disclosed the surrogate-vs-CFD split, the unsourced 12 °C cap, the Garcia-Nevado citation mismatch, the degenerate 3rd objective, and the CRS footgun. That candour is the project's strongest scientific asset and should be foregrounded, not buried.

However, the review surfaced **one error of kind, not just degree**, that the team has *not* fully called out and that undermines the headline KPI:

> **The optimizer maximizes a ΔTmrt surrogate (capped at 12 °C) but the product sells "UTCI relief per euro." Tmrt and UTCI are not interchangeable, and the conversion is non-linear and roughly an order of magnitude.** A 12 °C Tmrt drop in shade typically corresponds to only ~3–5 °C of UTCI relief, because UTCI folds Tmrt together with air temperature, wind, and humidity, and air temperature barely changes under a single plaza's worth of trees. Optimizing on Tmrt and reporting €/°C-UTCI without an explicit, validated Tmrt→UTCI transfer is a category substitution that a competent jury reviewer (or a city auditor) will catch.

This is fixable inside the hackathon window, mostly through honest relabeling and one validated conversion step, not new modeling. The verdict is "conditional" precisely because the fix is cheap.

---

## Thermal Surrogate Critique

### 1. Tmrt is the right *driver* but the wrong *unit* to report

The science backs the team's instinct that radiation load (Tmrt) is the dominant lever for daytime pedestrian heat stress, and that tree shade is the dominant way to cut it:

- Radiation loading quantified as Tmrt is the key factor driving poor daytime thermal comfort, and street trees act primarily by shading shortwave radiation ([Rahman et al. / "Maximizing the pedestrian radiative cooling benefit per street tree", *Sci. Total Environ.* 2022](https://www.sciencedirect.com/science/article/pii/S0169204622002572)).
- Measured shade-vs-sun Tmrt differences in real streets reach **~13–27 °C** depending on canopy density and species ([Variations in pedestrian Tmrt based on spacing/size of street trees, *Sustainable Cities & Society* 2019](https://www.sciencedirect.com/science/article/abs/pii/S2210670718314173); species effects up to ~26.8 °C reported in the cooling-effect review, [*Theor. Appl. Climatol.* 2025](https://link.springer.com/article/10.1007/s00704-025-05904-2)).

So a 12 °C Tmrt-reduction *cap* is **not implausible as a Tmrt ceiling** — it sits at the low end of the measured range. The problem is downstream:

- **The product reports UTCI relief, and UTCI ≠ Tmrt.** UTCI rises ~10 °C above air temperature under a full clear-sky radiant load but converges to air temperature in shade; the Tmrt→UTCI mapping is **non-linear and condition-dependent** ([Blazejczyk et al., "Comparison of UTCI to selected thermal indices", *Int. J. Biometeorol.* 2012](https://link.springer.com/article/10.1007/s00484-011-0453-2); see also the radiant-load dependency figures in [Bröde et al. UTCI sensitivity work](https://www.researchgate.net/figure/The-dependency-of-the-UTCI-on-the-difference-between-mean-radiant-temperature-and-air_fig3_255968995)).
- Real-world daytime **UTCI** reductions from shade are typically **~1.5–5 °C**, far smaller than the Tmrt reduction (arcade daily-mean UTCI relief ~4.4 °C; E–W street tree UTCI relief 1.5–2.5 °C in the search-grounded sources above). The team's own `nature_metrics.py` correctly computes UTCI via `ladybug_comfort` (ISO-grounded), so the machinery to report UTCI honestly *exists* — it is just not the quantity NSGA-II optimizes on.

**Recommendation:** Either (a) relabel the optimizer objective and KPI as **ΔTmrt** (the thing actually optimized) and report UTCI only on the Top-3 validated picks, or (b) insert a validated Tmrt→UTCI conversion (run `universal_thermal_climate_index` over the EPW hours at baseline-Tmrt and surrogate-reduced-Tmrt, exactly as `utci_hours_above()` already does) so the surrogate's Tmrt deltas are translated into UTCI deltas *before* the €/°C KPI is formed. Option (b) is preferable and is already 80% built in `nature_metrics.py`.

### 2. The Garcia-Nevado citation mismatch is worse than disclosed — wrong intervention *and* wrong variable

The team disclosed that Garcia-Nevado 2020 measures **surface temperature, not Tmrt at 1.1 m**. Verification shows a second, larger mismatch: the paper is about **textile sun sails / awnings in Córdoba**, not trees:

- Garcia-Nevado et al. 2020, *Sustainable Cities & Society*, measures **urban textile shading devices** (sun sails) via time-lapse IR thermography in Córdoba streets — ground-temperature reductions up to ~16 °C, façade up to ~6 °C ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S2210670720306788)). This is a **shade-structure** study, not an urban-forestry study.

So the surrogate's lower anchor is derived from a *non-tree, surface-temperature* measurement and used as a *tree, pedestrian-Tmrt* ceiling. That is two substitutions stacked. The transpirational cooling that a real tree adds (and a sun sail does not) is structurally absent from the anchor — see point 4.

**Recommendation:** Re-anchor the surrogate's Tmrt ceiling to a tree-and-Tmrt source. The strongest available precedent is **Schrodi et al. 2023 (NeurIPS Climate Change AI workshop)**, which trains a neural surrogate for point-wise Tmrt to optimize tree placements in Freiburg ([arXiv:2310.05691](https://arxiv.org/abs/2310.05691); [code](https://github.com/lmb-freiburg/tree-planting)). Even if you do not adopt their model, citing it (a) fixes the citation-domain mismatch and (b) shows the jury you know the state of the art. Rahman et al. 2022 (above) gives per-tree pedestrian radiative-cooling magnitudes for a tree+Tmrt anchor.

### 3. Time-of-day, season, and wind/humidity are collapsed away

The surrogate is a static, single-condition reduction. Real Tmrt/UTCI relief is strongly time- and geometry-dependent:

- Tmrt relief is concentrated in midday/afternoon clear-sky hours; at night air temperature dominates and shade relief approaches zero ([Las Vegas street-tree study, *Environ. Res.: Climate* 2025](https://iopscience.iop.org/article/10.1088/2752-5295/ade17d)).
- Benefit is highly sensitive to **street orientation and sun azimuth** (E–W streets benefit most for the heat-exposed hours) — same sources as above. The single 15:00-July sun position hard-coded in `plaza_shaded_fraction()` (alt 58°, azi 228°) is a reasonable *design-hour* snapshot but cannot represent annual relief, and the optimizer should not be tuned to one instant.
- **Wind and humidity are first-class UTCI inputs but only weakly differentiate tree configurations** (species differences in wind/RH are small per the spacing/size study), so they are *defensible to hold constant within a site* — but they must be held at honest, documented values, and they are exactly why a Tmrt drop does not translate 1:1 to UTCI.

**Recommendation:** Keep the static surrogate inside the NSGA-II hot path (correct for the sim-budget constraint), but report the KPI against an **annual or design-day UTCI-hours** integral (the `utci_hourly_histogram()` already produces this) rather than a single instantaneous ΔTmrt. State the design hour/season explicitly on every figure.

### 4. Shade-only model omits transpiration — directionally conservative, but state it

The surrogate models shade (radiation interception) only. Literature consensus is that **shading is the primary cooling mechanism but transpiration is a real secondary term**, contributing on the order of ~30% of solar-heating offset *when the tree is watered*, and collapsing under drought:

- Shading is the primary driver; evapotranspiration secondary, but latent heat compensated ~33% of solar heating even at 39 °C air temp **when soil moisture allowed** ([High transpirational cooling despite heatwaves, *Urban Forestry & Urban Greening* 2025](https://www.sciencedirect.com/science/article/pii/S1618866725001530); [soil-moisture/ET thermal-comfort study, *npj Urban Sustainability* 2025](https://www.nature.com/articles/s42949-025-00220-0)).
- Crucially: **extensive planting + full irrigation were still insufficient to remove heat stress on extreme days** ([WRI cooling-potential synthesis](https://www.wri.org/insights/urban-trees-cooling-potential)). The tool should not over-promise relief on the worst days, which are the days a Chief Heat Officer cares about most.

A shade-only surrogate therefore **under-counts** typical-day relief (omits transpiration) but **over-counts** if it ignores the drought/irrigation dependency. Net effect: acceptable for a conservative prototype if labeled "shade-only, irrigated-tree assumption."

---

## Ecological Rules Critique

### What is sound

- **30-20-10 diversity rule is correctly attributed and real.** Origin is Santamour (1990), "Trees for urban planting: diversity, uniformity, and common sense" (METRIA proceedings): ≤10% any species, ≤20% any genus, ≤30% any family ([DeepRoot summary](https://www.deeproot.com/blog/blog-entries/is-the-10-20-30-rule-for-tree-diversity-adequate/); [Garden Professors origin note](https://gardenprofessors.com/where-did-the-10-20-30-rule-come-from-is-it-adequate/)). **Caveat the team should add:** the rule is a rule of thumb that has been *critiqued as insufficient* — Kendal et al. and others find limited empirical support and argue it under-protects against multi-host pests ([Global patterns / 10-20-30 evidence test, *Urban Forestry & Urban Greening* 2014](https://www.sciencedirect.com/science/article/abs/pii/S1618866714000387)). Present it as a **floor**, not a guarantee.
- **Minimum spacing exists as a real arboricultural concern** (root competition, canopy collision), and `MIN_SPACING_M=4.0` is in the plausible range for small/medium street trees — but it is correctly tagged DECLARED, not sourced to Barcelona code.

### What is weak or missing

1. **Diversity is enforced over a 4-species demo palette** (`platanus, celtis, tilia, quercus`). With only 4 genera you can technically satisfy 30-20-10, but the palette is unverified against Barcelona's **Arbrat Viari** recommended-species list. *Platanus* in particular is a poster child for the over-planting problem the rule exists to prevent (plane-tree anthracnose, and it is already dominant in Barcelona) — recommending more *Platanus* would be ecologically backwards. **Needs verification against the Arbrat Viari zona list.**
2. **No species-specific cooling.** The surrogate treats all trees as one shade fraction (0.80) and one canopy radius (3.0 m). Cooling efficacy is strongly species- and trait-dependent (crown size, leaf area, density) per the cross-city efficacy study ([*Communications Earth & Environment* 2024](https://www.nature.com/articles/s43247-024-01908-4)). A diversity objective that ignores per-species cooling can trade away thermal performance for diversity *without the model knowing it*.
3. **No water demand / soil-moisture coupling.** The single biggest determinant of *whether the cooling actually materializes on a hot day* is soil moisture/irrigation (sources in Thermal Surrogate §4). A Mediterranean drought-prone site (Barcelona) optimized for cooling without an irrigation/water-budget term is optimistic. At minimum, flag water demand as an OpEx driver.
4. **No soil volume constraint.** Standard pits (~0.6×0.6×0.6 m) are inadequate for mature canopy; structural soil/soil-cell systems need ~3+ m³ ([GreenBlue Urban planting constraints](https://greenblue.com/na/urban-tree-planting-constraints/)). The model assumes mature-canopy shade (0.80 fraction, 3 m radius) without guaranteeing the rootable volume that produces that canopy. This is a **20-year promise made on a 0.6 m³ pit** unless soil volume is modeled.
5. **No growth horizon.** "Mature canopy" is years 15–30. CapEx buys a sapling; the cooling KPI assumes the adult. The €/°C should be discounted over an establishment-and-growth curve, not applied to a day-one tree.

---

## Spatial Methodology Gaps

### CRS / coordinate approximation

- **The equirectangular + cos-latitude local-metre approximation is acceptable *at this scale*** (±200 m around the plaza centroid at 41.38° N). Distortion over a few hundred metres is sub-metre and well below tree-placement tolerance. The team's own note ("accurate within ±200 m, degrades at longer ranges") is correct.
- **The real risk is the three-CRS coexistence and the origin offsets**, which `CONCERNS.md §2.4` rates HIGH and I agree: WGS84 (4326) inputs, plaza-local metres for NSGA-II, UTM 31N (25831) in cadastre headers, *plus* a separate 3D-scene origin with a SW-corner shift. A single mis-handled offset puts trees in plausible-but-wrong locations and the Infrared API will happily return valid-looking UTCI for the wrong geometry — a **silent** failure. **Recommendation:** pick one projected metric CRS (UTM 31N is the honest choice for Barcelona), convert once at ingest, and assert frame-consistency before the first SDK call (the proposed `test_coordinate_frame.py`).

### OSM collision realism

- Treating buildings, street centrelines, and existing greenery as hard constraints is a reasonable first cut, but **street *centrelines* are not the planting exclusion zone** — the carriageway, parking lanes, and footway widths are. Collision against a centreline either over- or under-constrains depending on street width. Use building footprints + carriageway/footway polygons, not centreline buffers, if the OSM data supports it.

### Real siting constraints that are ignored (and that an auditor will ask about)

Grounded in [GreenBlue Urban constraints](https://greenblue.com/na/urban-tree-planting-constraints/) and the [root–pavement conflict review, *Urban Ecosystems*](https://link.springer.com/article/10.1023/A:1024046004731):

1. **Subsurface utilities** (water, gas, electric, telecoms, metro tunnels in Raval) — frequently the binding constraint on where a pit can physically go.
2. **Root-vs-pavement / curb conflict** — mature roots heave pavement near old clay/cast-iron drains; a real siting model keeps trees off shallow-utility corridors.
3. **Sightlines / traffic visibility** at junctions and crossings.
4. **Solar access to buildings** — a tree optimized purely for pedestrian shade may overshadow south-facing windows and *raise* winter heating demand; deciduous species on south/west mitigate this ([USDA urban watershed forestry guidance](https://www.in.gov/dnr/forestry/files/fo-UrbanWatershedForestryPart_3.pdf)). This is a genuine multi-objective tension the tool currently ignores.
5. **Soil volume availability** (see Ecological §4) — arguably the #1 real constraint.

None of these are hackathon-blockers, but the report should **list them as known exclusions** so the tool is honestly scoped as "geometric feasibility, not full siting due-diligence."

---

## KPI Validity — "Carbon of Stress Relief" / €-per-°C

**Assessment: methodologically meaningful in principle, currently a vanity metric in execution.** Three problems, in order of severity:

1. **Unit mismatch (fatal if unfixed).** €-per-°C is computed against a Tmrt surrogate but sold as UTCI relief (see Thermal §1). Until the denominator is a *validated UTCI* delta, the ratio is precise but not accurate. The framing "annual reduction in high-heat UTCI hours per unit of cost" (CONCEPT_REPORT §4) is actually the *right* denominator — `utci_hours_above()` produces exactly that — so the fix is to make the KPI use UTCI-hours, not instantaneous ΔTmrt.

2. **Cost denominator is ~10× low and unsourced.** `CAPEX_PER_TREE_EUR=350` is tagged DECLARED. External benchmarks: NYC reports **~$3,300 fully-loaded per street tree** (excavation, soil, guarding, 2-yr establishment) ([Forest for All NYC](https://forestforall.nyc/costs-city-plant-tree-why/)); UK street-tree CBA work and planting-cost guides put establishment well above bare sapling price ([GreenBlue/Treeconomics Street Tree CBA 2018, PDF](https://www.treeconomics.co.uk/wp-content/uploads/2018/08/GBU_Street-Tree-Cost-Benefit-Analysis-2018.pdf)). A €350 figure looks like nursery + plant labour only and **omits pit excavation, structural soil, guarding, and the mandatory 2-year maintenance** that dominate real street-tree CapEx. If the denominator is 10× low, the €/°C is 10× too good — exactly the kind of error a budget auditor exists to catch. **Needs verification against Barcelona/Spanish municipal procurement.**

3. **No counterfactual discipline beyond a self-defined naive grid.** The `improvement_vs_naive_pct` vs an evenly-spaced grid is a good honest move, but the grid is a DECLARED heuristic, not a real municipal default. For a budget claim you need to beat *what the city would actually do*, not a strawman.

**Verdict on the KPI:** Keep it — €/°C-relief is a legitimate and decision-useful cost-effectiveness ratio (it is the spatial-planning analogue of cost-per-QALY). But it is only credible once (a) the denominator is validated UTCI-hours, (b) the cost reflects fully-loaded lifecycle cost, and (c) it is reported with an uncertainty band, not a point estimate. As currently wired it would lose to scrutiny.

---

## Validation Requirements for Credibility (for a public-budget audit)

Ranked by how much credibility each buys per unit of effort:

1. **Surrogate-vs-truth calibration curve.** Run the Infrared SDK UTCI on a handful (5–10) of *deliberately varied* configurations, not just the Top-3, and plot surrogate-ΔTmrt (and its UTCI translation) against measured UTCI. Report R² and RMSE with an error band. This single figure converts "trust me" into "here is the residual." The Top-3-only validation proves the pipeline runs but **cannot characterize surrogate error**, which is what an auditor needs.
2. **Tmrt→UTCI transfer validation.** Show that running the EPW-hour UTCI computation on baseline vs surrogate-reduced Tmrt reproduces the SDK's UTCI delta on the validated configs. This closes the unit-mismatch gap.
3. **Lifecycle cost sourcing.** Replace €350 with a sourced, fully-loaded figure (CapEx incl. pit/soil/guarding + multi-year OpEx), discounted over a growth horizon. Cite the procurement source.
4. **Sensitivity / uncertainty propagation.** The ±4 °C surrogate uncertainty (per the parent audit) must propagate into the €/°C band. A KPI without an interval is not auditable.
5. **Independent baseline.** Validate against a real published municipal planting pattern if one exists, not only the self-defined naive grid.
6. **Geometry round-trip test.** Assert OSM→local-metre→SDK-payload coordinate consistency before any live call (the HIGH-severity CRS footgun).
7. **Document the design hour/season and the irrigated-tree assumption** on every result, so no one mistakes a 15:00-July shade snapshot for an annual or extreme-day guarantee.

---

## Prioritized Fixes

| # | Severity | Fix | Effort | Why it matters |
|---|----------|-----|--------|----------------|
| 1 | **CRITICAL** | Stop reporting the raw ΔTmrt surrogate as "UTCI relief." Pipe surrogate-ΔTmrt through the existing `utci_hours_above()` / ladybug UTCI to produce a real UTCI-hours delta, and form €/°C on *that*. | Low (reuse `nature_metrics.py`) | Fixes the category error that voids the headline KPI. |
| 2 | **HIGH** | Re-source the surrogate's Tmrt ceiling to a *tree + pedestrian-Tmrt* reference (Schrodi 2023 / Rahman 2022); demote Garcia-Nevado to "shade-structure analogue, surface-temp." Keep the 12 °C cap only if it falls inside the cited tree-Tmrt range, with an error bar. | Low | Removes the double citation mismatch (wrong intervention + wrong variable). |
| 3 | **HIGH** | Replace €350 with a fully-loaded, sourced lifecycle cost (pit + soil + guarding + multi-year OpEx), discounted over a growth horizon; report €/°C as an interval. | Med | Denominator is ~10× low; this is the auditor's first attack. |
| 4 | **HIGH** | Add a surrogate-vs-Infrared calibration plot over 5–10 varied configs (not just Top-3). Report RMSE/R² + ±4 °C band. | Med | Only thing that turns the surrogate from "asserted" into "characterized." |
| 5 | **MED** | Assert one CRS end-to-end (UTM 31N), convert once, test geometry round-trip before any SDK call. | Low–Med | Prevents silent spatially-wrong UTCI. |
| 6 | **MED** | Caveat 30-20-10 as a *floor*, verify the species palette against Arbrat Viari, drop/justify *Platanus*, and add at least a coarse per-species cooling weight so diversity cannot silently trade away cooling. | Med | Ecological objective is currently cooling-blind and palette-unverified. |
| 7 | **MED** | List ignored real siting constraints (utilities, soil volume, sightlines, root-vs-pavement, solar access to buildings) as explicit out-of-scope exclusions; flag soil-volume + irrigation as the constraints most likely to invalidate the cooling promise. | Low | Honest scoping; pre-empts the "but you can't actually plant there" question. |
| 8 | **LOW** | Keep shipping as 2-objective (thermal + ecological); do not resurrect the degenerate pollinator objective. State the design hour/season + irrigated-tree assumption on every figure. | Trivial | Already the team's plan; just hold the line. |

---

### Sources

- Maximizing the pedestrian radiative cooling benefit per street tree (Rahman et al., 2022): https://www.sciencedirect.com/science/article/pii/S0169204622002572
- Variations in pedestrian Tmrt based on spacing/size of street trees (2019): https://www.sciencedirect.com/science/article/abs/pii/S2210670718314173
- A study of the cooling effect of urban trees (review, Theor. Appl. Climatol. 2025): https://link.springer.com/article/10.1007/s00704-025-05904-2
- Blazejczyk et al., Comparison of UTCI to selected thermal indices (Int. J. Biometeorol. 2012): https://link.springer.com/article/10.1007/s00484-011-0453-2
- UTCI dependency on (Tmrt − Tair) figure: https://www.researchgate.net/figure/The-dependency-of-the-UTCI-on-the-difference-between-mean-radiant-temperature-and-air_fig3_255968995
- Effectiveness of street trees in reducing air temperature / heat exposure, Las Vegas (Environ. Res. Climate 2025): https://iopscience.iop.org/article/10.1088/2752-5295/ade17d
- Garcia-Nevado et al. 2020, urban textile shading devices via time-lapse thermography (Córdoba): https://www.sciencedirect.com/science/article/abs/pii/S2210670720306788
- Schrodi et al. 2023, Climate-sensitive Urban Planning through Optimization of Tree Placements (arXiv): https://arxiv.org/abs/2310.05691 — code: https://github.com/lmb-freiburg/tree-planting
- High transpirational cooling by urban trees despite heatwaves (Urban For. Urban Green. 2025): https://www.sciencedirect.com/science/article/pii/S1618866725001530
- Impact of soil moisture on urban tree evaporative cooling & thermal comfort (npj Urban Sustainability 2025): https://www.nature.com/articles/s42949-025-00220-0
- Cooling Potential of Urban Trees (WRI synthesis): https://www.wri.org/insights/urban-trees-cooling-potential
- Cooling efficacy of trees determined by climate, morphology, tree trait (Comms Earth & Environment 2024): https://www.nature.com/articles/s43247-024-01908-4
- Santamour 30-20-10 origin & critique (DeepRoot): https://www.deeproot.com/blog/blog-entries/is-the-10-20-30-rule-for-tree-diversity-adequate/
- 10-20-30 rule origin note (Garden Professors): https://gardenprofessors.com/where-did-the-10-20-30-rule-come-from-is-it-adequate/
- Global patterns of urban-forest diversity / 10-20-30 evidence test (Urban For. Urban Green. 2014): https://www.sciencedirect.com/science/article/abs/pii/S1618866714000387
- It costs the city ~$3,300 to plant a tree (Forest for All NYC): https://forestforall.nyc/costs-city-plant-tree-why/
- Street Tree Cost-Benefit Analysis (GreenBlue/Treeconomics 2018, PDF): https://www.treeconomics.co.uk/wp-content/uploads/2018/08/GBU_Street-Tree-Cost-Benefit-Analysis-2018.pdf
- Urban Tree Planting Constraints (GreenBlue Urban): https://greenblue.com/na/urban-tree-planting-constraints/
- A review of tree root conflicts with sidewalks, curbs, roads (Urban Ecosystems): https://link.springer.com/article/10.1023/A:1024046004731
- USDA Urban Watershed Forestry — planting guide (solar access / siting): https://www.in.gov/dnr/forestry/files/fo-UrbanWatershedForestryPart_3.pdf

*Items I could not verify to the primary paper's own text are marked "needs verification" inline (Arbrat Viari species list; Barcelona-specific per-tree procurement cost; exact numeric anchor values inside Garcia-Nevado vs Vanos). No DOIs were fabricated.*
