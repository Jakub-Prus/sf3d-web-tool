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
- Backend: FastAPI, Python, PyTorch, Pillow/OpenCV-ready preprocessing layer
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
- The FastAPI app exposes `GET /api/health` and `POST /api/generate-3d`.
- The generation endpoint supports two paths:
  - default mock contract flow for local scaffold work
  - official `stable-fast-3d` runner execution when mock mode is disabled and the upstream repo is installed
- The mock flow currently:
  - saves the uploaded image
  - records preprocessing choices
  - writes placeholder metadata for the future SF3D integration
- The Next.js app includes:
  - upload form
  - generation options
  - result summary panel
  - viewer placeholder panel for the planned React Three Fiber integration

## Immediate next steps

1. Install the upstream `stable-fast-3d` Python dependencies and Hugging Face access in [models/stable-fast-3d](c:\github\my-projects\sf3d-web-tool\models\stable-fast-3d).
2. Disable mock mode and validate backend inference end to end through [backend/app/services/inference.py](c:\github\my-projects\sf3d-web-tool\backend\app\services\inference.py).
3. Add GLB loading in [frontend/components/viewer-panel.tsx](c:\github\my-projects\sf3d-web-tool\frontend\components\viewer-panel.tsx).
4. Add first-class preprocessing with Pillow or OpenCV in [backend/app/services/preprocess.py](c:\github\my-projects\sf3d-web-tool\backend\app\services\preprocess.py).

## Setup outline

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

To run the official SF3D path instead of the mock contract, install the upstream repo dependencies under [models/stable-fast-3d](c:\github\my-projects\sf3d-web-tool\models\stable-fast-3d), then set:

```powershell
$env:SF3D_ENABLE_MOCK_INFERENCE="false"
$env:SF3D_REPO_DIR="c:\github\my-projects\sf3d-web-tool\models\stable-fast-3d"
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Planning docs

- Detailed execution plan: [docs/PROJECT_PLAN.md](c:\github\my-projects\sf3d-web-tool\docs\PROJECT_PLAN.md)

## Demo goals for the finished product

- Upload a single object image
- Optionally remove the background and normalize framing
- Run SF3D inference through the backend
- Inspect the generated asset in the browser
- Export the result in useful formats
- Extend with cleanup tools, batch jobs, or deployment support
