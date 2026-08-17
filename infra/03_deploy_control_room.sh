#!/usr/bin/env bash
# Deploys the Next.js control room to Cloud Run, pointed at the agent
# service's URL. Run after 02_deploy_agent.sh so NEXT_PUBLIC_AGENT_URL exists.
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${REGION:=us-central1}"

AGENT_URL="$(gcloud run services describe second-unit-agent --region "$REGION" --format 'value(status.url)')"

gcloud builds submit ../control-room \
  --tag "gcr.io/${PROJECT_ID}/second-unit-control-room:latest" \
  --substitutions "_AGENT_URL=${AGENT_URL}"

gcloud run deploy second-unit-control-room \
  --image "gcr.io/${PROJECT_ID}/second-unit-control-room:latest" \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars "NEXT_PUBLIC_AGENT_URL=${AGENT_URL}"

echo "Control room deployed. This URL is what goes in the Devpost submission."
