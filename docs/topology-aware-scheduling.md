# Topology-Aware Scheduling

`make topology-plan` writes `.local/reports/topology_placement_plan.json` and pairs it with `kubernetes/topology-aware-scheduling.yaml`.

## What It Shows

- Kueue `Topology` and `ResourceFlavor.spec.topologyName` for rack-aware accelerator placement.
- A compact, required topology policy for distributed retraining pods that exchange gradients.
- Kubernetes `topologySpreadConstraints` for canary serving replicas that need zone-level availability.
- A provisioning admission check placeholder so cloud capacity is validated before Kueue admits a topology-sensitive workload.
- Explicit fallbacks when a rack-level assignment is not feasible.

## Production Notes

Topology-aware scheduling is not a blanket replacement for ordinary scheduling. Use compact placement for distributed training and latency-sensitive multi-pod workloads, then use topology spread constraints for serving high availability. Keeping these two intents separate avoids a common production mistake: compacting everything and then losing zone resilience.

References: Kueue Topology Aware Scheduling, Kubernetes topology spread constraints, Kueue AdmissionChecks, and Kubernetes Workload API TAS.
