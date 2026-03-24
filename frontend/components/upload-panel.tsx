"use client";

import { useEffect, useState } from "react";
import { DEFAULT_API_BASE_URL, ACCEPTED_IMAGE_TYPES } from "@/lib/config";
import type { ExportFormat, GenerationResponse, HealthResponse } from "@/lib/types";
import { InspectorPanel } from "@/components/inspector-panel";
import { ViewerPanel } from "@/components/viewer-panel";

const PREVIEW_READY_EXPORT_FORMATS: ExportFormat[] = ["glb", "zip"];
const MOCK_MODE_EXPORT_FORMATS: ExportFormat[] = ["glb"];
const MAX_UPLOAD_SIZE_MB = 10;
const BYTES_PER_MEGABYTE = 1024 * 1024;
const PROGRESS_UPDATE_INTERVAL_MS = 500;
const SECONDS_PER_MINUTE = 60;

type SubmitMode = HealthResponse["resolved_inference_mode"] | "unknown";

type ProgressStage = {
  startsAtSeconds: number;
  title: string;
  detail: string;
};

const GENERATION_PROGRESS_STAGES: Record<SubmitMode, ProgressStage[]> = {
  mock: [
    {
      startsAtSeconds: 0,
      title: "Uploading image and options",
      detail: "Sending the request to the backend mock pipeline.",
    },
    {
      startsAtSeconds: 2,
      title: "Writing placeholder artifacts",
      detail: "The backend is generating contract-safe mock outputs.",
    },
    {
      startsAtSeconds: 4,
      title: "Preparing response payload",
      detail: "Finalizing metadata and browser-loadable artifact links.",
    },
  ],
  local: [
    {
      startsAtSeconds: 0,
      title: "Uploading image and options",
      detail: "Sending the request and validating the uploaded file.",
    },
    {
      startsAtSeconds: 2,
      title: "Preprocessing input image",
      detail: "Applying background removal, crop, and canvas normalization when requested.",
    },
    {
      startsAtSeconds: 6,
      title: "Building preview mesh",
      detail: "Generating the local GLB preview mesh from the processed image silhouette and color-derived height cues.",
    },
    {
      startsAtSeconds: 12,
      title: "Finalizing GLB response",
      detail: "Writing artifacts, metadata, and the viewer URL for the browser.",
    },
  ],
  real: [
    {
      startsAtSeconds: 0,
      title: "Uploading image and options",
      detail: "Sending the request and validating the uploaded file.",
    },
    {
      startsAtSeconds: 3,
      title: "Preprocessing input image",
      detail: "Applying local preprocessing before the official SF3D runner starts.",
    },
    {
      startsAtSeconds: 10,
      title: "Starting official SF3D runner",
      detail: "Loading the model and preparing the upstream inference environment.",
    },
    {
      startsAtSeconds: 30,
      title: "Generating mesh and textures",
      detail: "The official runner is reconstructing the asset and baking materials.",
    },
    {
      startsAtSeconds: 60,
      title: "Packaging final artifacts",
      detail: "Saving the generated files, logs, and metadata for the response.",
    },
  ],
  unknown: [
    {
      startsAtSeconds: 0,
      title: "Submitting generation request",
      detail: "The backend request is running.",
    },
    {
      startsAtSeconds: 5,
      title: "Still running",
      detail: "The request has not finished yet, but the connection is still active.",
    },
  ],
};

function formatElapsedTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / SECONDS_PER_MINUTE);
  const seconds = totalSeconds % SECONDS_PER_MINUTE;
  if (minutes === 0) {
    return `${seconds}s`;
  }
  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}

function getProgressState(mode: SubmitMode, elapsedSeconds: number) {
  const stages = GENERATION_PROGRESS_STAGES[mode];
  const activeStageIndex = stages.reduce((currentIndex, stage, stageIndex) => {
    return elapsedSeconds >= stage.startsAtSeconds ? stageIndex : currentIndex;
  }, 0);
  return {
    stages,
    activeStageIndex,
    activeStage: stages[activeStageIndex],
  };
}

export function UploadPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [removeBackground, setRemoveBackground] = useState(true);
  const [autoCrop, setAutoCrop] = useState(true);
  const [normalizeSize, setNormalizeSize] = useState(true);
  const [exportFormat, setExportFormat] = useState<ExportFormat>("glb");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<GenerationResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [submitMode, setSubmitMode] = useState<SubmitMode>("unknown");
  const [submitStartedAt, setSubmitStartedAt] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const fileSummary = file
    ? `${file.name} - ${(file.size / BYTES_PER_MEGABYTE).toFixed(2)} MB`
    : "PNG, JPEG, or WEBP up to 10 MB";
  const exportFormats =
    health?.resolved_inference_mode === "mock" ? MOCK_MODE_EXPORT_FORMATS : PREVIEW_READY_EXPORT_FORMATS;
  const progressState = getProgressState(submitMode, elapsedSeconds);

  useEffect(() => {
    if (!isSubmitting || submitStartedAt === null) {
      return;
    }

    const intervalId = window.setInterval(() => {
      const nextElapsedSeconds = Math.max(
        0,
        Math.floor((Date.now() - submitStartedAt) / 1000),
      );
      setElapsedSeconds(nextElapsedSeconds);
    }, PROGRESS_UPDATE_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [isSubmitting, submitStartedAt]);

  useEffect(() => {
    async function loadHealth() {
      try {
        const response = await fetch(`${DEFAULT_API_BASE_URL}/health`);
        if (!response.ok) {
          throw new Error("Health request failed.");
        }

        const payload = (await response.json()) as HealthResponse;
        setHealth(payload);
        setExportFormat((currentFormat) =>
          payload.resolved_inference_mode === "mock" ? "glb" : currentFormat,
        );
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unable to load backend status.";
        setHealthError(message);
      }
    }

    void loadHealth();
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setResult(null);

    if (!file) {
      setErrorMessage("Select an object image before starting generation.");
      return;
    }

    if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
      setErrorMessage("Use PNG, JPEG, or WEBP input images for the initial pipeline.");
      return;
    }

    if (file.size > MAX_UPLOAD_SIZE_MB * BYTES_PER_MEGABYTE) {
      setErrorMessage("The starter API expects files no larger than 10 MB.");
      return;
    }

    const formData = new FormData();
    formData.append("image", file);
    formData.append("remove_background", String(removeBackground));
    formData.append("auto_crop", String(autoCrop));
    formData.append("normalize_size", String(normalizeSize));
    formData.append("export_format", exportFormat);

    setIsSubmitting(true);
    setSubmitMode(health?.resolved_inference_mode ?? "unknown");
    setSubmitStartedAt(Date.now());
    setElapsedSeconds(0);

    try {
        const response = await fetch(`${DEFAULT_API_BASE_URL}/generate-3d`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        const message = payload?.detail ?? (await response.text()) ?? "Generation request failed.";
        throw new Error(message || "Generation request failed.");
      }

      const payload = (await response.json()) as GenerationResponse;
      setResult(payload);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unexpected request failure.";
      setErrorMessage(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <form
        onSubmit={handleSubmit}
        className="rounded-[28px] border border-[var(--page-line)] bg-white/80 p-6 shadow-panel"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-tide">
              Upload workflow
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">Generate a 3D asset contract</h2>
          </div>
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-800">
            Local-first
          </span>
        </div>

        <label className="mt-6 flex cursor-pointer flex-col rounded-[24px] border border-dashed border-[var(--page-line)] bg-shell p-5 text-sm leading-6 text-ink transition hover:border-tide">
          <span className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--page-soft)]">
            Object image
          </span>
          <span className="mt-2 text-base font-medium">{fileSummary}</span>
          <span className="mt-2 text-[var(--page-soft)]">
            Center the object, keep the silhouette readable, and prefer a clean background.
          </span>
          <input
            className="sr-only"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <label className="flex items-center justify-between rounded-2xl border border-[var(--page-line)] bg-white px-4 py-3 text-sm text-ink">
            <span>Remove background</span>
            <input
              type="checkbox"
              checked={removeBackground}
              onChange={(event) => setRemoveBackground(event.target.checked)}
            />
          </label>
          <label className="flex items-center justify-between rounded-2xl border border-[var(--page-line)] bg-white px-4 py-3 text-sm text-ink">
            <span>Auto-crop object</span>
            <input
              type="checkbox"
              checked={autoCrop}
              onChange={(event) => setAutoCrop(event.target.checked)}
            />
          </label>
          <label className="flex items-center justify-between rounded-2xl border border-[var(--page-line)] bg-white px-4 py-3 text-sm text-ink sm:col-span-2">
            <span>Normalize image size</span>
            <input
              type="checkbox"
              checked={normalizeSize}
              onChange={(event) => setNormalizeSize(event.target.checked)}
            />
          </label>
        </div>

        <label className="mt-6 flex flex-col gap-2 text-sm text-ink">
          <span className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--page-soft)]">
            Preferred export format
          </span>
          <select
            value={exportFormat}
            onChange={(event) => setExportFormat(event.target.value as ExportFormat)}
            className="rounded-2xl border border-[var(--page-line)] bg-white px-4 py-3 outline-none ring-0"
          >
            {exportFormats.map((format) => (
              <option key={format} value={format}>
                {format.toUpperCase()}
              </option>
            ))}
          </select>
        </label>

        <div className="mt-6 rounded-2xl border border-[var(--page-line)] bg-slate-50 p-4 text-sm leading-6 text-[var(--page-soft)]">
          {healthError
            ? `Backend readiness could not be loaded: ${healthError}`
            : health?.resolved_inference_mode === "real"
              ? health.expected_runner_device === "cuda"
                ? "Real SF3D mode is active on GPU. Preview and ZIP export should be available with the fastest local runtime."
                : "Real SF3D mode is active on CPU. Preview and ZIP export should be available, but generation will be slower."
              : health?.resolved_inference_mode === "local"
                ? "Local preview mode is active. The backend will build a lightweight smoothed heightfield GLB preview until the official SF3D runner is available."
                : "Mock fallback is active. Requests will succeed, but the preview viewer will remain in fallback mode until real inference is ready."}
        </div>

        {health ? (
          <div className="mt-4 rounded-2xl border border-[var(--page-line)] bg-white px-4 py-3 text-sm text-ink">
            <p className="font-semibold uppercase tracking-[0.18em] text-[var(--page-soft)]">
              Backend mode
            </p>
            <p className="mt-2">
              Resolved mode: <span className="font-semibold">{health.resolved_inference_mode}</span>
            </p>
            <p>
              Runner device: <span className="font-semibold">{health.expected_runner_device.toUpperCase()}</span>
              {health.cuda_device_name ? ` (${health.cuda_device_name})` : ""}
            </p>
            <p>CUDA extension ready: {health.cuda_extension_ready ? "Yes" : "No"}</p>
            <p>Force CPU: {health.sf3d_force_cpu ? "Yes" : "No"}</p>
            <p>Preview expected: {health.viewer_preview_expected ? "Yes" : "No"}</p>
            {health.warnings.length > 0 ? (
              <ul className="mt-3 space-y-2 text-[var(--page-soft)]">
                {health.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}

        {errorMessage ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        {isSubmitting ? (
          <div className="mt-4 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-4 text-sm text-sky-950">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">
                  Generation in progress
                </p>
                <p className="mt-2 text-base font-semibold">{progressState.activeStage.title}</p>
              </div>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
                {formatElapsedTime(elapsedSeconds)}
              </span>
            </div>
            <p className="mt-2 leading-6 text-sky-900">{progressState.activeStage.detail}</p>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-sky-100">
              <div className="h-full w-2/5 animate-pulse rounded-full bg-sky-500" />
            </div>
            <ul className="mt-4 space-y-2">
              {progressState.stages.map((stage, stageIndex) => {
                const isActive = stageIndex === progressState.activeStageIndex;
                const isCompleted = stageIndex < progressState.activeStageIndex;

                return (
                  <li
                    key={`${stage.title}-${stage.startsAtSeconds}`}
                    className={`rounded-2xl border px-3 py-2 ${
                      isActive
                        ? "border-sky-300 bg-white text-sky-950"
                        : isCompleted
                          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                          : "border-sky-100 bg-white/70 text-sky-700"
                    }`}
                  >
                    <span className="font-medium">{stage.title}</span>
                  </li>
                );
              })}
            </ul>
            <p className="mt-3 text-xs leading-5 text-sky-700">
              This is an estimated progress indicator based on the active runtime mode. The request is still running until the backend responds.
            </p>
          </div>
        ) : null}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-6 inline-flex items-center justify-center rounded-full bg-ink px-6 py-3 text-sm font-semibold uppercase tracking-[0.18em] text-white transition hover:bg-tide disabled:cursor-not-allowed disabled:bg-slate-500"
        >
          {isSubmitting ? progressState.activeStage.title : "Run generate-3d"}
        </button>
      </form>

      <div className="grid gap-6">
        <ViewerPanel result={result} health={health} />
        {result ? <InspectorPanel result={result} health={health} /> : null}
      </div>
    </section>
  );
}
