# Indexed Job Resilience

Release validation is a finite batch problem hiding inside an online MLOps platform. Data checks, cohort scoring, canary analysis, drift probes, and rollback smoke tests should run as deterministic shards with bounded retries.

## Kubernetes Controls

- `completionMode: Indexed` gives every release shard a deterministic `JOB_COMPLETION_INDEX`.
- `backoffLimitPerIndex` limits retries for one bad cohort without delaying unrelated release checks.
- `maxFailedIndexes` stops wasteful release waves when too many shards fail.
- `podFailurePolicy` marks bad cohort data as `FailIndex`, image/config problems as `FailJob`, and node disruption as `Ignore`.
- `successPolicy` can declare quorum success while preserving failed-index evidence for targeted reruns.

## Airflow Backfill Create

Historical release repair uses failed-only reprocessing:

```bash
airflow backfill create \
  --dag-id enterprise_kubernetes_mlops_release \
  --from-date 2026-07-01 \
  --to-date 2026-07-07 \
  --reprocess-behavior failed \
  --max-active-runs 2 \
  --run-backwards
```

Use reverse ordering so recent release evidence recovers first, and keep the backfill `max_active_runs` lower than the live release DAG concurrency.

## Failure Semantics

| Failure | Policy | Outcome |
| --- | --- | --- |
| Bad scoring cohort | `FailIndex` | Mark that cohort failed and keep unrelated checks running. |
| Bad image or command | `FailJob` | Stop the wave because retries would be wasteful. |
| Node drain or preemption | `Ignore` | Do not count infrastructure churn against the retry budget. |
| Too many failed shards | `maxFailedIndexes` | Stop the wave and keep rollback capacity available. |

## Recovery Flow

1. Inspect `status.failedIndexes` and `status.completedIndexes`.
2. Rerun only failed cohort or release-check shards.
3. Keep rollback smoke checks in the highest-priority Kueue queue.
4. Attach `indexed_job_resilience_plan.json` to release evidence.
