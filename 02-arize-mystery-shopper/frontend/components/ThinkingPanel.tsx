"use client";

import { useEffect, useRef } from "react";

type AuditEvent = { kind: string; summary: string; raw: any; ts: number };

export function ThinkingPanel({
  events,
  status,
  error,
}: {
  events: AuditEvent[];
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
    <section className="thinking-panel relative rounded-lg border border-zinc-800 bg-ink-900 overflow-hidden">
      <header className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-zinc-500">
          Live thinking
        </h2>
        <span className="text-xs text-zinc-500">
          {events.length} {events.length === 1 ? "event" : "events"}
        </span>
      </header>
      <div
        ref={scrollRef}
        className="h-[420px] overflow-y-auto px-4 py-3 font-mono text-sm leading-relaxed"
      >
        {events.length === 0 && status === "idle" && (
          <p className="text-zinc-500">
            Press <span className="text-plum-400">Run audit</span> to start. The QA
            agent will run all scenarios against the SUT, introspect failures via
            Phoenix MCP, rewrite the SUT's system prompt, re-run, and report the
            score delta — live, here.
          </p>
        )}
        {events.map((ev, i) => (
          <EventLine key={i} ev={ev} />
        ))}
        {status === "running" && (
          <div className="text-plum-400/70 animate-pulse">▍</div>
        )}
        {error && (
          <p className="mt-3 text-rose-400 whitespace-pre-wrap">error: {error}</p>
        )}
      </div>
    </section>
  );
}

function EventLine({ ev }: { ev: AuditEvent }) {
  const isToolCall = ev.summary.startsWith("→");
  const isToolReturn = ev.summary.startsWith("←");
  const color = isToolCall
    ? "text-teal-400"
    : isToolReturn
    ? "text-teal-500"
    : "text-zinc-200";
  return (
    <div className="flex gap-3 py-0.5">
      <span className="text-zinc-600 select-none w-[60px] shrink-0">
        {new Date(ev.ts).toLocaleTimeString().slice(0, 8)}
      </span>
      <span className={color + " whitespace-pre-wrap break-words"}>
        {ev.summary}
      </span>
    </div>
  );
}
