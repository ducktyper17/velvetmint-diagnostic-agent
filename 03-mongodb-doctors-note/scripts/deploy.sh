#!/usr/bin/env bash
# Deploy the Doctor's Note Decoder to Cloud Run as a single service.
#
# Prereqs (one-time):
#   gcloud auth login
#   gcloud config set project <YOUR_PROJECT>
#   gcloud services enable run.googleapis.com aiplatform.googleapis.com \
#       secretmanager.googleapis.com cloudbuild.googleapis.com
#
# Then put your Atlas connection string in Secret Manager once:
#   printf '%s' 'mongodb+srv://USER:PASS@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority' \
#     | gcloud secrets create MONGODB_URI --data-file=- --replication-policy=automatic
#
# Usage:
#   ./scripts/deploy.sh                 # uses gcloud's current project + us-central1
#   REGION=us-east1 ./scripts/deploy.sh
set -euo pipefail

PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-doctors-note-decoder}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.1-pro-preview}"

if [[ -z "${PROJECT}" || "${PROJECT}" == "(unset)" ]]; then
  echo "ERROR: no GCP project set. Run: gcloud config set project <YOUR_PROJECT>" >&2
  exit 1
fi

echo ">> Project:  ${PROJECT}"
echo ">> Region:   ${REGION}"
echo ">> Service:  ${SERVICE}"
echo ">> Model:    ${GEMINI_MODEL}"

# Build context is the agent/ dir (where the Dockerfile lives).
cd "$(dirname "$0")/../agent"

gcloud run deploy "${SERVICE}" \
  --source . \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 120 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_LOCATION=${REGION},GEMINI_MODEL=${GEMINI_MODEL},MONGODB_DB=doctors_note,VERTEX_EMBEDDING_MODEL=gemini-embedding-001,VERTEX_EMBEDDING_DIM=3072,REQUIRE_DISCLAIMER_FILE=1" \
  --set-secrets "MONGODB_URI=MONGODB_URI:latest"

echo
echo ">> Deployed. Hosted URL:"
gcloud run services describe "${SERVICE}" --project "${PROJECT}" --region "${REGION}" \
  --format='value(status.url)'
