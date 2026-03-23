import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings

os.environ.setdefault("SF3D_OUTPUT_DIR", str(Path(__file__).resolve().parents[2] / "outputs" / "test-run"))
get_settings.cache_clear()

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
