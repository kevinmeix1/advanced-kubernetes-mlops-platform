# Architecture Notes

## Control Plane

Airflow is the scheduling control plane. The DAG in `airflow/dags/kubernetes_mlops_dag.py` models the daily lifecycle:

1. validate and train
2. evaluate gates
3. deploy to KServe when gates pass
4. build monitoring report

Metaflow owns the training flow shape. The local implementation keeps the same step boundaries so it can run without extra services, while `metaflow_flows/train_churn_flow.py` shows where artifact tracking, retries, and step-level lineage would live.

## Data Plane

The default data plane is local:

- `.local/data/training.csv`
- `.local/data/splits/train.csv`
- `.local/data/splits/validation.csv`
- `.local/data/splits/test.csv`
- `.local/data/current_scoring.csv`

In production this maps cleanly to S3, GCS, ADLS, or a lakehouse table format. The contract in `contracts/churn_training_contract.yml` is the boundary between upstream customer data and model training.

## Model Registry

The local registry mirrors MLflow concepts:

- candidate model version
- champion pointer
- previous champion pointer
- run metadata
- gate report
- metrics

Only passing candidates are copied into `registry/churn-risk/champion`. Failed candidates remain inspectable but are not deployable.

## Serving

`kserve/inferenceservice.yaml` and `kserve/canary-inferenceservice.yaml` show the Kubernetes serving target. The local serving path writes `deployments/kserve_state.json`, then predictions load the champion model and append structured records to `logs/predictions.jsonl`.

## Observability

The monitor command writes `reports/monitoring_report.json` and the HTML dashboard. It tracks:

- p50, p95, and p99 latency
- prediction throughput
- error rate
- feature drift against training means
- prediction distribution
- recent predictions
- active model version

Prometheus and Grafana scaffolding live under `monitoring/`.

