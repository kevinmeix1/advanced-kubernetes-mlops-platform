from __future__ import annotations

import html
import json
from pathlib import Path


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def badge(value: bool) -> str:
    klass = "pass" if value else "fail"
    label = "PASS" if value else "FAIL"
    return f'<span class="badge {klass}">{label}</span>'


def contract_badge(value: object) -> str:
    if value is None:
        return '<span class="badge neutral">NOT RUN</span>'
    return badge(bool(value))


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
    display = "/".join(parts[-2:]) if len(parts) > 2 else text
    if display and display != text:
        display = f".../{display}"
    return f'<code class="path" title="{esc(text)}">{esc(display)}</code>'


def display_label(value: object) -> str:
    text = "" if value is None else str(value)
    labels = {
        "churn-risk-predictor": "churn risk predictor",
        "kserve-sklearnserver": "KServe sklearn",
        "fail_closed_keep_pod_scheduling_gated": "Fail closed",
    }
    return f'<span class="nowrap" title="{esc(text)}">{esc(labels.get(text, text))}</span>'


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
    mlflow_contract: dict | None = None,
    scheduling_gate_controller: dict | None = None,
) -> Path:
    release_plan = release_plan or {}
    mlflow_contract = mlflow_contract or {}
    scheduling_gate_controller = scheduling_gate_controller or {}
    release_policy = release_plan.get("policy", {})
    queue_state = release_plan.get("queue_state", {})
    gate_controller_summary = scheduling_gate_controller.get("summary", {})
    gate_controller = scheduling_gate_controller.get("controller", {})
    mlflow_aliases = mlflow_contract.get("aliases", {})
    mlflow_versions = mlflow_contract.get("inventory", {}).get("versions", [])
    champion_registry_version = mlflow_aliases.get("champion")
    champion_application_version = next(
        (
            version.get("application_version")
            for version in mlflow_versions
            if version.get("registry_version") == champion_registry_version
        ),
        registry_metadata.get("version", "none"),
    )
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
    release_simulation = {
        "thresholds": release_plan.get(
            "thresholds",
            {
                "availability_slo": 0.995,
                "latency_p95_ms": 50.0,
                "error_budget_burn": 2.0,
                "queue_pressure": 0.8,
                "rollback_burn_rate": 8.0,
                "rollback_error_rate": 0.05,
            },
        ),
        "initial": {
            "offline_gates": bool(gate_report.get("passed", False)),
            "feature_healthy": bool(monitoring_report.get("feature_drift", {}).get("passed", True)),
            "latency_p95_ms": float(monitoring_report.get("latency_ms", {}).get("p95", 0.0)),
            "error_rate_pct": float(monitoring_report.get("error_rate", 0.0)) * 100,
            "queued_jobs": int(queue_state.get("queued_jobs", 0)),
            "available_slots": int(queue_state.get("available_slots", 1)),
        },
    }
    release_payload = json.dumps(release_simulation, separators=(",", ":")).replace("</", "<\\/")
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
        .layout > div, .panel {{ min-width: 0; }}
        .panel {{
          background: white;
          border: 1px solid #d7dee7;
          border-radius: 8px;
          margin-top: 16px;
          padding: 16px;
          box-shadow: 0 1px 2px rgba(23, 32, 38, 0.04);
        }}
        .table-wrap {{ overflow-x: auto; overscroll-behavior-inline: contain; border: 1px solid #e4e9f0; border-radius: 6px; }}
        table {{ width: 100%; min-width: 0; border-collapse: collapse; background: white; table-layout: fixed; }}
        th, td {{ border-bottom: 1px solid #e8edf3; padding: 11px 12px; text-align: left; font-size: 14px; overflow-wrap: anywhere; vertical-align: top; }}
        th {{ background: #f8fafc; color: #334155; font-weight: 700; }}
        tr:last-child td {{ border-bottom: 0; }}
        code {{ background: #eef2f6; border-radius: 4px; padding: 3px 5px; color: #0f172a; }}
        code.path, .nowrap {{ display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: bottom; }}
        .badge {{ display: inline-block; border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 800; }}
        .metric .badge {{ width: auto; max-width: max-content; }}
        .pass {{ background: #dcfce7; color: #166534; }}
        .fail {{ background: #fee2e2; color: #991b1b; }}
        .neutral {{ background: #e2e8f0; color: #334155; }}
        .traffic {{ color: #0f766e; font-weight: 700; }}
        .chip {{ display: inline-block; margin: 0 5px 5px 0; padding: 4px 8px; border-radius: 999px; background: #ecfdf5; color: #0f766e; font-size: 12px; font-weight: 800; white-space: nowrap; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
        .summary-item {{ border-top: 1px solid #e4e9f0; padding: 12px 2px; min-height: 70px; }}
        .summary-item span {{ display: block; color: #64748b; font-size: 12px; margin-bottom: 8px; }}
        .summary-item strong {{ display: block; font-size: 17px; line-height: 1.25; overflow-wrap: anywhere; }}
        .summary-item.wide {{ grid-column: 1 / -1; }}
        .decision-lab {{ border-left: 4px solid #0f766e; margin: 0 0 18px; }}
        .decision-heading {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 18px; }}
        .decision-heading p {{ color: #64748b; font-size: 13px; line-height: 1.45; margin: 5px 0 0; }}
        .decision-pill {{ min-width: 154px; border-radius: 6px; padding: 10px 14px; color: white; font-size: 13px; font-weight: 800; text-align: center; }}
        .decision-pill.advance {{ background: #15803d; }}
        .decision-pill.hold {{ background: #b45309; }}
        .decision-pill.rollback {{ background: #b91c1c; }}
        .decision-grid {{ display: grid; grid-template-columns: minmax(330px, .72fr) minmax(0, 1.28fr); gap: 22px; align-items: start; }}
        .decision-controls {{ display: grid; gap: 13px; }}
        .control-row {{ display: grid; grid-template-columns: 130px minmax(0, 1fr) 72px; align-items: center; gap: 10px; }}
        .control-row label, .toggle-row > span {{ color: #475569; font-size: 12px; font-weight: 700; }}
        .control-row input {{ width: 100%; accent-color: #0f766e; }}
        .control-value {{ border-radius: 5px; background: #eef2f6; color: #0f172a; padding: 6px 7px; font-size: 12px; font-weight: 800; text-align: center; }}
        .toggle-row {{ display: flex; min-height: 30px; align-items: center; justify-content: space-between; gap: 18px; }}
        .switch {{ position: relative; display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }}
        .switch input {{ position: absolute; width: 1px; height: 1px; opacity: 0; }}
        .switch-ui {{ position: relative; width: 40px; height: 22px; border-radius: 999px; background: #cbd5e1; transition: background .15s ease; }}
        .switch-ui::after {{ content: ""; position: absolute; width: 16px; height: 16px; left: 3px; top: 3px; border-radius: 50%; background: white; box-shadow: 0 1px 2px rgba(15,23,42,.25); transition: transform .15s ease; }}
        .switch input:checked + .switch-ui {{ background: #0f766e; }}
        .switch input:checked + .switch-ui::after {{ transform: translateX(18px); }}
        .switch input:focus-visible + .switch-ui {{ outline: 3px solid rgba(14,116,144,.22); outline-offset: 2px; }}
        .switch-label {{ color: #334155; font-size: 12px; font-weight: 800; min-width: 54px; text-align: right; }}
        .decision-kpis {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1px solid #e4e9f0; border-radius: 6px; overflow: hidden; }}
        .decision-kpis div {{ min-height: 72px; padding: 11px; background: #f8fafc; border-right: 1px solid #e4e9f0; }}
        .decision-kpis div:last-child {{ border-right: 0; }}
        .decision-kpis span {{ display: block; color: #64748b; font-size: 11px; margin-bottom: 7px; }}
        .decision-kpis strong {{ display: block; font-size: 17px; }}
        .decision-reason {{ min-height: 42px; color: #475569; font-size: 12px; line-height: 1.45; margin: 11px 0; }}
        .stage-rail {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); border-top: 1px solid #dbe3ec; }}
        .stage-step {{ min-width: 0; padding: 10px 9px; border-right: 1px solid #e4e9f0; border-bottom: 3px solid #94a3b8; }}
        .stage-step:last-child {{ border-right: 0; }}
        .stage-step.pass {{ border-bottom-color: #16a34a; }}
        .stage-step.fail {{ border-bottom-color: #dc2626; }}
        .stage-step.hold {{ border-bottom-color: #d97706; }}
        .stage-step span {{ display: block; color: #64748b; font-size: 10px; text-transform: uppercase; margin-bottom: 4px; }}
        .stage-step strong {{ display: block; font-size: 12px; overflow-wrap: anywhere; }}
        .check-list {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 5px; margin-top: 10px; }}
        .check-item {{ display: flex; align-items: center; justify-content: space-between; gap: 6px; padding: 6px 7px; border-radius: 4px; background: #f8fafc; color: #475569; font-size: 10px; }}
        .check-dot {{ width: 8px; height: 8px; flex: 0 0 8px; border-radius: 50%; background: #16a34a; }}
        .check-item.fail .check-dot {{ background: #dc2626; }}
        @media (max-width: 900px) {{
          header {{ padding: 22px 18px; }}
          main {{ padding: 18px; }}
          .layout, .decision-grid {{ grid-template-columns: 1fr; }}
          .wide-table {{ min-width: 680px; }}
          h1 {{ font-size: 24px; }}
        }}
        @media (max-width: 620px) {{
          .decision-heading {{ flex-direction: column; }}
          .decision-pill {{ width: 100%; }}
          .control-row {{ grid-template-columns: 104px minmax(0, 1fr) 64px; }}
          .decision-kpis, .check-list {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
          .decision-kpis div:nth-child(2) {{ border-right: 0; }}
          .decision-kpis div:last-child {{ grid-column: 1 / -1; border-top: 1px solid #e4e9f0; }}
          .stage-rail {{ grid-template-columns: 1fr; }}
          .stage-step {{ border-right: 0; }}
        }}
      </style>
    </head>
    <body>
      <header>
        <h1>Kubernetes MLOps Platform</h1>
        <p>Executable lifecycle and MLflow registry evidence, with separately scoped Airflow, KServe, and Kubernetes architecture labs.</p>
      </header>
      <main>
        <section class="grid">
          <div class="metric"><span>Champion model</span><strong>{esc(champion_application_version)}</strong></div>
          <div class="metric"><span>Gate status</span><strong>{badge(gate_report.get('passed', False))}</strong></div>
          <div class="metric"><span>KServe status</span><strong>{esc(deployment_state.get('status', 'not deployed'))}</strong></div>
          <div class="metric"><span>MLflow contract</span><strong>{contract_badge(mlflow_contract.get('passed'))}</strong></div>
          <div class="metric"><span>Latency p95</span><strong>{esc(monitoring_report.get('latency_ms', {}).get('p95', 'n/a'))} ms</strong></div>
          <div class="metric"><span>Observed feature drift</span><strong>{badge(monitoring_report.get('feature_drift', {}).get('passed', False))}</strong></div>
        </section>

        <section class="panel decision-lab" data-testid="canary-release-lab">
          <div class="decision-heading">
            <div><h2>Canary Release Lab</h2><p>Re-evaluate the generated Airflow, Kueue, KServe, and Prometheus release policy under live operating signals.</p></div>
            <div id="releaseDecision" class="decision-pill hold" aria-live="polite">HOLD RELEASE</div>
          </div>
          <div class="decision-grid">
            <div class="decision-controls">
              <div class="control-row"><label for="errorRate">Error rate</label><input id="errorRate" type="range" min="0" max="8" step="0.1"><output id="errorRateValue" class="control-value">0.0%</output></div>
              <div class="control-row"><label for="latencyP95">Latency p95</label><input id="latencyP95" type="range" min="0" max="120" step="0.01"><output id="latencyP95Value" class="control-value">0 ms</output></div>
              <div class="control-row"><label for="queuedJobs">Queued jobs</label><input id="queuedJobs" type="range" min="0" max="32" step="1"><output id="queuedJobsValue" class="control-value">0 jobs</output></div>
              <div class="control-row"><label for="availableSlots">Available slots</label><input id="availableSlots" type="range" min="1" max="16" step="1"><output id="availableSlotsValue" class="control-value">1 slot</output></div>
              <div class="toggle-row"><span id="offlineGatesName">Offline quality gates</span><label class="switch"><input id="offlineGates" type="checkbox" aria-labelledby="offlineGatesName offlineGatesLabel"><span class="switch-ui"></span><span id="offlineGatesLabel" class="switch-label">PASS</span></label></div>
              <div class="toggle-row"><span id="featureHealthyName">Feature drift checks</span><label class="switch"><input id="featureHealthy" type="checkbox" aria-labelledby="featureHealthyName featureHealthyLabel"><span class="switch-ui"></span><span id="featureHealthyLabel" class="switch-label">PASS</span></label></div>
            </div>
            <div>
              <div class="decision-kpis">
                <div><span>Error budget burn</span><strong id="releaseBurn">0.00x</strong></div>
                <div><span>Kueue pressure</span><strong id="releasePressure">0%</strong></div>
                <div><span>Failed checks</span><strong id="releaseFailedChecks">0 / 5</strong></div>
              </div>
              <p id="releaseReason" class="decision-reason"></p>
              <div class="stage-rail" aria-label="Release decision path">
                <div class="stage-step" data-policy-check="offline_gates"><span>Airflow</span><strong>Offline gates</strong></div>
                <div class="stage-step" data-policy-check="queue_pressure"><span>Kueue</span><strong>Reserve quota</strong></div>
                <div class="stage-step" data-policy-check="serving"><span>KServe</span><strong>Canary health</strong></div>
                <div class="stage-step" data-policy-check="error_budget_burn"><span>Prometheus</span><strong>SLO budget</strong></div>
                <div class="stage-step" data-policy-check="decision"><span>Airflow</span><strong>Release action</strong></div>
              </div>
              <div id="releaseChecks" class="check-list"></div>
            </div>
          </div>
        </section>

        <section class="layout">
          <div>
            <div class="panel">
              <h2>Evaluation Gates</h2>
              <div class="table-wrap"><table class="wide-table"><tr><th>Gate</th><th>Status</th><th>Observed</th><th>Threshold</th></tr>{rows(gate_rows, ['gate', 'status', 'observed', 'threshold'])}</table></div>
            </div>

            <div class="panel">
              <h2>KServe Deployment</h2>
              <div class="table-wrap">
                <table class="wide-table">
                  <tr><th>Service</th><th>Namespace</th><th>Runtime</th><th>Traffic</th><th>Model URI</th></tr>
                  <tr><td>{display_label(deployment_state.get('service_name'))}</td><td>{esc(deployment_state.get('namespace'))}</td><td>{display_label(deployment_state.get('runtime'))}</td><td class="traffic">{traffic_chips(deployment_state.get('traffic'))}</td><td>{short_path(deployment_state.get('model_uri'))}</td></tr>
                </table>
              </div>
            </div>

            <div class="panel">
              <h2>Recent Predictions</h2>
              <div class="table-wrap"><table class="wide-table"><tr><th>Customer</th><th>Score</th><th>Prediction</th><th>Model</th><th>Latency</th><th>Status</th></tr>{rows(prediction_rows, ['customer_id', 'churn_score', 'prediction', 'model_version', 'latency_ms', 'status'])}</table></div>
            </div>
          </div>

          <div>
            <div class="panel">
              <h2>Executable MLflow Registry</h2>
              <div class="summary-grid">
                <div class="summary-item"><span>Runtime</span><strong>{esc(mlflow_contract.get('mlflow_version', 'not run'))}</strong></div>
                <div class="summary-item"><span>Backend</span><strong>{esc(mlflow_contract.get('tracking_backend', 'not run'))}</strong></div>
                <div class="summary-item"><span>Registered model</span><strong>{esc(mlflow_contract.get('registered_model', 'not run'))}</strong></div>
                <div class="summary-item"><span>Registry versions</span><strong>{esc(len(mlflow_versions))}</strong></div>
                <div class="summary-item"><span>Champion alias</span><strong>{esc(mlflow_aliases.get('champion', 'not run'))}</strong></div>
                <div class="summary-item"><span>Previous alias</span><strong>{esc(mlflow_aliases.get('previous_champion', 'not run'))}</strong></div>
                <div class="summary-item"><span>Idempotency</span><strong>{contract_badge(mlflow_contract.get('checks', {}).get('registration_idempotency'))}</strong></div>
                <div class="summary-item"><span>Rollback parity</span><strong>{contract_badge(mlflow_contract.get('checks', {}).get('rollback_prediction_parity'))}</strong></div>
              </div>
            </div>

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
              <h2>Scheduling Gate Controller</h2>
              <div class="summary-grid">
                <div class="summary-item"><span>Mode</span><strong>{display_label(gate_controller.get('failure_mode', 'not planned'))}</strong></div>
                <div class="summary-item"><span>Leader election</span><strong>{badge(bool(gate_controller.get('leader_election')))}</strong></div>
                <div class="summary-item"><span>Pods released</span><strong>{esc(gate_controller_summary.get('pods_released', 'n/a'))}</strong></div>
                <div class="summary-item"><span>Gates removed</span><strong>{esc(gate_controller_summary.get('gates_removed', 'n/a'))}</strong></div>
                <div class="summary-item"><span>Still gated</span><strong>{esc(gate_controller_summary.get('pods_still_gated', 'n/a'))}</strong></div>
                <div class="summary-item"><span>Stale incidents</span><strong>{esc(gate_controller_summary.get('stale_incidents', 'n/a'))}</strong></div>
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
      <script>
        const releaseSimulation = {release_payload};
        const byId = (id) => document.getElementById(id);
        const inputs = releaseSimulation.initial;
        byId("errorRate").value = inputs.error_rate_pct;
        byId("latencyP95").value = inputs.latency_p95_ms;
        byId("queuedJobs").value = inputs.queued_jobs;
        byId("availableSlots").value = inputs.available_slots;
        byId("offlineGates").checked = inputs.offline_gates;
        byId("featureHealthy").checked = inputs.feature_healthy;

        function roundFour(value) {{
          return Math.round(value * 10000) / 10000;
        }}

        function evaluateReleasePolicy() {{
          const thresholds = releaseSimulation.thresholds;
          const errorRatePct = Number(byId("errorRate").value);
          const errorRate = errorRatePct / 100;
          const latency = Number(byId("latencyP95").value);
          const queued = Number(byId("queuedJobs").value);
          const slots = Number(byId("availableSlots").value);
          const burn = roundFour(errorRate / Math.max(1 - thresholds.availability_slo, 0.0001));
          const pressure = roundFour(queued / Math.max(queued + slots, 1));
          const checks = [
            {{key: "offline_gates", label: "Offline gates", passed: byId("offlineGates").checked}},
            {{key: "feature_drift", label: "Feature drift", passed: byId("featureHealthy").checked}},
            {{key: "latency_p95", label: "Latency p95", passed: latency <= thresholds.latency_p95_ms}},
            {{key: "error_budget_burn", label: "SLO burn", passed: burn <= thresholds.error_budget_burn}},
            {{key: "queue_pressure", label: "Queue pressure", passed: pressure <= thresholds.queue_pressure}},
          ];
          let action = "hold";
          if (burn >= thresholds.rollback_burn_rate || errorRate >= thresholds.rollback_error_rate) action = "rollback";
          else if (checks.every((check) => check.passed)) action = "advance_canary";
          return {{action, burn, pressure, errorRatePct, latency, queued, slots, checks}};
        }}

        function renderReleasePolicy() {{
          const result = evaluateReleasePolicy();
          byId("errorRateValue").textContent = result.errorRatePct.toFixed(1) + "%";
          byId("latencyP95Value").textContent = result.latency.toFixed(2) + " ms";
          byId("queuedJobsValue").textContent = result.queued + " jobs";
          byId("availableSlotsValue").textContent = result.slots + (result.slots === 1 ? " slot" : " slots");
          byId("offlineGatesLabel").textContent = byId("offlineGates").checked ? "PASS" : "FAIL";
          byId("featureHealthyLabel").textContent = byId("featureHealthy").checked ? "PASS" : "FAIL";
          byId("releaseBurn").textContent = result.burn.toFixed(2) + "x";
          byId("releasePressure").textContent = (result.pressure * 100).toFixed(1) + "%";
          const failed = result.checks.filter((check) => !check.passed);
          byId("releaseFailedChecks").textContent = failed.length + " / " + result.checks.length;

          const decision = byId("releaseDecision");
          decision.className = "decision-pill " + (result.action === "advance_canary" ? "advance" : result.action);
          decision.textContent = result.action === "advance_canary" ? "ADVANCE CANARY" : result.action === "rollback" ? "ROLLBACK" : "HOLD RELEASE";
          byId("releaseReason").textContent = result.action === "rollback"
            ? "Rollback threshold breached. Freeze promotion and restore the previous champion alias."
            : failed.length
              ? "Hold on " + failed.map((check) => check.label.toLowerCase()).join(", ") + "."
              : "All five controls pass. Airflow may advance the KServe canary under the recorded approval operation.";

          const passedByKey = Object.fromEntries(result.checks.map((check) => [check.key, check.passed]));
          const stageStates = {{
            offline_gates: passedByKey.offline_gates,
            queue_pressure: passedByKey.queue_pressure,
            serving: passedByKey.feature_drift && passedByKey.latency_p95,
            error_budget_burn: passedByKey.error_budget_burn,
          }};
          document.querySelectorAll("[data-policy-check]").forEach((stage) => {{
            const key = stage.dataset.policyCheck;
            if (key === "decision") stage.className = "stage-step " + (result.action === "advance_canary" ? "pass" : result.action === "rollback" ? "fail" : "hold");
            else stage.className = "stage-step " + (stageStates[key] ? "pass" : "fail");
          }});

          const checkList = byId("releaseChecks");
          checkList.replaceChildren();
          result.checks.forEach((check) => {{
            const item = document.createElement("div");
            item.className = "check-item" + (check.passed ? "" : " fail");
            const label = document.createElement("span");
            label.textContent = check.label;
            const dot = document.createElement("span");
            dot.className = "check-dot";
            item.append(label, dot);
            checkList.appendChild(item);
          }});
        }}

        ["errorRate", "latencyP95", "queuedJobs", "availableSlots", "offlineGates", "featureHealthy"].forEach((id) => byId(id).addEventListener("input", renderReleasePolicy));
        renderReleasePolicy();
      </script>
    </body>
    </html>
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    return output_path
