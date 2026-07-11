from __future__ import annotations

from pathlib import Path

from .io import write_json


def build_ai_workload_telemetry_plan(root: str | Path) -> dict:
    root = Path(root)
    workloads = [
        {
            "name": "churn-risk-training",
            "kind": "Indexed Job",
            "queue": "churn-release-queue",
            "asset": "s3://mlops/features/churn/daily",
            "resource_signals": ["pod.resources.requests.cpu", "pod.resources.limits.memory", "dra.resource.claim.name"],
            "otel_attributes": ["airflow.dag_id", "airflow.task_id", "ml.model.name", "ml.model.version"],
            "slo": {"latency_p95_ms": 0, "queue_wait_p95_seconds": 420, "freshness_minutes": 60},
            "remediation": "pause downstream release assets, replay failed partition, and admit only smoke validation while queue pressure burns down",
        },
        {
            "name": "churn-risk-kserve",
            "kind": "InferenceService",
            "queue": "online-serving",
            "asset": "kserve://mlops/churn-risk",
            "resource_signals": ["pod.resources.requests.cpu", "pod.resources.limits.memory", "dra.resourceclaim.status"],
            "otel_attributes": ["kserve.inferenceservice.name", "ml.model.version", "http.route", "prediction.request.id"],
            "slo": {"latency_p95_ms": 120, "queue_wait_p95_seconds": 0, "freshness_minutes": 5},
            "remediation": "freeze promotion, shift Gateway traffic to champion, and attach DRA health status to release admission evidence",
        },
        {
            "name": "airflow-release-control",
            "kind": "Airflow Asset DAG",
            "queue": "control-plane",
            "asset": "asset://release/churn-risk",
            "resource_signals": ["pod.resources.requests.cpu", "pod.resources.limits.memory", "pod.scheduling.gate"],
            "otel_attributes": ["airflow.dag_id", "airflow.run_id", "airflow.asset.uri", "release.decision"],
            "slo": {"latency_p95_ms": 0, "queue_wait_p95_seconds": 120, "freshness_minutes": 15},
            "remediation": "keep deadline-alert callbacks bounded, dedupe release alerts, and require fresh governance bundle before unpausing assets",
        },
    ]
    required_resource_fields = {
        field
        for workload in workloads
        for field in workload["resource_signals"]
    }
    required_otel_fields = {
        field
        for workload in workloads
        for field in workload["otel_attributes"]
    }
    plan = {
        "generated_at": "2026-07-11T00:00:00Z",
        "standard_alignment": {
            "kubernetes": "Kubernetes 1.34 pod-level resource and DRA visibility signals are treated as first-class release evidence.",
            "airflow": "Airflow assets connect dataset freshness, release gates, and deadline alert callbacks.",
            "opentelemetry": "Telemetry uses stable ML/service attributes and isolates experimental gen_ai-style fields behind an allow-list.",
        },
        "workloads": workloads,
        "required_resource_fields": sorted(required_resource_fields),
        "required_otel_fields": sorted(required_otel_fields),
        "checks": [
            {"name": "pod_level_resources_mapped", "passed": "pod.resources.requests.cpu" in required_resource_fields},
            {"name": "dra_health_mapped", "passed": any("dra." in field for field in required_resource_fields)},
            {"name": "asset_lineage_mapped", "passed": "airflow.asset.uri" in required_otel_fields},
            {"name": "release_remediation_declared", "passed": all(workload["remediation"] for workload in workloads)},
        ],
        "runbook": [
            "Join pod resource pressure, DRA claim health, and Airflow asset freshness before changing release state.",
            "Preserve request and run identifiers in traces, but redact customer payloads before exporting telemetry.",
            "Use this report as the evidence contract for dashboards, SLO burn alerts, and failed-run recovery guides.",
        ],
    }
    plan["passed"] = all(check["passed"] for check in plan["checks"])
    write_json(root / "reports" / "ai_workload_telemetry_plan.json", plan)
    return plan
