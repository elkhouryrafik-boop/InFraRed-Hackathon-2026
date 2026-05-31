# Species Ecological-Traits Dataset — Barcelona Street Trees

Per-species ecological traits for CoolSpend's 12-species palette (Barcelona's most-planted
street trees, see `coolspend/bcn_species.py`). Each dimension is scored 0–1 (or a category)
with a one-line justification and a source. Values that could not be sourced to an
authoritative reference are tagged **REQUIRES_VERIFICATION** — no numbers or DOIs are fabricated.

**Scope & honesty note.** Scores are *species-typical, literature-anchored estimates for
ranking/selection* — not measured per-tree values. Where a precise figure exists (e.g. OPALS
allergy ratings) it is cited; where the literature gives only qualitative statements, the 0–1
score is the author's coded interpretation of that statement and is flagged accordingly.
Allergy and ground-truth cooling are the two dimensions with the firmest external anchors
(OPALS scale; live Infrared UTCI respectively). `canopy_density` is cross-checked against the
existing `bcn_species.py` `shade_density` field and any divergence is noted.

Compiled: 2026-05-31. Climate context: Barcelona hotter/drier RCP/SSP projections (more
frequent summer drought + heat).

---

## How to read the scores

| Dimension | Range / categories | Direction |
|---|---|---|
| native_status | native Iberia/Med \| naturalised \| exotic \| exotic-invasive | benefit if native |
| drought_heat_tolerance | 0–1 | **higher = better** under BCN climate change |
| biodiversity_value | 0–1 | higher = better (habitat/food, fauna associations) |
| pollinator_value | 0–1 | higher = better (nectar/pollen for bees/pollinators) |
| allergenicity | 0–1 (OPALS/10) | **higher = WORSE** pollen-allergy burden |
| pest_disease_risk | 0–1 | **higher = WORSE** (major pests/pathogens) |
| canopy_density / shade | dense \| medium \| light | denser = more shade-cooling |
| longevity | years (typical urban) | higher = better |
| growth_rate | slow \| medium \| fast | establishment vs. brittleness trade-off |
| water_demand | low \| medium \| high | **lower = better** under drought |
| maintenance_burden | low \| medium \| high | **lower = better** |
| carbon_sequestration | 0–1 | higher = better (size × longevity × growth proxy) |
| mycorrhizal_type | AM \| EM \| mixed \| none | informational |

`allergenicity` 0–1 is derived from the **OPALS** (Ogren Plant Allergy Scale, 1–10) as
`OPALS/10`. OPALS 1 = least allergenic, 10 = most. [Ogren Plant Allergy Scale — Wikipedia](https://en.wikipedia.org/wiki/Ogren_Plant_Allergy_Scale);
genus-level OPALS values from the i-Tree supplemental table [i-Tree Supplemental Tables (PDF)](https://www.itreetools.org/documents/1004/Supplemental_Tables.pdf).
Note OPALS is genus-level for most taxa and varies strongly with sex for dioecious/cultivar
clones; street cultivars are typically the worse (male/monoecious) form.

---

## Master table

| Species (common) | native_status | drought_heat | biodiversity | pollinator | allergenicity (OPALS) | pest_disease | canopy/shade | longevity (urban yr) | growth | water | maint. | carbon_seq | mycorrhiza |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Platanus × acerifolia** (London plane) | exotic (hybrid) | 0.75 | 0.35 | 0.15 | **0.85 (OPALS ~8.5)** | **0.85** | dense | 80–150 | fast | medium | high | 0.90 | AM |
| **Celtis australis** (European hackberry) | **native Med** | 0.85 | 0.60 | 0.35 | **0.80 (OPALS 8, genus)** | 0.30 | dense | 80–150 | medium | low | low | 0.80 | AM |
| **Styphnolobium japonicum** (Japanese pagoda) | exotic | 0.80 | 0.55 | **0.85** | 0.30 *(REQUIRES_VERIFICATION — no genus OPALS in table)* | 0.25 | medium | 50–100 | medium | low | medium | 0.55 | AM (N-fixing, Fabaceae) |
| **Tipuana tipu** (Tipa) | exotic | **0.90** | 0.45 | **0.80** | 0.30 *(REQUIRES_VERIFICATION)* | 0.30 | dense | 50–80 | fast | low | high | 0.75 | AM (N-fixing, Fabaceae) |
| **Melia azedarach** (Chinaberry) | exotic (naturalised/weedy) | **0.90** | 0.40 | 0.50 | 0.40 *(REQUIRES_VERIFICATION)* | 0.25 | medium | 30–50 | fast | low | **high** (fruit litter, brittle) | 0.45 | AM |
| **Brachychiton populneus** (Kurrajong) | exotic | **0.95** | 0.35 | 0.45 | 0.30 *(REQUIRES_VERIFICATION)* | 0.20 | medium | 60–100 | slow–medium | **low** | low | 0.55 | AM |
| **Ligustrum lucidum** (Glossy privet) | **exotic-invasive** | 0.80 | 0.45 (bird-dispersed fruit) | 0.45 | **0.80 (OPALS 8, genus)** | 0.25 | dense | 40–70 | fast | low | medium (fruit, weedy seedlings) | 0.45 | AM |
| **Jacaranda mimosifolia** (Jacaranda) | exotic (VU in wild) | 0.70 | 0.40 | **0.70** | **0.40 (OPALS 4, genus)** | 0.20 | medium | 50–100 | medium | medium | medium | 0.55 | AM |
| **Ulmus pumila** (Siberian elm) | **exotic-invasive** | **0.90** | 0.45 | 0.20 | **0.80 (OPALS 8, genus)** | 0.45 (DED-tolerant but elm leaf beetle, brittle) | medium | 50–80 | fast | low | **high** (brittle wood, weedy seed) | 0.60 | mixed (EM + AM reported) |
| **Cercis siliquastrum** (Judas tree) | **native Med** | 0.80 | 0.50 | **0.75** | 0.25 *(REQUIRES_VERIFICATION — low, insect-pollinated)* | 0.25 | medium | 40–80 | slow | low | low | 0.35 | AM (N-fixing, Fabaceae) |
| **Robinia pseudoacacia** (Black locust) | **exotic-invasive** | **0.90** | 0.40 | **0.90** | **0.50 (OPALS 5, genus)** | 0.30 | medium | 40–90 | fast | low | **high** (suckering, brittle, thorns) | 0.60 | mixed (N-fixing + EM/AM) |
| **Magnolia grandiflora** (Southern magnolia) | exotic | 0.55 | 0.30 | 0.45 | **0.50 (OPALS 5, species)** | 0.15 | dense | 80–120 | slow | medium–high | medium (large leaf litter) | 0.65 | AM |

---

## Per-species notes & justifications

### Platanus × acerifolia — London plane
- **native_status:** exotic hybrid (*P. orientalis* × *P. occidentalis*); not native, but the
  dominant BCN street species (~28% of inventory). [Health Status of Plane Trees in Spain, Arboriculture & Urban Forestry](https://auf.isa-arbor.com/content/26/5/246)
- **drought_heat 0.75:** very tolerant of heat/pollution once established; deep-rooting. Some
  summer water stress in hottest BCN years. (urban-forestry consensus)
- **biodiversity 0.35 / pollinator 0.15:** wind-pollinated, low nectar; limited fauna value.
- **allergenicity 0.85:** Platanus is a leading spring-pollen allergen in Mediterranean cities;
  Ogren rates plane high (~OPALS 8–9). *Genus not in i-Tree subset table → value from Ogren's
  published rating; treat the exact decimal as **REQUIRES_VERIFICATION**, the "high" class is firm.*
  Also irritant leaf-hair trichomes. [Ogren Plant Allergy Scale](https://en.wikipedia.org/wiki/Ogren_Plant_Allergy_Scale)
- **pest_disease 0.85 (worst):** sycamore lace bug *Corythucha ciliata* widespread; **canker
  stain** *Ceratocystis platani* is the most destructive Platanus disease and lethal — the key
  reason cities are diversifying away from monoculture. [Ceratocystis platani inoculations, iForest 9:608](https://iforest.sisef.org/contents/?id=ifor1594-008); [C. ciliata feeding response, PMC6678411](https://pmc.ncbi.nlm.nih.gov/articles/PMC6678411/)
- **canopy:** dense — matches `bcn_species.py`.
- **carbon_seq 0.90:** large crown + long life = top sequestration of palette.
- **mycorrhiza:** AM (Platanaceae). REQUIRES_VERIFICATION at species precision.

### Celtis australis — European hackberry
- **native_status:** native to the Mediterranean basin incl. Iberia. (Euforgen/GBIF distribution)
- **drought_heat 0.85:** Mediterranean-native, strongly drought/heat adapted; a leading
  climate-resilient recommendation for BCN.
- **biodiversity 0.60:** fleshy drupes eaten by birds; native-range fauna associations.
- **pollinator 0.35:** wind-pollinated, modest insect interest.
- **allergenicity 0.80:** genus OPALS **8** in i-Tree table ("Celtis spp. hackberry 8"). [i-Tree Supplemental Tables](https://www.itreetools.org/documents/1004/Supplemental_Tables.pdf)
- **pest_disease 0.30:** comparatively few serious pests in BCN.
- **canopy:** dense — matches `bcn_species.py`. Long-lived, low water/maintenance.
- **mycorrhiza:** AM (Cannabaceae). REQUIRES_VERIFICATION at species precision.

### Styphnolobium japonicum — Japanese pagoda tree (syn. *Sophora japonica*)
- **native_status:** exotic (East Asia); long-cultivated, non-invasive.
- **drought_heat 0.80:** tolerates urban pollution + heat and some drought once established. [NC Extension — Styphnolobium japonicum](https://plants.ces.ncsu.edu/plants/styphnolobium-japonicum-pendula/)
- **pollinator 0.85:** heavy late-summer creamy-white flowering, strong bee forage (Fabaceae) —
  one of the best nectar trees in the palette.
- **allergenicity 0.30 (REQUIRES_VERIFICATION):** insect-pollinated legume → expected low; genus
  not present in i-Tree subset table, so the exact value is unverified.
- **growth medium, longevity 50–100, water/maint low–medium.**
- **mycorrhiza:** AM; Fabaceae N-fixing (Bradyrhizobium-type) — soil-fertility benefit.

### Tipuana tipu — Tipa
- **native_status:** exotic (South America).
- **drought_heat 0.90:** photosynthesis *accelerates* at high temperature and under drought;
  among the most heat-resilient BCN street trees. [Tipuana tipu irrigation tree-ring study, ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1618866726000816) / [USFS treesearch 80299](https://research.fs.usda.gov/treesearch/80299)
- **pollinator 0.80:** profuse yellow-orange flowering, strong bee attraction (Fabaceae).
- **maintenance high:** vigorous surface roots lift pavements; sticky honeydew/litter. (BCN
  arboriculture experience — REQUIRES_VERIFICATION for a single citation)
- **canopy:** dense — matches `bcn_species.py`. **carbon_seq 0.75** (large, fast, moderate life).
- **mycorrhiza:** AM; Fabaceae N-fixing.

### Melia azedarach — Chinaberry
- **native_status:** exotic; **naturalised/weedy** in warm regions, listed invasive in parts of
  the Americas/Australia (watch-list, not yet a Catalonia priority invader — REQUIRES_VERIFICATION
  for Catalan status). [Melia adaptability to drought & urban pollution, jardineriaon](https://en.jardineriaon.com/drought-resistant-trees.html)
- **drought_heat 0.90:** highly drought- and pollution-tolerant.
- **maintenance high:** abundant drupe litter (fruit toxic to humans/some animals), brittle wood,
  short life (30–50 yr) → frequent replacement.
- **pollinator 0.50:** fragrant lilac flowers visited by bees, moderate.
- **allergenicity 0.40 (REQUIRES_VERIFICATION):** insect-pollinated; not in OPALS subset table.
- **mycorrhiza:** AM (Meliaceae). REQUIRES_VERIFICATION.

### Brachychiton populneus — Kurrajong / Bottle tree
- **native_status:** exotic (Australia).
- **drought_heat 0.95 (best):** swollen water-storing trunk; "highly suited to dry climates,
  minimal maintenance." [Brachychiton populneus, Evergreen Trees Direct](https://www.evergreentrees.com.au/products/brachychiton-populneus-bottle-tree)
- **water low / maintenance low:** standout low-input species for a drying Barcelona.
- **canopy:** medium (semi-evergreen) — matches `bcn_species.py`.
- **biodiversity 0.35 / pollinator 0.45:** bell flowers visited by insects/birds in native range;
  limited local fauna ties.
- **allergenicity 0.30 (REQUIRES_VERIFICATION):** not in OPALS table; insect-pollinated, low expected.
- **growth slow–medium, longevity 60–100. mycorrhiza:** AM (Malvaceae). REQUIRES_VERIFICATION.

### Ligustrum lucidum — Glossy privet
- **native_status:** **exotic-invasive** — "a dangerous invasive species of subtropical and
  temperate forests worldwide," bird-dispersed, forms monospecific stands. Flag for Catalonia
  watch-list. [Ligustrum lucidum invasion, PMC11946171](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11946171/)
- **drought_heat 0.80; canopy dense (matches `bcn_species.py`); evergreen → year-round shade.**
- **allergenicity 0.80:** genus OPALS **8** ("Ligustrum spp. privet 8"); privet is a notable
  allergen and the heavily scented flowers irritate sensitive people. [i-Tree Supplemental Tables](https://www.itreetools.org/documents/1004/Supplemental_Tables.pdf)
- **biodiversity 0.45:** fruit feeds (and is spread by) birds — a double-edged "value" that
  drives invasion. **maintenance medium** (fruit litter, volunteer seedlings).
- **mycorrhiza:** AM (Oleaceae). REQUIRES_VERIFICATION.

### Jacaranda mimosifolia — Jacaranda
- **native_status:** exotic (South America); IUCN Vulnerable in native range, non-invasive in BCN.
- **drought_heat 0.70:** heat-tolerant, frost-sensitive; moderate drought tolerance. [Jacaranda heat tolerance, jardineriaon](https://en.jardineriaon.com/fast-growing-trees.html)
- **pollinator 0.70:** spectacular violet flowering attracts bees and butterflies.
- **allergenicity 0.40:** genus OPALS **4** ("Jacaranda spp. jacaranda 4") — one of the
  lower-allergen palette members. [i-Tree Supplemental Tables](https://www.itreetools.org/documents/1004/Supplemental_Tables.pdf)
- **canopy:** medium (matches `bcn_species.py`). **growth medium, longevity 50–100.**
- **mycorrhiza:** AM (Bignoniaceae). REQUIRES_VERIFICATION.

### Ulmus pumila — Siberian elm
- **native_status:** **exotic-invasive** — prolific wind-dispersed seed, naturalises on marginal
  land; listed invasive (e.g. Minnesota DNR) and "generally no longer recommended." [Ulmus pumila, Minnesota DNR](https://www.dnr.state.mn.us/invasives/terrestrialplants/woody/siberianelm.html); [Siberian elm fact sheet, invasive.org](https://www.invasive.org/weedcd/pdfs/wgw/siberianelm.pdf)
- **pest_disease 0.45:** **DED-tolerant** (resistant, not immune) — original reason for planting —
  but brittle branches + elm leaf beetle susceptibility raise the score. [DED resistance & xylem endophytes, PMC3585289](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3585289/)
- **drought_heat 0.90:** very hardy across drought/heat/cold. **water low, growth fast.**
- **allergenicity 0.80:** genus OPALS **8** ("Ulmus spp. elm 8"); wind-pollinated, early-spring
  allergen. [i-Tree Supplemental Tables](https://www.itreetools.org/documents/1004/Supplemental_Tables.pdf)
- **maintenance high:** brittle wood (storm breakage) + weedy seedlings.
- **canopy:** medium (matches `bcn_species.py`).
- **mycorrhiza:** mixed — *Ulmus* commonly reported as AM with EM associations noted. REQUIRES_VERIFICATION.

### Cercis siliquastrum — Judas tree
- **native_status:** **native** to the eastern/central Mediterranean (incl. parts of Iberia as
  Mediterranean-native ornamental). [Cercis siliquastrum, PFAF](https://pfaf.org/user/plant.aspx?LatinName=Cercis+siliquastrum)
- **drought_heat 0.80:** tolerates dry soils and drought; small-statured, good under wires.
- **pollinator 0.75:** bee-pollinated, attracts wildlife; flowers are even cauliflorous on trunk.
- **allergenicity 0.25 (REQUIRES_VERIFICATION):** insect-pollinated legume; not in OPALS subset →
  expected low, exact value unverified.
- **canopy medium (matches `bcn_species.py`); growth slow; longevity 40–80; carbon_seq 0.35**
  (smallest tree in palette).
- **mycorrhiza:** AM; Fabaceae N-fixing.

### Robinia pseudoacacia — Black locust
- **native_status:** **exotic-invasive in Europe/Catalonia** — among the 40 most invasive woody
  angiosperms globally, naturalised in NE-Iberian (Catalan) Mediterranean riparian zones; alters
  soil N. [Influence of invasive N-fixing Robinia on soil N in NE Spain, Eur J Forest Res](https://link.springer.com/article/10.1007/s10342-019-01226-x); [Black locust beloved & despised, PMC6143167](https://pmc.ncbi.nlm.nih.gov/articles/PMC6143167/)
- **pollinator 0.90 (best):** very high nectar yield, major honey/bee resource.
- **drought_heat 0.90:** drought-hardy, fast colonizer.
- **allergenicity 0.50:** genus OPALS **5** ("Robinia spp. black locust 5"); insect-pollinated so
  moderate. [i-Tree Supplemental Tables](https://www.itreetools.org/documents/1004/Supplemental_Tables.pdf)
- **maintenance high:** aggressive root suckering, brittle wood, thorns.
- **mycorrhiza:** mixed (N-fixing *Rhizobium* + reported EM/AM).
- **Conflict flag:** high pollinator value vs. invasive status — a textbook benefit/penalty
  tension for the composite.

### Magnolia grandiflora — Southern magnolia
- **native_status:** exotic (SE USA); non-invasive ornamental.
- **drought_heat 0.55 (lowest):** evergreen, prefers moist soil; least drought-adapted of the
  palette → poorer fit for a drying Barcelona without irrigation.
- **water medium–high; growth slow; longevity 80–120.**
- **allergenicity 0.50:** species OPALS **5** ("Magnolia grandiflora Southern magnolia 5"). [i-Tree Supplemental Tables](https://www.itreetools.org/documents/1004/Supplemental_Tables.pdf)
- **biodiversity 0.30 / pollinator 0.45:** large beetle-pollinated flowers; limited local fauna ties.
- **canopy:** dense, evergreen (matches `bcn_species.py`); large leathery leaf litter → medium maintenance.
- **mycorrhiza:** AM (Magnoliaceae). REQUIRES_VERIFICATION.

---

## Cross-check vs. `bcn_species.py` canopy/shade

All 12 `canopy_density` values in this table **agree** with the `shade_density` field in
`coolspend/bcn_species.py` (dense: Platanus, Celtis, Tipuana, Ligustrum, Magnolia; medium:
Styphnolobium, Melia, Brachychiton, Jacaranda, Ulmus, Cercis, Robinia). No divergence to flag.

---

## Scoring rationale — toward an ecosystem-health composite

The 13 dimensions split into **benefits** (raise ecosystem-health score) and **penalties**
(lower it). A defensible composite normalises each to 0–1 (penalties inverted), weights them by
project priority, and aggregates. Per OECD/JRC composite-indicator practice, weighting must be
explicit and sensitivity-tested — do not treat any single weighting as ground truth.

**Benefit dimensions (higher = healthier):**
- `drought_heat_tolerance` — climate-change fitness (high weight for BCN).
- `biodiversity_value`, `pollinator_value` — ecological function.
- `canopy_density`/shade and `carbon_sequestration` — regulating services (note: also captured by
  the live Infrared UTCI cooling, so avoid double-counting cooling in both the ecology composite
  and the thermal objective).
- `longevity` — amortises planting cost and carbon over time.
- native_status: native > naturalised > exotic > exotic-invasive (ordinal benefit).

**Penalty dimensions (higher = subtract):**
- `allergenicity` — public-health disservice (OPALS-anchored; the firmest external number here).
- `pest_disease_risk` — failure/replacement risk (Platanus monoculture is the cautionary tale).
- `water_demand` — operating cost + drought-failure risk; penalise heavily under SSP-hot BCN.
- `maintenance_burden` — litter, brittle wood, root/pavement damage, suckering.
- **exotic-invasive status — hard penalty / veto.** Invasive spread is an ecological *disservice*;
  recommend a cap or exclusion rather than letting high pollinator/cooling scores "buy back" an
  invader (Ligustrum lucidum, Ulmus pumila, Robinia in Catalonia).

**Suggested composite shape (illustrative, weights to be sensitivity-tested):**
```
eco_health = w1·drought_heat + w2·biodiversity + w3·pollinator + w4·longevity_norm
           + w5·native_score
           − p1·allergenicity − p2·pest_disease − p3·water_demand_norm − p4·maintenance_norm
           − INVASIVE_PENALTY   (large, or a hard exclusion flag)
```
Keep `carbon`/`canopy` *out* of `eco_health` if the same cooling/sequestration benefit is already
scored by the Infrared UTCI objective, to prevent double counting. Report eco_health *alongside*
the €/m²-cooled KPI rather than blending them, so reviewers see the health–cost trade-off explicitly.

---

## Sources

- [Ogren Plant Allergy Scale — Wikipedia](https://en.wikipedia.org/wiki/Ogren_Plant_Allergy_Scale)
- [i-Tree Supplemental Tables (OPALS genus/species values) — PDF](https://www.itreetools.org/documents/1004/Supplemental_Tables.pdf)
- [Health Status of Plane Trees (Platanus spp.) in Spain — Arboriculture & Urban Forestry](https://auf.isa-arbor.com/content/26/5/246)
- [Ceratocystis platani inoculations in Platanus × acerifolia — iForest 9:608 (2016)](https://iforest.sisef.org/contents/?id=ifor1594-008)
- [Platanus acerifolia response to Corythucha ciliata — PMC6678411](https://pmc.ncbi.nlm.nih.gov/articles/PMC6678411/)
- [Corythucha ciliata — Wikipedia](https://en.wikipedia.org/wiki/Corythucha_ciliata)
- [Invasive N-fixing Robinia pseudoacacia and soil N in NE Spain — Eur. J. Forest Res.](https://link.springer.com/article/10.1007/s10342-019-01226-x)
- [Black locust beloved and despised (invasive in Central Europe) — PMC6143167](https://pmc.ncbi.nlm.nih.gov/articles/PMC6143167/)
- [Ligustrum lucidum invasion process — PMC11946171](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11946171/)
- [Tipuana tipu drought/irrigation tree-ring study — ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1618866726000816) · [USFS treesearch 80299](https://research.fs.usda.gov/treesearch/80299)
- [Ulmus pumila (Siberian elm) — Minnesota DNR invasive profile](https://www.dnr.state.mn.us/invasives/terrestrialplants/woody/siberianelm.html)
- [Siberian elm fact sheet — invasive.org PDF](https://www.invasive.org/weedcd/pdfs/wgw/siberianelm.pdf)
- [DED resistance & xylem endophytic fungi in Ulmus — PMC3585289](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3585289/)
- [Cercis siliquastrum — Plants For A Future (PFAF)](https://pfaf.org/user/plant.aspx?LatinName=Cercis+siliquastrum)
- [Styphnolobium japonicum — NC State Extension Plant Toolbox](https://plants.ces.ncsu.edu/plants/styphnolobium-japonicum-pendula/)
- [Brachychiton populneus (Bottle Tree) — Evergreen Trees Direct](https://www.evergreentrees.com.au/products/brachychiton-populneus-bottle-tree)
- [Floral nectar & amino acid yield in landscape trees for pollinators — PMC12252262](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12252262/)
- [Drought-resistant trees for gardens and cities (Melia, Jacaranda) — jardineriaon](https://en.jardineriaon.com/drought-resistant-trees.html)

### Verification backlog (do not present as fact until sourced)
- OPALS decimals for **Platanus** (class "high ~8–9" firm; exact value), **Styphnolobium / Sophora**,
  **Tipuana**, **Melia**, **Brachychiton**, **Cercis** — not in the i-Tree subset table; need
  Ogren's full *Allergy-Free Gardening* / *Plant-Allergy* database.
- **Mycorrhizal type** at species precision for all taxa (genus/family-level inference only here).
- **Melia azedarach invasive status specifically in Catalonia** (weedy/naturalised elsewhere; Catalan
  legal/observed status unconfirmed).
- Per-species **urban longevity** figures (ranges are arboricultural consensus, not single-source).
- `carbon_sequestration` 0–1 is a size×longevity×growth proxy by the author, not a measured biomass figure.
