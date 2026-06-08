"""Tests for coolspend.store — the "make it remember" persistence layer.

Verifies the slides' Exercise-A contract: metadata lives in a row, the heavy
heatmap bytes live in the blob store, and the metadata row holds only the URL —
never the image bytes. Plus the save -> list -> get round-trip the save/load
feature needs, and the dual SQLite/Postgres dialect routing.

Durability change from the first MVP: the heatmap bytes now live IN the database
(a `blobs` table), not on the local filesystem — a free-tier host has no persistent
disk, so file-based blobs would not survive a redeploy. These tests run on SQLite;
the Postgres code path is asserted by dialect/placeholder routing (no live server).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from coolspend import store


@pytest.fixture()
def temp_store(tmp_path, monkeypatch):
    """Point the store at a temp SQLite db for the test."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("BLOB_BASE_URL", "/blobs")
    return tmp_path


def _fake_eval_dir(tmp_path: Path) -> Path:
    """An eval bundle dir with two heatmap PNGs, as evaluate would have written."""
    d = tmp_path / "eval_bundle"
    d.mkdir()
    (d / "utci_baseline.png").write_bytes(b"\x89PNG-baseline-bytes")
    (d / "utci_intervention.png").write_bytes(b"\x89PNG-intervention-bytes")
    return d


def _payload() -> dict:
    """A minimal evaluate-shaped payload (rank-1 config carries the headline KPIs)."""
    return {
        "decision": {
            "headline": "Plaça test — measured cooling",
            "backend": "cached",
            "configurations": [
                {
                    "rank": 1,
                    "tree_count": 18,
                    "cost_eur": 142000.0,
                    "cooled_footprint_m2": 3940.0,
                    "eur_per_m2": 36.0,
                    "delta_utci_c": -1.8,
                }
            ],
        },
        "boundary": {"type": "FeatureCollection", "features": []},
        "trees": {"type": "FeatureCollection", "features": []},
        "bounds": {"west": 2.16, "south": 41.38, "east": 2.17, "north": 41.39},
        "baselineImageUrl": "/eval_bundle/utci_baseline.png",
        "interventionImageUrl": "/eval_bundle/utci_intervention.png",
    }


def test_save_list_get_roundtrip(temp_store):
    eval_dir = _fake_eval_dir(temp_store)
    polygon = [[2.16, 41.38], [2.17, 41.38], [2.17, 41.39], [2.16, 41.38]]

    run_id = store.save_run(
        name="My plaza run",
        polygon=polygon,
        params={"budget_eur": 200000.0, "w_thermal": 0.6, "w_ecological": 0.4, "backend": "cached"},
        payload=_payload(),
        eval_dir=eval_dir,
    )
    assert isinstance(run_id, int) and run_id > 0

    # list_runs surfaces the denormalised headline KPIs for the gallery.
    runs = store.list_runs()
    assert len(runs) == 1
    row = runs[0]
    assert row["id"] == run_id
    assert row["name"] == "My plaza run"
    assert row["n_trees"] == 18
    assert row["cost_eur"] == 142000.0
    assert row["delta_utci_c"] == -1.8
    assert row["eur_per_m2"] == 36.0

    # get_run reconstructs an evaluate-shaped payload, with image URLs rewritten
    # to the blob store and the polygon embedded for re-save.
    got = store.get_run(run_id)
    assert got is not None
    assert got["baselineImageUrl"] == f"/blobs/runs/{run_id}/utci_baseline.png"
    assert got["interventionImageUrl"] == f"/blobs/runs/{run_id}/utci_intervention.png"
    assert got["site_polygon_lonlat"] == polygon
    assert got["decision"]["configurations"][0]["tree_count"] == 18


def test_blob_bytes_durable_in_db_link_in_row(temp_store):
    """Heatmap bytes live in the DB blob store (durable on a diskless host) and are
    retrievable by their URL path; the queryable metadata row holds only the link."""
    eval_dir = _fake_eval_dir(temp_store)
    run_id = store.save_run(
        name="bytes check",
        polygon=[[0, 0], [0, 1], [1, 1], [0, 0]],
        params={"budget_eur": 50000.0, "backend": "cached"},
        payload=_payload(),
        eval_dir=eval_dir,
    )

    # The PNG bytes round-trip through the blob store under their URL path...
    blob = store.get_blob(f"runs/{run_id}/utci_baseline.png")
    assert blob is not None
    content, mime = blob
    assert content == b"\x89PNG-baseline-bytes"
    assert mime == "image/png"

    # ...the queryable metadata row (list view) carries no image bytes, only KPIs...
    row = store.list_runs()[0]
    assert b"PNG-baseline-bytes" not in json.dumps(row).encode()

    # ...and the reloaded payload references the blob by URL (the slides' "just a link").
    got = store.get_run(run_id)
    assert got["baselineImageUrl"] == f"/blobs/runs/{run_id}/utci_baseline.png"


def test_get_blob_missing_returns_none(temp_store):
    store.init_db()
    assert store.get_blob("runs/123/nope.png") is None


def test_get_missing_run_returns_none(temp_store):
    store.init_db()
    assert store.get_run(99999) is None


def test_save_without_pngs_skips_images(temp_store, tmp_path):
    """A mock/scalar run has no heatmap PNGs — save must not fail, URLs are null."""
    empty_eval = tmp_path / "empty_eval"
    empty_eval.mkdir()
    payload = _payload()
    payload["baselineImageUrl"] = None
    payload["interventionImageUrl"] = None

    run_id = store.save_run(
        name="mock run",
        polygon=[[0, 0], [0, 1], [1, 1], [0, 0]],
        params={"budget_eur": 50000.0, "backend": "mock"},
        payload=payload,
        eval_dir=empty_eval,
    )
    got = store.get_run(run_id)
    assert got["baselineImageUrl"] is None
    assert got["interventionImageUrl"] is None
    # No blob was written for a run with no PNGs.
    assert store.get_blob(f"runs/{run_id}/utci_baseline.png") is None


def test_postgres_dialect_routing(monkeypatch):
    """The Postgres seam is now wired (not a NotImplementedError stub): a postgres://
    URL switches the dialect and the SQL placeholder style. Asserted as pure routing
    so no live Postgres server is needed in CI."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user@host:5432/db")
    assert store._is_postgres() is True
    assert store._q("SELECT 1 FROM runs WHERE id = ?") == "SELECT 1 FROM runs WHERE id = %s"

    monkeypatch.setenv("DATABASE_URL", "postgres://user@host/db")  # short scheme too
    assert store._is_postgres() is True

    monkeypatch.setenv("DATABASE_URL", "sqlite:///local.db")
    assert store._is_postgres() is False
    assert store._q("WHERE id = ?") == "WHERE id = ?"
