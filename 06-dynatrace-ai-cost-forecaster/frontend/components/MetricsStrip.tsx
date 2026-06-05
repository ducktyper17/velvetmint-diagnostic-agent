"use client";

import { useEffect, useRef, useState } from "react";
import type { AgentEvent } from "@/components/ThinkingPanel";

// Derives the before/after story straight from the telemetry the agent already
// streams: baseline vs current runtime signals + the forecast blast radius. This
// is the emotional payload of the demo — the jump the operator never saw coming.

type Signals = {
  baseline: Record<string, number>;
  current: Record<string, number>;
} | null;

function extractSignals(events: AgentEvent[]): Signals {
  const ev = [...events]
    .reverse()
    .find((e) => e.type === "tool_result" && e.payload?.name === "query_runtime_signals");
  const rows = ev?.payload?.result?.rows;
  if (!Array.isArray(rows) || rows.length < 2) return null;
  return { baseline: rows[0], current: rows[rows.length - 1] };
}

function extractForecastUsd(events: AgentEvent[]): number | null {
  const ev = [...events]
    .reverse()
    .find((e) => e.type === "tool_result" && e.payload?.name === "forecast_blast_radius");
  const r = ev?.payload?.result;
  if (!r) return null;
  const direct = r.raw?.projected_cost_usd;
  if (typeof direct === "number") return direct;
  // Fall back to scraping a "$3.4k" / "$3,480" style number from the verdict.
  const text: string = r.verdict || "";
  const m = text.match(/\$\s?([\d,.]+)\s?(k|m)?/i);
  if (!m) return null;
  let n = parseFloat(m[1].replace(/,/g, ""));
  if (m[2]?.toLowerCase() === "k") n *= 1_000;
  if (m[2]?.toLowerCase() === "m") n *= 1_000_000;
  return Number.isFinite(n) ? n : null;
}

export function MetricsStrip({ events }: { events: AgentEvent[] }) {
  const signals = extractSignals(events);
  const forecastUsd = extractForecastUsd(events);
  if (!signals && forecastUsd == null) return null;

  return (
    <section className="grid grid-cols-12 gap-4">
      {signals && (
        <div className="col-span-12 lg:col-span-8 grid grid-cols-3 gap-3">
          <MetricCard
            label="p95 latency"
            baseline={signals.baseline.p95_latency_ms}
            current={signals.current.p95_latency_ms}
            format={(v) => `${(v / 1000).toFixed(1)}s`}
          />
          <MetricCard
            label="tokens / request"
            baseline={signals.baseline.tokens_per_request}
            current={signals.current.tokens_per_request}
            format={(v) => Math.round(v).toLocaleString()}
          />
          <MetricCard
            label="tool error rate"
            baseline={signals.baseline.tool_error_rate}
            current={signals.current.tool_error_rate}
            format={(v) => `${(v * 100).toFixed(0)}%`}
          />
        </div>
      )}
      {forecastUsd != null && (
        <ForecastBanner
          usd={forecastUsd}
          className={signals ? "col-span-12 lg:col-span-4" : "col-span-12"}
        />
      )}
    </section>
  );
}

function MetricCard({
  label,
  baseline,
  current,
  format,
}: {
  label: string;
  baseline: number;
  current: number;
  format: (v: number) => string;
}) {
  const ratio = baseline > 0 ? current / baseline : 0;
  const worse = current > baseline;
  // Bar fills proportionally to the regression, capped so a 5x blowup still fits.
  const fill = Math.min(100, baseline > 0 ? (current / Math.max(current, baseline)) * 100 : 100);
  return (
    <div className="rounded-lg border border-zinc-800 bg-ink-900 p-3">
      <p className="text-[10px] uppercase tracking-widest text-zinc-500">{label}</p>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-zinc-500 text-sm line-through">{format(baseline)}</span>
        <span className="text-zinc-600">→</span>
        <span className={`text-xl font-semibold ${worse ? "text-rose-300" : "text-teal-300"}`}>
          {format(current)}
        </span>
      </div>
      <div className="mt-2 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${
            worse ? "bg-rose-500/80" : "bg-teal-500/80"
          }`}
          style={{ width: `${fill}%` }}
        />
      </div>
      {ratio > 0 && (
        <p className="mt-1 text-[11px] text-zinc-500">
          {worse ? "▲" : "▼"} {ratio.toFixed(1)}× vs baseline
        </p>
      )}
    </div>
  );
}

function ForecastBanner({ usd, className }: { usd: number; className?: string }) {
  const display = useCountUp(usd, 900);
  return (
    <div
      className={`rounded-lg border border-amber-500/30 bg-gradient-to-br from-amber-500/15 to-rose-500/10 p-4 flex flex-col justify-center ${
        className || ""
      }`}
    >
      <p className="text-[10px] uppercase tracking-widest text-amber-300/90">
        Projected weekly waste if ignored
      </p>
      <p className="text-3xl font-bold text-amber-200 tabular-nums glow-bondi mt-0.5">
        ${Math.round(display).toLocaleString()}
      </p>
      <p className="text-[11px] text-zinc-400 mt-1">
        Extrapolated from current request rate × token inflation over 7 days.
      </p>
    </div>
  );
}

// Animate a number from 0 → target with an ease-out curve.
function useCountUp(target: number, durationMs: number): number {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number | null>(null);
  useEffect(() => {
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(target * eased);
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [target, durationMs]);
  return value;
}
