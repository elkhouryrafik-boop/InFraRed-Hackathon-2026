# CoolSpend — Verified Real Data Sources (Barcelona)

Verified by fetching CKAN `package_show` + file headers on 2026-05-21. Field names,
resource UUIDs, record counts and the "no per-tree dimensions" finding are confirmed
from real data, not metadata claims. **Goal: place new trees ANYWHERE in Barcelona for
max heat relief per euro, knowing each species' real effect before placing it.**

## A. Tree inventory (Open Data BCN / CKAN) — CC-BY 4.0, weekly cadence

Publisher: Institut Municipal de Parcs i Jardins. Identical 22-column schema across all three.
CKAN base: `https://opendata-ajuntament.barcelona.cat/data/api/3/action/package_show?id=<slug>`
No datastore/SQL API (returns 404) — **download the CSV/JSON**. Resource UUIDs rotate; re-resolve
via `package_show?id=<slug>` (slugs are stable) before each fetch.

| Dataset | slug | CSV resource UUID (2026-04-01) | Records | Dims? |
|---|---|---|---|---|
| Street trees (Arbrat viari) | `arbrat-viari` | `23124fd5-521f-40f8-85b8-efb1e71c2ec8` | **145,391** (218 species) | No |
| Zone trees (Arbrat de zona) | `arbrat-zona` | `29cd5c1f-11b1-404b-b3a5-ae29940b8c55` | ~140k | No |
| Park trees (Arbrat dels parcs) | `arbrat-parcs` | `23076aaa-4f0e-4045-b4e5-61d5e651b5a6` | **33,383** | No |

**Schema (CSV header, all three identical):**
`codi, x_etrs89, y_etrs89, latitud, longitud, tipus_element, espai_verd, adreca,
cat_especie_id, cat_nom_cientific, cat_nom_castella, cat_nom_catala, categoria_arbrat,
data_plantacio, tipus_aigua, tipus_reg, geom, catalogacio, codi_barri, nom_barri,
codi_districte, nom_districte`

- **Coords:** `latitud`/`longitud` already **WGS84 (EPSG:4326)** — ready to use. `x_etrs89`/`y_etrs89`
  + `geom` WKT are **EPSG:25831 (ETRS89/UTM31N)** — use only for metric distance/area.
- **Species:** `cat_nom_cientific` (e.g. `Platanus × acerifolia`, `Pinus pinea`); `cat_especie_id`
  = stable numeric species key → join key to the species table.
- **`categoria_arbrat`** = EXEMPLAR/PRIMERA/SEGONA/TERCERA = vigor/maturity class (NOT a dimension).
- **CRITICAL: no height/crown/trunk per tree.** `ALCADA` (height) existed pre-2021 restructuring and
  was removed. Dimensions MUST come from a species lookup, not the inventory.

## B. Species dimensions — Verd Urbà (Diputació de Barcelona)

`https://verd-urba.diba.cat/cercador-arbrat` — **248 species/palms**, categorical attributes:
- Height (Alçada): Baixa <6 m / Mitjana 6–15 m / Alta >15 m
- Crown (Capçada): Estreta 2–4 m / Mitjana 4–6 m / Ampla 6–8 m / Molt ampla >8 m
- Leaf cycle: Caduca (deciduous) / Perenne (evergreen)
- Shade density (densitat d'ombra): Densa / Mitjana / Lleugera
- Plus pruning tolerance, disease/allergen, pavement effect.

**Honesty flags:** categorical BANDS not exact metres (use band midpoints, record the band);
**HTML-only, no API/export** (scrape ~248 rows); reuse license not CC-BY-stated — verify before redistribution.
Cross-check palette/size/leaf with **Pla director de l'arbrat de Barcelona 2017–2037** (PDF).

## C. Per-species natural capital — NO direct Barcelona dataset exists

i-Tree Barcelona (**Baró et al. 2014, Ambio 43(4):466–479**, DOI 10.1007/s13280-014-0507-x) exists but
is **city-aggregate** (3,345 sampled trees), not per-species: C storage 113,437 t; sequestration
6,187 t C/yr; pollution removal 305.6 t/yr ($2.38M/yr). No per-species cooling/UTCI figure published for BCN.

**Defensible proxy chain for per-species cooling (rank/seed only — Infrared sim is the ground truth):**
1. Shade cooling ∝ crown projected area (π·(crown_d/2)²) × shade-density class (LAI proxy).
2. Transpirative cooling ∝ crown × LAI × leaf cycle (evergreen year-round vs deciduous summer-peak).
3. Single-tree mechanistic option: **Rahman et al. 2020, Int J Biometeorol**, DOI 10.1007/s00484-020-02030-8
   — inputs (crown diameter, height, LAI, leaf type) match exactly what Verd Urbà gives.
4. Carbon/pollution: scale Baró 2014 city per-tree averages by crown size (declare as allocation).
5. **Ground truth: infrared.city UTCI per placement.** Proxy only ranks/selects species + seeds crown geometry.

## D. Recommended pipeline
- (i) **Existing context:** arbrat-viari + zona + parcs, join on `cat_especie_id`, WGS84 lat/lon.
- (ii) **Candidate palette w/ dimensions:** species table from Verd Urbà bands → numeric midpoints, keyed by scientific name / `cat_especie_id`.
- (iii) **Per-species cooling score:** proxy chain (C above), validated downstream by Infrared.

## E. Honesty flags (declare as assumptions)
1. No per-tree dims in municipal inventory (removed 2021) → species-typical from Verd Urbà bands.
2. Verd Urbà dims are categorical bands → midpoints assumed.
3. Verd Urbà no API/export + unclear reuse license → scrape + verify.
4. No per-species cooling/UTCI dataset for BCN → literature proxy, Infrared-validated, never a published figure.
5. i-Tree Barcelona is aggregate, sampled, 2008 land cover → city-scale only.
6. CKAN resource UUIDs rotate → re-resolve via `package_show?id=<slug>`.

**Sources:** Arbrat viari/zona/parcs (Open Data BCN) · Verd Urbà Cercador d'arbrat (Diputació de Barcelona) ·
Pla director de l'arbrat 2017–2037 · Baró et al. 2014 Ambio · Rahman et al. 2020 Int J Biometeorol.
