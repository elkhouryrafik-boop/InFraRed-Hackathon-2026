# Tree-Placement Spatial Constraints — Engineering Requirements Checklist

Derived from a focused deep-research pass (2026-05-30) on urban street-tree siting
standards, scoped to automated placement for heat mitigation in dense Barcelona.

**How this feeds the engine.** The placement engine answers three questions, and
each factor below belongs to exactly one:
- **WHERE TREES *CAN* GO** → `HARD` exclusions removed from candidate slots
  (`candidate_slots` `streets`/`buildings` + new point-feature buffers).
- **WHERE TREES *SHOULD* GO** → `SOFT` score modifiers on the demand/priority field
  (`placement_inputs.build_demand_cells`) — more cooling value where it helps most.
- **HOW MANY / SPREAD** → the budgeted greedy (`smart_placement`) over the above.

Tags: **[HARD]** = exclusion · **[SOFT]** = score · **[DATA ✓]** = derivable from open
data now · **[DATA ~]** = partial/proxy · **[DATA ✗]** = open-data gap, flag honestly.

---

## Already handled (baseline)
| Factor | Rule | Source in code |
|---|---|---|
| Site boundary | inside polygon only | `candidate_slots` |
| Building footprint + foundation setback | in-ground ≥ 6 m from facade; planter ≥ 0.6 m | `candidate_slots`, real ground-material building polys |
| Road carriageway | exclude buffered vehicle centerlines (class half-width) | `osm_roads` → `candidate_slots.streets` |
| Existing trees | ≥ 5 m centre-to-centre, no double-planting | `bcn_data` inventory |
| Building shadow | shaded ground reads cool → low demand | live UTCI grid |

---

## A. HARD exclusions — "the only places a tree CAN go"

| # | Factor | Why | Threshold (metric) | Data |
|---|--------|-----|--------------------|------|
| A1 | **Accessible pedestrian band** | Spanish law: a tree must **never** invade the accessible itinerary | keep a clear **1.80 m wide × 2.20 m high** walking band (Orden TMA/851/2021) | **[DATA ~]** OSM `footway`/`sidewalk` width often missing → infer from sidewalk polygon width (Urban Atlas / CartoBCN) or distance-to-curb; **[DATA ✗]** exact clear width often a gap |
| A2 | **Intersection / corner sight triangle** | keep driver/pedestrian sightlines; young (low-canopy) trees block them | no trunk within ~**3 m** of the intersection; clear-stem only if canopy > **2.1 m** (NACTO; US 10.7 m upstream / 6.1 m downstream of curb return) | **[DATA ✓]** OSM road-network nodes (junctions) → buffer |
| A3 | **Pedestrian crossings** | keep crossing sightlines + ramps clear | exclude ~**5 m** around crossing | **[DATA ✓]** OSM `highway=crossing`, `crossing=*` |
| A4 | **Fire hydrants** | firefighting access | ≥ **3 m** (10 ft) | **[DATA ✓]** OSM `emergency=fire_hydrant` |
| A5 | **Building entrances / fire access** | do not block entry/egress | no tree directly in front of entrance | **[DATA ~]** OSM `entrance=*` (sparse) → **[DATA ✗]** often a gap |
| A6 | **Bus/tram stops** | boarding area + shelter clearance | exclude stop footprint (~**5 m**) | **[DATA ✓]** OSM `highway=bus_stop`, `public_transport=platform`, tram stops |
| A7 | **Street lamps / traffic signals** | column clearance + avoid canopy-blocking light/signal | ≥ **2–3 m** | **[DATA ✓]** OSM `highway=street_lamp`, `highway=traffic_signals` |
| A8 | **Overhead power/tram lines** | tall species conflict with conductors | no large species under lines; ≥ ~**15 m** clearance for large crowns, else restrict to < ~8 m mature height | **[DATA ~]** OSM `power=line/minor_line`, tram `power=line` (coverage varies) |
| A9 | **Underground utilities** (water/gas/sewer/telecom) | roots vs apparatus; NJUG 1 m prohibited zone from trunk | trunk ≥ **1 m**, prefer ≥ 2 m from mains; roots live in top 600 mm | **[DATA ✗]** **OPEN-DATA GAP** — not in OSM; needs municipal utility GIS. Flag as "requires survey"; do not fake. |
| A10 | **Metro vents / utility vaults / manholes** | structural void, no rooting | exclude footprint + ~1 m | **[DATA ~]** OSM `railway=ventilation_shaft`, `man_made=manhole` (sparse) |
| A11 | **Monuments / heritage / protected views** | regulatory + cultural | exclude protected setting | **[DATA ~]** OSM `historic=*`, BCN heritage layer; **[DATA ✗]** view corridors a gap |

## B. SOFT suitability — "where a tree SHOULD go (most benefit)"

| # | Factor | Why | Effect on score | Data |
|---|--------|-----|-----------------|------|
| B1 | **Heat (UTCI/LST)** | cool where it's hottest | weight ∝ °C above comfort (already core) | **[DATA ✓]** live UTCI / Landsat LST |
| B2 | **Impervious / sealed surface** | shade helps paved ground most; depave target | demand only on impervious | **[DATA ✓]** ground-material / Copernicus sealed |
| B3 | **Not already shaded** | no value under existing canopy | exclude shaded cells | **[DATA ✓]** BCN inventory + ICGC LiDAR canopy height |
| B4 | **Sidewalk / planting-strip width** | wider strip → bigger species feasible, lower conflict | scale species crown to available width; favour wide strips | **[DATA ~]** sidewalk polygon width (CartoBCN / Urban Atlas) |
| B5 | **Soil / rooting volume** | survival + mature crown | small ≈ 8.5 m³, medium ≈ 17 m³, large ≈ 28–30 m³ per tree (Toronto 15 m³ shared / 30 m³ single); structural soil ~3× | **[DATA ✗]** not mappable from open data → **proxy**: cap crown by available open-ground / strip width |
| B6 | **Solar access trade-off (~41° N)** | deciduous = summer shade + winter sun | already deciduous-biased in `bcn_species`; keep | **[DATA ✓]** species table |
| B7 | **Species–site matching** | drought/wind tolerance, crown vs space | pick species whose mature crown fits B4/B5 + cooling | **[DATA ✓]** `bcn_species` + width |
| B8 | **Pedestrian flow / desire lines** | don't pinch busy footways | down-weight high-flow narrow segments | **[DATA ✗]** flow data a gap; proxy via footway width (B4) |

## C. Open-data gaps (be honest, don't fabricate)
- **A9 underground utilities** — the single biggest gap. Not in OSM. Real siting needs municipal utility GIS / a dig survey. Engine should mark in-ground placements **"REQUIRES utility survey"**, never assert clearance it can't see.
- **A1 exact accessible clear width**, **B5 soil volume**, **B8 pedestrian flow** — partial/proxy only.
- Policy: every gap is surfaced in the output (`REQUIRES_VERIFICATION`), matching the project's no-mock bar. A placement is "best-available-data plantable", **not** survey-grade.

---

## D. Build mapping (what to add)
1. **New module `osm_features.py`** — one Overpass fetch for points/lines: `emergency=fire_hydrant`, `highway=crossing|street_lamp|traffic_signals|bus_stop`, `public_transport=platform`, `power=line|minor_line`, `man_made=manhole`, `railway=ventilation_shaft`, `historic=*`. Buffer each by its A-table clearance → extra exclusion geometries for `candidate_slots` (same mechanism as roads).
2. **Accessibility (A1/B4)** — derive sidewalk/strip width from the sealed-surface / Urban Atlas footway polygons; cap species crown to width; exclude slots that would breach the 1.8 m clear band.
3. **Overhead lines (A8)** — if `power=line` present, restrict species mature height under/near them.
4. **Honest tagging** — in-ground placements carry `requires_utility_survey=True` (A9 gap). Output lists which constraints were data-backed vs assumed.
5. Heat/impervious/shade/soil-proxy already flow through the demand field + species crown.

This is the spec: HARD layers define *the only places a tree can go*; the heat-weighted
demand defines *where it should go*; the €1M budgeted greedy spreads trees across the
most heat. Underground utilities remain a declared survey-stage gap.

### Sources
- BS 5837:2012 / NJUG–Street Works UK Vol 4 (utility proximity, 1 m prohibited zone, roots in top 600 mm).
- NACTO Urban Street Design Guide — Visibility/Sight Distance; Plano TX street-tree standards (intersection setbacks).
- DeepRoot / Toronto Green Standard (soil-volume minimums); Citygreen.
- Orden TMA/851/2021 (Spain) — accessible itinerary 1.80 m × 2.20 m; trees must not invade.
- OpenStreetMap wiki tags: `emergency=fire_hydrant`, `highway=street_lamp|crossing|traffic_signals`, `power=line`.
- NYC Parks & Portland street-tree planting standards (hydrant 3 m, entrance/fire access, overhead-line species height).
- Ajuntament de Barcelona — *Trees for Life: Pla director de l'arbrat 2017–2037*.
