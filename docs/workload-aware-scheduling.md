# Kubernetes Workload-Aware Scheduling

`make workload-aware-scheduling` writes `.local/reports/workload_aware_scheduling_plan.json`.

## What It Shows

- Kubernetes v1.36 `scheduling.k8s.io/v1alpha2` Workload and PodGroup readiness.
- `WorkloadWithJob` fixed-shape Indexed Job integration.
- PodGroup atomic gang scheduling with `schedulingPolicy.gang.minCount`.
- Topology constraints for rack, zone, or host placement.
- Workload-aware preemption using PodGroup `priority` and `disruptionMode: PodGroup`.
- DRA ResourceClaim sharing at PodGroup scope for high-cardinality accelerator workloads.

## Production Notes

Workload-Aware Scheduling is alpha in Kubernetes v1.36 and should be treated as a readiness profile. This repo keeps it behind explicit feature gates and uses Kueue as the stable operational fallback.

The first production candidate is a fixed-shape Indexed Job where `.spec.parallelism == .spec.completions`, `.spec.completionMode` is `Indexed`, and the Pod template does not set `schedulingGroup` manually. More elastic shapes should stay on Kueue/JobSet until the upstream API graduates.

## Senior Review Angle

This demonstrates that release jobs are designed as coherent workloads, not random pods competing one at a time. The report connects Airflow release gates, Kueue admission, PodGroup scheduling, DRA ResourceClaims, rollback fallback, and release-admission evidence.

References:

- https://kubernetes.io/blog/2026/05/13/kubernetes-v1-36-advancing-workload-aware-scheduling/
- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
- https://kubernetes.io/blog/2026/05/07/kubernetes-v1-36-dra-136-updates/
