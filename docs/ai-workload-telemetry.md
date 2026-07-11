# AI Workload Telemetry Readiness

This project now emits `reports/ai_workload_telemetry_plan.json` during `make demo`.
The report maps critical AI workloads to Kubernetes pod-level resource signals,
Dynamic Resource Allocation health, Airflow asset lineage, OpenTelemetry
attributes, SLOs, and remediation actions.

The intent is to show how a production platform would connect scheduling,
serving, lineage, and observability evidence before allowing a model release to
advance. The report is deliberately contract-shaped so CI can validate it and a
dashboard or incident workflow can consume it without scraping prose.

Current practice reflected here:
- Kubernetes 1.34 exposes richer pod resource and DRA visibility for workload-aware operations.
- Airflow asset scheduling makes data freshness and downstream dependencies explicit.
- KServe and Gateway routing evidence are treated as release-control inputs.
- OpenTelemetry fields are allow-listed so experimental AI attributes do not leak sensitive payloads.
