# DRA AdminAccess Diagnostics

`make admin-access-diagnostics` writes `.local/reports/admin_access_diagnostics_plan.json` and pairs it with `kubernetes/dra-admin-access-diagnostics.yaml`.

## What It Shows

- Kubernetes v1.36 DRA `AdminAccess` for ResourceClaims in a namespace labeled `resource.kubernetes.io/admin-access: "true"`.
- Privileged but bounded health diagnostics for devices already allocated to release workloads.
- Least-privilege RBAC that separates claim creation in `mlops-dra-admin` from read-only status inspection in `mlops`.
- Short-lived diagnostic claims with cleanup deadlines, incident linkage, and Prometheus alerts.
- A runbook path from `ResourceHealthStatus` to deeper device evidence without widening canary traffic.

## Production Notes

AdminAccess is deliberately a break-glass diagnostic path. It is useful when a GPU-backed workload is still running, but the platform needs to inspect the in-use device for health, topology, or driver evidence before tainting a device or moving a release. The demo keeps this access in a dedicated admin namespace and makes the cleanup/audit requirements explicit so privileged ResourceClaims do not become an ordinary scheduling shortcut.

This complements the `ResourceHealthStatus` plan: health status tells the release controller that a device is suspect, while AdminAccess captures the deeper evidence needed for an incident review or device quarantine decision.

## References

- Kubernetes Dynamic Resource Allocation: <https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/>
- Kubernetes v1.36 release highlights: <https://github.com/kubernetes/sig-release/discussions/2958>
- KEP-5018 DRA Admin Access: <https://www.kubernetes.dev/resources/keps/5018/>
