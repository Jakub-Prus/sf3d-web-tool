import { resolveApiUrl } from "@/lib/config";
import type { GenerationResponse, HealthResponse } from "@/lib/types";

type InspectorPanelProps = {
  result: GenerationResponse;
  health: HealthResponse | null;
};

const labelMap: Record<string, string> = {
  job_id: "Job ID",
  status: "Status",
  export_format: "Export",
  generation_time_seconds: "Generation time (s)",
};

export function InspectorPanel({ result, health }: InspectorPanelProps) {
  const downloadArtifacts = result.artifacts.filter((artifact) =>
    ["archive", "mesh", "metadata", "input"].includes(artifact.kind),
  );

  const facts = [
    [labelMap.job_id, result.job_id],
    [labelMap.status, result.status],
    [labelMap.export_format, result.export_format.toUpperCase()],
    [labelMap.generation_time_seconds, result.generation_time_seconds.toFixed(2)],
    ["Runtime mode", health?.resolved_inference_mode ?? "unknown"],
    [
      "Runner device",
      health
        ? `${health.expected_runner_device.toUpperCase()}${health.cuda_device_name ? ` (${health.cuda_device_name})` : ""}`
        : "unknown",
    ],
    ["Preview expected", health?.viewer_preview_expected ? "Yes" : "No"],
  ];

  return (
    <section className="rounded-[28px] border border-[var(--page-line)] bg-white/80 p-6 shadow-panel">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-tide">
            Model inspector
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-ink">Artifact summary</h3>
        </div>
        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-amber-800">
          {result.status}
        </span>
      </div>

      <dl className="mt-6 grid gap-4 sm:grid-cols-2">
        {facts.map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-[var(--page-line)] bg-shell p-4">
            <dt className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--page-soft)]">
              {label}
            </dt>
            <dd className="mt-2 text-sm font-medium text-ink">{value}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--page-soft)]">
          Preprocessing steps
        </p>
        <ul className="mt-3 space-y-2 text-sm leading-6 text-ink">
          {result.preprocessing_steps.map((step) => (
            <li key={step} className="rounded-2xl border border-[var(--page-line)] bg-white p-3">
              {step}
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--page-soft)]">
          Preprocessing applied
        </p>
        <ul className="mt-3 space-y-2 text-sm leading-6 text-ink">
          {result.preprocessing_applied.length > 0 ? (
            result.preprocessing_applied.map((step) => (
              <li key={step} className="rounded-2xl border border-[var(--page-line)] bg-white p-3">
                {step}
              </li>
            ))
          ) : (
            <li className="rounded-2xl border border-[var(--page-line)] bg-white p-3">
              No local preprocessing steps were applied before inference.
            </li>
          )}
        </ul>
      </div>

      <div className="mt-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--page-soft)]">
          Downloads
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {downloadArtifacts.map((artifact) => (
            <a
              key={artifact.relative_path}
              href={resolveApiUrl(artifact.url)}
              target="_blank"
              rel="noreferrer"
              className="rounded-2xl border border-[var(--page-line)] bg-white px-4 py-3 text-sm font-medium text-ink transition hover:border-tide"
            >
              Download {artifact.file_name}
            </a>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--page-soft)]">
          Runner notes
        </p>
        <ul className="mt-3 space-y-2 text-sm leading-6 text-ink">
          {result.notes.map((note) => (
            <li key={note} className="rounded-2xl border border-[var(--page-line)] bg-white p-3">
              {note}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
