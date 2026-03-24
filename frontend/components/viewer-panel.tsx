"use client";

import { useEffect, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { Box3, Object3D, Vector3 } from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { resolveApiUrl } from "@/lib/config";
import type { GenerationResponse, HealthResponse } from "@/lib/types";

type ViewerPanelProps = {
  result: GenerationResponse | null;
  health: HealthResponse | null;
};

const viewerToggles = [
  "Orbit controls",
  "Wireframe overlay",
  "Texture on or off",
  "Normal visualization",
  "Lighting presets",
];

type ViewerPhase = "idle" | "missing-mesh" | "loading" | "ready" | "error" | "context-lost";

function FitCamera({ target }: { target: Object3D }) {
  const { camera, controls } = useThree();

  useEffect(() => {
    const bounds = new Box3().setFromObject(target);
    const size = bounds.getSize(new Vector3());
    const center = bounds.getCenter(new Vector3());
    const largestDimension = Math.max(size.x, size.y, size.z, 1);

    camera.position.set(center.x, center.y + largestDimension * 0.25, center.z + largestDimension * 2.2);
    camera.near = 0.01;
    camera.far = largestDimension * 20;
    camera.lookAt(center);
    camera.updateProjectionMatrix();

    const orbitControls = controls as { target?: Vector3; update?: () => void } | undefined;
    orbitControls?.target?.copy(center);
    orbitControls?.update?.();
  }, [camera, controls, target]);

  return null;
}

function CanvasLifecycle({
  onContextLost,
  onContextRestored,
}: {
  onContextLost: () => void;
  onContextRestored: () => void;
}) {
  const { gl } = useThree();

  useEffect(() => {
    const canvasElement = gl.domElement;

    function handleContextLost(event: Event) {
      event.preventDefault();
      onContextLost();
    }

    function handleContextRestored() {
      onContextRestored();
    }

    canvasElement.addEventListener("webglcontextlost", handleContextLost, false);
    canvasElement.addEventListener("webglcontextrestored", handleContextRestored, false);

    return () => {
      canvasElement.removeEventListener("webglcontextlost", handleContextLost, false);
      canvasElement.removeEventListener("webglcontextrestored", handleContextRestored, false);
    };
  }, [gl, onContextLost, onContextRestored]);

  return null;
}

export function ViewerPanel({ result, health }: ViewerPanelProps) {
  const viewerAssetUrl = result?.viewer_asset_url ? resolveApiUrl(result.viewer_asset_url) : null;
  const [viewerPhase, setViewerPhase] = useState<ViewerPhase>("idle");
  const [loadedScene, setLoadedScene] = useState<Object3D | null>(null);
  const [canvasInstanceKey, setCanvasInstanceKey] = useState(0);
  const currentAssetUrlRef = useRef<string | null>(null);

  useEffect(() => {
    const previousScene = loadedScene;

    if (!viewerAssetUrl) {
      currentAssetUrlRef.current = null;
      setLoadedScene(null);
      setViewerPhase(result ? "missing-mesh" : "idle");
      return;
    }

    if (currentAssetUrlRef.current === viewerAssetUrl && previousScene) {
      setViewerPhase("ready");
      return;
    }

    let ignoreResult = false;
    const loader = new GLTFLoader();

    currentAssetUrlRef.current = viewerAssetUrl;
    setLoadedScene(null);
    setViewerPhase("loading");

    loader.load(
      viewerAssetUrl,
      (gltf) => {
        if (ignoreResult) {
          return;
        }

        setLoadedScene(gltf.scene);
        setViewerPhase("ready");
      },
      undefined,
      () => {
        if (ignoreResult) {
          return;
        }

        setLoadedScene(null);
        setViewerPhase("error");
      },
    );

    return () => {
      ignoreResult = true;
    };
  }, [loadedScene, result, viewerAssetUrl]);

  const showScene = viewerPhase === "ready" && loadedScene !== null;

  function handleContextLost() {
    setViewerPhase("context-lost");
  }

  function handleContextRestored() {
    setViewerPhase(loadedScene ? "ready" : viewerAssetUrl ? "loading" : result ? "missing-mesh" : "idle");
  }

  function handleResetViewer() {
    setCanvasInstanceKey((currentKey) => currentKey + 1);
    setViewerPhase(viewerAssetUrl ? "loading" : result ? "missing-mesh" : "idle");
  }

  function renderOverlay() {
    if (viewerPhase === "ready") {
      return null;
    }

    if (viewerPhase === "loading") {
      return (
        <div>
          <p className="text-lg font-semibold text-white">Loading 3D preview...</p>
          <p className="mt-3 text-slate-300">Fetching the generated GLB from the backend.</p>
        </div>
      );
    }

    if (viewerPhase === "context-lost") {
      return (
        <div>
          <p className="text-lg font-semibold text-white">The browser lost the WebGL context.</p>
          <p className="mt-3 max-w-xl text-slate-300">
            The model was loaded, but the renderer was reset by the browser or GPU driver. Reset
            the viewer to recreate the canvas.
          </p>
          <button
            type="button"
            onClick={handleResetViewer}
            className="mt-4 rounded-full bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-ink transition hover:bg-slate-200"
          >
            Reset Viewer
          </button>
        </div>
      );
    }

    if (viewerPhase === "error") {
      return (
        <div>
          <p className="text-lg font-semibold text-white">Viewer failed to load the GLB.</p>
          <p className="mt-3 max-w-xl text-slate-300">
            The backend returned a mesh URL, but the browser could not render it. Use the download
            links to inspect the artifact directly.
          </p>
        </div>
      );
    }

    if (viewerPhase === "missing-mesh") {
      return (
        <div>
          <p className="text-lg font-semibold text-white">
            {result?.status === "mocked"
              ? "Mock mode does not produce a real preview mesh."
              : "The run finished without a browser-loadable GLB."}
          </p>
          <p className="mt-3 max-w-xl text-slate-300">
            {result?.status === "mocked"
              ? "Switch the backend to local or real inference mode to render a generated model in the preview."
              : "This response did not include a browser-loadable mesh. Use the notes and downloads below to inspect the output and runner state."}
          </p>
        </div>
      );
    }

    return (
      <div>
        <p className="text-lg font-semibold text-white">No generation result yet.</p>
        <p className="mt-3 max-w-xl text-slate-300">
          {health?.resolved_inference_mode === "mock"
            ? "The backend is currently resolved to mock mode, so preview is not expected until real inference is available."
            : health?.resolved_inference_mode === "local"
              ? "Upload an image to generate a local silhouette-based mesh preview. Once the official SF3D runner is ready, this viewer will load the higher-fidelity GLB instead."
              : health?.expected_runner_device === "cuda"
                ? "Upload an image to generate a real GPU-backed SF3D result. Once the GLB is available, it will load directly in this viewer with orbit controls."
                : "Upload an image to generate a real CPU-backed SF3D result. Once the GLB is available, it will load directly in this viewer with orbit controls."}
        </p>
      </div>
    );
  }

  return (
    <section className="rounded-[28px] border border-[var(--page-line)] bg-white/80 p-6 shadow-panel">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-tide">
            Viewer
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-ink">GLB model preview</h3>
        </div>
        <span className="rounded-full bg-ink px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-white">
          {viewerAssetUrl ? "Interactive" : "Waiting"}
        </span>
      </div>

      <div className="mt-6 overflow-hidden rounded-[24px] border border-dashed border-[var(--page-line)] bg-gradient-to-br from-white to-slate-100 p-6">
        <div className="relative min-h-72 rounded-[20px] bg-ink/95 p-6 text-center text-sm leading-7 text-slate-200">
          <div className="h-72 w-full overflow-hidden rounded-[20px]">
            <Canvas
              key={canvasInstanceKey}
              camera={{ position: [0, 0.5, 3], fov: 45 }}
              dpr={[1, 1.5]}
              gl={{ antialias: false, powerPreference: "high-performance" }}
            >
              <CanvasLifecycle
                onContextLost={handleContextLost}
                onContextRestored={handleContextRestored}
              />
              <ambientLight intensity={1.25} />
              <directionalLight position={[4, 6, 4]} intensity={2.5} />
              {showScene ? (
                <>
                  <primitive object={loadedScene} />
                  <FitCamera target={loadedScene} />
                </>
              ) : null}
              <OrbitControls enablePan enableRotate enableZoom enabled={showScene} />
            </Canvas>
          </div>
          {viewerPhase !== "ready" ? (
            <div className="absolute inset-0 flex items-center justify-center p-6">
              <div className="pointer-events-auto">{renderOverlay()}</div>
            </div>
          ) : null}
        </div>
      </div>

      <ul className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {viewerToggles.map((toggle) => (
          <li
            key={toggle}
            className="rounded-2xl border border-[var(--page-line)] bg-shell px-4 py-3 text-sm font-medium text-ink"
          >
            {toggle}
          </li>
        ))}
      </ul>
    </section>
  );
}
