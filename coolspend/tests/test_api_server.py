"""
Offline tests for coolspend/api_server.py (the interactive backend).

All tests run with INFRARED_BACKEND=mock so they are fully offline and fast —
they exercise the HTTP wiring, the server-side area cap, and the evaluate→bundle
contract without any network or API key.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("INFRARED_BACKEND", "mock")
    from coolspend.api_server import app
    return TestClient(app)


# A ~120 m x ~150 m polygon in the Eixample — comfortably inside the area cap.
SMALL_POLY = [[2.1660, 41.3820], [2.1680, 41.3820], [2.1680, 41.3835], [2.1660, 41.3835]]
# ~9 km x ~11 km — far over the cap.
HUGE_POLY = [[2.10, 41.30], [2.20, 41.30], [2.20, 41.40], [2.10, 41.40]]
# A few metres across — under the minimum.
TINY_POLY = [[2.1660, 41.3820], [2.16602, 41.3820], [2.16602, 41.38202], [2.1660, 41.38202]]


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["backend"] == "mock"


def test_area_cap_rejects_huge_polygon(client):
    r = client.post("/api/buildings", json={"polygon": HUGE_POLY})
    assert r.status_code == 422
    assert "too large" in r.json()["detail"]


def test_area_floor_rejects_tiny_polygon(client):
    r = client.post("/api/buildings", json={"polygon": TINY_POLY})
    assert r.status_code == 422
    assert "too small" in r.json()["detail"]


def test_buildings_offline_does_not_crash(client):
    """Under mock there is no network; the preview must degrade, not 500."""
    r = client.post("/api/buildings", json={"polygon": SMALL_POLY})
    assert r.status_code == 200
    body = r.json()
    assert body["polygon_area_m2"] > 0
    assert "context_building_count" in body
    assert body["buildings_available"] is False  # mock = no live buildings


def test_evaluate_returns_full_bundle(client):
    r = client.post("/api/evaluate", json={"polygon": SMALL_POLY, "budget_eur": 500_000})
    assert r.status_code == 200
    b = r.json()
    # Bundle contract the frontend Scene depends on.
    assert b["decision"]["headline"]
    assert len(b["decision"]["configurations"]) >= 1
    assert b["boundary"]["type"] == "FeatureCollection"
    assert b["trees"]["type"] == "FeatureCollection"
    assert "bounds" in b


def test_evaluate_rejects_bad_budget(client):
    r = client.post("/api/evaluate", json={"polygon": SMALL_POLY, "budget_eur": -5})
    assert r.status_code == 422  # pydantic gt=0 validation
