# Kueue Elastic Workloads

`make elastic-workload-plan` writes `.local/reports/elastic_workload_plan.json` and documents how the release platform would use Kueue Workload Slices for elastic training, batch scoring, canary analysis, and rollback validation.

## What It Shows

- Kueue `ElasticJobsViaWorkloadSlices` rollout plan with explicit rollback notes.
- JobSet integration for release training and batch scoring waves.
- Workload Slice annotations for original and replacement slices.
- Bounded scale-up for candidate training and GPU canary analysis.
- Scale-down by replacement slice so emergency rollback validation can reclaim quota.
- Prometheus alerts for pending slices, replacement lag, and JobSet replica lag.

## Production Notes

Elastic release workloads should never compete with rollback capacity. Use spare quota to widen training or scoring, but shrink elastic slices first when release safety work needs the cluster. The runbook should compare Kueue admitted Workload Slices, JobSet ready replicas, and actual pods before increasing parallelism.

If replacement admission fails or ClusterQueue usage does not match admitted slices, disable `ElasticJobsViaWorkloadSlices` and fall back to fixed-size JobSet waves until the accounting issue is understood.

## Current Research Basis

- Kueue Elastic Workloads use Workload Slices to track partial allocations during scale-up and scale-down.
- Kueue labels and annotations include workload-slice identifiers and replacement links.
- Kueue can schedule JobSet workloads by using the `kueue.x-k8s.io/queue-name` label.
- Kueue Workload objects represent the resource requirements that Kueue admits into a queue.
