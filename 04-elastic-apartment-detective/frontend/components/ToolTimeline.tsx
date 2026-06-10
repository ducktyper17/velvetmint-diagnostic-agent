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
          Elastic MCP tool calls
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
      <ToolKind name={pair.name} />
      <StatusDot status={pair.status} />
    </div>
  );
}

// Badge that makes the hybrid-vs-structured retrieval story legible to judges.
function ToolKind({ name }: { name: string }) {
  const kind =
    name === "search_tenant_sentiment"
      ? { label: "hybrid", tone: "bg-bondi-500/15 text-bondi-400" }
      : name === "search_building_memory"
      ? { label: "memory", tone: "bg-amber-500/15 text-amber-300" }
      : name === "save_building_brief"
      ? { label: "writeback", tone: "bg-amber-500/15 text-amber-300" }
      : { label: "ES|QL", tone: "bg-teal-500/15 text-teal-300" };
  return (
    <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-mono ${kind.tone}`}>
      {kind.label}
    </span>
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
    out.push(`${k}=${typeof v === "string" ? v.slice(0, 48) : JSON.stringify(v).slice(0, 48)}`);
  }
  return out.join(" · ");
}

function resultLine(name: string, r: any) {
  switch (name) {
    case "search_building_memory":
      return r.found ? `prior brief · risk ${r.prior_risk_score ?? "?"}` : "no prior brief";
    case "get_hpd_violations":
      return `${r.open_violations ?? 0} open violations`;
    case "get_311_signals":
      return `${r.complaint_count_90d ?? 0} complaints/90d`;
    case "search_tenant_sentiment":
      return `${r.mentions_found ?? 0} mentions`;
    case "compare_to_neighborhood_baseline":
      return r.summary || `${(r.complaint_index_vs_zip ?? 1).toFixed(1)}× baseline`;
    case "save_building_brief":
      return r.stored ? `saved → ${r.document_id}` : "save failed";
    default:
      if (r?.summary) return r.summary;
      if (r?.error) return `error: ${r.error}`;
      return JSON.stringify(r).slice(0, 160);
  }
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
