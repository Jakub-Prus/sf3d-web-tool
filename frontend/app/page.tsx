import { UploadPanel } from "@/components/upload-panel";

const phaseLabels = [
  "Phase 1: local image-to-3D pipeline",
  "Phase 2: browser viewer and export tooling",
  "Phase 3: preprocessing, cleanup, and deployment polish",
];

const portfolioSignals = [
  "AI model integration through a product-style API",
  "3D rendering and inspection in the browser",
  "Mesh, material, and export pipeline awareness",
  "Performance and user-experience tradeoff thinking",
];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-10 px-6 py-10 lg:px-10">
      <section className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[32px] border border-[var(--page-line)] bg-[var(--page-card)] p-8 shadow-panel backdrop-blur">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-tide">
            SF3D Product Scaffold
          </p>
          <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            Build a real image-to-3D workflow, not just a model wrapper.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-[var(--page-soft)]">
            This starter project frames SF3D as a full product surface: image upload,
            preprocessing, inference serving, browser inspection, and export.
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            {portfolioSignals.map((signal) => (
              <div
                key={signal}
                className="rounded-2xl border border-[var(--page-line)] bg-white/60 p-4 text-sm leading-6 text-ink"
              >
                {signal}
              </div>
            ))}
          </div>
        </div>

        <aside className="rounded-[32px] border border-[var(--page-line)] bg-ink bg-grid bg-[length:22px_22px] p-8 text-white shadow-panel">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-orange-200">
            Delivery path
          </p>
          <ol className="mt-6 space-y-4">
            {phaseLabels.map((phase, index) => (
              <li key={phase} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.3em] text-orange-100">
                  Step {index + 1}
                </p>
                <p className="mt-2 text-base font-medium leading-6">{phase}</p>
              </li>
            ))}
          </ol>
        </aside>
      </section>

      <UploadPanel />
    </main>
  );
}
