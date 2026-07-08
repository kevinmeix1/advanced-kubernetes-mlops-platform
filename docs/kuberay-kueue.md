# KubeRay and Kueue

`make kuberay-plan` writes `.local/reports/kuberay_capacity_plan.json` and pairs it with `kubernetes/kuberay-kueue-workloads.yaml`.

## What It Shows

- Kueue-admitted `RayJob` workloads for canary analysis and HPO fanout.
- elastic worker bounds and Ray autoscaling inside a bounded queue allocation.
- Priority separation between release-critical analysis and opportunistic sweeps.
- Airflow submit and wait tasks that keep Ray work observable in the release DAG.
- Fallback paths that preserve idempotency when Ray capacity is unavailable.

## Production Notes

KubeRay is useful when a release gate needs distributed compute but the Airflow scheduler should stay a control plane. The platform queues Ray workloads through Kueue, lets Ray scale workers only after admission, and keeps Airflow responsible for dependency order, retries, and final promotion decisions.

References: Kueue RayJob integration, Ray KubeRay with Kueue, and RayJob gang-scheduling examples.
