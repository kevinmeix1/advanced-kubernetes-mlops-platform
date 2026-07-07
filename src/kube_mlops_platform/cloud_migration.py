from __future__ import annotations

from pathlib import Path

from .io import write_json


def build_cloud_migration_plan(root: str | Path) -> dict:
    root = Path(root)
    plan = {
        "platform": "advanced-kubernetes-mlops-platform",
        "primary_target": "AWS EKS Auto Mode",
        "managed_service_mapping": {
            "orchestration": "Amazon MWAA or Airflow Helm chart on EKS",
            "training_compute": "EKS Auto Mode managed NodePools with Kueue admission",
            "model_registry": "MLflow on RDS PostgreSQL with S3 artifact storage",
            "serving": "KServe Standard mode on EKS with Gateway API",
            "monitoring": "Amazon Managed Service for Prometheus and Grafana",
            "artifacts": "S3 with versioning, lifecycle policy, and KMS encryption",
        },
        "migration_phases": [
            {"phase": "foundation", "tasks": ["provision EKS", "configure IRSA", "enable object storage", "install Airflow chart"]},
            {"phase": "platform", "tasks": ["install KServe", "install Kueue", "apply network policies", "connect MLflow"]},
            {"phase": "release", "tasks": ["sync GitOps overlays", "run make demo equivalent", "verify SLO and governance evidence"]},
        ],
        "portability_controls": [
            "keep Kubernetes manifests provider-neutral where possible",
            "isolate AWS-specific node pools and IAM in infra/terraform/aws",
            "use object-store URIs rather than local paths for model artifacts",
            "keep Airflow DAGs free of cloud SDK calls except provider hooks",
        ],
        "cost_controls": [
            "use Karpenter-style consolidation through EKS Auto Mode",
            "separate spot-friendly training from on-demand serving workloads",
            "apply S3 lifecycle rules to training snapshots and prediction logs",
            "right-size requests with the resource optimization report before scaling out",
        ],
    }
    write_json(root / "reports" / "cloud_migration_plan.json", plan)
    return plan
