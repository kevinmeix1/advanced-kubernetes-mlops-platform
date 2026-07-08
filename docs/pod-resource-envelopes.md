# Pod Resource Envelopes

`make pod-resource-envelopes` writes `.local/reports/pod_resource_envelope_plan.json` and pairs it with `kubernetes/pod-resource-envelopes.yaml`.

## What It Shows

- Kubernetes `PodLevelResources` with pod-level `spec.resources` for multi-container release, canary, and replay pods.
- Stable Pod Scheduling Readiness through `schedulingGates`.
- Release gate removal only after model cache, Gateway route, Kueue admission, and release evidence exist.
- Scheduler observability with `scheduler_pending_pods{queue="gated"}`.
- Dynamic Resource Allocation guardrails so ResourceClaims and container requests stay inside the pod-level envelope.

## Production Notes

This is a scheduler-churn control. Expensive ML pods should not immediately enter normal pending state while waiting for model cache downloads, release evidence, or Kueue admission. Scheduling gates keep them explicitly gated until the control plane removes the prerequisite gates.

Pod-level resources make sidecar-heavy jobs easier to budget because the pod owns a CPU and memory envelope while containers can still carry their own local requests. Use the `PodLevelResourceManagers` feature gate when CPUManager, MemoryManager, or TopologyManager alignment matters.

## References

- Kubernetes pod-level resources: <https://kubernetes.io/docs/tasks/configure-pod-container/assign-pod-level-resources/>
- Kubernetes Pod Scheduling Readiness: <https://kubernetes.io/docs/concepts/scheduling-eviction/pod-scheduling-readiness/>
- Kubernetes Dynamic Resource Allocation: <https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/>
