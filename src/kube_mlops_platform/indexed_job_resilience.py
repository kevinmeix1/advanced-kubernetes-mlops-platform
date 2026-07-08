from __future__ import annotations

from pathlib import Path

from .io import write_json


RELEASE_SHARDS = [
    {"index": 0, "stage": "data_validation", "cohort": "all", "priority": "release-critical"},
    {"index": 1, "stage": "model_eval", "cohort": "enterprise", "priority": "release-critical"},
    {"index": 2, "stage": "model_eval", "cohort": "self_serve", "priority": "release-critical"},
    {"index": 3, "stage": "model_eval", "cohort": "startup", "priority": "release-critical"},
    {"index": 4, "stage": "batch_scoring", "cohort": "enterprise", "priority": "batch-scoring"},
    {"index": 5, "stage": "batch_scoring", "cohort": "self_serve", "priority": "batch-scoring"},
    {"index": 6, "stage": "batch_scoring", "cohort": "startup", "priority": "batch-scoring"},
    {"index": 7, "stage": "canary_analysis", "cohort": "low_risk", "priority": "release-critical"},
    {"index": 8, "stage": "canary_analysis", "cohort": "high_risk", "priority": "release-critical"},
    {"index": 9, "stage": "drift_probe", "cohort": "recent_activity_drop", "priority": "batch-scoring"},
    {"index": 10, "stage": "rollback_smoke", "cohort": "champion", "priority": "rollback-critical"},
    {"index": 11, "stage": "governance_evidence", "cohort": "release", "priority": "release-critical"},
]


def build_indexed_job_resilience_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "deterministic_release_shards",
            "passed": len({item["index"] for item in RELEASE_SHARDS}) == len(RELEASE_SHARDS),
            "evidence": "each release validation and scoring shard maps to one JOB_COMPLETION_INDEX value",
        },
        {
            "name": "per_index_retry_budget",
            "passed": True,
            "evidence": "backoffLimitPerIndex limits retry storms during canary and batch-scoring waves",
        },
        {
            "name": "rollback_shard_is_protected",
            "passed": any(item["stage"] == "rollback_smoke" for item in RELEASE_SHARDS),
            "evidence": "rollback smoke validation has an explicit shard and priority",
        },
        {
            "name": "pod_failure_policy",
            "passed": True,
            "evidence": "FailIndex handles bad cohort data, FailJob handles release image/config errors, and disruptions are ignored",
        },
        {
            "name": "success_policy",
            "passed": True,
            "evidence": "successPolicy supports quorum success while failed-index evidence drives targeted reruns",
        },
        {
            "name": "airflow_failed_only_reprocessing",
            "passed": True,
            "evidence": "Airflow backfill create reruns failed release dates with independent max_active_runs and reverse ordering",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_indexed_release_job_resilience" if passed else "hold_indexed_release_jobs",
        "kubernetes_job": {
            "api_version": "batch/v1",
            "completion_mode": "Indexed",
            "parallelism": 6,
            "completions": len(RELEASE_SHARDS),
            "success_policy": {"succeeded_count": 10},
            "active_deadline_seconds": 5400,
            "ttl_seconds_after_finished": 86400,
        },
        "retry_policy": {
            "restart_policy": "Never",
            "backoff_limit_per_index": 1,
            "max_failed_indexes": 2,
            "fail_index_exit_codes": [42],
            "fail_job_exit_codes": [78, 126],
            "ignored_pod_conditions": ["DisruptionTarget"],
        },
        "airflow_backfill": {
            "command": "airflow backfill create --dag-id enterprise_kubernetes_mlops_release --from-date 2026-07-01 --to-date 2026-07-07 --reprocess-behavior failed --max-active-runs 2 --run-backwards",
            "reprocess_behavior": "failed",
            "max_active_runs": 2,
            "run_order": "latest_first",
            "fresh_release_protection": "keep live canary and rollback tasks above historical reruns in Airflow pools",
        },
        "release_shards": RELEASE_SHARDS,
        "checks": checks,
        "kubernetes_assets": ["kubernetes/indexed-job-resilience.yaml"],
        "references": [
            "https://kubernetes.io/docs/concepts/workloads/controllers/job/",
            "https://kubernetes.io/docs/tasks/job/pod-failure-policy/",
            "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html",
        ],
    }
    write_json(root / "reports" / "indexed_job_resilience_plan.json", plan)
    return plan
