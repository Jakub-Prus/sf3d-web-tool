from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.models.schemas import ExportFormat, GenerationResponse
from app.services.inference import (
    SF3DInferenceService,
    SF3DRunnerError,
    UnsupportedGenerationOptionError,
)
from app.services.preprocess import PreprocessOptions

router = APIRouter(tags=["generation"])
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post("/generate-3d", response_model=GenerationResponse, status_code=status.HTTP_200_OK)
async def generate_3d(
    image: UploadFile = File(...),
    remove_background: bool = Form(True),
    auto_crop: bool = Form(True),
    normalize_size: bool = Form(True),
    export_format: ExportFormat = Form("glb"),
) -> GenerationResponse:
    settings = get_settings()

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PNG, JPEG, or WEBP uploads are accepted.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a non-empty image.",
        )

    if len(image_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded image exceeds the configured size limit.",
        )

    preprocess_options = PreprocessOptions(
        remove_background=remove_background,
        auto_crop=auto_crop,
        normalize_size=normalize_size,
    )
    service = SF3DInferenceService(settings)
    try:
        return await service.generate(image, image_bytes, preprocess_options, export_format)
    except UnsupportedGenerationOptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SF3DRunnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
