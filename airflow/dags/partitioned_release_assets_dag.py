from __future__ import annotations

from airflow.sdk import Asset, CronPartitionTimetable, DAG, PartitionedAssetTimetable, StartOfHourMapper, task


raw_scoring_events = Asset("s3://mlops/raw/events/hourly")
churn_features = Asset("s3://mlops/features/churn/hourly")
candidate_model = Asset("mlflow://models/churn-risk/candidate")
canary_metrics = Asset("kserve://churn-risk/canary-metrics")
release_decision = Asset("s3://mlops/release/churn-risk/decisions")


with DAG(
    dag_id="partitioned_churn_feature_scoring",
    schedule=CronPartitionTimetable("0 * * * *", timezone="UTC"),
    catchup=False,
    tags=["airflow-3.2", "asset-partitioning", "release"],
):

    @task(outlets=[churn_features])
    def build_feature_partition(dag_run=None) -> dict[str, str | None]:
        partition_key = dag_run.partition_key if dag_run else None
        return {
            "partition_key": partition_key,
            "source_asset": raw_scoring_events.uri,
            "target_asset": churn_features.uri,
        }

    build_feature_partition()


with DAG(
    dag_id="partitioned_churn_release_gate",
    schedule=PartitionedAssetTimetable(
        assets=churn_features & candidate_model & canary_metrics,
        default_partition_mapper=StartOfHourMapper(),
    ),
    catchup=False,
    tags=["airflow-3.2", "partitioned-backfill", "canary"],
):

    @task(outlets=[release_decision])
    def evaluate_release_partition(dag_run=None) -> dict[str, str | None]:
        partition_key = dag_run.partition_key if dag_run else None
        return {
            "partition_key": partition_key,
            "decision_asset": release_decision.uri,
            "evidence": "aligned model, feature, and canary metric partitions",
        }

    evaluate_release_partition()
