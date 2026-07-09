# Suspended Job Resource Mutation

`make suspended-job-resources` writes `.local/reports/suspended_job_resources_plan.json`.

## What It Shows

- Kubernetes v1.36 `MutablePodResourcesForSuspendedJobs` beta behavior.
- Queue-controller resource patching before a Job is unsuspended.
- CPU, memory, GPU, and extended resource request changes on suspended Jobs.
- A hard boundary that active Jobs use in-place resize or replacement instead.
- Admission and alert guardrails around `spec.suspend: true`.

## Production Notes

This pattern is useful when Airflow, Kueue, or a release controller creates Jobs in a suspended state, waits for quota and cache evidence, then adjusts requests before starting Pods. It prevents over-admission and avoids wasting scarce GPU or CPU quota on a request shape that no longer fits the cluster.

It is intentionally not an active-Pod resize feature. Once a Job is running, use in-place resize where appropriate or create a replacement Job with a new template.

## Senior Review Angle

This shows scheduler-aware batch operations: queue controllers own when work starts, resource changes are tied to quota evidence, and unsuspend is gated. It is a small feature, but it demonstrates the difference between mutable queued work and unsafe mutation of running workloads.

References:

- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
- https://kubernetes.io/docs/concepts/workloads/controllers/job/
