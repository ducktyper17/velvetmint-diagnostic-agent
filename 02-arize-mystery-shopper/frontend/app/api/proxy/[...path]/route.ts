import { NextRequest } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8080";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

async function handle(req: NextRequest, ctx: { params: { path: string[] } }) {
  const url = `${BACKEND}/${ctx.params.path.join("/")}${
    req.nextUrl.search || ""
  }`;

  const init: RequestInit = {
    method: req.method,
    headers: forwardHeaders(req),
    body: ["GET", "HEAD"].includes(req.method) ? undefined : await req.text(),
    // @ts-ignore -- supported in Node fetch
    cache: "no-store",
  };

  const upstream = await fetch(url, init);
  // Stream the body straight through; SSE works because we pass the
  // ReadableStream untouched and preserve content-type: text/event-stream.
  return new Response(upstream.body, {
    status: upstream.status,
    headers: copyHeaders(upstream.headers),
  });
}

function forwardHeaders(req: NextRequest): HeadersInit {
  const out: Record<string, string> = {};
  req.headers.forEach((v, k) => {
    if (["host", "connection", "content-length"].includes(k.toLowerCase())) return;
    out[k] = v;
  });
  return out;
}

function copyHeaders(headers: Headers): HeadersInit {
  const out: Record<string, string> = {};
  headers.forEach((v, k) => {
    if (k.toLowerCase() === "transfer-encoding") return;
    out[k] = v;
  });
  return out;
}

export { handle as GET, handle as POST, handle as PUT, handle as DELETE };
