# Performance Budgets

This project treats performance as a release gate, not a dashboard afterthought. The local demo writes `.local/reports/performance_budget.json` with measured values, budgets, owners, PromQL signals, and remediation actions.

## What Is Gated

- Online inference p95 and p99 latency from Prometheus histograms.
- Training wall-clock time for candidate generation.
- Airflow queue wait p95 so pool and scheduler pressure are visible.
- Model artifact size before registry promotion.
- Validation accuracy so speed optimizations do not silently lower quality.

## Kubernetes And Airflow Controls

- KEDA Prometheus triggers are used for backlog-driven scale-out.
- HPA is tied to tail-latency signals instead of averages.
- VPA is recommendation-first for serving workloads, with Kubernetes in-place resize documented for controlled emergency corrections.
- Kueue quota gates expensive jobs before Airflow fans out dynamic tasks.
- Deferrable Airflow tasks avoid occupying workers while Kubernetes jobs are waiting.

## Current References

- Kubernetes resource requests and limits: <https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/>
- Kubernetes in-place pod resize: <https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/>
- KEDA Prometheus scaler: <https://keda.sh/docs/2.20/scalers/prometheus/>
- Prometheus histogram practices: <https://prometheus.io/docs/practices/histograms/>
- Airflow deferrable tasks: <https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/deferring.html>

Run `make performance-budget` after `make demo` to regenerate only this evidence.
