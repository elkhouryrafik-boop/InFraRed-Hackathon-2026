"""
coolspend/store.py — "make it remember": persist evaluated runs so the app stops
forgetting (IAAC Day-2 slides, Part 2).

The interactive flow (api_server.evaluate) computes a cooling result, renders it,
and — until now — forgot it: each /api/evaluate overwrote a single shared bundle
dir and kept no record. This module gives the app a memory.

Split by SHAPE, exactly as the slides' Exercise A teaches:
  - queryable metadata (name, polygon, budget, headline KPIs)  -> a row column
  - heavy files (the two UTCI heatmap PNGs)                     -> a `blobs` row
  - the metadata row stores only the URL of the blob — never the image bytes.

Storage is swappable via DATABASE_URL, and — unlike the first MVP — BOTH backends
are now real (the slides' SQLite -> Postgres progression, fully wired):
  DATABASE_URL unset / sqlite:///path   -> SQLite file (default coolspend/var).
  DATABASE_URL postgres://… | postgresql://…  -> Postgres (psycopg).

Durability note: the heatmap PNG bytes live IN the database (a `blobs` table,
BYTEA/BLOB), not on the local filesystem. That is deliberate — a free-tier host
(Render free web service) has an EPHEMERAL disk with no persistent volume, so a
file-based blob store would lose saved-run images on every redeploy/sleep. Keeping
the bytes in Postgres makes a saved run survive redeploys with zero object store.
The metadata row still holds only the blob's URL (the slides' "just a link"); the
bytes live in their own table, served by the API at BLOB_BASE_URL.

  BLOB_BASE_URL  URL prefix the API serves saved-run blobs at (default /blobs).

Public API:
  init_db()                                  -> create the tables if absent
  save_run(name, polygon, params, payload, eval_dir) -> int (new run id)
  list_runs()                                -> list[dict]  (newest first)
  get_run(run_id)                            -> dict | None (evaluate-shaped payload)
  get_blob(path)                             -> (bytes, mime) | None  (API blob route)
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("coolspend.store")

_BASE = Path(__file__).resolve().parent
_VAR = _BASE / "var"

# The two heatmap PNGs the exporter writes — the "big files" that go to the blob
# store, with only their URL kept in the metadata row.
_PNG_NAMES = ("utci_baseline.png", "utci_intervention.png")
# Payload key -> source PNG filename, so we copy + rewrite both image links.
_IMAGE_FIELDS = {
    "baselineImageUrl": "utci_baseline.png",
    "interventionImageUrl": "utci_intervention.png",
}


# ── Env seams / dialect ──────────────────────────────────────────────────────

def _database_url() -> str | None:
    return os.environ.get("DATABASE_URL") or None


def _is_postgres() -> bool:
    url = _database_url()
    return bool(url and url.startswith(("postgres://", "postgresql://")))


def _sqlite_path() -> Path:
    """Resolve the SQLite file path from DATABASE_URL (default coolspend/var)."""
    url = _database_url()
    if not url:
        return _VAR / "coolspend.db"
    if url.startswith("sqlite:///"):
        return Path(url[len("sqlite:///"):])
    return Path(url)


def _blob_base_url() -> str:
    return (os.environ.get("BLOB_BASE_URL") or "/blobs").rstrip("/")


def blob_base_url() -> str:
    """Public: the URL prefix the API serves saved-run blobs at (default /blobs).

    The API blob route and the URLs written into saved payloads derive from this
    single source so they always agree.
    """
    return _blob_base_url()


def _q(sql: str) -> str:
    """Translate the SQLite '?' placeholder to Postgres '%s' when on Postgres.

    Both drivers expose the same DB-API `execute(sql, params)`; only the
    placeholder style differs. Writing SQL once with '?' and rewriting keeps a
    single code path for every query.
    """
    return sql.replace("?", "%s") if _is_postgres() else sql


# ── Connection ───────────────────────────────────────────────────────────────

def _connect():
    """Open a connection to the configured DB (Postgres or SQLite).

    Both are returned configured for dict-style row access and used as
    `with _connect() as conn:` — the block commits on success. (psycopg also
    closes on exit; SQLite is reopened per call, so leaking is a non-issue.)
    """
    if _is_postgres():
        import psycopg  # noqa: PLC0415 — only needed on the Postgres path
        from psycopg.rows import dict_row  # noqa: PLC0415
        return psycopg.connect(_database_url(), row_factory=dict_row)
    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


# ── Schema (the slides' "shape of your data") ──────────────────────────────────
# A run is one saved evaluation. PK = id. `blob_url` is the FK-style pointer at the
# warehouse: it links to the blobs, it does NOT hold the image bytes. `payload_json`
# is the full evaluate-shaped result, so a reload needs no filesystem.
# The `blobs` table holds the heavy bytes (durable: see module docstring).

def _schema_statements() -> list[str]:
    if _is_postgres():
        return [
            """
            CREATE TABLE IF NOT EXISTS runs (
                id              SERIAL PRIMARY KEY,
                created_at      TEXT             NOT NULL,
                name            TEXT             NOT NULL,
                backend         TEXT,
                polygon_json    TEXT             NOT NULL,
                budget_eur      DOUBLE PRECISION,
                w_thermal       DOUBLE PRECISION,
                w_ecological    DOUBLE PRECISION,
                delta_utci_c    DOUBLE PRECISION,
                cooled_m2       DOUBLE PRECISION,
                n_trees         INTEGER,
                cost_eur        DOUBLE PRECISION,
                eur_per_m2      DOUBLE PRECISION,
                blob_url        TEXT,
                payload_json    TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS blobs (
                path     TEXT  PRIMARY KEY,
                content  BYTEA NOT NULL,
                mime     TEXT  NOT NULL
            );
            """,
        ]
    return [
        """
        CREATE TABLE IF NOT EXISTS runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at      TEXT    NOT NULL,
            name            TEXT    NOT NULL,
            backend         TEXT,
            polygon_json    TEXT    NOT NULL,
            budget_eur      REAL,
            w_thermal       REAL,
            w_ecological    REAL,
            delta_utci_c    REAL,
            cooled_m2       REAL,
            n_trees         INTEGER,
            cost_eur        REAL,
            eur_per_m2      REAL,
            blob_url        TEXT,
            payload_json    TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS blobs (
            path     TEXT PRIMARY KEY,
            content  BLOB NOT NULL,
            mime     TEXT NOT NULL
        );
        """,
    ]


def init_db() -> None:
    """Create the runs + blobs tables if they do not exist. Idempotent."""
    with _connect() as conn:
        for stmt in _schema_statements():
            conn.execute(stmt)


# ── Blob store (bytes in the DB — durable on a diskless host) ──────────────────

def _put_blob(conn, path: str, content: bytes, mime: str) -> None:
    """Upsert one blob (bytes) under `path` within an open connection."""
    if _is_postgres():
        conn.execute(
            _q("INSERT INTO blobs (path, content, mime) VALUES (?, ?, ?) "
               "ON CONFLICT (path) DO UPDATE SET content = EXCLUDED.content, "
               "mime = EXCLUDED.mime"),
            (path, content, mime),
        )
    else:
        conn.execute(
            "INSERT OR REPLACE INTO blobs (path, content, mime) VALUES (?, ?, ?)",
            (path, sqlite3.Binary(content), mime),
        )


def get_blob(path: str) -> tuple[bytes, str] | None:
    """Return (bytes, mime) for a stored blob, or None. Serves the API blob route.

    `path` is the part AFTER the BLOB_BASE_URL prefix, e.g.
    ``runs/7/utci_baseline.png`` for the URL ``/blobs/runs/7/utci_baseline.png``.
    """
    init_db()
    with _connect() as conn:
        row = conn.execute(
            _q("SELECT content, mime FROM blobs WHERE path = ?"), (path,)
        ).fetchone()
    if row is None:
        return None
    # SQLite returns bytes; psycopg returns bytes for BYTEA. bytes() normalises a
    # possible memoryview without copying semantics callers depend on.
    return bytes(row["content"]), row["mime"]


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
             and embedded in the payload so a reload can re-save it.
    params   {budget_eur, w_thermal, w_ecological, backend}.
    payload  the /api/evaluate response dict (decision/boundary/trees/bounds +
             image URLs + impervious/canopy/growth).
    eval_dir the dir the just-finished evaluate wrote its PNGs to (the live eval
             bundle). The PNG bytes are read OUT of it into this run's own blob
             rows, so a later evaluate overwriting eval_dir cannot corrupt this run.
    """
    init_db()
    eval_dir = Path(eval_dir)
    metrics = _headline_metrics(payload)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    insert_sql = (
        "INSERT INTO runs "
        "(created_at, name, backend, polygon_json, budget_eur, w_thermal, "
        " w_ecological, delta_utci_c, cooled_m2, n_trees, cost_eur, eur_per_m2, "
        " blob_url, payload_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    )
    insert_params = (
        created_at, name, params.get("backend"),
        json.dumps(polygon), params.get("budget_eur"),
        params.get("w_thermal"), params.get("w_ecological"),
        metrics["delta_utci_c"], metrics["cooled_m2"], metrics["n_trees"],
        metrics["cost_eur"], metrics["eur_per_m2"], None, None,
    )

    with _connect() as conn:
        if _is_postgres():
            cur = conn.execute(_q(insert_sql + " RETURNING id"), insert_params)
            run_id = int(cur.fetchone()["id"])
        else:
            cur = conn.execute(insert_sql, insert_params)
            run_id = int(cur.lastrowid)

        base_url = f"{_blob_base_url()}/runs/{run_id}"

        stored = dict(payload)
        stored["site_polygon_lonlat"] = polygon  # so reload can re-save
        for field, fname in _IMAGE_FIELDS.items():
            # Only store a PNG that this run actually has AND that is on disk in
            # eval_dir (mock/scalar backends produce no grid -> no PNG).
            if payload.get(field) and (eval_dir / fname).is_file():
                _put_blob(
                    conn, f"runs/{run_id}/{fname}",
                    (eval_dir / fname).read_bytes(), "image/png",
                )
                stored[field] = f"{base_url}/{fname}"
            else:
                stored[field] = None

        conn.execute(
            _q("UPDATE runs SET blob_url = ?, payload_json = ? WHERE id = ?"),
            (base_url, json.dumps(stored, ensure_ascii=False), run_id),
        )

    logger.info("saved run #%d (%s) -> %s", run_id, name, base_url)
    return run_id


def list_runs() -> list[dict[str, Any]]:
    """Return saved runs, newest first, with the headline KPIs for the list view."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, name, backend, budget_eur, "
            "       delta_utci_c, cooled_m2, n_trees, cost_eur, eur_per_m2 "
            "FROM runs ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_run(run_id: int) -> dict[str, Any] | None:
    """Return the stored evaluate-shaped payload for a run, or None if absent.

    The payload is read straight from the row (no filesystem); its image URLs
    already point at the blob route, so the frontend renders it through the same
    path as a fresh /api/evaluate.
    """
    init_db()
    with _connect() as conn:
        row = conn.execute(
            _q("SELECT payload_json FROM runs WHERE id = ?"), (run_id,)
        ).fetchone()
    if row is None or row["payload_json"] is None:
        return None
    return json.loads(row["payload_json"])
