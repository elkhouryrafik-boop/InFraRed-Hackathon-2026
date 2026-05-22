# Data sheet — ICGC + CREAF canopy-height (Hmitjana) LiDAR

## 1. Motivation
Measured EXISTING canopy height per site — the earn-the-data rigor upgrade over species-typical
Verd Urbà bands. Empirically refined after wiring (2026-05-22).

## 2. Composition
"Variables biofísiques de l'arbrat de Catalunya": mean tree height per **20 m** pixel, float32 m,
EPSG:25831, Catalonia-wide (bounds 260000–528000 E, 4488000–4750000 N). nodata=0. LiDAR (PNOA/ICGC)
+ Spanish Forest Inventory calibration by CREAF. Vintage **2016-2017**.

## 3. Collection
LiDAR-derived, forest-inventory-calibrated raster. Single ~166 MB GeoTIFF.

## 4. Pre-processing (EMPIRICAL — what actually works)
- **WMS GetFeatureInfo: UNUSABLE** — returns rendered RGB (all 0), not raw heights (verified).
- **GDAL /vsicurl remote sampling: UNUSABLE** — the TIFF is striped (not a COG); remote window reads
  return 0 (verified).
- **Local rasterio sampling: WORKS** — download the GeoTIFF once (cached, gitignored), reproject
  4326→25831, `ds.sample()`. This is the only reliable path → `coolspend/bcn_lidar.py`.
- Treat raw value 0 (and >80) as NoData → None.

## 5. Uses
- **Should:** measured EXISTING-canopy SITE CONTEXT. Forest/leafy locale → real height (e.g. Tibidabo
  10.3 m); bare hot urban target → 0/None = "no existing canopy, high planting opportunity".
- **Should NOT:** set a NEW planted tree's mature height (that is a species property, bcn_species). It is
  20 m MEAN, not per-tree, not max. Do not treat urban 0 as "measured 0 m trees" — it is NoData.

## 6. Distribution
ICGC datacloud GeoTIFF, CC-BY 4.0, no key. Credit **ICGC and CREAF**.

## 7. Maintenance
ICGC + CREAF. 2016-2017 edition (also 2005). LIDARCAT3 (2021-2023) exists only as raw LAZ → no ready CHM.

## 8. Limitations (EMPIRICAL)
- **Forest-oriented:** dense urban Barcelona — exactly where CoolSpend places street trees — is largely
  NoData=0 (Glòries, Eixample, Ciutadella park all 0). Verified. So it informs SITE CONTEXT
  ("is this bare?"), not per-urban-tree dimensions. The optimistic "replace Verd Urbà bands with measured
  per-tree dims" from the first brief-revisit does NOT hold for urban street trees.
- 20 m mean — coarse for a single specimen.
- Vintage ~9 yr old; recent plantings/fellings absent.
- nodata=0 conflates "no trees" with "not measured" — both → None; honest interpretation is "no measured
  canopy", not "verified treeless".
