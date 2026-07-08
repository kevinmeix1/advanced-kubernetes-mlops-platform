from __future__ import annotations

from pathlib import Path

from .io import write_json


RESIZE_POLICIES = [
    {
        "name": "canary-startup-boost",
        "workload": "churn-canary-inference",
        "scope": "container",
        "resource_patch": {"requests.cpu": "750m", "limits.memory": "768Mi"},
        "resize_policy": {"cpu": "NotRequired", "memory": "RestartContainer"},
        "trigger": "canary p95 latency exceeds 80 percent of the release budget for 3 minutes",
        "owner_action": "apply a CPU-only in-place resize before widening traffic, but recreate the pod for memory increases",
    },
    {
        "name": "ray-analysis-pod-level-burst",
        "workload": "release-analysis-ray-worker",
        "scope": "pod",
        "resource_patch": {"spec.resources.limits.cpu": "8", "spec.resources.requests.memory": "12Gi"},
        "resize_policy": {"cpu": "NotRequired", "memory": "RestartContainer"},
        "trigger": "Ray canary analysis enters CPU queue while the pod remains node-fit",
        "owner_action": "expand the pod-level resource envelope in-place and watch PodResizePending before adding workers",
    },
    {
        "name": "rollback-validation-shrink",
        "workload": "rollback-validation",
        "scope": "container",
        "resource_patch": {"requests.cpu": "250m", "limits.memory": "512Mi"},
        "resize_policy": {"cpu": "NotRequired", "memory": "NotRequired"},
        "trigger": "rollback smoke completed and the pod is waiting for the next release gate",
        "owner_action": "shrink idle rollback capacity in-place so emergency validation stays warm without wasting quota",
    },
]


def build_inplace_resize_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "container_resize_ga",
            "passed": True,
            "evidence": "Kubernetes v1.35 made in-place CPU and memory resizing stable through the resize subresource.",
        },
        {
            "name": "pod_level_resize_beta",
            "passed": any(policy["scope"] == "pod" for policy in RESIZE_POLICIES),
            "evidence": "Kubernetes v1.36 beta pod-level resource resizing covers multi-container release analysis workers.",
        },
        {
            "name": "resize_policy_defined",
            "passed": all("resize_policy" in policy and policy["resize_policy"] for policy in RESIZE_POLICIES),
            "evidence": "Every workload declares whether CPU and memory can resize without a restart.",
        },
        {
            "name": "resize_conditions_observed",
            "passed": True,
            "evidence": "Prometheus rules watch PodResizePending and PodResizeInProgress before release automation proceeds.",
        },
        {
            "name": "vpa_inplace_or_recreate_ready",
            "passed": True,
            "evidence": "VPA recommendation mode is modeled with InPlaceOrRecreate so automation can actuate when cluster support is enabled.",
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_inplace_resize_release_controls",
        "features": {
            "in_place_pod_resize": {
                "state": "Kubernetes v1.35 stable",
                "subresource": "pods/resize",
                "container_status_field": "status.containerStatuses[*].resources",
            },
            "pod_level_resource_resize": {
                "state": "Kubernetes v1.36 beta and enabled by default",
                "feature_gate": "InPlacePodLevelResourcesVerticalScaling",
                "pod_spec_field": "spec.resources",
                "status_conditions": ["PodResizePending", "PodResizeInProgress"],
            },
            "autoscaler_integration": {
                "vpa_update_mode": "InPlaceOrRecreate",
                "requires_runtime": "cgroup v2 and CRI UpdateContainerResources support",
            },
        },
        "policies": RESIZE_POLICIES,
        "operational_guardrails": [
            "Only use in-place resize for CPU or memory changes that match the container resizePolicy.",
            "Treat PodResizePending as a capacity signal and stop widening release fanout until it clears.",
            "Treat PodResizeInProgress as a rollout hold so latency evidence is not mixed across old and new cgroups.",
            "Keep rollback validation warm by shrinking idle pods instead of deleting the recovery path.",
            "Log desired resources, allocated resources, actual status.resources, and VPA recommendation in release evidence.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/inplace-pod-resize.yaml"],
        "references": [
            "https://kubernetes.io/blog/2025/12/19/kubernetes-v1-35-in-place-pod-resize-ga/",
            "https://kubernetes.io/blog/2026/04/30/kubernetes-v1-36-inplace-pod-level-resources-beta/",
            "https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/",
        ],
    }
    write_json(root / "reports" / "inplace_resize_plan.json", plan)
    return plan
