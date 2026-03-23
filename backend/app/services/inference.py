from __future__ import annotations

import asyncio
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from zipfile import ZIP_DEFLATED, ZipFile

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
OFFICIAL_RUN_SCRIPT_NAME = "run.py"
OFFICIAL_RUNNER_OUTPUT_DIRECTORY_NAME = "sf3d-runner-output"
RUNNER_STDOUT_LOG_NAME = "sf3d-runner.stdout.log"
RUNNER_STDERR_LOG_NAME = "sf3d-runner.stderr.log"
GENERATED_ZIP_NAME = "generated.zip"
OFFICIAL_OUTPUT_SUBDIRECTORY = "0"
OFFICIAL_OUTPUT_MESH_NAME = "mesh.glb"


class UnsupportedGenerationOptionError(ValueError):
    pass


class SF3DRunnerError(RuntimeError):
    pass


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
        started_at = perf_counter()
        job_id, job_dir = create_job_directory(self._settings.output_dir)
        input_filename = sanitize_filename(image.filename or "upload.png")
        input_path = write_binary_file(job_dir / INPUT_DIRECTORY_NAME / input_filename, image_bytes)

        preprocessing_steps = build_preprocessing_steps(preprocess_options)
        if self._settings.enable_mock_inference:
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

        return await self._run_official_inference(
            job_id=job_id,
            job_dir=job_dir,
            input_path=input_path,
            preprocess_options=preprocess_options,
            preprocessing_steps=preprocessing_steps,
            export_format=export_format,
            started_at=started_at,
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

    async def _run_official_inference(
        self,
        job_id: str,
        job_dir: Path,
        input_path: Path,
        preprocess_options: PreprocessOptions,
        preprocessing_steps: list[str],
        export_format: str,
        started_at: float,
    ) -> GenerationResponse:
        if export_format == "obj":
            raise UnsupportedGenerationOptionError(
                "The official SF3D runner currently exports GLB output only. Use glb or zip."
            )

        run_script_path = self._settings.sf3d_repo_dir / OFFICIAL_RUN_SCRIPT_NAME
        if not run_script_path.is_file():
            raise SF3DRunnerError(
                f"Official SF3D runner was not found at {run_script_path}. Clone the repository into models/stable-fast-3d first."
            )

        artifact_dir = job_dir / ARTIFACT_DIRECTORY_NAME
        runner_output_dir = artifact_dir / OFFICIAL_RUNNER_OUTPUT_DIRECTORY_NAME
        stdout_log_path = job_dir / RUNNER_STDOUT_LOG_NAME
        stderr_log_path = job_dir / RUNNER_STDERR_LOG_NAME

        command = [
            self._settings.sf3d_python_executable,
            str(run_script_path),
            str(input_path),
            "--output-dir",
            str(runner_output_dir),
            "--pretrained-model",
            self._settings.sf3d_pretrained_model,
        ]
        if self._settings.sf3d_force_cpu:
            command.extend(["--device", "cpu"])

        runner_env = os.environ.copy()
        if self._settings.sf3d_force_cpu:
            runner_env["SF3D_USE_CPU"] = "1"

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(self._settings.sf3d_repo_dir),
            env=runner_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._settings.sf3d_runner_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise SF3DRunnerError(
                f"Official SF3D runner timed out after {self._settings.sf3d_runner_timeout_seconds} seconds."
            ) from exc

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        write_text_file(stdout_log_path, stdout_text)
        write_text_file(stderr_log_path, stderr_text)

        if process.returncode != 0:
            raise SF3DRunnerError(
                "Official SF3D runner failed. Check the saved stdout and stderr logs in the job directory."
            )

        mesh_path = (
            runner_output_dir / OFFICIAL_OUTPUT_SUBDIRECTORY / OFFICIAL_OUTPUT_MESH_NAME
        )
        if not mesh_path.is_file():
            raise SF3DRunnerError(
                f"Official SF3D runner finished without producing the expected mesh at {mesh_path}."
            )

        asset_paths = self._collect_output_files(runner_output_dir)
        if export_format == "zip":
            zip_path = self._write_artifact_archive(artifact_dir, runner_output_dir)
            asset_paths.insert(0, str(zip_path))

        generation_time_seconds = perf_counter() - started_at
        notes = [
            "Official SF3D runner executed via the cloned stable-fast-3d repository.",
            f"Runner stdout log written to {stdout_log_path}",
            f"Runner stderr log written to {stderr_log_path}",
        ]
        notes.extend(self._build_preprocess_notes(preprocess_options))

        metadata_path = write_json_file(
            job_dir / "metadata.json",
            {
                "job_id": job_id,
                "export_format": export_format,
                "preprocessing_steps": preprocessing_steps,
                "preprocess_options": asdict(preprocess_options),
                "source_image": str(input_path),
                "asset_files": asset_paths,
                "mock_inference": False,
                "runner_command": command,
                "runner_stdout_log": str(stdout_log_path),
                "runner_stderr_log": str(stderr_log_path),
                "sf3d_repo_dir": str(self._settings.sf3d_repo_dir),
            },
        )
        notes.append(f"Metadata written to {metadata_path}")

        return GenerationResponse(
            job_id=job_id,
            status="completed",
            export_format=export_format,
            output_directory=str(job_dir),
            generated_at=datetime.now(timezone.utc),
            input_image_path=str(input_path),
            asset_files=asset_paths,
            preprocessing_steps=preprocessing_steps,
            notes=notes,
            generation_time_seconds=generation_time_seconds,
        )

    def _collect_output_files(self, output_dir: Path) -> list[str]:
        return sorted(
            str(path)
            for path in output_dir.rglob("*")
            if path.is_file()
        )

    def _write_artifact_archive(self, artifact_dir: Path, runner_output_dir: Path) -> Path:
        zip_path = artifact_dir / GENERATED_ZIP_NAME
        with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as zip_file:
            for path in runner_output_dir.rglob("*"):
                if path.is_file():
                    zip_file.write(path, arcname=path.relative_to(artifact_dir))
        return zip_path

    def _build_preprocess_notes(self, preprocess_options: PreprocessOptions) -> list[str]:
        notes = [
            "The upstream SF3D CLI currently applies its own background removal and foreground resize during inference."
        ]
        if not preprocess_options.remove_background or not preprocess_options.auto_crop:
            notes.append(
                "Requested background-removal or auto-crop toggles are recorded in metadata, but the upstream CLI does not expose matching disable flags yet."
            )
        if not preprocess_options.normalize_size:
            notes.append(
                "Requested normalize-size=false is recorded in metadata, but the upstream CLI still resizes the foreground internally."
            )
        return notes
