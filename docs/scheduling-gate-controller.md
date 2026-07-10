# Scheduling Gate Controller

`make scheduling-gate-controller` writes `.local/reports/scheduling_gate_controller_plan.json` and pairs it with `kubernetes/scheduling-gate-controller.yaml`.

This project already declares Kubernetes Pod Scheduling Readiness gates on release, canary, and replay pods. The production issue is the controller that removes those gates. A manual `kubectl patch` is easy to demo, but it is not a reliable platform pattern because it hides stale prerequisites, duplicate operator actions, and partially-ready accelerator state.

## Controller Contract

- Watches gated pods, Kueue Workloads, DRA ResourceClaims, KServe route status, and model-cache evidence.
- Removes gates only when the full evidence set for that pod is ready.
- Uses leader election and an idempotency key built from pod UID, gate name, and evidence digest.
- The controller fails closed by leaving pods `SchedulingGated` when evidence is missing or ambiguous.
- Creates stale-gate incidents instead of letting expensive ML release work sit in a silent queue.

## Demo Scenario

- `release-validation-controller` releases after DAG bundle, release admission, and asset-event evidence are ready.
- `churn-canary-analysis` releases after model cache, Gateway route, and endpoint-picker health are ready.
- `batch-scoring-replay` remains gated because Kueue admission and DRA allocation are not complete, then raises a stale-gate incident after 30 minutes.

## Observability

- `scheduler_pending_pods{queue="gated"}` separates intentionally gated pods from unschedulable pods.
- `mlops_scheduling_gate_age_seconds` exposes stuck gates before release SLOs expire.
- `mlops_scheduling_gate_patch_total` tracks successful gate removals by namespace and owner.
- `mlops_scheduling_gate_stale_total` feeds incident creation and reviewer-facing demo evidence.

## Why This Matters

For ML platforms, the expensive failure is not only a failed job. It is scheduling a GPU or canary-analysis pod before the model cache is warm, before Kueue has admitted the workload, or before DRA has bound a healthy device. Scheduling gates let the platform hold work before the default scheduler and autoscaler churn on it; the controller makes that hold auditable, observable, and reversible.

## References

- Kubernetes Pod Scheduling Readiness: <https://kubernetes.io/docs/concepts/scheduling-eviction/pod-scheduling-readiness/>
- Kubernetes Dynamic Resource Allocation: <https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/>
- Kueue Workloads: <https://kueue.sigs.k8s.io/docs/concepts/workload/>
