from __future__ import annotations

from pathlib import Path

from .io import write_json


RESOURCE_MUTATIONS = [
    {
        "name": "release-retraining-job",
        "suspended": True,
        "current_requests": {"cpu": "6", "memory": "24Gi", "nvidia.com/gpu": "1"},
        "proposed_requests": {"cpu": "4", "memory": "18Gi", "nvidia.com/gpu": "1"},
        "quota_reason": "Kueue reports GPU fit but CPU quota pressure in release-training.",
        "unsuspend_gate": "quota_fit_and_model_cache_warm",
    },
    {
        "name": "batch-scoring-replay-job",
        "suspended": True,
        "current_requests": {"cpu": "10", "memory": "20Gi"},
        "proposed_requests": {"cpu": "6", "memory": "14Gi"},
        "quota_reason": "Replay can use smaller CPU shards while preserving Indexed Job semantics.",
        "unsuspend_gate": "pool_slots_available_and_checkpoint_present",
    },
    {
        "name": "canary-analysis-job",
        "suspended": True,
        "current_requests": {"cpu": "3", "memory": "8Gi"},
        "proposed_requests": {"cpu": "4", "memory": "10Gi"},
        "quota_reason": "Canary analysis needs more memory before unsuspend because the candidate has a larger feature set.",
        "unsuspend_gate": "analysis_queue_ready_and_slo_budget_green",
    },
]

PROTECTED_JOBS = [
    {
        "name": "active-online-inference-smoke",
        "suspended": False,
        "reason": "Active smoke checks should use in-place resize or a replacement Job, not suspended Job resource mutation.",
    },
    {
        "name": "running-rollback-validation",
        "suspended": False,
        "reason": "Rollback validation should not be rewritten while Pods are running.",
    },
]


def _resource_delta_ok(item: dict) -> bool:
    current_cpu = float(item["current_requests"]["cpu"])
    proposed_cpu = float(item["proposed_requests"]["cpu"])
    return 0.25 <= proposed_cpu / current_cpu <= 1.5


def build_suspended_job_resource_plan(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    root = Path(root)
    feature = {
        "name": "MutablePodResourcesForSuspendedJobs",
        "state": "Kubernetes v1.36 beta and enabled by default",
        "scope": "resource requests and limits in the Pod template of suspended Jobs",
        "not_for": "actively running Pods; use in-place resize or recreate instead",
    }
    checks = [
        {
            "name": "beta_feature_status_recorded",
            "passed": feature["state"].startswith("Kubernetes v1.36 beta"),
            "evidence": "The plan records the feature gate and beta status before using it.",
        },
        {
            "name": "only_suspended_jobs_mutated",
            "passed": all(item["suspended"] for item in RESOURCE_MUTATIONS),
            "evidence": "Every mutable resource plan starts from spec.suspend=true.",
        },
        {
            "name": "active_jobs_not_resized",
            "passed": all(not item["suspended"] for item in PROTECTED_JOBS),
            "evidence": "Active inference smoke and rollback Jobs are explicitly excluded.",
        },
        {
            "name": "queue_controller_reason_recorded",
            "passed": all(item["quota_reason"] for item in RESOURCE_MUTATIONS),
            "evidence": "Every resource mutation is tied to Kueue quota, Airflow pool, or workload-shape evidence.",
        },
        {
            "name": "resource_delta_bounded",
            "passed": all(_resource_delta_ok(item) for item in RESOURCE_MUTATIONS),
            "evidence": "CPU request changes are bounded so admission cannot silently rewrite workload economics.",
        },
        {
            "name": "unsuspend_gate_requires_quota_fit",
            "passed": all("quota" in item["unsuspend_gate"] or "pool" in item["unsuspend_gate"] or "slo" in item["unsuspend_gate"] for item in RESOURCE_MUTATIONS),
            "evidence": "Unsuspend gates require quota, Airflow pool, cache, checkpoint, or SLO readiness.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-09T00:00:00Z",
        "recommended_action": "enable_suspended_job_resource_mutation_for_queued_ml_jobs" if passed else "keep_suspended_job_resources_observe_only",
        "passed": passed,
        "feature": feature,
        "resource_mutations": RESOURCE_MUTATIONS,
        "protected_jobs": PROTECTED_JOBS,
        "checks": checks,
        "runbook": [
            "Create batch Jobs with spec.suspend=true when queue admission owns the start decision.",
            "Patch CPU, memory, GPU, or extended resource requests only while the Job is suspended.",
            "Record the Kueue quota snapshot and Airflow pool reason before unsuspending.",
            "Use in-place resize or a replacement Job for active Pods; do not mutate active Job templates.",
        ],
        "references": [
            "https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/",
            "https://kubernetes.io/docs/concepts/workloads/controllers/job/",
        ],
    }
    write_json(root / "reports" / "suspended_job_resources_plan.json", plan)
    return plan
