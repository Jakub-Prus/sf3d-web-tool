from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ExportFormat = Literal["glb", "obj", "zip"]
GenerationStatus = Literal["mocked", "completed"]
ArtifactKind = Literal["input", "mesh", "archive", "log", "metadata"]
ResolvedInferenceMode = Literal["mock", "local", "real"]
RunnerDevice = Literal["cpu", "cuda"]


class HealthResponse(BaseModel):
    service: str = Field(..., description="API service name")
    status: str = Field(..., description="Current health state")
    resolved_inference_mode: ResolvedInferenceMode
    sf3d_repo_ready: bool
    viewer_preview_expected: bool
    torch_version: str | None
    cuda_available: bool
    cuda_device_name: str | None
    cuda_extension_ready: bool
    sf3d_force_cpu: bool
    expected_runner_device: RunnerDevice
    warnings: list[str]


class ArtifactDescriptor(BaseModel):
    kind: ArtifactKind
    file_name: str
    relative_path: str
    url: str


class GenerationResponse(BaseModel):
    job_id: str
    status: GenerationStatus
    export_format: ExportFormat
    output_directory: str
    generated_at: datetime
    input_image_path: str
    asset_files: list[str]
    artifacts: list[ArtifactDescriptor]
    viewer_asset_url: str | None
    download_urls: list[str]
    processed_image_url: str | None
    preprocessing_steps: list[str]
    preprocessing_applied: list[str]
    preprocessing_metadata: dict[str, Any]
    notes: list[str]
    generation_time_seconds: float
