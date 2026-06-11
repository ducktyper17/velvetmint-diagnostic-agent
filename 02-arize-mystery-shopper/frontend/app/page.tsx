"use client";

import { useEffect, useRef, useState } from "react";
import { ThinkingPanel } from "@/components/ThinkingPanel";
import { DeltaReport } from "@/components/DeltaReport";
import { PhoenixPanel } from "@/components/PhoenixPanel";

type AuditEvent = { kind: string; summary: string; raw: any; ts: number };

type Report = any | null;

export default function Page() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "running" | "complete" | "failed">("idle");
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [report, setReport] = useState<Report>(null);
  const [error, setError] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => sourceRef.current?.close();
  }, []);

  async function startAudit() {
    setStatus("running");
    setEvents([]);
    setReport(null);
    setError(null);

    try {
      const res = await fetch("/api/proxy/audit", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ sut_id: "velvetmint-support-v1", mode: "one_cycle" }),
      });
      if (!res.ok) throw new Error(`audit kickoff failed: ${res.status}`);
      const data = await res.json();
      setJobId(data.id);

      const es = new EventSource(`/api/proxy/audit/${data.id}/events`);
      sourceRef.current = es;
      es.addEventListener("thinking", (ev: MessageEvent) => {
        try {
          const raw = JSON.parse(ev.data);
          setEvents((prev) => [
            ...prev,
            {
              kind: summarizeEventKind(raw),
              summary: summarizeEvent(raw),
              raw,
              ts: Date.now(),
            },
          ]);
        } catch {
          /* ignore */
        }
      });
      es.addEventListener("done", async (ev: MessageEvent) => {
        try {
          const payload = JSON.parse(ev.data);
          setStatus(payload.status === "complete" ? "complete" : "failed");
          if (payload.error) setError(payload.error);
        } catch {}
        es.close();
        try {
          const rep = await fetch(`/api/proxy/audit/${data.id}/report`);
          if (rep.ok) setReport(await rep.json());
        } catch {}
      });
    } catch (e: any) {
      setError(e?.message || String(e));
      setStatus("failed");
    }
  }

  async function loadLoopReport() {
    setReport(null);
    setError(null);
    setStatus("running");
    // The backend scales to zero on Cloud Run; the first request after idle
    // can cold-start (and briefly 5xx). Retry a few times with backoff so a
    // single click "just works" instead of surfacing a transient error.
    const maxAttempts = 6;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const rep = await fetch("/api/proxy/loop/report", { cache: "no-store" });
        if (rep.ok) {
          setReport(await rep.json());
          setStatus("complete");
          return;
        }
      } catch {
        /* transient during cold start — fall through to retry */
      }
      if (attempt === maxAttempts) {
        setStatus("failed");
        setError(
          "Waking the demo backend (Cloud Run cold start). Give it a few seconds and click again."
        );
        return;
      }
      await new Promise((r) => setTimeout(r, 1500 * attempt));
    }
  }

  return (
    <div className="grid grid-rows-[auto_1fr] min-h-screen">
      <Header status={status} onStart={startAudit} onLoadLoop={loadLoopReport} />
      <main className="grid grid-cols-12 gap-4 p-4">
        <section className="col-span-12 lg:col-span-7 flex flex-col gap-4">
          <ThinkingPanel events={events} status={status} error={error} />
          <DeltaReport report={report} />
        </section>
        <aside className="col-span-12 lg:col-span-5">
          <PhoenixPanel />
        </aside>
      </main>
    </div>
  );
}

function Header({
  status,
  onStart,
  onLoadLoop,
}: {
  status: string;
  onStart: () => void;
  onLoadLoop: () => void;
}) {
  return (
    <header className="border-b border-zinc-800 bg-ink-900/80 backdrop-blur">
      <div className="max-w-screen-2xl mx-auto px-4 py-3 flex items-center gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            <span className="text-plum-400 glow">Self-Improving QA Agent</span>
          </h1>
          <p className="text-xs text-zinc-500 -mt-0.5">
            The AI quality engineer that never sleeps. Audits a Gemini agent,
            rewrites its prompts via Phoenix MCP, proves a score delta.
          </p>
        </div>
        <div className="grow" />
        <StatusPill status={status} />
        <button
          className="rounded-md bg-plum-500/90 hover:bg-plum-500 text-ink-950 font-medium text-sm px-3 py-1.5 transition"
          onClick={onStart}
          disabled={status === "running"}
        >
          {status === "running" ? "Auditing…" : "Run audit"}
        </button>
        <button
          className="rounded-md border border-zinc-700 hover:border-zinc-500 text-zinc-300 text-sm px-3 py-1.5 transition"
          onClick={onLoadLoop}
        >
          Show loop report
        </button>
      </div>
    </header>
  );
}

function StatusPill({ status }: { status: string }) {
  const tone = {
    idle: "bg-zinc-800 text-zinc-400",
    running: "bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/30",
    complete: "bg-teal-500/20 text-teal-300 ring-1 ring-teal-500/30",
    failed: "bg-rose-500/20 text-rose-300 ring-1 ring-rose-500/30",
  }[status] || "bg-zinc-800";
  return <span className={`px-2 py-0.5 rounded text-xs ${tone}`}>{status}</span>;
}

function summarizeEventKind(raw: any): string {
  if (!raw) return "event";
  if (raw.tool_calls?.length) return "tool";
  if (raw.function_call) return "tool";
  if (raw.text || raw.content) return "model";
  return raw.author || "event";
}

function summarizeEvent(raw: any): string {
  if (!raw) return "(empty event)";
  // Common ADK event shapes
  if (raw.content?.parts) {
    const txt = raw.content.parts
      .map((p: any) => p?.text)
      .filter(Boolean)
      .join(" ")
      .trim();
    if (txt) return txt;
    const tool = raw.content.parts.find((p: any) => p?.function_call);
    if (tool) return `→ tool ${tool.function_call.name}(${prettyArgs(tool.function_call.args)})`;
    const toolResp = raw.content.parts.find((p: any) => p?.function_response);
    if (toolResp) return `← ${toolResp.function_response.name} returned`;
  }
  if (raw.author && raw.partial !== undefined) return `${raw.author}: …`;
  return JSON.stringify(raw).slice(0, 280);
}

function prettyArgs(args: any) {
  if (!args) return "";
  try {
    return Object.entries(args)
      .map(([k, v]) => `${k}=${typeof v === "string" ? `"${v.slice(0, 40)}"` : JSON.stringify(v).slice(0, 40)}`)
      .join(", ");
  } catch {
    return "";
  }
}
