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

gcloud run deploy second-unit-agent \
  --image "gcr.io/${PROJECT_ID}/second-unit-agent:latest" \
  --region "$REGION" \
  --service-account "$SERVICE_ACCOUNT" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 3 \
  --memory 1Gi \
  --set-secrets "GRAFANA_URL=grafana-url:latest,GRAFANA_SERVICE_ACCOUNT_TOKEN=grafana-service-account-token:latest,GRAFANA_CLOUD_METRICS_USER=grafana-cloud-metrics-user:latest,GRAFANA_CLOUD_METRICS_TOKEN=grafana-cloud-metrics-token:latest,GRAFANA_CLOUD_LOGS_USER=grafana-cloud-logs-user:latest,GRAFANA_CLOUD_LOGS_TOKEN=grafana-cloud-logs-token:latest" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"

echo "Deployed. min-instances=0 means this scales to zero and costs ~nothing"
echo "when idle — important for keeping the hosted URL alive through judging"
echo "at \$0. Demo Mode (GET /demo) makes zero downstream API calls regardless."
