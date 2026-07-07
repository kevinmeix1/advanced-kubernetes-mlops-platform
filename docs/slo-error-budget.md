# SLO And Error Budget Automation

The platform now converts monitoring output into `reports/slo_error_budget.json`.

The report contains:

- SLO targets for inference availability, p95 latency, feature drift, and prediction drift
- burn-rate calculations against each target
- remaining error-budget percentage
- multi-window alert thresholds for fast page, slow page, and ticket workflows
- a release-freeze decision that can be consumed by Airflow or a release controller

Run it locally:

```bash
make demo
make slo-report
```

`kubernetes/slo-alerts.yaml` models the PrometheusRule and CronJob that would keep release automation aligned with SRE-style error-budget policy.
