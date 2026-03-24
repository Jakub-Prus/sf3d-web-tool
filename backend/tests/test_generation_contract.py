import os
import sys
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
import trimesh

from app.core.config import get_settings

os.environ.setdefault("SF3D_OUTPUT_DIR", str(Path(__file__).resolve().parents[2] / "outputs" / "test-run"))
get_settings.cache_clear()

from app.main import app  # noqa: E402

client = TestClient(app)


def create_png_bytes(*, transparent: bool = False) -> bytes:
    image = Image.new("RGBA", (8, 8), (255, 0, 0, 255))
    if transparent:
        image.putpixel((0, 0), (0, 0, 0, 0))

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def configure_fake_sf3d_runner(tmp_path: Path, monkeypatch) -> Path:
    repo_dir = tmp_path / "stable-fast-3d"
    repo_dir.mkdir()
    (repo_dir / "run.py").write_text(
        "\n".join(
            [
                "import argparse",
                "from pathlib import Path",
                "",
                "def main():",
                "    parser = argparse.ArgumentParser()",
                "    parser.add_argument('image', nargs='+')",
                "    parser.add_argument('--output-dir', required=True)",
                "    parser.add_argument('--pretrained-model')",
                "    parser.add_argument('--device')",
                "    args, _ = parser.parse_known_args()",
                "",
                "    output_dir = Path(args.output_dir) / '0'",
                "    output_dir.mkdir(parents=True, exist_ok=True)",
                "    (output_dir / 'mesh.glb').write_bytes(b'glb-bytes')",
                "    (output_dir / 'input.png').write_bytes(Path(args.image[0]).read_bytes())",
                "    print('fake sf3d runner completed')",
                "",
                "if __name__ == '__main__':",
                "    main()",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("SF3D_INFERENCE_MODE", "auto")
    monkeypatch.delenv("SF3D_ENABLE_MOCK_INFERENCE", raising=False)
    monkeypatch.setenv("SF3D_REPO_DIR", str(repo_dir))
    monkeypatch.setenv("SF3D_PYTHON_EXECUTABLE", sys.executable)
    monkeypatch.setenv("SF3D_OUTPUT_DIR", str(tmp_path / "outputs"))
    get_settings.cache_clear()
    return repo_dir


def test_generation_endpoint_returns_manifest(monkeypatch) -> None:
    monkeypatch.setenv("SF3D_INFERENCE_MODE", "mock")
    monkeypatch.delenv("SF3D_ENABLE_MOCK_INFERENCE", raising=False)
    get_settings.cache_clear()

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "true",
            "auto_crop": "true",
            "normalize_size": "false",
            "export_format": "glb",
        },
        files={"image": ("sample.png", create_png_bytes(transparent=True), "image/png")},
    )

    get_settings.cache_clear()

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "mocked"
    assert payload["export_format"] == "glb"
    assert payload["asset_files"]
    assert payload["artifacts"]
    assert payload["viewer_asset_url"] is None
    assert payload["processed_image_url"]
    assert "Remove background before inference" in payload["preprocessing_steps"]
    assert any("Auto-crop" in step for step in payload["preprocessing_applied"])


def test_generation_endpoint_uses_auto_local_preview_when_repo_missing(tmp_path: Path, monkeypatch) -> None:
    missing_repo = tmp_path / "missing-sf3d"
    monkeypatch.setenv("SF3D_INFERENCE_MODE", "auto")
    monkeypatch.delenv("SF3D_ENABLE_MOCK_INFERENCE", raising=False)
    monkeypatch.setenv("SF3D_REPO_DIR", str(missing_repo))
    monkeypatch.setenv("SF3D_OUTPUT_DIR", str(tmp_path / "outputs"))
    get_settings.cache_clear()

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "false",
            "auto_crop": "false",
            "normalize_size": "false",
            "export_format": "glb",
        },
        files={"image": ("sample.png", create_png_bytes(), "image/png")},
    )

    get_settings.cache_clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "completed"
    assert payload["viewer_asset_url"]
    assert any(path.endswith("mesh.glb") for path in payload["asset_files"])
    assert any("local preview mode" in note.lower() for note in payload["notes"])


def test_generation_endpoint_uses_auto_local_preview_when_runner_import_preflight_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_dir = tmp_path / "stable-fast-3d"
    repo_dir.mkdir()
    (repo_dir / "run.py").write_text("import definitely_missing_sf3d_dependency", encoding="utf-8")

    monkeypatch.setenv("SF3D_INFERENCE_MODE", "auto")
    monkeypatch.delenv("SF3D_ENABLE_MOCK_INFERENCE", raising=False)
    monkeypatch.setenv("SF3D_REPO_DIR", str(repo_dir))
    monkeypatch.setenv("SF3D_PYTHON_EXECUTABLE", sys.executable)
    monkeypatch.setenv("SF3D_OUTPUT_DIR", str(tmp_path / "outputs"))
    get_settings.cache_clear()

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "false",
            "auto_crop": "false",
            "normalize_size": "false",
            "export_format": "glb",
        },
        files={"image": ("sample.png", create_png_bytes(), "image/png")},
    )

    get_settings.cache_clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "completed"
    assert payload["viewer_asset_url"]
    assert any("import preflight check" in note for note in payload["notes"])
    assert any("definitely_missing_sf3d_dependency" in note for note in payload["notes"])
    assert any(path.endswith("mesh.glb") for path in payload["asset_files"])


def test_generation_endpoint_runs_explicit_local_preview_mode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SF3D_INFERENCE_MODE", "local")
    monkeypatch.setenv("SF3D_OUTPUT_DIR", str(tmp_path / "outputs"))
    get_settings.cache_clear()

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "true",
            "auto_crop": "true",
            "normalize_size": "true",
            "export_format": "zip",
        },
        files={"image": ("sample.png", create_png_bytes(transparent=True), "image/png")},
    )

    get_settings.cache_clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "completed"
    assert payload["viewer_asset_url"]
    assert any(path.endswith("generated.zip") for path in payload["asset_files"])
    assert any(path.endswith("mesh.glb") for path in payload["asset_files"])
    assert any("local preview mode" in note.lower() for note in payload["notes"])


def test_local_preview_generation_writes_a_parseable_glb(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SF3D_INFERENCE_MODE", "local")
    monkeypatch.setenv("SF3D_OUTPUT_DIR", str(tmp_path / "outputs"))
    get_settings.cache_clear()

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "false",
            "auto_crop": "false",
            "normalize_size": "true",
            "export_format": "glb",
        },
        files={"image": ("sample.png", create_png_bytes(), "image/png")},
    )

    get_settings.cache_clear()

    payload = response.json()
    mesh_artifact = next(artifact for artifact in payload["artifacts"] if artifact["kind"] == "mesh")
    mesh_path = tmp_path / "outputs" / payload["job_id"] / Path(mesh_artifact["relative_path"])
    mesh_scene = trimesh.load(mesh_path, force="scene")
    geometries = list(mesh_scene.geometry.values())

    assert response.status_code == 200
    assert mesh_path.is_file()
    assert mesh_path.read_bytes()[:4] == b"glTF"
    assert geometries
    assert sum(len(geometry.vertices) for geometry in geometries) > 0
    assert sum(len(geometry.faces) for geometry in geometries) > 0


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
        files={"image": ("sample.png", create_png_bytes(), "image/png")},
    )

    get_settings.cache_clear()

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["viewer_asset_url"]
    assert any(path.endswith("mesh.glb") for path in payload["asset_files"])
    assert any(artifact["kind"] == "mesh" for artifact in payload["artifacts"])
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
        files={"image": ("sample.png", create_png_bytes(transparent=True), "image/png")},
    )

    get_settings.cache_clear()

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["export_format"] == "zip"
    assert payload["asset_files"][2].endswith("generated.zip")
    assert any(path.endswith("mesh.glb") for path in payload["asset_files"])
    assert payload["processed_image_url"]
    assert any(artifact["kind"] == "archive" for artifact in payload["artifacts"])


def test_generation_endpoint_serves_artifacts_and_blocks_traversal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_fake_sf3d_runner(tmp_path, monkeypatch)

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "false",
            "auto_crop": "false",
            "normalize_size": "true",
            "export_format": "glb",
        },
        files={"image": ("sample.png", create_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()

    mesh_artifact = next(artifact for artifact in payload["artifacts"] if artifact["kind"] == "mesh")
    artifact_response = client.get(mesh_artifact["url"])
    traversal_response = client.get(
        f"/api/jobs/{payload['job_id']}/artifacts/%2E%2E/%2E%2E/outside.txt"
    )

    get_settings.cache_clear()

    assert artifact_response.status_code == 200
    assert artifact_response.content == b"glb-bytes"
    assert traversal_response.status_code == 400


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
        files={"image": ("sample.png", create_png_bytes(), "image/png")},
    )

    get_settings.cache_clear()

    assert response.status_code == 400
    assert "GLB output only" in response.json()["detail"]


def test_generation_endpoint_rejects_obj_export_in_local_preview_mode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SF3D_INFERENCE_MODE", "local")
    monkeypatch.setenv("SF3D_OUTPUT_DIR", str(tmp_path / "outputs"))
    get_settings.cache_clear()

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "true",
            "auto_crop": "true",
            "normalize_size": "true",
            "export_format": "obj",
        },
        files={"image": ("sample.png", create_png_bytes(), "image/png")},
    )

    get_settings.cache_clear()

    assert response.status_code == 400
    assert "GLB output only" in response.json()["detail"]


def test_generation_endpoint_uses_legacy_mock_toggle_when_mode_unset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_dir = tmp_path / "stable-fast-3d"
    repo_dir.mkdir()
    (repo_dir / "run.py").write_text("print('ready')", encoding="utf-8")

    monkeypatch.delenv("SF3D_INFERENCE_MODE", raising=False)
    monkeypatch.setenv("SF3D_ENABLE_MOCK_INFERENCE", "true")
    monkeypatch.setenv("SF3D_REPO_DIR", str(repo_dir))
    monkeypatch.setenv("SF3D_OUTPUT_DIR", str(tmp_path / "outputs"))
    get_settings.cache_clear()

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "false",
            "auto_crop": "false",
            "normalize_size": "false",
            "export_format": "glb",
        },
        files={"image": ("sample.png", create_png_bytes(), "image/png")},
    )

    get_settings.cache_clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "mocked"
    assert any("legacy setting" in note.lower() for note in payload["notes"])


def test_generation_endpoint_returns_runner_setup_error_when_python_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_dir = tmp_path / "stable-fast-3d"
    repo_dir.mkdir()
    (repo_dir / "run.py").write_text("print('ready')", encoding="utf-8")

    monkeypatch.setenv("SF3D_INFERENCE_MODE", "real")
    monkeypatch.setenv("SF3D_REPO_DIR", str(repo_dir))
    monkeypatch.setenv("SF3D_PYTHON_EXECUTABLE", str(tmp_path / "missing-python.exe"))
    monkeypatch.setenv("SF3D_OUTPUT_DIR", str(tmp_path / "outputs"))
    get_settings.cache_clear()

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "false",
            "auto_crop": "false",
            "normalize_size": "false",
            "export_format": "glb",
        },
        files={"image": ("sample.png", create_png_bytes(), "image/png")},
    )

    get_settings.cache_clear()

    assert response.status_code == 500
    assert "Python executable was not found" in response.json()["detail"]


def test_generation_endpoint_surfaces_runner_failure_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_dir = tmp_path / "stable-fast-3d"
    repo_dir.mkdir()
    (repo_dir / "run.py").write_text(
        "\n".join(
            [
                "import sys",
                "sys.stderr.write(\"ModuleNotFoundError: No module named 'rembg'\\n\")",
                "raise SystemExit(1)",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("SF3D_INFERENCE_MODE", "real")
    monkeypatch.setenv("SF3D_REPO_DIR", str(repo_dir))
    monkeypatch.setenv("SF3D_PYTHON_EXECUTABLE", sys.executable)
    monkeypatch.setenv("SF3D_OUTPUT_DIR", str(tmp_path / "outputs"))
    get_settings.cache_clear()

    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "false",
            "auto_crop": "false",
            "normalize_size": "false",
            "export_format": "glb",
        },
        files={"image": ("sample.png", create_png_bytes(), "image/png")},
    )

    get_settings.cache_clear()

    assert response.status_code == 500
    assert "Official SF3D runner failed" in response.json()["detail"]
    assert "ModuleNotFoundError" in response.json()["detail"]
    assert "rembg" in response.json()["detail"]


def test_generation_endpoint_rejects_invalid_image_payload() -> None:
    response = client.post(
        "/api/generate-3d",
        data={
            "remove_background": "true",
            "auto_crop": "true",
            "normalize_size": "true",
            "export_format": "glb",
        },
        files={"image": ("sample.png", b"not-a-real-image", "image/png")},
    )

    assert response.status_code == 400
    assert "Upload a valid PNG" in response.json()["detail"]
