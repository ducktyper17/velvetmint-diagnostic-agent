"use client";

export type FinalReport = {
  listing: { address: string; source: string; listing_url: string | null };
  risk_score: number;
  confidence?: "high" | "moderate" | "low";
  confidence_rationale?: string;
  summary: string;
  top_red_flags: string[];
  questions_to_ask: string[];
  evidence: string[];
} | null;

export function RiskBrief({
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
          Renter risk brief
        </h2>
        <p className="text-sm text-zinc-500">
          Populates once the detective finishes the investigation.
        </p>
        <div className="grow flex items-center justify-center text-zinc-700">
          {status === "running" ? (
            <span className="animate-pulse">gathering public records…</span>
          ) : (
            <span>—</span>
          )}
        </div>
      </section>
    );
  }

  const band = riskBand(report.risk_score);

  return (
    <section className="rounded-lg border border-zinc-800 bg-ink-900 overflow-hidden h-full flex flex-col">
      <header className={`px-4 py-3 border-b border-zinc-800 bg-gradient-to-b ${band.headerBg}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className={`text-xs uppercase tracking-widest ${band.label}`}>
              {band.title}
            </p>
            <h2 className="text-base font-semibold text-zinc-100 mt-0.5 truncate">
              {report.listing.address}
            </h2>
            <p className="text-[11px] text-zinc-500">
              source: {report.listing.source}
            </p>
          </div>
          <ScoreDial score={report.risk_score} tone={band.dial} />
        </div>
        {report.confidence && (
          <ConfidenceChip
            level={report.confidence}
            rationale={report.confidence_rationale}
          />
        )}
        <p className="text-sm text-zinc-300 mt-3 leading-relaxed">{report.summary}</p>
      </header>

      <div className="p-4 grid gap-4 overflow-y-auto">
        <Block label="Top red flags">
          <ul className="space-y-1">
            {report.top_red_flags.map((f, i) => (
              <li key={i} className="flex gap-2 text-sm text-rose-300">
                <span className="text-rose-500">▲</span>
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </Block>

        {report.evidence.length > 0 && (
          <Block label="Supporting evidence">
            <ul className="space-y-1">
              {report.evidence.map((e, i) => (
                <li key={i} className="flex gap-2 text-sm text-zinc-300">
                  <span className="text-zinc-600">·</span>
                  <span>{e}</span>
                </li>
              ))}
            </ul>
          </Block>
        )}

        <Block label="Questions to ask before you apply">
          <ol className="space-y-1 list-decimal list-inside">
            {report.questions_to_ask.map((q, i) => (
              <li key={i} className="text-sm text-teal-300">
                {q}
              </li>
            ))}
          </ol>
        </Block>
      </div>

      <footer className="mt-auto px-4 py-3 border-t border-zinc-800 text-xs text-zinc-500">
        Brief written back to the Elastic <code className="text-zinc-400">building_briefs</code>{" "}
        index — follow-up questions reuse it instead of re-investigating.
      </footer>
    </section>
  );
}

function ConfidenceChip({
  level,
  rationale,
}: {
  level: "high" | "moderate" | "low";
  rationale?: string;
}) {
  const tone = {
    high: "bg-teal-500/15 text-teal-300 ring-teal-500/30",
    moderate: "bg-amber-500/15 text-amber-300 ring-amber-500/30",
    low: "bg-zinc-700/40 text-zinc-300 ring-zinc-600/40",
  }[level];
  return (
    <div className="mt-2 flex items-center gap-2">
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ring-1 ${tone}`}
        title="Derived from how many independent Elastic sources corroborate — not guessed by the model."
      >
        {level} confidence
      </span>
      {rationale && (
        <span className="text-[11px] text-zinc-500 leading-tight">{rationale}</span>
      )}
    </div>
  );
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-widest text-zinc-500 mb-1.5">{label}</p>
      {children}
    </div>
  );
}

function ScoreDial({ score, tone }: { score: number; tone: string }) {
  const pct = Math.max(0, Math.min(100, (score / 10) * 100));
  return (
    <div className="shrink-0 text-right">
      <div className={`text-3xl font-bold tabular-nums ${tone}`}>
        {score.toFixed(1)}
        <span className="text-base text-zinc-600 font-normal">/10</span>
      </div>
      <div className="mt-1 h-1.5 w-24 rounded-full bg-zinc-800 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${tone.replace(
            "text-",
            "bg-"
          )}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function riskBand(score: number) {
  if (score >= 7)
    return {
      title: "High renter risk",
      label: "text-rose-400",
      dial: "text-rose-400",
      headerBg: "from-rose-500/15 to-transparent",
    };
  if (score >= 4.5)
    return {
      title: "Elevated risk — read carefully",
      label: "text-amber-300",
      dial: "text-amber-300",
      headerBg: "from-amber-500/10 to-transparent",
    };
  return {
    title: "Low risk on public signals",
    label: "text-teal-300",
    dial: "text-teal-300",
    headerBg: "from-teal-500/10 to-transparent",
  };
}
