# DRA Resource Health Status

`make resource-health-status` writes `.local/reports/resource_health_status_plan.json` and pairs it with `kubernetes/dra-resource-health-status.yaml`.

## What It Shows

- Kubernetes v1.36 `ResourceHealthStatus` for DRA device health in Pod status.
- `ResourceClaim` `status.devices` as companion evidence for allocated accelerators.
- Kubelet `PodResourcesLister` and `DynamicResource` metrics as the runtime cross-check.
- `DeviceTaintRule` quarantine for unhealthy GPU devices.
- Release-safe fallbacks when canary or Ray analysis devices become `Unhealthy` or `Unknown`.

## Production Notes

Accelerator failures often look like application failures unless the platform surfaces the device health path. This report makes that operationally explicit: inspect `status.containerStatuses[*].allocatedResourcesStatus`, compare it with `ResourceClaim.status.devices`, quarantine the bad device, and keep rollback validation CPU-runnable while the accelerator pool recovers.

The demo blocks canary advancement when release-critical devices are unhealthy or unknown, but it keeps emergency rollback validation schedulable without a DRA claim.

## References

- Kubernetes Dynamic Resource Allocation: <https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/>
- Kubernetes v1.36 DRA update: <https://kubernetes.io/blog/2026/05/07/kubernetes-v1-36-dra-136-updates/>
- Kubernetes v1.36 release highlights: <https://github.com/kubernetes/sig-release/discussions/2958>
