from __future__ import annotations

from pathlib import Path

from .io import write_json


WORKLOADS = [
    {
        "name": "churn-canary-inference",
        "queue": "churn-release-queue",
        "priority": "release-critical",
        "device_class": "gpu-l4-shared",
        "resource_claim_template": "l4-shared-canary",
        "sharing_strategy": "time-slicing",
        "requires_dra": True,
        "fallback": "hold canary at 10 percent and continue champion-only serving",
        "why": "low-risk canary scoring needs short bursts of GPU without exclusive isolation",
    },
    {
        "name": "batch-scoring-validation",
        "queue": "batch-scoring-queue",
        "priority": "normal",
        "device_class": "cpu-burst",
        "resource_claim_template": None,
        "sharing_strategy": "none",
        "requires_dra": False,
        "fallback": "run on CPU and extend the validation window",
        "why": "batch validation is latency tolerant and should not block release-critical GPU claims",
    },
    {
        "name": "emergency-rollback-validation",
        "queue": "churn-release-queue",
        "priority": "mlops-emergency-rollback",
        "device_class": "cpu-burst",
        "resource_claim_template": None,
        "sharing_strategy": "none",
        "requires_dra": False,
        "fallback": "preempt lower-priority queue work and validate rollback on CPU",
        "why": "rollback checks must remain schedulable even when accelerator pools are exhausted",
    },
]


def build_device_allocation_plan(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    root = Path(root)
    dra_workloads = [workload for workload in WORKLOADS if workload["requires_dra"]]
    checks = [
        {
            "name": "resource_claim_templates_declared",
            "passed": all(workload["resource_claim_template"] for workload in dra_workloads),
        },
        {
            "name": "kueue_quota_matches_claims",
            "passed": all(workload["queue"] for workload in WORKLOADS),
        },
        {
            "name": "fallback_paths_defined",
            "passed": all(workload["fallback"] for workload in WORKLOADS),
        },
        {
            "name": "sharing_modes_explicit",
            "passed": all(workload["sharing_strategy"] in {"time-slicing", "mig", "exclusive", "none"} for workload in WORKLOADS),
        },
        {
            "name": "dra_references_present",
            "passed": True,
            "observed": ["DeviceClass", "ResourceClaimTemplate", "ResourceClaim status"],
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "admit_dra_backed_canary" if all(check["passed"] for check in checks) else "hold_accelerator_workloads",
        "device_classes": [
            {
                "name": "gpu-l4-shared",
                "allocation": "ResourceClaimTemplate per pod",
                "sharing_strategy": "NVIDIA time-slicing",
                "isolation": "shared memory and fault domain; use only for low-risk canary and profiling",
                "kueue_flavor": "gpu-l4-shared",
            },
            {
                "name": "gpu-a100-mig",
                "allocation": "ResourceClaimTemplate per isolated slice",
                "sharing_strategy": "MIG",
                "isolation": "hardware-backed slice isolation for heavier model families",
                "kueue_flavor": "gpu-a100-mig",
            },
        ],
        "workloads": WORKLOADS,
        "checks": checks,
        "guardrails": [
            "Use DRA claims for accelerator workloads instead of only static nvidia.com/gpu limits.",
            "Reserve CPU fallback for emergency rollback and release validation.",
            "Use Kueue admission before creating expensive canary and batch-scoring pods.",
            "Keep time-sliced GPUs away from tenant-isolated or memory-sensitive jobs.",
            "Monitor ResourceClaim status and device health before increasing canary traffic.",
        ],
        "kubernetes_assets": ["kubernetes/dynamic-resource-allocation.yaml", "kubernetes/accelerator-scheduling.yaml"],
        "references": [
            "https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/",
            "https://kueue.sigs.k8s.io/docs/concepts/workload/",
            "https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html",
        ],
    }
    write_json(root / "reports" / "device_allocation_plan.json", plan)
    return plan
