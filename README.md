# SF3D Web Tool

Web-based SF3D demo and asset processing tool scaffold for turning a single object image into an inspectable 3D asset workflow.

## Problem statement

Convert a single 2D object image into a textured 3D mesh asset using SF3D, then make the result useful through preprocessing, browser inspection, export, and optional backend deployment paths.

## Why this project matters

- Demonstrates AI model integration with a real product wrapper instead of a notebook demo.
- Shows browser-side 3D rendering and inspection workflows.
- Covers mesh, texture, metadata, and export pipeline concerns.
- Creates a foundation for graphics, simulation, BIM, medical, or asset-pipeline portfolio work.

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS, React Three Fiber, Three.js
- Backend: FastAPI, Python, PyTorch, Pillow + OpenCV preprocessing layer
- 3D processing: `trimesh`, `open3d` hooks planned in the backend service layer
- Storage: local disk first, S3-compatible storage later
- Queue: Redis plus Celery or RQ reserved for a later phase

## Repository layout

```text
sf3d-web-tool/
  backend/      FastAPI API, inference orchestration, tests
  docs/         project plan and architecture notes
  frontend/     Next.js UI and viewer scaffold
  models/       local model weights and cloned repos
  outputs/      generated artifacts
  scripts/      local setup and run helpers
```

## Current scaffold status

- A dedicated Git repository has been initialized in this folder.
- The FastAPI app exposes:
  - `GET /api/health`
  - `POST /api/generate-3d`
  - `GET /api/jobs/{job_id}/artifacts/{artifact_path}`
- The generation endpoint supports three runtime outcomes:
  - mock contract flow for scaffold and API work
  - local preview GLB generation when the official runner is unavailable
  - official `stable-fast-3d` runner execution when the upstream repo is installed and importable
- The backend now:
  - saves both the original upload and a processed input image
  - returns browser-loadable artifact URLs and download metadata
  - writes job metadata, runner logs, and artifact manifests to disk
  - applies local image normalization, OpenCV-based border-connected background matting, and alpha-based auto-cropping before inference
- The Next.js app includes:
  - upload form
  - generation options
  - estimated in-flight progress feedback while generation is running
  - result summary panel
  - React Three Fiber GLB viewer
  - download actions for generated artifacts
- The frontend now checks backend readiness on page load and explains whether preview is expected before you run generation.
- The frontend now defaults to a same-origin `/api` proxy, so deployed builds do not need browser calls to `localhost:8000`.

## Current limitations

- The official upstream SF3D CLI still produces GLB output only in this integration, so real `obj` export is rejected.
- Local background removal now uses OpenCV in Lab color space. It works best for border-connected, mostly solid-color backdrops and can still struggle with shadows, gradients, or foreground colors that closely match the background.
- The upstream CLI may still apply its own background and foreground preprocessing even after local preprocessing runs.

## Runtime modes

Fresh-clone default behavior is `SF3D_INFERENCE_MODE=auto`.

- `auto`
  - uses real inference when the official SF3D runner is present and importable
  - falls back to a local smoothed heightfield preview mesh when the official runner is unavailable
- `mock`
  - always returns a valid contract response without a real preview mesh
- `local`
  - always generates a lightweight local GLB preview mesh from the uploaded image silhouette and color-derived height cues
- `real`
  - requires the upstream SF3D runner to be present and configured
  - can return textured official outputs, including material maps written by the upstream runner

The frontend preview is expected when the backend resolves to `local` or `real` mode and the run produces a GLB.

## Supported real-inference runtimes

This repo now supports two documented real-inference setups:

- `local-gpu`
  - Windows-native
  - uses the repo `.venv`
  - official SF3D runner targets `cuda`
- `deploy-cpu`
  - Docker on a Linux VPS
  - official SF3D runner targets `cpu`
  - slower, but keeps the public deployment usable without a GPU host

## Setup outline

### Local Windows GPU backend

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e "./backend[dev]"
python -m uvicorn app.main:app --reload --port 8000 --app-dir backend
```

Install a CUDA-enabled PyTorch build into the same repo `.venv`, then verify it:

```powershell
python - <<'PY'
import torch
print(torch.__version__)
print(torch.cuda.is_available())
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0))
PY
```

If you want real local GPU execution on Windows, you also need a local CUDA toolkit and a rebuild of the upstream native extensions so `texture_baker` exposes a CUDA kernel. A CUDA-enabled PyTorch wheel alone is not enough.

Install CUDA-enabled PyTorch and the local CUDA toolkit, then run the included rebuild helper:

```powershell
python -m pip install --upgrade pip
python -m pip install --index-url https://download.pytorch.org/whl/cu128 torch torchvision torchaudio
python .\scripts\patch_windows_torch_cuda_header.py
powershell -ExecutionPolicy Bypass -File .\scripts\rebuild_sf3d_windows_cuda.ps1
```

The patch helper is idempotent. It only applies a known Windows `nvcc` compatibility patch to the PyTorch header that currently trips `C2872: 'std' ambiguous symbol` during CUDA extension builds.

To run with the default auto behavior:

1. Leave `SF3D_INFERENCE_MODE=auto`.
2. If the upstream repo is present and runnable, the backend will resolve to real mode.
3. If the upstream repo is missing or not runnable, the backend will resolve to local preview mode and the UI will still show a browser-loadable GLB.

To force the official SF3D path instead of auto/mock fallback:

1. Clone or update the upstream repo in [models/stable-fast-3d](c:\github\my-projects\sf3d-web-tool\models\stable-fast-3d).
2. Install the upstream dependencies in the environment that will execute `run.py`.
3. Request access to the gated model on Hugging Face and log in with a read token.
4. Set the backend environment variables below.

```powershell
$env:SF3D_INFERENCE_MODE="real"
$env:SF3D_REPO_DIR="c:\github\my-projects\sf3d-web-tool\models\stable-fast-3d"
$env:SF3D_PYTHON_EXECUTABLE="c:\github\my-projects\sf3d-web-tool\.venv\Scripts\python.exe"
$env:SF3D_IMPORT_PROBE_TIMEOUT_SECONDS="30"
$env:SF3D_FORCE_CPU="false"
```

Expected local GPU verification sequence:

```powershell
nvidia-smi
python - <<'PY'
from app.core.config import Settings
from app.services.runtime_diagnostics import get_runtime_diagnostics
from app.services.runner_diagnostics import probe_runner_import

settings = Settings()
print(probe_runner_import(settings))
print(get_runtime_diagnostics(settings))
PY
```

Healthy local GPU output should show:
- `probe_runner_import(...).is_ready=True`
- `cuda_available=True`
- `cuda_extension_ready=True`
- `expected_runner_device='cuda'`

Legacy support:
- `SF3D_ENABLE_MOCK_INFERENCE` is still honored when `SF3D_INFERENCE_MODE` is unset.
- New configuration should use `SF3D_INFERENCE_MODE`.

If you want a preview-capable fallback without the full upstream runtime, set:

```powershell
$env:SF3D_INFERENCE_MODE="local"
```

If you want the backend preprocessing path enabled, no extra flag is required. The backend will always:
- persist the original upload
- write a processed PNG input
- record which preprocessing steps were requested versus actually applied

Real-world expectations:
- GPU is the recommended local runtime
- CPU mode is still available for verification and deployment, but it will be much slower
- Windows support depends on the upstream repo and local PyTorch/CUDA compatibility
- the import preflight timeout can be raised if the upstream environment has slow cold-start imports

### Docker/Linux CPU deployment

The public deployment target is Docker on a Linux VPS. It uses the official SF3D runner on CPU and proxies browser `/api` traffic through the frontend container.

Requirements:
- Docker and Docker Compose
- a Hugging Face token with access to `stabilityai/stable-fast-3d`

Start the stack:

```powershell
$env:HF_TOKEN="your_hugging_face_read_token"
docker compose up --build
```

Runtime defaults in the compose stack:
- backend runs in `real` mode
- backend sets `SF3D_FORCE_CPU=true`
- frontend is exposed on port `3000`
- backend artifacts and Hugging Face cache use persistent Docker volumes

The frontend talks to the backend through its own `/api` proxy route, so the browser does not need direct access to the backend container.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Manual verification

1. Start the backend and frontend.
2. Open the app in the browser.
3. Upload a PNG, JPEG, or WEBP object image.
4. Submit one run in mock mode and confirm:
   - the request succeeds
   - the backend status banner reports mock mode
   - the inspector shows notes, preprocessing fields, and download links
   - the viewer stays in the non-mesh fallback state
5. Submit one run with `SF3D_INFERENCE_MODE=local` and confirm:
   - the request succeeds
   - the backend status banner reports local mode
   - the viewer loads a real GLB preview mesh
   - the output directory contains `mesh.glb`
6. Submit one run with `SF3D_INFERENCE_MODE=real` or `auto` plus a working SF3D repo and confirm:
   - the request succeeds
   - the backend status banner reports real mode
   - the backend status banner shows the expected runner device (`CUDA` locally or `CPU` in Docker deploy)
   - the backend status banner shows whether the CUDA extension is ready
   - on Windows local GPU, `sf3d-runner.stdout.log` includes `Device used:  cuda`
   - the viewer loads a GLB scene
   - artifact download links open backend-served files
   - the processed input image, metadata, and upstream runner outputs are present in the job output directory
   - the runner notes mention the target device used for that job

## Planning docs

- Detailed execution plan: [docs/PROJECT_PLAN.md](c:\github\my-projects\sf3d-web-tool\docs\PROJECT_PLAN.md)
- Runtime behavior and fallback notes: [docs/RUNTIME_MODES.md](c:\github\my-projects\sf3d-web-tool\docs\RUNTIME_MODES.md)

## Demo goals for the finished product

- Upload a single object image
- Optionally remove the background and normalize framing
- Run SF3D inference through the backend
- Inspect the generated asset in the browser
- Export the result in useful formats
- Extend with cleanup tools, batch jobs, or deployment support
