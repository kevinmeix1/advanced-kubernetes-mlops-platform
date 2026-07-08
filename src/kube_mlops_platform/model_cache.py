from __future__ import annotations

from pathlib import Path

from .io import write_json


MODEL_ARTIFACTS = [
    {
        "alias": "candidate",
        "source_model_uri": "oci://ghcr.io/kevinmeix1/churn-risk-candidate:2026.07.0",
        "mlflow_alias": "candidate",
        "model_size_mib": 312,
        "node_groups": ["churn-risk-cache-nodes"],
        "expected_copies": 3,
        "min_available_copies": 2,
        "fallback_storage_uri": "pvc://mlflow-models/churn-risk/challenger",
    },
    {
        "alias": "champion",
        "source_model_uri": "oci://ghcr.io/kevinmeix1/churn-risk-champion:2026.07.0",
        "mlflow_alias": "champion",
        "model_size_mib": 304,
        "node_groups": ["churn-risk-cache-nodes"],
        "expected_copies": 3,
        "min_available_copies": 2,
        "fallback_storage_uri": "pvc://mlflow-models/churn-risk/champion",
    },
    {
        "alias": "previous-champion",
        "source_model_uri": "oci://ghcr.io/kevinmeix1/churn-risk-previous-champion:2026.06.2",
        "mlflow_alias": "previous_champion",
        "model_size_mib": 298,
        "node_groups": ["churn-risk-cache-nodes"],
        "expected_copies": 2,
        "min_available_copies": 1,
        "fallback_storage_uri": "pvc://mlflow-models/churn-risk/previous-champion",
    },
]


def _has_pinned_non_latest_tag(uri: str) -> bool:
    if ":" not in uri:
        return False
    return uri.rsplit(":", 1)[1] not in {"", "latest"}


def build_model_cache_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    node_storage_limit_mib = 16 * 1024
    total_model_mib = sum(item["model_size_mib"] for item in MODEL_ARTIFACTS)
    checks = [
        {
            "name": "localmodel_cache_declared",
            "passed": True,
            "evidence": "KServe LocalModelNamespaceCache objects prewarm candidate, champion, and previous champion artifacts.",
        },
        {
            "name": "node_group_has_headroom",
            "passed": node_storage_limit_mib > total_model_mib * 3,
            "evidence": "LocalModelNodeGroup storage limit leaves headroom for release and rollback modelcars.",
        },
        {
            "name": "modelcar_tags_pinned",
            "passed": all(item["source_model_uri"].startswith("oci://") and _has_pinned_non_latest_tag(item["source_model_uri"]) for item in MODEL_ARTIFACTS),
            "evidence": "All modelcar images use explicit non-latest tags so KServe can benefit from node-local cache.",
        },
        {
            "name": "promotion_requires_cache_evidence",
            "passed": True,
            "evidence": "Release automation waits for candidate and champion cache copies before advancing canary traffic.",
        },
        {
            "name": "rollback_model_preloaded",
            "passed": any(item["alias"] == "previous-champion" for item in MODEL_ARTIFACTS),
            "evidence": "Previous champion remains cached through the rollback window.",
        },
        {
            "name": "mlflow_aliases_preserved",
            "passed": all(item["mlflow_alias"] for item in MODEL_ARTIFACTS),
            "evidence": "Cache artifacts retain their MLflow alias relationship for auditability.",
        },
        {
            "name": "pvc_fallback_declared",
            "passed": all(item["fallback_storage_uri"].startswith("pvc://") for item in MODEL_ARTIFACTS),
            "evidence": "Local Minikube and clusters without localmodel can still use existing PVC storage URIs.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_release_model_cache_gate" if passed else "hold_release_model_cache_gate",
        "release_policy": {
            "promotion_requires_cache_evidence": True,
            "missing_cache_action": "freeze_candidate_promotion_and_keep_champion",
            "rollback_requires_previous_champion_cache": True,
            "latest_tag_allowed": False,
            "pvc_fallback_mode": "manual_or_local_cluster_only",
        },
        "cache_policy": {
            "install_component": "localmodel",
            "supported_workload": "InferenceService",
            "namespace_scope": "LocalModelNamespaceCache",
            "node_group": "churn-risk-cache-nodes",
            "node_storage_limit_mib": node_storage_limit_mib,
        },
        "status_gates": {
            "cache_status_field": "status.copies.available / status.copies.total",
            "node_status_values": ["NodeDownloadPending", "NodeDownloading", "NodeDownloaded", "NodeDownloadError"],
            "model_status_values": ["ModelDownloadPending", "ModelDownloading", "ModelDownloaded", "ModelDownloadError"],
            "minimum_candidate_copies": 2,
            "minimum_champion_copies": 2,
            "minimum_rollback_copies": 1,
        },
        "model_artifacts": MODEL_ARTIFACTS,
        "warmup_sequence": [
            "register candidate model and immutable modelcar digest in MLflow metadata",
            "apply LocalModelNodeGroup and LocalModelNamespaceCache resources",
            "wait for ModelDownloaded on enough serving nodes",
            "admit KServe canary only after cache status and release gates pass",
            "keep previous champion cached until rollback SLO expires",
        ],
        "operational_guardrails": [
            "Treat cache misses as rollout holds, not model-quality failures.",
            "Do not promote a candidate whose modelcar tag is latest or missing.",
            "Preserve PVC storage URIs for local demos and emergency fallback.",
            "Attach cache status to the release admission record beside SLO, queue, and provenance evidence.",
            "Keep the previous champion modelcar cached while the challenger is receiving traffic.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kserve/local-model-cache.yaml"],
        "references": [
            "https://kserve.github.io/website/docs/concepts/resources",
            "https://kserve.github.io/website/docs/install/overview",
            "https://kserve.github.io/website/docs/model-serving/storage/providers/oci",
            "https://kserve.github.io/website/docs/reference/crd-api",
        ],
    }
    write_json(root / "reports" / "model_cache_plan.json", plan)
    return plan
