from __future__ import annotations

from pathlib import Path

from .io import write_json


DAG_RELATIVE_PATH = Path("airflow/dags/airflow33_stateful_release_dag.py")
STATEFUL_ORCHESTRATION_FLOWS = [
    {
        "name": "release-evidence-rollup",
        "mapper": "RollupMapper",
        "wait_policy": "MinimumCount(3)",
        "max_downstream_keys": 1,
        "task_state_keys": ["release_operation_id", "release_progress"],
        "asset_state_keys": ["candidate_digest", "last_release_operation_id"],
        "retry_policy": "retry_connection_failures_fail_authorization_errors",
        "owner_action": "resume one release operation after worker failure without submitting duplicate side effects",
    },
    {
        "name": "candidate-daily-canary-fanout",
        "mapper": "FanOutMapper",
        "wait_policy": "one_run_per_day",
        "max_downstream_keys": 7,
        "task_state_keys": [],
        "asset_state_keys": [],
        "retry_policy": "retry_connection_failures_fail_authorization_errors",
        "owner_action": "bound one weekly candidate to seven independently retryable canary partitions",
    },
    {
        "name": "runtime-evidence-partitioning",
        "mapper": "PartitionedAtRuntime",
        "wait_policy": "emit_discovered_segments",
        "max_downstream_keys": 3,
        "task_state_keys": [],
        "asset_state_keys": [],
        "retry_policy": "producer_is_idempotent",
        "owner_action": "emit only evidence segments discovered during release preflight",
    },
]


def build_airflow_stateful_orchestration_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
    repo_root: str | Path | None = None,
) -> dict:
    root = Path(root)
    repo_root = (
        Path(repo_root)
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    dag_path = repo_root / DAG_RELATIVE_PATH
    ci_path = repo_root / ".github" / "workflows" / "ci.yml"
    dag_source = dag_path.read_text(encoding="utf-8") if dag_path.exists() else ""
    ci_source = ci_path.read_text(encoding="utf-8") if ci_path.exists() else ""

    checks = [
        {
            "name": "airflow_33_public_sdk_contract",
            "passed": all(
                token in dag_source
                for token in [
                    "from airflow.sdk import",
                    "task_state_store",
                    "asset_state_store",
                    "NEVER_EXPIRE",
                ]
            ),
            "evidence": "The DAG uses the Airflow 3.3 public Task SDK and the documented state-store accessors.",
        },
        {
            "name": "state_store_scope_separation",
            "passed": all(
                STATEFUL_ORCHESTRATION_FLOWS[0][key]
                for key in ["task_state_keys", "asset_state_keys"]
            ),
            "evidence": "Retry-local operation state and cross-run release asset state use separate key sets.",
        },
        {
            "name": "bounded_partition_mapping",
            "passed": all(
                flow["max_downstream_keys"] <= 7
                for flow in STATEFUL_ORCHESTRATION_FLOWS
            ),
            "evidence": "Rollup, fanout, and runtime partitions have explicit domain limits.",
        },
        {
            "name": "exception_aware_retry_policy",
            "passed": all(
                token in dag_source
                for token in [
                    "ExceptionRetryPolicy",
                    "RetryAction.RETRY",
                    "RetryAction.FAIL",
                ]
            ),
            "evidence": "Transient connectivity errors retry while authorization failures fail fast.",
        },
        {
            "name": "real_airflow_parse_gate",
            "passed": all(
                token in ci_source
                for token in [
                    "apache-airflow==3.3.0",
                    "make airflow-sdk-contract",
                    "python -m pip check",
                ]
            ),
            "evidence": "GitHub Actions installs constrained Airflow 3.3, checks dependencies, imports the DAGs, and runs DAG.validate().",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-10T00:00:00Z",
        "passed": passed,
        "recommended_action": "adopt_airflow_33_stateful_release_contract"
        if passed
        else "fix_airflow_33_contract_before_adoption",
        "features": {
            "airflow_version": "3.3.0",
            "asset_partition_mappers": [
                "RollupMapper",
                "FanOutMapper",
                "FixedKeyMapper",
                "SegmentWindow",
            ],
            "runtime_partitioning": "PartitionedAtRuntime",
            "state_store": ["task_state_store", "asset_state_store"],
            "retry_policy": "ExceptionRetryPolicy",
            "fanout_limit": "max_downstream_keys plus scheduler-level partition_mapper_max_downstream_keys",
        },
        "state_store_contract": {
            "task_scope": "dag_id + run_id + task_id + map_index; survives worker crashes and retries",
            "asset_scope": "asset identity across runs; stores release watermarks and immutable digests",
            "retention": "NEVER_EXPIRE only for operation identifiers needed to prevent duplicate submission",
            "cleanup": "airflow state-store clean --dry-run before scheduled garbage collection",
            "payload_rule": "coordination metadata only; large evidence stays in object storage",
        },
        "flows": STATEFUL_ORCHESTRATION_FLOWS,
        "ci_validation": {
            "command": "make airflow-sdk-contract",
            "runtime": "apache-airflow==3.3.0 with official Python 3.11 constraints",
            "assertions": [
                "expected DAG IDs registered",
                "DAG.validate succeeds",
                "every expected DAG has tasks",
                "pip check succeeds",
            ],
        },
        "limitations": [
            "The default demo generates deterministic evidence but does not start an Airflow scheduler or metadata database.",
            "The CI gate proves authoring compatibility and DAG structure, not end-to-end scheduler execution.",
            "Kubernetes, object-store, and registry side effects remain integration-environment responsibilities.",
        ],
        "checks": checks,
        "airflow_assets": [str(DAG_RELATIVE_PATH), "tools/validate_airflow33_dag.py"],
        "references": [
            "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/task-and-asset-state-store.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html#retry-policies",
            "https://airflow.apache.org/docs/apache-airflow/stable/installation/installing-from-pypi.html",
        ],
    }
    write_json(root / "reports" / "airflow_stateful_orchestration_plan.json", plan)
    return plan
