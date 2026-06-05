"use client";

import { useState } from "react";

const DEFAULT_PHOENIX_URL =
  process.env.NEXT_PUBLIC_PHOENIX_URL ||
  "https://app.phoenix.arize.com";

export function PhoenixPanel() {
  const [url, setUrl] = useState(DEFAULT_PHOENIX_URL);
  const [showInput, setShowInput] = useState(false);

  return (
    <section className="rounded-lg border border-zinc-800 bg-ink-900 overflow-hidden h-full flex flex-col">
      <header className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-zinc-500">
          Phoenix workspace
        </h2>
        <button
          className="text-xs text-zinc-500 hover:text-plum-400 transition"
          onClick={() => setShowInput((v) => !v)}
        >
          {showInput ? "hide" : "set URL"}
        </button>
      </header>
      {showInput && (
        <div className="px-3 py-2 border-b border-zinc-800 bg-ink-800">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://app.phoenix.arize.com/s/your-space"
            className="w-full bg-ink-950 border border-zinc-700 rounded px-2 py-1 text-xs"
          />
        </div>
      )}
      <iframe
        title="Arize Phoenix"
        src={url}
        className="grow w-full bg-ink-950"
        sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
      />
      <footer className="px-4 py-2 border-t border-zinc-800 text-xs text-zinc-500">
        Click into any trace, dataset, prompt version, or experiment row — Phoenix
        is the canonical record of every audit.
      </footer>
    </section>
  );
}
