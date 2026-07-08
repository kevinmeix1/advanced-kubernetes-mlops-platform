from __future__ import annotations

from pathlib import Path

from .io import write_json


RAY_WORKLOADS = [
    {
        "name": "churn-canary-analysis",
        "kind": "RayJob",
        "queue": "churn-release-queue",
        "priority": "release-critical",
        "min_workers": 2,
        "max_workers": 8,
        "gpus_per_worker": 0,
        "autoscaling": "elastic",
        "scheduling": "kueue_admitted_rayjob",
        "why": "fan out shadow and canary score comparison without blocking the release DAG worker",
        "fallback": "run the deterministic local canary evaluator and keep canary traffic at the previous step",
    },
    {
        "name": "segment-hpo-sweep",
        "kind": "RayJob",
        "queue": "churn-research-queue",
        "priority": "opportunistic",
        "min_workers": 0,
        "max_workers": 16,
        "gpus_per_worker": 1,
        "autoscaling": "elastic",
        "scheduling": "preemptible_queue",
        "why": "allow HPO to use idle accelerators while preserving release capacity",
        "fallback": "skip the sweep and train the baseline segment models already covered by release gates",
    },
    {
        "name": "batch-score-replay",
        "kind": "RayCluster",
        "queue": "churn-batch-queue",
        "priority": "standard",
        "min_workers": 1,
        "max_workers": 12,
        "gpus_per_worker": 0,
        "autoscaling": "elastic",
        "scheduling": "workload_slices",
        "why": "replay high-volume scoring partitions with controlled worker expansion",
        "fallback": "split replay into Airflow mapped tasks with identical idempotency keys",
    },
]


def build_kuberay_capacity_plan(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "ray_workloads_declared", "passed": len(RAY_WORKLOADS) >= 3},
        {"name": "kueue_queue_labels_required", "passed": all(workload["queue"] for workload in RAY_WORKLOADS)},
        {"name": "elastic_autoscaling_modelled", "passed": all(workload["autoscaling"] == "elastic" for workload in RAY_WORKLOADS)},
        {"name": "release_capacity_isolated", "passed": any(workload["priority"] == "release-critical" for workload in RAY_WORKLOADS)},
        {"name": "fallbacks_defined", "passed": all(workload["fallback"] for workload in RAY_WORKLOADS)},
    ]
    max_workers = sum(workload["max_workers"] for workload in RAY_WORKLOADS)
    max_gpu_demand = sum(workload["max_workers"] * workload["gpus_per_worker"] for workload in RAY_WORKLOADS)
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_kuberay_release_analysis" if all(check["passed"] for check in checks) else "keep_release_analysis_local",
        "workloads": RAY_WORKLOADS,
        "capacity": {
            "max_workers": max_workers,
            "max_gpu_demand": max_gpu_demand,
            "release_reserved_workers": 4,
            "autoscaler_idle_timeout_seconds": 90,
        },
        "checks": checks,
        "guardrails": [
            "Require Kueue admission before RayJob workers are created.",
            "Keep release-critical RayJobs in a queue that can preempt opportunistic sweeps.",
            "Use Ray autoscaling inside the admitted Kueue envelope instead of unbounded worker growth.",
            "Preserve Airflow idempotency keys when falling back from Ray to mapped KubernetesPodOperator tasks.",
            "Publish Ray dashboard, worker pending, and object store spill metrics into the release scorecard.",
        ],
        "kubernetes_assets": ["kubernetes/kuberay-kueue-workloads.yaml"],
        "references": [
            "https://kueue.sigs.k8s.io/docs/tasks/run/rayjobs/",
            "https://docs.ray.io/en/latest/cluster/kubernetes/k8s-ecosystem/kueue.html",
            "https://docs.ray.io/en/latest/cluster/kubernetes/examples/rayjob-kueue-gang-scheduling.html",
        ],
    }
    write_json(root / "reports" / "kuberay_capacity_plan.json", plan)
    return plan
