# Memory QoS Tiered Protection

`make memory-qos` writes `.local/reports/memory_qos_plan.json`.

## What It Shows

- Kubernetes v1.36 Memory QoS with `memoryReservationPolicy: TieredReservation`.
- cgroup v2 and kernel guardrails for ML-heavy node pools.
- `memory.min` hard protection for Guaranteed release controllers.
- `memory.low` soft protection for Burstable training and canary workloads.
- PSI and `memory.high` throttling alerts before latency regressions are blamed on the model.

## Production Notes

Memory pressure can make training, canary analysis, and rollback jobs look flaky even when model code is healthy. This plan makes the memory-protection intent explicit: release control stays Guaranteed, productive training gets Burstable protection, and ad-hoc diagnostics remain reclaimable.

The v1.36 update separates throttling from reservation. Enabling `MemoryQoS` turns on `memory.high` throttling, while `TieredReservation` opts into `memory.min` and `memory.low` protection.

## Senior Review Angle

This is a node-level reliability control for ML platforms. It shows that the project understands cgroup v2, QoS classes, request sizing, PSI signals, and why memory protection has to be tied to workload criticality rather than sprinkled across every pod.

References:

- https://kubernetes.io/blog/2026/04/29/kubernetes-v1-36-memory-qos-tiered-protection/
- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
