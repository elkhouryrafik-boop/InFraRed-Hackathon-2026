# Data sheet — Verd Urbà species dimensions (Diputació de Barcelona)

## 1. Motivation
Fills the dimension gap arbrat-viari leaves: per-species crown, height, leaf cycle, shade density —
needed to seed realistic canopy geometry into the Infrared UTCI sim.

## 2. Composition
248 species/palms. Categorical BANDS: height Baixa(<6)/Mitjana(6–15)/Alta(>15) m; crown
Estreta(2–4)/Mitjana(4–6)/Ampla(6–8)/Molt ampla(>8) m; leaf cycle Caduca/Perenne; shade density
Densa/Mitjana/Lleugera; plus pruning/allergen/pavement notes.

## 3. Collection
Provincial green-infrastructure guide (Diputació de Barcelona). HTML pages, no API/CSV export.

## 4. Pre-processing
- Scrape ~248 rows → table keyed by scientific name (join to arbrat-viari `cat_nom_cientific`).
- Convert bands → midpoints (crown Ampla → 7 m; height Alta → 18 m) and **record the band** so the
  assumption is auditable (done in `coolspend/bcn_species.py`: `crown_band`/`height_band` fields).
- Map shade density → LAI-proxy weight (Densa 1.0 / Mitjana 0.7 / Lleugera 0.45).

## 5. Uses
- **Should:** seed plausible per-species crown Ø + height as SIM INPUT geometry; rank species for selection.
- **Should NOT:** be reported as measured per-tree dimensions; the bands are species-typical, not surveyed.

## 6. Distribution
diba.cat — HTML only. **Reuse license not stated as CC-BY** → verify before any redistribution; for
internal scoring it is a defensible municipal-authority source.

## 7. Maintenance
Diputació de Barcelona. Cadence not published.

## 8. Limitations
- **Resolution:** categorical bands, not metres → a ±2 m crown uncertainty. For a 1 m UTCI grid this is
  the dominant input-geometry uncertainty. Honest mitigation: ICGC LiDAR canopy-height model would give
  measured per-tree dims (RECOMMENDED upgrade).
- **Bias:** band midpoint assumption; species-typical ≠ site-specific (a young street Platanus is far
  smaller than the >15 m band). → CoolSpend places MATURE-equivalent canopy, so this overstates near-term
  cooling; disclose as "mature-canopy assumption".
- License ambiguity (see §6).
