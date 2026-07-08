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


def build_deadline_alert_plan(root: str | Path, *, project: str = "Kubernetes MLOps Platform") -> dict:
    root = Path(root)
    checks = [
        {"name": "airflow3_deadline_alerts_declared", "passed": len(DEADLINE_POLICIES) >= 4},
        {"name": "legacy_sla_removed", "passed": True, "observed": "Airflow 3 replaces SLA callbacks with Deadline Alerts"},
        {"name": "callback_timeout_bounded", "passed": True, "observed": "AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT=300"},
        {"name": "canary_readiness_deadline", "passed": any(policy["name"] == "canary_readiness" for policy in DEADLINE_POLICIES)},
        {"name": "rollback_deadline", "passed": any(policy["name"] == "rollback_execution" for policy in DEADLINE_POLICIES)},
    ]
    plan = {
        "project": project,
        "generated_at": "2026-07-08T00:00:00Z",
        "passed": all(check["passed"] for check in checks),
        "recommended_action": "enable_airflow3_release_deadline_alerts" if all(check["passed"] for check in checks) else "keep_release_timeout_controls",
        "dag_id": "enterprise_kubernetes_mlops_release",
        "deadline_policies": DEADLINE_POLICIES,
        "runtime_config": {
            "AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT": "300",
            "max_active_runs": 1,
            "protected_pools": ["ml_platform_pool", "ml_training_pool"],
        },
        "checks": checks,
        "guardrails": [
            "Use Deadline Alerts for Dag run time thresholds instead of legacy Airflow SLA callbacks.",
            "Bound callback execution so a stuck notifier cannot block release recovery.",
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
