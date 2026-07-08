from __future__ import annotations

from pathlib import Path

from .io import write_json


REQUIRED_ATTRIBUTES = [
    "service.name",
    "deployment.environment.name",
    "k8s.namespace.name",
    "k8s.pod.name",
    "k8s.container.name",
    "airflow.dag_id",
    "airflow.task_id",
    "mlflow.run_id",
    "ml.model.name",
    "ml.model.version",
    "ml.model.stage",
    "kserve.inferenceservice.name",
    "inference.gateway.objective",
    "release.version",
    "slo.name",
]

REDACTED_ATTRIBUTES = [
    "prediction.request.features",
    "prediction.response.score",
    "http.request.body",
    "customer.id",
]


def build_semantic_telemetry_plan(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "release_trace_attributes", "passed": "airflow.dag_id" in REQUIRED_ATTRIBUTES and "release.version" in REQUIRED_ATTRIBUTES},
        {"name": "model_registry_correlation", "passed": "mlflow.run_id" in REQUIRED_ATTRIBUTES and "ml.model.version" in REQUIRED_ATTRIBUTES},
        {"name": "kserve_serving_correlation", "passed": "kserve.inferenceservice.name" in REQUIRED_ATTRIBUTES and "inference.gateway.objective" in REQUIRED_ATTRIBUTES},
        {"name": "kubernetes_resource_correlation", "passed": "k8s.pod.name" in REQUIRED_ATTRIBUTES and "k8s.container.name" in REQUIRED_ATTRIBUTES},
        {"name": "prediction_payload_redaction", "passed": "prediction.request.features" in REDACTED_ATTRIBUTES and "customer.id" in REDACTED_ATTRIBUTES},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enforce_release_telemetry_contract" if all(check["passed"] for check in checks) else "hold_release_telemetry_rollout",
        "schema": {
            "profile": "otel-kubernetes-ml-release",
            "required_attributes": REQUIRED_ATTRIBUTES,
            "redacted_attributes": REDACTED_ATTRIBUTES,
            "numeric_fields": [
                "training.duration_ms",
                "inference.latency_ms",
                "canary.traffic_percent",
                "slo.burn_rate",
            ],
        },
        "release_pivots": [
            {"pivot": "airflow_release", "attributes": ["airflow.dag_id", "airflow.task_id", "release.version"]},
            {"pivot": "registered_model", "attributes": ["mlflow.run_id", "ml.model.name", "ml.model.version", "ml.model.stage"]},
            {"pivot": "serving_runtime", "attributes": ["kserve.inferenceservice.name", "inference.gateway.objective", "k8s.pod.name"]},
            {"pivot": "slo_gate", "attributes": ["slo.name", "slo.burn_rate", "canary.traffic_percent"]},
        ],
        "checks": checks,
        "collector_policy": {
            "processor": "attributes/semantic_redaction",
            "drop_prediction_payloads_by_default": True,
            "exporter_contract": "release, model, serving, and SLO attributes stay queryable while prediction payloads and identifiers are removed",
        },
        "guardrails": [
            "Do not export feature dictionaries, prediction scores, request bodies, or customer identifiers by default.",
            "Attach MLflow run ID and model version before KServe canary routing so rollback traces are explainable.",
            "Attach Kubernetes resource attributes before batching so SLO regressions can pivot to pods and containers.",
            "Keep latency, burn-rate, and traffic percentage fields numeric for Prometheus and dashboard aggregation.",
        ],
        "kubernetes_assets": ["kubernetes/opentelemetry-collector.yaml"],
        "references": [
            "https://opentelemetry.io/docs/specs/semconv/",
            "https://opentelemetry.io/docs/specs/semconv/system/k8s-metrics/",
            "https://gateway-api-inference-extension.sigs.k8s.io/api-types/inferencepool/",
        ],
    }
    write_json(root / "reports" / "semantic_telemetry_plan.json", plan)
    return plan
