# Infra setup — $0, step by step

## 1. Google Cloud

1. Create a Google Cloud account and start the **free trial** (cloud.google.com/free) — a
   card is required to open it but is **not charged**, and the account does not silently
   upgrade to paid. $300 credit, 90 days.
2. Request the hackathon's **$100 Google Cloud credit** from the hackathon resources page —
   allow 1–5 business days, so do this on day 0.
3. Create a project, note its `PROJECT_ID`.
4. **Do not click "Upgrade account."** Everything in this repo runs comfortably inside the
   free trial: a handful of Gemini calls per triaged job, Cloud Run services with
   `min-instances=0` (scale to zero, no idle cost), a few hundred MB in GCS/Firestore.

## 2. Grafana Cloud

1. Sign up at grafana.com/auth/sign-up — the **Free plan requires no credit card** and does
   not expire: 10k active metric series, 50GB logs, 50GB traces, 14-day retention, 3 users.
2. Under your stack → Administration → Service accounts, create a service account with
   **Editor** role (needed for the write-back tools: annotations + incidents) and generate
   a token. This is `GRAFANA_SERVICE_ACCOUNT_TOKEN`.
3. Under your stack → Connections → find the Prometheus remote-write and Loki push
   endpoints and credentials — these back `GRAFANA_CLOUD_METRICS_USER/TOKEN` and
   `GRAFANA_CLOUD_LOGS_USER/TOKEN` for the backlot workers.
4. Your `GRAFANA_URL` is `https://<your-stack>.grafana.net`.

## 3. Run the scripts in order

```bash
PROJECT_ID=... ./00_project_setup.sh
PROJECT_ID=... GRAFANA_URL=... GRAFANA_SERVICE_ACCOUNT_TOKEN=... \
  GRAFANA_CLOUD_METRICS_USER=... GRAFANA_CLOUD_METRICS_TOKEN=... \
  GRAFANA_CLOUD_LOGS_USER=... GRAFANA_CLOUD_LOGS_TOKEN=... ./01_secrets.sh
PROJECT_ID=... ./02_deploy_agent.sh
PROJECT_ID=... ./03_deploy_control_room.sh
```

## Day-3 compliance check (do this before building anything else)

Grafana's hosted `mcp.grafana.com` endpoint requires an interactive OAuth 2.1 browser flow,
which a headless Cloud Run agent cannot complete on its own. This repo runs the official
open-source `grafana/mcp-grafana` binary as a stdio subprocess instead, authenticated with
the service account token above — this is still the real Grafana MCP server, operating
against a real Grafana Cloud stack, satisfying the track's runtime-integration requirement.

Prove this works before writing anything else:

```bash
cd ../agent
GRAFANA_URL=... GRAFANA_SERVICE_ACCOUNT_TOKEN=... python3 -c "
from second_unit.tools.grafana_mcp import read_toolset
print(read_toolset())
"
```

If this cannot be made to work, stop and reconsider the track — see the design rationale
document for the fallback (a one-time browser OAuth authorization stored in Secret Manager).

## Cost check

Nothing in this stack incurs cost while idle. `min-instances=0` on both Cloud Run services,
Grafana Cloud's free plan doesn't expire, and Demo Mode on the hosted control room makes
zero downstream API calls — so the submission stays live and free through judging even if
GCP trial credits eventually lapse.
