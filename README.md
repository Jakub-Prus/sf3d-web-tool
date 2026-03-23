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
- The generation endpoint currently runs a mock contract flow:
  - saves the uploaded image
  - records preprocessing choices
  - writes placeholder metadata for the future SF3D integration
- The Next.js app includes:
  - upload form
  - generation options
  - result summary panel
  - viewer placeholder panel for the planned React Three Fiber integration

## Immediate next steps

1. Clone the official SF3D repository into [models/](c:\github\my-projects\sf3d-web-tool\models).
2. Replace the mock inference service in [backend/app/services/inference.py](c:\github\my-projects\sf3d-web-tool\backend\app\services\inference.py) with the real SF3D runner.
3. Add GLB or OBJ loading in [frontend/components/viewer-panel.tsx](c:\github\my-projects\sf3d-web-tool\frontend\components\viewer-panel.tsx).
4. Add preprocessing with Pillow or OpenCV in [backend/app/services/preprocess.py](c:\github\my-projects\sf3d-web-tool\backend\app\services\preprocess.py).

## Setup outline

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
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
