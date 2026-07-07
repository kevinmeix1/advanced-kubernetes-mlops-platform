from __future__ import annotations

from pathlib import Path

from .io import write_json


def build_gitops_plan(root: str | Path) -> dict:
    root = Path(root)
    plan = {
        "platform": "advanced-kubernetes-mlops-platform",
        "deployment_controller": "Argo CD",
        "progressive_delivery": "Argo Rollouts canary with Prometheus analysis",
        "config_repo_pattern": "separate environment manifest repo with immutable image digests",
        "sync_waves": [
            {"wave": -3, "name": "policy-and-network-guardrails", "resources": ["ValidatingAdmissionPolicy", "NetworkPolicy", "PeerAuthentication"]},
            {"wave": -2, "name": "quota-and-autoscaling", "resources": ["ResourceQuota", "Kueue queues", "HPA", "VPA recommender"]},
            {"wave": -1, "name": "pre-sync-release-gates", "resources": ["data validation job", "policy audit job"]},
            {"wave": 0, "name": "runtime-workloads", "resources": ["KServe predictor", "Airflow release controller"]},
            {"wave": 1, "name": "post-sync-analysis", "resources": ["smoke tests", "rollout analysis", "trace validation"]},
        ],
        "promotion_stages": [
            {"environment": "dev", "sync": "automated", "self_heal": True, "approval": "pull request"},
            {"environment": "staging", "sync": "automated", "self_heal": True, "approval": "release manager approval"},
            {"environment": "prod", "sync": "manual", "self_heal": False, "approval": "change ticket plus green analysis"},
        ],
        "gates": [
            "model evaluation gates passed",
            "policy audit has no critical failures",
            "resource optimization report reviewed",
            "network topology report has no unexpected flows",
            "canary p95 latency and error-rate analysis passed",
        ],
        "rollback": {
            "command": "argocd app rollback advanced-kubernetes-mlops-platform <history-id>",
            "runtime": "argo rollouts abort churn-risk-predictor -n mlops",
            "evidence": ".local/reports/gate_report.json and .local/reports/monitoring_report.json",
        },
    }
    write_json(root / "reports" / "gitops_plan.json", plan)
    return plan
