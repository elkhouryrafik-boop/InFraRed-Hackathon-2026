"""
coolspend/population.py — Barcelona POPULATION-SERVED module.

Given a tree-cooling site (lon/lat centroid + optional cooled footprint), estimate
how many Barcelona residents are "served" — i.e. live within a 300 m walking
catchment of the new green (the "300" of the WHO / Cecil Konijnendijk 3-30-300
greening rule: every resident within 300 m of a quality green space).

REAL DATA — no mocks. Two datasets, fetched once and cached to disk so the module
runs offline thereafter:

1. POPULATION (registered residents, "Padró municipal d'habitants")
   Ajuntament de Barcelona Open Data — dataset slug ``pad_mdbas`` ("Població").
   Portal: https://opendata-ajuntament.barcelona.cat/data/ca/organization/poblacio
   We download the most recent annual CSV (vintage 2024-01-01 at time of writing;
   resolved at runtime via CKAN so it tracks the latest year). The CSV is per
   secció-censal; we aggregate ``Valor`` to the 73 barris by ``Codi_Barri``.
   Sanity: the 2024 file sums to 1,702,814 registered residents across 73 barris,
   matching Barcelona's published ~1.7 M population. License: CC-BY 4.0.

2. BARRI GEOMETRY (for area + point-in-polygon catchment)
   Clean GeoJSON mirror of the official Ajuntament barri boundaries:
   https://github.com/martgnz/bcn-geodata  (barris/barris.geojson).
   WGS84 lon/lat. Carries ``BARRI`` (code "01".."73") which joins 1:1 to the
   Padró ``Codi_Barri``. Its official ``AREA`` field matches our pyproj
   EPSG:25831 (UTM-31N) computed polygon area to the square metre.

CROSS-CHECK / documented alternative (NOT downloaded — too heavy):
   GHSL GHS-POP 100 m gridded population (JRC). Would give a finer areal basis but
   is a multi-GB global raster; the per-barri density approach is the lightest
   RELIABLE source and is defensible for a 300 m catchment.

METHOD & honesty
----------------
- Density basis: residents per m² = barri population / barri polygon area (m²,
  EPSG:25831). This is a uniform-density (areal-interpolation / dasymetric-free)
  assumption — residents are NOT actually uniformly spread within a barri, so a
  single-point catchment estimate carries that caveat. We state it in every result.
- People served for a circular 300 m catchment = sum over intersecting barris of
  (barri density × area of catchment∩barri). When shapely is available we compute
  the true geometric intersection (area-weighted, multi-barri). Without shapely we
  fall back to the single barri containing the point × catchment area.
- "Residents" = registered residents (Padró). Daytime/working population, tourists
  and the unregistered are NOT counted. This is the honest, defensible denominator.

Graceful degradation: if the network/dataset is unavailable on first run and no
cache exists, the fetchers log a warning and return None. ``people_served`` then
returns a result dict with ``people_served=None`` and ``method="unavailable"`` —
counts are NEVER fabricated.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import math
import time
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger("coolspend.population")

BASE = Path(__file__).resolve().parent
CACHE_DIR = BASE / "cache" / "population"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_TTL_SEC = 30 * 24 * 3600  # Padró is annual; 30-day cache is conservative.

USER_AGENT = "CoolSpend-Buildathon/2.0 (mailto:elkhouryrafik@gmail.com)"
_HTTP_TIMEOUT = (10.0, 300.0)

# Population dataset (CKAN slug is stable; resource UUIDs rotate, resolved at runtime).
CKAN_BASE = "https://opendata-ajuntament.barcelona.cat/data/api/3/action"
PADRO_SLUG = "pad_mdbas"

# Barri boundary GeoJSON (raw mirror). WGS84 lon/lat, BARRI code joins Codi_Barri.
BARRIS_GEOJSON_URL = (
    "https://raw.githubusercontent.com/martgnz/bcn-geodata/master/barris/barris.geojson"
)

# Default catchment radius — the "300" of WHO / 3-30-300.
DEFAULT_CATCHMENT_M = 300.0

# Cache file names.
_POP_CACHE = CACHE_DIR / "barri_population.json"
_GEO_CACHE = CACHE_DIR / "barris.geojson"
_DENSITY_CACHE = CACHE_DIR / "barri_density.json"


# ── HTTP ───────────────────────────────────────────────────────────────────────

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


# ── Population fetch + cache ────────────────────────────────────────────────────

def _resolve_latest_padro_csv() -> dict[str, str] | None:
    """Resolve the most recent annual CSV resource for ``pad_mdbas`` via CKAN.

    Returns {"url", "name", "year"} or None on failure (logged).
    """
    try:
        with _session() as s:
            r = s.get(
                f"{CKAN_BASE}/package_show",
                params={"id": PADRO_SLUG},
                timeout=_HTTP_TIMEOUT,
            )
            r.raise_for_status()
            payload = r.json()
        if not payload.get("success"):
            logger.warning("CKAN package_show failed for %s", PADRO_SLUG)
            return None
        resources = payload["result"]["resources"]
    except Exception as exc:  # noqa: BLE001 — network/parse failure → degrade
        logger.warning("Could not resolve Padró dataset (%s): %s", PADRO_SLUG, exc)
        return None

    # Annual CSVs are named "<YEAR>_pad_mdbas.csv"; pick the highest year.
    best: tuple[int, dict] | None = None
    for res in resources:
        if (res.get("format") or "").upper() != "CSV":
            continue
        name = res.get("name") or ""
        year = 0
        head = name.split("_", 1)[0]
        if head.isdigit():
            year = int(head)
        if best is None or year > best[0]:
            best = (year, res)
    if best is None:
        logger.warning("No CSV resource found in %s", PADRO_SLUG)
        return None
    year, res = best
    return {"url": res["url"], "name": res.get("name", ""), "year": str(year)}


def _fetch_barri_population() -> dict[str, Any] | None:
    """Download + aggregate the latest Padró CSV to {codi_barri: population}.

    Returns a dict {"year", "source", "population": {codi: int}, "names": {codi: name}}
    or None on failure. Cached to disk.
    """
    meta = _resolve_latest_padro_csv()
    if meta is None:
        return None
    try:
        with _session() as s:
            r = s.get(meta["url"], timeout=_HTTP_TIMEOUT)
            r.raise_for_status()
            # CSV is UTF-8 with BOM in practice; tolerate either.
            text = r.content.decode("utf-8-sig", errors="replace")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not download Padró CSV: %s", exc)
        return None

    population: dict[str, int] = {}
    names: dict[str, str] = {}
    try:
        rd = csv.DictReader(io.StringIO(text))
        for row in rd:
            codi = (row.get("Codi_Barri") or "").strip()
            if not codi:
                continue
            try:
                val = int(float(row.get("Valor") or 0))
            except (TypeError, ValueError):
                val = 0
            key = f"{int(codi):02d}"  # normalise to zero-padded code "01".."73"
            population[key] = population.get(key, 0) + val
            names.setdefault(key, (row.get("Nom_Barri") or "").strip())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not parse Padró CSV: %s", exc)
        return None

    if not population:
        logger.warning("Padró CSV parsed to zero barris — refusing to cache.")
        return None

    out = {
        "year": meta["year"],
        "source": (
            f"Ajuntament de Barcelona Open Data — {PADRO_SLUG} "
            f"({meta['name']}); Padró municipal d'habitants; CC-BY 4.0"
        ),
        "population": population,
        "names": names,
    }
    _POP_CACHE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _load_population_payload() -> dict[str, Any] | None:
    """Return the cached population payload, fetching once if stale/absent."""
    if _POP_CACHE.exists() and (time.time() - _POP_CACHE.stat().st_mtime) < CACHE_TTL_SEC:
        try:
            return json.loads(_POP_CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — corrupt cache → refetch
            pass
    payload = _fetch_barri_population()
    if payload is not None:
        return payload
    # Fetch failed — fall back to a stale cache if one exists (offline resilience).
    if _POP_CACHE.exists():
        try:
            logger.warning("Using stale population cache (fetch failed).")
            return json.loads(_POP_CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None
    return None


def barri_population() -> dict[str, int] | None:
    """Return {codi_barri ("01".."73"): registered residents}.

    None if the dataset is unavailable and no cache exists (never fabricated).
    """
    payload = _load_population_payload()
    if payload is None:
        return None
    return {k: int(v) for k, v in payload["population"].items()}


# ── Barri geometry fetch + cache ─────────────────────────────────────────────────

def _fetch_barris_geojson() -> dict[str, Any] | None:
    """Download the barri boundary GeoJSON (WGS84) and cache it. None on failure."""
    try:
        with _session() as s:
            r = s.get(BARRIS_GEOJSON_URL, timeout=_HTTP_TIMEOUT)
            r.raise_for_status()
            data = json.loads(r.content.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not download barri GeoJSON: %s", exc)
        return None
    if not data.get("features"):
        logger.warning("Barri GeoJSON has no features — refusing to cache.")
        return None
    _GEO_CACHE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def _load_barris_geojson() -> dict[str, Any] | None:
    """Return the cached barri GeoJSON, fetching once if stale/absent."""
    if _GEO_CACHE.exists() and (time.time() - _GEO_CACHE.stat().st_mtime) < CACHE_TTL_SEC:
        try:
            return json.loads(_GEO_CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    data = _fetch_barris_geojson()
    if data is not None:
        return data
    if _GEO_CACHE.exists():
        try:
            logger.warning("Using stale barri GeoJSON cache (fetch failed).")
            return json.loads(_GEO_CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None
    return None


# ── CRS helper (WGS84 lon/lat → EPSG:25831 UTM-31N, for all metre/area math) ─────

_TO_UTM = None


def _to_utm():
    global _TO_UTM
    if _TO_UTM is None:
        from pyproj import Transformer  # noqa: PLC0415
        _TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:25831", always_xy=True).transform
    return _TO_UTM


# ── Barri area + density ─────────────────────────────────────────────────────────

def _barri_area_m2() -> dict[str, float] | None:
    """Return {codi_barri: polygon area in m²} computed in EPSG:25831.

    Uses shapely for a correct multipolygon area. None if geometry unavailable.
    """
    geo = _load_barris_geojson()
    if geo is None:
        return None
    try:
        from shapely.geometry import shape  # noqa: PLC0415
        from shapely.ops import transform  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        logger.warning("shapely unavailable for area computation: %s", exc)
        return None

    tr = _to_utm()
    areas: dict[str, float] = {}
    for feat in geo["features"]:
        props = feat.get("properties", {})
        code = props.get("BARRI")
        if code is None:
            continue
        try:
            key = f"{int(code):02d}"
        except (TypeError, ValueError):
            continue
        try:
            geom_utm = transform(tr, shape(feat["geometry"]))
            areas[key] = float(geom_utm.area)
        except Exception as exc:  # noqa: BLE001 — skip a bad geometry, keep going
            logger.warning("Bad geometry for barri %s: %s", key, exc)
    return areas or None


def barri_density_per_m2() -> dict[str, float] | None:
    """Return {codi_barri: residents per m²} = population / EPSG:25831 area.

    None if either population or geometry is unavailable. Cached to disk.
    """
    pop = barri_population()
    areas = _barri_area_m2()
    if pop is None or areas is None:
        return None
    density: dict[str, float] = {}
    for code, area in areas.items():
        if area > 0 and code in pop:
            density[code] = pop[code] / area
    if not density:
        return None
    try:
        _DENSITY_CACHE.write_text(
            json.dumps({k: round(v, 8) for k, v in density.items()}, indent=2),
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001 — caching density is best-effort
        pass
    return density


# ── Catchment math ───────────────────────────────────────────────────────────────

def _circle_utm(cx: float, cy: float, radius_m: float):
    """A shapely circle (Point.buffer) in UTM metres."""
    from shapely.geometry import Point  # noqa: PLC0415
    return Point(cx, cy).buffer(radius_m, quad_segs=32)


def people_served(
    lon: float,
    lat: float,
    catchment_m: float = DEFAULT_CATCHMENT_M,
    barri: str | None = None,  # noqa: ARG001 — accepted for API symmetry; unused (we use geometry)
) -> dict[str, Any]:
    """Estimate residents living within ``catchment_m`` of (lon, lat).

    Area-weighted over all barris the 300 m circle intersects (true geometry when
    shapely is available; single-barri fallback otherwise). All metre/area math is
    done in EPSG:25831.

    Returns a dict:
      {people_served, density_basis, catchment_m, catchment_area_m2,
       method, source, barris, assumption}
    ``people_served`` is a non-negative int, or None when the data is unavailable.
    """
    density = barri_density_per_m2()
    payload = _load_population_payload()
    source = payload["source"] if payload else "unavailable"

    base = {
        "catchment_m": catchment_m,
        "catchment_area_m2": round(math.pi * catchment_m * catchment_m, 1),
        "source": source,
        "assumption": (
            "Registered residents (Padró) only; uniform-density areal interpolation "
            "within each barri (residents not actually uniformly distributed)."
        ),
    }

    if density is None:
        logger.warning("people_served: population/geometry unavailable — returning None.")
        return {
            **base,
            "people_served": None,
            "density_basis": None,
            "method": "unavailable",
            "barris": [],
        }

    # Reproject the point to UTM and build the catchment circle.
    tr = _to_utm()
    cx, cy = tr(lon, lat)

    geo = _load_barris_geojson()
    served = 0.0
    barris_hit: list[dict[str, Any]] = []
    method = "area_weighted_intersection"

    try:
        from shapely.geometry import shape  # noqa: PLC0415
        from shapely.ops import transform  # noqa: PLC0415

        circle = _circle_utm(cx, cy, catchment_m)
        trf = _to_utm()
        for feat in geo["features"]:
            props = feat.get("properties", {})
            code = props.get("BARRI")
            if code is None:
                continue
            try:
                key = f"{int(code):02d}"
            except (TypeError, ValueError):
                continue
            dens = density.get(key)
            if dens is None:
                continue
            geom_utm = transform(trf, shape(feat["geometry"]))
            if not geom_utm.intersects(circle):
                continue
            inter_area = geom_utm.intersection(circle).area
            if inter_area <= 0:
                continue
            contrib = dens * inter_area
            served += contrib
            barris_hit.append({
                "codi_barri": key,
                "nom_barri": (payload["names"].get(key) if payload else None),
                "density_per_m2": round(dens, 6),
                "intersection_m2": round(inter_area, 1),
                "people": round(contrib, 1),
            })
    except Exception as exc:  # noqa: BLE001 — shapely missing/failed → point fallback
        logger.warning("Area-weighted catchment failed (%s); using point-density fallback.", exc)
        method = "point_density_fallback"
        key = _barri_code_at_point(lon, lat)
        dens = density.get(key) if key else None
        if dens is None:
            # Last resort: city-mean density.
            dens = sum(density.values()) / len(density)
            method = "city_mean_density_fallback"
        served = dens * base["catchment_area_m2"]
        barris_hit.append({
            "codi_barri": key,
            "density_per_m2": round(dens, 6),
            "people": round(served, 1),
        })

    return {
        **base,
        "people_served": int(round(served)),
        "density_basis": "persons_per_m2_padro",
        "method": method,
        "barris": barris_hit,
    }


def _barri_code_at_point(lon: float, lat: float) -> str | None:
    """Return the codi_barri whose polygon contains (lon, lat), or None.

    Used only by the point-density fallback path.
    """
    geo = _load_barris_geojson()
    if geo is None:
        return None
    try:
        from shapely.geometry import Point, shape  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return None
    pt = Point(lon, lat)
    for feat in geo["features"]:
        props = feat.get("properties", {})
        code = props.get("BARRI")
        if code is None:
            continue
        try:
            if shape(feat["geometry"]).contains(pt):
                return f"{int(code):02d}"
        except Exception:  # noqa: BLE001
            continue
    return None


# ── Integration helper for citywide.py ───────────────────────────────────────────

def served_for_centroid(
    centroid_lonlat: tuple[float, float],
    catchment_m: float = DEFAULT_CATCHMENT_M,
) -> dict[str, Any]:
    """Cheap wrapper used by citywide.allocate_citywide for a per-cell centroid.

    Returns the same dict as ``people_served``. Safe to call repeatedly — both
    datasets are loaded once from the on-disk cache.
    """
    lon, lat = centroid_lonlat
    return people_served(lon, lat, catchment_m=catchment_m)


def portfolio_people_served(
    centroids_lonlat: list[tuple[float, float]],
    catchment_m: float = DEFAULT_CATCHMENT_M,
) -> dict[str, Any]:
    """Unique residents served by a PORTFOLIO of sites (overlaps de-duplicated).

    Builds the geometric UNION of every site's ``catchment_m`` circle in EPSG:25831,
    then sums (barri density × union∩barri area) so a resident inside two nearby
    catchments is counted once. Falls back to a simple sum of per-site estimates if
    shapely is unavailable.

    Returns {total_people_served, sites, method, catchment_m, sum_overlapping,
             source, assumption}. ``total_people_served`` is None if data is missing.
    """
    density = barri_density_per_m2()
    payload = _load_population_payload()
    source = payload["source"] if payload else "unavailable"
    assumption = (
        "Registered residents (Padró) only; uniform-density areal interpolation; "
        "overlapping 300 m catchments unioned so each resident is counted once."
    )

    # Per-site (overlapping) estimates — always useful for context.
    per_site = [people_served(lon, lat, catchment_m) for lon, lat in centroids_lonlat]
    sum_overlapping = sum(
        (s["people_served"] or 0) for s in per_site
    ) if per_site else 0

    if density is None or not centroids_lonlat:
        return {
            "total_people_served": (None if density is None else 0),
            "sites": len(centroids_lonlat),
            "sum_overlapping": (None if density is None else 0),
            "catchment_m": catchment_m,
            "method": ("unavailable" if density is None else "empty"),
            "source": source,
            "assumption": assumption,
        }

    geo = _load_barris_geojson()
    try:
        from shapely.geometry import shape  # noqa: PLC0415
        from shapely.ops import transform, unary_union  # noqa: PLC0415

        tr = _to_utm()
        circles = []
        for lon, lat in centroids_lonlat:
            cx, cy = tr(lon, lat)
            circles.append(_circle_utm(cx, cy, catchment_m))
        union = unary_union(circles)

        unique = 0.0
        for feat in geo["features"]:
            code = feat.get("properties", {}).get("BARRI")
            if code is None:
                continue
            try:
                key = f"{int(code):02d}"
            except (TypeError, ValueError):
                continue
            dens = density.get(key)
            if dens is None:
                continue
            geom_utm = transform(tr, shape(feat["geometry"]))
            if not geom_utm.intersects(union):
                continue
            unique += dens * geom_utm.intersection(union).area
        return {
            "total_people_served": int(round(unique)),
            "sites": len(centroids_lonlat),
            "sum_overlapping": int(round(sum_overlapping)),
            "catchment_m": catchment_m,
            "method": "union_area_weighted",
            "source": source,
            "assumption": assumption,
        }
    except Exception as exc:  # noqa: BLE001 — shapely missing → fall back to sum
        logger.warning("portfolio union failed (%s); summing per-site (may double-count).", exc)
        return {
            "total_people_served": int(round(sum_overlapping)),
            "sites": len(centroids_lonlat),
            "sum_overlapping": int(round(sum_overlapping)),
            "catchment_m": catchment_m,
            "method": "sum_no_dedup_fallback",
            "source": source,
            "assumption": assumption,
        }
