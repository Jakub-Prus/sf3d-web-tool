from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

JOB_PREFIX = "sf3d-job"
INPUT_DIRECTORY_NAME = "input"
ARTIFACT_DIRECTORY_NAME = "artifacts"
METADATA_FILE_NAME = "metadata.json"
MAX_FILE_STEM_LENGTH = 64


def create_job_directory(output_root: Path) -> tuple[str, Path]:
    job_id = f"{JOB_PREFIX}-{uuid4().hex[:12]}"
    job_dir = output_root / job_id
    (job_dir / INPUT_DIRECTORY_NAME).mkdir(parents=True, exist_ok=True)
    (job_dir / ARTIFACT_DIRECTORY_NAME).mkdir(parents=True, exist_ok=True)
    return job_id, job_dir


def sanitize_filename(filename: str) -> str:
    candidate = Path(filename or "upload.png").name
    stem = Path(candidate).stem[:MAX_FILE_STEM_LENGTH] or "upload"
    suffix = Path(candidate).suffix or ".png"
    return f"{stem}{suffix}"


def write_binary_file(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def write_text_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_json_file(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def resolve_job_file(output_root: Path, job_id: str, relative_path: str) -> Path:
    job_dir = (output_root / job_id).resolve()
    candidate = (job_dir / relative_path).resolve()
    candidate.relative_to(job_dir)
    return candidate
