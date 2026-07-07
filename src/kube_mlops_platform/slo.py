from __future__ import annotations

from pathlib import Path

from .io import read_json, write_json


def burn_rate(error_ratio: float, target: float) -> float:
    return round(error_ratio / max(1.0 - target, 0.0001), 4)


def remaining_budget_pct(error_ratio: float, target: float) -> float:
    budget = max(1.0 - target, 0.0001)
    return round(max(0.0, 100.0 * (1.0 - error_ratio / budget)), 2)


def _slo(name: str, *, target: float, error_ratio: float, owner: str) -> dict:
    burn = burn_rate(error_ratio, target)
    if burn >= 14.4:
        status = "page"
    elif burn >= 6.0:
        status = "hold_release"
    elif burn >= 1.0:
        status = "ticket"
    else:
        status = "healthy"
    return {
        "name": name,
        "target": target,
        "error_ratio": round(error_ratio, 6),
        "burn_rate": burn,
        "remaining_error_budget_pct": remaining_budget_pct(error_ratio, target),
        "status": status,
        "owner": owner,
    }


def build_slo_report(root: str | Path) -> dict:
    root = Path(root)
    monitoring = read_json(root / "reports" / "monitoring_report.json")
    latency_p95 = float(monitoring.get("latency_ms", {}).get("p95", 999.0))
    feature_drift_passed = bool(monitoring.get("feature_drift", {}).get("passed", False))
    prediction_drift_passed = bool(monitoring.get("prediction_drift", {}).get("passed", False))
    slos = [
        _slo("online_inference_availability", target=0.995, error_ratio=float(monitoring.get("error_rate", 1.0)), owner="serving"),
        _slo("online_inference_latency_p95", target=0.99, error_ratio=0.0 if latency_p95 <= 50.0 else 1.0, owner="serving"),
        _slo("feature_drift_clean_window", target=0.95, error_ratio=0.0 if feature_drift_passed else 1.0, owner="data-quality"),
        _slo("prediction_drift_clean_window", target=0.95, error_ratio=0.0 if prediction_drift_passed else 1.0, owner="ml-platform"),
    ]
    max_burn = max(item["burn_rate"] for item in slos)
    if max_burn >= 14.4:
        action = "freeze_promotion_and_page"
    elif max_burn >= 6.0:
        action = "hold_canary_and_open_incident"
    elif max_burn >= 1.0:
        action = "create_ticket_before_next_release"
    else:
        action = "allow_release"
    report = {
        "platform": "advanced-kubernetes-mlops-platform",
        "policy": {
            "window": "30d",
            "multiwindow_burn_rates": [
                {"name": "fast_page", "short_window": "5m", "long_window": "1h", "burn_rate": 14.4, "budget_consumed": "2%"},
                {"name": "slow_page", "short_window": "30m", "long_window": "6h", "burn_rate": 6.0, "budget_consumed": "5%"},
                {"name": "ticket", "short_window": "6h", "long_window": "3d", "burn_rate": 1.0, "budget_consumed": "10%"},
            ],
        },
        "slos": slos,
        "max_burn_rate": max_burn,
        "recommended_action": action,
        "release_freeze": action in {"freeze_promotion_and_page", "hold_canary_and_open_incident"},
    }
    write_json(root / "reports" / "slo_error_budget.json", report)
    return report
