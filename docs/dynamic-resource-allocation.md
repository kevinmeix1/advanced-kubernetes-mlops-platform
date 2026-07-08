# Dynamic Resource Allocation

This project now models accelerator scheduling with Kubernetes Dynamic Resource Allocation (DRA), not only static `nvidia.com/gpu` limits.

The demo writes `reports/device_allocation_plan.json` and the Kubernetes example lives in `kubernetes/dynamic-resource-allocation.yaml`.

## What It Shows

- `DeviceClass` and `ResourceClaimTemplate` resources for accelerator-aware canary work.
- Kueue queue annotations so expensive canary pods are admitted only when release quota is available.
- Explicit time-slicing versus MIG trade-offs.
- CPU fallback paths for rollback validation when accelerators are exhausted.
- ResourceClaim/device-health monitoring before increasing canary traffic.

## Production Notes

DRA is most useful when workload owners need device capabilities rather than a raw GPU count. For this platform, release-critical rollback stays CPU-runnable, while low-risk canary inference can use a time-sliced L4 claim. Heavier or tenant-sensitive workloads should use MIG or exclusive claims.

References: Kubernetes DRA docs, Kueue workload admission docs, and NVIDIA GPU Operator sharing docs.
