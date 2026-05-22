# CoolSpend — Brief Revisit (earn-the-data Step 10)

**Question:** Given what the data actually is, can CoolSpend defensibly place trees anywhere in
Barcelona and claim a per-euro cooling value, "knowing each tree" before placing it?

## Verdict: YES, BUT NARROWER — and the narrowing is already how the system is built.

The data earns three claims and explicitly does NOT earn a fourth:

### ✅ EARNED — "place real Barcelona species, anywhere"
arbrat-viari (rubric 14) gives the real planted palette + positions at point resolution, CC-BY,
citywide. The optimizer placing *Platanus × acerifolia, Tipuana tipu, Celtis australis…* (the actual
top street species) is fully defensible. Anywhere-in-Barcelona is earned by the inventory's citywide
coverage + the per-site polygon retarget.

### ✅ EARNED — "seed realistic per-species canopy geometry"
Verd Urbà (rubric 7) gives per-species crown/height as bands → midpoints, fed to the sim as INPUT
geometry. Defensible AS AN ASSUMPTION, with the band recorded. Honest label: "mature-canopy,
species-typical dimensions (Verd Urbà bands)".

### ✅ EARNED — "this placement cools N m² of ground per euro"
ONLY because the Infrared UTCI sim (rubric 11) resolves cooling at 1 m per placement. The headline is
earned by the simulation on real buildings + weather, not by any tree database. Reported as deltas
(baseline − intervention), which are the trustworthy quantity from a model.

### ❌ NOT EARNED — "species X removes Y °C / sequesters Z kg" as a measured per-species fact
No open dataset attaches measured cooling/natural-capital to individual Barcelona species. i-Tree
(Baró 2014, rubric 8) is city-aggregate → fails the 2× rule for per-species/per-tree claims. Our
`cooling_score` (crown × shade-density × leaf-cycle, Rahman 2020) is a SELECTION HEURISTIC, not a
measurement, and is labelled as such in `bcn_species.py`. The system must never present it as a
measured per-species value — and currently does not.

## The honest sentence the project can defend
> "Using Barcelona's real street-tree species (Open Data BCN) with species-typical canopy dimensions
> (Verd Urbà), CoolSpend places trees anywhere in the city and reports the cooled ground area per euro
> as **simulated** by infrared.city's 1 m UTCI model on real buildings and weather. Per-species cooling
> rank is a literature-based heuristic for selection; the cooling value itself is the simulation's."

## What's MISSING (to strengthen, not block)
1. **Measured per-tree dimensions** — ICGC LiDAR canopy-height was WIRED (2026-05-22, `coolspend/bcn_lidar.py`)
   and the hypothesis was empirically REVISED: the Hmitjana product is FOREST-oriented (20 m mean) and
   dense urban Barcelona — where we place street trees — is largely NoData=0. So it does NOT replace
   Verd Urbà per-tree dims; instead it serves as a measured EXISTING-CANOPY site-context signal (bare hot
   target → "high planting opportunity"; leafy locale → real height, e.g. Tibidabo 10.3 m). Also: the open
   WMS/`vsicurl` paths return only rendered RGB / 0 — only the local 166 MB raster sampled with rasterio
   gives real values (see data-sheets/icgc-lidar-canopy.md). True measured PER-URBAN-TREE dims would need
   raw LIDARCAT3 (2021-23) LAZ processing — heavy, deferred.
2. **Verd Urbà license clarity** — confirm reuse terms before any redistribution of the scraped table.
3. **Sim validation** — a surrogate-vs-Infrared RMSE band (the planned calibration study) is the
   credibility bridge; independent field-UTCI validation remains out of scope and should be disclosed.
4. **Young-vs-mature canopy** — `data_plantacio` profiling will quantify how much the mature-size
   assumption overstates near-term cooling; consider a "years-to-maturity" caveat in the headline.

## Bottom line
The sources earn the right to drive placement and to report a SIMULATED cooled-area-per-euro — provided
the per-species cooling stays labelled as a heuristic and the headline stays labelled as simulated.
That is exactly the current architecture. The one change that would materially raise rigor is ICGC
LiDAR for measured canopy dimensions.
