# CoolSpend

## One-line pitch

A budget-to-decision tool for city heat officers: draw any area in Barcelona, set a
budget, and CoolSpend places trees for the most **square-metres of ground cooled per
euro** — optimised, then **validated with real Infrared UTCI**, and scored as a whole
**ecosystem** (not just shade).

---

## What it is

CoolSpend turns "where is it hot?" into "where does each euro buy the most cooling — and
the healthiest urban ecosystem?" Two modes:

- **Design (site):** draw a polygon anywhere in Barcelona, set a budget. CoolSpend runs a
  multi-objective NSGA-II optimiser over real building/ground context, places species-
  specific trees, and **re-simulates the result on the live Infrared UTCI engine**. The
  headline KPI is **€ per m² of ground cooled ≥0.5 °C** — a footprint metric that does
  not saturate on already-hot sites.
- **Citywide (€1M):** ranks all **494 Barcelona grid cells** by heat × sealed-surface
  priority (Landsat LST + Sentinel sealing) and allocates a budget to the hottest cells
  first — district-scale triage for a multi-year canopy programme.

Every proposed tree is clickable: species, crown, **the actual m² of ground it shades**,
its cooling score, and a full **ecosystem profile**.

---

## Live result (Plaça dels Àngels, Barcelona — real Infrared UTCI)

Validated end-to-end on the **live** infrared.city engine (`backend=live`), with **615
real buildings** fetched for building-aware shade/heat:

- **28 trees** cool **4,268 m²** of ground by ≥0.5 °C at **€30 / m²** (€128,800 total).
- Sun-exposed peak felt temperature **31.0 °C → 29.8 °C**.
- Cooling depth: **3,260 m² cooled ≥1 °C · 1,716 m² ≥2 °C · 664 m² lifted out of heat
  stress** (≥26 °C UTCI).
- Species chosen: Celtis australis (native), Cercis siliquastrum (native), Tipuana tipu,
  Brachychiton populneus, Jacaranda, Melia, Platanus — **zero invasive species**.

---

## Technical depth

- **Optimise → validate.** NSGA-II (pymoo) runs on an analytical thermal surrogate inside
  the hot path (zero SDK calls during the thousands of per-generation evaluations); only
  the Top-3 Pareto picks are re-simulated on real Infrared UTCI (`SimBudget`-guarded). The
  headline number is the **measured** grid difference, not the surrogate.
- **Species-aware placement.** The chromosome carries a species gene per slot; the
  optimiser chooses each tree's species from the **plantable palette** weighted by a
  cooling proxy and ecological diversity.
- **Ecosystem-aware, Barcelona-aligned.** The palette is the 12 most-planted street species
  **minus the three Barcelona excludes as exotic-invasive** (Robinia pseudoacacia,
  Ligustrum lucidum, Ulmus pumila) — per the *Pla Director de l'Arbrat de Barcelona*.
  Each species carries an **ecosystem-health composite** (drought/heat tolerance,
  biodiversity, pollinator value, allergenicity, pest/disease risk, longevity, water,
  maintenance, native status, mycorrhizae) — benefits minus penalties minus an invasive
  veto, reported **alongside** the €/m² KPI, never blended into it.
- **Real measured grids.** Cooled-footprint, multi-threshold bands, and the on-site UTCI
  heatmap are all derived from the live 512×512 UTCI grid (cropped to the site polygon).
- **Clean backend boundary.** `mock | cached | live` via one env var; the live path is
  proven working (this submission's headline ran live). Cached replays real results
  offline for demos.

---

## Creativity

The creative core is **optimise-then-validate** plus **"you don't plant a tree, you
install an ecosystem."** CoolSpend reserves expensive real UTCI calls for the final picks,
keeps a single defensible KPI a budget committee understands (€/m² cooled), and refuses to
recommend a species the city itself is phasing out — so the plan is credible to an
arborist, not just a data scientist. Click any canopy disk to see exactly how much ground
it shades and what ecosystem it brings.

---

## Real-world impact

The persona is a city Chief Heat Officer with a fixed budget and a heatwave forecast.
CoolSpend hands her a ranked, costed, **live-validated** allocation she can defend — at the
site scale (Design mode) and across the whole city (Citywide €1M). It runs on the real
Barcelona street-tree inventory and the city's own planting strategy, and every number
carries a provenance tag (VERIFIED / DECLARED / REQUIRES_VERIFICATION).

---

## Presentation

A deck.gl + Mapbox web app on real Barcelona **satellite imagery**: the live UTCI heatmap
drapes the site, trees render as **per-species canopy-footprint disks**, and clicking one
opens a full species + ecosystem inspect panel. An age slider grows the canopy over the
establishment horizon. Citywide mode zooms out to the 494-cell priority heatmap. The
~3-minute demo: the decision problem → draw + evaluate → live UTCI before/after → click a
tree's ecosystem → the €/m² headline and the citywide €1M map.

---

## Honesty note

- The headline (28 trees, 4,268 m², €30/m², 31.0→29.8 °C) is a **real live Infrared UTCI**
  result at Plaça dels Àngels with 615 buildings; cached replay reproduces it offline.
- Per-species cooling and the **ecosystem-health composite are labelled heuristics for
  selection/ranking**, literature-anchored and cited (`coolspend/docs/`); the cooling
  magnitude itself is the Infrared sim's, not the heuristic's.
- Cost constants are itemised and Barcelona-anchored where verified (OpEx from BCN IMPJ
  Arbrat Viari; planting/guarding from Diputació de Barcelona); stock/excavation/soil are
  DECLARED pending direct tender extraction. The analytical surrogate's 12 °C ΔTmrt cap is
  unsourced (REQUIRES_VERIFICATION) and is used only to rank candidates, which are then
  re-simulated on real UTCI.
- Full data-source tags and disclosures: [MOCKS.md](MOCKS.md),
  [coolspend/docs/bcn_planting_strategy.md](coolspend/docs/bcn_planting_strategy.md),
  [coolspend/docs/species_ecology_traits.md](coolspend/docs/species_ecology_traits.md).

---

## Links

- GitHub repo: `<FILL IN>`
- Hugging Face Space / deployed app: `<FILL IN>`
- Demo video: `<FILL IN after recording>`
