"use client";

type FinalReport = {
  summary: string;
  probable_root_cause: string;
  impact: string;
  recommended_fix: string;
} | null;

export function InvestigationCard({
  report,
  status,
}: {
  report: FinalReport;
  status: string;
}) {
  if (!report) {
    return (
      <section className="rounded-lg border border-zinc-800 bg-ink-900 p-4 h-full flex flex-col gap-3">
        <h2 className="text-xs uppercase tracking-widest text-zinc-500">
          Investigation summary
        </h2>
        <p className="text-sm text-zinc-500">
          Will populate once the agent finalizes the investigation.
        </p>
        <div className="grow flex items-center justify-center text-zinc-700">
          {status === "running" ? (
            <span className="animate-pulse">collecting evidence…</span>
          ) : (
            <span>—</span>
          )}
        </div>
      </section>
    );
  }
  return (
    <section className="rounded-lg border border-zinc-800 bg-ink-900 overflow-hidden h-full flex flex-col">
      <header className="px-4 py-3 border-b border-zinc-800 bg-gradient-to-b from-amber-500/10 to-transparent">
        <p className="text-xs uppercase tracking-widest text-amber-300">
          Regression confirmed
        </p>
        <h2 className="text-lg font-semibold text-zinc-100 mt-0.5">
          {report.summary}
        </h2>
      </header>
      <div className="p-4 grid gap-4">
        <Field
          label="Probable root cause"
          value={report.probable_root_cause}
          tone="text-zinc-200"
        />
        <Field label="Impact" value={report.impact} tone="text-amber-200" />
        <Field
          label="Recommended fix"
          value={report.recommended_fix}
          tone="text-teal-300"
        />
      </div>
      <footer className="mt-auto px-4 py-3 border-t border-zinc-800 text-xs text-zinc-500">
        Evidence notebook published to Dynatrace; operator notified via the
        configured channel. Click through any tool result in the timeline to
        deep-link into Dynatrace.
      </footer>
    </section>
  );
}

function Field({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-widest text-zinc-500 mb-1">
        {label}
      </p>
      <p className={"text-sm leading-relaxed " + tone}>{value}</p>
    </div>
  );
}
