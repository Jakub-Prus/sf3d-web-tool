from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class Settings(BaseSettings):
    project_name: str = Field(default="SF3D Web Tool API", alias="PROJECT_NAME")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")
    output_dir: Path = Field(default=DEFAULT_OUTPUT_DIR, alias="SF3D_OUTPUT_DIR")
    enable_mock_inference: bool = Field(default=True, alias="SF3D_ENABLE_MOCK_INFERENCE")
    max_upload_bytes: int = Field(default=DEFAULT_MAX_UPLOAD_BYTES, alias="SF3D_MAX_UPLOAD_BYTES")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
