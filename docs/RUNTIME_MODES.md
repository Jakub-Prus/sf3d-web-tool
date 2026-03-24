# Runtime Modes

## Purpose

This project now has three practical runtime outcomes for generation requests:

- `mock`
  - returns placeholder artifacts only
  - useful for API contract work
- `local`
  - generates a lightweight GLB preview mesh by extruding the uploaded image silhouette
  - useful when the official SF3D runtime is not available locally
- `real`
  - runs the official `stable-fast-3d` pipeline
  - requires the upstream repo, dependencies, and model access

`auto` resolves to `real` only when the official runner is present and importable. Otherwise it falls back to `local`.

## Why Local Mode Exists

The checked-in SF3D upstream repository currently requires native extension builds and additional runtime dependencies that are not guaranteed on a fresh Windows setup.

In this repository, `local` mode keeps the product workflow usable:

- uploads still succeed
- a browser-loadable `mesh.glb` is generated
- the viewer can render a real model instead of placeholder text files
- artifact routes and download flows remain exercised end to end

This is a preview-oriented fallback, not a substitute for the official SF3D output quality.

## Viewer Stability

The browser viewer was updated to keep a single WebGL canvas mounted while models load. It now:

- loads GLBs without tearing down the renderer on transient state changes
- reduces renderer pressure with conservative DPR and antialias settings
- detects `webglcontextlost`
- exposes a viewer reset path after context loss

If preview loads briefly and then disappears, restart the frontend after pulling the latest code and retry. If the browser still drops the WebGL context, use the viewer reset control and compare behavior across browsers.

## Validation

The repo now verifies:

- health mode resolution
- local preview fallback behavior
- official runner behavior with a fake runner fixture
- parseable local GLB output
- frontend typecheck for the updated viewer state handling

## Recommended Local Setup

For the broadest chance of a working preview on a fresh machine:

```powershell
$env:SF3D_INFERENCE_MODE="auto"
```

If the official runner is not ready, the backend will resolve to `local` and still produce a real `mesh.glb`.

To force the fallback explicitly:

```powershell
$env:SF3D_INFERENCE_MODE="local"
```
