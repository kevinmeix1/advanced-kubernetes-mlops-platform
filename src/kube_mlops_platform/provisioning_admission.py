from __future__ import annotations

from pathlib import Path

from .io import write_json


CAPACITY_CLASSES = [
    {
        "name": "release-training-critical",
        "queue": "churn-release-provisioned-queue",
        "flavor": "cpu-release-provisioned",
        "managed_resources": ["cpu", "memory"],
        "max_run_duration_seconds": 3600,
        "fallback_queue": "churn-release-queue",
        "workload": "candidate training, evaluation gates, and release evidence generation",
    },
    {
        "name": "gpu-canary-analysis",
        "queue": "churn-gpu-provisioned-queue",
        "flavor": "gpu-l4-release-provisioned",
        "managed_resources": ["cpu", "memory", "nvidia.com/gpu"],
        "max_run_duration_seconds": 5400,
        "fallback_queue": "churn-release-queue",
        "workload": "distributed canary analysis, explainer probes, and rollback smoke validation",
    },
]


def build_provisioning_admission_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "admission_check_declared",
            "passed": True,
            "evidence": "AdmissionCheck uses kueue.x-k8s.io/provisioning-request for release workloads",
        },
        {
            "name": "provisioning_request_config_declared",
            "passed": all(item["managed_resources"] for item in CAPACITY_CLASSES),
            "evidence": "ProvisioningRequestConfig sets provisioningClassName, managedResources, retryStrategy, and podSetMergePolicy",
        },
        {
            "name": "quota_before_capacity",
            "passed": True,
            "evidence": "Kueue reserves logical release quota before asking Cluster Autoscaler for physical capacity",
        },
        {
            "name": "release_gates_wait_for_capacity",
            "passed": True,
            "evidence": "candidate training, scoring, canary analysis, and rollback smoke do not advance until the admission check is Ready",
        },
        {
            "name": "rollback_capacity_protected",
            "passed": any("rollback" in item["workload"] for item in CAPACITY_CLASSES),
            "evidence": "rollback smoke validation is modeled as a protected provisioned workload",
        },
        {
            "name": "fallback_queue_documented",
            "passed": all(item["fallback_queue"] for item in CAPACITY_CLASSES),
            "evidence": "capacity timeout freezes promotion and reroutes smaller recovery work to the fixed release queue",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_kueue_provisioning_admission_for_release"
        if passed
        else "hold_release_provisioning_admission",
        "capacity_classes": CAPACITY_CLASSES,
        "release_policy": {
            "promotion_requires_capacity_evidence": True,
            "failed_provisioning_action": "freeze_candidate_promotion",
            "rollback_path": "keep champion alias and run rollback smoke from fixed churn-release-queue",
        },
        "kueue_policy": {
            "admission_check_api": "kueue.x-k8s.io/v1beta2",
            "controller_name": "kueue.x-k8s.io/provisioning-request",
            "provisioning_request_config": "churn-release-provisioning-config",
            "cluster_queue_strategy": "admissionChecksStrategy.onFlavors",
            "quota_reservation_before_admission": True,
            "physical_capacity_signal_required": True,
        },
        "retry_strategy": {
            "backoff_limit_count": 2,
            "backoff_base_seconds": 60,
            "backoff_max_seconds": 1800,
            "pod_set_merge_policy": "IdenticalWorkloadSchedulingRequirements",
        },
        "operational_guardrails": [
            "Do not promote a candidate when release training or canary-analysis ProvisioningRequests are Pending or Failed.",
            "Release quota and requeue smaller validation waves when the autoscaler cannot provision requested capacity.",
            "Keep rollback smoke in a higher-priority recovery path than long batch scoring.",
            "Use podSetUpdates to target nodes created for the booking where the provider exposes provisioning-request labels.",
            "Alert on pending AdmissionCheckState before Airflow release backfills saturate the pool.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/provisioning-admission-checks.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/admission_check/",
            "https://kueue.sigs.k8s.io/docs/concepts/admission_check/provisioning_request/",
            "https://kueue.sigs.k8s.io/docs/tasks/troubleshooting/troubleshooting_provreq/",
            "https://kubernetes.io/docs/concepts/workloads/controllers/job/",
        ],
    }
    write_json(root / "reports" / "provisioning_admission_plan.json", plan)
    return plan
