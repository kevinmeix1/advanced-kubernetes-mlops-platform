# MLflow Registry Recovery Runbook

## Trigger

Use this runbook when a candidate is registered but aliases are inconsistent,
the champion cannot be loaded, a promotion partially fails, or a model produces
different predictions after packaging.

## Immediate Safety

1. Stop new promotion jobs for `prod.churn-risk`.
2. Record the release operation ID, source run ID, application version, registry
   version, artifact digest, gate digest, and current aliases.
3. Keep serving the last verified KServe revision. Do not infer deployment state
   from an intended MLflow alias alone.
4. If the active model is unsafe, point `champion` at the verified
   `previous_champion`, then run a loaded-model parity smoke before changing
   traffic.

## Local Diagnosis

```bash
make mlflow-contract PYTHON=.venv-mlflow/bin/python
python3 -m json.tool .local/reports/mlflow_registry_contract.json
```

Inspect:

- `checks.registration_idempotency`
- `checks.registration_conflict_detection`
- `checks.gate_enforced_promotion`
- `checks.champion_prediction_parity`
- `checks.rollback_prediction_parity`
- `aliases`
- `inventory.versions`

## Failure Cases

### Duplicate application version

If the artifact and gate digests match, reuse the existing registry version. If
either digest differs, create a new application version; never overwrite the
evidence tags on the existing version to make the conflict disappear.

### Candidate alias exists but gates failed

Remove the `candidate` alias, retain the failed model version and evidence, and
fix the pipeline policy. A failed version remains useful for audit and incident
analysis.

### Champion load or signature fails

Restore `previous_champion`, load it by alias, run parity scoring, and keep the
failed version registered with a quarantine tag. Compare the logged signature,
model-config artifact, Python requirements, feature contract, and source run.

### Partial alias promotion

Use the persisted release operation evidence to determine the intended state.
Reconcile `champion` first, then `previous_champion`, and verify both numeric
versions before resuming release jobs. In production, serialize mutations with
a durable operation record and single active reconciler.

### Database migration failure

Do not start the new MLflow server against a partially migrated production
database. Restore the pre-migration backup or follow the version-specific MLflow
migration recovery guidance. Test migrations against a restored copy before the
next attempt.

## Recovery Evidence

Recovery is complete only when:

- the intended champion alias resolves to one immutable registry version
- its application version and evidence digests match the approved release
- loading by alias succeeds with the expected signature
- prediction parity passes
- the serving revision reports the same model identity
- the incident and release operation record contain the reconciliation result

## Production Escalation

Escalate to the ML platform owner for registry corruption, repeated migration
failure, artifact-store inconsistency, or alias drift across concurrent release
jobs. Escalate to the serving owner when MLflow state is correct but the KServe
revision or live prediction evidence does not match.
