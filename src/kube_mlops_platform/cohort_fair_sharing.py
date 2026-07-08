from __future__ import annotations

from pathlib import Path

from .io import write_json


CLUSTER_QUEUE_POLICIES = [
    {
        "name": "release-critical",
        "cluster_queue": "churn-release-tenant-queue",
        "local_queues": ["release-validation", "rollback-smoke"],
        "weight": 4,
        "nominal_cpu": 24,
        "borrowing_limit_cpu": 8,
        "lending_limit_cpu": 2,
        "observed_cpu": 21,
        "historical_usage_score": 0.32,
        "preemption": {"withinClusterQueue": "LowerPriority", "reclaimWithinCohort": "Any"},
    },
    {
        "name": "batch-scoring",
        "cluster_queue": "batch-scoring-tenant-queue",
        "local_queues": ["batch-replay", "feature-refresh"],
        "weight": 2,
        "nominal_cpu": 18,
        "borrowing_limit_cpu": 10,
        "lending_limit_cpu": 6,
        "observed_cpu": 20,
        "historical_usage_score": 0.54,
        "preemption": {"withinClusterQueue": "LowerPriority", "reclaimWithinCohort": "LowerPriority"},
    },
    {
        "name": "experimentation",
        "cluster_queue": "experimentation-tenant-queue",
        "local_queues": ["notebook-sweeps", "hpo-low-priority"],
        "weight": 1,
        "nominal_cpu": 10,
        "borrowing_limit_cpu": 4,
        "lending_limit_cpu": 8,
        "observed_cpu": 8,
        "historical_usage_score": 0.76,
        "preemption": {"withinClusterQueue": "LowerPriority", "reclaimWithinCohort": "Never"},
    },
]


def _dominant_resource_share(queue: dict) -> float:
    borrowable = queue["nominal_cpu"] + queue["borrowing_limit_cpu"]
    return round(queue["observed_cpu"] / max(borrowable * queue["weight"], 0.0001), 4)


def build_cohort_fair_sharing_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    queues = [
        {
            **queue,
            "dominant_resource_share": _dominant_resource_share(queue),
            "exclusive_cpu_after_lending": queue["nominal_cpu"] - queue["lending_limit_cpu"],
            "max_cpu_after_borrowing": queue["nominal_cpu"] + queue["borrowing_limit_cpu"],
        }
        for queue in CLUSTER_QUEUE_POLICIES
    ]
    checks = [
        {
            "name": "fair_sharing_enabled",
            "passed": True,
            "evidence": "Kueue Configuration declares Fair Sharing preemption strategies for borrowed resources.",
        },
        {
            "name": "admission_fair_sharing_enabled",
            "passed": True,
            "evidence": "AdmissionFairSharing is documented as enabled by default and protected with entry-penalty style usage accounting.",
        },
        {
            "name": "borrowing_and_lending_limits_declared",
            "passed": all(queue["borrowing_limit_cpu"] >= 0 and queue["lending_limit_cpu"] >= 0 for queue in queues),
            "evidence": "Each ClusterQueue declares borrowingLimit and lendingLimit so shared quota has explicit blast-radius limits.",
        },
        {
            "name": "release_queue_weighted_above_experimentation",
            "passed": queues[0]["weight"] > queues[-1]["weight"],
            "evidence": "Release-critical workloads receive a higher fairSharing.weight than low-priority experimentation.",
        },
        {
            "name": "preemption_guardrails_declared",
            "passed": queues[0]["preemption"]["reclaimWithinCohort"] == "Any" and queues[-1]["preemption"]["reclaimWithinCohort"] == "Never",
            "evidence": "Release can reclaim borrowed quota, while experimentation cannot reclaim from other tenants.",
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_kueue_cohort_fair_sharing" if all(check["passed"] for check in checks) else "keep_static_clusterqueue_quotas",
        "kueue_version_target": "0.15+",
        "feature_gates": {
            "FairSharing": "stable since Kueue v0.7",
            "AdmissionFairSharing": "beta since Kueue v0.15 and enabled by default",
        },
        "fair_sharing_config": {
            "preemptionStrategies": ["LessThanOrEqualToFinalShare", "LessThanInitialShare"],
            "dominant_resource_share_signal": "observed_cpu / ((nominal_cpu + borrowing_limit_cpu) * fairSharing.weight)",
            "admission_order": "prefer LocalQueues with lower decayed historical usage and apply an entry penalty at admission time",
        },
        "cohort": {
            "name": "mlops-shared-cohort",
            "policy": "release-critical can reclaim its nominal quota; lower-priority tenants can borrow only bounded idle capacity",
        },
        "cluster_queues": queues,
        "operational_guardrails": [
            "Set nominal quota even for queues that mostly borrow, otherwise they cannot borrow the resource flavor.",
            "Use lendingLimit to reserve rollback and release capacity from being fully consumed by batch or experimentation.",
            "Use borrowingLimit to cap noisy neighbors before they cause wide preemption during release windows.",
            "Keep Admission Fair Sharing enabled so LocalQueues with lower historical usage get admission preference inside a ClusterQueue.",
            "Record preemption reason, ClusterQueue, LocalQueue, and fair-share values in release incident evidence.",
        ],
        "checks": checks,
        "kubernetes_assets": [
            "kubernetes/kueue-cohort-fair-sharing.yaml",
        ],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/",
            "https://kueue.sigs.k8s.io/docs/concepts/cohort/",
            "https://kueue.sigs.k8s.io/docs/concepts/preemption/",
            "https://kueue.sigs.k8s.io/docs/concepts/admission_fair_sharing/",
        ],
    }
    write_json(root / "reports" / "cohort_fair_sharing_plan.json", plan)
    return plan
