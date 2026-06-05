# Mock SaaS Server

Small FastAPI service that exposes the synthetic VelvetMint data over plain
HTTP endpoints.

Why this exists:

- We can build the agent loop before the real Fivetran trial is live.
- It gives us deterministic local/demo data with stable URLs.
- Later, we can use the same service for demo-mode replays and connector mocks.

## Endpoints

- `GET /healthz`
- `GET /datasets`
- `GET /shopify/orders`
- `GET /shopify/checkouts`
- `GET /shopify/customers`
- `GET /klaviyo/profiles`
- `GET /klaviyo/campaigns`
- `GET /klaviyo/flows`
- `GET /meta-ads/campaigns`
- `GET /meta-ads/insights`
- `GET /google-ads/campaigns`
- `GET /google-ads/insights`
- `GET /tiktok-ads/ads`
- `GET /tiktok-ads/insights`
- `GET /stripe/charges`
- `GET /stripe/refunds`
- `GET /yotpo/reviews`

Every dataset endpoint supports:

- `limit` / `offset`
- `start_date=YYYY-MM-DD`
- `end_date=YYYY-MM-DD`
- `field=name&value=...` for a simple equality filter

## Local run

From this directory:

```bash
uv run velvetmint-mock-saas
```

Or:

```bash
python -m uvicorn mock_saas.main:app --app-dir src --host 0.0.0.0 --port 8080
```

Example requests:

```bash
curl http://localhost:8080/healthz
curl "http://localhost:8080/shopify/orders?limit=5"
curl "http://localhost:8080/tiktok-ads/insights?start_date=2026-05-01&end_date=2026-05-10"
curl "http://localhost:8080/klaviyo/profiles?field=source&value=popup&limit=10"
```

## Cloud Run

Build from the **repo root** so the image can include `synthetic-data/`:

```bash
gcloud run deploy velvetmint-mock-saas \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

Or with Docker directly from the repo root:

```bash
docker build -f 01-fivetran-dtc-diagnostic/mock-saas/Dockerfile -t velvetmint-mock-saas .
docker run -p 8080:8080 velvetmint-mock-saas
```

If you deploy from a non-root context, set:

```bash
export SYNTHETIC_DATA_ROOT=/path/to/synthetic-data
```

The app reads that env var first and falls back to the checked-in local path.
This service is intentionally read-only and serves only the synthetic dataset.
