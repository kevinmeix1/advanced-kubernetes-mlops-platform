# Release Admission Control

This project now writes `reports/release_admission_decision.json`, a fail-closed decision record that decides whether a model change can advance. It composes the evidence reviewers normally have to inspect manually: SLO burn, performance budget checks, Kueue and Airflow queue safety, governance approval, supply-chain provenance, and the release control plan.

The demo intentionally models a conservative production stance. A canary is admitted only when every check passes. High burn rate freezes promotion, a rollback recommendation rolls back the champion, critical queue pressure throttles release work, and missing provenance holds the change.

## Production Shape

- Airflow treats the decision as an asset and short-circuits promotion unless the action is `admit_canary`.
- Kubernetes `ValidatingAdmissionPolicy` requires an approved `mlops.dev/release-decision` annotation and a 64-character evidence hash on KServe changes.
- Argo Rollouts `AnalysisTemplate` checks Prometheus SLO burn and p95 latency before traffic moves.
- Kueue priority and Airflow pools reserve rollback capacity before lower-priority work is admitted.

## Why This Is Senior-Level

The important part is not another report. The senior signal is the control loop: every promotion decision is deterministic, evidence-backed, auditable, and safe by default. In a real cluster this pattern prevents "green dashboard, unsafe deploy" drift because the same generated evidence is consumed by Airflow, admission policy, rollout analysis, and alerting.

## Current References

- Kubernetes `ValidatingAdmissionPolicy` uses CEL for declarative admission checks: https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/
- Argo Rollouts analysis templates define rollout metrics and pass/fail conditions: https://argo-rollouts.readthedocs.io/en/stable/features/analysis/
- KServe supports canary rollout strategies for inference services: https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary
- Airflow assets model data-aware scheduling dependencies: https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/assets.html
