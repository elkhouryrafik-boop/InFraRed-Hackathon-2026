"""Tests for coolspend.store — the "make it remember" persistence layer.

Verifies the slides' Exercise-A contract: metadata lives in a SQLite row, the
heavy heatmap files live in a blob dir, and the row stores only the URL — never
the bytes. Plus the save -> list -> get round-trip the save/load feature needs.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from coolspend import store


@pytest.fixture()
def temp_store(tmp_path, monkeypatch):
    """Point the store at a temp SQLite db + temp blob dir for the test."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("BLOB_DIR", str(tmp_path / "blobs"))
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


def test_blob_stores_link_not_bytes(temp_store):
    """The DB row holds a URL; the PNG bytes live only on disk in the blob dir."""
    eval_dir = _fake_eval_dir(temp_store)
    run_id = store.save_run(
        name="bytes check",
        polygon=[[0, 0], [0, 1], [1, 1], [0, 0]],
        params={"budget_eur": 50000.0, "backend": "cached"},
        payload=_payload(),
        eval_dir=eval_dir,
    )

    # The PNG was copied OUT into the run's own blob dir...
    blob_png = temp_store / "blobs" / "runs" / str(run_id) / "utci_baseline.png"
    assert blob_png.is_file()
    assert blob_png.read_bytes() == b"\x89PNG-baseline-bytes"

    # ...and the raw DB file does NOT contain those PNG bytes (only a link).
    db_bytes = (temp_store / "test.db").read_bytes()
    assert b"PNG-baseline-bytes" not in db_bytes
    assert f"/blobs/runs/{run_id}".encode() in db_bytes  # the link IS stored


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


def test_server_db_url_not_implemented(tmp_path, monkeypatch):
    """The Postgres seam is declared but fails loudly rather than silently faking."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user@host/db")
    with pytest.raises(NotImplementedError):
        store.init_db()
