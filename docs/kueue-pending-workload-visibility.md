# Kueue Pending Workload Visibility

`make pending-workload-visibility` writes `.local/reports/pending_workload_visibility_plan.json` and pairs it with `kubernetes/kueue-pending-workload-visibility.yaml`.

## What It Shows

- Kueue `VisibilityOnDemand` for ClusterQueue and LocalQueue pending workload queries.
- RBAC for `visibility.kueue.x-k8s.io` `clusterqueues/pendingworkloads` and `localqueues/pendingworkloads`.
- API Priority and Fairness setup via the Kueue release `visibility-apf.yaml`.
- Prometheus signals for admission wait time and pending requested resources.
- Queue triage actions for release validation, batch replay, and experimentation.

## Production Notes

Senior reviewers care about what operators do when jobs are stuck. Pending-workload visibility turns a vague "Kueue queue is full" story into a concrete workflow: query ClusterQueue visibility for platform triage, query LocalQueue visibility for tenant self-service, and attach the queue snapshot to release evidence when promotion is held.

The demo keeps low-priority experiments queued, splits batch replay before it borrows on-demand quota, and holds canary promotion when release validation is first in line but not yet admitted.

## References

- Kueue monitor pending workloads: <https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/>
- Kueue pending workloads on demand: <https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/pending_workloads_on_demand/>
- Kueue Prometheus metrics: <https://kueue.sigs.k8s.io/docs/reference/metrics/>
