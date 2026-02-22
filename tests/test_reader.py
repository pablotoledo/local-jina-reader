from unittest.mock import patch, AsyncMock

MOCK = {
    "url": "https://example.com",
    "title": "Example Domain",
    "content": "# Example\n\nThis domain is for illustrative examples.",
    "usage": {"tokens": 12},
    "cached": False,
    "fetched_at": "2026-02-22T10:00:00+00:00",
}

with patch("app.services.ml_engine.load_model", return_value=None):
    from app.main import app

from fastapi.testclient import TestClient

client = TestClient(app)


@patch("app.routers.reader.read_url", new_callable=AsyncMock, return_value=MOCK)
def test_markdown(mock_read):
    r = client.get("/r/https://example.com")
    assert r.status_code == 200
    assert "Example Domain" in r.text


@patch("app.routers.reader.read_url", new_callable=AsyncMock, return_value=MOCK)
def test_json(mock_read):
    r = client.get("/r/https://example.com", headers={"Accept": "application/json"})
    assert r.status_code == 200
    assert r.json()["title"] == "Example Domain"
