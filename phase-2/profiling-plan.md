# CoolSpend — Profiling Plan (run before committing to use)

8-cell profiling per recommended dataset. You run these on the actual data; the plan says what to look for.

## arbrat-viari (anchor — species + position)
1. **Shape/dtypes:** ~145k rows × 22 cols; confirm `latitud`/`longitud` parse as float (comma vs dot decimals).
2. **Missing:** % rows with null `cat_nom_cientific` (we saw species nulls in OSM; check the municipal set) and null coords — drop or flag.
3. **Numeric:** lat/lon bounding box inside Barcelona municipal bounds; flag (0,0) or out-of-bbox points.
4. **Categorical:** distinct `cat_nom_cientific` (≈287); top-N frequency = the real palette; check name spelling variants (× vs x, accents) before joining to bcn_species.
5. **Spatial coverage:** point density per district (`nom_districte`) — confirm all 10 districts present; note managed-street skew.
6. **Temporal:** `data_plantacio` range + nulls — how much of the canopy is young (affects mature-size assumption).
7. **Cross-field:** does `nom_districte` agree with the lat/lon location? spot-check 10.
8. **Bridging:** join key `cat_especie_id` ↔ bcn_species; measure % of inventory trees whose species is in our 12-species table (coverage of the palette).

## Verd Urbà species dims (supporting — crown/height bands)
1. Shape: ~248 species × {height band, crown band, leaf cycle, shade density}.
2. Missing: species in arbrat-viari top-N with NO Verd Urbà entry → fall back to default crown.
3. Numeric: band→midpoint mapping sanity (no crown > height nonsense).
4. Categorical: confirm band vocabulary exactly (Baixa/Mitjana/Alta; Estreta/…/Molt ampla).
5–7. (n/a spatial/temporal) — cross-check leaf cycle vs known botany for the top 12.
8. Bridging: scientific-name match rate to arbrat-viari `cat_nom_cientific` (the join that matters).

## Infrared UTCI sim (anchor — cooling)
1. Shape: `merged_grid` (rows×cols) ≈ site_size² cells; confirm baseline & intervention SAME shape (required for cell-wise diff).
2. Missing: NaN fraction = outside-polygon cells; confirm interior is fully populated.
3. Numeric: grid min/mean/p90/max; confirm intervention ≤ baseline almost everywhere (trees cool, not warm).
4. (n/a) 5. Spatial: cooled cells cluster UNDER tree points (sanity: cooling where canopy is).
6. Temporal: confirm July 09–17 window applied (same TimePeriod to weather + payload).
7. Cross-field: cooled_footprint scales with tree_count / crown size across configs.
8. Bridging: geometry-hash cache key stable → cached replay reproduces the same cooled_footprint.

## ICGC LiDAR CHM (recommended add — measured dims)
1–8. On acquisition: confirm tile coverage over target sites, vertical accuracy, vintage (post-2018 for current canopy), CRS 25831; extract canopy height at arbrat-viari tree points → compare to Verd Urbà band midpoints (the validation that would upgrade dims from band to measured).
