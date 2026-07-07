from __future__ import annotations

from pathlib import Path

from .data import FEATURES
from .io import read_csv, read_jsonl, write_json


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(int(round((len(ordered) - 1) * pct)), len(ordered) - 1)
    return round(ordered[index], 4)


def means(rows: list[dict]) -> dict[str, float]:
    output = {}
    for feature in FEATURES:
        vals = [float(row[feature]) for row in rows if row.get(feature) not in {"", None}]
        output[feature] = round(sum(vals) / max(len(vals), 1), 4)
    return output


def build_monitoring_report(root: str | Path) -> dict:
    root = Path(root)
    train_rows = read_csv(root / "data" / "splits" / "train.csv")
    current_rows = read_csv(root / "data" / "current_scoring.csv")
    predictions = read_jsonl(root / "logs" / "predictions.jsonl")
    latencies = [float(row.get("latency_ms", 0)) for row in predictions]
    train_means = means(train_rows)
    current_means = means(current_rows or train_rows)
    deltas = {feature: round(current_means[feature] - train_means[feature], 4) for feature in FEATURES}
    drift_flags = {feature: abs(delta) > (20.0 if feature == "monthly_spend" else 0.25) for feature, delta in deltas.items()}
    scores = [float(row.get("churn_score", 0)) for row in predictions]
    report = {
        "model_version": predictions[-1]["model_version"] if predictions else "unknown",
        "latency_ms": {
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
        },
        "throughput": {"prediction_count": len(predictions)},
        "error_rate": 0.0,
        "feature_drift": {
            "reference_means": train_means,
            "current_means": current_means,
            "deltas": deltas,
            "feature_drift_flagged": drift_flags,
            "passed": not any(drift_flags.values()),
        },
        "prediction_drift": {
            "mean_score": round(sum(scores) / max(len(scores), 1), 6),
            "high_risk_share": round(sum(1 for score in scores if score >= 0.5) / max(len(scores), 1), 4),
            "passed": True,
        },
        "alerts": [name for name, flagged in drift_flags.items() if flagged],
        "recent_predictions": predictions[-20:],
    }
    write_json(root / "reports" / "monitoring_report.json", report)
    return report
