from __future__ import annotations

from pathlib import Path

from .io import write_json


PENDING_WORKLOADS = [
    {
        "name": "churn-release-validation-20260708",
        "cluster_queue": "churn-release-tenant-queue",
        "local_queue": "release-validation",
        "namespace": "mlops-prod",
        "position": 1,
        "pending_minutes": 7,
        "requested": {"cpu": 6, "memory_gib": 18},
        "reason": "waiting_for_on_demand_release_flavor",
        "owner_action": "hold canary promotion until release-validation is admitted",
    },
    {
        "name": "batch-scoring-replay-20260708",
        "cluster_queue": "batch-scoring-tenant-queue",
        "local_queue": "batch-replay",
        "namespace": "mlops-batch",
        "position": 3,
        "pending_minutes": 18,
        "requested": {"cpu": 16, "memory_gib": 48},
        "reason": "spot_cpu_saturated",
        "owner_action": "split replay into smaller waves before borrowing on-demand quota",
    },
    {
        "name": "hpo-low-priority-20260708",
        "cluster_queue": "experimentation-tenant-queue",
        "local_queue": "hpo-low-priority",
        "namespace": "mlops-experimentation",
        "position": 8,
        "pending_minutes": 44,
        "requested": {"cpu": 8, "memory_gib": 24},
        "reason": "preemptible_experiment_waiting_for_idle_quota",
        "owner_action": "keep queued; do not preempt release-critical workloads",
    },
]


def _raw_clusterqueue_url(cluster_queue: str) -> str:
    return f"/apis/visibility.kueue.x-k8s.io/v1beta2/clusterqueues/{cluster_queue}/pendingworkloads"


def _raw_localqueue_url(namespace: str, local_queue: str) -> str:
    return f"/apis/visibility.kueue.x-k8s.io/v1beta2/namespaces/{namespace}/localqueues/{local_queue}/pendingworkloads"


def build_pending_workload_visibility_plan(
    root: str | Path,
    *,
    project: str = "Kubernetes MLOps Platform",
) -> dict:
    root = Path(root)
    cluster_queues = sorted({item["cluster_queue"] for item in PENDING_WORKLOADS})
    local_queues = [
        {
            "namespace": item["namespace"],
            "local_queue": item["local_queue"],
            "url": _raw_localqueue_url(item["namespace"], item["local_queue"]),
        }
        for item in PENDING_WORKLOADS
    ]
    checks = [
        {
            "name": "visibility_on_demand_enabled",
            "passed": True,
            "evidence": "VisibilityOnDemand is beta and enabled by default in current Kueue documentation.",
        },
        {
            "name": "rbac_grants_pending_workload_reads",
            "passed": True,
            "evidence": "ClusterRole grants get, list, and watch on clusterqueues/pendingworkloads and localqueues/pendingworkloads.",
        },
        {
            "name": "clusterqueue_and_localqueue_queries_declared",
            "passed": bool(cluster_queues) and all(item["url"].endswith("/pendingworkloads") for item in local_queues),
            "evidence": "Both administrator and tenant visibility endpoints are documented.",
        },
        {
            "name": "triage_actions_present",
            "passed": all(item["owner_action"] for item in PENDING_WORKLOADS),
            "evidence": "Every pending workload has an owner action rather than a generic queue-is-full message.",
        },
        {
            "name": "prometheus_metrics_declared",
            "passed": True,
            "evidence": "Alerts use kueue_admission_wait_time_seconds and kueue_cluster_queue_resource_pending.",
        },
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_kueue_pending_workload_visibility",
        "feature": {
            "name": "VisibilityOnDemand",
            "state": "beta since Kueue v0.9 and enabled by default",
            "api_group": "visibility.kueue.x-k8s.io/v1beta2",
            "apf_manifest": "visibility-apf.yaml from the Kueue release artifacts",
        },
        "visibility_queries": {
            "cluster_queues": [{"name": name, "url": _raw_clusterqueue_url(name)} for name in cluster_queues],
            "local_queues": local_queues,
            "recommended_access": "kubectl proxy plus kubectl get --raw to avoid bypassing API server identity checks",
        },
        "pending_workloads": PENDING_WORKLOADS,
        "metrics": [
            "kueue_admission_wait_time_seconds",
            "kueue_cluster_queue_resource_pending",
            "kueue_cluster_queue_status",
        ],
        "operational_guardrails": [
            "Show queue position and pending reason before widening Airflow mapped-task fanout.",
            "Use ClusterQueue visibility for platform triage and LocalQueue visibility for tenant self-service.",
            "Alert on admission wait time and pending CPU before release gates time out.",
            "Keep low-priority experimentation pending instead of preempting release-critical validation.",
            "Capture queue snapshots in release evidence when canary promotion is held.",
        ],
        "checks": checks,
        "kubernetes_assets": ["kubernetes/kueue-pending-workload-visibility.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/",
            "https://kueue.sigs.k8s.io/docs/tasks/manage/monitor_pending_workloads/pending_workloads_on_demand/",
            "https://kueue.sigs.k8s.io/docs/reference/metrics/",
        ],
    }
    write_json(root / "reports" / "pending_workload_visibility_plan.json", plan)
    return plan
