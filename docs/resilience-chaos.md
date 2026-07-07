# Resilience and Chaos Drills

This project includes a local chaos-drill report plus Kubernetes manifests for Chaos Mesh. The drills are intentionally bounded: each one names a blast radius, the expected control, and the recovery objective a platform team would review after the exercise.

## Drills

- `kserve_pod_kill`: kills one predictor pod and expects the KServe readiness path plus PodDisruptionBudget design to prevent full outage.
- `mlflow_network_latency`: injects latency into the training-to-registry path and expects Airflow retries plus release gates to hold promotion.
- `release_queue_saturation`: adds CPU pressure to release jobs and expects Kueue quotas and Airflow pools to throttle work.

Run the local evidence generator:

```bash
make chaos-drill
```

Apply the Kubernetes experiments in a real dev cluster after installing Chaos Mesh:

```bash
kubectl apply -f kubernetes/chaos-experiments.yaml
```

## Production Notes

- Use schedules with `concurrencyPolicy: Forbid` so a weekly drill cannot stack on a slow previous run.
- Keep selectors narrow and namespace-scoped; chaos should target one component, not the whole platform.
- Pair each experiment with an SLO assertion: availability, p95 latency, gate decision, or queue recovery time.
- Store drill reports next to release evidence so failed drills block production promotion.

References: Chaos Mesh supports pod, network, stress, and scheduled experiments; Kubernetes PodDisruptionBudgets define voluntary disruption tolerance for workloads.
