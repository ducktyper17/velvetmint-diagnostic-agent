"use client";

import { useEffect, useRef } from "react";

export type AgentEvent = {
  type: "thought" | "tool_call" | "tool_result" | "final_report" | "error" | "done" | "message";
  iteration: number;
  ts: number;
  payload: any;
};

export function ThinkingPanel({
  events,
  status,
  error,
}: {
  events: AgentEvent[];
  status: string;
  error: string | null;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [events]);

  return (
    <section className="scan relative rounded-lg border border-zinc-800 bg-ink-900 overflow-hidden">
      <header className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-zinc-500">
          Live agent thinking
        </h2>
        <span className="text-xs text-zinc-500">
          {events.length} event{events.length === 1 ? "" : "s"}
        </span>
      </header>
      <div
        ref={scrollRef}
        className="h-[360px] overflow-y-auto px-4 py-3 font-mono text-sm leading-relaxed"
      >
        {events.length === 0 && status === "idle" && (
          <p className="text-zinc-500">
            Press <span className="text-bondi-400">Investigate</span> to start.
            The guard agent will query Dynatrace for runtime signals, run change
            and forecast analyzers, draft an evidence notebook, and notify the
            owner — narrating each step live, here.
          </p>
        )}
        {events.map((ev, i) => (
          <EventLine key={i} ev={ev} />
        ))}
        {status === "running" && (
          <div className="text-bondi-400/70 animate-pulse">▍</div>
        )}
        {error && (
          <p className="mt-3 text-rose-400 whitespace-pre-wrap">error: {error}</p>
        )}
      </div>
    </section>
  );
}

function EventLine({ ev }: { ev: AgentEvent }) {
  const color = colorFor(ev.type);
  return (
    <div className="flex gap-3 py-0.5">
      <span className="text-zinc-600 select-none w-[64px] shrink-0">
        {new Date(ev.ts).toLocaleTimeString().slice(0, 8)}
      </span>
      <span className={color + " whitespace-pre-wrap break-words"}>
        {summarize(ev)}
      </span>
    </div>
  );
}

function colorFor(type: AgentEvent["type"]) {
  switch (type) {
    case "thought":
      return "text-zinc-200";
    case "tool_call":
      return "text-bondi-400";
    case "tool_result":
      return "text-teal-400";
    case "final_report":
      return "text-amber-300";
    case "error":
      return "text-rose-400";
    case "done":
      return "text-zinc-500";
    default:
      return "text-zinc-400";
  }
}

function summarize(ev: AgentEvent): string {
  const p = ev.payload || {};
  switch (ev.type) {
    case "thought":
      return `· ${p.text || "(no thought)"}`;
    case "tool_call":
      return `→ ${p.name}(${prettyArgs(p.args)})`;
    case "tool_result":
      return `← ${p.name}: ${shortResult(p.result)}`;
    case "final_report":
      return `★ final: ${p.summary || ""}`;
    case "error":
      return `✗ ${p.error || "error"}`;
    case "done":
      return `done (${p.reason || ""})`;
    default:
      return JSON.stringify(p).slice(0, 240);
  }
}

function prettyArgs(args: any) {
  if (!args) return "";
  const out: string[] = [];
  for (const [k, v] of Object.entries(args)) {
    if (k === "thought") continue;
    out.push(
      `${k}=${
        typeof v === "string" ? `"${v.slice(0, 30)}"` : JSON.stringify(v).slice(0, 30)
      }`
    );
  }
  return out.join(", ");
}

function shortResult(r: any) {
  if (!r) return "(empty)";
  if (typeof r === "string") return r.slice(0, 200);
  if (r.summary) return r.summary;
  if (r.verdict) return r.verdict;
  if (r.url) return r.url;
  if (r.delivery) return `${r.channel} (${r.delivery})`;
  return JSON.stringify(r).slice(0, 200);
}
