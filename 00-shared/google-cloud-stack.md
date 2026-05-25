# Google Cloud stack — what we use and why

Sources: [Resources page](https://rapid-agent.devpost.com/resources), [Gemini Enterprise Agent Platform product page](https://cloud.google.com/products/gemini-enterprise-agent-platform), [Scale your agents docs](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale), [Cloud Run quickstarts](https://docs.cloud.google.com/run/docs/quickstarts), [Secret Manager](https://cloud.google.com/security/products/secret-manager), [Agent Starter Pack](https://github.com/GoogleCloudPlatform/agent-starter-pack), [Responsible AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/responsible-ai).

This doc names every GCP product we'll actually touch, in build order, and resolves the recent renames so we don't waste time looking for "Vertex AI" or "Agent Builder" under the old names.

---

## Critical naming changes (Vertex AI → Gemini Enterprise Agent Platform)

Vertex AI was rebranded to **Gemini Enterprise Agent Platform** in 2026. Documentation still mixes the names. The rules and partner pages all say "Agent Builder" / "Vertex AI" — those refer to the same product now sold as Agent Platform. The current console layout puts everything under **Agent Platform → Studio** (this is what the forum users are looking for when they ask "where is Agent Builder").

| Old name | New name | Where it lives now |
|---|---|---|
| Vertex AI | **Gemini Enterprise Agent Platform** | console.cloud.google.com/agent-platform |
| Vertex AI Agent Builder | **Agent Platform → Studio** + **Agent Builder** (low-code) | Agent Studio (visual), Agent Builder (low-code workflow) |
| Vertex AI Agent Engine | **Agent Runtime** | Agent Platform → Runtime |
| Vertex AI Model Garden | **Model Garden** (unchanged) | 200+ models including Gemini 3, Gemma, Claude (do NOT use Claude per hackathon rules) |

## Three build-environment paths (we pick one)

Per the [Resources page](https://rapid-agent.devpost.com/resources), Phase 1 gives three options:

| Path | Best when | What you write |
|---|---|---|
| **Agent Builder (low-code)** | demo-heavy workflows with managed grounding, data stores, orchestration | configuration in a UI, light Python |
| **Agent Studio (managed API)** | need full control of Gemini calls + tool routing but want hosted infra | Python via `google-cloud-aiplatform` SDK |
| **Gemini Enterprise Agent Platform SDK / ADK (code-owned)** | want full control, custom orchestration loops, traces | Python with ADK, deploy to Agent Runtime or Cloud Run |

**Our choice: code-owned (ADK + Cloud Run).** Reasons:
1. Tiebreaker on judging is Technological Implementation first (see `hackathon-rules.md` §8). Code-owned shows engineering depth.
2. The Arize backup track *requires* code-owned (Agent Builder UI isn't supported for tracing). Keeping our architecture code-owned preserves optionality if we pivot.
3. We need precise control over the SSE streaming UX (live reasoning trace shown to the user). Low-code platforms hide that.

## The full GCP stack we'll touch

### Compute & hosting

| Service | What we use it for | Cost during build |
|---|---|---|
| **Cloud Run** | Hosts the agent backend (FastAPI Python) and the frontend (Next.js). Also hosts our forked Fivetran MCP server as a separate service. | Pay-per-request, free tier covers demo traffic. |
| **Cloud Functions** | Optional thin webhook trigger (`/start-diagnosis`) — see architecture doc. | Free tier covers it. |
| **Cloud Build** | CI/CD: builds container images on push to GitHub. | Free tier (120 build-min/day). |
| **Artifact Registry** | Stores our built container images. | Negligible at our scale. |

Reference: [Cloud Run quickstarts](https://docs.cloud.google.com/run/docs/quickstarts) — includes Python FastAPI, Smolagents, LangChain, **ADK for Python**, and a [Cloud Run remote MCP server quickstart](https://docs.cloud.google.com/run/docs/quickstarts) we'll use for hosting our Fivetran MCP fork.

### Agent + AI

| Service | What we use it for |
|---|---|
| **Gemini 3** (via Vertex AI / Agent Platform SDK) | Agent reasoning model. Gemini 3 Pro (text), possibly Gemini 3 Pro Image (Nano Banana Pro) if we want visualization, Gemini 3 Pro Multimodal if we accept screenshot inputs. |
| **Agent Development Kit (ADK) for Python** | Agent loop scaffolding. Has built-in support for tool calling, multi-turn, instrumentation hooks for Arize Phoenix (if we add observability). |
| **Agent Runtime** | Managed serverless runtime for ADK agents. Alternative to Cloud Run. We'll start with Cloud Run for control, may switch to Agent Runtime if we need managed Sessions. |
| **Memory Bank** (Agent Platform) | Long-term memory for user preferences. Not used in MVP (founder's diagnoses don't need persistent memory across sessions), but mention in writeup as "future work" since it's a flagship 2026 feature. |
| **Sessions** (Agent Platform) | Conversation state across turns. We're using MongoDB for this instead (partner alignment), so Sessions is out. |
| **Vertex AI text embeddings** (`text-embedding-005` or `gemini-embedding-001`) | If we need embeddings for similarity (we may not for the Fivetran agent, but the MongoDB backup needs it). |

### Data & storage

| Service | What we use it for |
|---|---|
| **BigQuery** | Destination for Fivetran-synced data. Our diagnostic engine queries it. |
| **Secret Manager** | All API keys (Fivetran, MongoDB, etc.). First 6 versions are free. Access ops $0.03/10K. **Mounted into Cloud Run as env vars** — see [pattern](https://cloud.google.com/security/products/secret-manager). |
| **Cloud Logging** | Audit trail for Secret Manager access, agent runs. |

### Observability (for the demo itself)

| Service | What we use it for |
|---|---|
| **Cloud Trace** | Distributed traces of agent loop — useful for the architecture writeup and as a "look how deep this goes" judge-bait. |
| **Cloud Monitoring** | Health metrics on the Cloud Run services. |

Optional for the Arize backup track: **OpenInference instrumentor** sends traces to Phoenix Cloud in addition to Cloud Trace.

### What we deliberately don't use

- **Antigravity** — Google's new agentic IDE (available through Agent Platform per the [product page](https://cloud.google.com/products/gemini-enterprise-agent-platform)). It's an agent *orchestration UI for developers*, not an agent runtime. Not relevant for our build but worth knowing if it comes up in conversation.
- **Agent Search / Data Stores** — Agent Builder's grounding/RAG layer. Our diagnoses come from queryable BigQuery tables, not unstructured documents, so this is overkill.
- **Model Garden non-Google models** — Claude, Llama, etc. are visible in Model Garden but the [hackathon rules §7.B](https://rapid-agent.devpost.com/rules) forbid them.

## Agent Starter Pack vs. agents-cli

The [Resources page](https://rapid-agent.devpost.com/resources) links to the [Agent Starter Pack](https://github.com/GoogleCloudPlatform/agent-starter-pack), but the ASP README says it's in **maintenance mode** as of 2026 — Google has moved active development to a new CLI called `agents-cli`:

```bash
uvx google-agents-cli setup     # new
uvx agent-starter-pack create   # old, still works, no new features
```

What this means for us:
- **We can use either**. Both produce Apache-2.0 Python agent scaffolds with Terraform/CI/CD/observability built in.
- **Mention both in the README** to show we know the ecosystem. The reviewer who scored Agent Starter Pack in a previous hackathon will see "still using ASP" as legitimate; the Google judge who knows the rename will see "we're up to date."
- Practically, **we hand-write the scaffold** (which we've already done). Neither CLI is on the critical path — they're nice-to-haves for matching Google's expected structure. The ADK is the actually-load-bearing dependency.

## Responsible AI requirements

Per the [Responsible AI docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/responsible-ai), every production Gemini deployment should configure:

- **Safety settings** (block harassment, hate speech, sexually explicit, dangerous content at default thresholds)
- **System instructions** that scope the agent's purpose narrowly (we already do this)
- **Output validation** — for our diagnostic agent, we structure-validate the final report against a Pydantic schema before sending it to the user

We'll add a short "Safety" section to our Devpost writeup citing these. Judges score Design partly on responsible deployment.

## Cost projection for the build

| Item | 19-day burn |
|---|---|
| Gemini 3 API calls (build + demo) | ~$5 (small even at full chat usage) |
| Cloud Run requests | <$1 (free tier) |
| BigQuery queries | <$1 (free tier: 1 TB/month) |
| Secret Manager | $0 (within free 6 versions) |
| MongoDB Atlas M0 | $0 (always-free) |
| Fivetran | $0 (14-day trial) |
| **Total** | **<$10**, comfortably within $300 GCP free trial + $100 credit |

## The build sequence (just the GCP side)

1. Activate GCP free trial + apply for $100 credit
2. Create project `rapid-agent-hack-2026`
3. Enable APIs: Vertex AI, Cloud Run, Cloud Functions, Secret Manager, Cloud Build, BigQuery, Artifact Registry, Cloud Trace
4. `gcloud auth application-default login` locally
5. Confirm Gemini 3 access in Model Garden (Agent Platform → Models)
6. Stash Fivetran key, MongoDB URI in Secret Manager
7. Scaffold the FastAPI agent locally (already done)
8. First Cloud Run deploy: `gcloud run deploy agent --source .`
9. Wire the Fivetran MCP server (forked) as a second Cloud Run service
10. Iterate on the diagnostic engine + BigQuery queries
