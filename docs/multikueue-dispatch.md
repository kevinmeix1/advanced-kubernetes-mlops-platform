# MultiKueue Dispatch

`make multikueue-dispatch` writes `.local/reports/multikueue_dispatch_plan.json` and pairs it with `kubernetes/multikueue-dispatch.yaml`.

This release platform uses MultiKueue for candidate training, batch scoring, canary analysis, and rollback smoke evidence. The goal is not just extra capacity; it is release safety. A candidate cannot advance when the Workload has not selected a worker cluster. The champion registry alias stays intact until evidence Workloads report `status.clusterName`.

## Operating Model

- Airflow submits release Jobs to a manager cluster LocalQueue.
- The manager reserves ClusterQueue quota and delegates Workloads to worker clusters through the `kueue.x-k8s.io/multikueue` admission check.
- Worker clusters mirror namespaces, LocalQueues, service accounts, registry credentials, and image admission policy.
- `status.nominatedClusterNames` is watched while a Workload is pending.
- `status.clusterName` is recorded after a worker admits the Workload.
- The remote Job is linked with `kueue.x-k8s.io/prebuilt-workload-name`.
- Missing worker assignment freezes candidate promotion and keeps the current champion alias.

## Failure Recovery

If candidate training cannot dispatch, shrink the training wave and rerun release evidence on the fixed `churn-release-queue`. If batch scoring lags during a canary, preempt scoring and run rollback smoke first. If GPU canary analysis cannot dispatch or book capacity, skip GPU-only evidence, require manual review, and preserve the existing champion route.

## References

- Kueue MultiKueue concept: <https://kueue.sigs.k8s.io/docs/concepts/multikueue/>
- MultiKueue setup: <https://kueue.sigs.k8s.io/docs/tasks/manage/setup_multikueue/>
- Kubernetes Job in Multi-Cluster: <https://kueue.sigs.k8s.io/docs/tasks/run/multikueue/job/>
