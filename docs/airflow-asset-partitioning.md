# Airflow Asset Partitioning

`make asset-partitioning-plan` writes `.local/reports/asset_partitioning_plan.json` and pairs it with `airflow/dags/partitioned_release_assets_dag.py`.

## What It Shows

- Airflow 3.2 asset partitioning for partition-aware release workflows.
- `CronPartitionTimetable` for scheduled partitioned DAG runs.
- `PartitionedAssetTimetable` and `StartOfHourMapper` for aligned feature, model, and canary metric partitions.
- `dag_run.partition_key` captured as release evidence, MLflow tags, and OpenLineage facets.
- scheduler-managed partition backfills instead of broad whole-DAG replay.

## Production Notes

Without asset partitioning, an updated hourly feature or canary window can trigger unrelated downstream work. The demo models the better pattern: the release DAG waits for the model, feature, and SLO assets for the same partition, then evaluates only that slice.

This is useful in interviews because it shows how asset-aware orchestration becomes operationally precise: smaller backfills, clearer lineage, less queue pressure, and fewer accidental release decisions from mixed partitions.

## References

- Airflow 3.2 release announcement: <https://airflow.apache.org/blog/airflow-3.2.0/>
- Airflow release notes: <https://airflow.apache.org/docs/apache-airflow/stable/release_notes.html>
- Airflow assets: <https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html>
