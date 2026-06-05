"use client";

import { useEffect, useRef, useState } from "react";
import { ThinkingPanel, type AgentEvent } from "@/components/ThinkingPanel";
import { InvestigationCard } from "@/components/InvestigationCard";
import { ToolTimeline } from "@/components/ToolTimeline";
import { MetricsStrip } from "@/components/MetricsStrip";

type FinalReport = {
  summary: string;
  probable_root_cause: string;
  impact: string;
  recommended_fix: string;
} | null;

export default function Page() {
  const [serviceName, setServiceName] = useState("refund-assistant");
  const [releaseId, setReleaseId] = useState("release-2026-05-26-bad-prompt");
  const [lookbackMinutes, setLookbackMinutes] = useState(180);
  const [replay, setReplay] = useState(false);
  const [status, setStatus] = useState<"idle" | "running" | "complete" | "failed">("idle");
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [finalReport, setFinalReport] = useState<FinalReport>(null);
  const [error, setError] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => () => sourceRef.current?.close(), []);

  async function startInvestigation() {
    setStatus("running");
    setEvents([]);
    setFinalReport(null);
    setError(null);

    try {
      const url = `/api/proxy/investigate`;
      const body = JSON.stringify({
        question: `Investigate why ${serviceName} regressed after ${releaseId || "the latest release"}.`,
        service_name: serviceName,
        release_id: releaseId || undefined,
        lookback_minutes: lookbackMinutes,
        replay,
      });

      // EventSource can't issue a POST, so we POST with fetch and read the SSE
      // stream off the response body manually below.
      const res = await fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body,
      });
      if (!res.ok || !res.body) throw new Error(`investigate failed: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      // Minimal SSE parser. Each event ends with \n\n; lines start with
      // event:/data:.
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf("\n\n")) >= 0) {
          const chunk = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          handleSse(chunk);
        }
      }
      setStatus((s) => (s === "running" ? "complete" : s));
    } catch (e: any) {
      setStatus("failed");
      setError(e?.message || String(e));
    }
  }

  function handleSse(chunk: string) {
    let eventName = "message";
    const dataLines: string[] = [];
    for (const line of chunk.split("\n")) {
      if (line.startsWith("event:")) eventName = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    const dataStr = dataLines.join("\n");
    if (!dataStr) return;
    let data: any;
    try {
      data = JSON.parse(dataStr);
    } catch {
      data = { raw: dataStr };
    }
    if (eventName === "final_report") {
      setFinalReport({
        summary: data.summary,
        probable_root_cause: data.probable_root_cause,
        impact: data.impact,
        recommended_fix: data.recommended_fix,
      });
    }
    if (eventName === "done") {
      setStatus("complete");
    }
    if (eventName === "error") {
      setStatus("failed");
      setError(data.error || "unknown");
    }
    setEvents((prev) => [
      ...prev,
      {
        type: eventName as AgentEvent["type"],
        iteration: data.iteration ?? 0,
        ts: data.ts_ms ?? Date.now(),
        payload: data,
      },
    ]);
  }

  return (
    <div className="grid grid-rows-[auto_1fr] min-h-screen">
      <Header
        status={status}
        serviceName={serviceName}
        releaseId={releaseId}
        lookbackMinutes={lookbackMinutes}
        replay={replay}
        onServiceName={setServiceName}
        onReleaseId={setReleaseId}
        onLookbackMinutes={setLookbackMinutes}
        onReplay={setReplay}
        onStart={startInvestigation}
      />
      <main className="grid grid-cols-12 gap-4 p-4 content-start">
        <div className="col-span-12">
          <MetricsStrip events={events} />
        </div>
        <section className="col-span-12 lg:col-span-7 flex flex-col gap-4">
          <ThinkingPanel events={events} status={status} error={error} />
          <ToolTimeline events={events} />
        </section>
        <aside className="col-span-12 lg:col-span-5">
          <InvestigationCard report={finalReport} status={status} />
        </aside>
      </main>
    </div>
  );
}

function Header(props: {
  status: string;
  serviceName: string;
  releaseId: string;
  lookbackMinutes: number;
  replay: boolean;
  onServiceName: (v: string) => void;
  onReleaseId: (v: string) => void;
  onLookbackMinutes: (v: number) => void;
  onReplay: (v: boolean) => void;
  onStart: () => void;
}) {
  return (
    <header className="border-b border-zinc-800 bg-ink-900/80 backdrop-blur">
      <div className="max-w-screen-2xl mx-auto px-4 py-3 flex flex-wrap items-center gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            <span className="text-bondi-400 glow-bondi">Agent Reliability Guard</span>
          </h1>
          <p className="text-xs text-zinc-500 -mt-0.5">
            Watches Gemini-agent telemetry via Dynatrace. Catches regressions
            after deploys before they burn money and trust.
          </p>
        </div>
        <div className="grow" />
        <Field
          label="service"
          value={props.serviceName}
          onChange={props.onServiceName}
        />
        <Field
          label="release"
          value={props.releaseId}
          onChange={props.onReleaseId}
        />
        <Field
          label="lookback (min)"
          value={String(props.lookbackMinutes)}
          width="w-24"
          onChange={(v) => props.onLookbackMinutes(parseInt(v) || 0)}
        />
        <StatusPill status={props.status} />
        <label
          className="flex items-center gap-1.5 text-xs text-zinc-400 cursor-pointer select-none"
          title="Deterministic, paced offline run — bulletproof for a live demo"
        >
          <input
            type="checkbox"
            checked={props.replay}
            onChange={(e) => props.onReplay(e.target.checked)}
            className="accent-bondi-500"
          />
          replay
        </label>
        <button
          className="rounded-md bg-bondi-500/90 hover:bg-bondi-500 text-ink-950 font-medium text-sm px-3 py-1.5 transition"
          onClick={props.onStart}
          disabled={props.status === "running"}
        >
          {props.status === "running" ? "Investigating…" : "Investigate"}
        </button>
      </div>
    </header>
  );
}

function Field({
  label,
  value,
  onChange,
  width = "w-56",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  width?: string;
}) {
  return (
    <label className="text-xs text-zinc-500 flex flex-col">
      <span className="ml-1">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={
          "bg-ink-800 border border-zinc-700 rounded px-2 py-1 text-sm text-zinc-200 " +
          width
        }
      />
    </label>
  );
}

function StatusPill({ status }: { status: string }) {
  const tone =
    {
      idle: "bg-zinc-800 text-zinc-400",
      running: "bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/30",
      complete: "bg-teal-500/20 text-teal-300 ring-1 ring-teal-500/30",
      failed: "bg-rose-500/20 text-rose-300 ring-1 ring-rose-500/30",
    }[status] || "bg-zinc-800";
  return <span className={`px-2 py-0.5 rounded text-xs ${tone}`}>{status}</span>;
}
