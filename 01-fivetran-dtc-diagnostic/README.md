# DTC Brand Health Diagnostic Agent

> When a DTC e-commerce founder asks *"why is my revenue down?"*, this agent autonomously
> sets up Fivetran data connectors across Shopify, Klaviyo, Meta Ads, Google Ads,
> TikTok Ads, Stripe, and reviews — then diagnoses the root cause in 90 seconds.

**Hackathon:** [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/)
**Submission track:** Fivetran
**Deadline:** June 11, 2026 (2:00 PM PDT)
**License:** Apache-2.0 (added at root before submission)

---

## The problem

A DTC (direct-to-consumer) e-commerce brand's "revenue is down" panic is the most
common founder pain in 2026, and it is genuinely hard to diagnose:

- Revenue is the **interaction** of paid acquisition (Meta / Google / TikTok),
  retention (Klaviyo email, SMS), conversion (Shopify funnel, checkout JS), payments
  (Stripe declines), and brand trust (Yotpo / reviews).
- The data lives in **6+ SaaS tools that do not talk to each other**.
- Existing "DTC analytics" tools (Triple Whale, Polar Analytics, Daasity) are
  dashboards. They show numbers. They do not reason. The founder still has to do the
  cross-platform detective work.

The first time a founder hits this, they pay an agency $5K–$20K to investigate, or
they spend two weekends in spreadsheets and Looker.

## The user

**Maya, 32**, founder of *VelvetMint* (a fictional skincare DTC brand we use in the
demo). $1.4M ARR, 2-person team, no full-time data person. She just saw revenue come
in 22% under last month and has 30 minutes between calls to figure out what to do.

## What the agent does

1. **Listens to the question** in plain English: *"Why is my revenue down 22% this month?"*
2. **Inventories the brand's stack** by asking which tools they use, or detecting
   them from existing Fivetran connections via the MCP server.
3. **Wires up missing data pipelines autonomously** — calls `create_connection`,
   `run_connection_setup_tests`, `sync_connection` on the Fivetran MCP server for
   each source (Shopify, Klaviyo, Meta Ads, Google Ads, TikTok Ads, Stripe, Yotpo).
4. **Waits for the first sync window** (or, in the demo, uses pre-warmed data).
5. **Runs a battery of diagnostic queries** in BigQuery — ROAS by channel, list
   decay rate, funnel conversion by browser, refund rate, paid vs. organic mix,
   creative fatigue, etc.
6. **Surfaces 3 ranked findings** with dollar impact and a recommended fix.

The agent's reasoning streams live to the dashboard via SSE so the founder sees the
work being done.

## Why this wins

- **Genuinely impossible without unified data.** Fivetran is load-bearing, not decorative.
- **Uses the Fivetran MCP server in WRITE mode** (`create_connection`, `sync_connection`,
  `modify_connection_schema_config`) — most submissions will use read-only MCP tools.
  Autonomous connector creation is the killer demo move.
- **Fivetran track is among the least crowded** because most hackathon participants
  do not know what Fivetran is.
- **Clean, structured output** that judges can read in 60 seconds: problem → root
  cause → revenue impact → fix.

See [`../DECISION.md`](../DECISION.md) for the full A/B/C scoring vs. the other ideas.

## Stack

| Layer | Tech |
|---|---|
| Agent runtime | Google Cloud **Agent Builder** + **Gemini 3** via Vertex AI |
| MCP server | [Fivetran MCP](https://github.com/fivetran/fivetran-mcp) (HTTP transport, write mode) |
| Agent service | Python 3.11, FastAPI on Cloud Run |
| Data warehouse | BigQuery (Fivetran's destination) |
| State / history | MongoDB Atlas (free tier M0) |
| Webhooks | Cloud Function (`/start-diagnosis`) |
| Frontend | Next.js 15 + shadcn/ui + Tailwind on Cloud Run |
| Streaming | Server-Sent Events (SSE) for live agent reasoning |
| Repo | Public GitHub, Apache-2.0 |

See [`architecture.md`](./architecture.md) for the full system diagram and data flow.

## Demo flow

A staged 3-minute video. Founder Maya types her revenue question; the agent
streams its reasoning, wires up the connectors live, and surfaces three concrete
findings with dollar impact. Then a cut to the GitHub repo + tech stack overlay.

Beat-by-beat in [`demo-script.md`](./demo-script.md).

## Repository layout

```
01-fivetran-dtc-diagnostic/
├── README.md                 (this file)
├── architecture.md           (system diagram, data flow)
├── demo-script.md            (3-minute video script)
├── build-plan.md             (day-by-day, May 24 to June 11)
├── SCAFFOLD-NOTES.md         (what is done, what is stubbed, what is risky)
├── agent/                    (Python service: FastAPI + agent loop + MCP client)
│   ├── README.md
│   ├── pyproject.toml
│   ├── .env.example
│   └── src/agent/
│       ├── __init__.py
│       ├── main.py
│       ├── agent_loop.py
│       ├── tools.py
│       ├── prompts.py
│       ├── diagnostic_engine.py
│       └── config.py
├── frontend/                 (Next.js dashboard, scaffolded later)
│   └── README.md
└── infra/                    (Cloud Run + Cloud Function deploy)
    ├── README.md
    └── cloudbuild.yaml
```

## Status

This is a scaffold. See [`SCAFFOLD-NOTES.md`](./SCAFFOLD-NOTES.md) for what is wired up
versus stubbed. The day-by-day plan in [`build-plan.md`](./build-plan.md) tracks the
work to a working demo.

## Quick start (once env is provisioned)

```bash
cd agent
cp .env.example .env
# Fill in GOOGLE_CLOUD_PROJECT, FIVETRAN_MCP_URL, MONGODB_URI, etc.

python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn agent.main:app --reload --port 8080
```

Then `POST /diagnose` with `{"question": "why is revenue down 22%?"}` and watch the
SSE stream.

## License

Apache-2.0 (will be added at the workspace root before submission, per hackathon
OSI license requirement).
