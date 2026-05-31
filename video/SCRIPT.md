# CoolSpend — The Locked Shooting Script
### A budget-constrained, geometry-aware decision-support system for cooling Barcelona with street trees

**Total runtime: ~10:00 (600 s)** · VO budget ≈ 2.4 words/second · Tone: cinematic climate-documentary — serious, measured, human.

> EDITOR'S NOTE (locked): The only factual source is PAPER.md. The shipped method is the **budgeted weighted-maximum-coverage greedy** ("smart placement": submodular, (1−1/e) guarantee, ray-cast shade-gain over July suns, 8 m spacing, plantability gate, 40% anti-monoculture cap, then optimise-then-validate on the live Infrared UTCI engine). NSGA-II / TOPSIS / Pareto are NOT the shipped pipeline and are omitted. Two canon datasets are used deliberately: the **single-site canon bundle** for Scene 08 (20 trees / 2,779 m² / €72 / 31.0→30.6 °C, per decision.json) and **PAPER.md §6.2** for the city-wide portfolio in Scene 09 (€900,000 / 90 trees / 6 sites / 20,609 m² / ~26,745 residents / €44 per m² cooled). The brief's mismatched "canon portfolio" line was rejected against PAPER.md and corrected here.

---

## [00:00–01:00] SCENE 01 — The Hottest Block in Barcelona
**SHOT (higgsfield, primary):** Cinematic aerial drift over a dense Mediterranean city at the peak of a summer afternoon — a Barcelona-like grid of tight blocks and bare paved plazas shimmering in heat haze, asphalt and stone radiating warmth, almost no trees, a few green pockets standing out as cool oases. Slow descending push toward one sun-blasted treeless plaza where heat distortion ripples off the pavement. Harsh overhead sun, oppressive stillness; cool teal-green grade in the shaded corners against hot bleached concrete. No people in focus, no text, no logos, no maps.

**VO:** Cities are warmer than the land around them. We call it the urban heat island: the built city runs hotter than the countryside, because dark, sealed surfaces soak up the sun all day, and there is little vegetation left to cool the air by evaporation. And heat is among the deadliest of all climate hazards. But it does not fall evenly. The hottest blocks in Barcelona are the most paved, the least green, and often the most densely lived-in, all at once. Meet the person who has to act on that map — a city's Chief Heat Officer. One fixed budget. A heatwave coming. And a single, unforgiving question: of all these streets, where do we plant the trees?

**ON-SCREEN:** THE HOTTEST BLOCK IN BARCELONA · URBAN HEAT ISLAND · most sealed — least green — most inhabited · ONE BUDGET. WHERE DO WE PLANT?

**GLOSSES:**
- *urban heat island* — Cities run hotter than the surrounding countryside because dark, sealed surfaces store daytime heat and there is little vegetation left to evaporate it away.
- *Chief Heat Officer* — A city official responsible for protecting residents from extreme heat, who must decide how to spend a fixed budget before a heatwave hits.

> FIX APPLIED: "A heatwave already in the forecast" → "A heatwave coming" (paper uses a fixed July peak-heat window, not a forecast). "Chief Heat Officer" retained as an explicit dramatized persona only.

---

## [01:00–01:55] SCENE 02 — UTCI: Measuring What People Feel
**SHOT (dataviz, primary):** Cool documentary palette on near-black. A thermometer reads calm air (~31 °C) beside a translucent human silhouette on a plaza tile; wavy "RADIANT HEAT" arrows rise from pavement and walls, drawn larger/redder than a small wind arrow and a humidity droplet. The four inputs funnel into one rounded chip — **UTCI**, "what a body actually feels (°C)" — radiant heat visibly weighted heaviest. A vertical UTCI gauge sweeps up; a hard tick at 26 °C splits "no thermal stress" from "moderate heat stress." Window stamp: "July 09:00–17:00 · 1.1 m (pedestrian height)." A tree canopy slides in; the radiant arrows under its shadow dim and the needle eases back. End card: "SHADE → cuts radiant heat → cuts UTCI."

**VO:** And to act on it, you first have to measure heat the way a body does. A thermometer reads the air. But a body on a sunlit plaza feels something else entirely. The pavement, the walls, the sky all radiate heat onto your skin — and that radiant load, not the air, is the biggest driver of daytime discomfort. So CoolSpend judges every plan on UTCI, the Universal Thermal Climate Index. UTCI folds four things into one number in degrees Celsius: air temperature, radiant heat off hot surfaces, wind, and humidity. It is, in short, what a body actually feels. Above twenty-six degrees, comfort tips into moderate heat stress. We evaluate it where it matters — a July day, nine to five, at one-point-one metres, the height of a walking person. And here is the lever: shade attacks the radiant term directly. Cool the surfaces, and you cool the person.

**ON-SCREEN:** UTCI · °C = what a body feels · 26 °C · July 09:00–17:00 · 1.1 m · SHADE → radiant heat

**GLOSSES:**
- *UTCI / Universal Thermal Climate Index* — One number, in degrees Celsius, for what a body actually feels: it folds air temperature, radiant heat off hot surfaces, wind, and humidity into a single value.
- *Mean radiant temperature* — The heat radiating off sunlit pavement and walls — the biggest driver of daytime discomfort, and exactly what shade removes.
- *26 °C UTCI threshold* — The boundary between no thermal stress and moderate heat stress; above it, comfort starts to break down.

> CONNECTIVE OPENING added. "a July afternoon" → "a July day, nine to five" for precision (window starts in the morning).

---

## [01:55–02:55] SCENE 03 — Four Real Maps of a Real City
**SHOT (dataviz, primary):** Dark Barcelona outline. Four translucent map layers fan out and stack. Zoom to the vulnerability grid: ~494 square cells (~400 m) pulse warm-to-cool by composite score, with three source chips — a Landsat thermal swatch heating red ("land-surface temperature"), a Sentinel-1 radar swatch filling solid ("sealed surface"), a Sentinel-2 swatch where a low-NDVI bar stays nearly empty ("low NDVI = little vegetation"). Caption stamp: "WHERE to look — not how much cooling." OSM vector geometry draws on (footprints, road centerlines, furniture dots) with a tiny tree icon bouncing OFF a rooftop. A 12-row "arbrat viari" species table flickers in. A population card counts up to 1,702,814 across 73 barris. End: "Four maps. One real city."

**VO:** A model is only as honest as the maps beneath it. CoolSpend stands on four real, independently sourced layers of Barcelona. The first is a satellite vulnerability grid: four hundred and ninety-four cells, each roughly four hundred metres across. Landsat reads land-surface temperature. Sentinel-one radar reads sealed, paved ground. And Sentinel-two reads NDVI — a satellite greenness index, where low values mean little existing vegetation. Together they answer where to look — not how much a plan will cool. Second, OpenStreetMap gives real building, road and street-furniture geometry, so no tree lands on a roof or in traffic. Third, Barcelona's arbrat-viari street-tree inventory supplies a twelve-species candidate table. And fourth, the Padró municipal register: one million, seven hundred and two thousand, eight hundred and fourteen residents, across seventy-three neighbourhoods. Four maps. One real city.

**ON-SCREEN:** FOUR REAL MAPS · 494 cells · ~400 m · Landsat · Sentinel-1 · Sentinel-2 · NDVI = greenness · WHERE to look, not how much cooling · OpenStreetMap · arbrat viari · 12 species · Padró: 1,702,814 residents · 73 barris

**GLOSSES:**
- *vulnerability grid* — A heat-and-sealing risk map that tells you WHERE in the city to look, not how much cooling a given plan will deliver.
- *NDVI* — A satellite greenness index, where low values mean little existing vegetation on the ground.
- *land-surface temperature* — How hot the ground itself is, read by Landsat's thermal infrared bands from orbit.
- *sealed surface* — Paved, impervious ground that traps heat, detected by Sentinel-1 radar.
- *arbrat viari* — Barcelona's municipal street-tree inventory, the source of the 12-species candidate table.
- *Padró* — Barcelona's official municipal population register of who lives where, by neighbourhood.

> CLEAN per fact-check. The 12 figure is the candidate INVENTORY table (§3.3), not the 8-species plantable palette — kept as 12.

---

## [02:55–03:50] SCENE 04 — Where a Tree Can Actually Go
**SHOT (dataviz, primary):** Top-down stylised plaza. A 4 m square lattice of dots floods in row-major, with a "4 m" caliper. Constraint filtering animates as elimination: dots inside buildings snap red and vanish, dots on the road turn amber and vanish, a façade clearance ring culls more. Survivors run the spacing test — each accepted dot blooms an 8 m radius that greys out neighbours, leaving a legible allée. An inset shows three bracketed ranges (NACTO 6–9 m, climate 8–10 m, de-paving 6–10 m) snapping onto a shared 8 m tick. Two slots flip to mode cards: PLANTER (box on pavement, 0.6 m wall tick, "no de-paving") and IN-GROUND (de-paved pit, 6 m setback line, dashed unknown utility line, pulsing "requires_utility_survey" tag).

**VO:** Before the algorithm chooses anything, the city has to know where a tree can actually go. CoolSpend never optimizes over open space. It first builds a finite set of candidate slots — each one a single, pre-validated spot a tree could physically occupy. It starts on a four-metre lattice, then tests every point against the plantability constraints: inside the site, off the buildings, off the roadway, clear of every façade, and at least eight metres from any other tree. That eight-metre spacing isn't a guess — it's where three standards converge: NACTO's six-to-nine, the climate guideline's eight-to-ten, de-paving practice's six-to-ten. Then each slot picks a mode. A planter sits on pavement — contained roots, just point-six metres off a wall, no digging. In-ground means a de-paved pit, roots in real soil — a larger mature crown, so more cooling, but a six-metre foundation setback and a buried-utility risk the system won't pretend it can see. So every in-ground slot ships with one honest flag: requires utility survey.

**ON-SCREEN:** WHERE A TREE CAN ACTUALLY GO · 4 m lattice · 8 m minimum spacing · NACTO 6–9 m · climate 8–10 m · de-paving 6–10 m · PLANTER · 0.6 m wall · no de-paving · IN-GROUND · 6 m setback · pit cost · requires_utility_survey

**GLOSSES:**
- *candidate slot* — A single pre-validated spot a tree could physically occupy, rather than any point in open space.
- *plantability constraints* — The rules a spot must pass: inside the site, off buildings, off the roadway, clear of façades, and 8 m from any other tree.
- *4 m generation lattice* — A regular 4-metre grid of test points the system walks to propose candidate spots before validating them.
- *8 m minimum spacing* — No two trees sit closer than 8 m, the distance where street, climate and de-paving standards all agree.
- *planter mode* — A contained planter resting on pavement — roots boxed in, no digging, only 0.6 m of wall clearance needed.
- *in-ground mode* — A de-paved pit with roots in real soil — a larger mature crown and more cooling, but it needs a 6 m foundation setback and carries buried-utility risk.
- *requires utility survey* — An honesty flag on every in-ground slot: the system can't see underground pipes in open data, so it asks for a dig survey instead of assuming the ground is clear.

> FIX APPLIED: "legally and physically occupy" → "physically occupy" (paper does not validate legal clearance). "more cooling" → "a larger mature crown, so more cooling" (tracks "full mature crown").

---

## [03:50–05:10] SCENE 05 — The Greedy Shade-Gain Engine
**SHOT (dataviz, primary):** Top-down schematic plaza, cool green/teal on near-black. ACT 1 — DEMAND FIELD: ground cells color only if they pass three ticking chips ("UTCI > 26 °C", "impervious", "not already shaded"); hottest cells float "weight = UTCI − 26". ACT 2 — SHADE-GAIN: a sun arc sweeps low across the south ("July sun angles"); each shadow ellipse lands NORTH of the trunk; touched cells tally a shade-gain fraction; caption "shade falls north → plant SOUTH of the hotspot" as the tree slides south and its captured cells jump. ACT 3 — THE GREEDY: ghost candidates each show a "gain / euro" chip; the highest pulses and is placed; captured cells dim; the next pick's gain is smaller; a corner curve bends into a concave "diminishing returns / submodular" shape. ACT 4 — GUARANTEE + STOP: dashed "OPTIMUM" line, filled band to ~63%, "(1 − 1/e) = 63%" snaps in; two stop conditions blink ("no positive-gain affordable slot", "budget exhausted") with a struck-through "fixed iteration cap."

**VO:** So how does CoolSpend decide where each tree goes? It starts with a demand field — a map of the ground that actually needs cooling. A cell counts only if it is hot, paved, and unshaded: felt temperature above twenty-six degrees, an impervious surface, and not already under a canopy. Each cell's weight is simply its temperature minus twenty-six, so the hottest ground asks loudest for shade. Then comes the key idea: shade-gain. A tree earns credit only for the ground its real shadow actually covers, traced across many July sun angles. Because the sun sits to the south, shade falls north — so the engine plants trees south of the hotspot, not on top of it. Now the greedy. At every step it picks the single tree giving the most shade-gain per euro, then repeats. Shaded ground can't be cooled twice, so each new tree helps a little less — diminishing returns. That property, submodularity, carries a mathematical guarantee: this simple step-by-step rule reaches at least sixty-three percent of the perfect answer. It stops only when no affordable tree adds value, or the budget runs dry — never on a fixed counter.

**ON-SCREEN:** THE DEMAND FIELD · UTCI > 26 °C + impervious + not-already-shaded · weight = UTCI − 26 · SHADE-GAIN · plant SOUTH of the hotspot · gain per euro · (1 − 1/e) = 63% of optimum · stops on a real condition, never a fixed cap

**GLOSSES:**
- *demand field* — The map of ground that needs cooling — hot, paved, and sunlit — with hotter ground weighted more heavily.
- *UTCI (felt temperature)* — What a person actually feels outdoors, combining air, radiant heat, wind, and humidity into one temperature in degrees Celsius.
- *shade-gain* — The credit a tree earns only for the ground its real shadow actually covers across July sun angles, which pushes trees south of the hotspot.
- *greedy (cost-benefit)* — At each step it simply takes the tree that gives the most shade-gain per euro, then repeats.
- *submodular / diminishing returns* — Each extra tree helps a little less, because shaded ground cannot be cooled twice.
- *(1−1/e) guarantee* — Because of diminishing returns, taking the best-value tree at each step is mathematically proven to reach at least about 63% of the perfect answer.

> FIX APPLIED (required): VO "the most cooling per euro" → "the most shade-gain per euro." Cooling magnitude must never be attributed to the heuristic — cooling comes only from the live UTCI sim. On-screen "gain per euro" was already correct.

---

## [05:10–06:00] SCENE 06 — No Invasives, No London Plane
**SHOT (dataviz, primary):** A 12-row species table fades in. A "GATE" bar sweeps down: Robinia pseudoacacia, Ligustrum lucidum, Ulmus pumila each flash "EXOTIC-INVASIVE — VETOED" and slide out; Platanus × acerifolia gets an amber "PHASE-DOWN — ≈25% of BCN street trees" tag and dims. Counter morphs 12 → 8; survivors snap into a green palette grid. Zoom into one survivor: a stacked health-score bar assembles from drought 0.30, biodiversity 0.20, pollinator 0.20, longevity 0.15, native 0.15, then grey penalty notches subtract and a red −0.30 "INVASIVE VETO" block drives an invasive bar to zero. Nine tree icons drop; a 40% ceiling line appears after a 4-tree grace period and swaps a would-be 5th same-species icon. End: "ECOLOGY-REAL, NOT JUST COOL."

**VO:** A tree is not just a cooling machine. Plant the wrong species and you trade a heat problem for an ecological one. So before the algorithm places a single tree, every candidate passes the plantability gate — a hard filter that refuses invasive and over-represented species outright. Three exotic invasives — Robinia, Ligustrum, Ulmus pumila — are vetoed; even Robinia, a prized honey tree, loses, because escaping cultivation and damaging native ecosystems outweighs its nectar. The London plane is phased down: a quarter of Barcelona's street trees, heavy on allergy and disease. Twelve species become a plantable eight. Each survivor earns a health score — drought, biodiversity, pollinators, longevity, native status. And an anti-monoculture cap holds any one species at forty percent, so a single pest can never take the whole plan down.

**ON-SCREEN:** THE PLANTABILITY GATE · 12 → 8 SPECIES · 3 INVASIVES VETOED · LONDON PLANE ≈ 25% → PHASED DOWN · HEALTH SCORE · drought 0.30 · biodiversity 0.20 · pollinator 0.20 · longevity 0.15 · native 0.15 · INVASIVE = −0.30 HARD VETO · MAX 40% ONE SPECIES

**GLOSSES:**
- *plantability gate* — A hard filter that refuses ecologically wrong species before any optimisation even runs.
- *exotic-invasive* — A non-native species that escapes cultivation and damages local ecosystems.
- *anti-monoculture cap* — No single species may exceed 40% of the planting, so one pest cannot wipe out the whole plan.
- *health score* — A 0-to-1 ecological rating combining drought tolerance, biodiversity, pollinator value, longevity and native status, minus penalties.

> POLISH APPLIED: "refuses ecologically wrong species" → "refuses invasive and over-represented species" (London plane is phase-down, not invasive). "under forty percent" → "at forty percent" to match the 40% cap exactly.

---

## [06:00–06:50] SCENE 07 — Decades of Canopy, Counted in Euros
**SHOT (dataviz, primary):** ACT 1 — GROWTH: axis "crown diameter (m)" vs "tree age (0–40 yr)"; a dot anchors at 1.5 m, age 0. Two Chapman–Richards sigmoids draw from the shared origin — a bright FAST curve (Tipuana tipu, k≈0.204, 95% at age 20) and a muted SLOW curve (Cercis siliquastrum, k≈0.102, 95% at age 40); a tracer rides each to show slow-fast-slow. Equation chip: crown(age) = max(1.5, A·(1−e^(−k·age))³). ACT 2 — COST: an itemised CapEx ledger builds — stock 600 + pit 500 + soil 600 + guarding 200 + labour 300 = €2,200; an OpEx callout resolves 12,658,229 / 206,556 = 61.28 (VERIFIED); a 40-year timeline drops coins that shrink as they recede (3.5% discount), collapsing into "lifecycle PV ≈ €3,481/tree." Underline: "auditable."

**VO:** A tree is not a switch you flip. Plant it, and its crown is barely a metre and a half across. So CoolSpend grows each species on a Chapman-Richards curve — the forester's S-shape: slow at first, fast in the middle, easing off as it matures. A fast Tipuana fills its crown in twenty years; a slow Cercis takes forty — roughly twice as long. Now the money. Every euro is itemised. Two thousand two hundred to plant one tree — stock, pit, soil, guarding, labour. Then sixty euros a year to keep it alive, a figure we did not invent: it's Barcelona's own parks budget, twelve point six million divided by two hundred thousand trees. Run that over forty years, discounted at three and a half percent, and one tree costs about three thousand five hundred euros. Auditable, line by line.

**ON-SCREEN:** crown(age) · Chapman–Richards · fast k≈0.204 / slow k≈0.102 · CapEx €2,200 · OpEx €60/tree/yr · 12,658,229 / 206,556 = 61.28 (VERIFIED) · 40 yr @ 3.5% · PV ≈ €3,481/tree

**GLOSSES:**
- *Chapman-Richards growth* — The standard forestry S-curve — canopy grows slowly at first, fast in the middle, then slows as it matures — so cooling ramps up realistically over years, not instantly.
- *CapEx vs OpEx* — CapEx is the one-time cost to plant the tree; OpEx is the yearly cost to keep it alive.
- *discount rate* — Future euros are counted as slightly less valuable than today's euros — the standard EU/UK Green Book convention for comparing costs across decades.

> CLEAN per fact-check. Narration rounds 12,658,229→"twelve point six million" and 206,556→"two hundred thousand"; on-screen carries exact verified figures (honest disclosure).

---

## [06:50–08:05] SCENE 08 — Optimise, Then Validate — Live
**SHOT (app_capture, primary):** Live CoolSpend single-site UI in 2D analysis mode on the satellite basemap, 20 green canopy-footprint discs at 8 m spacing already placed. Step 1: toggle the UTCI heatmap to the BASELINE grid (red-hot, cropped to polygon). Step 2: toggle to the INTERVENTION grid — the same area shifts cooler under the discs (the visible before/after). Step 3: let the HUD surface the measured numbers (2,779 / 2,239 / 1,491 m² bands, mean −1.48 °C, peak 31.0 → 30.6 °C, €72/m²). Step 4: click one tree to pop the inspector (e.g. Tipuana tipu) with its shade footprint and the data-provenance footer, MEASURED badge lit. Hold on the MEASURED badge.
**Lower-third (Remotion overlay):** 4-step pipeline ribbon "measured baseline UTCI field → greedy place → live before/after → measured grid difference," with a €72/m² count-up on the final beat.

**VO:** Now watch a layout stop being a proposal and become a measurement. CoolSpend follows one rule: optimise, then validate. Let the fast, deterministic greedy engine choose the layout, then spend the expensive real simulations to find out what it actually does. Four steps. Build the demand field from a measured baseline UTCI field. Greedily place the trees where their shadows truly fall. Run a live before-and-after simulation on the Infrared engine. Then report only the measured difference between the two grids. On this site, the greedy placed twenty trees: eight Tipuana tipu, five Styphnolobium japonicum, four Cercis siliquastrum, three Melia azedarach. Zero invasive. Zero London plane. Live calls are hard-capped at three per run, so one evaluation can never burn a runaway stack of paid simulations. And the result is the proof. Two thousand seven hundred and seventy-nine square metres cooled by at least half a degree. Two thousand two hundred and thirty-nine, by a full degree. Fourteen ninety-one, by two. Mean felt-temperature drop, one point four eight degrees. At the busiest sun-exposed cell, peak felt heat falls from thirty-one to thirty point six. Seventy-two euros per square metre cooled. Not estimated. Measured.

**ON-SCREEN:** OPTIMISE, THEN VALIDATE · 20 TREES · 2,779 m² ≥ 0.5 °C · 2,239 m² ≥ 1 °C · 1,491 m² ≥ 2 °C · −1.48 °C MEAN · 31.0 → 30.6 °C · €72 / m² COOLED · MEASURED

**GLOSSES:**
- *optimise-then-validate* — Let the fast deterministic engine pick the layout, then spend the expensive real simulation to measure its true cooling instead of trusting an estimate.
- *cooled-footprint bands* — How many square metres of ground dropped by at least 0.5, 1, and 2 degrees, counted threshold by threshold.
- *peak felt temperature (90th-percentile cell)* — The headline hot reading is taken at the 90th-percentile cell, not the single hottest pixel, so one freak hot spot cannot inflate the number.
- *SimBudget* — A hard cap of three live simulations per run so a single evaluation can never trigger an unbounded burst of paid calls.

> FIXES APPLIED: "measured baseline heat grid" → "measured baseline UTCI field" (avoids conflation with the 494-cell satellite grid, which is NOT a UTCI field). "spend one expensive real simulation" → "spend the expensive real simulations" (the run is baseline + intervention, capped at three). Single-site canon bundle numbers retained per task instruction — NOT swapped to the paper's 28-tree showcase.

---

## [08:05–09:15] SCENE 09 — Spending a Million Euros Across the City
**SHOT (app_capture, primary):** CoolSpend city-wide mode on the Mapbox satellite basemap, the 494-cell vulnerability grid shaded by composite heat score. (1) Full city, hottest cells glowing. (2) The allocator drops 200 m × 200 m sample polygons over top candidate cells, each flashing a live UTCI evaluation. (3) Six geographically separated per-site markers spread across distinct districts, each with a budget chip staying under €150,000. (4) Click one marker → portfolio panel with placed canopy discs and its 300 m population catchment. (5) Toggle the 300 m catchment circles for all 6 sites — unioned, de-duplicated coverage. (6) End on the portfolio summary: €900,000 committed, 90 trees, 6 sites, 20,609 m² cooled (MEASURED badge), ~26,745 residents, €44/m². MEASURED badge visible throughout.
**Lower-third (Remotion overlay):** counter ticking €0 → €900,000 of €1,000,000.

**VO:** One plaza is a proof. A city is the real question. So we hand CoolSpend a single instruction: spend a million euros, anywhere in Barcelona, where it relieves the most people. It starts from the satellite map — ranks all four hundred ninety-four vulnerability cells, then drops a two-hundred by two-hundred metre sample over the highest-priority candidates and evaluates each one live, on real Infrared comfort fields. A hard rule keeps it honest: no single site may take more than a hundred and fifty thousand euros — so it can never saturate one plaza. It funds the best cost-per-square-metre first, spreads sites apart, and stops on its own. The result: nine hundred thousand euros committed; ninety trees across six separated sites; a measured twenty thousand, six hundred and nine square metres cooled; about twenty-six thousand, seven hundred and forty-five residents reached inside a three-hundred-metre walk — counted once, not twice. Forty-four euros per square metre cooled. The mix is drawn entirely from the plantable palette: zero invasive, zero London plane. The remaining hundred thousand stays uncommitted, by design. This is the answer a Chief Heat Officer can sign.

**ON-SCREEN:** SPEND €1,000,000 · 494 cells ranked · Per-site cap €150,000 · €900,000 committed · 90 trees / 6 sites · 20,609 m² cooled · ~26,745 residents served · €44 / m² cooled · 3-30-300: green within 300 m · €100,000 uncommitted (by design) · ZERO invasive | ZERO London plane

**GLOSSES:**
- *3-30-300 rule / 300 m catchment* — An access norm: every home should have quality green space within a 300-metre walk, so we count the residents living inside that radius of each new planting.
- *de-duplicated catchment union* — When two sites' 300-metre circles overlap, the people in the overlap are counted only once, giving an honest population-served number instead of an inflated sum.
- *person-degrees* — Residents served multiplied by the cooling they actually feel — one people-weighted number for how much heat relief a plan delivers.
- *€ per m² cooled* — The cost-efficiency the budget is allocated by — euros spent divided by the ground area measurably cooled, so cheaper-to-cool sites get funded first.
- *per-site cap* — A €150,000 ceiling on any one location so the budget spreads across the city instead of over-planting a single plaza.

> FIXES APPLIED (required, to PAPER.md §6.2): €990,000→€900,000 · 99 trees→90 trees · 7 sites→6 sites · 24,356 m²→20,609 m² · ~22,590 residents→~26,745 · €32-41/m²→€44/m². DELETED invented per-species counts "40 Tipuana / 33 Celtis / 26 Styphnolobium" (no portfolio per-species counts exist in PAPER.md); replaced with "the mix is drawn entirely from the plantable palette." Added the €100,000-uncommitted line (§6.2/§9.7).

---

## [09:15–10:00] SCENE 10 — Never Report a Number We Didn't Compute
**SHOT (dataviz, primary):** Three horizontal lanes — MOCK / CACHED / LIVE — with a single toggle sliding between them ("selected by one setting"). MOCK: a synthetic plaza tile gets a red "NOT MEASURED DATA" stamp; a network-globe icon shows strikethrough "ZERO NETWORK CALLS." CACHED: a polygon morphs into a hash string; a magnifier snaps onto a match and replays a real heatmap; then the failure branch — no match → a hard red "ERROR" card, an X blocking the arrow back to MOCK ("never silently falls to mock"). LIVE: an arrow hits the Infrared engine, a real red-blue UTCI grid renders, a return arrow deposits a card into the CACHED store ("writes to cache for replay"). FINALE: every number gets a pill — green VERIFIED, amber DECLARED, grey REQUIRES_VERIFICATION; a "MEASURED" badge stays dark over the mock tile but lights only over the live grid. Headline lockup: "NEVER REPORT A NUMBER WE DIDN'T COMPUTE."

**VO:** And here is the idea we are proudest of. Most prototypes blur the line between a number that was computed and a number that was merely hoped for. CoolSpend forces that line into the code itself. Every result comes from one of three backends, chosen by a single setting. Mock is a clearly fake preview: it makes zero network calls and stamps every output "not measured data." Cached replays a real prior run, matched by a hash of the exact geometry; if there's no match, it raises an error — it never quietly falls back to the fake one. Live calls the real Infrared engine, then writes its answer to the cache for replay. And every number wears a provenance tag — verified, declared, or requires-verification. The interface will not say "measured" unless a real thermal grid sits behind it. The discipline is simple: never report a number we did not compute.

**ON-SCREEN:** NEVER REPORT A NUMBER WE DIDN'T COMPUTE · MOCK · CACHED · LIVE · MOCK = NOT MEASURED DATA · ZERO NETWORK CALLS · CACHE MISS → ERROR, NOT MOCK · LIVE → REAL UTCI → WRITES CACHE · VERIFIED / DECLARED / REQUIRES_VERIFICATION

**GLOSSES:**
- *three-tier backend* — Three ways to get a result, picked by one setting: mock is a clearly fake preview, cached is a saved real run replayed, and live is a fresh real simulation.
- *provenance tag* — A label on every number stating how sure we are of it: verified from a source, declared as a design choice, or still needing verification.
- *measured-vs-estimate badge* — A UI label that refuses to say "measured" unless a real UTCI grid is actually behind the number.
- *geometry hash* — A short fingerprint of the exact shape being simulated, used to find the matching saved result in the cache.

> CLEAN per fact-check. Connective opening added ("And here is the idea…").

---

## [10:00–10:35] SCENE 11 — What We Don't Yet Know — and Why That's the Point
**SHOT (higgsfield, primary):** Cinematic aerial drifting slowly over a hot, sealed Barcelona block at golden dusk; long tree shadows stretch north across pale paving stones, mature canopies casting cool green pools onto bright concrete; one open de-paved soil pit sits empty and waiting beside a sidewalk. Slow descending crane settling toward street level as warm light cools to dusk blue; heat shimmer easing. Cool teal-and-green palette, soft volumetric light, shallow depth of field, no people in focus, no text, no logos. Quiet, measured, reflective.

**VO:** And in the end, a tool that guides public money should be judged on what it admits it cannot see. CoolSpend cannot see buried pipes or exact sidewalk widths, so every in-ground slot is flagged for a pre-dig survey, never assumed clear. Its six-metre setback is deliberately cautious. Its shade-gain is only a placement guide; the cooling number always comes from the live simulation. It leaves one hundred thousand of a million euros uncommitted by design, and it speaks for one city, one July. That honesty is the point. Trust is earned through fidelity, not novelty.

**ON-SCREEN:** WHAT WE DON'T YET KNOW · FLAGGED, NOT ASSUMED · 6 m setback · shade-gain = placement proxy · cooling = live UTCI sim · €100,000 / €1,000,000 uncommitted · one city — one July · FIDELITY, NOT NOVELTY

**GLOSSES:**
- *honest limitation* — A gap the system flags out loud rather than hides — it refuses to claim a buried pipe is clear when it simply cannot see it.
- *shade-gain (placement proxy)* — A fast estimate of how much real shadow a tree casts on a hot spot, used only to choose where to plant — never as the reported cooling.
- *6 m setback* — A conservative safe distance kept between an in-ground tree pit and any building, until species roots and local code confirm a tighter number.

> CLEAN per fact-check. Connective opening added. €100,000 / €1,000,000 framing matches PAPER.md §6.2 / §9.7 exactly. End-thesis is the documentary landing.

---

### Recurring-number consistency check (locked, all identical across scenes)
- 494 vulnerability cells (Sc 03, 05-context, 09) · ~400 m cells (Sc 03)
- 8 m spacing (Sc 04, 08) · 4 m lattice · 0.6 m planter wall · 6 m setback (Sc 04, 11)
- 26 °C UTCI threshold; weight = UTCI − 26 (Sc 02, 05)
- (1 − 1/e) = 63% (Sc 05)
- 12 → 8 species; max 40%; invasive −0.30; health weights 0.30/0.20/0.20/0.15/0.15 (Sc 06)
- CapEx €2,200; OpEx €60/yr (12,658,229 / 206,556 = 61.28); 40 yr @ 3.5%; PV ≈ €3,481 (Sc 07)
- **Single-site (canon bundle):** 20 trees; 2,779 / 2,239 / 1,491 m² bands; −1.48 °C mean; 31.0 → 30.6 °C; €72/m² (Sc 08)
- **City-wide (PAPER.md §6.2):** €1,000,000 budget; €150,000 per-site cap; €900,000 committed; 90 trees; 6 sites; 20,609 m² cooled; ~26,745 residents; €44/m²; €100,000 uncommitted (Sc 09, 11)
- Padró 1,702,814 residents / 73 barris (Sc 03)
- Three-tier backend: mock / cached / live; VERIFIED / DECLARED / REQUIRES_VERIFICATION (Sc 10)
