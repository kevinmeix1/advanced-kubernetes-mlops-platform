# Control Plane Diagnostics

`make control-plane-diagnostics` writes `.local/reports/control_plane_diagnostics_plan.json`.

## What It Shows

- Kubernetes v1.36 controller staleness mitigation and stale-cache observability.
- Component `/statusz` and `/flagz` readiness for API server, controller manager, scheduler, and kubelet.
- PSI metric use for CPU, memory, and IO stall detection on ML nodes.
- native histogram readiness for high-resolution control-plane and inference latency metrics.
- Release-controller fail-closed behavior when informer cache freshness is outside budget.

## Production Notes

Release automation can make bad decisions if it reconciles against stale Kubernetes state. This plan records freshness budgets for promotion, canary analysis, and rollback-smoke controllers, then ties them to metrics and runbook actions.

`/statusz` shows what component is actually running. `/flagz` shows effective flags after an upgrade. Together they make feature-gate drift visible before a release controller trusts a new scheduling, admission, or security behavior.

## Senior Review Angle

This is the operator layer of the platform: it shows how the MLOps release system detects stale watches, feature-gate drift, node pressure, and metrics-cardinality risk before those issues corrupt release decisions.

References:

- https://kubernetes.io/blog/2026/04/28/kubernetes-v1-36-staleness-mitigation-for-controllers/
- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
- https://kubernetes.io/blog/2026/04/25/kubernetes-v1-36-psi-metrics/
