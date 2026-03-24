import os
import sys
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
    assert response.json()["resolved_inference_mode"] in {"mock", "local", "real"}


def test_lifespan_creates_output_directory(tmp_path: Path, monkeypatch) -> None:
    target_output_dir = tmp_path / "created-on-startup"
    monkeypatch.setenv("SF3D_OUTPUT_DIR", str(target_output_dir))
    get_settings.cache_clear()

    with TestClient(app) as test_client:
        response = test_client.get("/api/health")

    get_settings.cache_clear()

    assert response.status_code == 200
    assert target_output_dir.is_dir()


def test_health_endpoint_reports_auto_local_preview_when_repo_missing(tmp_path: Path, monkeypatch) -> None:
    missing_repo = tmp_path / "missing-sf3d"
    monkeypatch.setenv("SF3D_INFERENCE_MODE", "auto")
    monkeypatch.delenv("SF3D_ENABLE_MOCK_INFERENCE", raising=False)
    monkeypatch.setenv("SF3D_REPO_DIR", str(missing_repo))
    get_settings.cache_clear()

    response = client.get("/api/health")

    get_settings.cache_clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["resolved_inference_mode"] == "local"
    assert payload["sf3d_repo_ready"] is False
    assert payload["viewer_preview_expected"] is True
    assert payload["warnings"]


def test_health_endpoint_reports_auto_real_when_repo_exists(tmp_path: Path, monkeypatch) -> None:
    repo_dir = tmp_path / "stable-fast-3d"
    repo_dir.mkdir()
    (repo_dir / "run.py").write_text("print('ready')", encoding="utf-8")

    monkeypatch.setenv("SF3D_INFERENCE_MODE", "auto")
    monkeypatch.delenv("SF3D_ENABLE_MOCK_INFERENCE", raising=False)
    monkeypatch.setenv("SF3D_REPO_DIR", str(repo_dir))
    get_settings.cache_clear()

    response = client.get("/api/health")

    get_settings.cache_clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["resolved_inference_mode"] == "real"
    assert payload["sf3d_repo_ready"] is True
    assert payload["viewer_preview_expected"] is True


def test_health_endpoint_reports_auto_local_preview_when_runner_import_preflight_fails(
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
    get_settings.cache_clear()

    response = client.get("/api/health")

    get_settings.cache_clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["resolved_inference_mode"] == "local"
    assert payload["sf3d_repo_ready"] is False
    assert payload["viewer_preview_expected"] is True
    assert any("import preflight check" in warning for warning in payload["warnings"])
    assert any("definitely_missing_sf3d_dependency" in warning for warning in payload["warnings"])


def test_health_endpoint_warns_when_python_executable_is_missing(tmp_path: Path, monkeypatch) -> None:
    repo_dir = tmp_path / "stable-fast-3d"
    repo_dir.mkdir()
    (repo_dir / "run.py").write_text("print('ready')", encoding="utf-8")

    monkeypatch.setenv("SF3D_INFERENCE_MODE", "real")
    monkeypatch.setenv("SF3D_REPO_DIR", str(repo_dir))
    monkeypatch.setenv("SF3D_PYTHON_EXECUTABLE", str(tmp_path / "missing-python.exe"))
    get_settings.cache_clear()

    response = client.get("/api/health")

    get_settings.cache_clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["resolved_inference_mode"] == "real"
    assert payload["sf3d_repo_ready"] is False
    assert payload["viewer_preview_expected"] is False
    assert any("Python executable was not found" in warning for warning in payload["warnings"])


def test_health_endpoint_warns_when_runner_import_preflight_fails(tmp_path: Path, monkeypatch) -> None:
    repo_dir = tmp_path / "stable-fast-3d"
    repo_dir.mkdir()
    (repo_dir / "run.py").write_text("import definitely_missing_sf3d_dependency", encoding="utf-8")

    monkeypatch.setenv("SF3D_INFERENCE_MODE", "real")
    monkeypatch.setenv("SF3D_REPO_DIR", str(repo_dir))
    get_settings.cache_clear()

    response = client.get("/api/health")

    get_settings.cache_clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["resolved_inference_mode"] == "real"
    assert payload["sf3d_repo_ready"] is False
    assert payload["viewer_preview_expected"] is False
    assert any("import preflight check" in warning for warning in payload["warnings"])
    assert any("definitely_missing_sf3d_dependency" in warning for warning in payload["warnings"])


def test_health_endpoint_respects_configured_import_probe_timeout(tmp_path: Path, monkeypatch) -> None:
    repo_dir = tmp_path / "stable-fast-3d"
    repo_dir.mkdir()
    (repo_dir / "run.py").write_text(
        "\n".join(
            [
                "import time",
                "time.sleep(2)",
                "print('ready')",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("SF3D_INFERENCE_MODE", "auto")
    monkeypatch.delenv("SF3D_ENABLE_MOCK_INFERENCE", raising=False)
    monkeypatch.setenv("SF3D_REPO_DIR", str(repo_dir))
    monkeypatch.setenv("SF3D_PYTHON_EXECUTABLE", sys.executable)
    monkeypatch.setenv("SF3D_IMPORT_PROBE_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()

    response = client.get("/api/health")

    get_settings.cache_clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["resolved_inference_mode"] == "local"
    assert payload["sf3d_repo_ready"] is False
    assert any("timed out after 1 seconds" in warning for warning in payload["warnings"])
