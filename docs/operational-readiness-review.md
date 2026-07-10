# Operational Readiness Review

`make demo` writes `reports/operational_readiness_review.json` as the operator-facing release packet for the Kubernetes MLOps platform.

The review aggregates release admission, SLO burn rate, AI workload telemetry, performance budgets, cost evidence, and supply-chain provenance into one deterministic decision record. It is meant to answer the reviewer question: "What evidence proves this platform is ready to promote or should be held?"

The packet is intentionally fail-closed. A missing release decision, paging-level burn rate, missing provenance, incomplete telemetry dimensions, or failed performance guardrail lowers the readiness score and returns a remediation action instead of approving the release.

Judge demo talking points:

- Promotion is based on evidence, not a static checklist.
- Airflow assets, KServe rollout state, Kubernetes resource telemetry, MLflow provenance, and rollback capacity are reviewed together.
- The JSON packet is small enough to attach to pull requests, incident timelines, or change-review records.
