from unittest.mock import patch

with patch("app.services.ml_engine.load_model", return_value=None):
    from app.main import app

from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
