from __future__ import annotations

import asyncio
import os
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import quote
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import UploadFile

from app.core.config import Settings
from app.models.schemas import ArtifactDescriptor, GenerationResponse
from app.services.preprocess import (
    InvalidInputImageError,
    PreprocessOptions,
    PreprocessResult,
    preprocess_image,
)
from app.services.local_preview import generate_local_preview_mesh
from app.services.runner_diagnostics import probe_runner_import, summarize_runner_failure
from app.services.runtime_diagnostics import get_runtime_diagnostics
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
PROCESSED_INPUT_FILE_NAME = "processed-input.png"
OFFICIAL_RUN_SCRIPT_NAME = "run.py"
OFFICIAL_RUNNER_OUTPUT_DIRECTORY_NAME = "sf3d-runner-output"
RUNNER_STDOUT_LOG_NAME = "sf3d-runner.stdout.log"
RUNNER_STDERR_LOG_NAME = "sf3d-runner.stderr.log"
GENERATED_ZIP_NAME = "generated.zip"
OFFICIAL_OUTPUT_SUBDIRECTORY = "0"
OFFICIAL_OUTPUT_MESH_NAME = "mesh.glb"
LOCAL_PREVIEW_REJECTED_EXPORT_MESSAGE = (
    "The local preview mesh generator currently exports GLB output only. Use glb or zip."
)


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
        preprocess_result = preprocess_image(image_bytes, preprocess_options)
        processed_input_path = write_binary_file(
            job_dir / INPUT_DIRECTORY_NAME / PROCESSED_INPUT_FILE_NAME,
            preprocess_result.processed_bytes,
        )

        runner_import_probe = probe_runner_import(self._settings)
        resolved_mode = self._settings.resolve_inference_mode(
            runner_is_ready=runner_import_probe.is_ready
        )
        runtime_warnings = self._settings.build_runtime_warnings()
        if runner_import_probe.warning and self._settings.inference_mode == "auto":
            runtime_warnings.append(runner_import_probe.warning)

        if resolved_mode == "mock":
            asset_files = self._create_mock_artifacts(job_dir, export_format)
            metadata_path = write_json_file(
                job_dir / "metadata.json",
                {
                    "job_id": job_id,
                    "export_format": export_format,
                    "preprocessing_steps": preprocess_result.requested_steps,
                    "preprocessing_applied": preprocess_result.applied_steps,
                    "preprocessing_metadata": preprocess_result.metadata,
                    "source_image": str(input_path),
                    "processed_image": str(processed_input_path),
                    "asset_files": asset_files,
                    "mock_inference": True,
                    "resolved_inference_mode": resolved_mode,
                },
            )
            artifact_paths = [input_path, processed_input_path, *[Path(path) for path in asset_files], metadata_path]
            artifacts = self._build_artifact_descriptors(job_id, job_dir, artifact_paths)
            generation_time_seconds = perf_counter() - started_at

            return GenerationResponse(
                job_id=job_id,
                status="mocked",
                export_format=export_format,
                output_directory=str(job_dir),
                generated_at=datetime.now(timezone.utc),
                input_image_path=str(input_path),
                asset_files=asset_files,
                artifacts=artifacts,
                viewer_asset_url=None,
                download_urls=self._build_download_urls(artifacts),
                processed_image_url=self._find_artifact_url(artifacts, "input", PROCESSED_INPUT_FILE_NAME),
                preprocessing_steps=preprocess_result.requested_steps,
                preprocessing_applied=preprocess_result.applied_steps,
                preprocessing_metadata=preprocess_result.metadata,
                notes=[
                    "Mock inference mode is active until the official SF3D runner is connected.",
                    *runtime_warnings,
                    *preprocess_result.notes,
                    f"Metadata written to {metadata_path}",
                ],
                generation_time_seconds=generation_time_seconds,
            )

        if resolved_mode == "local":
            return self._run_local_preview_generation(
                job_id=job_id,
                job_dir=job_dir,
                input_path=input_path,
                processed_input_path=processed_input_path,
                preprocess_options=preprocess_options,
                preprocess_result=preprocess_result,
                export_format=export_format,
                resolved_mode=resolved_mode,
                runtime_warnings=runtime_warnings,
                started_at=started_at,
            )

        return await self._run_official_inference(
            job_id=job_id,
            job_dir=job_dir,
            input_path=input_path,
            processed_input_path=processed_input_path,
            preprocess_options=preprocess_options,
            preprocess_result=preprocess_result,
            export_format=export_format,
            resolved_mode=resolved_mode,
            started_at=started_at,
        )

    def _run_local_preview_generation(
        self,
        *,
        job_id: str,
        job_dir: Path,
        input_path: Path,
        processed_input_path: Path,
        preprocess_options: PreprocessOptions,
        preprocess_result: PreprocessResult,
        export_format: str,
        resolved_mode: str,
        runtime_warnings: list[str],
        started_at: float,
    ) -> GenerationResponse:
        if export_format == "obj":
            raise UnsupportedGenerationOptionError(LOCAL_PREVIEW_REJECTED_EXPORT_MESSAGE)

        artifact_dir = job_dir / ARTIFACT_DIRECTORY_NAME
        preview_result = generate_local_preview_mesh(
            processed_image_bytes=preprocess_result.processed_bytes,
            artifact_dir=artifact_dir,
        )

        artifact_paths = [input_path, processed_input_path, preview_result.mesh_path]
        if export_format == "zip":
            zip_path = self._write_local_preview_archive(
                artifact_dir=artifact_dir,
                mesh_path=preview_result.mesh_path,
                processed_input_path=processed_input_path,
            )
            artifact_paths.insert(2, zip_path)

        metadata_path = write_json_file(
            job_dir / "metadata.json",
            {
                "job_id": job_id,
                "export_format": export_format,
                "preprocessing_steps": preprocess_result.requested_steps,
                "preprocessing_applied": preprocess_result.applied_steps,
                "preprocessing_metadata": preprocess_result.metadata,
                "preprocess_options": asdict(preprocess_options),
                "source_image": str(input_path),
                "processed_image": str(processed_input_path),
                "asset_files": [str(path) for path in artifact_paths],
                "mock_inference": False,
                "local_preview_generation": True,
                "resolved_inference_mode": resolved_mode,
            },
        )
        artifact_paths.append(metadata_path)
        artifacts = self._build_artifact_descriptors(job_id, job_dir, artifact_paths)
        generation_time_seconds = perf_counter() - started_at

        notes = [*preview_result.notes, *runtime_warnings, *preprocess_result.notes]
        notes.extend(self._build_preprocess_notes(preprocess_options, preprocess_result.applied_steps))
        notes.append(f"Metadata written to {metadata_path}")

        return GenerationResponse(
            job_id=job_id,
            status="completed",
            export_format=export_format,
            output_directory=str(job_dir),
            generated_at=datetime.now(timezone.utc),
            input_image_path=str(input_path),
            asset_files=[str(path) for path in artifact_paths],
            artifacts=artifacts,
            viewer_asset_url=self._find_artifact_url(artifacts, "mesh"),
            download_urls=self._build_download_urls(artifacts),
            processed_image_url=self._find_artifact_url(artifacts, "input", PROCESSED_INPUT_FILE_NAME),
            preprocessing_steps=preprocess_result.requested_steps,
            preprocessing_applied=preprocess_result.applied_steps,
            preprocessing_metadata=preprocess_result.metadata,
            notes=notes,
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

    async def _run_official_inference(
        self,
        job_id: str,
        job_dir: Path,
        input_path: Path,
        processed_input_path: Path,
        preprocess_options: PreprocessOptions,
        preprocess_result: PreprocessResult,
        export_format: str,
        resolved_mode: str,
        started_at: float,
    ) -> GenerationResponse:
        if export_format == "obj":
            raise UnsupportedGenerationOptionError(
                "The official SF3D runner currently exports GLB output only. Use glb or zip."
            )

        run_script_path = self._settings.sf3d_repo_dir / OFFICIAL_RUN_SCRIPT_NAME
        if not run_script_path.is_file():
            raise SF3DRunnerError(
                f"Official SF3D runner was not found at {run_script_path}. Configure mock mode or clone the repository into models/stable-fast-3d first."
            )
        if not self._settings.is_sf3d_python_ready():
            raise SF3DRunnerError(
                f"The configured SF3D Python executable was not found at {self._settings.sf3d_python_executable}."
            )

        artifact_dir = job_dir / ARTIFACT_DIRECTORY_NAME
        runner_output_dir = artifact_dir / OFFICIAL_RUNNER_OUTPUT_DIRECTORY_NAME
        stdout_log_path = job_dir / RUNNER_STDOUT_LOG_NAME
        stderr_log_path = job_dir / RUNNER_STDERR_LOG_NAME
        absolute_processed_input_path = processed_input_path.resolve()
        absolute_runner_output_dir = runner_output_dir.resolve()
        runtime_diagnostics = get_runtime_diagnostics(self._settings)

        command = [
            self._settings.sf3d_python_executable,
            str(run_script_path),
            str(absolute_processed_input_path),
            "--output-dir",
            str(absolute_runner_output_dir),
            "--pretrained-model",
            self._settings.sf3d_pretrained_model,
            "--device",
            runtime_diagnostics.expected_runner_device,
        ]

        runner_env = os.environ.copy()
        if self._settings.sf3d_force_cpu:
            runner_env["SF3D_USE_CPU"] = "1"

        try:
            completed_process = await asyncio.to_thread(
                subprocess.run,
                command,
                cwd=str(self._settings.sf3d_repo_dir),
                env=runner_env,
                capture_output=True,
                text=False,
                timeout=self._settings.sf3d_runner_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SF3DRunnerError(
                f"Official SF3D runner timed out after {self._settings.sf3d_runner_timeout_seconds} seconds."
            ) from exc
        except (OSError, ValueError, NotImplementedError) as exc:
            raise SF3DRunnerError(
                f"Failed to start the SF3D runner process with {self._settings.sf3d_python_executable}. Check the Python path and upstream environment setup."
            ) from exc

        stdout_text = completed_process.stdout.decode("utf-8", errors="replace")
        stderr_text = completed_process.stderr.decode("utf-8", errors="replace")
        write_text_file(stdout_log_path, stdout_text)
        write_text_file(stderr_log_path, stderr_text)

        if completed_process.returncode != 0:
            failure_summary = summarize_runner_failure(stdout_text, stderr_text)
            failure_message = "Official SF3D runner failed. Check the saved stdout and stderr logs in the job directory."
            if failure_summary:
                failure_message = f"{failure_message} Summary: {failure_summary}"
            raise SF3DRunnerError(
                failure_message
            )

        mesh_path = (
            runner_output_dir / OFFICIAL_OUTPUT_SUBDIRECTORY / OFFICIAL_OUTPUT_MESH_NAME
        )
        if not mesh_path.is_file():
            raise SF3DRunnerError(
                f"Official SF3D runner finished without producing the expected mesh at {mesh_path}."
            )

        artifact_paths = [input_path, processed_input_path, *self._collect_output_files(runner_output_dir)]
        if export_format == "zip":
            zip_path = self._write_artifact_archive(artifact_dir, runner_output_dir)
            artifact_paths.insert(2, zip_path)

        generation_time_seconds = perf_counter() - started_at
        notes = [
            "Official SF3D runner executed via the cloned stable-fast-3d repository.",
            (
                "Official SF3D runner target device: "
                f"{runtime_diagnostics.expected_runner_device}"
                + (
                    f" ({runtime_diagnostics.cuda_device_name})"
                    if runtime_diagnostics.expected_runner_device == "cuda" and runtime_diagnostics.cuda_device_name
                    else ""
                )
                + "."
            ),
            f"Runner stdout log written to {stdout_log_path}",
            f"Runner stderr log written to {stderr_log_path}",
        ]
        notes.extend(preprocess_result.notes)
        notes.extend(self._build_preprocess_notes(preprocess_options, preprocess_result.applied_steps))

        metadata_path = write_json_file(
            job_dir / "metadata.json",
            {
                "job_id": job_id,
                "export_format": export_format,
                "preprocessing_steps": preprocess_result.requested_steps,
                "preprocessing_applied": preprocess_result.applied_steps,
                "preprocessing_metadata": preprocess_result.metadata,
                "preprocess_options": asdict(preprocess_options),
                "source_image": str(input_path),
                "processed_image": str(processed_input_path),
                "asset_files": [str(path) for path in artifact_paths],
                "mock_inference": False,
                "resolved_inference_mode": resolved_mode,
                "runner_command": command,
                "runner_stdout_log": str(stdout_log_path),
                "runner_stderr_log": str(stderr_log_path),
                "sf3d_repo_dir": str(self._settings.sf3d_repo_dir),
            },
        )
        artifact_paths.extend([stdout_log_path, stderr_log_path, metadata_path])
        artifacts = self._build_artifact_descriptors(job_id, job_dir, artifact_paths)
        notes.append(f"Metadata written to {metadata_path}")

        return GenerationResponse(
            job_id=job_id,
            status="completed",
            export_format=export_format,
            output_directory=str(job_dir),
            generated_at=datetime.now(timezone.utc),
            input_image_path=str(input_path),
            asset_files=[str(path) for path in artifact_paths],
            artifacts=artifacts,
            viewer_asset_url=self._find_artifact_url(artifacts, "mesh"),
            download_urls=self._build_download_urls(artifacts),
            processed_image_url=self._find_artifact_url(artifacts, "input", PROCESSED_INPUT_FILE_NAME),
            preprocessing_steps=preprocess_result.requested_steps,
            preprocessing_applied=preprocess_result.applied_steps,
            preprocessing_metadata=preprocess_result.metadata,
            notes=notes,
            generation_time_seconds=generation_time_seconds,
        )

    def _collect_output_files(self, output_dir: Path) -> list[Path]:
        return sorted(
            path
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

    def _write_local_preview_archive(
        self,
        *,
        artifact_dir: Path,
        mesh_path: Path,
        processed_input_path: Path,
    ) -> Path:
        zip_path = artifact_dir / GENERATED_ZIP_NAME
        with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as zip_file:
            zip_file.write(mesh_path, arcname=mesh_path.relative_to(artifact_dir))
            zip_file.write(processed_input_path, arcname=processed_input_path.name)
        return zip_path

    def _build_preprocess_notes(
        self,
        preprocess_options: PreprocessOptions,
        applied_steps: list[str],
    ) -> list[str]:
        notes = [
            "The upstream SF3D CLI currently applies its own background removal and foreground resize during inference."
        ]
        if preprocess_options.remove_background:
            notes.append(
                "Background removal may still run upstream because the official SF3D CLI does not expose a disable flag."
            )
        if preprocess_options.auto_crop and not any("Auto-crop" in step for step in applied_steps):
            notes.append(
                "Auto-crop was requested but skipped locally because a reliable alpha silhouette was not available."
            )
        if preprocess_options.normalize_size:
            notes.append(
                "Local normalize-size preprocessing was applied before inference, but the upstream CLI may still resize the foreground internally."
            )
        return notes

    def _build_artifact_descriptors(
        self,
        job_id: str,
        job_dir: Path,
        artifact_paths: list[Path],
    ) -> list[ArtifactDescriptor]:
        descriptors: list[ArtifactDescriptor] = []
        seen_paths: set[str] = set()

        for path in artifact_paths:
            relative_path = path.relative_to(job_dir).as_posix()
            if relative_path in seen_paths:
                continue
            seen_paths.add(relative_path)

            descriptors.append(
                ArtifactDescriptor(
                    kind=self._classify_artifact_kind(path),
                    file_name=path.name,
                    relative_path=relative_path,
                    url=self._build_artifact_url(job_id, relative_path),
                )
            )

        return descriptors

    def _classify_artifact_kind(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if path.name == "metadata.json":
            return "metadata"
        if suffix == ".log":
            return "log"
        if suffix == ".zip":
            return "archive"
        if suffix == ".glb":
            return "mesh"
        return "input"

    def _build_artifact_url(self, job_id: str, relative_path: str) -> str:
        encoded_path = quote(relative_path, safe="/")
        return f"{self._settings.api_prefix}/jobs/{job_id}/artifacts/{encoded_path}"

    def _build_download_urls(self, artifacts: list[ArtifactDescriptor]) -> list[str]:
        return [
            artifact.url
            for artifact in artifacts
            if artifact.kind in {"archive", "mesh", "metadata", "input"}
        ]

    def _find_artifact_url(
        self,
        artifacts: list[ArtifactDescriptor],
        kind: str,
        file_name: str | None = None,
    ) -> str | None:
        for artifact in artifacts:
            if artifact.kind != kind:
                continue
            if file_name is not None and artifact.file_name != file_name:
                continue
            return artifact.url
        return None
