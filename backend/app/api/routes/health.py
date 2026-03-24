from fastapi import APIRouter

from app.core.config import get_settings
from app.models.schemas import HealthResponse
from app.services.runner_diagnostics import probe_runner_import

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    settings = get_settings()
    runner_import_probe = probe_runner_import(settings)
    resolved_mode = settings.resolve_inference_mode(runner_is_ready=runner_import_probe.is_ready)
    runtime_warnings = settings.build_runtime_warnings()
    sf3d_repo_ready = (
        settings.is_sf3d_repo_ready()
        and settings.is_sf3d_python_ready()
        and runner_import_probe.is_ready
    )
    if runner_import_probe.warning and settings.inference_mode in {"auto", "real"}:
        runtime_warnings.append(runner_import_probe.warning)

    return HealthResponse(
        service=settings.project_name,
        status="ok",
        resolved_inference_mode=resolved_mode,
        sf3d_repo_ready=sf3d_repo_ready,
        viewer_preview_expected=resolved_mode == "local" or (resolved_mode == "real" and sf3d_repo_ready),
        warnings=runtime_warnings,
    )
