# KServe Canary Readiness

`make kserve-canary-readiness` writes `reports/kserve_canary_readiness_plan.json`.
The report models the first cluster milestone without claiming a live
reconciliation: render the champion-to-canary `InferenceService`, validate it
with Kubernetes server-side dry run, and gate promotion with Argo analysis
metrics.

The release controller uses Server-Side Apply with a dedicated field manager so
Kubernetes managed fields can detect ownership conflicts. The dry-run step asks
the API server to run admission, defaulting, and validation before anything is
persisted. After that, Argo analysis checks canary error rate and p95 latency
before Airflow advances traffic.

Run:

```bash
make demo
make kserve-canary-readiness
```

In a real cluster, the apply sequence is intentionally two-step:

```bash
kubectl apply --server-side --dry-run=server \
  --field-manager=mlops-release-controller \
  -f kserve/canary-inferenceservice.yaml
kubectl apply --server-side \
  --field-manager=mlops-release-controller \
  -f kserve/canary-inferenceservice.yaml
```
