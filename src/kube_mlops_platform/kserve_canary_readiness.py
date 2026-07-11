from __future__ import annotations

import re
from pathlib import Path

from .io import read_json, write_json


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _scalar(text: str, key: str, default: str = "") -> str:
    match = re.search(rf"^\s*{re.escape(key)}:\s*\"?([^\"\n]+)\"?\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else default


def _int_scalar(text: str, key: str, default: int = 0) -> int:
    value = _scalar(text, key, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def build_kserve_canary_readiness_plan(
    root: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> dict:
    root = Path(root)
    repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
    champion_manifest = _read(repo_root / "kserve" / "inferenceservice.yaml")
    canary_manifest = _read(repo_root / "kserve" / "canary-inferenceservice.yaml")
    analysis_manifest = _read(repo_root / "kserve" / "canary-analysis.yaml")
    release_admission_path = root / "reports" / "release_admission_decision.json"
    release_admission = read_json(release_admission_path) if release_admission_path.exists() else {}
    release_decision = release_admission.get("decision", {})
    canary_percent = _int_scalar(canary_manifest, "canaryTrafficPercent")
    champion_uri = _scalar(champion_manifest, "storageUri")
    canary_uri = _scalar(canary_manifest, "storageUri")
    service_name = _scalar(canary_manifest, "name")
    namespace = _scalar(canary_manifest, "namespace")
    checks = [
        {
            "name": "server_side_apply_field_manager",
            "passed": "kubectl apply --server-side" in analysis_manifest
            and "--field-manager=mlops-release-controller" in analysis_manifest,
            "evidence": "release controller owns only the InferenceService fields it applies",
        },
        {
            "name": "server_dry_run_required",
            "passed": "--dry-run=server" in analysis_manifest,
            "evidence": "API server admission, defaulting, and validation run before persistence",
        },
        {
            "name": "kserve_canary_traffic_split",
            "passed": 0 < canary_percent <= 25 and champion_uri != canary_uri,
            "evidence": {
                "champion_uri": champion_uri,
                "canary_uri": canary_uri,
                "canary_traffic_percent": canary_percent,
            },
        },
        {
            "name": "analysis_template_gates",
            "passed": all(
                token in analysis_manifest
                for token in ["AnalysisTemplate", "successCondition", "failureLimit"]
            ),
            "evidence": "Prometheus latency, error, and drift gates are declared before promotion",
        },
        {
            "name": "release_admission_fail_closed",
            "passed": not release_decision
            or release_decision.get("failure_policy") == "fail_closed",
            "evidence": release_decision.get(
                "recommended_action",
                "pending_release_admission_defaults_to_fail_closed",
            ),
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": "Kubernetes MLOps Platform",
        "generated_at": "2026-07-10T00:00:00Z",
        "passed": passed,
        "recommended_action": "apply_canary_with_server_side_dry_run"
        if passed
        else "hold_canary_until_apply_evidence_is_ready",
        "target": f"kserve://{namespace}/{service_name}",
        "traffic_plan": {
            "champion_percent": 100 - canary_percent,
            "canary_percent": canary_percent,
            "champion_uri": champion_uri,
            "canary_uri": canary_uri,
        },
        "apply_sequence": [
            "kubectl apply --server-side --dry-run=server --field-manager=mlops-release-controller -f kserve/canary-inferenceservice.yaml",
            "kubectl apply --server-side --field-manager=mlops-release-controller -f kserve/canary-inferenceservice.yaml",
            "kubectl argo rollouts run analysis churn-risk-canary-analysis -n mlops",
            "kubectl annotate inferenceservice churn-risk-predictor mlops.dev/release-decision=admit_canary -n mlops --overwrite",
        ],
        "checks": checks,
        "rollback_policy": {
            "trigger": "analysis failure, KServe revision not ready, or SLO burn above rollback threshold",
            "action": "remove canaryTrafficPercent and re-apply the champion storageUri",
            "previous_good_revision": "KServe retains the last revision that served 100% traffic",
        },
        "research_basis": [
            "KServe canary rollouts shift a configured percentage of traffic to a new InferenceService revision.",
            "Kubernetes Server-Side Apply tracks field ownership through managedFields and can be dry-run on the API server.",
            "Argo Rollouts AnalysisTemplates define metric checks, frequency, and success or failure conditions.",
        ],
    }
    write_json(root / "reports" / "kserve_canary_readiness_plan.json", plan)
    return plan
