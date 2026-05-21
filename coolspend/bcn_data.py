"""
coolspend/bcn_data.py — REAL Barcelona tree data (Open Data BCN / CKAN).

Replaces the placeholder 4-name species palette with Barcelona's ACTUAL street-tree
inventory + a sourced per-species attribute table. See DATA_SOURCES.md for full
provenance, field schema, and honesty flags.

What this module provides:
  - resolve_resource(slug)         : current CSV resource UUID via CKAN package_show
                                     (UUIDs rotate; slugs are stable).
  - download_inventory(slug)       : download + 30-day cache the inventory CSV.
  - load_trees(slug, bbox)         : real existing trees (lon/lat + scientific species),
                                     optionally filtered to a [w,s,e,n] WGS84 bbox.
  - species_frequency(slug)        : {scientific_name: count} — the real planted palette.

Honesty: the inventory has NO per-tree height/crown (removed 2021). Dimensions come
from the species table in bcn_species.py (Verd Urbà bands). Coordinates: 'latitud'/
'longitud' are WGS84 (EPSG:4326), ready to use.

License: CC-BY 4.0 (Ajuntament de Barcelona). No-auth JSON/CSV CKAN. No datastore API
(download files). Network-only; cached to disk so repeat runs are offline.
"""
from __future__ import annotations

import csv
import io
import json
import time
from pathlib import Path
from typing import Any

import requests

BASE = Path(__file__).resolve().parent
CACHE_DIR = BASE / "cache" / "bcn_data"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL_SEC = 30 * 24 * 3600  # inventory updates weekly; 30-day cache is safe

CKAN_BASE = "https://opendata-ajuntament.barcelona.cat/data/api/3/action"
USER_AGENT = "CoolSpend-Buildathon/2.0 (mailto:elkhouryrafik@gmail.com)"

# Stable dataset slugs (DATA_SOURCES.md §A). UUIDs rotate — resolve at runtime.
INVENTORY_SLUGS = ("arbrat-viari", "arbrat-zona", "arbrat-parcs")
DEFAULT_SLUG = "arbrat-viari"  # street trees — the relevant context for street planting

_HTTP_TIMEOUT = (10.0, 300.0)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def resolve_resource(slug: str = DEFAULT_SLUG) -> dict[str, str]:
    """Resolve the current CSV resource (UUID + download URL) for a dataset slug.

    Queries CKAN package_show (slugs are stable; resource UUIDs rotate). Returns the
    first CSV-format resource. Cached 30 days.

    Returns: {"resource_id", "url", "format", "last_modified"}.
    Raises: RuntimeError if the package or a CSV resource is not found.
    """
    cache = CACHE_DIR / f"resolve_{slug}.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < CACHE_TTL_SEC:
        return json.loads(cache.read_text(encoding="utf-8"))

    with _session() as s:
        r = s.get(f"{CKAN_BASE}/package_show", params={"id": slug}, timeout=_HTTP_TIMEOUT)
        r.raise_for_status()
        payload = r.json()
    if not payload.get("success"):
        raise RuntimeError(f"CKAN package_show failed for slug={slug!r}")
    resources = payload["result"]["resources"]
    csv_res = next(
        (res for res in resources if (res.get("format") or "").upper() == "CSV"),
        None,
    )
    if csv_res is None:
        raise RuntimeError(f"No CSV resource in dataset {slug!r}")
    out = {
        "resource_id": csv_res["id"],
        "url": csv_res["url"],
        "format": csv_res.get("format", ""),
        "last_modified": csv_res.get("last_modified") or csv_res.get("modified") or "",
    }
    cache.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def download_inventory(slug: str = DEFAULT_SLUG) -> Path:
    """Download + 30-day cache the inventory CSV for a slug. Returns the cached path."""
    cache = CACHE_DIR / f"{slug}.csv"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < CACHE_TTL_SEC:
        return cache
    res = resolve_resource(slug)
    with _session() as s:
        r = s.get(res["url"], timeout=_HTTP_TIMEOUT)
        r.raise_for_status()
        cache.write_bytes(r.content)
    return cache


def _read_rows(slug: str) -> list[dict[str, str]]:
    """Read the inventory CSV into row dicts (download/cache as needed)."""
    path = download_inventory(slug)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    # Sniff delimiter — Open Data BCN CSVs are usually comma but occasionally ';'.
    sample = text[:4096]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delim))


def load_trees(
    slug: str = DEFAULT_SLUG,
    bbox: tuple[float, float, float, float] | None = None,
) -> list[dict[str, Any]]:
    """Load real existing trees as {lon, lat, species, district}.

    Args:
        slug: dataset slug (default arbrat-viari = street trees).
        bbox: optional (west, south, east, north) WGS84 filter — keep trees inside.

    Returns:
        List of dicts with lon, lat (float, WGS84), species (scientific name or None),
        species_id, district. Rows with unparseable coordinates are skipped.
    """
    rows = _read_rows(slug)
    out: list[dict[str, Any]] = []
    for row in rows:
        lat_s = row.get("latitud") or row.get("LATITUD")
        lon_s = row.get("longitud") or row.get("LONGITUD")
        if not lat_s or not lon_s:
            continue
        try:
            lat = float(lat_s.replace(",", "."))
            lon = float(lon_s.replace(",", "."))
        except ValueError:
            continue
        if bbox is not None:
            w, s, e, n = bbox
            if not (w <= lon <= e and s <= lat <= n):
                continue
        out.append({
            "lon": lon,
            "lat": lat,
            "species": (row.get("cat_nom_cientific") or "").strip() or None,
            "species_id": (row.get("cat_especie_id") or "").strip() or None,
            "district": (row.get("nom_districte") or "").strip() or None,
        })
    return out


def species_frequency(slug: str = DEFAULT_SLUG) -> dict[str, int]:
    """Return {scientific_name: count} over the whole inventory — the real planted palette."""
    rows = _read_rows(slug)
    freq: dict[str, int] = {}
    for row in rows:
        sp = (row.get("cat_nom_cientific") or "").strip()
        if sp:
            freq[sp] = freq.get(sp, 0) + 1
    return dict(sorted(freq.items(), key=lambda kv: kv[1], reverse=True))


if __name__ == "__main__":
    print("Resolving arbrat-viari resource…")
    res = resolve_resource()
    print("  resource_id:", res["resource_id"])
    print("  last_modified:", res["last_modified"])
    print("Downloading inventory (cached)…")
    p = download_inventory()
    print("  cached at:", p, f"({p.stat().st_size/1e6:.1f} MB)")
    trees = load_trees()
    print(f"Loaded {len(trees):,} street trees.")
    freq = species_frequency()
    print(f"Distinct species: {len(freq)}. Top 15 planted street species:")
    for i, (sp, n) in enumerate(list(freq.items())[:15], 1):
        print(f"  {i:2d}. {sp:<34} {n:>7,}")
