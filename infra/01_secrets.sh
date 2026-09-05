#!/usr/bin/env bash
# Stores the Grafana Cloud service account token and OTLP credentials in
# Secret Manager, so they never appear in code, images, or logs. Run once
# per environment, after creating a Grafana Cloud service account with
# Editor role (Editor is required for the write-back tools — annotations
# and incidents — see agent/second_unit/tools/grafana_mcp.py) and an access
# policy token scoped metrics:write, logs:write, traces:write (see
# agent/second_unit/telemetry.py and backlot/worker/render_worker.py, which
# both push over this one OTLP gateway instead of the old, dead Prometheus
# remote-write path).
#
# OTEL_EXPORTER_OTLP_ENDPOINT / _HEADERS: read the real values from your
# stack's OpenTelemetry tile (Grafana Cloud -> your stack -> OpenTelemetry)
# rather than assuming them — the gateway host varies by region/vintage.
# OTEL_EXPORTER_OTLP_HEADERS is the literal string
# "Authorization=Basic <base64 of instanceID:token>".
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${GRAFANA_URL:?set GRAFANA_URL, e.g. https://yourstack.grafana.net}"
: "${GRAFANA_SERVICE_ACCOUNT_TOKEN:?set GRAFANA_SERVICE_ACCOUNT_TOKEN}"
: "${OTEL_EXPORTER_OTLP_ENDPOINT:?set OTEL_EXPORTER_OTLP_ENDPOINT, from the OpenTelemetry tile in your stack}"
: "${OTEL_EXPORTER_OTLP_HEADERS:?set OTEL_EXPORTER_OTLP_HEADERS, e.g. Authorization=Basic <base64 instanceID:token>}"

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
create_or_update_secret otel-exporter-otlp-endpoint "$OTEL_EXPORTER_OTLP_ENDPOINT"
create_or_update_secret otel-exporter-otlp-headers "$OTEL_EXPORTER_OTLP_HEADERS"

echo "Secrets stored. Next: infra/02_deploy_agent.sh"
