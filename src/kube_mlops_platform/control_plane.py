from __future__ import annotations

from pathlib import Path

from .io import read_json, write_json

RELEASE_THRESHOLDS = {
    "availability_slo": 0.995,
    "latency_p95_ms": 50.0,
    "error_budget_burn": 2.0,
    "queue_pressure": 0.80,
    "rollback_burn_rate": 8.0,
    "rollback_error_rate": 0.05,
}


def error_budget_burn_rate(
    error_rate: float,
    *,
    availability_slo: float = RELEASE_THRESHOLDS["availability_slo"],
) -> float:
    error_budget = max(1.0 - availability_slo, 0.0001)
    return round(error_rate / error_budget, 4)


def queue_pressure(queued_jobs: int, available_slots: int) -> float:
    return round(queued_jobs / max(queued_jobs + available_slots, 1), 4)


def _load_json_or_empty(path: Path) -> dict:
    return read_json(path) if path.exists() else {}


def evaluate_release_policy(gate_report: dict, monitoring_report: dict, queue_state: dict) -> dict:
    latency_p95 = float(monitoring_report.get("latency_ms", {}).get("p95", 0.0))
    error_rate = float(monitoring_report.get("error_rate", 0.0))
    burn = error_budget_burn_rate(error_rate)
    pressure = queue_pressure(int(queue_state.get("queued_jobs", 0)), int(queue_state.get("available_slots", 1)))
    drift_passed = bool(monitoring_report.get("feature_drift", {}).get("passed", True))
    gate_passed = bool(gate_report.get("passed", False))
    checks = [
        {"name": "offline_gates", "passed": gate_passed, "observed": gate_passed},
        {"name": "feature_drift", "passed": drift_passed, "observed": monitoring_report.get("feature_drift", {})},
        {
            "name": "latency_p95",
            "passed": latency_p95 <= RELEASE_THRESHOLDS["latency_p95_ms"],
            "observed": latency_p95,
            "threshold": RELEASE_THRESHOLDS["latency_p95_ms"],
        },
        {
            "name": "error_budget_burn",
            "passed": burn <= RELEASE_THRESHOLDS["error_budget_burn"],
            "observed": burn,
            "threshold": RELEASE_THRESHOLDS["error_budget_burn"],
        },
        {
            "name": "queue_pressure",
            "passed": pressure <= RELEASE_THRESHOLDS["queue_pressure"],
            "observed": pressure,
            "threshold": RELEASE_THRESHOLDS["queue_pressure"],
        },
    ]
    if (
        burn >= RELEASE_THRESHOLDS["rollback_burn_rate"]
        or error_rate >= RELEASE_THRESHOLDS["rollback_error_rate"]
    ):
        action = "rollback"
    elif all(check["passed"] for check in checks):
        action = "advance_canary"
    else:
        action = "hold"
    return {"action": action, "checks": checks, "error_budget_burn_rate": burn, "queue_pressure": pressure}


def build_release_plan(root: str | Path, *, queued_jobs: int = 2, available_slots: int = 8) -> dict:
    root = Path(root)
    gate_report = _load_json_or_empty(root / "reports" / "gate_report.json")
    monitoring_report = _load_json_or_empty(root / "reports" / "monitoring_report.json")
    queue_state = {
        "queue": "churn-release-queue",
        "queued_jobs": queued_jobs,
        "available_slots": available_slots,
        "airflow_pool": "ml_platform_pool",
        "kueue_cluster_queue": "churn-release-cluster-queue",
    }
    policy = evaluate_release_policy(gate_report, monitoring_report, queue_state)
    plan = {
        "model": "churn-risk",
        "target": "kserve://mlops/churn-risk-predictor",
        "recommended_action": policy["action"],
        "thresholds": dict(RELEASE_THRESHOLDS),
        "queue_state": queue_state,
        "policy": policy,
        "stages": [
            {"name": "validate_offline_gates", "system": "airflow", "pool_slots": 2},
            {"name": "reserve_kueue_quota", "system": "kueue", "queue": queue_state["queue"]},
            {"name": "deploy_canary", "system": "kserve", "traffic_percent": 10},
            {"name": "watch_slo_budget", "system": "prometheus", "burn_rate_limit": 2.0},
            {"name": "promote_or_rollback", "system": "airflow", "action": policy["action"]},
        ],
        "rollback": {
            "trigger": "burn_rate>=8 or error_rate>=0.05",
            "command": "make rollback",
            "expected_recovery_minutes": 10,
        },
    }
    write_json(root / "reports" / "release_control_plan.json", plan)
    return plan
