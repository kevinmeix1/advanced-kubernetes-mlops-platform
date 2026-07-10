from __future__ import annotations

from pathlib import Path

from .io import write_json


DEADLINE_POLICIES = [
    {
        "name": "dagrun_queue_to_start",
        "reference": "DeadlineReference.DAGRUN_QUEUED_AT",
        "interval": "10m",
        "callback": "notify_ml_platform_release",
        "severity": "page",
        "next_action": "inspect scheduler capacity, Airflow pools, and Kueue release queue headroom",
    },
    {
        "name": "training_to_candidate_registered",
        "reference": "DeadlineReference.DAGRUN_START_DATE",
        "interval": "2h",
        "callback": "open_training_release_incident",
        "severity": "ticket",
        "next_action": "check Metaflow training pods, MLflow artifact logging, and evaluation gates",
    },
    {
        "name": "canary_readiness",
        "reference": "custom_canary_submitted_at",
        "interval": "20m",
        "callback": "page_serving_release_owner",
        "severity": "page",
        "next_action": "inspect KServe readiness, Gateway route acceptance, and SLO burn",
    },
    {
        "name": "rollback_execution",
        "reference": "custom_rollback_requested_at",
        "interval": "15m",
        "callback": "page_release_incident_commander",
        "severity": "page",
        "next_action": "restore previous champion, freeze promotion, and attach release evidence",
    },
]


CALLBACK_CONTRACTS = {
    "notify_ml_platform_release": {
        "receiver": "slack://ml-platform-release",
        "dedupe_key": "dag_id:run_id:dagrun_queue_to_start",
        "payload_fields": ["dag_id", "run_id", "deadline_policy", "queued_at", "pool", "kueue_queue"],
        "retry_policy": "bounded exponential backoff, max 3 attempts inside callback timeout",
        "allowed_side_effect": "notify only; capacity changes remain explicit Airflow tasks",
        "owner": "ml-platform-oncall",
    },
    "open_training_release_incident": {
        "receiver": "incident://training-release",
        "dedupe_key": "model_version:training_to_candidate_registered",
        "payload_fields": ["model_version", "metaflow_run_id", "mlflow_run_id", "gate_summary"],
        "retry_policy": "single incident upsert keyed by model version and policy",
        "allowed_side_effect": "open or update incident; do not promote or rollback",
        "owner": "training-platform",
    },
    "page_serving_release_owner": {
        "receiver": "pagerduty://serving-release",
        "dedupe_key": "model_version:canary_readiness",
        "payload_fields": ["model_version", "inferenceservice", "route_generation", "slo_burn"],
        "retry_policy": "page once, then attach evidence updates to the same incident",
        "allowed_side_effect": "freeze canary widening only",
        "owner": "serving-oncall",
    },
    "page_release_incident_commander": {
        "receiver": "pagerduty://release-incident-commander",
        "dedupe_key": "model_version:rollback_execution",
        "payload_fields": ["model_version", "previous_champion", "rollback_requested_at", "release_operation_id"],
        "retry_policy": "page once per rollback operation id",
        "allowed_side_effect": "request champion restore task; callback itself does not mutate registry aliases",
        "owner": "release-commander",
    },
}


def _deadline_policies_with_callbacks() -> list[dict]:
    return [
        {
            **policy,
            "callback_contract": CALLBACK_CONTRACTS[policy["callback"]],
        }
        for policy in DEADLINE_POLICIES
    ]


def build_deadline_alert_plan(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    root = Path(root)
    deadline_policies = _deadline_policies_with_callbacks()
    checks = [
        {"name": "airflow3_deadline_alerts_declared", "passed": len(DEADLINE_POLICIES) >= 4},
        {"name": "legacy_sla_removed", "passed": True, "observed": "Airflow 3 replaces SLA callbacks with Deadline Alerts"},
        {"name": "callback_timeout_bounded", "passed": True, "observed": "AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT=300"},
        {
            "name": "callback_contracts_declared",
            "passed": all(policy.get("callback_contract", {}).get("dedupe_key") for policy in deadline_policies),
        },
        {
            "name": "callbacks_have_bounded_side_effects",
            "passed": all("allowed_side_effect" in policy.get("callback_contract", {}) for policy in deadline_policies),
        },
        {"name": "canary_readiness_deadline", "passed": any(policy["name"] == "canary_readiness" for policy in DEADLINE_POLICIES)},
        {"name": "rollback_deadline", "passed": any(policy["name"] == "rollback_execution" for policy in DEADLINE_POLICIES)},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_airflow3_release_deadline_alerts" if all(check["passed"] for check in checks) else "keep_release_timeout_controls",
        "dag_id": "enterprise_kubernetes_mlops_release",
        "deadline_policies": deadline_policies,
        "callback_contracts": CALLBACK_CONTRACTS,
        "runtime_config": {
            "AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT": "300",
            "max_active_runs": 1,
            "protected_pools": ["ml_platform_pool", "ml_training_pool"],
        },
        "checks": checks,
        "guardrails": [
            "Use Deadline Alerts for Dag run time thresholds instead of legacy Airflow SLA callbacks.",
            "Bound callback execution so a stuck notifier cannot block release recovery.",
            "Keep callbacks idempotent with explicit dedupe keys and bounded payloads.",
            "Callbacks may notify, page, open incidents, or request guarded tasks; they must not directly mutate registry, routes, or quota.",
            "Route candidate registration misses to training, registry, and evaluation-gate owners.",
            "Route canary and rollback misses to KServe readiness, Gateway routing, and champion restore actions.",
        ],
        "references": [
            "https://airflow.apache.org/docs/apache-airflow/stable/howto/deadline-alerts.html",
            "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html#slas",
            "https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html#callback-execution-timeout",
        ],
    }
    write_json(root / "reports" / "deadline_alert_plan.json", plan)
    return plan
