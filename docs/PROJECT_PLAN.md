# SF3D Web Tool Plan

## Project summary

- Product name: `SF3D Web Tool`
- Positioning: web-based SF3D demo and asset processing tool
- Core outcome: turn a single object image into a downloadable, inspectable 3D asset
- Primary portfolio signal:
  - AI model integration
  - 3D rendering in the browser
  - mesh and texture pipeline understanding
  - backend inference serving
  - performance and UX thinking
  - practical asset workflow design

## Product goals

- Build a full image-to-3D workflow instead of a notebook-only proof of concept.
- Expose the parts of the workflow real users care about:
  - upload
  - preprocessing
  - inference
  - viewer
  - export
  - optional cleanup
- Keep the MVP local-first so setup and debugging stay simple.
- Structure the app so later deployment, queueing, and storage upgrades do not require a rewrite.

## Non-goals for the first release

- Multi-tenant authentication
- cloud-native production hardening
- real-time collaborative editing
- automatic cost optimization for GPU inference
- mobile-first UX

## Definition of done

- A local developer can run the frontend and backend with documented steps.
- The backend accepts an uploaded image and returns a structured generation result.
- The frontend lets a user upload an image, choose preprocessing options, submit a job, and inspect result metadata.
- The repository documents architecture, scope, roadmap, and next implementation steps.
- The scaffold is organized for direct SF3D integration without major restructuring.

## Current implementation status

- Backend generation contract is implemented with artifact URLs, processed-image metadata, and a read-only artifact route.
- Frontend upload, inspector, downloads, and GLB viewer are implemented.
- Local preprocessing currently applies normalization and alpha-based auto-crop.
- Backend tests pass and frontend production build passes.
- Runtime alignment now includes three usable paths:
  - `mock` for placeholder contract testing
  - `local` for preview-capable silhouette extrusion fallback
  - `real` for the official SF3D runner when the upstream environment is ready
- The viewer now keeps a persistent canvas mounted and includes explicit context-loss recovery UI.

## Current gaps

- The official SF3D Windows environment still depends on native upstream extensions and gated model access.
- The local preview fallback is intentionally lower fidelity than the official SF3D output.
- Background removal remains requested-but-not-applied locally.

## Next fix slice

- Validate the official upstream runner on a machine with the required native toolchain.
- Improve local preview output quality without breaking the GLB contract.
- Add browser-level preview smoke coverage when the project adopts a frontend test runner.
- Continue aligning README, `.env.example`, and runtime docs with observed setup behavior.

## Architecture

### End-to-end flow

- User uploads an image in the frontend.
- Frontend sends a multipart request to the backend API.
- Backend validates the file and generation options.
- Backend preprocesses the image before inference.
- Backend runs SF3D inference.
- Backend saves artifacts and metadata to disk.
- Frontend displays generation details and loads the output asset into a browser viewer.
- User downloads the generated outputs.

### Core services

- Frontend application
  - upload workflow
  - generation settings
  - viewer and inspector UI
  - export actions
- Backend API
  - input validation
  - preprocessing orchestration
  - inference orchestration
  - artifact storage
  - metadata reporting
- Storage layer
  - local disk for uploaded files
  - local disk for generated outputs
  - optional object storage later

### Planned folder structure

- `frontend/`
  - `app/`
  - `components/`
  - `lib/`
- `backend/`
  - `app/api/routes/`
  - `app/core/`
  - `app/models/`
  - `app/services/`
  - `tests/`
- `models/`
- `outputs/`
- `scripts/`
- `docs/`

## Phase 1: working SF3D pipeline

### Goal

- Get a complete image-to-3D result running end to end on a local machine.

### Deliverable

- A local app where a user can:
  - upload a single object image
  - optionally remove the background
  - run SF3D
  - preview the generated mesh
  - download the result

### Step-by-step tasks

- Research and validate the model
  - Read the official SF3D repository.
  - Read the model card and licensing notes.
  - Capture required input formats and expected output assets.
  - Document runtime requirements, especially GPU and CUDA assumptions.
- Prepare the inference environment
  - Create a Python virtual environment for backend and model tooling.
  - Install PyTorch with the correct CUDA build.
  - Clone the SF3D repository under `models/`.
  - Run the official demo or inference script on known sample inputs.
  - Record timings, memory needs, and any failure modes.
- Build the backend contract
  - Create `POST /api/generate-3d`.
  - Accept multipart image upload and generation options.
  - Validate file type, size, and option values.
  - Return structured artifact metadata and execution notes.
- Save outputs predictably
  - Store uploaded source images.
  - Store generated mesh files.
  - Store generated texture maps and materials.
  - Store preview images or turntable renders when available.
  - Store `metadata.json` with generation settings and timings.
- Build the initial frontend
  - Add image upload UI.
  - Add preprocessing toggles.
  - Add progress and loading state.
  - Add result card with download actions.
- Document the local setup
  - Add backend install steps.
  - Add frontend install steps.
  - Add expected environment variables.
  - Add sample run instructions.

### Definition of done

- One-click or near-one-click local startup is documented.
- Three test images process successfully once the SF3D integration is in place.
- Generated outputs are saved consistently and can be downloaded.
- The README explains setup, architecture, and usage.

## Phase 2: real 3D application

### Goal

- Make the generated result inspectable and useful instead of just downloadable.

### Deliverable

- A browser UI with interactive 3D viewing and asset inspection controls.

### Step-by-step tasks

- Build the viewer
  - Use Three.js or React Three Fiber.
  - Add orbit controls.
  - Add wireframe toggle.
  - Add texture on and off toggle.
  - Add normal visualization mode.
  - Add lighting controls.
- Build the inspector
  - Show vertex count.
  - Show triangle count.
  - Show texture resolution.
  - Show generation time.
  - Show file size.
- Add comparison views
  - Show the original uploaded image.
  - Show the generated 3D preview.
  - Add a turntable-style preview when feasible.
- Add export choices
  - Export `GLB`.
  - Export `OBJ + MTL + textures`.
  - Export a ZIP with all artifacts.
- Improve failure handling
  - Add input quality tips.
  - Validate image size and centering.
  - Explain transparent background expectations.
  - Show user-friendly error states and recovery actions.

### Definition of done

- The 3D model loads in the browser.
- The user can inspect the asset and toggle visualization modes.
- Multiple export formats work from the UI.
- The app handles low-quality or invalid inputs gracefully.

## Phase 3: portfolio-grade differentiation

### Goal

- Add high-signal features that show engineering depth beyond a thin model wrapper.

### Choose 3 to 5 enhancements

- Preprocessing pipeline
  - Add background removal.
  - Add object centering.
  - Add auto-crop.
  - Add padding.
  - Add resize normalization.
- Mesh cleanup and optimization
  - Add decimation.
  - Add Laplacian smoothing.
  - Add normal recomputation.
  - Add watertightness checks.
  - Add non-manifold detection.
- Batch mode
  - Accept multiple uploads.
  - Queue jobs.
  - Compare timings.
  - Keep result history.
- Asset QA metrics
  - Compute polycount.
  - Compute bounding box dimensions.
  - Compute disconnected component count.
  - Compute texture coverage.
  - Compute generation latency.
- Turntable renderer
  - Render a short preview video or GIF from the final mesh.
- Job system
  - Add Redis and a worker queue.
  - Add background processing.
  - Add status polling.
- Cloud deployment
  - Deploy the frontend on Vercel.
  - Deploy the backend to a GPU-capable host.
  - Store outputs in S3-compatible storage.

## Technology stack

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- React Three Fiber
- Three.js

### Backend

- FastAPI
- Python
- PyTorch
- Pillow or OpenCV for preprocessing

### 3D processing

- `trimesh`
- `open3d`
- optional `pymeshlab`
- optional Blender automation scripts

### Storage and infrastructure

- local disk first
- S3-compatible storage later
- Redis plus Celery or RQ if background jobs are added

## MVP feature list

### MVP

- Upload image
- Run SF3D
- View model in browser
- Download `GLB` or `OBJ`
- Show generation time
- Apply simple preprocessing
- Maintain a clean README

### Strong v2

- Background removal toggle
- Mesh cleanup tools
- Batch processing
- Quality metrics
- Turntable preview
- Deployed demo

## Suggested execution plan

### Week 1: core integration

- Run the official SF3D repository locally.
- Test the pipeline on sample object images.
- Build the FastAPI endpoint.
- Save outputs to disk.
- Verify export files and metadata.
- Document install and run steps.

### Week 1 goal

- End-to-end inference works from the project API.

### Week 2: frontend and viewer

- Build the upload UI.
- Build the result page.
- Add the Three.js or React Three Fiber viewer.
- Add the inspector panel.
- Add error handling.
- Support file downloads.

### Week 2 goal

- The local app is usable by someone other than the author.

### Week 3: polish and differentiation

- Improve preprocessing.
- Add mesh cleanup and quality checks.
- Benchmark generation time.
- Write architecture notes.
- Record a demo video.
- Deploy if possible.

### Week 3 goal

- The project is portfolio-ready.

## README checklist for the finished version

- Problem statement
  - Explain single-image 2D to textured 3D asset conversion with SF3D.
- Why it matters
  - Mention rapid asset generation, prototyping, e-commerce, 3D content pipelines, and AR/VR visualization.
- Architecture diagram
  - Show frontend, API, preprocessing, SF3D model, storage, and viewer/export pieces.
- Demo GIF
  - Show upload, generation, and model inspection.
- Technical challenges
  - Explain preprocessing sensitivity, inconsistent outputs, browser rendering, and export cleanup.
- Future work
  - Mention comparing or swapping models such as SPAR3D later.

## Risks and mitigation

- GPU requirements may block contributors without CUDA hardware.
  - Mitigation: keep a mock mode and document cloud GPU options.
- Inference may be slow or unstable for poor inputs.
  - Mitigation: invest in preprocessing and user guidance.
- Generated meshes may require cleanup for browser viewing.
  - Mitigation: add validation, repair, and export normalization steps.
- Asset storage can grow quickly.
  - Mitigation: enforce retention policies and optional object storage later.

## Current scaffold deliverables

- Frontend upload and result shell
- Backend API skeleton with mock generation contract
- Local output storage structure
- Markdown plan that can guide implementation phase by phase
