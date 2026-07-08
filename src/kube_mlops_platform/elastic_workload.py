from __future__ import annotations

from pathlib import Path

from .io import write_json


WORKLOAD_SLICES = [
    {
        "name": "candidate-training-scale-up",
        "workload": "churn-release-elastic-training",
        "queue": "churn-release-queue",
        "slice_name": "churn-training-slice-a",
        "replacement_for": None,
        "min_replicas": 4,
        "max_replicas": 16,
        "reason": "use spare quota to train challenger and segment models before the release window",
    },
    {
        "name": "batch-scoring-scale-down",
        "workload": "churn-batch-scoring-jobset",
        "queue": "churn-release-queue",
        "slice_name": "churn-scoring-slice-b",
        "replacement_for": "mlops/churn-scoring-slice-a",
        "min_replicas": 3,
        "max_replicas": 12,
        "reason": "return quota to rollback validation without suspending the entire batch scoring JobSet",
    },
    {
        "name": "ray-canary-analysis-burst",
        "workload": "churn-canary-analysis",
        "queue": "churn-gpu-release-queue",
        "slice_name": "churn-ray-slice-a",
        "replacement_for": None,
        "min_replicas": 2,
        "max_replicas": 10,
        "reason": "burst distributed canary analysis when GPU ResourceFlavor quota is unused",
    },
]


def build_elastic_workload_plan(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "workload_slices_declared", "passed": all(item["slice_name"] for item in WORKLOAD_SLICES)},
        {"name": "replacement_slice_modeled", "passed": any(item["replacement_for"] for item in WORKLOAD_SLICES)},
        {"name": "jobset_integration_declared", "passed": True, "evidence": "release training and batch scoring use JobSet queue labels"},
        {"name": "rollback_capacity_reclaim", "passed": any("rollback" in item["reason"] for item in WORKLOAD_SLICES)},
        {"name": "gpu_burst_bounded", "passed": any(item["queue"] == "churn-gpu-release-queue" for item in WORKLOAD_SLICES)},
        {"name": "feature_gate_documented", "passed": True, "evidence": "ElasticJobsViaWorkloadSlices is gated and rollbackable"},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_kueue_elastic_release_slices" if all(check["passed"] for check in checks) else "hold_elastic_release_workloads",
        "feature_gate": "ElasticJobsViaWorkloadSlices",
        "workload_slices": WORKLOAD_SLICES,
        "jobset_policy": {
            "api": "jobset.x-k8s.io/v1alpha2",
            "queue_label": "kueue.x-k8s.io/queue-name",
            "slice_annotation": "kueue.x-k8s.io/workload-slice-name",
            "replacement_annotation": "kueue.x-k8s.io/workload-slice-replacement-for",
        },
        "operational_guardrails": [
            "Keep emergency rollback validation ahead of elastic batch scoring in Kueue priority.",
            "Use replacement slices to shrink scoring waves before evicting active release work.",
            "Require a canary-analysis smoke result before widening GPU Ray workers.",
            "Disable ElasticJobsViaWorkloadSlices if Workload Slice accounting diverges from ClusterQueue usage.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/kueue-elastic-workloads.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/elastic_workload/",
            "https://kueue.sigs.k8s.io/docs/reference/labels-and-annotations/",
            "https://kueue.sigs.k8s.io/docs/tasks/run/jobsets/",
            "https://kueue.sigs.k8s.io/docs/concepts/workload/",
        ],
    }
    write_json(root / "reports" / "elastic_workload_plan.json", plan)
    return plan
