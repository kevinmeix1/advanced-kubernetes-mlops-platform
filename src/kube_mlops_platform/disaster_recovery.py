from __future__ import annotations

from pathlib import Path

from .io import write_json


def build_disaster_recovery_plan(root: str | Path) -> dict:
    root = Path(root)
    plan = {
        "platform": "advanced-kubernetes-mlops-platform",
        "rpo_minutes": 30,
        "rto_minutes": 90,
        "backup_policy": {
            "cluster_objects": "Velero namespace backup every 30 minutes",
            "persistent_volumes": "CSI VolumeSnapshot with Retain deletion policy",
            "airflow_metadata": "Postgres logical dump before schema-changing maintenance",
            "mlflow_registry": "database dump plus artifact bucket versioning",
        },
        "restore_sequence": [
            {"order": 1, "asset": "namespace and CRDs", "validation": "kubectl get namespace mlops"},
            {"order": 2, "asset": "network, policy, and quota guardrails", "validation": "policy audit passes"},
            {"order": 3, "asset": "Airflow metadata database", "validation": "scheduler starts with expected DAG runs"},
            {"order": 4, "asset": "MLflow registry and artifacts", "validation": "champion model metadata resolves"},
            {"order": 5, "asset": "KServe runtime", "validation": "health endpoint reports Ready"},
        ],
        "drills": [
            "restore into mlops-restore namespace monthly",
            "run make demo after restore to validate model, registry, serving, and monitoring path",
            "compare restored champion version against pre-backup release evidence",
        ],
    }
    write_json(root / "reports" / "disaster_recovery_plan.json", plan)
    return plan
