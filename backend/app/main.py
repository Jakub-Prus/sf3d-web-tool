from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.generation import router as generation_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description="Backend scaffold for the SF3D Web Tool project.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(generation_router, prefix=settings.api_prefix)


@app.on_event("startup")
def ensure_output_directory() -> None:
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
