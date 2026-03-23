from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ExportFormat = Literal["glb", "obj", "zip"]
GenerationStatus = Literal["mocked", "completed"]


class HealthResponse(BaseModel):
    service: str = Field(..., description="API service name")
    status: str = Field(..., description="Current health state")


class GenerationResponse(BaseModel):
    job_id: str
    status: GenerationStatus
    export_format: ExportFormat
    output_directory: str
    generated_at: datetime
    input_image_path: str
    asset_files: list[str]
    preprocessing_steps: list[str]
    notes: list[str]
    generation_time_seconds: float
