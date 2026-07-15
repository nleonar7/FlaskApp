"use client";

import { useEffect, useState } from "react";
import type { FeasibilityInputs } from "@/lib/feasibility";
import type { IntakeSummary } from "@/lib/interview";

export function Report({
  feasibility,
  intake,
}: {
  feasibility: FeasibilityInputs;
  intake: IntakeSummary;
}) {
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetch("/api/report", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ feasibility, intake }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error ?? "Report failed.");
        if (!cancelled) setMarkdown(data.markdown);
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [feasibility, intake]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!markdown)
    return <p className="text-sm text-slate-500">Composing your report…</p>;

  return (
    <section>
      <div className="mb-4 flex items-center justify-between no-print">
        <h2 className="text-lg font-semibold">Feasibility Report</h2>
        <button
          onClick={() => window.print()}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium"
        >
          Print / Save PDF
        </button>
      </div>
      {/* Lightweight render: report markdown as preformatted prose. A markdown
          renderer (react-markdown) is a fast-follow; kept dependency-free here. */}
      <article className="whitespace-pre-wrap rounded-xl border border-slate-200 bg-white p-6 text-sm leading-relaxed shadow-sm">
        {markdown}
      </article>
    </section>
  );
}
