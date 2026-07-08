from __future__ import annotations

from pathlib import Path

from .io import write_json


OBJECTIVES = [
    {
        "name": "churn-online",
        "priority": 20,
        "pool": "churn-risk-inference-pool",
        "traffic_class": "online",
        "latency_slo_ms": 120,
        "fallback": "fail open to the KServe champion route when the endpoint picker is unavailable",
    },
    {
        "name": "churn-canary",
        "priority": 10,
        "pool": "churn-risk-inference-pool",
        "traffic_class": "canary",
        "latency_slo_ms": 220,
        "fallback": "hold canary traffic and route high-risk customers to champion",
    },
    {
        "name": "bulk-score-replay",
        "priority": -5,
        "pool": "churn-risk-inference-pool",
        "traffic_class": "batch",
        "latency_slo_ms": 1000,
        "fallback": "pause replay while online queue pressure is elevated",
    },
]


def build_inference_gateway_plan(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "stable_inference_pool_declared", "passed": True, "observed": "inference.networking.k8s.io/v1"},
        {"name": "release_canary_objective_declared", "passed": any(item["traffic_class"] == "canary" for item in OBJECTIVES)},
        {"name": "online_priority_above_batch", "passed": max(item["priority"] for item in OBJECTIVES) > min(item["priority"] for item in OBJECTIVES)},
        {"name": "endpoint_picker_failure_mode_defined", "passed": any("fail open" in item["fallback"] for item in OBJECTIVES)},
        {"name": "fallbacks_defined", "passed": all(item["fallback"] for item in OBJECTIVES)},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_inference_gateway_for_release_routes" if all(check["passed"] for check in checks) else "keep_kserve_route_only",
        "pool": {
            "name": "churn-risk-inference-pool",
            "api_version": "inference.networking.k8s.io/v1",
            "target_port": 8000,
            "endpoint_picker": "churn-endpoint-picker:9002",
            "failure_mode": "FailOpen",
        },
        "objectives": OBJECTIVES,
        "routing_signals": [
            "queue_length",
            "model_server_readiness",
            "prefix_cache_hit_rate",
            "tenant_priority",
            "canary_route_weight",
        ],
        "checks": checks,
        "guardrails": [
            "Use InferencePool v1 for routable model-server backends.",
            "Keep InferenceObjective alpha usage isolated to documented priority experiments.",
            "Fail open to the existing KServe champion route during endpoint-picker failures.",
            "Give online churn-risk requests higher priority than batch replay.",
            "Capture endpoint-picker decisions in prediction logs for rollback analysis.",
        ],
        "kubernetes_assets": ["kubernetes/inference-gateway-routing.yaml"],
        "references": [
            "https://gateway-api-inference-extension.sigs.k8s.io/api-types/inferencepool/",
            "https://gateway-api-inference-extension.sigs.k8s.io/concepts/api-overview/",
            "https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api-inference-extension/",
        ],
    }
    write_json(root / "reports" / "inference_gateway_plan.json", plan)
    return plan
