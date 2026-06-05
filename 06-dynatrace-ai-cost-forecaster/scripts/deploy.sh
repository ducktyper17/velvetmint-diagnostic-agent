#!/usr/bin/env bash
# Cloud Run deploy for Agent Reliability Guard.
#
# Deploys three services:
#   - reliability-guard-demo-app   (refund-assistant, the workload being watched)
#   - reliability-guard-backend    (the guard agent)
#   - reliability-guard-frontend   (the dashboard)
#
# Required env (sourced from agent/.env if present):
#   GOOGLE_CLOUD_PROJECT
#   GOOGLE_CLOUD_LOCATION         default us-central1
#   DYNATRACE_ENVIRONMENT_URL     your Dynatrace tenant URL
#   DYNATRACE_MCP_URL             Dynatrace MCP gateway endpoint
#   OTEL_EXPORTER_OTLP_ENDPOINT   Dynatrace OTLP endpoint for the demo-app
#   OTEL_EXPORTER_OTLP_HEADERS    Authorization header for OTLP (Api-Token ...)
#
# Required Secret Manager secrets in the project:
#   dynatrace-mcp-token           bearer token for the MCP endpoint

set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f agent/.env ]; then
  # shellcheck disable=SC1091
  set -a; . agent/.env; set +a
fi

: "${GOOGLE_CLOUD_PROJECT:?GOOGLE_CLOUD_PROJECT required}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
: "${DYNATRACE_ENVIRONMENT_URL:?DYNATRACE_ENVIRONMENT_URL required}"
: "${DYNATRACE_MCP_URL:?DYNATRACE_MCP_URL required}"
OTEL_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-}"
OTEL_HEADERS="${OTEL_EXPORTER_OTLP_HEADERS:-}"

BACKEND="reliability-guard-backend"
DEMO_APP="reliability-guard-demo-app"
FRONTEND="reliability-guard-frontend"

deploy_demo_app() {
  echo "==> Deploying demo-app to ${REGION}/${DEMO_APP}"
  gcloud run deploy "${DEMO_APP}" \
    --source demo-app \
    --region "${REGION}" --project "${GOOGLE_CLOUD_PROJECT}" \
    --platform managed --allow-unauthenticated \
    --cpu 1 --memory 1Gi --concurrency 16 --timeout 60 \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=${REGION},VERTEX_MODEL=gemini-2.5-flash,RELEASE_ID=release-baseline,PROMPT_VERSION=v11,PROMPT_MODE=healthy,OTEL_SERVICE_NAME=refund-assistant${OTEL_ENDPOINT:+,OTEL_EXPORTER_OTLP_ENDPOINT=${OTEL_ENDPOINT}}${OTEL_HEADERS:+,OTEL_EXPORTER_OTLP_HEADERS=${OTEL_HEADERS}}"
}

deploy_backend() {
  echo "==> Deploying backend to ${REGION}/${BACKEND}"
  gcloud run deploy "${BACKEND}" \
    --source agent \
    --region "${REGION}" --project "${GOOGLE_CLOUD_PROJECT}" \
    --platform managed --allow-unauthenticated \
    --cpu 2 --memory 2Gi --concurrency 4 --timeout 600 \
    --set-secrets "DYNATRACE_MCP_TOKEN=dynatrace-mcp-token:latest" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=${REGION},VERTEX_MODEL=gemini-2.5-pro,DYNATRACE_ENVIRONMENT_URL=${DYNATRACE_ENVIRONMENT_URL},DYNATRACE_MCP_URL=${DYNATRACE_MCP_URL},ENVIRONMENT=prod,LOG_LEVEL=INFO"
}

deploy_frontend() {
  local backend_url
  backend_url=$(gcloud run services describe "${BACKEND}" \
    --region "${REGION}" --project "${GOOGLE_CLOUD_PROJECT}" \
    --format='value(status.url)' || true)
  if [ -z "${backend_url}" ]; then
    echo "!! Backend URL not found. Deploy backend first." >&2
    exit 1
  fi
  echo "==> Deploying frontend to ${REGION}/${FRONTEND} (backend=${backend_url})"
  gcloud run deploy "${FRONTEND}" \
    --source frontend \
    --region "${REGION}" --project "${GOOGLE_CLOUD_PROJECT}" \
    --platform managed --allow-unauthenticated \
    --cpu 1 --memory 512Mi --concurrency 80 \
    --set-env-vars "BACKEND_URL=${backend_url}"
}

case "${1:-all}" in
  demo-app) deploy_demo_app ;;
  backend) deploy_backend ;;
  frontend) deploy_frontend ;;
  all) deploy_demo_app; deploy_backend; deploy_frontend ;;
  *) echo "usage: $0 [demo-app|backend|frontend|all]"; exit 2 ;;
esac

echo
gcloud run services list --region "${REGION}" --project "${GOOGLE_CLOUD_PROJECT}" \
  --filter="metadata.name~reliability-guard-" --format="table(metadata.name,status.url)"
