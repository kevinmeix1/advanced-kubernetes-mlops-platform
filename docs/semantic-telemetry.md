# Semantic Telemetry Contract

`make semantic-telemetry-plan` writes `.local/reports/semantic_telemetry_plan.json` and pairs the release trace with `kubernetes/opentelemetry-collector.yaml`.

## What It Shows

- Release spans with Airflow DAG, task, release version, and environment attributes.
- Training and registry spans with MLflow run ID, model name, model version, and model stage.
- KServe canary spans with `InferenceService`, gateway objective, latency, and traffic percentage.
- Kubernetes namespace, pod, and container attributes for root-cause pivots.
- Collector-side redaction of feature dictionaries, prediction scores, request bodies, and customer identifiers.

## Production Notes

The value is operational joinability. A failed canary should answer which Airflow release, MLflow run, KServe route, model version, pod, and SLO changed without custom log parsing. Prediction payloads and identifiers stay out of default telemetry exports, while numeric latency, traffic, and burn-rate fields remain queryable.
