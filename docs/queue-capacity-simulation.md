# Queue Capacity Simulation

The local queue simulator writes `.local/reports/queue_simulation.json`. It models Kueue-style quota, workload priority, preemption, and Airflow pool slots before work is admitted.

## What It Demonstrates

- Release-critical workloads are protected by nominal ClusterQueue quota.
- Emergency rollback validation can preempt low-priority experimentation.
- Airflow pool slots are treated as a first-class capacity limit beside CPU, memory, and GPU.
- Non-critical work can remain pending without blocking rollback or release safety checks.

## Current References

- Kueue ClusterQueue borrowing and cohorts: <https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/>
- Kueue WorkloadPriorityClass: <https://kueue.sigs.k8s.io/docs/concepts/workload_priority_class/>
- Kueue preemption: <https://kueue.sigs.k8s.io/docs/concepts/preemption/>
- Airflow pools: <https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html>
- Kubernetes pod priority and preemption: <https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/>

Run `make queue-simulation` after `make demo` to regenerate only this report.
