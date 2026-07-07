# Disaster Recovery

This project includes a disaster-recovery plan and Kubernetes backup examples for Velero, CSI snapshots, and logical Airflow metadata backup.

Run:

```bash
make dr-plan
```

The report is written to `.local/reports/disaster_recovery_plan.json`.

## Restore Order

1. Namespace and CRDs.
2. Network, policy, quota, and admission guardrails.
3. Airflow metadata database.
4. MLflow registry and artifacts.
5. KServe runtime and health checks.

## Notes

Velero backs up Kubernetes resources and can snapshot persistent volumes, but application consistency still needs hooks or logical database dumps. Kubernetes VolumeSnapshot objects depend on CSI driver support. Airflow recommends backing up the metadata database before maintenance or schema-changing work.
