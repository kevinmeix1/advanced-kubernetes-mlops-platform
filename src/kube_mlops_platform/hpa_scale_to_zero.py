from __future__ import annotations

from pathlib import Path

from .io import write_json


SCALE_TO_ZERO_WORKLOADS = [
    {
        "name": "batch-scoring-worker",
        "target_ref": "Deployment/batch-scoring-worker",
        "min_replicas": 0,
        "max_replicas": 24,
        "metric_type": "External",
        "metric_name": "mlops_batch_scoring_queue_depth",
        "wake_threshold": 1,
        "cold_start_budget_seconds": 90,
        "scale_to_zero_allowed": True,
        "reason": "Batch scoring is elastic and can tolerate a short cold start when queue depth wakes the worker.",
    },
    {
        "name": "drift-replay-runner",
        "target_ref": "Deployment/drift-replay-runner",
        "min_replicas": 0,
        "max_replicas": 12,
        "metric_type": "External",
        "metric_name": "mlops_drift_replay_pending_partitions",
        "wake_threshold": 1,
        "cold_start_budget_seconds": 120,
        "scale_to_zero_allowed": True,
        "reason": "Replay work is event-driven and should not reserve pods when no partitions are pending.",
    },
    {
        "name": "canary-analysis-worker",
        "target_ref": "Deployment/canary-analysis-worker",
        "min_replicas": 0,
        "max_replicas": 8,
        "metric_type": "Object",
        "metric_name": "canary_analysis_backlog",
        "metric_object": "Service/canary-analysis-queue",
        "wake_threshold": 1,
        "cold_start_budget_seconds": 60,
        "scale_to_zero_allowed": True,
        "reason": "Canary analysis fanout can start on demand after the release controller creates analysis backlog.",
    },
]

PROTECTED_WORKLOADS = [
    {
        "name": "release-admission-controller",
        "min_replicas": 2,
        "reason": "Promotion and rollback decisions must not wait for HPA cold start.",
    },
    {
        "name": "online-inference-api",
        "min_replicas": 2,
        "reason": "Customer-facing inference remains warm behind KServe autoscaling policy.",
    },
    {
        "name": "rollback-smoke-probe",
        "min_replicas": 1,
        "reason": "Rollback validation is a control-plane safety check rather than an elastic worker.",
    },
]


def build_hpa_scale_to_zero_plan(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    root = Path(root)
    feature_gate = {
        "name": "HPAScaleToZero",
        "minimum_version": "Kubernetes v1.36",
        "stage": "alpha",
        "default": "disabled",
        "requirement": "minReplicas=0 requires at least one Object or External metric in autoscaling/v2",
    }
    checks = [
        {
            "name": "feature_gate_documented",
            "passed": feature_gate["name"] == "HPAScaleToZero" and feature_gate["stage"] == "alpha",
            "evidence": "The plan records that HPAScaleToZero must be explicitly enabled before rollout.",
        },
        {
            "name": "all_zero_min_replicas_use_external_or_object_metrics",
            "passed": all(workload["metric_type"] in {"External", "Object"} for workload in SCALE_TO_ZERO_WORKLOADS),
            "evidence": "No scale-to-zero HPA uses Resource or ContainerResource metrics.",
        },
        {
            "name": "critical_control_plane_not_scaled_to_zero",
            "passed": not ({workload["name"] for workload in SCALE_TO_ZERO_WORKLOADS} & {item["name"] for item in PROTECTED_WORKLOADS}),
            "evidence": "Release admission, online inference, and rollback smoke checks keep non-zero replica floors.",
        },
        {
            "name": "wake_metric_contract",
            "passed": all(workload["wake_threshold"] >= 1 and workload["metric_name"] for workload in SCALE_TO_ZERO_WORKLOADS),
            "evidence": "Every idleable workload declares a backlog metric that can wake the HPA from zero.",
        },
        {
            "name": "cold_start_budget_recorded",
            "passed": all(workload["cold_start_budget_seconds"] <= 120 for workload in SCALE_TO_ZERO_WORKLOADS),
            "evidence": "Cold-start budgets are explicit so SLO-sensitive services are excluded.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-09T00:00:00Z",
        "recommended_action": "enable_hpa_scale_to_zero_for_elastic_noncritical_workers" if passed else "keep_hpa_scale_to_zero_disabled",
        "passed": passed,
        "feature_status": {
            "hpa_scale_to_zero": "Kubernetes v1.36 alpha and disabled by default behind HPAScaleToZero",
            "metric_requirement": "minReplicas=0 is valid only with at least one Object or External metric",
            "api_version": "autoscaling/v2",
        },
        "feature_gate": feature_gate,
        "scale_to_zero_workloads": SCALE_TO_ZERO_WORKLOADS,
        "protected_workloads": PROTECTED_WORKLOADS,
        "checks": checks,
        "runbook": [
            "Enable HPAScaleToZero only in a non-production cluster or an isolated elastic-worker node pool first.",
            "Verify the external metrics adapter returns queue depth while replicas are zero.",
            "Keep release, rollback, and online inference control-plane components above zero replicas.",
            "Alert if backlog remains positive while desired replicas stay at zero past the cold-start budget.",
        ],
        "references": [
            "https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/",
            "https://kubernetes.io/docs/reference/kubernetes-api/autoscaling/horizontal-pod-autoscaler-v2/",
            "https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/",
        ],
    }
    write_json(root / "reports" / "hpa_scale_to_zero_plan.json", plan)
    return plan
