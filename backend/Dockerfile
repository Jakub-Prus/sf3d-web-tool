FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/data/huggingface

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        ninja-build \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend /app/backend

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --index-url https://download.pytorch.org/whl/cpu torch \
    && python -m pip install -e /app/backend

RUN git clone --depth 1 https://github.com/Stability-AI/stable-fast-3d.git /opt/stable-fast-3d

RUN python -m pip install \
        einops==0.7.0 \
        jaxtyping==0.2.31 \
        omegaconf==2.3.0 \
        transformers==4.42.3 \
        open_clip_torch==2.24.0 \
        trimesh==4.4.1 \
        numpy==1.26.4 \
        huggingface-hub==0.23.4 \
        rembg==2.0.57 \
        pynanoinstantmeshes==0.0.3 \
    && python -m pip install /opt/stable-fast-3d/texture_baker /opt/stable-fast-3d/uv_unwrapper

RUN python - <<'PY'
from pathlib import Path

mesh_path = Path("/opt/stable-fast-3d/sf3d/models/mesh.py")
source = mesh_path.read_text(encoding="utf-8")
source = source.replace("import gpytoolbox", "")
source = source.replace("import pynanoinstantmeshes", "")
source = source.replace(
    "        v, f = gpytoolbox.remesh_botsch(",
    "        import gpytoolbox\n\n        v, f = gpytoolbox.remesh_botsch(",
)
source = source.replace(
    "        vertices, faces = pynanoinstantmeshes.remesh(",
    "        import pynanoinstantmeshes\n\n        vertices, faces = pynanoinstantmeshes.remesh(",
)
mesh_path.write_text(source, encoding="utf-8")
PY

ENV PROJECT_NAME="SF3D Web Tool API" \
    API_PREFIX=/api \
    FRONTEND_ORIGIN=http://localhost:3000 \
    SF3D_INFERENCE_MODE=real \
    SF3D_REPO_DIR=/opt/stable-fast-3d \
    SF3D_PYTHON_EXECUTABLE=python \
    SF3D_IMPORT_PROBE_TIMEOUT_SECONDS=30 \
    SF3D_FORCE_CPU=true \
    SF3D_OUTPUT_DIR=/app/outputs

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
