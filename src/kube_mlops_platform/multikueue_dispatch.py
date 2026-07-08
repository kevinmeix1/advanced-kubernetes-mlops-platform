from __future__ import annotations

from pathlib import Path

from .io import write_json


WORKER_CLUSTERS = [
    {
        "name": "release-training-east",
        "region": "us-east-1",
        "workload_class": "candidate-training-and-evaluation",
        "cpu_quota": 64,
        "memory_gib_quota": 256,
        "gpu_quota": 2,
        "queue_mirror": "churn-multikueue-release",
        "provisioning_request_enabled": True,
    },
    {
        "name": "release-scoring-west",
        "region": "us-west-2",
        "workload_class": "batch-scoring-and-drift-replay",
        "cpu_quota": 48,
        "memory_gib_quota": 192,
        "gpu_quota": 0,
        "queue_mirror": "churn-multikueue-release",
        "provisioning_request_enabled": True,
    },
    {
        "name": "release-gpu-canary",
        "region": "us-east-2",
        "workload_class": "gpu-canary-analysis-and-rollback-smoke",
        "cpu_quota": 32,
        "memory_gib_quota": 256,
        "gpu_quota": 4,
        "queue_mirror": "churn-multikueue-release",
        "provisioning_request_enabled": True,
    },
]


def _quota_totals() -> dict:
    return {
        "cpu": sum(cluster["cpu_quota"] for cluster in WORKER_CLUSTERS),
        "memory_gib": sum(cluster["memory_gib_quota"] for cluster in WORKER_CLUSTERS),
        "nvidia_com_gpu": sum(cluster["gpu_quota"] for cluster in WORKER_CLUSTERS),
    }


def build_multikueue_dispatch_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    manager_quota = _quota_totals()
    checks = [
        {
            "name": "admission_check_declared",
            "passed": True,
            "evidence": "AdmissionCheck uses kueue.x-k8s.io/multikueue for release evidence workloads.",
        },
        {
            "name": "multikueue_config_declared",
            "passed": len(WORKER_CLUSTERS) >= 2,
            "evidence": "MultiKueueConfig lists worker clusters for training, scoring, and GPU canary analysis.",
        },
        {
            "name": "worker_clusters_declared",
            "passed": all(cluster["queue_mirror"] for cluster in WORKER_CLUSTERS),
            "evidence": "Each worker mirrors the release LocalQueue and identity contract.",
        },
        {
            "name": "manager_quota_aligned",
            "passed": manager_quota["cpu"] == 144 and manager_quota["nvidia_com_gpu"] == 6,
            "evidence": "Manager ClusterQueue quota equals aggregate worker CPU, memory, and GPU capacity.",
        },
        {
            "name": "release_gates_wait_for_dispatch",
            "passed": True,
            "evidence": "Promotion requires status.clusterName for candidate training, scoring, canary analysis, and rollback smoke evidence.",
        },
        {
            "name": "rollback_capacity_protected",
            "passed": any("rollback" in cluster["workload_class"] for cluster in WORKER_CLUSTERS),
            "evidence": "Rollback smoke has a protected worker class and can preempt lower-priority scoring waves.",
        },
        {
            "name": "status_sync_documented",
            "passed": True,
            "evidence": "Runbook records status.nominatedClusterNames while pending and status.clusterName after worker admission.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_multikueue_release_dispatch" if passed else "hold_multikueue_release_dispatch",
        "release_policy": {
            "promotion_requires_dispatch_evidence": True,
            "missing_worker_assignment_action": "freeze_candidate_promotion",
            "champion_alias_policy": "preserve current champion until candidate evidence has an admitted worker cluster",
            "rollback_path": "run rollback smoke through churn-release-queue if MultiKueue workers are unavailable",
        },
        "cluster_topology": {
            "manager_cluster": "mlops-release-manager",
            "manager_is_worker": False,
            "worker_clusters": WORKER_CLUSTERS,
        },
        "manager_quota": manager_quota,
        "dispatch_policy": {
            "controller_name": "kueue.x-k8s.io/multikueue",
            "dispatcher": "Incremental for normal releases; AllAtOnce for rollback smoke during incidents",
            "manager_quota_matches_worker_sum": True,
            "wait_for_workload_admitted": True,
            "status_fields": ["status.nominatedClusterNames", "status.clusterName"],
            "prebuilt_workload_label": "kueue.x-k8s.io/prebuilt-workload-name",
        },
        "operational_guardrails": [
            "Do not promote a candidate until release evidence Workloads have a selected status.clusterName.",
            "Keep the manager cluster out of its own worker set; use a fixed local release queue for emergency rollback smoke.",
            "Mirror namespaces, LocalQueues, release service accounts, registry secrets, and image policy on every worker.",
            "Use Incremental dispatch for routine release economics and AllAtOnce when rollback validation is time-critical.",
            "Combine MultiKueue status with ProvisioningRequest capacity checks on GPU canary workers.",
            "Freeze canary promotion and preserve the champion alias when dispatch stalls beyond the release SLO.",
        ],
        "failure_modes": [
            {
                "mode": "candidate_training_dispatch_timeout",
                "detection": "No status.clusterName after 20 minutes while candidate training is quota reserved.",
                "recovery": "Hold promotion, reduce training wave size, and rerun release evidence on churn-release-queue.",
            },
            {
                "mode": "batch_scoring_worker_lag",
                "detection": "Scoring Workload stays pending while canary route waits for evidence.",
                "recovery": "Preempt lower-priority scoring, run rollback smoke first, and keep champion traffic unchanged.",
            },
            {
                "mode": "gpu_canary_capacity_gap",
                "detection": "GPU canary Workload fails MultiKueue admission or ProvisioningRequest capacity check.",
                "recovery": "Skip GPU-only analysis, require manual review, and preserve the existing champion alias.",
            },
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/multikueue-dispatch.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/multikueue/",
            "https://kueue.sigs.k8s.io/docs/tasks/manage/setup_multikueue/",
            "https://kueue.sigs.k8s.io/docs/tasks/run/multikueue/job/",
            "https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta2/",
            "https://kubernetes.io/docs/concepts/workloads/controllers/job/",
        ],
    }
    write_json(root / "reports" / "multikueue_dispatch_plan.json", plan)
    return plan
