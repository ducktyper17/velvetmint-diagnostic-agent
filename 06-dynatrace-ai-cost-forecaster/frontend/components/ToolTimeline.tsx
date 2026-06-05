"use client";

import type { AgentEvent } from "@/components/ThinkingPanel";

type ToolPair = {
  iteration: number;
  name: string;
  args: any;
  result?: any;
  status: "pending" | "ok" | "error";
};

export function ToolTimeline({ events }: { events: AgentEvent[] }) {
  const pairs = pairToolEvents(events);
  if (!pairs.length) return null;

  return (
    <section className="rounded-lg border border-zinc-800 bg-ink-900">
      <header className="px-4 py-2 border-b border-zinc-800">
        <h2 className="text-xs uppercase tracking-widest text-zinc-500">
          Dynatrace MCP tool calls
        </h2>
      </header>
      <div className="divide-y divide-zinc-900">
        {pairs.map((p, i) => (
          <ToolRow key={i} pair={p} />
        ))}
      </div>
    </section>
  );
}

function ToolRow({ pair }: { pair: ToolPair }) {
  return (
    <div className="px-4 py-2 flex items-start gap-3 text-sm">
      <span className="w-6 text-zinc-600 text-xs tabular-nums">{pair.iteration}</span>
      <code className="text-bondi-400 font-mono shrink-0">{pair.name}</code>
      <div className="grow min-w-0">
        <p className="text-xs text-zinc-500 font-mono truncate">
          {kvPreview(pair.args)}
        </p>
        {pair.result && (
          <p className="text-xs text-zinc-300 mt-0.5 truncate">
            {resultLine(pair.name, pair.result)}
          </p>
        )}
      </div>
      <StatusDot status={pair.status} />
    </div>
  );
}

function StatusDot({ status }: { status: ToolPair["status"] }) {
  const color =
    status === "ok"
      ? "bg-teal-400"
      : status === "error"
      ? "bg-rose-500"
      : "bg-amber-400 animate-pulse";
  return <span className={`mt-1 inline-block w-2 h-2 rounded-full ${color}`} />;
}

function kvPreview(args: any) {
  if (!args) return "";
  const out: string[] = [];
  for (const [k, v] of Object.entries(args)) {
    if (k === "thought") continue;
    out.push(`${k}=${typeof v === "string" ? v.slice(0, 40) : JSON.stringify(v).slice(0, 40)}`);
  }
  return out.join(" · ");
}

function resultLine(name: string, r: any) {
  if (r?.summary) return r.summary;
  if (r?.verdict) return r.verdict;
  if (r?.url) return `notebook → ${r.url}`;
  if (r?.delivery) return `${r.channel} → ${r.delivery}`;
  if (r?.error) return `error: ${r.error}`;
  return JSON.stringify(r).slice(0, 180);
}

function pairToolEvents(events: AgentEvent[]): ToolPair[] {
  const out: ToolPair[] = [];
  for (const ev of events) {
    if (ev.type === "tool_call") {
      out.push({
        iteration: ev.iteration,
        name: ev.payload.name,
        args: ev.payload.args,
        status: "pending",
      });
    } else if (ev.type === "tool_result") {
      const match = out.slice().reverse().find((p) => p.name === ev.payload.name && !p.result);
      if (match) {
        match.result = ev.payload.result;
        match.status = match.result?.error ? "error" : "ok";
      }
    }
  }
  return out;
}
