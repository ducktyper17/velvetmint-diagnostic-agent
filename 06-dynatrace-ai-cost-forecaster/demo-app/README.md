# Refund Assistant — demo workload

Small Gemini-powered support app used as the **observed system** for Agent Reliability
Guard. It exposes a single `/chat` endpoint and emits OpenTelemetry spans with the
tags the guard agent expects:

- `service.name` = `refund-assistant`
- `release_id`
- `prompt_version`
- `tool.name` / `tool.status`
- token usage attributes on spans

## Healthy vs bad deploy

Set `PROMPT_MODE`:

| Value | Behavior |
|---|---|
| `healthy` | One `refund_check` tool call, normal latency |
| `bad` | Up to three `refund_check` retries on ambiguous refunds (token/latency spike) |

Pair with `RELEASE_ID` and `PROMPT_VERSION` headers on each request so Dynatrace DQL
can slice before/after a deploy.

## Setup

```bash
cd demo-app
python -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# fill GOOGLE_CLOUD_PROJECT and Dynatrace OTLP settings if exporting live telemetry
```

## Run

```bash
refund-assistant
# or: uvicorn refund_assistant.main:app --reload --port 8090
```

## Generate traffic

```bash
python scripts/traffic.py --mode healthy --requests 5
python scripts/traffic.py --mode bad --release-id release-2026-05-26-bad-prompt --requests 10
```

## Dynatrace OTLP

Point standard OTel env vars at your tenant (see `.env.example`). Once spans appear in
Dynatrace, run the guard agent against the same `service_name` and `release_id`.
