# Event-Driven Assets

`make event-driven-assets` writes `.local/reports/event_driven_assets_plan.json`.

## What It Shows

- Airflow 3 event-driven scheduling for raw events, candidate model registration, and KServe readiness.
- `AssetWatcher` contracts for Kafka, MLflow, and Kubernetes event sources.
- `BaseEventTrigger` compatibility so event scheduling does not create accidental infinite rescheduling loops.
- `shared_stream_key` planning so sibling watchers can share one upstream poll loop when they read from the same event source.
- conditional asset expression: `(RAW_EVENTS & CANDIDATE_MODEL) | ROLLBACK_REQUEST`.
- `AssetAlias` usage for runtime model artifact URIs after MLflow registration.
- Queued asset event inspection and deletion runbook steps for stuck release triggers.

## Production Notes

This keeps the release path reactive without making it reckless. Raw-event freshness alone should not start a canary, and a candidate model alone should not start serving. The release DAG should fire when both data and candidate model events are ready, while rollback events remain an emergency override.

Watcher lag is treated as an orchestration SLO. If Kafka, MLflow, or Kubernetes watchers fall behind, the platform should page before stale signals drive a release.

## References

- Airflow event-driven scheduling: <https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/event-scheduling.html>
- Airflow asset-aware scheduling: <https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html>
- Airflow asset definitions and AssetAlias: <https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html>
