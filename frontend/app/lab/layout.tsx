import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { labEnabled } from "./lab-flags";

// Local-only gate. Every /lab/* route (page + API) renders through this layout;
// when the Lab is disabled — ALWAYS in a production build — it 404s, so the Model
// Lab is effectively absent from the prod surface. noindex for good measure.
export const metadata: Metadata = {
  title: "Model Lab",
  robots: { index: false, follow: false },
};

export default function LabLayout({ children }: { children: React.ReactNode }) {
  if (!labEnabled()) notFound();
  return (
    <div className="mx-auto max-w-wide px-6 pb-24 pt-12">
      <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-line px-3 py-1 text-label uppercase text-ink-2">
        <span aria-hidden>●</span> local-only · excluded from prod
      </div>
      {children}
    </div>
  );
}
