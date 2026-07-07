from __future__ import annotations

import hashlib
from pathlib import Path

from .io import write_json


def _hex(value: str, length: int) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def span(trace_id: str, name: str, *, parent: str | None, service: str, duration_ms: float, attributes: dict) -> dict:
    span_id = _hex(f"{trace_id}:{name}:{service}", 16)
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent,
        "name": name,
        "service": service,
        "kind": "internal",
        "status": "ok",
        "duration_ms": duration_ms,
        "attributes": attributes,
    }


def build_trace_report(root: str | Path) -> dict:
    root = Path(root)
    trace_id = _hex("churn-risk-release-trace", 32)
    release = span(trace_id, "airflow.release", parent=None, service="airflow", duration_ms=1800.0, attributes={"dag": "enterprise_kubernetes_mlops_release"})
    train = span(trace_id, "metaflow.train", parent=release["span_id"], service="metaflow", duration_ms=780.0, attributes={"model": "churn-risk"})
    registry = span(trace_id, "mlflow.register", parent=train["span_id"], service="mlflow", duration_ms=42.0, attributes={"stage": "candidate"})
    serve = span(trace_id, "kserve.canary", parent=registry["span_id"], service="kserve", duration_ms=310.0, attributes={"traffic_percent": 10})
    monitor = span(trace_id, "prometheus.slo_check", parent=serve["span_id"], service="prometheus", duration_ms=18.0, attributes={"slo": "latency_p95"})
    spans = [release, train, registry, serve, monitor]
    report = {
        "trace_id": trace_id,
        "span_count": len(spans),
        "critical_path_ms": round(sum(item["duration_ms"] for item in spans), 2),
        "root_service": "airflow",
        "leaf_service": "prometheus",
        "spans": spans,
    }
    write_json(root / "reports" / "trace_report.json", report)
    return report
