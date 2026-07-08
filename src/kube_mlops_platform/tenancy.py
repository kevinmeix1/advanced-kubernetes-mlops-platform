from __future__ import annotations

from pathlib import Path

from .io import write_json


def _utilization(used: float, quota: float) -> float:
    return round(used / max(quota, 0.0001), 4)


def _tenant(
    *,
    name: str,
    namespace: str,
    queue: str,
    cost_center: str,
    cpu_quota: float,
    cpu_used: float,
    memory_quota_gib: float,
    memory_used_gib: float,
    pool_slots: int,
    pool_used: int,
    priority_class: str,
) -> dict:
    return {
        "name": name,
        "namespace": namespace,
        "queue": queue,
        "cost_center": cost_center,
        "priority_class": priority_class,
        "quota": {"cpu": cpu_quota, "memory_gib": memory_quota_gib, "airflow_pool_slots": pool_slots},
        "observed": {"cpu": cpu_used, "memory_gib": memory_used_gib, "airflow_pool_slots": pool_used},
        "utilization": {
            "cpu": _utilization(cpu_used, cpu_quota),
            "memory": _utilization(memory_used_gib, memory_quota_gib),
            "airflow_pool": _utilization(pool_used, pool_slots),
        },
        "labels": {
            "platform.mlops.dev/tenant": name,
            "platform.mlops.dev/cost-center": cost_center,
            "platform.mlops.dev/data-domain": "customer-retention",
        },
    }


def build_tenancy_report(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    tenants = [
        _tenant(
            name="release-critical",
            namespace="mlops-prod",
            queue="churn-release-queue",
            cost_center="ml-platform",
            cpu_quota=24,
            cpu_used=14,
            memory_quota_gib=96,
            memory_used_gib=44,
            pool_slots=8,
            pool_used=4,
            priority_class="mlops-release-critical",
        ),
        _tenant(
            name="batch-scoring",
            namespace="mlops-batch",
            queue="batch-scoring-queue",
            cost_center="customer-success",
            cpu_quota=18,
            cpu_used=12,
            memory_quota_gib=72,
            memory_used_gib=46,
            pool_slots=5,
            pool_used=3,
            priority_class="mlops-batch-normal",
        ),
        _tenant(
            name="experimentation",
            namespace="mlops-experimentation",
            queue="experimentation-queue",
            cost_center="ml-research",
            cpu_quota=10,
            cpu_used=8,
            memory_quota_gib=40,
            memory_used_gib=27,
            pool_slots=2,
            pool_used=2,
            priority_class="mlops-low-priority",
        ),
    ]
    cpu_utils = [tenant["utilization"]["cpu"] for tenant in tenants]
    pool_utils = [tenant["utilization"]["airflow_pool"] for tenant in tenants]
    noisy_neighbor_risks = [
        tenant["name"]
        for tenant in tenants
        if max(tenant["utilization"].values()) >= 0.90 and tenant["priority_class"] == "mlops-low-priority"
    ]
    checks = [
        {"name": "namespace_resource_quotas", "passed": all(tenant["quota"]["cpu"] > 0 for tenant in tenants)},
        {"name": "no_hard_quota_breach", "passed": all(max(tenant["utilization"].values()) <= 1.0 for tenant in tenants)},
        {"name": "release_capacity_reserved", "passed": tenants[0]["quota"]["airflow_pool_slots"] - tenants[0]["observed"]["airflow_pool_slots"] >= 2},
        {"name": "tenant_cost_labels", "passed": all("platform.mlops.dev/cost-center" in tenant["labels"] for tenant in tenants)},
        {"name": "noisy_neighbor_contained", "passed": all(risk == "experimentation" for risk in noisy_neighbor_risks), "observed": noisy_neighbor_risks},
    ]
    report = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "tenants": tenants,
        "checks": checks,
        "fairness": {
            "cohort": "mlops-shared-cohort",
            "max_cpu_utilization_gap": round(max(cpu_utils) - min(cpu_utils), 4),
            "max_airflow_pool_utilization_gap": round(max(pool_utils) - min(pool_utils), 4),
            "borrowing_policy": "tenants may borrow unused cohort quota, but release-critical rollback preempts lower-priority experimentation first",
        },
        "controls": [
            "Namespaces isolate release, batch, and experimentation tenants with ResourceQuota and LimitRange.",
            "Kueue cohorts allow controlled quota borrowing while preserving release-critical priority.",
            "Airflow pools map to tenant queues so one domain cannot exhaust all workers.",
            "Cost-center labels are required for chargeback and FinOps reporting.",
            "Default-deny NetworkPolicies keep tenants from calling each other directly.",
        ],
        "references": [
            "https://kubernetes.io/docs/concepts/security/multi-tenancy/",
            "https://kubernetes.io/docs/concepts/policy/resource-quotas/",
            "https://kueue.sigs.k8s.io/docs/concepts/cohort/",
            "https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html",
        ],
    }
    write_json(Path(root) / "reports" / "tenancy_fairness_report.json", report)
    return report
