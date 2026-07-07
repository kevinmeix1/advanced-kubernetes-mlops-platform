from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .io import read_json, write_json


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_optional_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return read_json(path)


def _sha256(path: Path) -> dict:
    if not path.exists() or not path.is_file():
        return {"path": str(path), "exists": False, "sha256": None}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": str(path), "exists": True, "sha256": digest}


def build_governance_bundle(root: str | Path) -> dict:
    root = Path(root)
    model = _read_optional_json(root / "registry" / "churn-risk" / "champion" / "model.json", {})
    metadata = _read_optional_json(root / "registry" / "churn-risk" / "champion" / "metadata.json", {})
    metrics = _read_optional_json(root / "reports" / "metrics.json", {})
    gates = _read_optional_json(root / "reports" / "gate_report.json", {"passed": False, "checks": []})
    validation = _read_optional_json(root / "reports" / "data_validation.json", {"passed": False})
    monitoring = _read_optional_json(root / "reports" / "monitoring_report.json", {})

    artifact_paths = [
        root / "data" / "training.csv",
        root / "reports" / "data_validation.json",
        root / "reports" / "metrics.json",
        root / "reports" / "gate_report.json",
        root / "reports" / "monitoring_report.json",
        root / "registry" / "churn-risk" / "champion" / "model.json",
        root / "deployments" / "kserve_state.json",
    ]
    reproducibility_manifest = {
        "generated_at": _utc_iso(),
        "platform": "advanced-kubernetes-mlops-platform",
        "model_name": metadata.get("model_name", model.get("name", "churn-risk")),
        "model_version": metadata.get("version", model.get("version", "unknown")),
        "artifact_hashes": [_sha256(path) for path in artifact_paths],
        "environment": {
            "python": ">=3.9",
            "orchestrator": "Airflow DAG with KubernetesPodOperator and asset gates",
            "registry": "MLflow-style registry with champion alias semantics",
            "serving": "KServe InferenceService metadata and local health state",
        },
    }

    model_card = {
        "name": metadata.get("model_name", model.get("name", "churn-risk")),
        "version": metadata.get("version", model.get("version", "unknown")),
        "intended_use": "Prioritize churn-retention outreach for customer success operations.",
        "out_of_scope_use": "Do not use as the sole basis for credit, employment, or eligibility decisions.",
        "features": model.get("feature_names", []),
        "training_rows": model.get("training_rows"),
        "metrics": metrics.get("validation", metadata.get("metrics", {})),
        "segment_performance": metrics.get("test", {}).get("segment_accuracy", {}),
        "limitations": [
            "Synthetic portfolio dataset used for repeatable local review.",
            "Segment gap gate is a proxy fairness check, not a legal fairness determination.",
            "Monitoring must be connected to production traffic before automatic promotion.",
        ],
    }

    data_card = {
        "dataset": "synthetic_churn_training",
        "owner": "ml-platform",
        "source": "deterministic generator in src/kube_mlops_platform/data.py",
        "validation_passed": validation.get("passed", False),
        "row_count": validation.get("row_count"),
        "schema_contract": "contracts/churn_training_contract.yml",
        "sensitive_data": "No direct PII in the synthetic demo dataset.",
        "retention": "Keep raw training snapshots and split manifests for 90 days in the local demo; map to object lifecycle policy in cloud.",
    }

    risk_register = [
        {
            "risk": "weak model promoted to production",
            "impact": "bad retention prioritization and noisy customer outreach",
            "control": "automated quality, calibration, segment-gap, and latency gates",
            "evidence": "reports/gate_report.json",
            "status": "controlled" if gates.get("passed") else "blocked",
        },
        {
            "risk": "training-serving skew",
            "impact": "online predictions disagree with evaluated model behavior",
            "control": "feature contract plus KServe deployment state tied to champion version",
            "evidence": "contracts/churn_training_contract.yml",
            "status": "controlled",
        },
        {
            "risk": "unnoticed post-deployment drift",
            "impact": "model quality decays without release owners noticing",
            "control": "monitoring report records feature drift, prediction drift, latency, and error rate",
            "evidence": "reports/monitoring_report.json",
            "status": "controlled" if monitoring else "needs_runtime_data",
        },
    ]

    approval_record = {
        "approval_id": f"churn-risk-{metadata.get('version', model.get('version', 'unknown'))}",
        "decision": "approved_for_champion" if gates.get("passed") else "blocked",
        "generated_at": _utc_iso(),
        "approvers": ["ml-platform-owner", "data-quality-owner"],
        "required_evidence": [
            "data validation passed",
            "evaluation gates passed",
            "registry champion metadata exists",
            "monitoring report available",
            "reproducibility hashes captured",
        ],
        "gate_summary": gates,
    }

    bundle = {
        "platform": "advanced-kubernetes-mlops-platform",
        "framework_alignment": {
            "nist_ai_rmf": ["Govern", "Map", "Measure", "Manage"],
            "mlflow_registry": "use model versions, tags, and aliases rather than implicit stage-only promotion",
            "model_transparency": "model card plus dataset datasheet style evidence",
        },
        "release": {
            "model_name": model_card["name"],
            "model_version": model_card["version"],
            "decision": approval_record["decision"],
        },
        "evidence_files": {
            "model_card": "governance/model_card.json",
            "data_card": "governance/data_card.json",
            "risk_register": "governance/risk_register.json",
            "approval_record": "governance/approval_record.json",
            "reproducibility_manifest": "governance/reproducibility_manifest.json",
        },
    }

    write_json(root / "governance" / "model_card.json", model_card)
    write_json(root / "governance" / "data_card.json", data_card)
    write_json(root / "governance" / "risk_register.json", risk_register)
    write_json(root / "governance" / "approval_record.json", approval_record)
    write_json(root / "governance" / "reproducibility_manifest.json", reproducibility_manifest)
    write_json(root / "reports" / "governance_evidence_bundle.json", bundle)
    return bundle
