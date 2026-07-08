# Airflow DAG Bundles

`make dag-bundle-plan` writes `.local/reports/dag_bundle_versioning_plan.json` and pairs it with `airflow/dag-bundle-config.ini`.

## What It Shows

- Airflow 3 `GitDagBundle` configuration for the release DAG instead of an unversioned local DAG folder.
- Bundle versioning kept on with `disable_bundle_versioning = False`.
- Rerun semantics set to `rerun_with_latest_version = False` for incident replay and failed-release debugging.
- Git credentials referenced through `git_conn_id`, so tokens belong in Airflow Connections or a secrets backend.
- `sparse_dirs` scoped to DAGs, Kubernetes manifests, contracts, and package code to reduce scheduler parse cost.
- Scheduler-managed backfills separated into current-code backfills and incident reproductions that preserve the original bundle version.

## Production Notes

Release orchestration needs reproducibility at the DAG-code layer, not only the model or container layer. If a failed model promotion is rerun after a commit changes the DAG, the team needs to know whether it is debugging the original incident or testing a new workflow.

This project keeps release DAG reruns pinned to the original bundle version. New backfills can intentionally use current DAG code, but incident replay should record the original `bundle_name`, `bundle_version`, model version, MLflow run id, and workload image tag in the release evidence.

## Failure Recovery

- If the Git bundle cannot refresh, restore Git connectivity and verify `github_dag_bundle` before restarting DAG processors.
- If a bad DAG commit is deployed, revert the commit and launch a fresh run instead of mutating evidence from the failed bundle version.
- If a replay must compare old and new code, run the original bundle as incident evidence and a separate latest-code run as remediation evidence.

## References

- Airflow DAG Bundles: <https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html>
- Airflow `GitDagBundle`: <https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html#gitdagbundle>
- Airflow rerun behavior: <https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/dag-bundles.html#rerun-behavior>
