from __future__ import annotations

from datetime import datetime, timedelta

try:
    from airflow.decorators import dag, task
    from airflow.sdk import Asset
except Exception:  # Allows static import in local tests without Airflow.
    class Asset:  # type: ignore
        def __init__(self, uri: str):
            self.uri = uri

    def dag(*args, **kwargs):
        def wrapper(func):
            return func

        return wrapper

    def task(func):
        return func


DEFAULT_ARGS = {
    "owner": "ml-platform",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

TRAINING_DATA = Asset("lakehouse://ml/churn/training")
CHAMPION_MODEL = Asset("mlflow://models/churn-risk@champion")
KSERVE_SERVICE = Asset("kserve://mlops/churn-risk-predictor")


@dag(
    start_date=datetime(2026, 1, 1),
    schedule=[TRAINING_DATA],
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["mlops", "kserve", "asset-aware", "gated-release"],
)
def kubernetes_mlops_training():
    @task
    def validate_and_train():
        return {
            "command": "make train",
            "artifact": ".local/models/candidate/model.json",
            "outlet": str(CHAMPION_MODEL.uri if hasattr(CHAMPION_MODEL, "uri") else CHAMPION_MODEL),
        }

    @task
    def evaluate_gates(context):
        return {**context, "command": "make evaluate", "promotion_policy": "all_gates_must_pass"}

    @task
    def deploy_kserve(context):
        return {
            **context,
            "command": "make deploy",
            "manifest": "kserve/inferenceservice.yaml",
            "hardening_manifest": "kserve/production-hardening.yaml",
            "outlet": str(KSERVE_SERVICE.uri if hasattr(KSERVE_SERVICE, "uri") else KSERVE_SERVICE),
        }

    @task
    def monitor_model(context):
        return {**context, "command": "make monitor", "dashboard": ".local/reports/mlops_platform_dashboard.html"}

    monitor_model(deploy_kserve(evaluate_gates(validate_and_train())))


kubernetes_mlops_training()
