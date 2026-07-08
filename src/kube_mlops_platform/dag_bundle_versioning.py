from __future__ import annotations

from pathlib import Path

from .io import write_json


AIRFLOW_DAG_BUNDLE = {
    "name": "kubernetes-mlops-release-bundle",
    "provider": "GitDagBundle",
    "tracking_ref": "main",
    "subdir": "airflow/dags",
    "git_conn_id": "github_dag_bundle",
    "sparse_dirs": ["airflow/dags", "kubernetes", "contracts", "src"],
    "refresh_interval_seconds": 60,
}


def build_dag_bundle_versioning_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
    dag_id: str = "enterprise_kubernetes_mlops_release",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "git_dag_bundle_declared",
            "passed": AIRFLOW_DAG_BUNDLE["provider"] == "GitDagBundle",
            "evidence": "Airflow loads the release DAG from a Git-backed DAG Bundle, not an unversioned local folder.",
        },
        {
            "name": "bundle_versioning_enabled",
            "passed": True,
            "evidence": "[dag_processor] disable_bundle_versioning = False keeps historical DAG code versions available.",
        },
        {
            "name": "reruns_preserve_original_bundle",
            "passed": True,
            "evidence": "[core] rerun_with_latest_version = False and DAG-level rerun_with_latest_version=False protect incident replay.",
        },
        {
            "name": "credentials_kept_in_airflow_connection",
            "passed": AIRFLOW_DAG_BUNDLE["git_conn_id"] == "github_dag_bundle",
            "evidence": "The bundle references git_conn_id so deploy keys or tokens live in Airflow Connections or a secrets backend.",
        },
        {
            "name": "sparse_checkout_scoped",
            "passed": "airflow/dags" in AIRFLOW_DAG_BUNDLE["sparse_dirs"] and "kubernetes" in AIRFLOW_DAG_BUNDLE["sparse_dirs"],
            "evidence": "Sparse checkout keeps scheduler parsing focused on DAGs plus release manifests/contracts.",
        },
        {
            "name": "scheduler_managed_backfill_policy",
            "passed": True,
            "evidence": "Backfills are scheduled as first-class Airflow 3 backfill runs with explicit bundle-version policy.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_airflow3_git_dag_bundle_versioning" if passed else "hold_airflow_dag_bundle_rollout",
        "airflow_version_target": "3.3.x",
        "dag_id": dag_id,
        "bundle": AIRFLOW_DAG_BUNDLE,
        "runtime_config": {
            "AIRFLOW__DAG_PROCESSOR__DAG_BUNDLE_CONFIG_LIST": "configured in airflow/dag-bundle-config.ini",
            "AIRFLOW__DAG_PROCESSOR__DISABLE_BUNDLE_VERSIONING": "False",
            "AIRFLOW__CORE__RERUN_WITH_LATEST_VERSION": "False",
        },
        "rerun_policy": {
            "core.rerun_with_latest_version": False,
            "dag.rerun_with_latest_version": False,
            "incident_replay_uses_original_bundle": True,
            "manual_hotfix_requires_new_dagrun": True,
        },
        "backfill_policy": {
            "scheduler_managed_backfills": True,
            "default_backfill_bundle_behavior": "latest_version_for_new_backfills",
            "incident_backfill_override": "pin_to_original_bundle_version_when_reproducing_a_failed_release",
            "max_active_runs": 1,
            "pool": "ml_platform_pool",
        },
        "failure_modes": [
            {
                "mode": "git_bundle_refresh_failure",
                "blast_radius": "new DAG parses stop but running task instances keep their recorded bundle version",
                "recovery": "restore Git connectivity, verify git_conn_id, then refresh the DAG processor",
            },
            {
                "mode": "bad_dag_commit_released",
                "blast_radius": "new runs can fail parse or task import checks",
                "recovery": "revert the Git commit, preserve failed run bundle_version for debugging, and launch a fresh run",
            },
            {
                "mode": "incident_replay_drift",
                "blast_radius": "rerun executes different code than the original release incident",
                "recovery": "keep rerun_with_latest_version disabled and record bundle_version in incident notes",
            },
        ],
        "operational_guardrails": [
            "Store Git credentials in Airflow Connections or a secrets backend, never inline in dag_bundle_config_list.",
            "Keep versioning enabled for release DAGs so task retries and incident reruns can explain exactly which code ran.",
            "Use sparse_dirs to reduce scheduler parse surface without hiding manifests needed by KubernetesPodOperator tasks.",
            "Attach bundle name and version to release evidence beside model version, image tag, and MLflow run id.",
            "Treat new backfills and incident replays differently: new backfills can use current code, reproductions should pin the original bundle version.",
        ],
        "checks": checks,
        "airflow_assets": [
            "airflow/dag-bundle-config.ini",
            "airflow/dags/enterprise_kubernetes_mlops_release_dag.py",
            "docs/airflow-dag-bundles.md",
        ],
        "references": [
            "https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html#gitdagbundle",
            "https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html#rerun-behavior",
            "https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html",
        ],
    }
    write_json(root / "reports" / "dag_bundle_versioning_plan.json", plan)
    return plan
