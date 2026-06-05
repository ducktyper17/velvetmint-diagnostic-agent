# Self-Improving QA Agent — frontend

Minimal Next.js 14 (App Router) dashboard that renders the QA agent's
live thinking trace, the embedded Phoenix workspace, and the final
delta report.

## Quick start

```bash
cd frontend
npm install        # or pnpm install
BACKEND_URL=http://localhost:8080 npm run dev
# open http://localhost:3000
```

The frontend proxies every request through `/api/proxy/*` to `BACKEND_URL`
so CORS does not have to be configured separately on the FastAPI side and
so SSE streams pass through untouched.

## Configuration

| Env var | Default | What it does |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8080` | FastAPI backend root (set to the Cloud Run URL in prod). |
| `NEXT_PUBLIC_PHOENIX_URL` | `https://app.phoenix.arize.com` | URL embedded in the Phoenix iframe. Set this to your space URL for the demo (`.../s/<your-space>`). |

## Layout

- **Top left:** Live thinking panel — SSE stream of ADK events.
- **Bottom left:** Final delta report (per-dimension table + prompt diff).
- **Right column:** Embedded Phoenix UI so judges can click into any trace.

## Production deploy

We deploy this as a separate Cloud Run service (`make deploy-frontend` at the
project root) pointed at the Cloud Run backend URL via `BACKEND_URL`.
