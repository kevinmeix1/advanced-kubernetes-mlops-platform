# HPA Scale To Zero

`make hpa-scale-zero` writes `.local/reports/hpa_scale_to_zero_plan.json`.

## What It Shows

- Kubernetes v1.36 `HPAScaleToZero` as an alpha, disabled-by-default feature gate.
- `autoscaling/v2` HorizontalPodAutoscaler objects with `minReplicas: 0`.
- Object and External metrics only, because Resource metrics cannot wake a workload from zero.
- Explicit cold-start budgets for batch scoring, drift replay, and canary-analysis workers.
- A protected workload list for release admission, rollback smoke checks, and online inference.

## Production Notes

Scale to zero is useful for expensive, bursty ML platform workers, but it is not a blanket reliability improvement. The platform keeps user-facing inference and safety controllers warm, then applies scale-to-zero only to backlog-driven workers where a cold start is acceptable.

The operational contract is the metric adapter: if queue-depth or object-backlog metrics disappear, the HPA cannot safely wake a zero-replica workload. The manifest pairs the HPA objects with alerts for missing metrics, failed wakeups, and cold-start budget breaches.

## Senior Review Angle

This is a cost and capacity control with clear boundaries. It demonstrates feature-gate awareness, HPA API constraints, external metric adapter dependency, cold-start SLO thinking, and a realistic decision not to scale every component to zero.

References:

- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
- https://kubernetes.io/docs/reference/kubernetes-api/autoscaling/horizontal-pod-autoscaler-v2/
- https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/
