"""
coolspend/bcn_lidar.py — MEASURED existing-canopy height from ICGC + CREAF LiDAR.

The earn-the-data rigor upgrade (phase-2/brief-revisit.md): a real, measured signal of
EXISTING canopy at a site, to complement the species-typical Verd Urbà bands.

PRODUCT: "Variables biofísiques de l'arbrat de Catalunya" — mean tree height per 20 m
pixel (m), EPSG:25831, vintage 2016-2017, LiDAR + forest-inventory calibrated by CREAF.
License CC-BY 4.0 (credit ICGC and CREAF). No API key.
  Raster: https://datacloud.icgc.cat/datacloud/variables-biofisiques-arbrat/tif_unzip/
          variables-biofisiques-arbrat-v1r1-hmitjana-2016-2017.tif  (~166 MB)

ACCESS NOTE (verified empirically 2026-05-22):
  - The open WMS GetFeatureInfo returns only RENDERED RGB (all 0), NOT raw heights — unusable.
  - GDAL /vsicurl remote sampling returns 0 (the TIFF is striped, not a COG) — unusable.
  - The ONLY reliable path is the local raster sampled with rasterio. So this module
    downloads the raster ONCE into cache (gitignored) and samples it locally.

HONESTY (phase-2 data sheets — confirmed by sampling):
  * 20 m MEAN canopy height, FOREST-oriented. Forest points return real values
    (e.g. Tibidabo 10.3 m; global range 3.5–24.9 m, mean 8.6 m). DENSE URBAN BARCELONA is
    largely NoData=0 (Glòries, Eixample, Ciutadella all 0) — the product was built for
    forest stands, not isolated street trees.
  * For CoolSpend this is exactly useful as SITE CONTEXT: a hot urban target returning ~0
    measured canopy = "bare site, high planting opportunity"; a value = existing canopy to
    account for. It does NOT set a NEW planted tree's mature height (that stays a species
    property, bcn_species) — it measures what is already there.
  * Vintage 2016-2017 (~9 yr old). Returns None on NoData/0 → caller falls back gracefully.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
CACHE_DIR = BASE / "cache" / "bcn_lidar"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
RASTER_PATH = CACHE_DIR / "hmitjana_2016_2017.tif"
RASTER_URL = (
    "https://datacloud.icgc.cat/datacloud/variables-biofisiques-arbrat/tif_unzip/"
    "variables-biofisiques-arbrat-v1r1-hmitjana-2016-2017.tif"
)
ATTRIBUTION = "ICGC + CREAF, CC BY 4.0 (Variables biofísiques de l'arbrat de Catalunya, 2016-2017)"
_HTTP_TIMEOUT = (10.0, 600.0)
_USER_AGENT = "CoolSpend-Buildathon/2.0 (mailto:elkhouryrafik@gmail.com)"


def ensure_raster(auto_download: bool = True) -> bool:
    """Ensure the canopy-height raster is present locally. Returns True if available.

    Downloads once (~166 MB) into cache (gitignored). Set auto_download=False to only
    check presence (e.g. in offline/test contexts).
    """
    if RASTER_PATH.exists() and RASTER_PATH.stat().st_size > 1_000_000:
        return True
    if not auto_download:
        return False
    try:
        import requests  # noqa: PLC0415
        with requests.get(RASTER_URL, timeout=_HTTP_TIMEOUT, stream=True,
                          headers={"User-Agent": _USER_AGENT}) as r:
            r.raise_for_status()
            with open(RASTER_PATH, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
        return RASTER_PATH.exists()
    except Exception:  # noqa: BLE001 — measured context is optional; degrade gracefully
        return False


def canopy_height_m(lon: float, lat: float, auto_download: bool = True) -> float | None:
    """Measured existing canopy height (m) at (lon, lat), or None if NoData/unavailable.

    Samples the local ICGC+CREAF Hmitjana 20 m raster (downloads once if needed).
    Reprojects WGS84 -> EPSG:25831 internally. Returns None for NoData=0 (common in dense
    urban Barcelona) or if rasterio/raster is unavailable — the caller falls back to
    species-typical dimensions. Cached per rounded point.
    """
    key = f"{round(lat, 5)},{round(lon, 5)}"
    cache = CACHE_DIR / f"pt_{key.replace(',', '_').replace('.', 'p').replace('-', 'm')}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8")).get("height_m")

    val: float | None = None
    try:
        import rasterio  # noqa: PLC0415
        from rasterio.warp import transform  # noqa: PLC0415
        if ensure_raster(auto_download=auto_download):
            with rasterio.open(RASTER_PATH) as ds:
                xs, ys = transform("EPSG:4326", ds.crs, [lon], [lat])
                raw = float(next(ds.sample([(xs[0], ys[0])]))[0])
            # nodata=0; the product is 0 over non-forest/urban. Treat 0 (and out-of-range)
            # as "no measured canopy here" -> None (caller falls back / reads as bare).
            if 0.0 < raw <= 80.0:
                val = round(raw, 2)
    except Exception:  # noqa: BLE001
        val = None

    cache.write_text(json.dumps({"height_m": val, "attribution": ATTRIBUTION}), encoding="utf-8")
    return val


def site_canopy_context(lon: float, lat: float) -> dict:
    """Measured existing-canopy context for a site centroid (for the result/UI).

    Returns {measured_canopy_height_m, interpretation, source}. height None/~0 ->
    "bare / high planting opportunity"; a value -> existing canopy to account for.
    """
    h = canopy_height_m(lon, lat)
    if h is None:
        interp = "no measured tree canopy at this 20 m cell (bare / high planting opportunity)"
    else:
        interp = f"existing measured canopy ~{h:.0f} m at this locale"
    return {
        "measured_canopy_height_m": h,
        "interpretation": interp,
        "source": ATTRIBUTION,
    }


if __name__ == "__main__":
    for name, lon, lat in [
        ("Tibidabo forest", 2.1180, 41.4180),
        ("Glories paved", 2.1850, 41.4030),
        ("Eixample", 2.1620, 41.3880),
    ]:
        print(f"{name:<16} -> {site_canopy_context(lon, lat)}")
    print("Attribution:", ATTRIBUTION)
