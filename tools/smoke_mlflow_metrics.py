from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path


def evaluate_metrics(
    body: str,
    content_type: str,
    expected_exporter_version: str,
) -> tuple[dict[str, bool], str | None]:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    samples = [line for line in lines if line.startswith("mlflow_exporter_info{")]
    expected_label = f'version="{expected_exporter_version}"'
    sample = samples[0] if samples else None
    checks = {
        "prometheus_content_type": content_type.lower().startswith("text/plain"),
        "exporter_help_declared": (
            "# HELP mlflow_exporter_info Information about the Prometheus Flask exporter"
            in lines
        ),
        "exporter_type_declared": "# TYPE mlflow_exporter_info gauge" in lines,
        "pinned_exporter_reported": any(
            expected_label in candidate and candidate.endswith(" 1.0")
            for candidate in samples
        ),
    }
    return checks, sample


def run_contract(
    base_url: str,
    expected_exporter_version: str,
    timeout_seconds: float,
) -> dict:
    url = f"{base_url.rstrip('/')}/metrics"
    status: int | None = None
    content_type = ""
    body = ""
    error: str | None = None
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            body = response.read().decode("utf-8")
    except (OSError, UnicodeError) as exc:
        error = str(exc)

    checks, sample = evaluate_metrics(
        body,
        content_type,
        expected_exporter_version,
    )
    checks = {"endpoint_reachable": status == 200, **checks}
    return {
        "passed": all(checks.values()),
        "endpoint": url,
        "status": status,
        "content_type": content_type,
        "expected_exporter_version": expected_exporter_version,
        "observed_info_sample": sample,
        "metric_family_count": sum(
            1 for line in body.splitlines() if line.startswith("# HELP ")
        ),
        "checks": checks,
        "error": error,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the MLflow Prometheus exposition contract"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--expected-exporter-version", default="0.23.2")
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".local/reports/mlflow_server_metrics_contract.json"),
    )
    args = parser.parse_args()

    report = run_contract(
        args.base_url,
        args.expected_exporter_version,
        args.timeout_seconds,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
