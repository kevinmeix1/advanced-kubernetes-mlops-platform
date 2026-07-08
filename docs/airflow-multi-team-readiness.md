# Airflow Multi-Team Readiness

`make multi-team-readiness` writes `.local/reports/multi_team_readiness_plan.json`.

## What It Shows

- `core.multi_team = True` in the Airflow preview profile.
- DAG Bundle `team_name` ownership for release-control DAGs.
- Team-scoped pools with `airflow pools set ... --team-name`.
- Team-scoped variables and connections using `AIRFLOW_VAR__ML_PLATFORM___...` and `AIRFLOW_CONN__ML_PLATFORM___...`.
- Team-specific executor routing and `airflow triggerer --team-name ml-platform`.
- `AssetAccessControl` with `producer_teams`, `consumer_teams`, and `allow_global=False` for cross-team release assets.

## Production Notes

Airflow multi-team support is still preview/experimental, so this project treats it as readiness evidence rather than a hard local runtime dependency. In a real deployment, create `ml-platform` before DAG bundle sync, run a team triggerer for deferrable Kubernetes tasks, and keep release pools, secrets, and executors scoped to that team.

This is logical/resource isolation inside one Airflow deployment. For regulated hard tenancy boundaries, run separate Airflow deployments or separate Kubernetes namespaces with independent metadata stores.

## Example Bootstrap

```bash
airflow teams create ml-platform
airflow pools set model_release_pool 8 "Release and rollback pool" --team-name ml-platform
airflow pools set canary_analysis_pool 6 "Canary analysis pool" --team-name ml-platform
airflow triggerer --team-name ml-platform
```

## Asset Filtering Contract

```python
from airflow.sdk import Asset
from airflow.sdk.definitions.asset import AssetAccessControl

release_asset = Asset(
    "model://churn-risk/candidate",
    access_control=AssetAccessControl(
        producer_teams={"ml-platform"},
        consumer_teams={"ml-serving", "ml-training", "ml-observability"},
        allow_global=False,
    ),
)
```

## Senior Review Angle

The goal is to show that release orchestration is ready for multiple teams without overselling the feature. The report captures bootstrap commands, config keys, DAG Bundle ownership, executor routing, team-scoped secrets, and asset-event filtering in one auditable artifact.

References:

- https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/multi-team.html
- https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html
- https://airflow.apache.org/blog/airflow-3.2.0/
