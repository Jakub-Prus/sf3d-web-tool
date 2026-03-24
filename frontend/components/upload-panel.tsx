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

  const fileSummary = file
    ? `${file.name} - ${(file.size / BYTES_PER_MEGABYTE).toFixed(2)} MB`
    : "PNG, JPEG, or WEBP up to 10 MB";
  const exportFormats =
    health?.resolved_inference_mode === "mock" ? MOCK_MODE_EXPORT_FORMATS : PREVIEW_READY_EXPORT_FORMATS;

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
              ? "Real SF3D mode is active. Preview and ZIP export should be available when the runner succeeds."
              : health?.resolved_inference_mode === "local"
                ? "Local preview mode is active. The backend will extrude the detected object silhouette into a lightweight GLB preview until the official SF3D runner is available."
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

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-6 inline-flex items-center justify-center rounded-full bg-ink px-6 py-3 text-sm font-semibold uppercase tracking-[0.18em] text-white transition hover:bg-tide disabled:cursor-not-allowed disabled:bg-slate-500"
        >
          {isSubmitting ? "Generating..." : "Run generate-3d"}
        </button>
      </form>

      <div className="grid gap-6">
        <ViewerPanel result={result} health={health} />
        {result ? <InspectorPanel result={result} health={health} /> : null}
      </div>
    </section>
  );
}
