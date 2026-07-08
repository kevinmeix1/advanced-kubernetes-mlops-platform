from __future__ import annotations

from pathlib import Path

from .io import write_json


def _fits(used: dict, workload: dict, quota: dict) -> bool:
    return (
        used["cpu"] + workload["cpu"] <= quota["cpu"]
        and used["memory_gib"] + workload["memory_gib"] <= quota["memory_gib"]
        and used["gpu"] + workload.get("gpu", 0) <= quota["gpu"]
        and used["airflow_pool_slots"] + workload["airflow_pool_slots"] <= quota["airflow_pool_slots"]
    )


def _add(used: dict, workload: dict, sign: int = 1) -> None:
    used["cpu"] += sign * workload["cpu"]
    used["memory_gib"] += sign * workload["memory_gib"]
    used["gpu"] += sign * workload.get("gpu", 0)
    used["airflow_pool_slots"] += sign * workload["airflow_pool_slots"]


def simulate_queue(workloads: list[dict], quota: dict) -> dict:
    used = {"cpu": 0.0, "memory_gib": 0.0, "gpu": 0.0, "airflow_pool_slots": 0.0}
    admitted: list[dict] = []
    pending: list[dict] = []
    preempted: list[dict] = []
    for workload in sorted(workloads, key=lambda item: (item["submitted_minute"], -item["priority"])):
        if _fits(used, workload, quota):
            _add(used, workload)
            admitted.append({**workload, "status": "admitted"})
            continue
        victims = sorted(
            [item for item in admitted if item["priority"] < workload["priority"]],
            key=lambda item: (item["priority"], -item["duration_minutes"]),
        )
        evicted: list[dict] = []
        for victim in victims:
            admitted.remove(victim)
            _add(used, victim, sign=-1)
            evicted.append(victim)
            if _fits(used, workload, quota):
                break
        if _fits(used, workload, quota):
            _add(used, workload)
            admitted.append({**workload, "status": "admitted", "preempted_workloads": [item["name"] for item in evicted]})
            preempted.extend({**item, "status": "preempted_by", "preemptor": workload["name"]} for item in evicted)
        else:
            for victim in evicted:
                _add(used, victim)
                admitted.append(victim)
            pending.append({**workload, "status": "pending", "reason": "quota_or_pool_exhausted"})
    return {"admitted": admitted, "pending": pending, "preempted": preempted, "used": {key: round(value, 2) for key, value in used.items()}}


def build_queue_simulation(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    quota = {"cpu": 16.0, "memory_gib": 64.0, "gpu": 1.0, "airflow_pool_slots": 8.0}
    workloads = [
        {"name": "candidate-training-gpu", "queue": "churn-release-queue", "priority": 750, "cpu": 8.0, "memory_gib": 28.0, "gpu": 1.0, "airflow_pool_slots": 4.0, "duration_minutes": 34, "submitted_minute": 0},
        {"name": "batch-scoring-validation", "queue": "churn-release-queue", "priority": 500, "cpu": 4.0, "memory_gib": 10.0, "gpu": 0.0, "airflow_pool_slots": 2.0, "duration_minutes": 18, "submitted_minute": 0},
        {"name": "ad-hoc-feature-notebook", "queue": "experimentation", "priority": 100, "cpu": 3.0, "memory_gib": 8.0, "gpu": 0.0, "airflow_pool_slots": 1.0, "duration_minutes": 55, "submitted_minute": 1},
        {"name": "drift-monitor-backfill", "queue": "observability", "priority": 450, "cpu": 3.0, "memory_gib": 8.0, "gpu": 0.0, "airflow_pool_slots": 1.0, "duration_minutes": 22, "submitted_minute": 2},
        {"name": "emergency-rollback-validation", "queue": "churn-release-queue", "priority": 1000, "cpu": 3.0, "memory_gib": 6.0, "gpu": 0.0, "airflow_pool_slots": 2.0, "duration_minutes": 8, "submitted_minute": 5},
    ]
    simulation = simulate_queue(workloads, quota)
    critical_pending = [item for item in simulation["pending"] if item["priority"] >= 900]
    queue_pressure = round(simulation["used"]["cpu"] / quota["cpu"], 4)
    report = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "quota": quota,
        "workload_count": len(workloads),
        "admitted_count": len(simulation["admitted"]),
        "pending_count": len(simulation["pending"]),
        "preempted_count": len(simulation["preempted"]),
        "queue_pressure": queue_pressure,
        "passed": not critical_pending,
        "simulation": simulation,
        "controls": [
            "Kueue ClusterQueue nominal quota protects release-critical workloads.",
            "WorkloadPriority allows emergency rollback validation to preempt lower-priority experimentation.",
            "Airflow pool slots are modeled alongside CPU, memory, and GPU quota so the scheduler does not over-admit.",
            "Non-critical drift backfill can remain pending without blocking champion rollback validation.",
        ],
        "recommendations": [
            "Keep experimentation in a separate LocalQueue with low priority.",
            "Reserve at least two Airflow pool slots for rollback and incident validation.",
            "Alert when queue pressure exceeds 0.85 for more than one release window.",
        ],
        "references": [
            "https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/",
            "https://kueue.sigs.k8s.io/docs/concepts/workload_priority_class/",
            "https://kueue.sigs.k8s.io/docs/concepts/preemption/",
            "https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html",
            "https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/",
        ],
    }
    write_json(Path(root) / "reports" / "queue_simulation.json", report)
    return report
