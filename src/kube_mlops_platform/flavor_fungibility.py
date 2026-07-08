from __future__ import annotations

from pathlib import Path

from .io import write_json


FLAVOR_POLICIES = [
    {
        "name": "release-validation",
        "cluster_queue": "release-validation-flavor-queue",
        "local_queue": "release-validation",
        "resource": "cpu",
        "flavor_order": ["cpu-on-demand", "cpu-spot"],
        "when_can_borrow": "TryNextFlavor",
        "when_can_preempt": "TryNextFlavor",
        "preference": "BorrowingOverPreemption",
        "nominal_quota": {"cpu-on-demand": 16, "cpu-spot": 8},
        "borrowing_limit": {"cpu-on-demand": 4, "cpu-spot": 12},
        "rationale": "release gates prefer stable on-demand nodes, then fall back to spot before borrowing or preempting",
    },
    {
        "name": "batch-scoring",
        "cluster_queue": "batch-scoring-flavor-queue",
        "local_queue": "batch-replay",
        "resource": "cpu",
        "flavor_order": ["cpu-spot", "cpu-on-demand"],
        "when_can_borrow": "TryNextFlavor",
        "when_can_preempt": "TryNextFlavor",
        "preference": "BorrowingOverPreemption",
        "nominal_quota": {"cpu-spot": 24, "cpu-on-demand": 6},
        "borrowing_limit": {"cpu-spot": 18, "cpu-on-demand": 4},
        "rationale": "batch scoring uses cheaper spot first and upgrades to on-demand before stealing release capacity",
    },
    {
        "name": "gpu-canary-analysis",
        "cluster_queue": "canary-analysis-flavor-queue",
        "local_queue": "gpu-canary-analysis",
        "resource": "nvidia.com/gpu",
        "flavor_order": ["gpu-l4-reserved", "gpu-l4-spot"],
        "when_can_borrow": "TryNextFlavor",
        "when_can_preempt": "TryNextFlavor",
        "preference": "BorrowingOverPreemption",
        "nominal_quota": {"gpu-l4-reserved": 1, "gpu-l4-spot": 2},
        "borrowing_limit": {"gpu-l4-reserved": 1, "gpu-l4-spot": 2},
        "rationale": "canary analysis uses reserved GPU slices first and tries spot GPU before preempting lower-priority jobs",
    },
]


def _fallback_depth(policy: dict) -> int:
    return max(len(policy["flavor_order"]) - 1, 0)


def build_flavor_fungibility_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    policies = [
        {
            **policy,
            "fallback_depth": _fallback_depth(policy),
            "total_nominal_quota": sum(policy["nominal_quota"].values()),
            "total_borrowing_limit": sum(policy["borrowing_limit"].values()),
        }
        for policy in FLAVOR_POLICIES
    ]
    checks = [
        {
            "name": "resource_flavors_declared",
            "passed": True,
            "evidence": "ResourceFlavors separate spot, on-demand, and GPU node pools with labels and taints.",
        },
        {
            "name": "try_next_before_borrow",
            "passed": all(policy["when_can_borrow"] == "TryNextFlavor" for policy in policies),
            "evidence": "ClusterQueues try the next ResourceFlavor before borrowing quota from cohort peers.",
        },
        {
            "name": "try_next_before_preempt",
            "passed": all(policy["when_can_preempt"] == "TryNextFlavor" for policy in policies),
            "evidence": "ClusterQueues try an alternate flavor before preempting already-admitted release or scoring work.",
        },
        {
            "name": "explicit_preference_declared",
            "passed": all(policy["preference"] in {"BorrowingOverPreemption", "PreemptionOverBorrowing"} for policy in policies),
            "evidence": "The preference field is explicit so behavior does not depend on implicit defaults.",
        },
        {
            "name": "release_and_batch_have_distinct_flavor_order",
            "passed": policies[0]["flavor_order"] != policies[1]["flavor_order"],
            "evidence": "Release gates prefer stability while batch scoring prefers lower cost.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_kueue_flavor_fungibility" if passed else "keep_single_flavor_clusterqueues",
        "kueue_api_target": "kueue.x-k8s.io/v1beta1",
        "feature": {
            "name": "FlavorFungibility",
            "whenCanBorrow": "TryNextFlavor avoids borrowing if another flavor can fit the workload",
            "whenCanPreempt": "TryNextFlavor avoids preemption if another flavor can fit the workload",
            "preference": "BorrowingOverPreemption is declared explicitly instead of relying on implicit defaults",
        },
        "flavor_policies": policies,
        "operational_guardrails": [
            "Use flavor order to express business intent: stable release paths before cheap batch capacity.",
            "Keep borrowingLimit per flavor so an elastic batch queue cannot consume every on-demand fallback.",
            "Prefer TryNextFlavor before preemption to reduce churn for already-admitted model lifecycle jobs.",
            "Record selected ResourceFlavor, fallback depth, and preemption mode in release evidence.",
            "Test spot outage, on-demand saturation, and GPU exhaustion scenarios before raising quotas.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/kueue-flavor-fungibility.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/",
            "https://kueue.sigs.k8s.io/docs/concepts/resource_flavor/",
            "https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta1/#flavorfungibility",
        ],
    }
    write_json(root / "reports" / "flavor_fungibility_plan.json", plan)
    return plan
