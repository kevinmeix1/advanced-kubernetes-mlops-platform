# Cost Observability and FinOps

`make cost-observability` writes `.local/reports/cost_observability_report.json` and validates the platform cost-allocation contract used by the release control plane.

## What It Shows

- OpenCost exporter metrics scraped by Prometheus every minute.
- CPU, RAM, GPU, node, PVC, and load-balancer cost signals for MLOps workloads.
- Required ownership labels: `team`, `cost-center`, `model`, and `workload-type`.
- Separate budgets for online serving, Airflow release training, and KubeRay canary analysis.
- Budget alerts for monthly namespace spend, idle GPU waste, and missing allocation labels.
- The split between OpenCost allocation evidence and Kubernetes `ResourceQuota` or `LimitRange` admission guardrails.

## Production Notes

OpenCost is useful here because model platforms can look healthy while quietly wasting money through over-requested training pods, idle GPUs, oversized canary replicas, or unowned batch jobs. The release gate should review cost regressions beside SLO burn, queue pressure, provenance, and governance evidence.

The implementation deliberately uses labels instead of team-specific dashboards as the core contract. Labels survive across Prometheus, OpenCost, cloud billing export, Argo CD, Kueue, and incident tooling. If a workload cannot be attributed to a team, model, and cost center, it should not be promoted automatically.

## Current Research Basis

- OpenCost can run as a Prometheus metric exporter and expose allocation metrics without requiring the full UI.
- OpenCost requires Prometheus for scraping metrics and storage.
- OpenCost generated metrics include CPU, RAM, GPU, node, PVC, and load balancer cost signals.
- Kubernetes `ResourceQuota` constrains namespace consumption, while `LimitRange` can set default requests and limits so quota enforcement is practical.
