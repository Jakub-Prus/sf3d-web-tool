import type { GenerationResponse } from "@/lib/types";

type ViewerPanelProps = {
  result: GenerationResponse | null;
};

const viewerToggles = [
  "Orbit controls",
  "Wireframe overlay",
  "Texture on or off",
  "Normal visualization",
  "Lighting presets",
];

export function ViewerPanel({ result }: ViewerPanelProps) {
  return (
    <section className="rounded-[28px] border border-[var(--page-line)] bg-white/80 p-6 shadow-panel">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-tide">
            Viewer plan
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-ink">React Three Fiber integration point</h3>
        </div>
        <span className="rounded-full bg-ink px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-white">
          Scaffolded
        </span>
      </div>

      <div className="mt-6 rounded-[24px] border border-dashed border-[var(--page-line)] bg-gradient-to-br from-white to-slate-100 p-6">
        <div className="flex min-h-72 items-center justify-center rounded-[20px] bg-ink/95 p-6 text-center text-sm leading-7 text-slate-200">
          {result ? (
            <div>
              <p className="text-lg font-semibold text-white">Model preview will mount here.</p>
              <p className="mt-3 max-w-xl text-slate-300">
                Replace this placeholder with a GLB or OBJ loader once the backend writes real
                mesh assets from SF3D inference.
              </p>
              <p className="mt-4 text-xs uppercase tracking-[0.24em] text-orange-200">
                Output directory: {result.output_directory}
              </p>
            </div>
          ) : (
            <div>
              <p className="text-lg font-semibold text-white">No generation result yet.</p>
              <p className="mt-3 max-w-xl text-slate-300">
                Upload an image to exercise the API contract. The viewer area is already reserved
                for the R3F scene, controls, and asset overlays.
              </p>
            </div>
          )}
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
