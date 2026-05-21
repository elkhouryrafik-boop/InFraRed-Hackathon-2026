# CoolSpend — Data Inventory (earn-the-data, Phase 2)

Vetting the data that drives tree placement + cooling claims. Verified against primary
sources (DATA_SOURCES.md, 2026-05-21) + Open Data BCN / Diputació / publications.

## Decision unit (Step 1)

CoolSpend makes claims at TWO units — both must be earned:

| Axis | Decision unit | Why |
|---|---|---|
| **Placement** | individual tree (point) within a ~100–500 m site | we place specific trees at specific (lon,lat) |
| **Cooling** | 1 m UTCI grid cell, summer daytime window | the headline (€/m² cooled) is counted per 1 m cell |
| **Species effect** | per-species canopy geometry (crown Ø, height, leaf cycle) | "each tree is different" — drives the sim's MRT |
| Temporal | multi-year summer climatology (July 09–17 window) | design-condition heat relief, not a single day |

**The hard implication:** any source claiming to support the *cooling number* must resolve at
~1 m / per-tree. A city-aggregate cannot. This is the axis most candidates fail.

## Candidates across the six categories (Step 2)

1. Remote sensing optical — ICGC orthophoto / Sentinel-2 NDVI (existing-canopy validation)
2. Remote sensing thermal — Landsat 8/9 TIRS, ECOSTRESS (hot-spot site targeting)
3. Climate reanalysis — the Infrared SDK weather file (nearest EPW station) — drives the sim
4. In-situ — XVPCA air-quality stations (not used; not heat)
5. Biodiversity/ecosystems — i-Tree Barcelona (Baró 2014); GBIF/iNaturalist (rejected: recreation-biased)
6. Built environment — Open Data BCN **arbrat-viari/zona/parcs** (inventory); Verd Urbà (species dims);
   ICGC **LiDAR canopy-height model** (measured dims — currently MISSING from our pipeline); Infrared
   buildings/ground (fetched live per polygon)

## Rubric scores (Steps 3–5)

Decision unit in the verdict column = which unit the source earns. CRS: BCN data is EPSG:4326
(lat/lon, in arbrat-viari) or EPSG:25831 (UTM31N) — reproject to 25831 for any area/distance.

| Dataset | Prov | Res | Cov | Lic | Bias | Total | Verdict |
|---|---|---|---|---|---|---|---|
| **arbrat-viari** (Open Data BCN street trees) | 3 | 3* | 3 | 3 | 2 | **14** | ANCHOR — *species + position* at point res. *Res=3 for species/position; Res=0 for DIMENSIONS (absent).* |
| **Verd Urbà** species dim bands (Diputació) | 2 | 1 | 2 | 1 | 1 | **7** | SUPPORTING — seeds crown/height as band midpoints; license unclear → verify before redistribution. |
| **i-Tree Barcelona** (Baró 2014, Ambio) | 3 | 0 | 2 | 2 | 1 | **8** | SUPPORTING ONLY — city-aggregate; fails 2× for per-species/per-tree cooling. Context, not a claim. |
| **Infrared UTCI simulation** (infrared.city) | 2 | 3 | 3 | 2 | 1 | **11** | ANCHOR for the COOLING claim — 1 m grid per placement. It is a *model*, not measurement (bias=1). |
| **Infrared weather** (nearest EPW station) | 2 | 1 | 2 | 2 | 1 | **8** | SUPPORTING — single nearest station drives the sim's climate; coarse but standard. |
| ICGC LiDAR canopy-height model | 3 | 3 | 2 | 2 | 2 | **12** | RECOMMENDED ADD — would give MEASURED per-tree height/crown, replacing Verd Urbà bands. NOT yet wired. |
| Landsat/ECOSTRESS thermal | 3 | 0 | 3 | 3 | 2 | **11** | SUPPORTING — 70–100 m LST for *where is hot* (site targeting); fails 2× for 1 m placement. |
| GBIF / iNaturalist (mycorrhizal/fungi) | 3 | 0 | 1 | 3 | 0 | **7** | REJECT for this project — recreation/fruiting-body biased; no per-street-tree cooling signal. |

\* arbrat-viari Resolution is split: **3** for the species + position axes it actually carries; **0**
for crown/height (the `ALCADA` field was removed in the 2021 restructuring). It anchors *which species
and where*, not *how big* — that gap is filled (weakly) by Verd Urbà or (strongly) by ICGC LiDAR.

## What earns what

- **Species selection + existing context** → arbrat-viari (ANCHOR, 14). Real, point-resolution, CC-BY.
- **Per-species crown/height geometry** → Verd Urbà bands (SUPPORTING, 7) TODAY; ICGC LiDAR (12) is the
  honest upgrade. Both feed the sim as *input geometry*, never as a cooling claim.
- **The cooling number (€/m² cooled)** → Infrared UTCI sim ONLY (ANCHOR, 11). This is why the architecture
  routes the headline through the sim, not through any tree database.
- **Per-species cooling rank** (which species to prefer) → literature PROXY (crown × shade-density ×
  leaf-cycle; Rahman 2020). A *selection heuristic*, explicitly NOT a measured value. Not a dataset → not
  scored; lives in METHODOLOGY.

See `data-sheets/` for the 8-section sheets and `brief-revisit.md` for the verdict.
