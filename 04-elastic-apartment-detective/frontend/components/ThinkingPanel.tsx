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
          Live investigation
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
            Paste a StreetEasy or Zillow link and press{" "}
            <span className="text-bondi-400">Investigate</span>. The detective
            queries Elastic for HPD violations, 311 complaints, and tenant
            sentiment, compares the building to its neighborhood, then writes a
            renter-risk brief — narrating each step live, here.
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
      return `← ${p.name}: ${shortResult(p.name, p.result)}`;
    case "final_report":
      return `★ brief: ${p.summary || ""}`;
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
        typeof v === "string" ? `"${v.slice(0, 40)}"` : JSON.stringify(v).slice(0, 40)
      }`
    );
  }
  return out.join(", ");
}

// One-line, human summary of each Elastic tool result shape.
function shortResult(name: string, r: any): string {
  if (!r) return "(empty)";
  switch (name) {
    case "search_building_memory":
      return r.found
        ? `prior brief found · risk ${r.prior_risk_score ?? "?"} · ${(r.prior_flags || []).join(", ")}`
        : "no prior brief for this address";
    case "get_hpd_violations":
      return `${r.open_violations ?? 0} open violations · ${(r.severe_categories || []).join(", ")}`;
    case "get_311_signals":
      return `${r.complaint_count_90d ?? 0} complaints/90d · ${Math.round(
        (r.nighttime_noise_share ?? 0) * 100
      )}% late-night · ${(r.top_categories || []).slice(0, 3).join(", ")}`;
    case "search_tenant_sentiment":
      return `${r.mentions_found ?? 0} tenant mentions found`;
    case "compare_to_neighborhood_baseline":
      return `${(r.complaint_index_vs_zip ?? 1).toFixed(1)}× vs ZIP baseline`;
    case "save_building_brief":
      return r.stored ? `brief saved → ${r.document_id}` : "save failed";
    default:
      if (typeof r === "string") return r.slice(0, 200);
      if (r.summary) return r.summary;
      return JSON.stringify(r).slice(0, 200);
  }
}
