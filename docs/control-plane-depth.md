# Advanced Control Plane Layer

This repo now includes a local release control plane in `src/kube_mlops_platform/control_plane.py`.

## Operator Workflow

- Run `make demo` to generate model, gate, deployment, and monitoring artifacts.
- Run `make plan-release` to generate `reports/release_control_plan.json`.
- Inspect the recommended action: `advance_canary`, `hold`, or `rollback`.

## What The Planner Uses

- Offline model gate status.
- Feature drift status.
- P95 latency.
- Error-budget burn rate for a 99.5 percent availability target.
- Kueue queue pressure for release jobs.
- Airflow pool name and Kueue queue identity.

## Production Signal

The planner separates model quality from platform readiness. A model can pass offline gates and still be held because the serving layer is burning error budget or because shared cluster capacity is saturated.
