# CoolSpend: A Budget-Constrained Decision-Support System for Street-Tree Placement to Mitigate Urban Heat in Barcelona

**R. El Khoury**
*Infrared.city Buildathon 2026 — Independent submission*

---

## Abstract

Urban heat is a spatially concentrated, life-threatening hazard, yet the planting decisions that mitigate it — *which* species, placed *where*, for *how much* benefit per euro — are usually made without a quantitative, geometry-aware, budget-bounded model. We present **CoolSpend**, an end-to-end decision-support system that recommends where to plant street trees anywhere in Barcelona, evaluates the resulting outdoor thermal comfort against simulated Universal Thermal Climate Index (UTCI) fields, and allocates a fixed capital budget across the city's most heat-vulnerable sites. The system couples four classes of real data — satellite heat and imperviousness (Landsat thermal land-surface temperature, Sentinel-1 sealed-surface, Sentinel-2 vegetation) aggregated into a 494-cell vulnerability grid; OpenStreetMap building, street and furniture geometry; the Barcelona municipal street-tree inventory; and the municipal population register — with the Infrared.city pedestrian-comfort engine. Placement is posed as budgeted weighted maximum coverage over a building-, street- and furniture-aware lattice of validated planting slots, solved with a greedy algorithm carrying the classical (1 − 1/e) submodular guarantee; an alternative path solves a bi-objective (thermal relief vs. ecological coherence) formulation with NSGA-II. Species selection enforces an ecological-health gate that excludes exotic-invasive taxa and the over-represented London plane (*Platanus* × *acerifolia*). A multi-site allocator spreads a €1,000,000 budget across geographically separated sites under a per-site cap, partial-funding the final site so the full budget is committed. We quantify outcomes the way practitioners do: cooled ground area, mean and peak UTCI reduction, cost per square metre cooled, canopy cover against the 30% target, and a *population-served* metric using the World Health Organization-endorsed 300 m green-access catchment. On a live Infrared.city run for a 0.5 ha plaza, 20 placed trees cool 2,838 m² of ground by at least 0.5 °C, with a mean UTCI reduction of 1.86 °C at €70.5 per m² cooled. A €1,000,000 portfolio (placement and population real; per-site cooling a labelled synthetic preview) funds 100 trees across 7 sites, serving approximately 24,612 residents and adding 5,451 m² of mature canopy with zero invasive or phase-down species. We report the system honestly: a three-tier backend (mock, cached, live) makes the distinction between *measured* and *synthetic* cooling explicit at every stage, and we enumerate the provenance gaps (notably the raw-imagery derivation of the satellite vulnerability sub-scores) that a production deployment would need to close. The contribution is less a new algorithm than a faithful, auditable assembly: real geometry, real ecology, real population, a bounded optimiser, and a discipline of never reporting a number we did not compute.

**Keywords:** urban heat island; Universal Thermal Climate Index; street-tree placement; submodular optimisation; urban greening; decision-support system; Barcelona; nature-based solutions

---

## 1. Introduction

Cities are warmer than the rural land that surrounds them. The urban heat island (UHI) — the systematic temperature excess of the built environment — arises from the radiative and thermal properties of urban surfaces: dark, sealed materials with high heat capacity absorb shortwave radiation by day and re-radiate it by night, while reduced vegetation suppresses the evaporative cooling that would otherwise dissipate that energy (Oke, 1982). The consequence is not an abstraction. Heat is among the deadliest climate hazards, and its burden falls unevenly across a city's blocks: the hottest places are typically the most sealed, the least vegetated, and — frequently — among the most densely inhabited.

Urban trees are the canonical intervention. They cool through two coupled mechanisms: shade, which intercepts shortwave radiation before it reaches and heats a surface, and transpiration, which converts absorbed energy into latent heat. A systematic review of the empirical literature found that, on average, an urban park is roughly 1 °C cooler than its surroundings during the day, with tree-dominated greening producing the most reliable effect (Bowler et al., 2010). Species and site mediate the magnitude: contrasting street-tree species under comparable conditions differ measurably in their air-temperature, surface-temperature and physiologically-equivalent-temperature reductions (Rahman et al., 2020), and trees deliver co-benefits beyond cooling, including measurable air-pollution removal (Nowak et al., 2006).

Knowing that trees cool, however, does not tell a city *where to plant them, which species to choose, or how to spend a finite budget*. These are the questions a planner actually faces, and they are rarely answered with a model that is simultaneously (a) grounded in real site geometry, so that a recommended tree does not land on a roof or against a foundation; (b) grounded in real species ecology, so that the palette is plantable and not invasive; (c) evaluated against a defensible thermal-comfort metric rather than a hand-waved temperature drop; and (d) bounded by a real budget, so that the recommendation is an *allocation*, not a wish list.

CoolSpend is our attempt to answer all four at once for the city of Barcelona, a Mediterranean (Köppen *Csa*) city with hot, dry summers, an extensive sealed core, and an active municipal agenda of de-paving and urban greening exemplified by its "superblock" (*superilla*) programme (Mueller et al., 2020). The system lets a user draw a polygon anywhere in the city or accept an automatically ranked list of the most heat-vulnerable cells, and returns a concrete, costed, ecologically screened planting plan whose cooling is evaluated on the Infrared.city UTCI engine. It then scales that single-site capability into a city-wide capital-allocation tool that spreads a €1,000,000 budget across the highest-priority sites.

Our contribution is threefold. First, a **faithful data assembly**: four independent real-world data sources (satellite, OpenStreetMap, municipal tree inventory, municipal census) are fused into a placement model in which every spatial exclusion is enforced from open data, and the absence of survey-grade data (underground utilities, sidewalk widths) is flagged rather than silently assumed away. Second, a **bounded optimisation layer** that treats placement as budgeted weighted maximum coverage with a provable approximation guarantee, complemented by a multi-objective evolutionary alternative and a multi-site capital allocator. Third, and most important for a tool intended to inform public spending, an **honesty architecture**: a three-tier simulation backend that never lets a synthetic preview masquerade as a measured result, and a set of practitioner-facing metrics (cost per m² cooled, canopy cover against target, population served) that a non-specialist reviewer can interrogate.

The remainder of this paper is organised as follows. Section 2 situates the work in urban-climate and optimisation literature. Section 3 describes the four data sources and their provenance, including the gaps. Section 4 details the methods: candidate-slot generation, the greedy and evolutionary placement algorithms, species ecology screening, growth modelling, the cost model, and the multi-site allocator. Section 5 presents the system architecture and the three-tier backend. Section 6 reports results for a live single-site run and the €1,000,000 portfolio. Section 7 documents a structured validation against sixteen urban-design knowledge bases. Section 8 discusses implications, Section 9 enumerates limitations frankly, and Section 10 concludes.

---

## 2. Background and Related Work

### 2.1 Thermal comfort and the choice of metric

A cooling intervention should be judged by what people *feel*, not only by air temperature. The Universal Thermal Climate Index (UTCI) is an equivalent-temperature index derived from a multi-node model of human thermoregulation coupled to an adaptive clothing model; it integrates air temperature, mean radiant temperature, wind and humidity into a single value expressed in degrees Celsius, defined as the air temperature of a reference environment that would produce the same physiological strain (Bröde et al., 2012). UTCI is well suited to evaluating tree shade because shade acts primarily on the *mean radiant temperature* term — the dominant driver of daytime outdoor discomfort — which a simple air-temperature metric would miss. CoolSpend adopts UTCI as its headline thermal metric and uses the 26 °C threshold (the boundary between "no thermal stress" and "moderate heat stress") both as the comfort cut-off for demand weighting and as the heat-stress-relief threshold for reporting.

### 2.2 Greening targets and access norms

Beyond per-site cooling, contemporary urban-greening practice is increasingly organised around access and coverage norms. The **3–30–300 rule** (Konijnendijk, 2023) synthesises the evidence into three thresholds: at least three mature trees visible from every home, at least 30% canopy cover in every neighbourhood, and a high-quality green space within 300 m of every residence. CoolSpend operationalises two of these directly: the 30% canopy-cover target drives its design-metric scoring, and the 300 m catchment defines the radius of its population-served calculation, which we treat as a proxy for the "300" access criterion.

### 2.3 Placement as submodular coverage

The core placement problem — choose a set of tree locations that maximises demand-weighted shade coverage under a budget — is an instance of *weighted maximum coverage*, whose objective is monotone and submodular (adding a tree never decreases coverage, and its marginal benefit diminishes as coverage grows). For such objectives, the greedy algorithm that repeatedly adds the highest-marginal-gain element achieves at least (1 − 1/e) ≈ 63% of the optimum (Nemhauser et al., 1978). Under a budget (knapsack) constraint, a cost-benefit greedy that ranks candidates by marginal-gain-per-cost retains a constant-factor guarantee, and the lazy-evaluation refinement (CELF) accelerates it by orders of magnitude by exploiting submodularity to skip stale re-evaluations (Leskovec et al., 2007). CoolSpend's primary placement engine is a budgeted cost-benefit greedy of exactly this lineage.

### 2.4 Multi-objective design

Cooling is not the only design objective: a monoculture optimised purely for shade is ecologically fragile. We therefore also expose a bi-objective formulation — thermal relief versus ecological coherence — and solve it with the Non-dominated Sorting Genetic Algorithm II (NSGA-II), the standard elitist multi-objective evolutionary algorithm, which returns a Pareto front of non-dominated trade-offs in a single run via fast non-dominated sorting and crowding-distance diversity preservation (Deb et al., 2002). Selecting a single plan from the front is a multi-criteria decision problem, for which we use the Technique for Order of Preference by Similarity to Ideal Solution (TOPSIS) (Hwang & Yoon, 1981).

---

## 3. Data

CoolSpend fuses four independent real-world data sources. We describe each, its role, and — in keeping with the honesty architecture — its provenance limits.

### 3.1 Satellite heat-vulnerability grid

Site *prioritisation* (where in the city to act) is driven by a pre-computed vulnerability grid, `scored_grid`, covering Barcelona in **494 cells** of approximately 400 m × 400 m (≈160,000 m² each) in the EPSG:25831 (UTM zone 31N) projection. Each cell carries:

- `mean_lst_celsius` and `lst_anomaly` — mean land-surface temperature and its anomaly, derived from **Landsat** thermal infrared bands;
- `mean_sealed` — the impervious/sealed-surface fraction (0–1), derived from **Sentinel-1** synthetic-aperture radar;
- `mean_ndvi` — the Normalised Difference Vegetation Index, derived from **Sentinel-2** optical bands, used as an existing-vegetation signal;
- `composite_score_B` — the primary ranking signal, a composite emphasising the product of heat and sealing (hot × sealed), so that the highest-priority cells are those that are simultaneously hottest and most paved;
- administrative attributes (`district`, `barri`) and existing street-tree counts from the municipal inventory.

This grid is a satellite-derived *heat-vulnerability* surface, **not** a UTCI field. It answers *where to look*, not *how much cooling a plan delivers*. Crucially, it requires no live API calls: prioritisation reads the static grid.

**Provenance.** The composite is fully reproducible in-repo: a least-squares fit over all 494 cells recovers the exact weights `0.45·sealed + 0.20·LST-anomaly + 0.15·(1−NDVI) + 0.05·mismatch + 0.15·prpi`, reconstructing `composite_score_B` to floating-point epsilon (see `coolspend/provenance.py`, the datasheet in `docs/scored_grid_datasheet.md`, and the regression test). The residual gap is narrower than first stated: the derivation of three sub-scores from raw imagery — the Sentinel-1 SAR-to-sealed classifier, the Landsat LST-anomaly baseline, and the `mismatch`/`prpi` indices — lives in an upstream ingestion pipeline and is not documented here (Section 9, item 1).

### 3.2 OpenStreetMap geometry

Physical placement validity is enforced from **OpenStreetMap** (OSM) data retrieved via the Overpass API and cached locally:

- **Building footprints**, which exclude planting on roofs and enforce clearance from façades. Critically, OSM buildings are *backend-independent*: they are available even when no Infrared.city building layer is (the Infrared building layer is a live-only product), which is what keeps a tree off a roof on the mock and cached backends.
- **Road carriageways** and **junction sight-triangles**, which exclude the trafficked roadway (plazas and footways remain plantable).
- **Street furniture** — hydrants, crossings, stops, lamp posts, signals, manholes, power lines — which carry local exclusions.

When Overpass is unreachable, these exclusion sets degrade gracefully to empty rather than failing, with the degradation logged.

### 3.3 Municipal street-tree inventory

Species parameters derive from Barcelona's *arbrat viari* (street-tree) inventory, the basis for a 12-species candidate table with per-species mature crown diameter and height assigned from the inventory's documented size bands (height: low <6 m → 4 m, medium 6–15 m → 10 m, tall >15 m → 18 m; crown: narrow → 3 m, medium → 5 m, wide → 7 m, very wide → 10 m). The inventory also supplies the *existing* trees within a site, whose mature canopy footprints are treated as already-shaded ground and excluded from planting demand.

### 3.4 Municipal population register

The population-served metric uses the Barcelona municipal register (*Padró*) published as open data (dataset `pad_mdbas`), which records **1,702,814** registered residents (2024 vintage) across the city's **73 *barris*** (neighbourhoods). Neighbourhood boundary geometry is taken from an open GeoJSON mirror in WGS84 and joined 1:1 to the register by neighbourhood code. All areal computation is performed in EPSG:25831 so that catchment areas and densities are in true metres.

---

## 4. Methods

### 4.1 Candidate-slot generation

CoolSpend never optimises over continuous space; it optimises over a finite set of *validated* candidate slots. Slots are generated on a deterministic 4 m lattice (`GRID_STEP_M = 4.0`) walked in row-major order, then each candidate is validated against a conjunction of constraints:

1. **Inside the site boundary** polygon.
2. **Not inside any building footprint** (no roofs).
3. **Building clearance**, which depends on the *planting mode* (see below).
4. **Outside the street buffer** (trunk kept off the carriageway).
5. **At least `MIN_SPACING_M` from existing trees and from already-accepted slots.**

The minimum spacing is **8 m**. This value is not arbitrary: it is the interval at which three independent design standards converge — NACTO's 6–9 m on-centre street-tree spacing, the climate-responsive guideline that "trees at 8–10 m create continuous canopy at maturity" for Mediterranean conditions, and de-paving practice's default 6–10 m. An earlier 5 m value packed canopies into overlapping clumps; 8 m produces a legible allée and prevents the visual "trees everywhere" failure mode.

**Two planting modes** encode the central de-paving trade-off:

- **Planter mode** — a tree in a large planter resting on the pavement. Roots are contained, so there is no foundation risk and the tree may sit near a building, requiring only a 0.6 m physical wall clearance (`PLANTER_WALL_CLEARANCE_M`). No de-paving is needed, but the contained root volume caps the mature crown and raises watering cost.
- **In-ground mode** — a de-paved pit with roots in soil. This permits the full mature crown but introduces foundation risk, so a 6 m setback from any building is enforced (`FOUNDATION_SETBACK_M`), and the de-paving incurs a pit cost over a 9 m² (3 m × 3 m) structural tree-pit footprint.

Two honesty flags attach here. The 6 m foundation setback is a conservative single value for large street species and is marked as requiring verification against species-specific root-spread and municipal setback code. And because underground utilities are not present in open data, every in-ground slot in the output carries a `requires_utility_survey` flag — the system asserts plantability from the best available data but explicitly declines to assert clearance of buried mains it cannot see.

### 4.2 Demand field

Placement maximises coverage of a *demand field* — a set of weighted cells representing ground that is hot, paved, and unshaded. On the live backend, the field is built from the baseline UTCI grid: a cell becomes a demand cell if and only if its UTCI exceeds the 26 °C comfort threshold, it is impervious, it is not already shaded by an existing canopy, and its value is not NaN. The cell weight is `UTCI − 26`, so hotter ground attracts more shade.

Two robustness mechanisms matter. First, the Infrared.city SDK returns a 512 × 512 grid that spans a square larger than the drawn polygon; the field builder crops the grid to its non-NaN bounding box before mapping rows and columns onto the polygon's extent, fixing a registration error that otherwise scattered demand to the wrong coordinates and produced zero placements. Second, if the impervious filter eliminates *all* demand (sparse or misclassified land cover), the builder falls back to treating all hot, unshaded ground as demand — an honest degradation that shades the hottest ground it can confirm rather than refusing to act.

On the mock and cached backends, where no measured UTCI grid exists, the builder substitutes a uniform proxy demand (a 40 × 40 lattice over the bounding box). This is the crux of the honesty design: **placement remains real and valid even when the cooling number is a labelled synthetic preview**, because placement depends on geometry and the proxy field, not on measured cooling.

### 4.3 Greedy weighted maximum-coverage placement

The primary placement engine (`smart_placement`) solves budgeted weighted maximum coverage. For a set *S* of placed trees, the objective is

> value(*S*) = Σ weight(cell), over all demand cells covered by at least one tree in *S*,

where a tree of species with crown diameter *d* covers every demand cell within radius *d*/2. The algorithm is a cost-benefit greedy: at each step it computes, for every (slot, species) pair, the *marginal* demand weight newly covered, divides by the tree's cost to obtain gain-per-euro, and selects the maximum, breaking ties first by the species' cooling score and then by absolute marginal gain (for determinism). Selection stops when no affordable slot yields positive marginal gain or the budget is exhausted.

This inherits the (1 − 1/e) submodular guarantee (Nemhauser et al., 1978) in its cost-benefit form (Leskovec et al., 2007). Two refinements temper a pure shade-maximiser: an **anti-monoculture constraint** caps any single species at 40% of the placement after a four-tree grace period, and the per-tree crown used for coverage is capped to the site (Section 4.4).

We are explicit about what the greedy objective is and is not. The demand weights are computed on the *baseline* UTCI field — the field before any tree is planted. True cooling is non-linear: a planted tree changes the field, so the greedy "gain" is a coverage *proxy* for marginal cooling, not measured cooling. The chosen layout's true cooling is established afterward by a live UTCI simulation (Section 4.8).

### 4.4 Crown-to-site matching

A mature canopy must not grow into a wall, but it *should* overhang the street it shades. The crown cap therefore depends on distance to the nearest **building façade only**: `max(5 m, 2 × distance-to-building)`. Streets and sidewalks deliberately do not cap the crown — overhanging the carriageway is precisely the shade being purchased, and the trunk is already kept out of the street buffer at the slot-validation stage. The 5 m floor ensures the smallest species can always fit; an earlier version that also capped on street distance shrank crowns below the smallest species on tight plazas and produced zero placements.

### 4.5 Species ecology and the plantability gate

Species selection is governed by a single source of truth, an ecological-health composite combined with a hard plantability gate.

The **ecosystem-health score** (0–1) is a weighted sum of benefits minus penalties:

- *Benefits:* drought/heat tolerance (0.30), biodiversity value (0.20), pollinator value (0.20), longevity (0.15, from maturity years normalised over 30–150 years), native status (0.15; native → 1.0, naturalised → 0.6, exotic → 0.4, invasive → 0.0).
- *Penalties:* allergenicity (0.15, OPALS-scaled pollen burden), pest/disease risk (0.10), water demand (0.10), maintenance burden (0.10), and a hard invasive veto (0.30 subtracted when the species is invasive).

This score is always reported *alongside* the cooling and cost metrics, never blended into them, so that an ecological trade-off is visible rather than hidden inside a single number.

The **plantability gate** (`is_plantable`) removes four taxa from the 12-species table, leaving an **8-species** palette:

- three **exotic-invasive** species — *Robinia pseudoacacia*, *Ligustrum lucidum*, *Ulmus pumila* — vetoed outright;
- the **phase-down** species *Platanus* × *acerifolia* (London plane), which constitutes roughly a quarter of Barcelona's street trees, carries high allergy and disease burden, and is being deliberately reduced; the municipality's over-reliance on it is exactly the monoculture risk the system is designed to avoid amplifying.

The same gate is the single species source for both the greedy engine and the NSGA-II optimiser, so neither path can ever recommend an excluded species.

### 4.6 Growth and time-to-maturity

A newly planted tree does not deliver its mature cooling on day one. CoolSpend models establishment with a growth-discount ramp: cooling benefit rises linearly from an initial 20% at planting to 100% over a 25-year establishment period, after which it is held constant, with future benefits discounted at 3.5% per year (the EU/UK Green Book convention) over a 40-year functional horizon.

The "years after planting" experience is, however, *species-specific*, and the system makes this explicit. Each species' time to near-mature canopy is assigned from its growth-rate band — fast = 20 years, medium = 30 years, slow = 40 years — consistent with arboricultural (i-Tree) establishment ranges and with the climate-responsive guideline's "continuous canopy at maturity (20–30 years)". This per-species maturity rides through to the interactive inspector, so a reviewer clicking a fast-growing *Tipuana tipu* sees a 20-year maturity while a slow *Cercis siliquastrum* shows 40 — the growth datum is no longer one flat curve.

### 4.7 Cost model

The capital and operating costs are itemised, not assumed. Per-tree capital expenditure totals **€2,200**: tree stock at large caliper (€600), pit excavation (€500), structural soil (€600), guarding (€200, verified against Diputació de Barcelona figures), and planting labour (€300, likewise verified). Operating expenditure is **€60 per tree per year**, derived from Barcelona's municipal parks-institute 2023 activity accounts (€12,658,229 maintenance ÷ 206,556 trees = €61.28/tree/year, rounded). Costs are evaluated over the 40-year horizon. One calibration constant in the cost-per-degree-hour conversion is flagged as requiring verification.

### 4.8 Multi-objective alternative and validation

The alternative optimiser poses a bi-objective problem solved with NSGA-II. The decision vector has 3·*n* genes — *n* (*x*, *y*) positions plus *n* species genes — where the tree count *n* scales with site area at one tree per 225 m² (15 m × 15 m nominal), clamped to [12, 100] for tractability. The two objectives (both minimised by pymoo convention) are the negative of a site-averaged thermal-relief surrogate weighted by mean species cooling factor, and the negative of an ecological-coherence (diversity) score; the budget enters as an inequality constraint. NSGA-II runs with a population of 60 over 60 generations (3,600 evaluations), simulated-binary crossover (probability 0.9, η = 15), polynomial mutation (η = 20), and a fixed seed of 42 for reproducibility. From the Pareto front, three configurations are selected — best thermal, best ecological, and the balanced point nearest the normalised utopia corner — then ranked by TOPSIS with weights (thermal 0.6, ecological 0.4) and a primary cost-per-UTCI-degree criterion.

Both paths converge on the same validation step. The chosen layout(s) are submitted to the Infrared.city engine for a true UTCI evaluation: one baseline simulation (uncounted) plus up to three intervention simulations, hard-capped by a simulation budget. The thermal-relief surrogate used inside NSGA-II is an analytical proxy with a stated ±4 °C uncertainty, explicitly *not* a measured value — only the post-hoc Infrared run yields the reported ΔUTCI.

### 4.9 Cooled-footprint profile

Given baseline and intervention UTCI grids (512 × 512 at 1 m resolution, evaluated for the July 09:00–17:00 peak-heat window at 1.1 m pedestrian height), the system computes a multi-band cooled-footprint profile:

- **cooled area by band** — m² cooled by ≥0.5 °C, ≥1 °C and ≥2 °C;
- **mean, standard deviation, 10th/90th percentile and peak** of the per-cell UTCI drop over cooled cells;
- **heat-stress area relieved** — m² that crosses from ≥26 °C at baseline to <26 °C after;
- **largest contiguous cooled patch** and **patch count**, via connected-component labelling (4-connectivity), distinguishing one continuous shaded corridor from scattered dapples;
- the **peak** felt-temperature is reported as the 90th-percentile cell rather than the maximum, to avoid a single outlier driving the headline.

The headline "cooled footprint" is the ≥0.5 °C band.

### 4.10 Multi-site €1,000,000 allocation

The city-scale tool spreads a fixed budget across the highest-priority cells. By default it considers the top 12 cells, caps any single site at €150,000 (≈ enough for an uncrowded ~15–20-tree intervention, not a saturated plaza), and enforces a **500 m minimum separation** between funded sites so the portfolio is geographically distributed rather than clustered in one hot district. Funding order is by ascending cost-per-m²-cooled when measured cooling exists, and otherwise by descending `composite_score_B`. To commit the *entire* budget, the final site is **partial-funded**: if the remainder cannot fund a full site, the site's best-value trees are kept as a prefix sized to the remaining euros and the site is marked partial.

Each funded site carries its placed trees, its population served, and its design metrics; the portfolio aggregates total trees, total cooled area, total canopy, total person-degrees, and a de-duplicated total population served.

### 4.11 Population served

Population served operationalises the 300 m access criterion of the 3–30–300 rule (Konijnendijk, 2023). For a single site, residents within a 300 m catchment are estimated by intersecting the catchment disc with neighbourhood polygons in EPSG:25831 and area-weighting each neighbourhood's resident density. For a portfolio, the catchment discs are unioned and the population is computed against the union geometry, so residents in the overlap of two nearby sites are counted **once** — a de-duplicated, area-weighted union rather than a naïve sum.

### 4.12 Design metrics

Three geometric metrics translate a plan into planner-legible terms. **Canopy area** is the sum of mature crown discs (Σ π r²). **Canopy cover** is that area as a percentage of the site, scored against the 30% target with the gap reported. An **estimated air-temperature drop** applies the climate-literature midpoint of 0.075 °C per +1 percentage-point of canopy cover (the centre of the 0.5–1.0 °C-per-10% range). **Person-degrees** — residents served × mean UTCI reduction — is a single people-weighted heat-relief figure. These are explicitly geometric estimates; measured cooling remains the UTCI simulation.

---

## 5. System Architecture

CoolSpend is a Python computational core exposed through a FastAPI service to a deck.gl/Mapbox web client.

### 5.1 Three-tier simulation backend

The defining architectural decision is a three-tier Infrared backend selected by environment variable, designed so that a synthetic result can never be mistaken for a measured one:

- **mock** — a deterministic scalar UTCI model (open-plaza 41.0 °C interpolated toward under-canopy 30.5 °C by coverage fraction). It performs **no network call** and every result carries the disclaimer "NOT MEASURED DATA — synthetic field for UI integration only." It exists so the full pipeline (placement, costing, metrics, web export) runs offline with real geometry but a labelled synthetic cooling estimate.
- **cached** — replays a prior result from a disk cache keyed by a SHA-256 hash of the query geometry. On a cache miss it raises an error rather than silently falling through to mock, and replayed results are tagged with their original provenance.
- **live** — calls the real Infrared.city UTCI engine, requires the API key, hits the network once per evaluation, and writes the result to the cache for later offline replay.

A simulation budget hard-caps live calls at three per run, so a single evaluation can never trigger an unbounded burst of paid simulations. The API key is never read into a return value, logged, or serialised.

### 5.2 Pipeline and endpoints

The FastAPI layer exposes: a polygon-preview endpoint (building count and impervious analysis, no simulation); `/api/evaluate`, which runs the full single-site pipeline on a drawn polygon and writes a self-contained web bundle (decision JSON, trees and boundary GeoJSON, raster bounds, baseline and intervention UTCI PNGs, optional 3D scene); `/api/citywide/scan`, a fast ranking of the 494 cells with no live calls; and `/api/citywide/allocate`, the multi-site allocator. The evaluate endpoint writes to an isolated bundle directory distinct from the curated showcase, so an exploratory user run cannot overwrite the demonstration artifact.

### 5.3 Web client

The client renders on a Mapbox satellite basemap with a deck.gl overlay. Proposed and existing trees are drawn as **canopy-footprint discs** (ScatterplotLayer) whose radius is the true crown radius in metres — the literal ground area shaded — which is both more honest than a generic sprite and more robust to render over a basemap than metre-scale billboards. The UTCI heatmap is draped as a bitmap cropped to its valid extent and colourised on a 20–40 °C red–blue scale with out-of-polygon cells fully transparent. A click inspector surfaces each tree's species identity, shade footprint, full ecological profile, and species-specific time-to-maturity. A separate city-wide mode renders the satellite vulnerability grid and the €1,000,000 plan as per-site markers with a portfolio panel.

---

## 6. Results

### 6.1 Live single-site evaluation

We evaluated a ~0.5 ha plaza on the **live** Infrared.city backend. The greedy engine placed **20 trees** drawn from the plantable palette. The measured cooled-footprint profile reported **2,838 m² cooled by at least 0.5 °C**, a **mean UTCI reduction of 1.86 °C** over cooled ground, and a cost efficiency of **€70.5 per m² cooled**. This is the system's measured proof point: real geometry, real species screening, and a real UTCI A/B simulation on the same site.

A note on the curated showcase. Because this live run predates the introduction of the London-plane phase-down, its 20-tree layout still contains 8 *Platanus* × *acerifolia* trees. Every output of the *current* pipeline — the evaluate endpoint's bundle and the €1,000,000 plan — contains zero London-plane and zero invasive species, confirming the gate is effective; refreshing the curated live showcase to the new palette requires one further live simulation and is deferred to respect the simulation budget.

### 6.2 City-wide €1,000,000 portfolio

The multi-site allocator committed the full **€1,000,000** across **7 geographically separated sites**, funding **100 trees** in total. The portfolio adds **5,451 m² of mature canopy** and serves approximately **24,612 residents** within the unioned 300 m catchments (de-duplicated). The species mix across the portfolio is *Tipuana tipu* (40), *Celtis australis* (34) and *Styphnolobium japonicum* (26) — zero London-plane, zero invasive.

We state the portfolio's epistemic status precisely. Its **placement is real** (building-, street- and furniture-aware geometry on every site), its **population served is real** (municipal register and neighbourhood geometry), and its **site prioritisation is real** (the satellite vulnerability composite). Its **per-site cooling is a labelled synthetic preview**: the portfolio was assembled on the mock backend, so funding order fell back to `composite_score_B` rather than measured cost-per-m²-cooled, and the per-site cooling figures are estimates, not UTCI measurements. Producing a fully measured portfolio would require roughly seven additional live simulations and was deliberately not run.

### 6.3 Reproducibility and security posture

The NSGA-II path is deterministic under its fixed seed, pinning the Pareto front across runs. GeoJSON input is parsed only via a JSON parser, never evaluated as code; live simulations are capped at three per run; and the Infrared API key is never logged or returned.

---

## 7. Validation Against Urban-Design Knowledge Bases

Because CoolSpend makes recommendations in a domain with deep professional standards, we validated its placement and metric choices against sixteen structured urban-design knowledge bases spanning street design, climate-responsive design, public-space design, zoning, density, transit-oriented design, mobility, mixed-use programming, site analysis, precedent study, cost estimation, sustainability scoring, design evaluation, urban regeneration, and a quantitative urban calculator.

The exercise was deliberately adversarial: the question was not "does the tool look good" but "which standard changes a parameter, and which merely confirms one." The outcome separates cleanly into three groups.

**Standards that changed the product.** Street-design standards (NACTO) fixed the 8 m spacing, the 1.5 m × 1.5 m tree-well footprint, and the trunk-clearance and bike-lane-clearance rules that became the façade and street-buffer exclusions. Climate-responsive design supplied the Mediterranean 20–30% canopy target and the 0.075 °C-per-1%-canopy coefficient now in the design metrics. The quantitative urban-calculator framing produced the entire metrics layer — canopy area, cover, person-degrees, canopy-per-euro. Sustainability scoring produced the ecosystem-health composite and the plantability gate that excludes the invasive and phase-down species. Urban regeneration contributed the de-sealing/de-paving logic and the in-ground-versus-planter trade-off. Precedent study anchored the de-paving rules in Barcelona's *superilla* programme. Public-space design produced the "do not saturate the plaza" principle that became the per-site budget cap and the 8 m spacing — the direct answer to the over-crowding failure mode.

**Standards that validated without changing code.** Urban-design foundations (human scale, enclosure) confirmed plaza siting; site analysis confirmed the heat × sealed × vegetation signal as the correct prioritisation surface; design evaluation confirmed the multi-configuration KPI-ranking approach; cost estimation confirmed the per-tree cost model.

**Standards that did not fit.** Block-and-density, transit-oriented design, and mixed-use programming operate at the master-planning scale and have nothing to place in a street-tree problem; mobility-and-transport contributed only the bike-lane clearance already covered by street design.

The most useful result of the exercise was *convergence*: three independent standards (NACTO 6–9 m, climate-responsive 8–10 m, de-paving 6–10 m) arrive at the same 8 m spacing. That a parameter is over-determined by three bodies of practice is stronger evidence than any single citation. The exercise did **not** invent new placement logic — placement was already geometry-aware — but it confirmed the rules and contributed the quantitative metric layer that makes a plan legible to a non-specialist.

---

## 8. Discussion

CoolSpend's central design claim is that a decision-support tool for public spending earns trust through *fidelity and auditability*, not through algorithmic novelty. Each layer is independently inspectable. A reviewer can verify that no tree sits on a roof by checking the building exclusion; that no recommended species is invasive by reading the plantability gate; that the budget is fully committed by summing the per-site costs; that the cooling is measured by reading the backend tag on the result. The (1 − 1/e) guarantee matters less for the absolute optimality it promises than for the fact that the placement is a principled coverage maximisation rather than an opaque heuristic.

The three-tier backend is the architectural expression of the same value. Hackathon and prototype tools routinely blur the line between a number that was computed and a number that was wished for; CoolSpend forces the distinction into the type system. The mock backend is not a placeholder to be apologised for — it is the mechanism that lets the *geometry-real, cooling-synthetic* preview run anywhere in the city without spending a paid simulation, while a single environment variable promotes any site to a measured live evaluation. The €1,000,000 portfolio is the clearest illustration: it is genuinely useful as a prioritised, costed, population-aware allocation even though its per-site cooling is a preview, *because the parts that are real are labelled real and the part that is synthetic is labelled synthetic*.

The population-served metric deserves emphasis as a bridge between thermal physics and public value. A plan that cools an empty lot and a plan that cools a dense residential block can have identical UTCI profiles; person-degrees and population-served distinguish them, and they tie the tool directly to the access norm (300 m) that municipalities increasingly adopt. This reframes the optimisation target from "cool the most ground" toward "relieve the most people," which is the question a public-health-minded planner actually asks.

---

## 9. Limitations

We enumerate the limitations frankly, because a tool that informs spending should be judged on what it does not yet know as much as on what it does.

1. **Satellite-composite provenance** *(substantially remediated; see `coolspend/provenance.py` and `docs/scored_grid_datasheet.md`).* The original concern was that `composite_score_B` could not be reproduced from this codebase. On inspection that was too pessimistic: each cell stores its five sub-scores, and a least-squares fit over all 494 cells recovers a single constant weight vector — `0.45·sealed + 0.20·LST-anomaly + 0.15·(1−NDVI) + 0.05·mismatch + 0.15·prpi` — that reconstructs the published composite to floating-point epsilon (R² = 1.0, maximum absolute residual ≈ 2 × 10⁻¹⁶). The *composite formula* is therefore exactly reproducible in-repo, verified by a regression test. The genuine residual gap is narrower: the derivation of three sub-scores from *raw imagery* — the Sentinel-1 SAR-to-sealed classifier and its training data, the Landsat LST-anomaly baseline, and the `mismatch`/`prpi` index definitions — lives in an upstream ingestion pipeline and remains undocumented here. Closing that requires the ingestion source, not a re-run of CoolSpend.

2. **Coverage proxy versus measured cooling.** The greedy objective weights demand by the *baseline* UTCI field; because a planted tree changes the field, the marginal "gain" is a coverage proxy, not measured marginal cooling. The system mitigates this by validating the final layout with a true UTCI simulation, but the *placement order* is proxy-driven.

3. **Synthetic cooling on non-live backends.** The mock and cached backends do not measure cooling. The €1,000,000 portfolio reported here was assembled on mock, so its per-site cooling and its `composite_score_B` funding order are previews; a measured portfolio needs ~7 live simulations.

4. **Surrogate thermal relief in NSGA-II.** The evolutionary path optimises an analytical ΔTmrt surrogate with a stated ±4 °C uncertainty and an unsourced linear cap; it is a search heuristic, and only the post-hoc Infrared run is treated as measured.

5. **Unsurveyed sub-surface conditions.** Underground utilities and exact sidewalk widths are absent from open data. In-ground slots are flagged for a pre-dig utility survey rather than asserted clear, and the 6 m foundation setback is a conservative placeholder pending species-specific and code-specific verification.

6. **Cost calibration** *(remediated; see `coolspend/cost_model.py:hours_per_degc()`).* The single `REQUIRES_VERIFICATION` constant — the UTCI-hours-above-32 °C removed per °C of cooling — is now computed directly from the in-repo Barcelona TMYx EPW via the project's ladybug UTCI machinery, rather than hand-derived. The empirical value is ≈47 h/°C (band-mean over 0.5–2 °C interventions), markedly lower than the prior 200 h/°C (which had assumed a 600 h/yr heat-stress baseline, whereas the EPW yields 98 h/yr above 32 °C); the corrected value also brings the surrogate UTCI-hours path into closer agreement with the measured live ΔUTCI. The 200 figure is retained only as an offline fallback. The relationship is convex, so the constant is reported with its band; the live calibration study (`calibration.py`) remains the definitive arbiter.

7. **Canopy-cover denominator.** Canopy cover is computed against the sampled cell area, which can read low for a small intervention within a large cell; a plantable-strip denominator would give a truer figure.

8. **Single-city scope and static meteorology.** The data assembly, species palette and cost figures are Barcelona-specific, and the UTCI window is a fixed July peak-heat period; seasonal and inter-annual variation, and transfer to other climates, are out of scope here.

---

## 10. Conclusion

CoolSpend demonstrates that the planting decisions a city actually faces — where, which species, how to spend a fixed budget — can be answered by a system that is simultaneously geometry-real, ecology-real, population-real, budget-bounded, and honest about the boundary between measured and synthetic results. Placement is a principled budgeted coverage maximisation with a classical approximation guarantee, screened against an ecological-health gate that excludes invasive and over-represented species; cooling is evaluated on a recognised thermal-comfort index; and outcomes are reported in the practitioner's own terms, including a population-served metric tied to an internationally adopted access norm. A live single-site run cools 2,838 m² of ground by a mean of 1.86 °C at €70.5 per m² cooled, and a €1,000,000 portfolio funds 100 trees across 7 sites serving roughly 24,612 residents with no invasive or phase-down species. The system's most transferable idea is its honesty architecture: the discipline of never reporting a number it did not compute, and of labelling every preview as a preview. Future work is dictated by the limitations — closing the satellite-composite provenance, running the measured city-wide portfolio, replacing the thermal surrogate and the placement proxy with measured fields, and integrating a utility survey — each of which tightens the link between a recommendation and the public money it would direct.

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

This manuscript and the underlying system were developed with assistance from an AI coding and writing assistant (Anthropic Claude). AI assistance was used for software implementation, code and data fact-extraction, literature citation retrieval and verification, and manuscript drafting. All technical facts reported here were extracted from and verified against the project source code; all external citations were verified against publisher records via web search and carry DOIs. The author reviewed and is responsible for all content.

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
