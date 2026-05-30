"""coolspend.sites — locked demo sites (single source of truth for site selection).

Decision 2026-05-29: the hero site is Plaça dels Països Catalans (Sants, Barcelona)
— a deliberately barren, over-paved, near-treeless, sun-exposed hardscape: the poster
child for Barcelona's depavement ("despavimentació") need. Maximises both measured
cooling delta (hot asphalt baseline) and narrative impact.

Each site: WGS84 centre (lon, lat) + the square side in metres the scan covers.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Site:
    key: str
    name: str
    lon: float
    lat: float
    side_m: float
    note: str


SITES: dict[str, Site] = {
    "paisos_catalans": Site(
        "paisos_catalans", "Plaça dels Països Catalans, Barcelona",
        2.1402, 41.3793, 90.0,
        "Barren over-paved hardscape in front of Sants station; depavement hero site.",
    ),
    "superilla_sant_antoni": Site(
        "superilla_sant_antoni", "Superilla Sant Antoni, Barcelona",
        2.1605, 41.3795, 90.0,
        "Sant Antoni superblock — reclaimed road space; practical depave + planter site.",
    ),
    "superilla_poblenou": Site(
        "superilla_poblenou", "Superilla Poblenou, Barcelona",
        2.1975, 41.4036, 90.0,
        "Poblenou superblock intersection — pedestrianised reclaimed asphalt.",
    ),
}

# LOCKED hero site for the demo.
DEFAULT_SITE_KEY: str = "paisos_catalans"


def default_site() -> Site:
    return SITES[DEFAULT_SITE_KEY]
