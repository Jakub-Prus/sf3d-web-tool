from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.services.storage import resolve_job_file

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}/artifacts/{artifact_path:path}")
async def get_job_artifact(job_id: str, artifact_path: str) -> FileResponse:
    settings = get_settings()

    try:
        file_path = resolve_job_file(settings.output_dir, job_id, artifact_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid artifact path.") from exc

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found.")

    return FileResponse(file_path)
