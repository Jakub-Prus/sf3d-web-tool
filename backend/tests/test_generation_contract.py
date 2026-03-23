import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings

os.environ.setdefault("SF3D_OUTPUT_DIR", str(Path(__file__).resolve().parents[2] / "outputs" / "test-run"))
get_settings.cache_clear()

from app.main import app  # noqa: E402

client = TestClient(app)
PNG_HEADER_BYTES = b"\x89PNG\r\n\x1a\n"


def test_generation_endpoint_returns_manifest() -> None:
    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "true",
            "auto_crop": "true",
            "normalize_size": "false",
            "export_format": "glb",
        },
        files={"image": ("sample.png", PNG_HEADER_BYTES + b"mock-image-payload", "image/png")},
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "mocked"
    assert payload["export_format"] == "glb"
    assert payload["asset_files"]
    assert "Remove background before inference" in payload["preprocessing_steps"]
