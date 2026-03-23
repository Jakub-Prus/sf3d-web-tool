from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from fastapi import UploadFile

from app.core.config import Settings
from app.models.schemas import GenerationResponse
from app.services.preprocess import PreprocessOptions, build_preprocessing_steps
from app.services.storage import (
    ARTIFACT_DIRECTORY_NAME,
    INPUT_DIRECTORY_NAME,
    create_job_directory,
    sanitize_filename,
    write_binary_file,
    write_json_file,
    write_text_file,
)

GLB_PLACEHOLDER_NAME = "generated.glb.mock.txt"
OBJ_PLACEHOLDER_NAME = "generated.obj.mock.txt"
ZIP_PLACEHOLDER_NAME = "generated.zip.mock.txt"
TEXTURE_PLACEHOLDER_NAME = "albedo.png.mock.txt"
PREVIEW_PLACEHOLDER_NAME = "preview.txt"


class SF3DInferenceService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(
        self,
        image: UploadFile,
        image_bytes: bytes,
        preprocess_options: PreprocessOptions,
        export_format: str,
    ) -> GenerationResponse:
        if not self._settings.enable_mock_inference:
            raise NotImplementedError("Real SF3D inference integration is not wired yet.")

        started_at = perf_counter()
        job_id, job_dir = create_job_directory(self._settings.output_dir)
        input_filename = sanitize_filename(image.filename or "upload.png")
        input_path = write_binary_file(job_dir / INPUT_DIRECTORY_NAME / input_filename, image_bytes)

        preprocessing_steps = build_preprocessing_steps(preprocess_options)
        asset_files = self._create_mock_artifacts(job_dir, export_format)
        generation_time_seconds = perf_counter() - started_at

        metadata_path = write_json_file(
            job_dir / "metadata.json",
            {
                "job_id": job_id,
                "export_format": export_format,
                "preprocessing_steps": preprocessing_steps,
                "source_image": str(input_path),
                "asset_files": asset_files,
                "mock_inference": True,
            },
        )

        return GenerationResponse(
            job_id=job_id,
            status="mocked",
            export_format=export_format,
            output_directory=str(job_dir),
            generated_at=datetime.now(timezone.utc),
            input_image_path=str(input_path),
            asset_files=asset_files,
            preprocessing_steps=preprocessing_steps,
            notes=[
                "Mock inference mode is active until the official SF3D runner is connected.",
                f"Metadata written to {metadata_path}",
            ],
            generation_time_seconds=generation_time_seconds,
        )

    def _create_mock_artifacts(self, job_dir: Path, export_format: str) -> list[str]:
        artifact_dir = job_dir / ARTIFACT_DIRECTORY_NAME
        export_map = {
            "glb": GLB_PLACEHOLDER_NAME,
            "obj": OBJ_PLACEHOLDER_NAME,
            "zip": ZIP_PLACEHOLDER_NAME,
        }
        export_file_name = export_map.get(export_format, GLB_PLACEHOLDER_NAME)

        artifact_paths = [
            write_text_file(
                artifact_dir / export_file_name,
                "Placeholder export. Replace this file with real SF3D output artifacts.",
            ),
            write_text_file(
                artifact_dir / TEXTURE_PLACEHOLDER_NAME,
                "Placeholder texture note. Real material maps will be saved here later.",
            ),
            write_text_file(
                artifact_dir / PREVIEW_PLACEHOLDER_NAME,
                "Placeholder preview note. Hook a preview render or turntable output here.",
            ),
        ]

        return [str(path) for path in artifact_paths]
