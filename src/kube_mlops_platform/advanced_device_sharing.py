from __future__ import annotations

from pathlib import Path

from .io import write_json


DEVICE_SHARING_POLICIES = [
    {
        "name": "release-canary-accelerator-priority",
        "workload": "churn-canary-inference",
        "primary": "gpu-a100-mig",
        "alternatives": ["gpu-l4-shared", "cpu-burst"],
        "feature": "DRAPrioritizedList",
        "owner_action": "try MIG first, fall back to shared L4, then hold GPU-dependent gates on CPU",
    },
    {
        "name": "batch-scoring-consumable-capacity",
        "workload": "nightly-batch-scoring",
        "primary": "partitionable-a100",
        "alternatives": ["8GiB-vgpu-slice", "cpu-burst"],
        "feature": "DRAConsumableCapacity",
        "owner_action": "request bounded GPU memory slices so batch scoring cannot monopolize a physical device",
    },
    {
        "name": "fabric-attached-release-analysis",
        "workload": "release-analysis-ray-worker",
        "primary": "fabric-attached-a100",
        "alternatives": ["zone-local-l4", "cpu-burst"],
        "feature": "DRADeviceBindingConditions",
        "owner_action": "wait for device preparation before binding Ray workers and abort on preparation failure",
    },
]


def build_advanced_device_sharing_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "prioritized_device_alternatives_defined",
            "passed": all(policy["alternatives"] for policy in DEVICE_SHARING_POLICIES),
            "evidence": "Each release-critical workload declares ordered accelerator fallbacks instead of a single hard GPU shape.",
        },
        {
            "name": "partitionable_device_policy_defined",
            "passed": any("partitionable" in policy["primary"] for policy in DEVICE_SHARING_POLICIES),
            "evidence": "A100 capacity is modeled as partitionable so smaller workloads can consume slices.",
        },
        {
            "name": "consumable_capacity_budgeted",
            "passed": any(policy["feature"] == "DRAConsumableCapacity" for policy in DEVICE_SHARING_POLICIES),
            "evidence": "Batch scoring uses bounded GPU memory slices rather than whole-device reservations.",
        },
        {
            "name": "device_binding_conditions_required",
            "passed": any(policy["feature"] == "DRADeviceBindingConditions" for policy in DEVICE_SHARING_POLICIES),
            "evidence": "Fabric-attached accelerators must report prepared before scheduler binding completes.",
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_dra_advanced_device_sharing_policy",
        "features": {
            "prioritized_list": {
                "state": "Kubernetes v1.36 stable",
                "feature_gate": "DRAPrioritizedList",
                "purpose": "ordered alternative device requests for graceful accelerator fallback",
            },
            "partitionable_devices": {
                "state": "Kubernetes v1.36 beta and enabled by default",
                "feature_gate": "DRAPartitionableDevices",
                "purpose": "represent physical accelerators as smaller logical devices",
            },
            "consumable_capacity": {
                "state": "feature-gated sharing primitive; validate target-cluster support before enforcement",
                "feature_gate": "DRAConsumableCapacity",
                "purpose": "allocate bounded portions such as memory or bandwidth across claims",
            },
            "device_binding_conditions": {
                "state": "Kubernetes v1.36 beta and enabled by default",
                "feature_gate": "DRADeviceBindingConditions",
                "scheduler_phase": "PreBind",
                "default_wait_seconds": 600,
            },
        },
        "policies": DEVICE_SHARING_POLICIES,
        "operational_guardrails": [
            "Use prioritized alternatives for canaries so a missing premium GPU does not silently block release recovery.",
            "Use partitionable devices for batch and analysis work before reserving whole accelerators.",
            "Keep consumable capacity opt-in until the target Kubernetes version and DRA driver both support it.",
            "Treat binding failure conditions as release blockers, not generic Airflow retries.",
            "Keep CPU fallback evidence in release-admission records so rollback remains schedulable.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/dra-advanced-device-sharing.yaml"],
        "references": [
            "https://kubernetes.io/blog/2026/05/07/kubernetes-v1-36-dra-136-updates/",
            "https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/",
            "https://kubernetes.io/blog/2025/09/18/kubernetes-v1-34-dra-consumable-capacity/",
        ],
    }
    write_json(root / "reports" / "advanced_device_sharing_plan.json", plan)
    return plan
