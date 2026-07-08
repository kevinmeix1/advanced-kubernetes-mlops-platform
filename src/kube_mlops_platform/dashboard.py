from __future__ import annotations

import html
from pathlib import Path


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def badge(value: bool) -> str:
    klass = "pass" if value else "fail"
    label = "PASS" if value else "FAIL"
    return f'<span class="badge {klass}">{label}</span>'


DISPLAY_NAMES = {
    "data_quality_gate": "Data quality",
    "min_accuracy": "Minimum accuracy",
    "min_f1": "Minimum F1",
    "max_brier_score": "Max Brier score",
    "segment_accuracy_gap": "Segment gap",
    "latency_gate_p95_ms": "Latency p95",
    "row_count_min_500": "Row count",
    "required_columns_present": "Required columns",
    "no_nulls_in_required_columns": "No nulls",
    "numeric_features_parse": "Numeric features",
    "binary_target": "Binary target",
    "target_has_signal": "Target signal",
    "late_payments": "Late payments",
    "monthly_spend": "Monthly spend",
    "support_tickets": "Support tickets",
    "tenure_months": "Tenure",
    "usage_drop_pct": "Usage drop",
}


def pretty(value: object) -> str:
    text = str(value)
    return DISPLAY_NAMES.get(text, text.replace("_", " "))


def traffic_chips(value: object) -> str:
    if not isinstance(value, dict):
        return esc(value)
    return "".join(f'<span class="chip">{esc(key)} {esc(amount)}%</span>' for key, amount in sorted(value.items()))


def short_path(value: object) -> str:
    text = "" if value is None else str(value)
    parts = [part for part in text.split("/") if part]
    display = "/".join(parts[-3:]) if len(parts) > 3 else text
    if display and display != text:
        display = f".../{display}"
    return f'<code title="{esc(text)}">{esc(display)}</code>'


def rows(items: list[dict], columns: list[str]) -> str:
    if not items:
        return f"<tr><td colspan='{len(columns)}'>No records</td></tr>"
    rendered = []
    for item in items:
        rendered.append("<tr>" + "".join(f"<td>{cell(item.get(column, ''))}</td>" for column in columns) + "</tr>")
    return "\n".join(rendered)


def cell(value: object) -> str:
    text = str(value)
    if text.startswith("<span class="):
        return text
    return esc(text)


def render_dashboard(
    output_path: str | Path,
    *,
    validation_report: dict,
    gate_report: dict,
    deployment_state: dict,
    monitoring_report: dict,
    registry_metadata: dict,
    release_plan: dict | None = None,
) -> Path:
    release_plan = release_plan or {}
    release_policy = release_plan.get("policy", {})
    queue_state = release_plan.get("queue_state", {})
    gate_rows = [
        {
            "gate": pretty(check.get("name")),
            "status": badge(bool(check.get("passed"))),
            "observed": check.get("observed"),
            "threshold": check.get("threshold", ""),
        }
        for check in gate_report.get("checks", [])
    ]
    validation_rows = [
        {"check": pretty(check["name"]), "status": badge(bool(check["passed"])), "observed": check.get("observed")}
        for check in validation_report.get("checks", [])
    ]
    drift = monitoring_report.get("feature_drift", {})
    drift_rows = [
        {
            "feature": pretty(feature),
            "delta": drift.get("deltas", {}).get(feature),
            "flagged": badge(not bool(drift.get("feature_drift_flagged", {}).get(feature))),
        }
        for feature in sorted(drift.get("deltas", {}))
    ]
    prediction_rows = monitoring_report.get("recent_predictions", [])[-12:]
    alerts = ", ".join(pretty(alert) for alert in monitoring_report.get("alerts", [])) or "none"
    body = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <title>Kubernetes MLOps Platform Dashboard</title>
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <style>
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          background: #f4f6f8;
          color: #172026;
          font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        header {{
          background: #172026;
          color: white;
          padding: 28px 36px;
          border-bottom: 5px solid #10b981;
        }}
        main {{ padding: 24px 36px 42px; max-width: 1480px; margin: 0 auto; }}
        h1 {{ margin: 0; font-size: 28px; line-height: 1.2; }}
        h2 {{ margin: 0 0 14px; font-size: 17px; line-height: 1.3; color: #172026; }}
        header p {{ margin: 8px 0 0; color: #cbd5df; max-width: 880px; line-height: 1.5; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin-bottom: 18px; }}
        .metric {{
          min-height: 112px;
          background: white;
          border: 1px solid #d7dee7;
          border-radius: 8px;
          padding: 16px;
          box-shadow: 0 1px 2px rgba(23, 32, 38, 0.04);
        }}
        .metric span {{ display: block; color: #64748b; font-size: 13px; margin-bottom: 10px; }}
        .metric strong {{ display: block; font-size: 24px; line-height: 1.2; overflow-wrap: anywhere; }}
        .metric code {{ font-size: 18px; }}
        .layout {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(340px, 0.45fr); gap: 16px; align-items: start; }}
        .panel {{
          background: white;
          border: 1px solid #d7dee7;
          border-radius: 8px;
          margin-top: 16px;
          padding: 16px;
          box-shadow: 0 1px 2px rgba(23, 32, 38, 0.04);
        }}
        .table-wrap {{ overflow-x: auto; border: 1px solid #e4e9f0; border-radius: 6px; }}
        table {{ width: 100%; min-width: 0; border-collapse: collapse; background: white; table-layout: fixed; }}
        th, td {{ border-bottom: 1px solid #e8edf3; padding: 11px 12px; text-align: left; font-size: 14px; overflow-wrap: anywhere; vertical-align: top; }}
        th {{ background: #f8fafc; color: #334155; font-weight: 700; }}
        tr:last-child td {{ border-bottom: 0; }}
        code {{ background: #eef2f6; border-radius: 4px; padding: 3px 5px; color: #0f172a; }}
        .badge {{ display: inline-block; border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 800; }}
        .metric .badge {{ width: auto; max-width: max-content; }}
        .pass {{ background: #dcfce7; color: #166534; }}
        .fail {{ background: #fee2e2; color: #991b1b; }}
        .traffic {{ color: #0f766e; font-weight: 700; }}
        .chip {{ display: inline-block; margin: 0 5px 5px 0; padding: 4px 8px; border-radius: 999px; background: #ecfdf5; color: #0f766e; font-size: 12px; font-weight: 800; white-space: nowrap; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
        .summary-item {{ border: 1px solid #e4e9f0; border-radius: 6px; padding: 12px; min-height: 76px; }}
        .summary-item span {{ display: block; color: #64748b; font-size: 12px; margin-bottom: 8px; }}
        .summary-item strong {{ display: block; font-size: 17px; line-height: 1.25; overflow-wrap: anywhere; }}
        .summary-item.wide {{ grid-column: 1 / -1; }}
        @media (max-width: 900px) {{
          header {{ padding: 22px 18px; }}
          main {{ padding: 18px; }}
          .layout {{ grid-template-columns: 1fr; }}
          h1 {{ font-size: 24px; }}
        }}
      </style>
    </head>
    <body>
      <header>
        <h1>Kubernetes MLOps Platform</h1>
        <p>Metaflow training, Airflow orchestration, MLflow registry, KServe serving, and production-grade observability.</p>
      </header>
      <main>
        <section class="grid">
          <div class="metric"><span>Champion model</span><strong>{esc(registry_metadata.get('version', 'none'))}</strong></div>
          <div class="metric"><span>Gate status</span><strong>{badge(gate_report.get('passed', False))}</strong></div>
          <div class="metric"><span>KServe status</span><strong>{esc(deployment_state.get('status', 'not deployed'))}</strong></div>
          <div class="metric"><span>Latency p95</span><strong>{esc(monitoring_report.get('latency_ms', {}).get('p95', 0))} ms</strong></div>
        </section>

        <section class="layout">
          <div>
            <div class="panel">
              <h2>Evaluation Gates</h2>
              <div class="table-wrap"><table><tr><th>Gate</th><th>Status</th><th>Observed</th><th>Threshold</th></tr>{rows(gate_rows, ['gate', 'status', 'observed', 'threshold'])}</table></div>
            </div>

            <div class="panel">
              <h2>KServe Deployment</h2>
              <div class="table-wrap">
                <table>
                  <tr><th>Service</th><th>Namespace</th><th>Runtime</th><th>Traffic</th><th>Model URI</th></tr>
                  <tr><td>{esc(deployment_state.get('service_name'))}</td><td>{esc(deployment_state.get('namespace'))}</td><td>{esc(deployment_state.get('runtime'))}</td><td class="traffic">{traffic_chips(deployment_state.get('traffic'))}</td><td>{short_path(deployment_state.get('model_uri'))}</td></tr>
                </table>
              </div>
            </div>

            <div class="panel">
              <h2>Recent Predictions</h2>
              <div class="table-wrap"><table><tr><th>Customer</th><th>Score</th><th>Prediction</th><th>Model</th><th>Latency</th><th>Status</th></tr>{rows(prediction_rows, ['customer_id', 'churn_score', 'prediction', 'model_version', 'latency_ms', 'status'])}</table></div>
            </div>
          </div>

          <div>
            <div class="panel">
              <h2>Great Expectations Validation</h2>
              <div class="table-wrap"><table><tr><th>Check</th><th>Status</th><th>Observed</th></tr>{rows(validation_rows, ['check', 'status', 'observed'])}</table></div>
            </div>

            <div class="panel">
              <h2>Feature Drift</h2>
              <div class="table-wrap"><table><tr><th>Feature</th><th>Delta</th><th>Status</th></tr>{rows(drift_rows, ['feature', 'delta', 'flagged'])}</table></div>
            </div>

            <div class="panel">
              <h2>Release Control Plane</h2>
              <div class="summary-grid">
                <div class="summary-item"><span>Recommended action</span><strong>{esc(release_plan.get('recommended_action', 'not planned'))}</strong></div>
                <div class="summary-item"><span>Error budget burn</span><strong>{esc(release_policy.get('error_budget_burn_rate', 'n/a'))}</strong></div>
                <div class="summary-item"><span>Queue pressure</span><strong>{esc(release_policy.get('queue_pressure', 'n/a'))}</strong></div>
                <div class="summary-item"><span>Kueue queue</span><strong>{esc(queue_state.get('queue', 'n/a'))}</strong></div>
              </div>
            </div>

            <div class="panel">
              <h2>Serving Observability</h2>
              <div class="summary-grid">
                <div class="summary-item"><span>Predictions</span><strong>{esc(monitoring_report.get('throughput', {}).get('prediction_count'))}</strong></div>
                <div class="summary-item"><span>Error rate</span><strong>{esc(monitoring_report.get('error_rate'))}</strong></div>
                <div class="summary-item"><span>Mean score</span><strong>{esc(monitoring_report.get('prediction_drift', {}).get('mean_score'))}</strong></div>
                <div class="summary-item"><span>High risk share</span><strong>{esc(monitoring_report.get('prediction_drift', {}).get('high_risk_share'))}</strong></div>
                <div class="summary-item wide"><span>Alerts</span><strong>{esc(alerts)}</strong></div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </body>
    </html>
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    return output_path
