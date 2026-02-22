"""Integration tests for the reader API."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app

client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_get_missing_scheme():
    resp = client.get("/example.com")
    assert resp.status_code == 400


def test_get_ssrf_blocked():
    resp = client.get("/http://127.0.0.1/")
    assert resp.status_code == 400


def test_post_missing_url():
    resp = client.post("/", json={})
    assert resp.status_code == 422  # validation error


@patch("app.api.routes_reader._process_url", new_callable=AsyncMock)
def test_get_returns_markdown(mock_process):
    mock_process.return_value = {
        "url": "https://example.com",
        "title": "Example",
        "content": "# Hello",
        "meta": {"from_cache": False, "elapsed_ms": 10, "engine": "test", "accept": "text/markdown", "respond_with": "markdown"},
    }
    resp = client.get("/https://example.com")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers["content-type"]
    assert "Example" in resp.text


@patch("app.api.routes_reader._process_url", new_callable=AsyncMock)
def test_get_returns_json(mock_process):
    mock_process.return_value = {
        "url": "https://example.com",
        "title": "Example",
        "content": "# Hello",
        "meta": {"from_cache": False, "elapsed_ms": 10, "engine": "test", "accept": "application/json", "respond_with": "markdown"},
    }
    resp = client.get("/https://example.com", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "https://example.com"
    assert "content" in data


@patch("app.api.routes_reader._process_url", new_callable=AsyncMock)
def test_post_returns_response(mock_process):
    mock_process.return_value = {
        "url": "https://example.com/#/dashboard",
        "title": "Dashboard",
        "content": "# Dashboard",
        "meta": {"from_cache": False, "elapsed_ms": 5, "engine": "test", "accept": "application/json", "respond_with": "markdown"},
    }
    resp = client.post("/", json={"url": "https://example.com/#/dashboard"}, headers={"Accept": "application/json"})
    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data
