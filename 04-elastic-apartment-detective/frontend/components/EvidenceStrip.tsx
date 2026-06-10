"use client";

import type { AgentEvent } from "@/components/ThinkingPanel";

// Derives the at-a-glance risk dashboard straight from the Elastic tool results
// the agent already streams: hard HPD evidence, 311 quality-of-life signals, and
// how the building stacks up against its own neighborhood. This is the emotional
// payload of the demo — the public record the listing never shows you.

function lastResult(events: AgentEvent[], name: string): any | null {
  const ev = [...events]
    .reverse()
    .find((e) => e.type === "tool_result" && e.payload?.name === name);
  return ev?.payload?.result ?? null;
}

export function EvidenceStrip({ events }: { events: AgentEvent[] }) {
  const hpd = lastResult(events, "get_hpd_violations");
  const signals = lastResult(events, "get_311_signals");
  const baseline = lastResult(events, "compare_to_neighborhood_baseline");
  if (!hpd && !signals && !baseline) return null;

  return (
    <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {hpd && (
        <StatCard
          label="Open HPD violations"
          value={String(hpd.open_violations ?? 0)}
          sub={(hpd.severe_categories || []).slice(0, 2).join(", ") || "none severe"}
          tone={hpd.open_violations >= 3 ? "bad" : hpd.open_violations > 0 ? "warn" : "ok"}
        />
      )}
      {signals && (
        <StatCard
          label="311 complaints / 90d"
          value={String(signals.complaint_count_90d ?? 0)}
          sub={(signals.top_categories || []).slice(0, 3).join(", ")}
          tone={signals.complaint_count_90d >= 10 ? "bad" : signals.complaint_count_90d >= 5 ? "warn" : "ok"}
        />
      )}
      {signals && (
        <StatCard
          label="Late-night noise share"
          value={`${Math.round((signals.nighttime_noise_share ?? 0) * 100)}%`}
          sub="of nearby noise complaints"
          tone={
            signals.nighttime_noise_share >= 0.5
              ? "bad"
              : signals.nighttime_noise_share >= 0.3
              ? "warn"
              : "ok"
          }
        />
      )}
      {baseline && (
        <StatCard
          label="Vs. neighborhood"
          value={`${(baseline.complaint_index_vs_zip ?? 1).toFixed(1)}×`}
          sub="complaint density vs ZIP baseline"
          tone={
            baseline.complaint_index_vs_zip >= 1.3
              ? "bad"
              : baseline.complaint_index_vs_zip >= 1.1
              ? "warn"
              : "ok"
          }
        />
      )}
    </section>
  );
}

function StatCard({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub: string;
  tone: "ok" | "warn" | "bad";
}) {
  const valueTone =
    tone === "bad" ? "text-rose-400" : tone === "warn" ? "text-amber-300" : "text-teal-300";
  const ring =
    tone === "bad"
      ? "border-rose-500/30"
      : tone === "warn"
      ? "border-amber-500/30"
      : "border-zinc-800";
  return (
    <div className={`rounded-lg border ${ring} bg-ink-900 p-3`}>
      <p className="text-[10px] uppercase tracking-widest text-zinc-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${valueTone}`}>{value}</p>
      <p className="mt-1 text-[11px] text-zinc-500 truncate" title={sub}>
        {sub || "—"}
      </p>
    </div>
  );
}
