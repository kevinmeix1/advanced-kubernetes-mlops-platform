# Kueue Concurrent Admission

`make concurrent-admission` writes `.local/reports/concurrent_admission_plan.json` and pairs it with `kubernetes/kueue-concurrent-admission.yaml`.

## What It Shows

- Kueue `ConcurrentAdmission` feature-gate readiness.
- `ClusterQueue.spec.concurrentAdmissionPolicy.migration.mode: TryPreferredFlavors`.
- `lastAcceptableFlavorName` boundaries for release, batch, and GPU canary workloads.
- Flavor-scoped admission checks that can run in parallel for capacity, image policy, DRA health, model cache, release windows, and cost budgets.
- Parent Workload and Variant Workload evidence for operator triage.

## Why It Matters

Flavor fungibility answers, "what fallback flavor is allowed?" Concurrent Admission answers a harder production question: "can the workload start on an acceptable fallback while Kueue keeps trying the preferred flavor and migrates when it becomes available?"

That matters for ML release systems because training, scoring, and canary analysis often have different economics:

- Release validation can start on spot if the window is tight, but it should migrate back to reservation capacity.
- Batch scoring should not silently migrate into expensive on-demand capacity unless the cost gate allows it.
- GPU canary analysis can start on spot L4, but production release evidence should prefer reserved GPU plus DRA health and model-cache checks.

## Operator Workflow

1. Confirm the Kueue controller manager has `ConcurrentAdmission=true`.
2. Submit workloads to the LocalQueue; Kueue creates a Parent Workload and flavor-constrained Variant Workloads.
3. Inspect Parent Workloads with `kueue.x-k8s.io/concurrent-admission-parent=true`.
4. Compare admitted flavor, variant admission checks, and `lastAcceptableFlavorName`.
5. Hold model promotion if the admitted flavor is outside the release policy.

## Guardrails

Concurrent Admission is alpha in Kueue v0.18, so this project keeps it as evidence and manifest design rather than a required local cluster dependency. Production rollout should start with release-validation queues only, then expand to batch replay after alerting and cost evidence are stable.

## References

- Kueue Concurrent Admission setup: <https://kueue.sigs.k8s.io/docs/tasks/manage/setup_concurrent_admission/>
- Kueue Workload concept: <https://kueue.sigs.k8s.io/docs/concepts/workload/>
- Kueue Concurrent Admission concept: <https://kueue.sigs.k8s.io/docs/concepts/concurrent_admission/>
