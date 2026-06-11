"use client";

type Report = any | null;

const DIMS = [
  "empathy",
  "accuracy",
  "escalation",
  "bias",
  "hallucination",
  "brand_voice",
];

export function DeltaReport({ report }: { report: Report }) {
  if (!report) {
    return (
      <section className="rounded-lg border border-zinc-800 bg-ink-900 p-4">
        <h2 className="text-xs uppercase tracking-widest text-zinc-500">
          Final delta report
        </h2>
        <p className="mt-2 text-sm text-zinc-500">
          Will populate when the audit completes (or click{" "}
          <span className="text-plum-400">Show loop report</span> to render a
          pre-computed run).
        </p>
      </section>
    );
  }

  const delta = report.delta || {};
  const cluster = report.top_cluster;
  const mutation = report.mutation;
  const baseRate = report.baseline_pass_rate;
  const postRate = report.post_fix_pass_rate;

  return (
    <section className="rounded-lg border border-zinc-800 bg-ink-900">
      <header className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-zinc-500">
          Final delta report
        </h2>
        {report.audit_job_id && (
          <code className="text-xs text-zinc-500">
            job {String(report.audit_job_id).slice(0, 12)}
          </code>
        )}
      </header>

      {(baseRate !== undefined || postRate !== undefined) && (
        <div className="grid grid-cols-2 divide-x divide-zinc-800 border-b border-zinc-800">
          <PassRate label="Baseline pass rate" value={baseRate} />
          <PassRate
            label="Post-fix pass rate"
            value={postRate}
            highlight={postRate > baseRate}
          />
        </div>
      )}

      {cluster && (
        <div className="px-4 py-3 border-b border-zinc-800">
          <h3 className="text-xs uppercase tracking-widest text-zinc-500 mb-1">
            Top failure cluster
          </h3>
          <p className="text-sm">
            <code className="text-plum-400">{cluster.name}</code>{" "}
            <span className="text-zinc-400">
              ({cluster.count} failures, dims:{" "}
              {(cluster.dimensions_affected || []).join(", ") || "—"})
            </span>
          </p>
          <p className="text-sm text-zinc-300 mt-1">
            {cluster.root_cause_hypothesis || "—"}
          </p>
        </div>
      )}

      {mutation && (
        <div className="px-4 py-3 border-b border-zinc-800">
          <h3 className="text-xs uppercase tracking-widest text-zinc-500 mb-1">
            SUT system-prompt diff
            {Array.isArray(mutation.removed_flaw_lines) &&
              mutation.removed_flaw_lines.length > 0 && (
                <span className="ml-2 text-rose-400 normal-case tracking-normal">
                  −{mutation.removed_flaw_lines.length} flawed{" "}
                  {mutation.removed_flaw_lines.length === 1 ? "rule" : "rules"} removed
                </span>
              )}
          </h3>
          <p className="text-xs text-zinc-400 mb-2">{mutation.rationale || ""}</p>
          <pre className="rounded bg-ink-800 border border-zinc-800 p-2 text-xs whitespace-pre-wrap break-words overflow-x-auto leading-relaxed">
            {Array.isArray(mutation.removed_flaw_lines) &&
              mutation.removed_flaw_lines.map((line: string, i: number) => (
                <div key={`r${i}`} className="text-rose-400">
                  − {line}
                </div>
              ))}
            {mutation.appended && (
              <div className="text-teal-300">+ {mutation.appended}</div>
            )}
          </pre>
        </div>
      )}

      <table className="w-full text-sm">
        <thead className="text-zinc-500 text-xs uppercase tracking-widest">
          <tr>
            <th className="text-left px-4 py-2">Dimension</th>
            <th className="text-right px-4 py-2">Baseline</th>
            <th className="text-right px-4 py-2">Post-fix</th>
            <th className="text-right px-4 py-2">Δ</th>
            <th className="text-right px-4 py-2 pr-6">p</th>
          </tr>
        </thead>
        <tbody>
          {DIMS.map((dim) => {
            const d = delta[dim];
            if (!d) return null;
            // Bias is a paired-A/B dimension; degenerate in single-conversation
            // scoring. Dim it and tag so it doesn't read as a broken 0.00→0.00.
            const isBias = dim === "bias";
            const sign = d.delta == null ? 0 : Math.sign(d.delta);
            return (
              <tr
                key={dim}
                className={
                  "border-t border-zinc-900 " + (isBias ? "opacity-40" : "")
                }
              >
                <td className="px-4 py-2 text-zinc-300">
                  {dim}
                  {isBias && (
                    <span className="ml-1 text-[10px] text-zinc-500">
                      (paired eval)
                    </span>
                  )}
                </td>
                <td className="px-4 py-2 text-right tabular-nums text-zinc-400">
                  {fmt(d.baseline_mean)}
                </td>
                <td className="px-4 py-2 text-right tabular-nums text-zinc-200">
                  {fmt(d.post_fix_mean)}
                </td>
                <td
                  className={
                    "px-4 py-2 text-right tabular-nums " +
                    (sign > 0
                      ? "text-teal-400"
                      : sign < 0
                      ? "text-rose-400"
                      : "text-zinc-500")
                  }
                >
                  {fmtDelta(d.delta)}
                </td>
                <td className="px-4 py-2 pr-6 text-right tabular-nums text-zinc-500">
                  {fmt(d.p_value)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {report.raw && !report.parsed && (
        <div className="px-4 py-3 border-t border-zinc-800">
          <h3 className="text-xs uppercase tracking-widest text-zinc-500 mb-1">
            Agent narrative
          </h3>
          <pre className="text-xs text-zinc-300 whitespace-pre-wrap">
            {String(report.raw)}
          </pre>
        </div>
      )}
    </section>
  );
}

function PassRate({
  label,
  value,
  highlight,
}: {
  label: string;
  value?: number;
  highlight?: boolean;
}) {
  return (
    <div className="px-4 py-3">
      <p className="text-xs uppercase tracking-widest text-zinc-500">{label}</p>
      <p
        className={
          "text-2xl font-semibold " +
          (highlight ? "text-teal-300" : "text-zinc-200")
        }
      >
        {value == null ? "—" : `${Math.round(value * 100)}%`}
      </p>
    </div>
  );
}

function fmt(v: any) {
  if (v == null) return "—";
  if (typeof v !== "number") return String(v);
  return v.toFixed(2);
}

function fmtDelta(v: any) {
  if (v == null) return "—";
  if (typeof v !== "number") return String(v);
  const s = v > 0 ? "+" : "";
  return s + v.toFixed(3);
}
