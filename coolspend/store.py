"""
coolspend/store.py — "make it remember": persist evaluated runs so the app stops
forgetting (IAAC Day-2 slides, Part 2).

The interactive flow (api_server.evaluate) computes a cooling result, renders it,
and — until now — forgot it: each /api/evaluate overwrote a single shared bundle
dir and kept no record. This module gives the app a memory.

Split by SHAPE, exactly as the slides' Exercise A teaches:
  - queryable metadata (name, polygon, budget, headline KPIs)  -> a SQLite ROW
  - heavy files (the two UTCI heatmap PNGs + the bundle JSON)   -> a BLOB dir
  - the row stores only the URL of the blob — never the bytes.

Storage is swappable via environment, so "local & MVP" today can become
"Postgres + S3" in production without touching callers (the slides' SQLite ->
Postgres -> S3 progression):
  DATABASE_URL   sqlite file path (default coolspend/var/coolspend.db).
                 A non-sqlite URL (e.g. postgres://) raises NotImplementedError —
                 the seam is declared, not faked.
  BLOB_DIR       directory for run blobs (default coolspend/var/blobs).
  BLOB_BASE_URL  URL prefix the web server exposes BLOB_DIR at (default /blobs).

Public API:
  init_db()                                  -> create the runs table if absent
  save_run(name, polygon, params, payload, eval_dir) -> int (new run id)
  list_runs()                                -> list[dict]  (newest first)
  get_run(run_id)                            -> dict | None (evaluate-shaped payload)
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("coolspend.store")

_BASE = Path(__file__).resolve().parent
_VAR = _BASE / "var"

# The two heatmap PNGs the exporter writes — the "big files" that go to the blob
# store, with only their URL kept in the row.
_PNG_NAMES = ("utci_baseline.png", "utci_intervention.png")
# Payload key -> source PNG filename, so we copy + rewrite both image links.
_IMAGE_FIELDS = {
    "baselineImageUrl": "utci_baseline.png",
    "interventionImageUrl": "utci_intervention.png",
}


# ── Env seams ────────────────────────────────────────────────────────────────

def _db_path() -> Path:
    """Resolve the SQLite file path from DATABASE_URL (default coolspend/var)."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return _VAR / "coolspend.db"
    if url.startswith("sqlite:///"):
        return Path(url[len("sqlite:///"):])
    if url.startswith(("postgres://", "postgresql://", "mysql://")):
        # The seam is real but unimplemented — fail loudly rather than silently
        # writing to a local file the operator did not intend (slides: Postgres
        # is the production swap; wire a driver here when you take it).
        raise NotImplementedError(
            f"DATABASE_URL points at a server DB ({url.split('://', 1)[0]}); "
            "coolspend.store only implements SQLite. Add a driver here to swap."
        )
    return Path(url)


def _blob_dir() -> Path:
    return Path(os.environ.get("BLOB_DIR") or (_VAR / "blobs"))


def _blob_base_url() -> str:
    return (os.environ.get("BLOB_BASE_URL") or "/blobs").rstrip("/")


def blob_mount() -> tuple[str, Path]:
    """(url_prefix, directory) for the web server to expose the blob store at.

    The directory is created so a StaticFiles mount never fails on first boot.
    """
    d = _blob_dir()
    d.mkdir(parents=True, exist_ok=True)
    return _blob_base_url(), d


# ── Connection ───────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


# ── Schema (the slides' "shape of your data") ──────────────────────────────────
# A run is one saved evaluation. PK = id. The blob_url column is the FK-style
# pointer at the warehouse: it links to the file dir, it does NOT hold the file.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT    NOT NULL,
    name            TEXT    NOT NULL,
    backend         TEXT,
    polygon_json    TEXT    NOT NULL,
    budget_eur      REAL,
    w_thermal       REAL,
    w_ecological    REAL,
    -- headline KPIs, denormalised into columns so the list view can show + sort
    -- them without opening every blob.
    delta_utci_c    REAL,
    cooled_m2       REAL,
    n_trees         INTEGER,
    cost_eur        REAL,
    eur_per_m2      REAL,
    -- link to the blob dir (the slides' "just a link", never the bytes).
    blob_url        TEXT
);
"""


def init_db() -> None:
    """Create the runs table if it does not exist. Idempotent."""
    with _connect() as conn:
        conn.execute(_SCHEMA)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _headline_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    """Pull the rank-1 KPIs out of the evaluate payload into flat columns."""
    cfgs = ((payload.get("decision") or {}).get("configurations")) or []
    top = cfgs[0] if cfgs else {}
    return {
        "delta_utci_c": top.get("delta_utci_c"),
        "cooled_m2": top.get("cooled_footprint_m2"),
        "n_trees": top.get("tree_count"),
        "cost_eur": top.get("cost_eur"),
        "eur_per_m2": top.get("eur_per_m2"),
    }


# ── Save / load ────────────────────────────────────────────────────────────────

def save_run(
    name: str,
    polygon: list,
    params: dict[str, Any],
    payload: dict[str, Any],
    eval_dir: Path | str,
) -> int:
    """Persist one evaluated run. Returns the new run id.

    name     human label for the run.
    polygon  the drawn ring ([[lon,lat], ...]) — stored both as a queryable column
             and embedded in the blob JSON so a reload can re-save it.
    params   {budget_eur, w_thermal, w_ecological, backend}.
    payload  the /api/evaluate response dict (decision/boundary/trees/bounds +
             image URLs + impervious/canopy/growth).
    eval_dir the dir the just-finished evaluate wrote its PNGs to (the live
             eval bundle). The PNGs are copied OUT of it into the run's own blob
             dir so a later evaluate overwriting eval_dir cannot corrupt this run.
    """
    init_db()
    eval_dir = Path(eval_dir)
    metrics = _headline_metrics(payload)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO runs
               (created_at, name, backend, polygon_json, budget_eur,
                w_thermal, w_ecological, delta_utci_c, cooled_m2, n_trees,
                cost_eur, eur_per_m2, blob_url)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                created_at, name, params.get("backend"),
                json.dumps(polygon), params.get("budget_eur"),
                params.get("w_thermal"), params.get("w_ecological"),
                metrics["delta_utci_c"], metrics["cooled_m2"], metrics["n_trees"],
                metrics["cost_eur"], metrics["eur_per_m2"], None,
            ),
        )
        run_id = int(cur.lastrowid)

        # Blob dir for this run; copy the heavy files in, rewrite the links.
        run_blob = _blob_dir() / "runs" / str(run_id)
        run_blob.mkdir(parents=True, exist_ok=True)
        base_url = f"{_blob_base_url()}/runs/{run_id}"

        stored = dict(payload)
        stored["site_polygon_lonlat"] = polygon  # so reload can re-save
        for field, fname in _IMAGE_FIELDS.items():
            # Only copy a PNG that this run actually has AND that is on disk in
            # eval_dir (mock/scalar backends produce no grid -> no PNG).
            if payload.get(field) and (eval_dir / fname).is_file():
                shutil.copy2(eval_dir / fname, run_blob / fname)
                stored[field] = f"{base_url}/{fname}"
            else:
                stored[field] = None

        (run_blob / "run.json").write_text(
            json.dumps(stored, ensure_ascii=False), encoding="utf-8"
        )
        conn.execute("UPDATE runs SET blob_url = ? WHERE id = ?", (base_url, run_id))

    logger.info("saved run #%d (%s) -> %s", run_id, name, base_url)
    return run_id


def list_runs() -> list[dict[str, Any]]:
    """Return saved runs, newest first, with the headline KPIs for the list view."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            """SELECT id, created_at, name, backend, budget_eur,
                      delta_utci_c, cooled_m2, n_trees, cost_eur, eur_per_m2
               FROM runs ORDER BY id DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def get_run(run_id: int) -> dict[str, Any] | None:
    """Return the stored evaluate-shaped payload for a run, or None if absent.

    Reads the run's blob JSON; its image URLs already point at the blob store, so
    the frontend renders it through the same path as a fresh /api/evaluate.
    """
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT blob_url FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    run_json = _blob_dir() / "runs" / str(run_id) / "run.json"
    if not run_json.is_file():
        logger.warning("run #%d row exists but blob JSON missing at %s", run_id, run_json)
        return None
    return json.loads(run_json.read_text(encoding="utf-8"))
