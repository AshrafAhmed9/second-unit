#!/usr/bin/env bash
# Builds and deploys the agent service to Cloud Run, wired to the secrets
# created in 01_secrets.sh. A least-privilege runtime service account is
# created if it doesn't exist, with only secretAccessor + storage/firestore
# roles it actually needs — not the default compute service account.
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${REGION:=us-central1}"
SERVICE_ACCOUNT="second-unit-agent-runner@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT" >/dev/null 2>&1; then
  gcloud iam service-accounts create second-unit-agent-runner \
    --display-name "SECOND UNIT agent runtime (least privilege)"
fi

for role in roles/secretmanager.secretAccessor roles/datastore.user roles/storage.objectViewer roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member "serviceAccount:${SERVICE_ACCOUNT}" --role "$role" --condition=None >/dev/null
done

gcloud builds submit ../agent --tag "gcr.io/${PROJECT_ID}/second-unit-agent:latest"

# --max-instances 1: _pending_plans in server.py is a module-level in-memory
# dict, not a shared store. With >1 instance the run and the later approve
# call can land on different instances and the approve 404s. Fix properly
# (Firestore/Redis) if this ever needs real concurrency; for judging traffic
# one instance is enough and keeps the approve path honest.
gcloud run deploy second-unit-agent \
  --image "gcr.io/${PROJECT_ID}/second-unit-agent:latest" \
  --region "$REGION" \
  --service-account "$SERVICE_ACCOUNT" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --timeout 900 \
  --memory 1Gi \
  --set-secrets "GRAFANA_URL=grafana-url:latest,GRAFANA_SERVICE_ACCOUNT_TOKEN=grafana-service-account-token:latest,OTEL_EXPORTER_OTLP_ENDPOINT=otel-exporter-otlp-endpoint:latest,OTEL_EXPORTER_OTLP_HEADERS=otel-exporter-otlp-headers:latest" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_LOCATION=${REGION},BACKLOT_BUCKET=${PROJECT_ID}-backlot"

# BACKLOT_BUCKET is what makes Live Mode work on the deployed service, not
# just Demo Mode. Cloud Run's local filesystem is ephemeral and per-instance
# — without a bucket, EyesAgent's load_frames finds nothing on a real
# container, so a judge clicking "Live Mode" would get an agent with no
# picture to look at. Create the bucket once and upload real frames with:
#   gcloud storage buckets create gs://${PROJECT_ID}-backlot --location=us-central1
#   gcloud storage cp -r ../backlot/frames_local/job-seq042-sh0420 gs://${PROJECT_ID}-backlot/

echo "Deployed. min-instances=0 means this scales to zero and costs ~nothing"
echo "when idle — important for keeping the hosted URL alive through judging"
echo "at \$0. Demo Mode (GET /demo) makes zero downstream API calls regardless."
