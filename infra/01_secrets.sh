#!/usr/bin/env bash
# Stores the Grafana Cloud service account token and OTLP credentials in
# Secret Manager, so they never appear in code, images, or logs. Run once
# per environment, after creating a Grafana Cloud service account with
# Editor role (Editor is required for the write-back tools — annotations
# and incidents — see agent/second_unit/tools/grafana_mcp.py).
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${GRAFANA_URL:?set GRAFANA_URL, e.g. https://yourstack.grafana.net}"
: "${GRAFANA_SERVICE_ACCOUNT_TOKEN:?set GRAFANA_SERVICE_ACCOUNT_TOKEN}"
: "${GRAFANA_CLOUD_METRICS_USER:?set GRAFANA_CLOUD_METRICS_USER}"
: "${GRAFANA_CLOUD_METRICS_TOKEN:?set GRAFANA_CLOUD_METRICS_TOKEN}"
: "${GRAFANA_CLOUD_LOGS_USER:?set GRAFANA_CLOUD_LOGS_USER}"
: "${GRAFANA_CLOUD_LOGS_TOKEN:?set GRAFANA_CLOUD_LOGS_TOKEN}"

create_or_update_secret() {
  local name="$1" value="$2"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=-
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- --replication-policy=automatic
  fi
}

create_or_update_secret grafana-url "$GRAFANA_URL"
create_or_update_secret grafana-service-account-token "$GRAFANA_SERVICE_ACCOUNT_TOKEN"
create_or_update_secret grafana-cloud-metrics-user "$GRAFANA_CLOUD_METRICS_USER"
create_or_update_secret grafana-cloud-metrics-token "$GRAFANA_CLOUD_METRICS_TOKEN"
create_or_update_secret grafana-cloud-logs-user "$GRAFANA_CLOUD_LOGS_USER"
create_or_update_secret grafana-cloud-logs-token "$GRAFANA_CLOUD_LOGS_TOKEN"

echo "Secrets stored. Next: infra/02_deploy_agent.sh"
