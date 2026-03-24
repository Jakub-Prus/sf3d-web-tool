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
- The generation endpoint supports two paths:
  - default mock contract flow for local scaffold work
  - official `stable-fast-3d` runner execution when mock mode is disabled and the upstream repo is installed
- The backend now:
  - saves both the original upload and a processed input image
  - returns browser-loadable artifact URLs and download metadata
  - writes job metadata, runner logs, and artifact manifests to disk
  - applies local image normalization, OpenCV-based border-connected background matting, and alpha-based auto-cropping before inference
- The Next.js app includes:
  - upload form
  - generation options
  - result summary panel
  - React Three Fiber GLB viewer
  - download actions for generated artifacts
- The frontend now checks backend readiness on page load and explains whether preview is expected before you run generation.

## Current limitations

- The official upstream SF3D CLI still produces GLB output only in this integration, so real `obj` export is rejected.
- Local background removal now uses OpenCV in Lab color space. It works best for border-connected, mostly solid-color backdrops and can still struggle with shadows, gradients, or foreground colors that closely match the background.
- The upstream CLI may still apply its own background and foreground preprocessing even after local preprocessing runs.

## Runtime modes

Fresh-clone default behavior is `SF3D_INFERENCE_MODE=auto`.

- `auto`
  - uses real inference when the official SF3D runner is present and importable
  - falls back to a local silhouette-extrusion preview mesh when the official runner is unavailable
- `mock`
  - always returns a valid contract response without a real preview mesh
- `local`
  - always generates a lightweight local GLB preview mesh from the uploaded image silhouette
- `real`
  - requires the upstream SF3D runner to be present and configured

The frontend preview is expected when the backend resolves to `local` or `real` mode and the run produces a GLB.

## Setup outline

### Backend

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e "./backend[dev]"
python -m uvicorn app.main:app --reload --port 8000 --app-dir backend
```

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
# Optional when no compatible GPU is available:
$env:SF3D_FORCE_CPU="true"
```

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
- GPU is preferred for usable inference speed
- CPU mode is available for verification, but it will be much slower
- Windows support depends on the upstream repo and local PyTorch/CUDA compatibility

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
5. Submit one run with `SF3D_INFERENCE_MODE=real` or `auto` plus a working SF3D repo and confirm:
   - the request succeeds
   - the backend status banner reports real mode
   - the viewer loads a GLB scene
   - artifact download links open backend-served files
   - the processed input image and metadata are present in the job output directory

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
