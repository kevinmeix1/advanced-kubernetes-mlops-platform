# DRA Advanced Device Sharing

`make advanced-device-sharing` writes `.local/reports/advanced_device_sharing_plan.json` and pairs it with `kubernetes/dra-advanced-device-sharing.yaml`.

## What It Shows

- DRA prioritized device alternatives for canary and release-analysis workloads.
- Partitionable devices for splitting expensive accelerators into logical slices; the manifest also calls out partitionable device examples explicitly.
- Consumable capacity examples for bounded GPU memory or bandwidth allocation.
- Device binding conditions that delay scheduler binding until external accelerator setup is ready.

## Production Notes

This is the efficiency layer above basic `ResourceClaimTemplate` usage. The platform should not require one exact device shape when an ordered set of alternatives is acceptable. It should also avoid reserving a whole accelerator for batch scoring if a smaller partition or consumable capacity slice is sufficient.

Device binding conditions matter for fabric-attached devices and other accelerators that need node-specific preparation. The scheduler waits in PreBind for readiness, aborts when a binding failure condition appears, and surfaces that as a release blocker rather than a generic task retry.

Consumable capacity remains a target-cluster compatibility decision in this demo. Keep it opt-in until the Kubernetes version and DRA driver support it cleanly.

## References

- Kubernetes v1.36 DRA update: <https://kubernetes.io/blog/2026/05/07/kubernetes-v1-36-dra-136-updates/>
- Kubernetes Dynamic Resource Allocation: <https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/>
- Kubernetes DRA consumable capacity: <https://kubernetes.io/blog/2025/09/18/kubernetes-v1-34-dra-consumable-capacity/>
