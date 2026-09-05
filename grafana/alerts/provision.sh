#!/usr/bin/env bash
# Provisions the "visual defect detected" alert rule on second_unit_visual_
# defects_detected_total (agent/second_unit/sub_agents/verdict.py) via
# Grafana Cloud's alerting provisioning API — the alert that closes the
# loop: vision finding -> metric -> alert -> annotation, all inside
# Grafana, not just on our own control-room screen.
#
# Requires GRAFANA_URL and GRAFANA_SERVICE_ACCOUNT_TOKEN (see infra/.env) and
# a folder to hold it — creates "SECOND UNIT" if it doesn't already exist.
set -euo pipefail

: "${GRAFANA_URL:?set GRAFANA_URL}"
: "${GRAFANA_SERVICE_ACCOUNT_TOKEN:?set GRAFANA_SERVICE_ACCOUNT_TOKEN}"

AUTH_HEADER="Authorization: Bearer ${GRAFANA_SERVICE_ACCOUNT_TOKEN}"

FOLDER_UID=$(curl -s -H "$AUTH_HEADER" "$GRAFANA_URL/api/folders" \
  | python3 -c "import json,sys; fs=json.load(sys.stdin); m=[f for f in fs if f['title']=='SECOND UNIT']; print(m[0]['uid'] if m else '')")

if [ -z "$FOLDER_UID" ]; then
  FOLDER_UID=$(curl -s -H "$AUTH_HEADER" -H "Content-Type: application/json" \
    -X POST "$GRAFANA_URL/api/folders" -d '{"title":"SECOND UNIT"}' \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['uid'])")
  echo "Created folder SECOND UNIT ($FOLDER_UID)"
fi

PROM_UID=$(curl -s -H "$AUTH_HEADER" "$GRAFANA_URL/api/datasources" \
  | python3 -c "import json,sys; ds=json.load(sys.stdin); m=[d for d in ds if d['type']=='prometheus' and 'usage' not in d['name']]; print(m[0]['uid'])")

python3 - "$FOLDER_UID" "$PROM_UID" << 'PYEOF' > /tmp/second-unit-alert-rule.json
import json, sys
folder_uid, prom_uid = sys.argv[1], sys.argv[2]
rule = json.load(open("grafana/alerts/visual_defect_alert.json"))
rule["folderUID"] = folder_uid
rule["data"][0]["datasourceUid"] = prom_uid
print(json.dumps(rule))
PYEOF

RESP=$(curl -s -w "\n%{http_code}" -H "$AUTH_HEADER" -H "Content-Type: application/json" \
  -X POST "$GRAFANA_URL/api/v1/provisioning/alert-rules" -d @/tmp/second-unit-alert-rule.json)
CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')

if [ "$CODE" = "201" ]; then
  echo "Alert rule provisioned: $BODY"
else
  echo "Provisioning failed ($CODE): $BODY" >&2
  exit 1
fi
