# Kubernetes And Airflow Robustness Layer

This repo now includes a production-shaped control plane in addition to the local demo.

## Airflow Features

- Enterprise release DAG with TaskGroups for quality, training, registry, and release.
- Dynamic task mapping across customer segments.
- Branching for canary versus rollback.
- Short-circuit gate before promotion.
- KubernetesPodOperator tasks for isolated execution.
- Deferrable KubernetesPodOperator settings so long pod waits release Airflow worker slots.
- Capacity and SLO governance TaskGroup before release branching.
- Failure callback placeholder for alert routing.
- Airflow KubernetesExecutor pod template with init container and health probes.

## Kubernetes Features

- ResourceQuota and LimitRange for namespace governance.
- Kueue ResourceFlavor, ClusterQueue, LocalQueue, and WorkloadPriorityClass for fair batch admission.
- PriorityClass for release and rollback jobs.
- Gateway API HTTPRoute example for internal inference routing.
- CronJob for retraining.
- Job for backfill.
- RBAC Role/RoleBinding.
- NetworkPolicy, PodDisruptionBudget, service account, resource limits, and pod security labels.

## Why It Matters

This separates concerns cleanly: Airflow owns orchestration and policy; Kubernetes owns workload isolation, scheduling, quota, security, and routing; KServe owns model serving.

The latest pass adds admission control rather than raw scheduling only: retraining and backfill jobs now declare a queue, priority, resource budget, and preemption policy. That is the difference between "run a job" and "operate a shared ML platform without starving other workloads."
