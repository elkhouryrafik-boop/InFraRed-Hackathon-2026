# Barcelona Official Urban Tree Planting Strategy — Research Brief

**Purpose:** Provenance-checked inputs for the CoolSpend ecological scoring model (species selection / diversity penalties / invasive exclusions).
**Compiled:** 2026-05-31
**Provenance policy:** Each claim carries a source URL + year. Figures I could not confirm in an accessible primary source are tagged `REQUIRES_VERIFICATION`. The Ajuntament de Barcelona PDF servers (`ajuntament.barcelona.cat`, `w110.bcn.cat`, `barcelona.cat`) returned HTTP 418 to automated fetches, so several primary-document figures below are sourced via search-engine extraction of those same PDFs and via reputable Catalan press that quote the plan directly. Where two independent figures conflict, both are shown.

---

## Primary / official sources referenced

| Tag | Document | Body | Year | URL |
|-----|----------|------|------|-----|
| [PDA] | *Arbres per viure — Pla Director de l'Arbrat de Barcelona 2017–2037* | Ajuntament de Barcelona | 2017 (rev. 2024) | https://ajuntament.barcelona.cat/espaisverds/sites/default/files/2024-10/Pla-director-arbrat-barcelona-CA_0.pdf |
| [PDA-CAST] | Same plan, Castilian edition | Ajuntament de Barcelona | 2017 | https://ajuntament.barcelona.cat/ecologiaurbana/sites/default/files/Pla-director-arbrat-barcelona-CAST.pdf |
| [GAV] | *Pla de Gestió de l'Arbrat Viari de Barcelona* (street-tree management) | Ajuntament de Barcelona | n.d. | https://ajuntament.barcelona.cat/ecologiaurbana/sites/default/files/Plagestioarbratviaribcn_cat.pdf · repository copy https://bcnroc.ajuntament.barcelona.cat/jspui/bitstream/11703/86306/1/3264.pdf |
| [SEL] | *Arbrat Viari: Selecció d'Espècies* | Parcs i Jardins de Barcelona | n.d. | https://w110.bcn.cat/MediAmbient/Continguts/Continguts_Contextuals/Documentacio/Documents/Fitxers/arbrat_viari.pdf |
| [PVB] | *Pla del Verd i de la Biodiversitat de Barcelona 2020 — Resum* | Ajuntament de Barcelona | 2013 | https://ajuntament.barcelona.cat/ecologiaurbana/sites/default/files/Pla%20del%20verd%20i%20de%20la%20biodiversitat%20de%20Barcelona%202020.%20Resum.pdf |
| [PN] | *Pla Natura Barcelona 2021–2030* | Ajuntament de Barcelona | 2021 | https://www.barcelona.cat/barcelonasostenible/sites/default/files/2023-12/Pla%20Natura%20Barcelona%202030.pdf |
| [INV] | *Estudi d'espècies invasores a la ciutat de Barcelona i proposta 2012–2020* | Ajuntament de Barcelona | 2012 | https://ajuntament.barcelona.cat/espaisverds/sites/default/files/2024-09/EstudiEspeciesInvasores.pdf |
| [DIBA-INV] | *Plantes exòtiques invasores — Guia d'identificació i substitució en jardineria* | Diputació de Barcelona | 2021 | https://parcs.diba.cat/documents/43788175/50929993/PlantesExotiquesInvasores.pdf |
| [DIBA-PRES] | Presentation of the Pla Director de l'Arbrat (Diputació network) | Diputació de Barcelona / Xarxa | 2018 | https://xarxaenxarxa.diba.cat/sites/xarxaenxarxa.diba.cat/files/badalona_presentacio_pla_director_darbrat_7-3-18.pdf |
| [CREAF] | *Quins arbres hem de plantar a les ciutats?* | CREAF (research centre) | n.d. | https://www.creaf.cat/en/node/70218 |

Secondary press quoting the plans (used only to triangulate primary figures): beteve.cat, elnacional.cat, totbarcelona.cat, catalunyapress.cat, ara.cat, diarieljardi.cat (URLs inline below).

---

## 1. Species & genus DIVERSIFICATION rules

**VERIFIED — "no single species > 15% of the tree population."**
The plan's governing diversity criterion is that **no single species may exceed 15%** of the total tree heritage. This is the explicit, repeatedly stated rule.
- "no single species should exceed 15% of the total urban tree heritage" — [PDA] via search extraction; corroborated by beteve: *"que cap [espècie] suposi més del 15% de la població d'arbres"* over a ~50-year horizon ([beteve, 2017](https://beteve.cat/societat/en-20-anys-el-30-de-superficie-estara-coberta-per-arbres/)) and elnacional: *"cap espècie superi el 15% del total"* ([elnacional, 2017](https://www.elnacional.cat/ca/barcelona/barcelona-reduira-mes-meitat-plataners-fer-arbrat-mes-divers-representen-30-total_1634608_102.html)).

**Rationale (VERIFIED):** to reduce vulnerability to a single pest/disease wiping out a large share of the canopy (the monoculture-fragility argument), and to increase the fauna diversity associated with a wider palette of species ([PDA] via [diarieljardi](https://diarieljardi.cat/tipus-i-beneficis-arbrat-viari-a-barcelona/); [elnacional, 2017](https://www.elnacional.cat/ca/barcelona/barcelona-reduira-mes-meitat-plataners-fer-arbrat-mes-divers-representen-30-total_1634608_102.html)).

**Per-GENUS and per-FAMILY thresholds — `REQUIRES_VERIFICATION`.**
A specific "no single *genus* > X%" / "no single *family* > Y%" numeric target (the classic Santamour 10-20-30 rule used by many municipal arboriculture plans) was **NOT confirmed** in any source I could access. Barcelona's accessible material states only the 15%-per-species figure. Do **not** hardcode a genus/family cap as Barcelona-official without checking pp. on diversity in [PDA] / [GAV] directly.
- Modelling guidance: if the scoring model needs a genus penalty, use 15% as the only Barcelona-attested cap and treat any genus/family cap as a generic best-practice assumption, not a cited Barcelona target.

**Context — current diversity baseline (VERIFIED):** Barcelona's street-tree stock spans **>150,000 trees across 40+ species** ([diarieljardi](https://diarieljardi.cat/tipus-i-beneficis-arbrat-viari-a-barcelona/), [GAV]). Historically the plane tree was a near-monoculture: **~90% of the tree population in the 1990s** ([beteve, 2017](https://beteve.cat/societat/en-20-anys-el-30-de-superficie-estara-coberta-per-arbres/)).

---

## 2. The PLATANUS problem

**Current share (VERIFIED, two figures — both reported):**
- **~30% of the total tree population** is the headline figure used by the city and press ([elnacional, 2017](https://www.elnacional.cat/ca/barcelona/barcelona-reduira-mes-meitat-plataners-fer-arbrat-mes-divers-representen-30-total_1634608_102.html); [beteve, 2017](https://beteve.cat/societat/en-20-anys-el-30-de-superficie-estara-coberta-per-arbres/)).
- A more precise figure of **27.45%** appears in the plan/press ([catalunyapress, 2026](https://www.catalunyapress.cat/article/barcelona/2026-05-04/5867931-barcelona-declara-guerra-plataner-larbre-icnic-podria-desaparixer-dels-seus-carrers)).
- Absolute count: **43,722 plane trees**, of which the plan removes/replaces **~56%** over the plan horizon ([catalunyapress, 2026](https://www.catalunyapress.cat/article/barcelona/2026-05-04/5867931-barcelona-declara-guerra-plataner-larbre-icnic-podria-desaparixer-dels-seus-carrers)).
- Note a unit caveat: some sources express ~30% as share of the *whole* tree heritage; one general "urban green population" tally put *Platanus* at 18,744 specimens / 8.8% — that is a different (larger) denominator. For street trees specifically use the **~30% (street-tree)** figure. `REQUIRES_VERIFICATION` on exactly which denominator your model needs.

**Target (VERIFIED):** reduce the plane tree to **~12% by 2037** ([catalunyapress, 2026](https://www.catalunyapress.cat/article/barcelona/2026-05-04/5867931-barcelona-declara-guerra-plataner-larbre-icnic-podria-desaparixer-dels-seus-carrers)); often summarised as "to 15%" to align with the species cap ([beteve, 2017](https://beteve.cat/societat/en-20-anys-el-30-de-superficie-estara-coberta-per-arbres/)). Plane trees are **not replaced like-for-like since 1998** — when one dies it is swapped for another species ([diarieljardi](https://diarieljardi.cat/tipus-i-beneficis-arbrat-viari-a-barcelona/): *"des de l'any 1998, aquesta espècie no se substitueix"*).

**WHY they are reducing it (VERIFIED reasons):**
1. **Monoculture / pest-disease fragility** — over-dependence on one species raises catastrophic-loss risk ([elnacional, 2017](https://www.elnacional.cat/ca/barcelona/barcelona-reduira-mes-meitat-plataners-fer-arbrat-mes-divers-representen-30-total_1634608_102.html)).
2. **Allergenicity / pollen + seed nuisance** — mass seed/fibre fall and pollen cause documented complaints, especially for allergy sufferers ([catalunyapress, 2026](https://www.catalunyapress.cat/article/barcelona/2026-05-04/5867931-barcelona-declara-guerra-plataner-larbre-icnic-podria-desaparixer-dels-seus-carrers); [totbarcelona](https://www.totbarcelona.cat/societat/fi-regnat-plataner-barcelona-aposta-reduir-presencia-568783/)).
3. **Corythucha ciliata (tigre del plataner / plane lace bug)** — invasive US-origin pest, overwinters under bark; recurrent outbreaks in Eixample, Gràcia, Sant Andreu, Sant Martí; reduces vigour/photosynthesis and invades homes/cafés ([beteve, tiger bug](https://beteve.cat/societat/insectes-la-plaga-del-tigre-del-platan-sesten-a-altres-barris/); [desinsectador, 2015](https://desinsectador.com/2015/07/15/tigre-del-platano-de-sombra-corythucha-ciliata-heteroptera-tingidae-en-barcelona/)). *This pest's severity on the dominant species is a core driver of diversification, though press articles do not always explicitly link it to the 2037 reduction target.*
4. **Ceratocystis platani (xancre acolorit / canker stain)** — lethal vascular fungus of *Platanus*, a recognised threat in Catalonia; spreads via wounds/pruning tools ([Consorci Forestal de Catalunya fitxa, 2020 (ResearchGate)](https://www.researchgate.net/publication/341193195); [Girona/Devesa protocol PDF](https://web.girona.cat/documents/20147/280355/Devesa_Ceratocystis_Protocol2.pdf)). Confirms why a *Platanus* monoculture is dangerous; `REQUIRES_VERIFICATION` whether [PDA] names it explicitly.
5. **High water / maintenance demand** — broadly cited climate-resilience rationale; specific water-use figures `REQUIRES_VERIFICATION` against [PDA].

---

## 3. Species Barcelona is ACTIVELY SHIFTING TOWARD (climate resilience)

There **is** a preferred / recommended-species approach. The dedicated primary document is **[SEL] *Arbrat Viari: Selecció d'Espècies* (Parcs i Jardins)** and the selection criteria in **[GAV]**. The selection prioritises species **adapted to the Mediterranean climate and resilient to drought/heat under climate change**, favouring subtropical and some northern-European taxa over slow-growing natives that give poor street shade ([PVB]; [totbarcelona](https://www.totbarcelona.cat/societat/fi-regnat-plataner-barcelona-aposta-reduir-presencia-568783/)).

**Favoured taxa already prominent / being expanded (VERIFIED, names attested):**
| Species | Common | Note / source |
|---------|--------|---------------|
| *Celtis australis* | Lledoner / hackberry | 2nd most common street tree, ~12%; low water need; explicitly recommended ([diarieljardi](https://diarieljardi.cat/tipus-i-beneficis-arbrat-viari-a-barcelona/); [CREAF](https://www.creaf.cat/en/node/70218)) |
| *Styphnolobium japonicum* (syn. *Sophora japonica*) | Sòfora | ~6% ([diarieljardi](https://diarieljardi.cat/tipus-i-beneficis-arbrat-viari-a-barcelona/)) |
| *Tipuana tipu* | Tipuana | ~4%; "adapted perfectly to our Mediterranean climate" ([diarieljardi](https://diarieljardi.cat/tipus-i-beneficis-arbrat-viari-a-barcelona/)) |
| *Brachychiton* spp. | Bottle tree / arbre ampolla | ~4% ([diarieljardi](https://diarieljardi.cat/tipus-i-beneficis-arbrat-viari-a-barcelona/)) |
| *Melia azedarach* | Mèlia | ~3%, rising from 3% → 4.37% ([catalunyapress, 2026](https://www.catalunyapress.cat/article/barcelona/2026-05-04/5867931-barcelona-declara-guerra-plataner-larbre-icnic-podria-desaparixer-dels-seus-carrers)) |
| *Tilia* spp. | Tell / lime | ~3% ([diarieljardi](https://diarieljardi.cat/tipus-i-beneficis-arbrat-viari-a-barcelona/)) |
| *Jacaranda mimosifolia* | Jacaranda | Thrives in BCN Mediterranean climate ([diarieljardi](https://diarieljardi.cat/tipus-i-beneficis-arbrat-viari-a-barcelona/)) |
| *Koelreuteria paniculata* | Golden-rain tree | Climate-adapted ([diarieljardi](https://diarieljardi.cat/tipus-i-beneficis-arbrat-viari-a-barcelona/)) |
| *Gleditsia triacanthos* | Honey locust | Common street species, ~12% in one tally ([elnacional, 2017](https://www.elnacional.cat/ca/barcelona/...)) — note: hackberry vs honey-locust labelling of the "~12%" slot differs between sources; `REQUIRES_VERIFICATION` |

**Drought-tolerant low-water natives recommended by CREAF (research-backed, VERIFIED):** *Quercus ilex* (alzina), *Celtis australis* (lledoner), *Olea europaea* (olivera) — low hydric requirements; CREAF advises **mixing drought-resistant + shade-producing species** for resilience ([CREAF](https://www.creaf.cat/en/node/70218)). Caveat from [PVB]: pure natives (pines, holm oak, olive, cork oak) are *not ideal as street trees* — slow growth, open crown, evergreen, poor wide cool shade, pines damage pavement — so they are favoured in parks/gardens more than along streets.

**Being phased OUT / reduced:** *Platanus × acerifolia* (see §2). General principle: shift away from a single dominant species toward a broader, climate-resilient palette.

> Action item for accuracy: the **full ranked "espècies recomanades" list lives in [SEL] and [GAV]** — both were 418-blocked to automated fetch. Pull those two PDFs by hand to obtain the complete recommended-species table for the scoring model. Treat the table above as the *attested subset*, not the complete official list. `REQUIRES_VERIFICATION` for completeness.

---

## 4. Ecosystem / co-benefit goals & measurable targets

**Canopy / tree cover (VERIFIED):** target **30% of the city surface covered by tree canopy** within ~20 years, up from **~25%** ([beteve, 2017](https://beteve.cat/societat/en-20-anys-el-30-de-superficie-estara-coberta-per-arbres/)). The strategy emphasises improving tree *quality/resilience* rather than only increasing raw count.

**Green-space growth (VERIFIED, Pla Natura 2021–2030 [PN]):**
- **+160 hectares of green by 2030**, delivering **+1 m² of green per inhabitant** (fulfils the 2015 Climate Commitment, baseline 2015) ([PN] via search; [barcelonaciencia, 2021](https://www.barcelona.cat/barcelonaciencia/ca/noticia/el-nou-pla-natura-preveu-crear-186-hectarees-mes-de-verd-per-al-2023-2_1062127)).
- **+100 hectares of "naturalised" area**, **10 biodiversity shelters (refugis de biodiversitat)**, 40 new "tothom a fer verd" projects, doubling participation in nature activities ([PN] via search; [decidim.barcelona](https://www.decidim.barcelona/processes/PlaNaturaBCN)).
- Structure: 3 axes + 20 actions + 100 projects, 10-year horizon, first 2021–2025 action programme.

**Connectivity / corridors (VERIFIED):** build a functional network of **green corridors** linking city parks/gardens to surrounding forest & river ecosystems — Collserola, and the Llobregat & Besòs river spaces ([PN]; [GAV]; [PVB]).

**Biodiversity / pollinators / birds:** the plans explicitly aim to **increase fauna associated with trees** by widening the species palette ([elnacional, 2017](https://www.elnacional.cat/ca/barcelona/barcelona-reduira-mes-meitat-plataners-fer-arbrat-mes-divers-representen-30-total_1634608_102.html)) and to promote habitat/flower/fruit provision ([PVB]). **Specific numeric pollinator or bird-species targets were not found** in accessible sources — `REQUIRES_VERIFICATION` against [PN]/[PVB] full text.

**Allergenicity reduction:** addressed via reducing *Platanus* and diversifying (§2); no standalone numeric allergen target found — `REQUIRES_VERIFICATION`.

**Stormwater / water:** drought-tolerant species selection and SUDS/green-infrastructure framing are present qualitatively; **no specific stormwater volume target** found in accessible sources — `REQUIRES_VERIFICATION`.

**Budget (context):** ~**€9M/year** for arbrat (a ~16% increase) per the master plan reporting ([beteve, 2017](https://beteve.cat/societat/en-20-anys-el-30-de-superficie-estara-coberta-per-arbres/)).

---

## 5. Invasive / problematic species to AVOID

**VERIFIED — official invasive-species exclusions (do not plant):**
| Species | Common | Status / source |
|---------|--------|-----------------|
| *Ailanthus altissima* | Ailant / tree of heaven | "Very high" priority invasive; in Spanish Catalogue (RD 630/2013); Barcelona spread rate **30.5%**; toxic, attacks native biodiversity ([INV]; [DIBA-INV]; [3cat, 2024](https://www.3cat.cat/324/la-lluita-contra-lailant-larbre-invasor-i-toxic-que-ataca-la-biodiversitat-a-catalunya/noticia/3195788/)) |
| *Robinia pseudoacacia* | Falsa acàcia / black locust | "Medium" priority invasive; Barcelona spread rate **34.5%**; avoid in urban planting ([INV]; [DIBA-INV]; [CREAF](https://www.creaf.cat/en/node/70218)) |
| *Fraxinus ornus* | Freixe de flor / flowering ash | Listed invasive to avoid ([CREAF](https://www.creaf.cat/en/node/70218)) |

**Nuance for the model:** *Robinia* and *Melia* appear in the *existing* street-tree stock (~3% each) yet *Robinia* is flagged invasive — i.e. legacy presence ≠ recommended for new planting. Treat both *Ailanthus* and *Robinia* as **exclude-from-new-planting** in the scoring model. *Ligustrum lucidum* (troana, ~3% stock) appears on broader invasive watchlists in Catalonia — `REQUIRES_VERIFICATION` whether Barcelona's own [INV] flags it for street-tree exclusion.

Official watchlist references: [INV — Estudi d'espècies invasores Barcelona 2012–2020](https://ajuntament.barcelona.cat/espaisverds/sites/default/files/2024-09/EstudiEspeciesInvasores.pdf); [DIBA-INV — Plantes exòtiques invasores, guia de substitució](https://parcs.diba.cat/documents/43788175/50929993/PlantesExotiquesInvasores.pdf).

---

## Modelling cheat-sheet (what to encode)

- **Diversity penalty:** any species pushing toward **>15%** of local stock → penalise (only Barcelona-attested cap). Genus/family caps = generic assumption, NOT cited.
- **Platanus × acerifolia:** strong negative weight for *new* planting (target ↓ to ~12% by 2037; pest/disease/allergy/water flags).
- **Recommended palette (attested):** *Celtis australis, Styphnolobium japonicum, Tipuana tipu, Brachychiton* spp., *Melia azedarach, Tilia* spp., *Jacaranda mimosifolia, Koelreuteria paniculata, Gleditsia triacanthos*; drought natives for park contexts: *Quercus ilex, Olea europaea*.
- **Hard-exclude invasives:** *Ailanthus altissima, Robinia pseudoacacia, Fraxinus ornus* (and verify *Ligustrum lucidum*).
- **City targets to align KPIs:** 30% canopy cover; +1 m²/inhabitant (+160 ha) by 2030; green-corridor connectivity to Collserola/Llobregat/Besòs.
- **Verify against full PDFs before publishing:** per-genus/family caps; complete [SEL]/[GAV] recommended-species table; explicit Ceratocystis mention; pollinator/bird/stormwater numeric targets.
