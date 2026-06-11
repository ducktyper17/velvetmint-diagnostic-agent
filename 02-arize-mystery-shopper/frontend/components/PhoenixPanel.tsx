"use client";

const PHOENIX_URL =
  process.env.NEXT_PUBLIC_PHOENIX_URL || "https://app.phoenix.arize.com/s/ghac";

// Phoenix Cloud sets X-Frame-Options / CSP frame-ancestors that block being
// embedded in an iframe, so we render a deep-link card instead of a broken
// frame. The card lists exactly what lives in the workspace so a reviewer
// knows what they'll see when they click through.
const ARTIFACTS: { label: string; detail: string }[] = [
  { label: "Datasets", detail: "velvetmint-support.scenarios — 30 versioned test scenarios" },
  { label: "Prompts", detail: "sut-velvetmint-support v1 → v2, plus 6 judge prompts" },
  { label: "Experiments", detail: "baseline vs post-fix, 6 dimensions × replicas" },
  { label: "Traces & sessions", detail: "every SUT turn auto-instrumented via OpenInference" },
];

export function PhoenixPanel() {
  return (
    <section className="rounded-lg border border-zinc-800 bg-ink-900 overflow-hidden h-full flex flex-col">
      <header className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-zinc-500">
          Phoenix workspace
        </h2>
        <span className="text-xs text-zinc-600">canonical record</span>
      </header>

      <div className="grow p-4 flex flex-col gap-4">
        <p className="text-sm text-zinc-300">
          Every audit is written to Arize Phoenix as first-class objects. The
          QA agent reads and writes them at runtime through the Phoenix MCP
          server — Phoenix is the system of record, not just a viewer.
        </p>

        <ul className="flex flex-col gap-2">
          {ARTIFACTS.map((a) => (
            <li
              key={a.label}
              className="rounded border border-zinc-800 bg-ink-800 px-3 py-2"
            >
              <p className="text-sm font-medium text-plum-300">{a.label}</p>
              <p className="text-xs text-zinc-400">{a.detail}</p>
            </li>
          ))}
        </ul>

        <a
          href={PHOENIX_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-auto inline-flex items-center justify-center rounded-md bg-plum-500/90 hover:bg-plum-500 text-ink-950 font-medium text-sm px-3 py-2 transition"
        >
          Open the live Phoenix workspace →
        </a>
      </div>

      <footer className="px-4 py-2 border-t border-zinc-800 text-xs text-zinc-500">
        Open Phoenix to click into any trace, dataset, prompt version, or
        experiment row — the full audit trail is reproducible there.
      </footer>
    </section>
  );
}
