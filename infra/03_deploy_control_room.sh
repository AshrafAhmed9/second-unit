#!/usr/bin/env bash
# Deploys the Next.js control room to Cloud Run, pointed at the agent
# service's URL. Run after 02_deploy_agent.sh so NEXT_PUBLIC_AGENT_URL exists.
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${REGION:=us-central1}"

AGENT_URL="$(gcloud run services describe second-unit-agent --region "$REGION" --format 'value(status.url)')"
IMAGE="gcr.io/${PROJECT_ID}/second-unit-control-room:latest"

# NEXT_PUBLIC_* vars are inlined into the JS bundle at BUILD time, not read
# at container runtime — `gcloud run deploy --set-env-vars` on the running
# service would silently do nothing for it. Must go in as a Docker build-arg
# instead, which needs an explicit cloudbuild.yaml step: plain
# `gcloud builds submit --tag ... --substitutions` does NOT forward
# substitutions into the build as --build-arg on its own. Found via review
# before deploying, not after a wasted build cycle.
gcloud builds submit ../control-room \
  --config ../control-room/cloudbuild.yaml \
  --substitutions "_AGENT_URL=${AGENT_URL},_IMAGE=${IMAGE}"

gcloud run deploy second-unit-control-room \
  --image "$IMAGE" \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 3

echo "Control room deployed. This URL is what goes in the Devpost submission."
