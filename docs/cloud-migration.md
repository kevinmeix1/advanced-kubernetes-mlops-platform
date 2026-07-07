# Cloud Migration Plan

## AWS

- Store datasets and model artifacts in S3.
- Run Airflow on MWAA or self-managed EKS.
- Run training on Metaflow with AWS Batch or Kubernetes.
- Use MLflow Tracking with RDS backend and S3 artifact store.
- Deploy KServe on EKS with IRSA access to model artifacts.
- Send prediction logs to CloudWatch, Firehose, or S3.
- Scrape metrics with Amazon Managed Prometheus and Grafana.

## Databricks

- Store training tables in Delta Lake.
- Use Databricks Workflows or Airflow for orchestration.
- Use MLflow Tracking and Model Registry natively.
- Export champion model artifacts to a location KServe can read.
- Use Lakehouse Monitoring or Evidently-style reports for drift.

## Snowflake

- Keep feature and label tables in Snowflake.
- Use Snowpark or external training jobs for model building.
- Persist prediction logs and monitoring aggregates back to Snowflake.
- Use MLflow for model metadata and KServe for low-latency serving.

## Production Hardening Checklist

- Replace local files with object storage and a metadata database.
- Add real service authentication.
- Enforce feature contracts at training and serving boundaries.
- Add CI checks for data contract changes.
- Add canary rollout automation and rollback policy.
- Add alert routing to PagerDuty, Slack, or email.
- Add model card and approval workflow for high-risk domains.

