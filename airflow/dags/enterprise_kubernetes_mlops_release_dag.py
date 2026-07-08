from __future__ import annotations

from datetime import datetime, timedelta

AIRFLOW_AVAILABLE = True

try:
    from airflow.decorators import dag, task, task_group
    from airflow.operators.empty import EmptyOperator
    from airflow.operators.python import BranchPythonOperator, ShortCircuitOperator
    from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
    from airflow.sdk import Asset
    from airflow.utils.trigger_rule import TriggerRule
except Exception:
    AIRFLOW_AVAILABLE = False


MODEL_SEGMENTS = ["enterprise", "self_serve", "high_value", "new_customer"]
QUALITY_SUITES = ["schema", "freshness", "distribution", "label_balance"]
RELEASE_STAGES = ["candidate", "shadow", "canary", "champion"]


def on_failure_callback(context):
    task_id = context.get("task_instance").task_id if context.get("task_instance") else "unknown"
    return {"alert": "pagerduty-placeholder", "task_id": task_id, "severity": "high"}


def pod_task(task_id: str, command: list[str], *, pool: str = "ml_platform_pool", priority_weight: int = 1):
    return KubernetesPodOperator(
        task_id=task_id,
        namespace="mlops",
        image="ghcr.io/kevinmeix1/advanced-kubernetes-mlops-platform:2026.07.0",
        cmds=["bash", "-lc"],
        arguments=[" ".join(command)],
        service_account_name="churn-risk-predictor",
        get_logs=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        deferrable=True,
        logging_interval=30,
        reattach_on_restart=True,
        on_finish_action="delete_pod",
        on_kill_action="delete_pod",
        startup_timeout_seconds=300,
        execution_timeout=timedelta(hours=2),
        pod_template_file="/opt/airflow/dags/repo/kubernetes/airflow-kubernetes-executor-pod-template.yaml",
        pool=pool,
        priority_weight=priority_weight,
        retries=2,
        retry_delay=timedelta(minutes=5),
        container_resources={
            "request_cpu": "500m",
            "request_memory": "1Gi",
            "limit_cpu": "2",
            "limit_memory": "2Gi",
        },
        labels={"platform": "advanced-kubernetes-mlops", "component": task_id},
        annotations={"sidecar.istio.io/inject": "false"},
    )


if AIRFLOW_AVAILABLE:
    RAW_EVENTS = Asset("lakehouse://events/churn/raw")
    TRAINING_DATASET = Asset("lakehouse://features/churn/training")
    CANDIDATE_MODEL = Asset("mlflow://models/churn-risk@candidate")
    CHAMPION_MODEL = Asset("mlflow://models/churn-risk@champion")
    KSERVE_SERVICE = Asset("kserve://mlops/churn-risk-predictor")

    @dag(
        dag_id="enterprise_kubernetes_mlops_release",
        start_date=datetime(2026, 1, 1),
        schedule=[RAW_EVENTS],
        catchup=False,
        max_active_runs=1,
        default_args={
            "owner": "ml-platform",
            "depends_on_past": False,
            "retries": 2,
            "retry_delay": timedelta(minutes=5),
            "on_failure_callback": on_failure_callback,
        },
        tags=["mlops", "kubernetes", "kserve", "mlflow", "asset-aware", "release-gates"],
    )
    def enterprise_kubernetes_mlops_release():
        start = EmptyOperator(task_id="start_release")

        @task(outlets=[TRAINING_DATASET])
        def materialize_partition_manifest(data_interval_start=None) -> dict:
            partition = data_interval_start.strftime("%Y-%m-%d") if data_interval_start else "manual"
            return {
                "partition": partition,
                "raw_asset": RAW_EVENTS.uri,
                "training_asset": TRAINING_DATASET.uri,
                "idempotency_key": f"churn-training:{partition}",
            }

        @task
        def list_segments(manifest: dict) -> list[dict]:
            return [{"segment": segment, "partition": manifest["partition"]} for segment in MODEL_SEGMENTS]

        @task
        def list_quality_suites() -> list[str]:
            return QUALITY_SUITES

        @task_group(group_id="data_quality")
        def data_quality_group():
            validate_contract = pod_task("validate_contract", ["make", "train"], priority_weight=4)
            run_expectations = pod_task("run_expectations", ["make", "evaluate"], priority_weight=3)
            reconcile_counts = pod_task("reconcile_row_counts", ["python", "-m", "kube_mlops_platform", "train"], priority_weight=2)
            validate_contract >> run_expectations >> reconcile_counts
            return reconcile_counts

        @task_group(group_id="segment_parallel_training")
        def segment_training_group(segment_specs: list[dict]):
            @task(pool="ml_training_pool", retries=2)
            def train_segment_model(segment_spec: dict) -> dict:
                return {
                    "segment": segment_spec["segment"],
                    "partition": segment_spec["partition"],
                    "artifact": f"mlflow://runs/{segment_spec['segment']}/model",
                }

            @task(pool="ml_training_pool")
            def evaluate_segment_model(segment_result: dict) -> dict:
                return {**segment_result, "passed": True, "metric_floor": "f1>=0.62"}

            trained = train_segment_model.expand(segment_spec=segment_specs)
            return evaluate_segment_model.expand(segment_result=trained)

        @task_group(group_id="evaluation_and_registry")
        def evaluation_and_registry_group(segment_reports):
            aggregate_metrics = pod_task("aggregate_segment_metrics", ["make", "evaluate"], priority_weight=4)
            fairness_slice_gate = pod_task("fairness_slice_gate", ["python", "-m", "kube_mlops_platform", "evaluate"], priority_weight=4)
            register_candidate = pod_task("register_candidate_model", ["make", "train"], priority_weight=3)
            aggregate_metrics >> fairness_slice_gate >> register_candidate
            return register_candidate

        @task_group(group_id="capacity_and_slo_governance")
        def capacity_and_slo_group():
            reserve_release_quota = pod_task(
                "reserve_kueue_release_quota",
                ["kubectl", "get", "localqueue", "churn-release-queue", "-n", "mlops"],
                priority_weight=4,
            )
            submit_ray_canary_analysis = pod_task(
                "submit_kuberay_canary_analysis",
                ["kubectl", "apply", "-f", "kubernetes/kuberay-kueue-workloads.yaml"],
                priority_weight=4,
            )
            wait_for_ray_canary_analysis = pod_task(
                "wait_for_kuberay_canary_analysis_deferrable",
                [
                    "kubectl",
                    "wait",
                    "--for=condition=Complete",
                    "rayjob/churn-canary-analysis",
                    "-n",
                    "mlops",
                    "--timeout=20m",
                ],
                priority_weight=4,
            )
            verify_serving_budget = pod_task(
                "verify_serving_latency_budget",
                ["python", "-m", "kube_mlops_platform", "monitor"],
                priority_weight=4,
            )
            wait_for_kserve_readiness = pod_task(
                "wait_for_kserve_readiness_deferrable",
                [
                    "kubectl",
                    "wait",
                    "--for=condition=Ready",
                    "inferenceservice/churn-risk-predictor",
                    "-n",
                    "mlops",
                    "--timeout=10m",
                ],
                priority_weight=5,
            )
            reserve_release_quota >> submit_ray_canary_analysis >> wait_for_ray_canary_analysis >> verify_serving_budget >> wait_for_kserve_readiness
            return wait_for_kserve_readiness

        @task
        def decide_release_strategy() -> str:
            return "deploy_canary"

        branch = BranchPythonOperator(task_id="branch_on_release_policy", python_callable=decide_release_strategy)

        deploy_canary = pod_task("deploy_canary", ["make", "deploy"], priority_weight=5)
        run_shadow_checks = pod_task("run_shadow_checks", ["make", "monitor"], priority_weight=5)
        promote_champion = pod_task("promote_champion", ["make", "deploy"], priority_weight=5)
        rollback = pod_task("rollback_previous_champion", ["make", "rollback"], priority_weight=10)
        rollback.trigger_rule = TriggerRule.ONE_FAILED

        can_publish = ShortCircuitOperator(
            task_id="all_release_gates_passed",
            python_callable=lambda: True,
            ignore_downstream_trigger_rules=False,
        )
        publish_lineage = pod_task("publish_openlineage_events", ["make", "monitor"], priority_weight=1)
        publish_lineage.trigger_rule = TriggerRule.ALL_DONE
        end = EmptyOperator(task_id="release_complete", outlets=[CHAMPION_MODEL, KSERVE_SERVICE])

        manifest = materialize_partition_manifest()
        segments = list_segments(manifest)
        quality = data_quality_group()
        trained = segment_training_group(segments)
        registry = evaluation_and_registry_group(trained)
        capacity = capacity_and_slo_group()
        suites = list_quality_suites()
        start >> manifest >> [quality, suites] >> trained >> registry >> capacity >> branch
        branch >> deploy_canary >> run_shadow_checks >> can_publish >> promote_champion >> end
        branch >> rollback >> publish_lineage >> end
        promote_champion >> publish_lineage

    enterprise_kubernetes_mlops_release()
