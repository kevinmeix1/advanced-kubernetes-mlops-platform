# Multi-Tenant Fairness

The demo writes `reports/tenancy_fairness_report.json`, which models how a shared MLOps platform protects release-critical work from noisy neighbors. The report covers release, batch scoring, and experimentation tenants with namespace quotas, Kueue queues, Airflow pool slots, cost labels, and isolation controls.

## Controls

- `ResourceQuota` and `LimitRange` cap tenant CPU, memory, pods, and default requests.
- Kueue `Cohort` and `ClusterQueue` resources allow controlled quota borrowing while preserving release-critical preemption.
- Airflow pools mirror the tenant queues so experimentation cannot consume release rollback slots.
- Cost-center labels support chargeback and FinOps reporting.
- Default-deny `NetworkPolicy` keeps tenants from calling each other directly.

## References

- Kubernetes multi-tenancy: https://kubernetes.io/docs/concepts/security/multi-tenancy/
- Kubernetes ResourceQuota: https://kubernetes.io/docs/concepts/policy/resource-quotas/
- Kueue Cohorts: https://kueue.sigs.k8s.io/docs/concepts/cohort/
- Airflow Pools: https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html
