# CoolSpend: A Budget-Constrained, Geometry-Aware Decision-Support System for Street-Tree Placement to Mitigate Urban Heat in Barcelona

**R. El Khoury**
*Infrared.city Buildathon 2026 — Independent submission*

---

## Abstract

Urban heat is a spatially concentrated, life-threatening hazard, yet the planting decisions that mitigate it — *which* species, placed *where*, for *how much* benefit per euro — are usually made without a quantitative, geometry-aware, budget-bounded model. We present **CoolSpend**, an end-to-end decision-support system that recommends where to plant street trees anywhere in Barcelona, evaluates the resulting outdoor thermal comfort against simulated Universal Thermal Climate Index (UTCI) fields, and allocates a fixed capital budget across the city's most heat-vulnerable sites. The system fuses four classes of real data — satellite heat and imperviousness (Landsat thermal land-surface temperature, Sentinel-1 sealed-surface, Sentinel-2 vegetation) aggregated into a 494-cell vulnerability grid; OpenStreetMap building, street and furniture geometry; the Barcelona municipal street-tree inventory; and the municipal population register — with the Infrared.city pedestrian-comfort engine. The deployed placement engine, used for both the single-site and the city-wide path, poses placement as **budgeted weighted maximum coverage** over a building-, street- and furniture-aware lattice of validated planting slots whose demand field is built from a **measured baseline UTCI grid**, solved with a cost-benefit greedy algorithm carrying the classical (1 − 1/e) submodular guarantee; a bi-objective (thermal relief vs. ecological coherence) NSGA-II formulation was implemented and benchmarked as a design alternative but is *not* in the shipped pipeline. Species selection enforces an ecological-health gate that excludes three exotic-invasive taxa and the over-represented London plane (*Platanus* × *acerifolia*), leaving an eight-species plantable palette. A multi-site allocator spreads a €1,000,000 budget across geographically separated sites under a per-site cap. We quantify outcomes the way practitioners do: cooled ground area, peak UTCI reduction, cost per square metre cooled, canopy cover against the 30% target, and a *population-served* metric using the World Health Organization-endorsed 300 m green-access catchment. On a live Infrared.city run at Plaça dels Àngels (615 real buildings fetched), 28 placed trees cool 4,268 m² of ground by at least 0.5 °C at €30 per m² cooled, lowering the sun-exposed peak felt temperature from 31.0 to 29.8 °C, with zero invasive species. A €1,000,000 portfolio — with per-site cooling measured on live Infrared UTCI and cached for replay — evaluates the 14 highest-priority cells and funds 90 trees across 6 geographically separated sites for €900,000 (the remaining €100,000 uncommitted after the feasibility, population-weighting and per-*barri* de-duplication filters), cooling a measured 20,609 m², serving 26,745 residents and adding 4,849 m² of canopy at an average €44 per m² cooled, with zero invasive or phase-down species. We report the system honestly: a three-tier backend (mock, cached, live) makes the distinction between *measured* and *synthetic* cooling explicit at every stage, and we enumerate the provenance gaps a production deployment would need to close. The contribution is less a new algorithm than a faithful, auditable assembly — real geometry, real ecology, real population, a bounded optimiser with a provable guarantee, and a discipline of never reporting a number we did not compute.

**Keywords:** urban heat island; Universal Thermal Climate Index; street-tree placement; submodular optimisation; urban greening; decision-support system; Barcelona; nature-based solutions

---

## 1. Introduction

Cities are warmer than the rural land that surrounds them. The urban heat island (UHI) — the systematic temperature excess of the built environment — arises from the radiative and thermal properties of urban surfaces: dark, sealed materials with high heat capacity absorb shortwave radiation by day and re-radiate it by night, while reduced vegetation suppresses the evaporative cooling that would otherwise dissipate that energy (Oke, 1982). The consequence is not an abstraction. Heat is among the deadliest climate hazards, and its burden falls unevenly across a city's blocks: the hottest places are typically the most sealed, the least vegetated, and frequently among the most densely inhabited.

Urban trees are the canonical intervention. They cool through two coupled mechanisms: shade, which intercepts shortwave radiation before it reaches and heats a surface, and transpiration, which converts absorbed energy into latent heat. A systematic review of the empirical literature found that, on average, an urban park is roughly 1 °C cooler than its surroundings during the day, with tree-dominated greening producing the most reliable effect (Bowler et al., 2010). Species and site mediate the magnitude: contrasting street-tree species under comparable conditions differ measurably in their air-temperature, surface-temperature and physiologically-equivalent-temperature reductions (Rahman et al., 2020), and trees deliver co-benefits beyond cooling, including measurable air-pollution removal (Nowak et al., 2006).

Knowing that trees cool, however, does not tell a city *where to plant them, which species to choose, or how to spend a finite budget*. These are the questions a planner actually faces, and they are rarely answered with a model that is simultaneously (a) grounded in real site geometry, so that a recommended tree does not land on a roof or against a foundation; (b) grounded in real species ecology, so that the palette is plantable and not invasive; (c) evaluated against a defensible thermal-comfort metric rather than a hand-waved temperature drop; and (d) bounded by a real budget, so that the recommendation is an *allocation*, not a wish list.

CoolSpend answers all four at once for the city of Barcelona, a Mediterranean (Köppen *Csa*) city with hot, dry summers, an extensive sealed core, and an active municipal agenda of de-paving and urban greening exemplified by its "superblock" (*superilla*) programme (Mueller et al., 2020). The system lets a user draw a polygon anywhere in the city or accept an automatically ranked list of the most heat-vulnerable cells, and returns a concrete, costed, ecologically screened planting plan whose cooling is evaluated on the Infrared.city UTCI engine. It then scales that single-site capability into a city-wide capital-allocation tool that spreads a €1,000,000 budget across the highest-priority sites.

Our contribution is threefold. First, a **faithful data assembly**: four independent real-world data sources (satellite, OpenStreetMap, municipal tree inventory, municipal census) are fused into a placement model in which every spatial exclusion is enforced from open data, and the absence of survey-grade data (underground utilities, sidewalk widths) is flagged rather than silently assumed away. Second, a **bounded optimisation layer** that treats placement as budgeted weighted maximum coverage with a provable approximation guarantee, complemented by a multi-objective evolutionary alternative and a multi-site capital allocator. Third, and most important for a tool intended to inform public spending, an **honesty architecture**: a three-tier simulation backend that never lets a synthetic preview masquerade as a measured result, and a set of practitioner-facing metrics (cost per m² cooled, canopy cover against target, population served) that a non-specialist reviewer can interrogate.

The remainder of this paper is organised as follows. Section 2 situates the work in urban-climate and optimisation literature. Section 3 describes the four data sources and their provenance, including the gaps. Section 4 details the methods — candidate-slot generation, the deployed greedy placement algorithm and the evolutionary alternative, species ecology screening, growth modelling, the cost model, the multi-site allocator, and the supporting metrics — with the governing equations and the actual constants drawn from the source code. Section 5 describes the system architecture and the three-tier backend, mapping each responsibility to its module. Section 6 reports results for a live single-site run and the €1,000,000 portfolio. Section 7 documents a structured validation against sixteen urban-design knowledge bases. Section 8 discusses implications, Section 9 enumerates limitations frankly, and Section 10 concludes.

---

## 2. Background and Related Work

### 2.1 Thermal comfort and the choice of metric

A cooling intervention should be judged by what people *feel*, not only by air temperature. The Universal Thermal Climate Index (UTCI) is an equivalent-temperature index derived from a multi-node model of human thermoregulation coupled to an adaptive clothing model; it integrates air temperature, mean radiant temperature, wind and humidity into a single value expressed in degrees Celsius, defined as the air temperature of a reference environment that would produce the same physiological strain (Bröde et al., 2012). UTCI is well suited to evaluating tree shade because shade acts primarily on the *mean radiant temperature* term — the dominant driver of daytime outdoor discomfort — which a simple air-temperature metric would miss. CoolSpend adopts UTCI as its headline thermal metric and uses the **26 °C threshold** (the boundary between "no thermal stress" and "moderate heat stress") both as the comfort cut-off for demand weighting and as the heat-stress-relief threshold for reporting.

### 2.2 Greening targets and access norms

Beyond per-site cooling, contemporary urban-greening practice is increasingly organised around access and coverage norms. The **3–30–300 rule** (Konijnendijk, 2023) synthesises the evidence into three thresholds: at least three mature trees visible from every home, at least 30% canopy cover in every neighbourhood, and a high-quality green space within 300 m of every residence. CoolSpend operationalises two of these directly: the 30% canopy-cover target drives its design-metric scoring, and the 300 m catchment defines the radius of its population-served calculation, which we treat as a proxy for the "300" access criterion.

### 2.3 Placement as submodular coverage

The core placement problem — choose a set of tree locations that maximises demand-weighted shade coverage under a budget — is an instance of *weighted maximum coverage*, whose objective is monotone and submodular: adding a tree never decreases coverage, and its marginal benefit diminishes as coverage grows (a cell already shaded cannot be shaded twice). For such objectives, the greedy algorithm that repeatedly adds the highest-marginal-gain element achieves at least (1 − 1/e) ≈ 63% of the optimum (Nemhauser et al., 1978). Under a budget (knapsack) constraint, a cost-benefit greedy that ranks candidates by marginal-gain-per-cost retains a constant-factor guarantee, and the lazy-evaluation refinement (CELF) accelerates it by orders of magnitude by exploiting submodularity to skip stale re-evaluations (Leskovec et al., 2007). CoolSpend's deployed placement engine is a budgeted cost-benefit greedy of exactly this lineage.

### 2.4 The multi-objective alternative

Cooling is not the only design objective: a monoculture optimised purely for shade is ecologically fragile. We therefore *explored* a bi-objective formulation — thermal relief versus ecological coherence — solved with the Non-dominated Sorting Genetic Algorithm II (NSGA-II), the standard elitist multi-objective evolutionary algorithm, which returns a Pareto front of non-dominated trade-offs in a single run via fast non-dominated sorting and crowding-distance diversity preservation (Deb et al., 2002); single-plan selection from the front uses the Technique for Order of Preference by Similarity to Ideal Solution (TOPSIS) (Hwang & Yoon, 1981). This evolutionary path is documented here as a design alternative and a benchmark. The *deployed* engine in both the single-site and city-wide pipelines is the greedy coverage maximiser of Section 2.3, which folds ecological diversity in as an anti-monoculture constraint (Section 4.3) rather than as a second optimisation objective. The reasons for this choice are practical and are discussed in Sections 4.8 and 8: the greedy operates directly on the *measured* baseline UTCI field, is deterministic and interpretable, and reserves the expensive live simulations for validating a single layout rather than scoring thousands of candidate layouts on an analytical surrogate.

---

## 3. Data

CoolSpend fuses four independent real-world data sources. We describe each, its role, and — in keeping with the honesty architecture — its provenance limits.

### 3.1 Satellite heat-vulnerability grid

Site *prioritisation* (where in the city to act) is driven by a pre-computed vulnerability grid, `scored_grid`, covering Barcelona in **494 cells** of approximately 400 m × 400 m in the EPSG:25831 (UTM zone 31N) projection. Each cell carries:

- `mean_lst_celsius` and `lst_anomaly` — mean land-surface temperature and its anomaly, derived from **Landsat** thermal infrared bands;
- `mean_sealed` — the impervious/sealed-surface fraction (0–1), derived from **Sentinel-1** synthetic-aperture radar;
- `mean_ndvi` — the Normalised Difference Vegetation Index, derived from **Sentinel-2** optical bands, used as an existing-vegetation signal;
- `composite_score_B` — the primary ranking signal, a composite emphasising the product of heat and sealing (hot × sealed), so that the highest-priority cells are those that are simultaneously hottest and most paved;
- administrative attributes (`district`, `barri`) and existing street-tree counts from the municipal inventory.

This grid is a satellite-derived *heat-vulnerability* surface, **not** a UTCI field. It answers *where to look*, not *how much cooling a plan delivers*, and reading it requires no live API calls.

**Provenance.** The composite is exactly reproducible in-repo: a least-squares fit over all 494 cells recovers a single constant weight vector,

> `composite_score_B = 0.45·sealed + 0.20·LST-anomaly + 0.15·(1 − NDVI) + 0.05·mismatch + 0.15·prpi`,

reconstructing the published composite to floating-point epsilon (R² = 1.0, maximum absolute residual ≈ 2 × 10⁻¹⁶; see `coolspend/provenance.py`, the datasheet in `docs/scored_grid_datasheet.md`, and the regression test). The residual gap is narrower than first stated: the derivation of three sub-scores from raw imagery — the Sentinel-1 SAR-to-sealed classifier, the Landsat LST-anomaly baseline, and the `mismatch`/`prpi` indices — lives in an upstream ingestion pipeline and is not documented here (Section 9, item 1).

### 3.2 OpenStreetMap geometry

Physical placement validity is enforced from **OpenStreetMap** (OSM) data retrieved via the Overpass API and cached locally:

- **Building footprints**, which exclude planting on roofs and enforce clearance from façades. Critically, OSM buildings are *backend-independent*: they are available even when no Infrared.city building layer is (the Infrared building layer is a live-only product), which is what keeps a tree off a roof on the mock and cached backends.
- **Road carriageways** and **junction sight-triangles**, which exclude the trafficked roadway (plazas and footways remain plantable).
- **Street furniture** — hydrants, crossings, stops, lamp posts, signals, manholes, power lines — which carry local exclusions.

When Overpass is unreachable, these exclusion sets degrade gracefully to empty rather than failing, with the degradation logged.

### 3.3 Municipal street-tree inventory

Species parameters derive from Barcelona's *arbrat viari* (street-tree) inventory, the basis for a 12-species candidate table with per-species mature crown diameter and height assigned from the inventory's documented size bands (height: low < 6 m → 4 m, medium 6–15 m → 10 m, tall > 15 m → 18 m; crown: narrow → 3 m, medium → 5 m, wide → 7 m, very wide → 10 m). The inventory also supplies the *existing* trees within a site, whose mature canopy footprints are treated as already-shaded ground and excluded from planting demand.

### 3.4 Municipal population register

The population-served metric uses the Barcelona municipal register (*Padró*) published as open data (dataset `pad_mdbas`), which records **1,702,814** registered residents (2024 vintage) across the city's **73 *barris*** (neighbourhoods). Neighbourhood boundary geometry is taken from an open GeoJSON mirror in WGS84 and joined 1:1 to the register by neighbourhood code. All areal computation is performed in EPSG:25831 so that catchment areas and densities are in true metres.

---

## 4. Methods

This section gives the governing equations and the actual constants from the source. Where a constant is a literature- or procurement-anchored value rather than a fitted one, we say so; where a number is `REQUIRES_VERIFICATION`, we mark it.

### 4.1 Candidate-slot generation

CoolSpend never optimises over continuous space; it optimises over a finite set of *validated* candidate slots (`coolspend/candidate_slots.py`). Slots are generated on a deterministic 4 m lattice (`GRID_STEP_M = 4.0`) walked in row-major order, then each candidate is validated against a conjunction of constraints:

1. **Inside the site boundary** polygon.
2. **Not inside any building footprint** (no roofs).
3. **Building clearance**, which depends on the *planting mode* (below).
4. **Outside the street buffer** (trunk kept off the carriageway).
5. **At least `MIN_SPACING_M` from existing trees and from already-accepted slots.**

The minimum spacing is **8 m** (`MIN_SPACING_M = 8.0`). This value is not arbitrary: it is the interval at which three independent design standards converge — NACTO's 6–9 m on-centre street-tree spacing, the climate-responsive guideline that "trees at 8–10 m create continuous canopy at maturity" for Mediterranean conditions, and de-paving practice's default 6–10 m. An earlier 5 m value packed canopies into overlapping clumps; 8 m produces a legible *allée* and prevents the visual "trees everywhere" failure mode.

**Two planting modes** encode the central de-paving trade-off:

- **Planter mode** (`PLANTER`) — a tree in a large planter resting on the pavement. Roots are contained, so there is no foundation risk and the tree may sit near a building, requiring only a 0.6 m physical wall clearance (`PLANTER_WALL_CLEARANCE_M = 0.6`). No de-paving is needed, but the contained root volume caps the mature crown and raises watering cost.
- **In-ground mode** (`IN_GROUND`) — a de-paved pit with roots in soil. This permits the full mature crown but introduces foundation risk, so a 6 m setback from any building is enforced (`FOUNDATION_SETBACK_M = 6.0`), and the de-paving incurs a pit cost over the structural tree-pit footprint.

Two honesty flags attach here. The 6 m foundation setback is a conservative single value for large street species and is marked as requiring verification against species-specific root-spread and municipal setback code. And because underground utilities are not present in open data, every in-ground slot in the output carries a `requires_utility_survey` flag (`placement_inputs.py`) — the system asserts plantability from the best available data but explicitly declines to assert clearance of buried mains it cannot see.

### 4.2 Demand field

Placement maximises coverage of a *demand field* — a set of weighted cells representing ground that is hot, paved, and unshaded (`placement_inputs.assemble_inputs` → `build_demand_cells`). On the live backend, the field is built from a single **baseline UTCI grid** returned by the Infrared.city engine: a cell becomes a demand cell if and only if

> UTCI > 26 °C ∧ impervious ∧ not-already-shaded ∧ value ≠ NaN,

and its weight is

> `weight = UTCI − 26`,

so hotter ground attracts more shade. Imperviousness is tested against the OSM/ground-material impervious union; "already shaded" is tested against the union of existing-canopy discs (each existing tree's mature crown radius from the inventory).

Two robustness mechanisms matter. First, the Infrared.city SDK returns a 512 × 512 grid that spans a square *larger* than the drawn polygon, with the valid (non-NaN) cells in a corner; the field builder crops the grid to its non-NaN bounding box before mapping rows and columns onto the polygon's extent (`_crop_grid_to_valid`), fixing a registration error that otherwise scattered demand to the wrong coordinates and produced zero placements. Second, if the impervious filter eliminates *all* demand (sparse or misclassified land cover — e.g. a paved plaza tagged as vegetation), the builder falls back to treating all hot, unshaded ground as demand — an honest degradation that shades the hottest ground it can confirm rather than refusing to act, logged as a warning.

On the mock and cached backends, where no measured UTCI grid exists, the builder substitutes a uniform proxy demand (a 40 × 40 lattice over the bounding box, each cell weighted `COMFORT_UTCI_C + 1.0`). This is the crux of the honesty design: **placement remains real and valid even when the cooling number is a labelled synthetic preview**, because placement depends on geometry and the proxy field, not on measured cooling.

### 4.3 Greedy weighted maximum-coverage placement (deployed engine)

The deployed placement engine (`coolspend/smart_placement.py:place_trees_greedy`) solves budgeted weighted maximum coverage. For a set *S* of placed trees, the objective is

> value(*S*) = Σ over demand cells *c* of `weight(c) · min(1, Σ over trees t∈S of shade_gain(t, c))`,

where each demand cell is covered not by mere crown overlap but by **shade-gain**: the fraction of sampled July sun positions whose crown shadow actually falls on the cell (`coolspend/shade_proxy.py`). A tree therefore earns a cell only if its shadow reaches it — placing trees *south* of midday hotspots, not merely on top of them — and a cell already shaded contributes only the *new* blockage (per-cell captured gain is capped at 1.0, so double-shading yields nothing; this cap is what makes the objective submodular).

The algorithm is a cost-benefit greedy. Coverage is precomputed once, because geometry is static: for every (candidate slot *ci*, species *si*) pair it stores the map {demand-cell index → shade_gain ∈ (0, 1]}. Then at each step it computes, for every still-affordable, still-spaced (slot, species) pair, the **marginal gain**

> marginal = Σ over cells *i* in coverage(ci, si) of `weight(i) · max(0, shade_gain(i) − captured(i))`,

divides by the pair's cost to obtain **gain-per-euro** `gpc = marginal / cost`, and selects the maximum. Ties are broken first by the species' cooling score and then by absolute marginal gain, for determinism. The selected tree's cells update `captured`, its slot is retired, its position joins the spacing set, and the loop repeats. The cost of a pair is `tree_cost(species) + depave_cost(slot)` (the de-pave term is zero for planter slots).

```
precompute coverage[(ci, si)] = { cell_i : shade_gain }      # static geometry
captured = {}, placed = [], spent = 0
loop:
    best = argmax over (ci not used, si) with:
        slot not within 8 m of any placed tree
        species crown fits slot.max_crown_m
        spent + cost(ci, si) <= budget
        marginal(ci, si) > 0
      ranked by ( marginal/cost , cooling_score , marginal )    # cost-benefit greedy
      subject to anti-monoculture cap after the grace period
    if best is None: stop_reason = "no positive-gain affordable slot"; break
    place best; update captured, spent, placed, species_count
```

Two refinements temper a pure shade-maximiser. An **anti-monoculture constraint** caps any single species at 40% of the planting (`max_species_share = 0.40`) once past a four-tree grace period (`diversity_grace = 4`), so a strong species can establish before the cap binds; the engine tracks two running bests, one honouring the cap and one ignoring it, and prefers the cap-respecting pick but falls back to the unconstrained best so the cap can never *stall* a still-improving run. And the per-tree crown used for coverage is capped to the site (Section 4.4). Selection stops on a real condition — *no affordable slot yields positive marginal gain*, or *the budget is exhausted* — recorded as `stop_reason`; the loop is never bounded by a fixed iteration count. A `use_shade_gain = False` flag falls back to the legacy binary crown-coverage proxy (gain = 1.0 inside the crown radius).

This inherits the (1 − 1/e) submodular guarantee (Nemhauser et al., 1978) in its cost-benefit form (Leskovec et al., 2007): the shade-gain sets union exactly like coverage sets, so submodularity is preserved. A live A/B study confirmed the shade-gain ordering does not regress the headline — it cooled a larger measured footprint at a lower cost-per-m² than the binary-coverage layout, the larger footprint including more marginal-benefit edge cells at a slightly lower mean ΔUTCI.

We are explicit about what the greedy objective is and is not. The demand weights are computed on the *baseline* UTCI field — the field before any tree is planted. True cooling is non-linear: a planted tree changes the field, so the greedy "gain" is a coverage *proxy* for marginal cooling, not measured cooling. The chosen layout's true cooling is established afterward by a live UTCI simulation (Section 4.8), and every reported cooling magnitude comes from that simulation, never from the proxy.

### 4.4 Crown-to-site matching

A mature canopy must not grow into a wall, but it *should* overhang the street it shades. The crown cap therefore depends on distance to the nearest **building façade only**:

> max_crown(slot) = max(5 m, 2 × distance-to-nearest-building).

Streets and sidewalks deliberately do not cap the crown — overhanging the carriageway is precisely the shade being purchased, and the trunk is already kept out of the street buffer at the slot-validation stage. The 5 m floor ensures the smallest species can always fit; an earlier version that also capped on street distance shrank crowns below the smallest species on tight plazas and produced zero placements. A (slot, species) pair is simply skipped when the species' mature crown exceeds the slot's `max_crown_m`.

### 4.5 Species ecology and the plantability gate

Species selection is governed by a single source of truth (`coolspend/ecology.py`): a per-species ecological-health composite combined with a hard plantability gate. The composite is reported *alongside* the cooling and cost metrics, never blended into them, so an ecological trade-off is visible rather than hidden inside a single number.

The **ecosystem-health score** ∈ [0, 1] is a weighted sum of benefits minus penalties, with the benefit weights summing to 1.0 and the penalties subtracting:

- *Benefits:* drought/heat tolerance (`_W_DROUGHT = 0.30`), biodiversity value (`_W_BIODIV = 0.20`), pollinator value (`_W_POLLINATOR = 0.20`), longevity (`_W_LONGEVITY = 0.15`, from the typical urban-midpoint maturity years normalised over a 30–150-year span), and native status (`_W_NATIVE = 0.15`; native → 1.0, naturalised → 0.6, exotic → 0.4, exotic-invasive → 0.0).
- *Penalties:* allergenicity (`_P_ALLERGEN = 0.15`, an OPALS-scaled pollen burden where higher is worse), pest/disease risk (0.10), water demand (0.10), maintenance burden (0.10), and a hard **invasive veto** (0.30 subtracted when the species is exotic-invasive).

Schematically, for a species *s* with native-status score *n(s)* and normalised longevity *ℓ(s)*:

> health(*s*) = 0.30·drought + 0.20·biodiv + 0.20·pollinator + 0.15·ℓ + 0.15·n − 0.15·allergen − 0.10·pest − 0.10·water − 0.10·maint − 0.30·[*s* is invasive].

The weights are `DECLARED` design constants, not fitted values, and are sensitivity-testable via `coolspend/sensitivity.py`. They encode a clear value judgement: drought/heat fitness under a warming Mediterranean climate is the single most important trait, biodiversity and pollinator value matter equally and together outweigh any single benefit, and an invasive species is vetoed regardless of how well it cools or forages (the canonical case is *Robinia pseudoacacia*, a top honey tree whose invasive penalty deliberately outweighs its nectar value).

The **plantability gate** (`is_plantable`) removes four taxa from the 12-species table, leaving an **8-species** palette:

- three **exotic-invasive** species — *Robinia pseudoacacia*, *Ligustrum lucidum*, *Ulmus pumila* — vetoed outright;
- the **phase-down** species *Platanus* × *acerifolia* (London plane), which constitutes roughly a quarter of Barcelona's street trees, carries high allergy and disease burden, and is being deliberately reduced; the municipality's over-reliance on it is exactly the monoculture risk the system is designed to avoid amplifying.

The same gate is the single species source for both the greedy engine and the NSGA-II alternative, so neither path can ever recommend an excluded species. The resulting palette spans Mediterranean natives (*Celtis australis*, *Cercis siliquastrum*), drought specialists (*Brachychiton populneus*, with the palette's best drought tolerance and lowest input), and heavy pollinator foragers (*Styphnolobium japonicum*, *Tipuana tipu*, *Jacaranda mimosifolia*).

### 4.6 Growth and time-to-maturity

A newly planted tree does not deliver its mature cooling on day one. CoolSpend models the *economic* establishment with a growth-discount ramp used for net-present-value accounting (Section 4.7): cooling benefit rises linearly from an initial 20% at planting (`initial_fraction = 0.20`) to 100% over a 25-year establishment period (`ramp_years = 25`), after which it is held constant, with future benefits discounted at 3.5% per year over a 40-year horizon.

The *visual and canopy-area* growth, however, is species-specific and uses a proper growth curve rather than the flat ramp (`coolspend/growth.py`, mirrored client-side in `web/src/lib/growth.ts`). Each species' crown follows a **Chapman–Richards** growth function — the standard forestry/urban-tree sigmoid — of the form

> crown(age) = max(PLANTING_CROWN_M, A · (1 − e^(−k·age))^P),

with `PLANTING_CROWN_M = 1.5 m` (a realistic large-caliper nursery crown at age 0), shape exponent `P = 3.0` (giving the slow–fast–slow sigmoid), and `A` the species' mature crown diameter from the inventory. The single rate parameter *k* is solved analytically so the crown reaches 95% of its mature diameter (`_MATURITY_FRACTION = 0.95`) at the species' maturity year *T*, which is assigned from its growth-rate band (fast = 20, medium = 30, slow = 40 years):

> k = −ln(1 − 0.95^(1/3)) / T = −ln(0.0170) / T ≈ 4.074 / T.

Worked example: a fast *Tipuana tipu* (*T* = 20) has k ≈ 0.204 yr⁻¹; a slow *Cercis siliquastrum* (*T* = 40) has k ≈ 0.102 yr⁻¹ — so the fast species fills its crown about twice as quickly, visibly and in the per-tree inspector. Shade scales with crown *area*, so the cooling fraction at a given age is the squared crown ratio,

> cooling_fraction(age) = (crown(age) / A)².

The model invents no per-species fitted coefficients — only the sigmoid form and the two anchors (mature crown, maturity year) — and is structured to accept measured i-Tree/Pretzsch coefficients later without changing call sites. The age slider grows each tree's canopy disc on its own curve.

### 4.7 Cost model

Capital and operating costs are itemised, not assumed (`coolspend/cost_model.py`, `coolspend/cost_config.json`). Per-tree **capital expenditure** totals **€2,200**, as the sum of five lines:

| Line | € / tree | Confidence |
|---|---|---|
| Tree stock (large-caliper, 20–25 cm circ.) | 600 | DECLARED |
| Pit excavation (new *alcorque*, 2×2×1.2 m) | 500 | DECLARED |
| Structural soil / sand mix (installed) | 600 | DECLARED |
| Guarding, staking, aeration tube | 200 | VERIFIED |
| Planting labour | 300 | VERIFIED |
| **CapEx total** | **2,200** | |

**Operating expenditure** is **€60 per tree per year**, derived directly from Barcelona's municipal parks-institute 2023 activity accounts: €12,658,229 maintenance ÷ 206,556 street trees = €61.28/tree/year, rounded (VERIFIED, source BCN IMPJ Activity 0214 — *Arbrat Viari*, covering pruning, watering, biennial risk inspection, phytosanitary treatment and replacement). The guarding and labour lines are cross-checked against the Diputació de Barcelona replacement-grant bundle and BCN tender 23/0157; the stock, excavation and soil lines are `DECLARED` pending direct tender unit-price extraction.

Costs are evaluated over a **40-year** functional horizon (`OPEX_HORIZON_YEARS = 40`) at a **3.5%** social discount rate (the EU/UK Green Book convention; locale-editable). The present value of a tree's lifecycle is CapEx (year 0, undiscounted) plus the discounted OpEx stream. The 40-year discount annuity factor is

> a = (1 − (1 + r)^(−H)) / r = (1 − 1.035^(−40)) / 0.035 ≈ 21.36,

so PV(OpEx) ≈ 60 × 21.36 ≈ **€1,281** per tree, and the per-tree lifecycle present value ≈ 2,200 + 1,281 ≈ **€3,481**. The headline €/m²-cooled KPI reported to the user, however, is computed on the *placement* cost actually committed at planting — `tree_cost + depave_cost` summed over placed trees — divided by the measured cooled footprint; the discounted-lifetime machinery (`discounted_lifetime_degc`, `discounted_total_cost`) is retained for net-present-value comparisons and editable cost tables.

A single calibration constant — the UTCI-hours-above-32 °C removed per °C of cooling, used in the surrogate's hours-above-threshold path — is computed from the in-repo Barcelona TMYx EPW via the project's ladybug UTCI machinery (`hours_per_degc()`), yielding ≈47 h/°C (band-mean over 0.5–2 °C interventions), markedly lower than the prior literal 200 h/°C, which had assumed a 600 h/yr heat-stress baseline whereas the EPW yields 98 h/yr above 32 °C. The 200 figure is retained only as an offline fallback (`HOURS_PER_DEGC_REF`); the live calibration study (Section 4.8) is the definitive arbiter.

### 4.8 The multi-objective alternative and live validation

The deployed pipeline does not run NSGA-II; the following bi-objective formulation (`coolspend/optimizer.py`) was implemented and benchmarked as a design alternative, and is described here for completeness.

The NSGA-II decision vector has 3·*n* genes — *n* (*x*, *y*) positions plus *n* species genes — where the tree count *n* scales with site area at one tree per 225 m² (15 m × 15 m nominal), clamped to [12, 100] for tractability. The two objectives (both minimised by pymoo convention) are the negative of a site-averaged thermal-relief **surrogate** weighted by mean species cooling factor, and the negative of an ecological-coherence (diversity) score; the budget enters as an inequality constraint. NSGA-II runs with a population of 60 over 60 generations (3,600 surrogate evaluations), simulated-binary crossover (probability 0.9, η = 15), polynomial mutation (η = 20), and a fixed seed of 42 for reproducibility. From the Pareto front, three configurations are selected — best thermal, best ecological, and the balanced point nearest the normalised utopia corner — then ranked by TOPSIS with weights (thermal 0.6, ecological 0.4).

The thermal-relief surrogate (`coolspend/spatial_engine.py:delta_tmrt_surrogate`) is an analytical proxy, explicitly *not* a measured value:

> ΔTmrt = min(MAX_TMRT_REDUCTION_C · effective_shade · shade_efficiency(tilt, height), MAX_TMRT_REDUCTION_C),

with `MAX_TMRT_REDUCTION_C = 12 °C` a non-binding linear cap and `MAX_SITE_COVERAGE = 0.90` a coverage ceiling. The surrogate's character was measured directly in a live calibration study (`coolspend/calibration.py`, 10–11 live simulations; summary in `coolspend/data/calibration_summary.json`): against real UTCI deltas it has an empirical 95% band of **±0.78 °C** (1.96 × RMSE 0.398 °C), roughly five times tighter than the previously assumed ±4 °C, but it is a *weak magnitude predictor* (R² = −0.946, biased low) and only a *moderate ranker* (Spearman ρ = 0.687, Kendall τ = 0.584, with 2 of 3 top-three configurations retained under real UTCI). This is precisely why the surrogate is used only for *ordering* candidates and never for a reported magnitude — and, more decisively, why the deployed engine bypasses the surrogate entirely in favour of the *measured* baseline UTCI demand field. The 12 °C cap is documented as a non-binding guard: the calibration shows the surrogate never predicts above ~0.5 °C site-averaged ΔTmrt in practice, so the cap is never reached.

**Both paths converge on the same validation step.** The chosen layout is submitted to the Infrared.city engine for a true UTCI evaluation: one baseline simulation (no trees) plus the intervention simulation (with the placed trees), hard-capped by a simulation budget of three live calls per run (`SimBudget`, `coolspend/sdk_client.py`); a fourth call raises a `RuntimeError`. The single-site live pipeline is therefore: build the measured demand field from the baseline grid → greedily place trees → run the intervention simulation → report the *measured* grid difference. The reported ΔUTCI is `baseline.utci_c − intervention.utci_c`, and the headline cooled footprint and €/m² are derived from the two measured 512 × 512 grids.

### 4.9 Cooled-footprint profile

Given baseline and intervention UTCI grids (512 × 512 at 1 m resolution, evaluated for the July 09:00–17:00 peak-heat window at 1.1 m pedestrian height), the system computes a multi-band cooled-footprint profile (`sdk_client.cooled_footprint_m2`, `cooled_footprint_profile`):

- **cooled area by band** — m² cooled by ≥ 0.5 °C (the headline band), ≥ 1 °C and ≥ 2 °C, counting cells whose per-cell drop crosses each threshold at a 1 m² pitch;
- **mean, standard deviation, 10th/90th percentile and peak** of the per-cell UTCI drop over cooled cells;
- **heat-stress area relieved** — m² that crosses from ≥ 26 °C at baseline to < 26 °C after;
- **largest contiguous cooled patch** and **patch count**, via connected-component labelling (4-connectivity), distinguishing one continuous shaded corridor from scattered dapples;
- the **peak** felt temperature is reported as the **90th-percentile** cell rather than the maximum, so a single outlier cell cannot drive the headline.

### 4.10 Multi-site €1,000,000 allocation

The city-scale tool (`coolspend/citywide.py:allocate_citywide`) spreads a fixed budget across the highest-priority cells. It ranks all 494 cells by `composite_score_B`, takes the top-ranked candidates (14 were evaluated on the live backend in the committed run), and runs the full single-site `smart_evaluate` chain on a **200 m × 200 m** sample polygon centred on each candidate cell, at a per-site budget cap of **€150,000** (≈ enough for an uncrowded ~15-tree intervention, not a saturated plaza). It then funds the best candidates first — by *measured* cost-per-m²-cooled when live, else by descending `composite_score_B` — until the total budget is committed, enforcing geographic spread (per-*barri* de-duplication plus a minimum separation between funded sites) so the portfolio is distributed rather than clustered in one hot district. Each funded site carries its placed trees, its population served, and its design metrics; the portfolio aggregates total trees, cooled area, canopy, person-degrees, and a de-duplicated total population served.

### 4.11 Population served

Population served operationalises the 300 m access criterion of the 3–30–300 rule (`coolspend/population.py`). For a single site, residents within a 300 m catchment are estimated by intersecting the catchment disc with neighbourhood polygons in EPSG:25831 and area-weighting each neighbourhood's resident density. For a portfolio, the catchment discs are **unioned** and the population is computed against the union geometry, so residents in the overlap of two nearby sites are counted **once** — a de-duplicated, area-weighted union rather than a naïve sum.

### 4.12 Design metrics

Three geometric metrics translate a plan into planner-legible terms (`coolspend/design_metrics.py`). **Canopy area** is the sum of mature crown discs (Σ π r²). **Canopy cover** is that area as a percentage of the site, scored against the 30% target with the gap reported, and computed against two denominators — the sampled cell area (comparable city-wide) and the *plantable strip* (the site minus buildings and street/furniture buffers), with the headline using the plantable strip as the truer local intensity. An **estimated air-temperature drop** applies the climate-literature midpoint of **0.075 °C per +1 percentage-point** of canopy cover (the centre of the 0.5–1.0 °C-per-10% range). **Person-degrees** — residents served × mean UTCI reduction — is a single people-weighted heat-relief figure. These are explicitly geometric estimates; measured cooling remains the UTCI simulation.

---

## 5. System Architecture

CoolSpend is a Python computational core exposed through a FastAPI service to a deck.gl/Mapbox web client. The module map mirrors the methods: `candidate_slots.py` and `placement_inputs.py` assemble validated slots and the demand field; `smart_placement.py` runs the deployed greedy; `shade_proxy.py` computes shade-gain; `sdk_client.py` is the Infrared boundary; `ecology.py`, `bcn_species.py` and `growth.py` carry species data; `cost_model.py` carries the cost table; `citywide.py` and `population.py` carry the city-scale allocation; `app_pipeline.py` (`smart_evaluate`) and `api_server.py` orchestrate; `export_web.py` writes the web bundle.

### 5.1 Three-tier simulation backend

The defining architectural decision is a three-tier Infrared backend selected by environment variable, designed so a synthetic result can never be mistaken for a measured one:

- **mock** — a deterministic scalar UTCI model (open-plaza 41.0 °C interpolated toward under-canopy 30.5 °C by coverage fraction). It performs **no network call** and every result carries the disclaimer "NOT MEASURED DATA — synthetic field for UI integration only." It exists so the full pipeline (placement, costing, metrics, web export) runs offline with real geometry but a labelled synthetic cooling estimate.
- **cached** — replays a prior result from a disk cache keyed by a SHA-256 hash of the query geometry. On a cache miss it raises an error rather than silently falling through to mock, and replayed results retain their original provenance.
- **live** — calls the real Infrared.city UTCI engine, requires the API key, hits the network once per simulation, and writes the result to the cache for later offline replay.

The `SimBudget` guard hard-caps live calls at three per run, so a single evaluation can never trigger an unbounded burst of paid simulations. The API key is never read into a return value, logged, or serialised.

### 5.2 Pipeline and endpoints

The FastAPI layer exposes: a polygon-preview endpoint (building count and impervious analysis, no simulation); `/api/evaluate`, which runs the full single-site `smart_evaluate` pipeline on a drawn polygon and writes a self-contained web bundle (decision JSON, trees and boundary GeoJSON, raster bounds, baseline and intervention UTCI PNGs, optional 3D scene); `/api/citywide/scan`, a fast ranking of the 494 cells with no live calls; and `/api/citywide/allocate`, the multi-site allocator. The evaluate endpoint writes to an isolated bundle directory distinct from the curated showcase, so an exploratory user run cannot overwrite the demonstration artifact.

### 5.3 Web client

The client renders on a Mapbox satellite basemap with a deck.gl overlay. Proposed and existing trees are drawn as **canopy-footprint discs** (ScatterplotLayer) whose radius is the true crown radius in metres — the literal ground area shaded — which is both more honest than a generic sprite and more robust to render over a basemap than metre-scale billboards; a lighter concentric inner core gives each canopy a tree-like density read from top-down. Each disc grows on its species' Chapman–Richards curve as the age slider moves. The UTCI heatmap is draped as a bitmap cropped to its valid extent and colourised on a 20–40 °C red–blue scale with out-of-polygon cells fully transparent. A click inspector surfaces each tree's species identity, shade footprint, full ecological profile, species-specific time-to-maturity, and an explicit **data-provenance footer**. The measured-vs-estimate distinction is shown as a badge in both the single-site HUD and the city-wide panel, driven by the backend tag — never claiming "measured" without a live UTCI grid behind it. A separate city-wide mode renders the satellite vulnerability grid and the €1,000,000 plan as per-site markers with a portfolio panel. A 3D cinematic mode extrudes building footprints and renders trees as spheres for presentation; the 2D analysis mode is the measured-data view.

---

## 6. Results

### 6.1 Live single-site evaluation

We evaluated Plaça dels Àngels on the **live** Infrared.city backend, with **615 real buildings** fetched for building-aware shade and heat. The greedy engine (shade-gain weighting) placed **28 trees** drawn from the plantable palette. The measured cooled-footprint profile reported **4,268 m² cooled by at least 0.5 °C** at a cost efficiency of **€30 per m² cooled**, lowering the sun-exposed peak felt temperature from **31.0 to 29.8 °C**, with a cooling depth of 3,260 m² cooled ≥ 1 °C, 1,716 m² ≥ 2 °C, and 664 m² lifted out of heat stress (≥ 26 °C UTCI). This is the system's measured proof point: real geometry, real species screening, and a real before/after UTCI simulation on the same site. The showcase layout contains **zero** *Platanus* × *acerifolia* and zero invasive species, at 8 m spacing with per-tree maturity, confirming the plantability gate is effective end-to-end. Every output of the current pipeline — the showcase, the evaluate endpoint, and the €1,000,000 plan — is London-plane- and invasive-free.

### 6.2 City-wide €1,000,000 portfolio

From 494 scanned cells, the allocator evaluated the **14** highest-priority candidates on the live backend and committed **€900,000** across **6 geographically separated sites**, funding **90 trees** in total; the remaining **€100,000** was left uncommitted because the feasibility, population-weighting and per-*barri* de-duplication filters exhausted the qualifying candidate pool before a seventh distinct site cleared all gates (zero sites were rejected as infeasible). On the live backend the portfolio cools a **measured 20,609 m²** (`cooling_source = "measured_utci"`, `cooling_is_measured = true`), adds **4,849 m² of mature canopy**, and serves approximately **26,745 residents** within the unioned 300 m catchments (de-duplicated), at an average **€44 per m² cooled** (900,000 ÷ 20,609 = 43.7). The aggregate person-degrees figure is 7,667. The species mix is non-invasive throughout — zero London-plane, zero invasive or phase-down species.

We state the portfolio's epistemic status precisely. Its **placement is real** (building-, street- and furniture-aware geometry on every site), its **population served is real** (municipal register and neighbourhood geometry), its **site prioritisation is real** (the satellite vulnerability composite), and its **per-site cooling is measured** — each funded cell was evaluated on the live Infrared UTCI backend, the funding order is by measured cost-per-m²-cooled, and the results are cached by geometry hash for offline replay. Between the two backends the system exposes a three-tier `CoolingEstimator` (mock scalar → sim-free shade proxy → cached/live measured UTCI), so a sim-free build still produces a geometry-grounded *estimate* clearly badged as such, while the committed artifact is measured.

The honest comparison with an earlier "three-hour pass" portfolio (which reported 8 sites / 48k residents) is instructive: that figure double-counted overlapping catchments, used a proxy rather than measured cooling, and included an un-plantable cell in the Gòtic. The current 6-site / 26,745-resident / 20,609 m² figure is smaller precisely because it is measured, de-duplicated and feasibility-gated — the honesty discipline costs headline magnitude and buys defensibility.

### 6.3 Reproducibility and security posture

The NSGA-II alternative is deterministic under its fixed seed, pinning its Pareto front across runs; the deployed greedy is deterministic by construction (its tie-breaks are total). GeoJSON input is parsed only via a JSON parser, never evaluated as code; live simulations are capped at three per run by `SimBudget`; and the Infrared API key is never logged or returned. The Python test suite passes (392 passed / 1 skipped at the last run), the web client type-checks and builds clean, and the `placement_audit.py` independent OSM re-check confirms zero trees placed on buildings across the committed plan.

---

## 7. Validation Against Urban-Design Knowledge Bases

Because CoolSpend makes recommendations in a domain with deep professional standards, we validated its placement and metric choices against sixteen structured urban-design knowledge bases spanning street design, climate-responsive design, public-space design, zoning, density, transit-oriented design, mobility, mixed-use programming, site analysis, precedent study, cost estimation, sustainability scoring, design evaluation, urban regeneration, and a quantitative urban calculator. The exercise was deliberately adversarial: the question was not "does the tool look good" but "which standard changes a parameter, and which merely confirms one." The outcome separates cleanly into three groups.

**Standards that changed the product.** Street-design standards (NACTO) fixed the 8 m spacing, the tree-well footprint, and the trunk- and bike-lane-clearance rules that became the façade and street-buffer exclusions. Climate-responsive design supplied the Mediterranean 20–30% canopy target and the 0.075 °C-per-1%-canopy coefficient now in the design metrics. The quantitative urban-calculator framing produced the entire metrics layer — canopy area, cover, person-degrees, canopy-per-euro. Sustainability scoring produced the ecosystem-health composite and the plantability gate that excludes the invasive and phase-down species. Urban regeneration contributed the de-sealing/de-paving logic and the in-ground-versus-planter trade-off. Precedent study anchored the de-paving rules in Barcelona's *superilla* programme. Public-space design produced the "do not saturate the plaza" principle that became the per-site budget cap and the 8 m spacing — the direct answer to the over-crowding failure mode.

**Standards that validated without changing code.** Urban-design foundations (human scale, enclosure) confirmed plaza siting; site analysis confirmed the heat × sealed × vegetation signal as the correct prioritisation surface; design evaluation confirmed the multi-configuration KPI-ranking approach; cost estimation confirmed the per-tree cost model.

**Standards that did not fit.** Block-and-density, transit-oriented design, and mixed-use programming operate at the master-planning scale and have nothing to place in a street-tree problem; mobility-and-transport contributed only the bike-lane clearance already covered by street design.

The most useful result of the exercise was *convergence*: three independent standards (NACTO 6–9 m, climate-responsive 8–10 m, de-paving 6–10 m) arrive at the same 8 m spacing. That a parameter is over-determined by three bodies of practice is stronger evidence than any single citation. The exercise did **not** invent new placement logic — placement was already geometry-aware — but it confirmed the rules and contributed the quantitative metric layer that makes a plan legible to a non-specialist.

---

## 8. Discussion

CoolSpend's central design claim is that a decision-support tool for public spending earns trust through *fidelity and auditability*, not through algorithmic novelty. Each layer is independently inspectable. A reviewer can verify that no tree sits on a roof by checking the building exclusion; that no recommended species is invasive by reading the plantability gate; that the budget is committed by summing the per-site costs; that the cooling is measured by reading the backend tag on the result. The (1 − 1/e) guarantee matters less for the absolute optimality it promises than for the fact that the placement is a principled coverage maximisation rather than an opaque heuristic.

The choice to deploy the greedy rather than the NSGA-II alternative is the clearest expression of this philosophy, and it is worth stating plainly because the two are easy to conflate. NSGA-II is the more elaborate algorithm, but it optimises on an analytical *surrogate* whose calibrated character is a negative R² for magnitude — it cannot predict how much a layout cools, only roughly rank layouts — and it must run thousands of such evaluations per site. The greedy, by contrast, builds its demand field from the *measured* baseline UTCI grid, places trees deterministically by where shade actually falls, carries a provable approximation guarantee, and spends its single expensive live simulation validating one layout rather than scoring three thousand on a proxy. For a tool whose output directs public money, an interpretable engine on measured data beats an elaborate engine on a surrogate. The evolutionary path remains in the codebase as a documented alternative and a benchmark, but it is not what ships, and the paper now says so.

The three-tier backend is the architectural expression of the same value. Hackathon and prototype tools routinely blur the line between a number that was computed and a number that was wished for; CoolSpend forces the distinction into the type system. The mock backend is not a placeholder to be apologised for — it is the mechanism that lets the *geometry-real, cooling-synthetic* preview run anywhere in the city without spending a paid simulation, while a single environment variable promotes any site to a measured live evaluation.

The population-served metric deserves emphasis as a bridge between thermal physics and public value. A plan that cools an empty lot and a plan that cools a dense residential block can have identical UTCI profiles; person-degrees and population-served distinguish them, and they tie the tool directly to the access norm (300 m) that municipalities increasingly adopt. This reframes the optimisation target from "cool the most ground" toward "relieve the most people," which is the question a public-health-minded planner actually asks.

---

## 9. Limitations

We enumerate the limitations frankly, because a tool that informs spending should be judged on what it does not yet know as much as on what it does. Several have been substantially remediated this cycle; we report the current state.

1. **Satellite-composite provenance** *(substantially remediated).* The composite *formula* is exactly reproducible in-repo — a least-squares fit over all 494 cells recovers a single constant weight vector that reconstructs `composite_score_B` to floating-point epsilon (R² = 1.0), verified by a regression test. The genuine residual gap is narrower: the derivation of three sub-scores from *raw imagery* — the Sentinel-1 SAR-to-sealed classifier and its training data, the Landsat LST-anomaly baseline, and the `mismatch`/`prpi` index definitions — lives in an upstream ingestion pipeline and remains undocumented here. Closing it requires the ingestion source, not a re-run of CoolSpend.

2. **Coverage proxy versus measured cooling** *(remediated in the deployed engine).* The greedy weights each (slot, species)→cell pair by ray-cast **shade-gain** — the fraction of sampled suns whose crown shadow lands on the cell — rather than binary crown overlap, with per-cell captured gain capped so double-shading earns nothing; the objective stays submodular (preserving the (1 − 1/e) guarantee). The residual is epistemic, not procedural: shade-gain is a first-order direct-beam proxy used only for *placement order*, so the cooling *magnitude* is always taken from the live UTCI validation, by design.

3. **Synthetic cooling on non-live backends** *(remediated for the headline).* The headline €1,000,000 portfolio and the single-site showcase are assembled from **live Infrared UTCI** (`cooling_source = "measured_utci"`), cached by geometry hash for offline replay, and funded by measured €/m²-cooled. For sim-free builds, a three-tier `CoolingEstimator` provides a geometry-grounded shade-proxy *estimate* with the measured-vs-estimate distinction enforced by an `is_measured` flag and surfaced as a UI badge. The residual honesty point is that the cheapest sim-free tier remains an estimate, by design.

4. **Surrogate thermal relief in the NSGA-II alternative** *(remediated; not in the deployed path).* The assumed ±4 °C uncertainty is replaced by an empirical **±0.78 °C** band from a live calibration study (1.96 × RMSE). The study also quantified the surrogate's character honestly — R² = −0.946 (weak magnitude) but Spearman ρ = 0.69 (moderate ranking) — which is exactly why the surrogate is confined to ranking inside an alternative the production pipeline does not use. The 12 °C cap is a non-binding guard never reached in practice.

5. **Unsurveyed sub-surface conditions.** Underground utilities and exact sidewalk widths are absent from open data. In-ground slots are flagged for a pre-dig utility survey rather than asserted clear, and the 6 m foundation setback is a conservative placeholder pending species-specific and code-specific verification.

6. **Cost calibration** *(remediated).* The single `REQUIRES_VERIFICATION` constant — the UTCI-hours-above-32 °C removed per °C of cooling — is now computed directly from the in-repo Barcelona TMYx EPW via the project's ladybug UTCI machinery (≈47 h/°C, band-mean), rather than the prior hand-derived 200 h/°C. The relationship is convex, so the constant is reported with its band; the live calibration study remains the arbiter. Three of the five CapEx lines are `DECLARED` pending direct BCN tender unit-price extraction.

7. **Portfolio budget headroom.** The committed plan spends €900,000 of €1,000,000; the remaining €100,000 is uncommitted because the feasibility, population-weighting and per-*barri* de-duplication filters exhausted the qualifying candidate pool before a seventh distinct site cleared every gate. Widening the candidate pool (a larger top-N) would commit the remainder across more sites — a deliberately conservative default rather than a defect.

8. **Single-city scope and static meteorology.** The data assembly, species palette and cost figures are Barcelona-specific, and the UTCI window is a fixed July peak-heat period; seasonal and inter-annual variation, and transfer to other climates, are out of scope here.

---

## 10. Conclusion

CoolSpend demonstrates that the planting decisions a city actually faces — where, which species, how to spend a fixed budget — can be answered by a system that is simultaneously geometry-real, ecology-real, population-real, budget-bounded, and honest about the boundary between measured and synthetic results. The deployed placement is a principled budgeted coverage maximisation on a *measured* UTCI demand field, carrying a classical approximation guarantee, screened against an ecological-health gate that excludes invasive and over-represented species; cooling is evaluated on a recognised thermal-comfort index; and outcomes are reported in the practitioner's own terms, including a population-served metric tied to an internationally adopted access norm. A live single-site run at Plaça dels Àngels cools 4,268 m² of ground at €30 per m² cooled, lowering peak felt temperature from 31.0 to 29.8 °C, and a €1,000,000 portfolio funds 90 trees across 6 sites — cooling a measured 20,609 m² and serving roughly 26,745 residents at €44 per m² cooled — with no invasive or phase-down species. The system's most transferable idea is its honesty architecture: the discipline of never reporting a number it did not compute, and of labelling every preview as a preview. Future work is dictated by the limitations — closing the satellite-composite provenance, widening the candidate pool so the final €100,000 commits a seventh site, replacing the placement-proxy shade-gain with measured per-tree fields, and integrating a utility survey — each of which tightens the link between a recommendation and the public money it would direct.

---

## Data Availability Statement

The system integrates publicly available data: the Barcelona municipal population register (*Padró*, dataset `pad_mdbas`) and street-tree inventory (*arbrat viari*) from the Barcelona Open Data portal; neighbourhood boundary geometry from an open GeoJSON mirror; building, road and street-furniture geometry from OpenStreetMap via the Overpass API; and satellite-derived heat, imperviousness and vegetation layers (Landsat, Sentinel-1, Sentinel-2). UTCI fields are produced by the third-party Infrared.city engine, which requires an API key and is not redistributable. The satellite vulnerability composite (`scored_grid`) is a derived product; its ranking formula is exactly reproducible in-repo (`coolspend/provenance.py`), while the derivation of its constituent sub-scores from raw imagery is external (see Limitations). Project source code and cached non-proprietary artifacts are held in the project repository.

## Ethics Declaration

This study involves no human subjects, no personal data, and no animal experimentation. The population data used are aggregate neighbourhood-level resident counts from a public municipal register; no individual-level data are processed.

## Author Contributions (CRediT)

**R. El Khoury:** Conceptualization, Methodology, Software, Validation, Formal analysis, Data curation, Writing – original draft, Visualization. AI-assisted tooling contributed to software implementation and manuscript drafting under author direction and review (see AI Disclosure).

## Conflict of Interest Statement

The author declares no competing financial or non-financial interests. The work was prepared as an independent submission to the Infrared.city Buildathon 2026; the use of the Infrared.city engine reflects the event context and confers no commercial relationship.

## Funding

No external funding was received for this work. The €1,000,000 figure is a hypothetical capital budget used to demonstrate the allocation method and does not represent committed funds.

## AI Disclosure

This manuscript and the underlying system were developed with assistance from an AI coding and writing assistant (Anthropic Claude). AI assistance was used for software implementation, code and data fact-extraction, literature citation retrieval and verification, and manuscript drafting. All technical facts reported here — constants, formulae, algorithm behaviour, and result numbers — were extracted from and verified against the project source code (`coolspend/` modules and `web/public/citywide_plan.json`); all external citations were verified against publisher records and carry DOIs. The author reviewed and is responsible for all content.

---

## References

Bowler, D. E., Buyung-Ali, L., Knight, T. M., & Pullin, A. S. (2010). Urban greening to cool towns and cities: A systematic review of the empirical evidence. *Landscape and Urban Planning, 97*(3), 147–155. https://doi.org/10.1016/j.landurbplan.2010.05.006

Bröde, P., Fiala, D., Błażejczyk, K., Holmér, I., Jendritzky, G., Kampmann, B., Tinz, B., & Havenith, G. (2012). Deriving the operational procedure for the Universal Thermal Climate Index (UTCI). *International Journal of Biometeorology, 56*(3), 481–494. https://doi.org/10.1007/s00484-011-0454-1

Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. *IEEE Transactions on Evolutionary Computation, 6*(2), 182–197. https://doi.org/10.1109/4235.996017

Hwang, C. L., & Yoon, K. (1981). *Multiple attribute decision making: Methods and applications*. Springer-Verlag. https://doi.org/10.1007/978-3-642-48318-9

Konijnendijk, C. C. (2023). Evidence-based guidelines for greener, healthier, more resilient neighbourhoods: Introducing the 3–30–300 rule. *Journal of Forestry Research, 34*(3), 821–830. https://doi.org/10.1007/s11676-022-01523-z

Leskovec, J., Krause, A., Guestrin, C., Faloutsos, C., VanBriesen, J., & Glance, N. (2007). Cost-effective outbreak detection in networks. In *Proceedings of the 13th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining* (pp. 420–429). ACM. https://doi.org/10.1145/1281192.1281239

Mueller, N., Rojas-Rueda, D., Khreis, H., Cirach, M., Andrés, D., Ballester, J., Bartoll, X., Daher, C., Deluca, A., Echave, C., Milà, C., Márquez, S., Palou, J., Pérez, K., Tonne, C., Stevenson, M., Rueda, S., & Nieuwenhuijsen, M. (2020). Changing the urban design of cities for health: The superblock model. *Environment International, 134*, 105132. https://doi.org/10.1016/j.envint.2019.105132

Nemhauser, G. L., Wolsey, L. A., & Fisher, M. L. (1978). An analysis of approximations for maximizing submodular set functions—I. *Mathematical Programming, 14*(1), 265–294. https://doi.org/10.1007/BF01588971

Nowak, D. J., Crane, D. E., & Stevens, J. C. (2006). Air pollution removal by urban trees and shrubs in the United States. *Urban Forestry & Urban Greening, 4*(3–4), 115–123. https://doi.org/10.1016/j.ufug.2006.01.007

Oke, T. R. (1982). The energetic basis of the urban heat island. *Quarterly Journal of the Royal Meteorological Society, 108*(455), 1–24. https://doi.org/10.1002/qj.49710845502

Rahman, M. A., Stratopoulos, L. M. F., Moser-Reischl, A., Zölch, T., Häberle, K.-H., Rötzer, T., Pretzsch, H., & Pauleit, S. (2020). Tree cooling effects and human thermal comfort under contrasting species and sites. *Agricultural and Forest Meteorology, 287*, 107941. https://doi.org/10.1016/j.agrformet.2020.107941
