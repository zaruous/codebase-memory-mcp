"""
Integration tests for BGE Server API.
Uses httpx.AsyncClient against the actual FastAPI app (no real model loading).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import model as mdl
from main import build_app

FAKE_DIM = 4
FAKE_VEC = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)


@pytest.fixture
def client():
    app = build_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def mock_model(monkeypatch):
    """Patch model functions so tests don't require a real GPU or model download."""
    monkeypatch.setattr(mdl, "is_loaded", lambda: True)

    async def fake_embed(texts, normalize=None):
        return np.stack([FAKE_VEC] * len(texts))

    monkeypatch.setattr(mdl, "embed_texts", fake_embed)
    monkeypatch.setattr(mdl, "get_model_info", lambda: {
        "model": "BAAI/bge-m3",
        "device": "cpu",
        "precision": "float32",
        "max_length": 8192,
        "loaded": True,
        "loaded_at": 0.0,
    })


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["loaded"] is True


def test_embed_single(client):
    r = client.post("/embed", json={"text": "hello world"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["embedding"]) == FAKE_DIM
    assert data["dim"] == FAKE_DIM


def test_embed_batch(client):
    r = client.post("/embed/batch", json={"texts": ["hello", "world", "foo"]})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 3
    assert len(data["embeddings"]) == 3


def test_openai_compat_single(client):
    r = client.post("/v1/embeddings", json={"input": "hello"})
    assert r.status_code == 200
    data = r.json()
    assert data["object"] == "list"
    assert len(data["data"]) == 1
    assert data["data"][0]["object"] == "embedding"


def test_openai_compat_batch(client):
    r = client.post("/v1/embeddings", json={"input": ["a", "b"]})
    assert r.status_code == 200
    data = r.json()
    assert len(data["data"]) == 2


def test_similarity(client):
    r = client.post("/similarity", json={"text_a": "hello", "text_b": "world"})
    assert r.status_code == 200
    data = r.json()
    assert "score" in data
    assert -1.0 <= data["score"] <= 1.0


def test_search(client):
    r = client.post("/search", json={
        "query": "find user",
        "documents": ["get user by id", "create post", "delete account"],
        "top_k": 2,
    })
    assert r.status_code == 200
    data = r.json()
    assert len(data["hits"]) == 2
    assert all("score" in h for h in data["hits"])
    assert all("index" in h for h in data["hits"])


def test_embed_batch_empty_rejected(client):
    r = client.post("/embed/batch", json={"texts": []})
    assert r.status_code == 422


def test_search_top_k_clamped(client):
    docs = [f"doc {i}" for i in range(5)]
    r = client.post("/search", json={"query": "test", "documents": docs, "top_k": 100})
    assert r.status_code == 200
    assert len(r.json()["hits"]) == 5  # clamped to len(documents)
