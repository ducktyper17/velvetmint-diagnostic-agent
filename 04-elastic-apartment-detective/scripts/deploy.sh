#!/usr/bin/env bash
# Cloud Run deploy for the Elastic Apartment Detective.
#
# Deploys two services:
#   - apartment-detective-backend   (the Gemini + Elastic agent)
#   - apartment-detective-frontend  (the paste-a-listing dashboard)
#
# Required env (sourced from agent/.env if present):
#   GOOGLE_CLOUD_PROJECT
#   GOOGLE_CLOUD_LOCATION   default us-central1
#   ELASTIC_MCP_URL         Agent Builder MCP endpoint from Kibana
#
# Required Secret Manager secret in the project:
#   elastic-mcp-api-key     API key with agentBuilder:read + index read
#
# To run the agent live (not demo), pass DEMO_MODE=false and
# STUB_GEMINI_RESPONSES=false in the env before deploying.

set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f agent/.env ]; then
  # shellcheck disable=SC1091
  set -a; . agent/.env; set +a
fi

: "${GOOGLE_CLOUD_PROJECT:?GOOGLE_CLOUD_PROJECT required}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
: "${ELASTIC_MCP_URL:?ELASTIC_MCP_URL required}"
DEMO_MODE="${DEMO_MODE:-false}"
STUB_GEMINI="${STUB_GEMINI_RESPONSES:-false}"
VERTEX_MODEL="${VERTEX_MODEL:-gemini-2.5-flash}"

BACKEND="apartment-detective-backend"
FRONTEND="apartment-detective-frontend"

deploy_backend() {
  echo "==> Deploying backend to ${REGION}/${BACKEND}"
  gcloud run deploy "${BACKEND}" \
    --source agent \
    --region "${REGION}" --project "${GOOGLE_CLOUD_PROJECT}" \
    --platform managed --allow-unauthenticated \
    --cpu 2 --memory 2Gi --concurrency 4 --timeout 600 \
    --set-secrets "ELASTIC_MCP_API_KEY=elastic-mcp-api-key:latest" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=${REGION},VERTEX_MODEL=${VERTEX_MODEL},ELASTIC_MCP_URL=${ELASTIC_MCP_URL},DEMO_MODE=${DEMO_MODE},STUB_GEMINI_RESPONSES=${STUB_GEMINI},ENVIRONMENT=prod,LOG_LEVEL=INFO"
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
  backend) deploy_backend ;;
  frontend) deploy_frontend ;;
  all) deploy_backend; deploy_frontend ;;
  *) echo "usage: $0 [backend|frontend|all]"; exit 2 ;;
esac

echo
gcloud run services list --region "${REGION}" --project "${GOOGLE_CLOUD_PROJECT}" \
  --filter="metadata.name~apartment-detective-" --format="table(metadata.name,status.url)"
