# Alert rule: visual defect detected

`visual_defect_alert.json` is a template for a Grafana alert rule on
`second_unit_visual_defects_detected_total` (emitted by VerdictAgent's
`after_agent_callback`, see `agent/second_unit/sub_agents/verdict.py`). It
closes the loop this project argues for: vision finding -> Prometheus metric
-> alert -> annotation, all inside Grafana, not just on the control room
screen.

`REPLACE_WITH_YOUR_FOLDER_UID` and `REPLACE_WITH_YOUR_PROMETHEUS_DS_UID` in
the template are placeholders — `provision.sh` resolves them against your
own stack (creating a "SECOND UNIT" folder if needed) and POSTs the result
to the Grafana Cloud alerting provisioning API. Run once, after
`infra/01_secrets.sh` and a deploy that's produced at least one real
diagnose run (so the metric has data):

```bash
set -a && source ../../.env && set +a
bash provision.sh
```

Verified live on this project's own stack: rule uid `ffxc7u4gabsowc`,
firing on `increase(second_unit_visual_defects_detected_total[5m]) > 0`.
