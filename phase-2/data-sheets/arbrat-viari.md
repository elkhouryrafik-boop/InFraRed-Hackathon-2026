# Data sheet — Arbrat viari (Open Data BCN street-tree inventory)

## 1. Motivation
Municipal street-tree register, Institut Municipal de Parcs i Jardins. For CoolSpend it
supplies (a) the real planted-species palette and (b) existing-tree context per site.

## 2. Composition
145,391 street trees (companions: arbrat-zona ~140k, arbrat-parcs 33,383). 22 columns incl.
`latitud`/`longitud` (EPSG:4326), `x_etrs89`/`y_etrs89`/`geom` (EPSG:25831), `cat_nom_cientific`
(scientific name), `cat_especie_id` (stable species key), `categoria_arbrat` (vigor class
EXEMPLAR/PRIMERA/…), `data_plantacio`, `nom_barri`, `nom_districte`. **No height/crown/trunk** —
the `ALCADA` field was removed in the 23/03/2021 restructuring; crown/trunk never present.

## 3. Collection
Field-maintained municipal asset register. Updated weekly (SETMANAL cadence). Resource UUIDs
rotate — resolve via CKAN `package_show?id=arbrat-viari` (slug stable). No datastore/SQL API
(`datastore_search` → 404); download CSV/JSON.

## 4. Pre-processing
- Use `latitud`/`longitud` directly (WGS84) for mapping + as Infrared vegetation Points.
- **CRS pitfall:** for any distance/area/buffer, reproject to EPSG:25831 (UTM31N) — do NOT compute
  metres in lat/lon degrees.
- Join species attributes on `cat_especie_id` (numeric, stable) — more robust than name strings.

## 5. Uses
- **Should:** derive the real top-N street species (palette); show existing canopy; "don't double-plant".
- **Should NOT:** infer tree SIZE (no dims); infer cooling (no thermal field). Vigor class is maturity,
  not crown size.

## 6. Distribution
Open Data BCN, CC-BY 4.0, no-auth JSON/CSV.

## 7. Maintenance
Ajuntament de Barcelona / Parcs i Jardins. Weekly. Re-resolve UUID before each fetch.

## 8. Limitations
- No per-tree dimensions (2021 removal) → dimensions must come from a species lookup or LiDAR.
- **Bias:** completeness skews to managed streets; informal/private trees and very recent plantings may
  lag. Vigor class (`categoria_arbrat`) is subjective field assessment. Coordinates are trunk points,
  not crown extents. → For CoolSpend (we place NEW trees and the sim computes cooling) these biases are
  low-impact: we use the inventory for species realism + context, not as the cooling signal.
