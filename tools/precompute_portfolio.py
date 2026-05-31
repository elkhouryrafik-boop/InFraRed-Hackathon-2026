"""Precompute the MEASURED €1M citywide portfolio (batch B).

Runs allocate_citywide on the LIVE Infrared backend once, writing every per-cell
UTCI result to the geometry-keyed cache (so future rebuilds replay for free) and
the portfolio to web/public/citywide_plan.json. This replaces the mock/shade-
proxy preview with a measured-grid portfolio: real cooled m² per site, funding
order by measured €/m²-cooled (cooling_source="measured_utci").

Cost: ~2 live sims per evaluated cell (baseline + intervention). With TOP_N=10
that is ~20 sims, paid once. Set INFRARED_BACKEND=cached afterwards to replay.

Usage:  python -m tools.precompute_portfolio
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")

ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:  # noqa: BLE001
    pass

# Default to live for this one-off; honour an explicit override.
os.environ.setdefault("INFRARED_BACKEND", "live")
BACKEND = os.environ["INFRARED_BACKEND"]

TOP_N = int(os.environ.get("PORTFOLIO_TOP_N", "10"))
BUDGET = float(os.environ.get("PORTFOLIO_BUDGET", "1000000"))
PER_SITE = float(os.environ.get("PORTFOLIO_PER_SITE", "150000"))


def main() -> None:
    from coolspend.citywide import allocate_citywide  # noqa: PLC0415

    logging.info(
        "Precomputing portfolio: backend=%s top_n=%d budget=€%.0f per_site=€%.0f",
        BACKEND, TOP_N, BUDGET, PER_SITE,
    )
    plan = allocate_citywide(
        budget_eur=BUDGET,
        top_n=TOP_N,
        backend=BACKEND,
        per_site_budget_eur=PER_SITE,
    )

    out = ROOT / "web" / "public" / "citywide_plan.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    logging.info(
        "\nWrote %s\n  cooling_source=%s measured=%s\n  %d sites, %d trees, €%s spent, "
        "%s m² cooled, %s people served",
        out, plan.get("cooling_source"), plan.get("cooling_is_measured"),
        plan.get("allocated_count"), plan.get("total_trees"),
        f"{plan.get('total_allocated_eur', 0):,.0f}",
        f"{plan.get('total_cooled_footprint_m2', 0):,.0f}",
        f"{plan.get('total_people_served') or 0:,}",
    )


if __name__ == "__main__":
    main()
