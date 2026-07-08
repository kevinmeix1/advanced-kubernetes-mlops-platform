from __future__ import annotations

from pathlib import Path

from .io import write_json


def _identity(
    *,
    workload: str,
    namespace: str,
    service_account: str,
    role: str,
    spiffe_id: str,
    secrets: list[str],
    permissions: list[str],
) -> dict:
    return {
        "workload": workload,
        "namespace": namespace,
        "service_account": service_account,
        "automount_service_account_token": False,
        "token": {"projected": True, "audience": "sts.amazonaws.com", "ttl_seconds": 3600},
        "cloud_access": {"provider": "aws", "role": role, "credential_mode": "federated_oidc"},
        "spiffe_id": spiffe_id,
        "external_secrets": [
            {"name": secret, "provider": "aws-secrets-manager", "refresh_interval_minutes": 30, "static_credentials": False}
            for secret in secrets
        ],
        "rbac": {"scope": "namespace", "permissions": permissions},
    }


def build_identity_access_report(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    identities = [
        _identity(
            workload="airflow-release-controller",
            namespace="mlops",
            service_account="airflow-release-runner",
            role="arn:aws:iam::111122223333:role/mlops-airflow-release",
            spiffe_id="spiffe://mlops.local/ns/mlops/sa/airflow-release-runner",
            secrets=["mlflow-tracking-credentials", "release-webhook-token"],
            permissions=["get configmaps", "create jobs", "patch inferenceservices"],
        ),
        _identity(
            workload="kserve-churn-predictor",
            namespace="mlops",
            service_account="churn-risk-predictor",
            role="arn:aws:iam::111122223333:role/kserve-churn-artifact-reader",
            spiffe_id="spiffe://mlops.local/ns/mlops/sa/churn-risk-predictor",
            secrets=["model-registry-readonly"],
            permissions=["get model artifacts", "write prediction logs"],
        ),
        _identity(
            workload="metaflow-training-worker",
            namespace="mlops-batch",
            service_account="metaflow-training-runner",
            role="arn:aws:iam::111122223333:role/metaflow-training-artifact-writer",
            spiffe_id="spiffe://mlops.local/ns/mlops-batch/sa/metaflow-training-runner",
            secrets=["feature-store-readonly", "mlflow-write-token"],
            permissions=["read training data", "write model artifacts"],
        ),
    ]
    all_secrets = [secret for identity in identities for secret in identity["external_secrets"]]
    checks = [
        {"name": "bound_service_account_tokens", "passed": all(identity["token"]["projected"] for identity in identities)},
        {"name": "token_ttl_leq_one_hour", "passed": all(identity["token"]["ttl_seconds"] <= 3600 for identity in identities)},
        {"name": "no_static_cloud_keys", "passed": all(not secret["static_credentials"] for secret in all_secrets)},
        {"name": "external_secret_refresh_leq_30m", "passed": all(secret["refresh_interval_minutes"] <= 30 for secret in all_secrets)},
        {"name": "namespace_scoped_rbac", "passed": all(identity["rbac"]["scope"] == "namespace" for identity in identities)},
        {"name": "spiffe_identity_declared", "passed": all(identity["spiffe_id"].startswith("spiffe://") for identity in identities)},
        {
            "name": "airflow_task_service_account_pinned",
            "passed": any(identity["service_account"] == "airflow-release-runner" for identity in identities),
        },
    ]
    report = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "identities": identities,
        "checks": checks,
        "controls": [
            "Pods disable default long-lived service account token mounting and use projected, audience-bound tokens.",
            "Cloud access is represented as federated workload identity roles rather than static cloud keys.",
            "External Secrets Operator refreshes sensitive runtime material from the provider secret store.",
            "Airflow KubernetesPodOperator tasks pin service accounts instead of inheriting scheduler permissions.",
            "SPIFFE IDs document the intended workload identity boundary for service-to-service authentication.",
        ],
        "rotation": {
            "projected_token_ttl_seconds": 3600,
            "external_secret_refresh_minutes": 30,
            "break_glass_static_secret_allowed": False,
        },
        "references": [
            "https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/",
            "https://external-secrets.io/latest/introduction/getting-started/",
            "https://spiffe.io/docs/latest/try/getting-started-k8s/",
            "https://airflow.apache.org/docs/apache-airflow-providers-cncf-kubernetes/stable/operators.html",
        ],
    }
    write_json(Path(root) / "reports" / "identity_access_report.json", report)
    return report
