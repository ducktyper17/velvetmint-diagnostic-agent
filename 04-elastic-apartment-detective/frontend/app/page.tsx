"use client";

import { useEffect, useRef, useState } from "react";
import { ThinkingPanel, type AgentEvent } from "@/components/ThinkingPanel";
import { ToolTimeline } from "@/components/ToolTimeline";
import { EvidenceStrip } from "@/components/EvidenceStrip";
import { RiskBrief, type FinalReport } from "@/components/RiskBrief";

const DEMO_URL =
  "https://streeteasy.example/listing/123-orchard-st-new-york-ny-10002";

export default function Page() {
  const [listingUrl, setListingUrl] = useState(DEMO_URL);
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<"idle" | "running" | "complete" | "failed">("idle");
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [finalReport, setFinalReport] = useState<FinalReport>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  async function startInvestigation(followUp?: string) {
    setStatus("running");
    setEvents([]);
    setFinalReport(null);
    setError(null);

    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    try {
      const body = JSON.stringify({
        listing_url: listingUrl || undefined,
        question: (followUp ?? question) || undefined,
      });

      // EventSource can't POST, so we POST with fetch and read the SSE stream
      // off the response body manually below.
      const res = await fetch(`/api/proxy/investigate`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body,
        signal: ac.signal,
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
      if (e?.name === "AbortError") return;
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
        listing: data.listing,
        risk_score: data.risk_score,
        confidence: data.confidence,
        confidence_rationale: data.confidence_rationale,
        summary: data.summary,
        top_red_flags: data.top_red_flags || [],
        questions_to_ask: data.questions_to_ask || [],
        evidence: data.evidence || [],
      });
    }
    if (eventName === "done") setStatus("complete");
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
        listingUrl={listingUrl}
        status={status}
        onListingUrl={setListingUrl}
        onStart={() => startInvestigation()}
      />
      <main className="grid grid-cols-12 gap-4 p-4 content-start max-w-screen-2xl mx-auto w-full">
        <div className="col-span-12">
          <EvidenceStrip events={events} />
        </div>
        <section className="col-span-12 lg:col-span-7 flex flex-col gap-4">
          <ThinkingPanel events={events} status={status} error={error} />
          <ToolTimeline events={events} />
        </section>
        <aside className="col-span-12 lg:col-span-5 flex flex-col gap-4">
          <RiskBrief report={finalReport} status={status} />
          {finalReport && (
            <FollowUp
              question={question}
              disabled={status === "running"}
              onQuestion={setQuestion}
              onAsk={() => startInvestigation()}
            />
          )}
        </aside>
      </main>
    </div>
  );
}

function Header(props: {
  listingUrl: string;
  status: string;
  onListingUrl: (v: string) => void;
  onStart: () => void;
}) {
  return (
    <header className="border-b border-zinc-800 bg-ink-900/80 backdrop-blur sticky top-0 z-10">
      <div className="max-w-screen-2xl mx-auto px-4 py-3 flex flex-wrap items-center gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            <span className="text-bondi-400 glow-bondi">Apartment Detective</span>
          </h1>
          <p className="text-xs text-zinc-500 -mt-0.5">
            Paste a listing. Get the truth before you sign. Powered by Gemini +
            Elastic over NYC HPD, 311, and tenant signals.
          </p>
        </div>
        <div className="grow" />
        <label className="text-xs text-zinc-500 flex flex-col grow max-w-xl">
          <span className="ml-1">StreetEasy / Zillow listing URL</span>
          <input
            value={props.listingUrl}
            onChange={(e) => props.onListingUrl(e.target.value)}
            placeholder="https://streeteasy.com/building/..."
            className="bg-ink-800 border border-zinc-700 rounded px-2 py-1.5 text-sm text-zinc-200 w-full"
            onKeyDown={(e) => e.key === "Enter" && props.onStart()}
          />
        </label>
        <StatusPill status={props.status} />
        <button
          className="rounded-md bg-bondi-500/90 hover:bg-bondi-500 text-ink-950 font-medium text-sm px-4 py-2 transition disabled:opacity-50"
          onClick={props.onStart}
          disabled={props.status === "running"}
        >
          {props.status === "running" ? "Investigating…" : "Investigate"}
        </button>
      </div>
    </header>
  );
}

function FollowUp(props: {
  question: string;
  disabled: boolean;
  onQuestion: (v: string) => void;
  onAsk: () => void;
}) {
  return (
    <section className="rounded-lg border border-zinc-800 bg-ink-900 p-4">
      <p className="text-[11px] uppercase tracking-widest text-zinc-500 mb-2">
        Ask a follow-up
      </p>
      <div className="flex gap-2">
        <input
          value={props.question}
          onChange={(e) => props.onQuestion(e.target.value)}
          placeholder="e.g. What's the biggest concern if I work nights?"
          className="bg-ink-800 border border-zinc-700 rounded px-2 py-1.5 text-sm text-zinc-200 grow"
          onKeyDown={(e) => e.key === "Enter" && !props.disabled && props.onAsk()}
        />
        <button
          className="rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm px-3 py-1.5 transition disabled:opacity-50"
          onClick={props.onAsk}
          disabled={props.disabled || !props.question.trim()}
        >
          Ask
        </button>
      </div>
      <p className="text-[11px] text-zinc-600 mt-2">
        Reuses the stored Elastic brief instead of re-running the full
        investigation.
      </p>
    </section>
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
