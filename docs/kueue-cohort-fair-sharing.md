# Kueue Cohort Fair Sharing

`make cohort-fair-sharing` writes `.local/reports/cohort_fair_sharing_plan.json` and pairs it with `kubernetes/kueue-cohort-fair-sharing.yaml`.

## What It Shows

- Kueue Fair Sharing with `preemptionStrategies` for borrowed resources inside a cohort.
- Admission Fair Sharing so `LocalQueue` admission considers decayed historical usage and entry penalties.
- `borrowingLimit` and `lendingLimit` per `ClusterQueue` to cap noisy-neighbor blast radius.
- `fairSharing.weight` differences between release-critical, batch-scoring, and experimentation tenants.
- Preemption policy separation between `withinClusterQueue` and `reclaimWithinCohort`.

## Production Notes

Static quotas are not enough once ML workloads share capacity. Release validation, rollback smoke tests, batch replay, and experimentation all compete for the same CPU and GPU flavors. Cohort borrowing keeps idle quota useful, while Fair Sharing and lending limits prevent low-priority tenants from turning that flexibility into release risk.

Admission Fair Sharing is different from cohort-level Fair Sharing: it orders competing `LocalQueue` work inside a `ClusterQueue` based on historical usage. Keep both visible in review evidence so a senior reviewer can explain queue fairness across tenants and within a tenant.

## References

- Kueue ClusterQueue: <https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/>
- Kueue Cohort: <https://kueue.sigs.k8s.io/docs/concepts/cohort/>
- Kueue Preemption and Fair Sharing: <https://kueue.sigs.k8s.io/docs/concepts/preemption/>
- Kueue Admission Fair Sharing: <https://kueue.sigs.k8s.io/docs/concepts/admission_fair_sharing/>
