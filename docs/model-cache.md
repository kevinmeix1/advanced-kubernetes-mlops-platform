# Release Model Cache

`make model-cache` writes `.local/reports/model_cache_plan.json` and pairs it with `kserve/local-model-cache.yaml`.

This project uses the KServe local model cache pattern as a release-gate design.
The fast lifecycle writes inspectable local metadata, while the executable
MLflow 3 contract registers immutable versions and manages aliases. The cache
plan maps those approved versions to digest-pinned modelcar OCI images and
requires enough downloaded copies before traffic can widen.

## Operating Model

- Register the candidate in MLflow metadata and publish a pinned modelcar image.
- Use `LocalModelNodeGroup` for the serving cache node group.
- Use `LocalModelNamespaceCache` in the `mlops` namespace for candidate, champion, and previous champion artifacts.
- Block canary promotion until cache status reports enough `ModelDownloaded` copies.
- Keep the previous champion cached until the rollback SLO expires.
- Preserve existing `pvc://mlflow-models/...` PVC paths for local Minikube and emergency fallback.

## Release Semantics

Cache readiness is release evidence. If the candidate modelcar is missing, uses `latest`, or cannot reach the minimum available copies, the release should freeze the candidate and keep champion traffic unchanged. That failure is operational, not a model-quality failure, so it should not contaminate model metrics.

The useful interview point is the boundary: MLflow says which model version should be served; KServe and LocalModel status prove the artifact can actually start quickly enough to serve or roll back.

## References

- KServe resource concepts: <https://kserve.github.io/website/docs/concepts/resources>
- KServe localmodel install component: <https://kserve.github.io/website/docs/install/overview>
- KServe OCI Modelcars: <https://kserve.github.io/website/docs/model-serving/storage/providers/oci>
- KServe control plane API: <https://kserve.github.io/website/docs/reference/crd-api>
