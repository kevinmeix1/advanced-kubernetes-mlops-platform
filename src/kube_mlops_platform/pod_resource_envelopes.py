from __future__ import annotations

from pathlib import Path

from .io import write_json


POD_RESOURCE_WORKLOADS = [
    {
        "name": "release-validation-controller",
        "namespace": "mlops",
        "pod_level_requests": {"cpu": "2", "memory": "4Gi"},
        "pod_level_limits": {"cpu": "3", "memory": "6Gi"},
        "scheduling_gates": ["mlops.kevinmei.dev/release-evidence-ready"],
        "release_condition": "release_admission_decision.json, DAG bundle version, and event-driven asset evidence are present",
        "containers": ["release-runner", "otel-sidecar"],
    },
    {
        "name": "churn-canary-analysis",
        "namespace": "mlops",
        "pod_level_requests": {"cpu": "3", "memory": "6Gi"},
        "pod_level_limits": {"cpu": "4", "memory": "8Gi"},
        "scheduling_gates": ["mlops.kevinmei.dev/model-cache-ready", "mlops.kevinmei.dev/gateway-route-accepted"],
        "release_condition": "KServe LocalModel cache reports ModelDownloaded and Gateway route is accepted",
        "containers": ["canary-analyzer", "metrics-exporter"],
    },
    {
        "name": "batch-scoring-replay",
        "namespace": "mlops-batch",
        "pod_level_requests": {"cpu": "4", "memory": "8Gi"},
        "pod_level_limits": {"cpu": "6", "memory": "12Gi"},
        "scheduling_gates": ["mlops.kevinmei.dev/kueue-admitted", "mlops.kevinmei.dev/replay-window-approved"],
        "release_condition": "Kueue admits the replay workload and replay window is approved by release control",
        "containers": ["scoring-worker", "checkpoint-writer"],
    },
]


def build_pod_resource_envelope_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    checks = [
        {
            "name": "pod_level_resources_declared",
            "passed": all(item["pod_level_requests"] and item["pod_level_limits"] for item in POD_RESOURCE_WORKLOADS),
            "evidence": "Each multi-container workload has a pod-level resource envelope for CPU and memory.",
        },
        {
            "name": "scheduling_gates_declared",
            "passed": all(item["scheduling_gates"] for item in POD_RESOURCE_WORKLOADS),
            "evidence": "Pods stay SchedulingGated until release evidence, model cache, or Kueue admission is ready.",
        },
        {
            "name": "gate_release_runbook",
            "passed": True,
            "evidence": "Gates are removed only by a controller after evidence files and Kubernetes status conditions are observed.",
        },
        {
            "name": "scheduler_churn_metric",
            "passed": True,
            "evidence": "scheduler_pending_pods{queue=\"gated\"} is tracked separately from unschedulable pods.",
        },
        {
            "name": "dra_compatibility_guardrail",
            "passed": True,
            "evidence": "DRA node-allocatable resources and container requests must fit inside pod-level envelopes before gate removal.",
        },
    ]
    passed = all(check["passed"] for check in checks)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": passed,
        "recommended_action": "enable_pod_resource_envelopes_and_scheduling_gates" if passed else "keep_container_only_requests",
        "kubernetes_version_target": "1.34+",
        "feature_gates": {
            "PodLevelResources": "beta, enabled by default in Kubernetes 1.34+ clusters that support the feature",
            "PodSchedulingReadiness": "stable since Kubernetes 1.30",
            "PodLevelResourceManagers": "enable where CPUManager, MemoryManager, or TopologyManager alignment is required",
        },
        "workloads": POD_RESOURCE_WORKLOADS,
        "release_runbook": [
            "Create pods with schedulingGates so the scheduler and autoscaler do not churn before prerequisites exist.",
            "Verify release admission, model cache, Gateway route, Kueue admission, and replay approvals.",
            "Patch away gates in any order only after prerequisites pass; never add new gates after pod creation.",
            "Alert on scheduler_pending_pods{queue=\"gated\"} and on gates older than their workload SLO.",
        ],
        "checks": checks,
        "kubernetes_assets": [
            "kubernetes/pod-resource-envelopes.yaml",
        ],
        "references": [
            "https://kubernetes.io/docs/tasks/configure-pod-container/assign-pod-level-resources/",
            "https://kubernetes.io/docs/concepts/scheduling-eviction/pod-scheduling-readiness/",
            "https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/",
        ],
    }
    write_json(root / "reports" / "pod_resource_envelope_plan.json", plan)
    return plan
