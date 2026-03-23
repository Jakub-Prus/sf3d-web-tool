import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings

os.environ.setdefault("SF3D_OUTPUT_DIR", str(Path(__file__).resolve().parents[2] / "outputs" / "test-run"))
get_settings.cache_clear()

from app.main import app  # noqa: E402

client = TestClient(app)
PNG_HEADER_BYTES = b"\x89PNG\r\n\x1a\n"


def configure_fake_sf3d_runner(tmp_path: Path, monkeypatch) -> Path:
    repo_dir = tmp_path / "stable-fast-3d"
    repo_dir.mkdir()
    (repo_dir / "run.py").write_text(
        "\n".join(
            [
                "import argparse",
                "from pathlib import Path",
                "",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('image', nargs='+')",
                "parser.add_argument('--output-dir', required=True)",
                "parser.add_argument('--pretrained-model')",
                "parser.add_argument('--device')",
                "args, _ = parser.parse_known_args()",
                "",
                "output_dir = Path(args.output_dir) / '0'",
                "output_dir.mkdir(parents=True, exist_ok=True)",
                "(output_dir / 'mesh.glb').write_bytes(b'glb-bytes')",
                "(output_dir / 'input.png').write_bytes(Path(args.image[0]).read_bytes())",
                "print('fake sf3d runner completed')",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("SF3D_ENABLE_MOCK_INFERENCE", "false")
    monkeypatch.setenv("SF3D_REPO_DIR", str(repo_dir))
    monkeypatch.setenv("SF3D_PYTHON_EXECUTABLE", sys.executable)
    monkeypatch.setenv("SF3D_OUTPUT_DIR", str(tmp_path / "outputs"))
    get_settings.cache_clear()
    return repo_dir


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


def test_generation_endpoint_runs_official_runner_when_mock_disabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_fake_sf3d_runner(tmp_path, monkeypatch)

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "false",
            "auto_crop": "false",
            "normalize_size": "false",
            "export_format": "glb",
        },
        files={"image": ("sample.png", PNG_HEADER_BYTES + b"runner-image-payload", "image/png")},
    )

    get_settings.cache_clear()

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "completed"
    assert any(path.endswith("mesh.glb") for path in payload["asset_files"])
    assert any("Official SF3D runner executed" in note for note in payload["notes"])


def test_generation_endpoint_returns_zip_archive_in_real_runner_mode(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_fake_sf3d_runner(tmp_path, monkeypatch)

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "true",
            "auto_crop": "true",
            "normalize_size": "true",
            "export_format": "zip",
        },
        files={"image": ("sample.png", PNG_HEADER_BYTES + b"runner-image-payload", "image/png")},
    )

    get_settings.cache_clear()

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["export_format"] == "zip"
    assert payload["asset_files"][0].endswith("generated.zip")
    assert any(path.endswith("mesh.glb") for path in payload["asset_files"])


def test_generation_endpoint_rejects_obj_export_in_real_runner_mode(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_fake_sf3d_runner(tmp_path, monkeypatch)

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "true",
            "auto_crop": "true",
            "normalize_size": "true",
            "export_format": "obj",
        },
        files={"image": ("sample.png", PNG_HEADER_BYTES + b"runner-image-payload", "image/png")},
    )

    get_settings.cache_clear()

    assert response.status_code == 400
    assert "GLB output only" in response.json()["detail"]
