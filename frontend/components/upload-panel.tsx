"use client";

import { useState } from "react";
import { DEFAULT_API_BASE_URL, ACCEPTED_IMAGE_TYPES } from "@/lib/config";
import type { ExportFormat, GenerationResponse } from "@/lib/types";
import { InspectorPanel } from "@/components/inspector-panel";
import { ViewerPanel } from "@/components/viewer-panel";

const EXPORT_FORMATS: ExportFormat[] = ["glb", "obj", "zip"];
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

  const fileSummary = file
    ? `${file.name} - ${(file.size / BYTES_PER_MEGABYTE).toFixed(2)} MB`
    : "PNG, JPEG, or WEBP up to 10 MB";

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
        const message = await response.text();
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
            {EXPORT_FORMATS.map((format) => (
              <option key={format} value={format}>
                {format.toUpperCase()}
              </option>
            ))}
          </select>
        </label>

        <div className="mt-6 rounded-2xl border border-[var(--page-line)] bg-slate-50 p-4 text-sm leading-6 text-[var(--page-soft)]">
          The current backend returns a mock generation manifest. Swap in the real SF3D runner
          once the model repository and CUDA runtime are in place.
        </div>

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
        <ViewerPanel result={result} />
        {result ? <InspectorPanel result={result} /> : null}
      </div>
    </section>
  );
}
