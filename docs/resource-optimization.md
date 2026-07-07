# Resource Optimization

This layer turns observed workload profiles into reviewable right-sizing recommendations. It is deliberately conservative: VPA is configured in recommendation-only mode, HPA uses stabilization windows, and Airflow pools remain the concurrency control for external systems.

Run:

```bash
make optimize-resources
```

The report is written to `.local/reports/resource_optimization.json`.

## Decisions

- CPU requests use p95 usage plus 35 percent headroom.
- Memory requests use p99 usage plus 20 percent headroom; limits use another 25 percent buffer.
- Latency-sensitive inference avoids CPU limits unless throttling has been tested.
- HPA scale-down uses a 300 second stabilization window to reduce flapping.
- Airflow pool slots are aligned to Kueue quota before increasing mapped task parallelism.

## References

Kubernetes requests guide scheduling and limits control enforcement. VPA is a separately installed CRD with `autoscaling.k8s.io/v1`; using `updateMode: "Off"` lets teams collect recommendations before applying changes. Airflow pools limit parallelism against scarce systems, and deferrable operators release worker capacity while waiting.
