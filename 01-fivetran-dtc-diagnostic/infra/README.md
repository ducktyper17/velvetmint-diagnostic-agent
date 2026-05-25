# Infra — Cloud Run + Cloud Function deploy plan

Three Cloud Run services and one Cloud Function. All in `us-central1`,
all in the same GCP project (`rapid-agent-hack-2026` by default).

```
                ┌────────────────────────────────────────┐
                │ Cloud Function: dtc-start-diagnosis    │
                │ (HTTPS trigger; thin proxy to agent)   │
                └────────────────────────────────────────┘
                                  │
                                  ▼
                ┌────────────────────────────────────────┐
                │ Cloud Run service: dtc-agent           │
                │ (FastAPI; the brain)                   │
                │                                        │
                │   talks to ───────────────────────┐    │
                │     - Vertex AI / Gemini 3        │    │
                │     - BigQuery                    │    │
                │     - MongoDB Atlas (egress)      │    │
                │     - dtc-fivetran-mcp (below)    │    │
                └──────────────────────────────┬─┴──┘
                                               │
                                               ▼
                ┌────────────────────────────────────────┐
                │ Cloud Run service: dtc-fivetran-mcp    │
                │ (the official Fivetran MCP server)     │
                └────────────────────────────────────────┘

                ┌────────────────────────────────────────┐
                │ Cloud Run service: dtc-frontend        │
                │ (Next.js 15)                           │
                │ talks to: dtc-agent over SSE           │
                └────────────────────────────────────────┘
```

## One-time prerequisites (Day 1)

```bash
gcloud config set project rapid-agent-hack-2026
gcloud config set run/region us-central1

# Enable the APIs we need.
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudfunctions.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  iam.googleapis.com \
  artifactregistry.googleapis.com

# Artifact Registry repo for our container images.
gcloud artifacts repositories create dtc \
  --repository-format=docker \
  --location=us-central1 \
  --description="DTC diagnostic agent images"

# Service account that the agent runs as.
gcloud iam service-accounts create dtc-agent-sa \
  --display-name="DTC Diagnostic Agent runtime"

# Roles the agent needs.
PROJECT_ID=$(gcloud config get-value project)
AGENT_SA="dtc-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com"

for ROLE in \
  roles/aiplatform.user \
  roles/bigquery.jobUser \
  roles/bigquery.dataViewer \
  roles/secretmanager.secretAccessor \
  roles/run.invoker
do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${AGENT_SA}" \
    --role="$ROLE"
done
```

## Secrets (Day 1)

Every secret lives in Secret Manager; Cloud Run mounts them as env vars.

```bash
# Create.
echo -n "$FIVETRAN_API_KEY"      | gcloud secrets create fivetran-api-key --data-file=-
echo -n "$FIVETRAN_API_SECRET"   | gcloud secrets create fivetran-api-secret --data-file=-
echo -n "$FIVETRAN_MCP_TOKEN"    | gcloud secrets create fivetran-mcp-token --data-file=-
echo -n "$MONGODB_URI"           | gcloud secrets create mongodb-uri --data-file=-

# Grant the agent SA read access to each.
for S in fivetran-api-key fivetran-api-secret fivetran-mcp-token mongodb-uri; do
  gcloud secrets add-iam-policy-binding "$S" \
    --member="serviceAccount:${AGENT_SA}" \
    --role="roles/secretmanager.secretAccessor"
done
```

## Deploying the agent (`dtc-agent`)

The recommended path is via Cloud Build using [`cloudbuild.yaml`](./cloudbuild.yaml):

```bash
gcloud builds submit . \
  --config=infra/cloudbuild.yaml \
  --substitutions=_SERVICE=dtc-agent,_IMAGE_TAG=$(git rev-parse --short HEAD)
```

Cloud Build does build → push → deploy in a single shot. After it finishes:

```bash
gcloud run services describe dtc-agent --format='value(status.url)'
# https://dtc-agent-xxxxxx-uc.a.run.app
```

## Deploying the Fivetran MCP server (`dtc-fivetran-mcp`)

The MCP runs as its own Cloud Run service so we can scale and authenticate
it independently. We build from the upstream repo:

```bash
git clone https://github.com/fivetran/fivetran-mcp.git /tmp/fivetran-mcp
cd /tmp/fivetran-mcp

gcloud run deploy dtc-fivetran-mcp \
  --source . \
  --region=us-central1 \
  --service-account="$AGENT_SA" \
  --no-allow-unauthenticated \
  --set-secrets=FIVETRAN_API_KEY=fivetran-api-key:latest \
  --set-secrets=FIVETRAN_API_SECRET=fivetran-api-secret:latest \
  --set-env-vars=FIVETRAN_ALLOW_WRITES=true,TRANSPORT=http,PORT=8080
```

Notes:
- `--no-allow-unauthenticated` plus `roles/run.invoker` granted to the agent
  SA means only the agent service can call the MCP.
- The MCP exposes its bearer-token authentication on top of Cloud Run IAM,
  so we have defense in depth.

## Deploying the frontend (`dtc-frontend`)

Day 8 of the build plan. Once the Next.js project exists:

```bash
cd frontend
gcloud run deploy dtc-frontend \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated \
  --set-env-vars=AGENT_URL=$(gcloud run services describe dtc-agent --format='value(status.url)')
```

## Cloud Function (`dtc-start-diagnosis`)

Thin HTTPS trigger that forwards a body to the agent's `/diagnose`. Useful
for the front-page "Try it" button and any future scheduled diagnoses.

```bash
gcloud functions deploy dtc-start-diagnosis \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=infra/functions/start_diagnosis \
  --entry-point=start_diagnosis \
  --trigger-http \
  --allow-unauthenticated \
  --service-account="$AGENT_SA" \
  --set-env-vars=AGENT_URL=$(gcloud run services describe dtc-agent --format='value(status.url)')
```

A minimal `infra/functions/start_diagnosis/main.py` will land alongside this
on Day 11.

## Local run vs. deployed run

| Concern | Local | Deployed |
|---|---|---|
| Auth to Vertex AI | `gcloud auth application-default login` | Workload identity on the SA |
| Auth to BigQuery | same as above | same |
| Auth to MongoDB | URI in `.env` | URI in Secret Manager |
| Auth to MCP | localhost, no IAM | Cloud Run IAM `roles/run.invoker` |
| Hot reload | yes (uvicorn `--reload`) | no |
| Logs | stdout | Cloud Logging |

## Cost notes (back-of-envelope, hackathon scope)

- Cloud Run cold start ~1.5s; we keep min instances at 0 outside the demo
  window. During the demo, set `--min-instances=1` for `dtc-agent` and
  `dtc-fivetran-mcp` to avoid a first-call yawn.
- Vertex AI Gemini 3: a full diagnosis is ~5-10 model calls of <2K tokens
  each. Each diagnosis costs in the low-cents range. The $300 free trial
  covers >>1000 demo runs.
- BigQuery: 12 small queries per diagnosis, all <1 GB scanned, well under
  the 1 TB/month free tier.
- MongoDB Atlas M0: free, period.

## Teardown

```bash
gcloud run services delete dtc-agent dtc-fivetran-mcp dtc-frontend --quiet
gcloud functions delete dtc-start-diagnosis --gen2 --region=us-central1 --quiet
gcloud artifacts repositories delete dtc --location=us-central1 --quiet
```
