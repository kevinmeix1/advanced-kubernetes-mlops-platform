# Production-Grade Refinements

This pass upgrades the project from a runnable demo into a credible platform sample.

## Kubernetes And KServe

- KServe manifests include min/max scale and target concurrency annotations.
- The predictor uses explicit CPU and memory requests and limits.
- A dedicated service account is declared with token automount disabled.
- Namespace pod-security labels require restricted workloads.
- NetworkPolicy and PodDisruptionBudget examples document the expected production guardrails.
- Prometheus scrape annotations make the serving endpoint observable by default.

## Airflow

- The DAG is asset-aware and reacts to a training data asset instead of a vague clock-only schedule.
- `max_active_runs=1` prevents overlapping deployments.
- Retries and retry delay are explicit.
- Gate evaluation is modeled as a release policy, not a best-effort report.

## Model Lifecycle

- The local registry models candidate, champion, and previous champion stages.
- Promotion requires data quality, F1, calibration, segment gap, and latency gates.
- Rollback is first-class and test-covered.

## Why This Matters

Production MLOps systems fail at boundaries: data freshness, artifact identity, model promotion, and serving rollout. This project now makes those boundaries visible and testable.
