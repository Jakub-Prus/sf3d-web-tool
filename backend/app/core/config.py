from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_SF3D_REPO_DIR = PROJECT_ROOT / "models" / "stable-fast-3d"
DEFAULT_SF3D_PYTHON_EXECUTABLE = "python"
DEFAULT_SF3D_PRETRAINED_MODEL = "stabilityai/stable-fast-3d"
DEFAULT_SF3D_RUNNER_TIMEOUT_SECONDS = 30 * 60
DEFAULT_SF3D_IMPORT_PROBE_TIMEOUT_SECONDS = 30
InferenceMode = Literal["auto", "mock", "local", "real"]
ResolvedInferenceMode = Literal["mock", "local", "real"]


class Settings(BaseSettings):
    project_name: str = Field(default="SF3D Web Tool API", alias="PROJECT_NAME")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")
    output_dir: Path = Field(default=DEFAULT_OUTPUT_DIR, alias="SF3D_OUTPUT_DIR")
    inference_mode: InferenceMode = Field(default="auto", alias="SF3D_INFERENCE_MODE")
    enable_mock_inference: bool | None = Field(default=None, alias="SF3D_ENABLE_MOCK_INFERENCE")
    max_upload_bytes: int = Field(default=DEFAULT_MAX_UPLOAD_BYTES, alias="SF3D_MAX_UPLOAD_BYTES")
    sf3d_repo_dir: Path = Field(default=DEFAULT_SF3D_REPO_DIR, alias="SF3D_REPO_DIR")
    sf3d_python_executable: str = Field(
        default=DEFAULT_SF3D_PYTHON_EXECUTABLE,
        alias="SF3D_PYTHON_EXECUTABLE",
    )
    sf3d_pretrained_model: str = Field(
        default=DEFAULT_SF3D_PRETRAINED_MODEL,
        alias="SF3D_PRETRAINED_MODEL",
    )
    sf3d_runner_timeout_seconds: int = Field(
        default=DEFAULT_SF3D_RUNNER_TIMEOUT_SECONDS,
        alias="SF3D_RUNNER_TIMEOUT_SECONDS",
    )
    sf3d_import_probe_timeout_seconds: int = Field(
        default=DEFAULT_SF3D_IMPORT_PROBE_TIMEOUT_SECONDS,
        alias="SF3D_IMPORT_PROBE_TIMEOUT_SECONDS",
    )
    sf3d_force_cpu: bool = Field(default=False, alias="SF3D_FORCE_CPU")

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    def is_sf3d_repo_ready(self) -> bool:
        return (self.sf3d_repo_dir / "run.py").is_file()

    def is_sf3d_python_ready(self) -> bool:
        python_path = Path(self.sf3d_python_executable)
        if python_path.is_absolute() or "\\" in self.sf3d_python_executable or "/" in self.sf3d_python_executable:
            return python_path.is_file()
        return True

    def resolve_inference_mode(self, *, runner_is_ready: bool | None = None) -> ResolvedInferenceMode:
        if self.inference_mode == "mock":
            return "mock"
        if self.inference_mode == "real":
            return "real"
        if self.inference_mode == "local":
            return "local"
        if self.enable_mock_inference is not None:
            return "mock" if self.enable_mock_inference else "real"
        if not self.is_sf3d_repo_ready() or not self.is_sf3d_python_ready():
            return "local"

        if runner_is_ready is None:
            from app.services.runner_diagnostics import probe_runner_import

            runner_is_ready = probe_runner_import(self).is_ready

        return "real" if runner_is_ready else "local"

    def build_runtime_warnings(self) -> list[str]:
        warnings: list[str] = []

        if self.inference_mode == "real" and not self.is_sf3d_repo_ready():
            warnings.append(
                f"Real inference mode was requested, but no SF3D runner was found at {self.sf3d_repo_dir / 'run.py'}."
            )
        if self.inference_mode in {"auto", "real"} and not self.is_sf3d_python_ready():
            warnings.append(
                f"The configured SF3D Python executable was not found at {self.sf3d_python_executable}."
            )
        if self.inference_mode == "auto" and not self.is_sf3d_repo_ready():
            warnings.append(
                "Auto mode is falling back to the local preview mesh generator because the upstream SF3D repository is not available."
            )
        if self.enable_mock_inference is not None:
            warnings.append(
                "SF3D_ENABLE_MOCK_INFERENCE is a legacy setting. Prefer SF3D_INFERENCE_MODE."
            )

        return warnings


@lru_cache
def get_settings() -> Settings:
    return Settings()
