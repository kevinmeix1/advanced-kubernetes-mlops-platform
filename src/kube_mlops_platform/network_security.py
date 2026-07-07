from __future__ import annotations

from pathlib import Path

from .io import write_json


ALLOWED_FLOWS = [
    {
        "source": "airflow-release-controller",
        "destination": "mlflow-registry",
        "port": 5000,
        "protocol": "HTTP over mesh mTLS",
        "justification": "register and promote candidate model versions",
    },
    {
        "source": "airflow-release-controller",
        "destination": "kserve-control-plane",
        "port": 443,
        "protocol": "HTTPS over mesh mTLS",
        "justification": "apply and verify inference rollout state",
    },
    {
        "source": "churn-risk-predictor",
        "destination": "otel-collector",
        "port": 4317,
        "protocol": "OTLP gRPC over mesh mTLS",
        "justification": "export prediction traces and latency metrics",
    },
]


DENIED_FLOWS = [
    {
        "source": "churn-risk-predictor",
        "destination": "mlflow-registry",
        "reason": "online serving must not mutate registry state",
    },
    {
        "source": "drift-monitor",
        "destination": "kubernetes-api",
        "reason": "monitoring jobs read generated artifacts instead of cluster secrets",
    },
]


def build_network_security_report(root: str | Path) -> dict:
    root = Path(root)
    report = {
        "platform": "advanced-kubernetes-mlops-platform",
        "namespace": "mlops",
        "default_policy": "deny all ingress and egress, then allow listed service flows",
        "mtls_mode": "STRICT",
        "gateway_boundary": "Gateway API routes stay in namespace unless explicitly allowed",
        "allowed_flow_count": len(ALLOWED_FLOWS),
        "denied_flow_count": len(DENIED_FLOWS),
        "allowed_flows": ALLOWED_FLOWS,
        "denied_by_default": DENIED_FLOWS,
        "controls": [
            "default deny NetworkPolicy for ingress and egress",
            "dedicated DNS egress allow because default deny blocks DNS",
            "Istio PeerAuthentication STRICT for namespace traffic",
            "AuthorizationPolicy restricts rollout operations to the Airflow service account",
        ],
    }
    write_json(root / "reports" / "network_security.json", report)
    return report
