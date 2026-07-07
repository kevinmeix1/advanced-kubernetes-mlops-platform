from __future__ import annotations


def evaluate_gates(metrics: dict, validation_report: dict, *, latency_ms_p95: float = 25.0) -> dict:
    checks = [
        {"name": "data_quality_gate", "passed": validation_report.get("passed", False), "observed": validation_report.get("row_count")},
        {"name": "min_accuracy", "passed": metrics.get("accuracy", 0) >= 0.70, "observed": metrics.get("accuracy"), "threshold": 0.70},
        {"name": "min_f1", "passed": metrics.get("f1", 0) >= 0.62, "observed": metrics.get("f1"), "threshold": 0.62},
        {"name": "max_brier_score", "passed": metrics.get("brier_score", 1) <= 0.24, "observed": metrics.get("brier_score"), "threshold": 0.24},
        {
            "name": "segment_accuracy_gap",
            "passed": metrics.get("segment_accuracy_gap", 1) <= 0.18,
            "observed": metrics.get("segment_accuracy_gap"),
            "threshold": 0.18,
        },
        {"name": "latency_gate_p95_ms", "passed": latency_ms_p95 <= 50.0, "observed": latency_ms_p95, "threshold": 50.0},
    ]
    return {"passed": all(check["passed"] for check in checks), "checks": checks}
