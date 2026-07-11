# Runbook

## Candidate Fails Evaluation Gates

Symptoms:

- `make evaluate` returns `"promoted": false`
- `.local/reports/gate_report.json` contains one or more failed checks
- `make deploy` cannot find a champion model if no prior model was promoted

Actions:

1. Inspect `.local/reports/gate_report.json`.
2. Check whether the failure is data quality, model quality, segment performance, calibration, or latency.
3. Inspect `.local/reports/metrics.json` for train, validation, and test divergence.
4. Retrain with a new version only after the failure is understood.
5. Do not bypass gates unless an explicit emergency policy exists.

## Drift Alert

Symptoms:

- Dashboard shows a feature drift failure
- `.local/reports/monitoring_report.json` has `feature_drift.passed = false`

Actions:

1. Identify which features are flagged.
2. Compare `reference_means` and `current_means`.
3. Check whether upstream source behavior changed.
4. If the change is expected, create a retraining task.
5. If the change is unexpected, pause promotion and investigate the source.

## Rollback

Use rollback when a newly promoted champion behaves badly in serving or monitoring.

```bash
make rollback
make deploy
make health
```

The local registry keeps a `previous_champion` pointer when a second champion is
promoted. The executable MLflow contract maps that behavior to `champion` and
`previous_champion` aliases on immutable registry versions. Follow
[`mlflow-registry-recovery.md`](mlflow-registry-recovery.md) before reconciling
the KServe revision or changing live traffic.

## KServe Deployment Failure

Checks:

1. Confirm the namespace exists.
2. Confirm the `storageUri` is reachable by the model runtime.
3. Confirm the model format matches the runtime.
4. Check pod events with `kubectl describe`.
5. Check readiness status on the InferenceService.

Useful commands:

```bash
kubectl get inferenceservice -n mlops
kubectl describe inferenceservice churn-risk-predictor -n mlops
kubectl get pods -n mlops
```
