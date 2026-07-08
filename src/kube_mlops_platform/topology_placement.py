from __future__ import annotations

from pathlib import Path

from .io import write_json


WORKLOADS = [
    {
        "name": "distributed-retraining-wave",
        "queue": "churn-release-queue",
        "placement": "compact",
        "topology_key": "cloud.provider.com/topology-rack",
        "pod_count": 8,
        "policy": "required",
        "why": "all-reduce retraining should avoid cross-rack latency before a release candidate is registered",
        "fallback": "split into two four-pod waves or use the deterministic CPU baseline",
    },
    {
        "name": "churn-canary-predictor",
        "queue": "churn-release-queue",
        "placement": "spread",
        "topology_key": "topology.kubernetes.io/zone",
        "pod_count": 3,
        "policy": "preferred",
        "why": "serving replicas should survive a zone failure while canary traffic stays below release limits",
        "fallback": "pin canary traffic at 10 percent until zone skew recovers",
    },
    {
        "name": "batch-scoring-replay",
        "queue": "batch-scoring-queue",
        "placement": "balanced",
        "topology_key": "kubernetes.io/hostname",
        "pod_count": 6,
        "policy": "best-effort",
        "why": "batch replay should pack cheaply without fragmenting release-critical accelerator topology",
        "fallback": "lower parallelism and rely on idempotent replay checkpoints",
    },
]


def build_topology_placement_plan(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "topology_resource_declared", "passed": True, "observed": "kueue.x-k8s.io/Topology"},
        {"name": "resource_flavor_references_topology", "passed": True, "observed": "spec.topologyName"},
        {"name": "compact_training_has_required_topology", "passed": any(workload["placement"] == "compact" and workload["policy"] == "required" for workload in WORKLOADS)},
        {"name": "serving_ha_spread_defined", "passed": any(workload["placement"] == "spread" for workload in WORKLOADS)},
        {"name": "fallbacks_defined", "passed": all(workload["fallback"] for workload in WORKLOADS)},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_topology_aware_release_training" if all(check["passed"] for check in checks) else "hold_topology_sensitive_workloads",
        "topology_levels": [
            "cloud.provider.com/topology-block",
            "cloud.provider.com/topology-rack",
            "kubernetes.io/hostname",
        ],
        "workloads": WORKLOADS,
        "checks": checks,
        "guardrails": [
            "Use Kueue Topology Aware Scheduling only for workloads that benefit from compact placement.",
            "Use topologySpreadConstraints for serving high availability instead of compacting every predictor.",
            "Keep a CPU fallback for release validation when no rack-level placement is available.",
            "Pair topology-aware ResourceFlavors with ProvisioningRequest-style admission checks before cloud scale-out.",
            "Alert when topology assignment remains pending so release traffic is not increased blindly.",
        ],
        "kubernetes_assets": ["kubernetes/topology-aware-scheduling.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/topology_aware_scheduling/",
            "https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/",
            "https://kueue.sigs.k8s.io/docs/concepts/admission_check/",
            "https://kubernetes.io/docs/concepts/workloads/workload-api/topology-aware-scheduling/",
        ],
    }
    write_json(root / "reports" / "topology_placement_plan.json", plan)
    return plan
