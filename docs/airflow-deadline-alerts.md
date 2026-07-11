# Airflow Deadline Alerts

`make deadline-alerts-plan` writes `.local/reports/deadline_alert_plan.json`.

## What It Shows

- Airflow 3-style Deadline Alert policies for release queue time, candidate registration, canary readiness, and rollback execution.
- A migration stance away from legacy Airflow 2 SLA callbacks.
- `AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT=300` so notification callbacks cannot hang release recovery.
- Explicit callback contracts with dedupe keys, bounded payload fields, owners, and allowed side effects.
- Candidate-registration remediation for Metaflow training pods, MLflow artifact logging, and evaluation gates.
- Canary and rollback remediation for KServe readiness, Gateway route acceptance, SLO burn, and champion restore actions.

## Callback Contract

Every Deadline Alert callback is treated as a small integration contract. The generated plan records the receiver, owner, dedupe key, retry policy, payload fields, and allowed side effect. The callback may notify, page, open or update an incident, or request a guarded Airflow task. It must not directly mutate MLflow aliases, KServe routes, Kubernetes quota, or release state.

## Production Notes

Release DAGs need time-bound alerts at the places where operational risk changes: scheduler queueing, model registration, serving readiness, and rollback. Deadline Alerts make those thresholds explicit and route each miss to a concrete recovery path.
