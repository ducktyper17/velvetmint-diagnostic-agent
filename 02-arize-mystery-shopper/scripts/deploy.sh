#!/usr/bin/env bash
# Cloud Run deploy script. Builds + ships backend then frontend.
#
# Required env (sourced from .env if present):
#   GOOGLE_CLOUD_PROJECT       GCP project to deploy to
#   GOOGLE_CLOUD_LOCATION      region (default: us-central1)
#   PHOENIX_COLLECTOR_ENDPOINT must include /s/<your-space>
#   PHOENIX_PROJECT_NAME       Phoenix project name (default: self-improving-qa-agent)
#
# Required Secret Manager secrets in the project:
#   phoenix-api-key            Phoenix Cloud API key (px_live_...)
#
# Usage:
#   ./scripts/deploy.sh            # deploy both backend and frontend
#   ./scripts/deploy.sh backend    # backend only
#   ./scripts/deploy.sh frontend   # frontend only

set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f agent/.env ]; then
  # shellcheck disable=SC1091
  set -a; . agent/.env; set +a
fi

: "${GOOGLE_CLOUD_PROJECT:?GOOGLE_CLOUD_PROJECT is required}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
PROJECT_NAME="${PHOENIX_PROJECT_NAME:-self-improving-qa-agent}"
SUT_DATASET="${PHOENIX_SCENARIO_DATASET_NAME:-velvetmint-support.scenarios}"
SUT_PROMPT="${PHOENIX_SUT_PROMPT_NAME:-sut-velvetmint-support}"

BACKEND_SERVICE="self-improving-qa-backend"
FRONTEND_SERVICE="self-improving-qa-frontend"

deploy_backend() {
  echo "==> Deploying backend to ${REGION}/${BACKEND_SERVICE}"
  gcloud run deploy "${BACKEND_SERVICE}" \
    --source agent \
    --region "${REGION}" \
    --project "${GOOGLE_CLOUD_PROJECT}" \
    --platform managed \
    --allow-unauthenticated \
    --cpu 2 --memory 2Gi --timeout 900 --concurrency 4 \
    --set-secrets "PHOENIX_API_KEY=phoenix-api-key:latest" \
    --set-env-vars "PHOENIX_PROJECT_NAME=${PROJECT_NAME},PHOENIX_COLLECTOR_ENDPOINT=${PHOENIX_COLLECTOR_ENDPOINT:?PHOENIX_COLLECTOR_ENDPOINT required},PHOENIX_SCENARIO_DATASET_NAME=${SUT_DATASET},PHOENIX_SUT_PROMPT_NAME=${SUT_PROMPT},GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=${REGION},APP_ENV=production"
}

deploy_frontend() {
  local backend_url
  backend_url=$(gcloud run services describe "${BACKEND_SERVICE}" \
    --region "${REGION}" --project "${GOOGLE_CLOUD_PROJECT}" \
    --format='value(status.url)' || true)
  if [ -z "${backend_url}" ]; then
    echo "!! Could not look up backend URL. Deploy backend first or set BACKEND_URL." >&2
    exit 1
  fi
  echo "==> Deploying frontend to ${REGION}/${FRONTEND_SERVICE} (backend=${backend_url})"
  gcloud run deploy "${FRONTEND_SERVICE}" \
    --source frontend \
    --region "${REGION}" \
    --project "${GOOGLE_CLOUD_PROJECT}" \
    --platform managed \
    --allow-unauthenticated \
    --cpu 1 --memory 512Mi --concurrency 80 \
    --set-env-vars "BACKEND_URL=${backend_url},NEXT_PUBLIC_PHOENIX_URL=${PHOENIX_COLLECTOR_ENDPOINT:-https://app.phoenix.arize.com}"
}

case "${1:-all}" in
  backend) deploy_backend ;;
  frontend) deploy_frontend ;;
  all) deploy_backend; deploy_frontend ;;
  *) echo "usage: $0 [backend|frontend|all]"; exit 2 ;;
esac

echo
echo "Done."
gcloud run services list --region "${REGION}" --project "${GOOGLE_CLOUD_PROJECT}" \
  --filter="metadata.name~self-improving-qa-" --format="table(metadata.name,status.url)"
