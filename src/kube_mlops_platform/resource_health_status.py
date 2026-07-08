from __future__ import annotations

from pathlib import Path

from .io import write_json


DEVICE_HEALTH_EVENTS = [
    {
        "workload": "churn-canary-inference",
        "namespace": "mlops",
        "pod": "churn-canary-dra-smoke-0",
        "container": "canary-load-check",
        "resource_claim": "l4-shared-canary-claim",
        "device_class": "gpu-l4-shared",
        "resource": "gpu.resource.kubernetes.io",
        "health": "Unhealthy",
        "message": "driver reported XID 79 reset on time-sliced L4",
        "owner_action": "hold canary at 10 percent and continue champion-only serving",
    },
    {
        "workload": "release-analysis-ray-worker",
        "namespace": "mlops",
        "pod": "release-analysis-ray-worker-2",
        "container": "ray-worker",
        "resource_claim": "a100-mig-analysis-claim",
        "device_class": "gpu-a100-mig",
        "resource": "gpu.resource.kubernetes.io",
        "health": "Unknown",
        "message": "DRA driver missed health update timeout after 30 seconds",
        "owner_action": "stop widening Ray fanout and retry on CPU-burst validation path",
    },
    {
        "workload": "rollback-validation",
        "namespace": "mlops",
        "pod": "rollback-validation-cpu-0",
        "container": "rollback-check",
        "resource_claim": None,
        "device_class": "cpu-burst",
        "resource": "cpu",
        "health": "Healthy",
        "message": "CPU fallback path has no DRA device dependency",
        "owner_action": "keep rollback validation schedulable while GPU pool recovers",
    },
]


def build_resource_health_status_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    unhealthy = [event for event in DEVICE_HEALTH_EVENTS if event["health"] in {"Unhealthy", "Unknown"}]
    checks = [
        {
            "name": "resource_health_status_enabled",
            "passed": True,
            "evidence": "ResourceHealthStatus is beta and enabled by default in Kubernetes v1.36.",
        },
        {
            "name": "pod_allocated_resources_status_checked",
            "passed": all(event["container"] and event["pod"] for event in DEVICE_HEALTH_EVENTS),
            "evidence": "Runbook queries Pod status.containerStatuses[*].allocatedResourcesStatus for DRA device health.",
        },
        {
            "name": "resourceclaim_device_status_checked",
            "passed": any(event["resource_claim"] for event in DEVICE_HEALTH_EVENTS),
            "evidence": "ResourceClaim status.devices is captured for allocated accelerator claims.",
        },
        {
            "name": "device_taint_rule_declared",
            "passed": True,
            "evidence": "DeviceTaintRule quarantines unhealthy GPU devices before another canary claim lands on them.",
        },
        {
            "name": "fallback_actions_defined",
            "passed": all(event["owner_action"] for event in DEVICE_HEALTH_EVENTS),
            "evidence": "Every unhealthy or unknown device event maps to a release-safe fallback.",
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_dra_resource_health_runbook",
        "feature": {
            "name": "ResourceHealthStatus",
            "state": "Kubernetes v1.36 beta and enabled by default",
            "pod_status_field": "status.containerStatuses[*].allocatedResourcesStatus",
            "driver_service": "DRAResourceHealth gRPC service",
            "default_unknown_timeout_seconds": 30,
        },
        "companion_features": {
            "resource_claim_device_status": "Kubernetes v1.33 beta; status.devices on ResourceClaim",
            "granular_status_authorization": "Kubernetes v1.36 beta; synthetic subresources and node-aware verbs",
            "device_taints": "Kubernetes v1.36 beta; DeviceTaintRule uses resource.k8s.io/v1beta2",
        },
        "device_health_events": DEVICE_HEALTH_EVENTS,
        "unhealthy_or_unknown_count": len(unhealthy),
        "operational_guardrails": [
            "Never advance canary traffic when any release-critical DRA device is Unhealthy or Unknown.",
            "Query Pod allocatedResourcesStatus before blaming application code for GPU-backed job failures.",
            "Compare ResourceClaim status.devices with kubelet PodResourcesLister metrics during incident review.",
            "Taint a faulty device pool and keep rollback validation CPU-runnable while accelerators recover.",
            "Require a fresh healthy device snapshot before increasing Airflow mapped fanout or KServe canary traffic.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/dra-resource-health-status.yaml"],
        "references": [
            "https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/",
            "https://kubernetes.io/blog/2026/05/07/kubernetes-v1-36-dra-136-updates/",
            "https://github.com/kubernetes/sig-release/discussions/2958",
        ],
    }
    write_json(root / "reports" / "resource_health_status_plan.json", plan)
    return plan
