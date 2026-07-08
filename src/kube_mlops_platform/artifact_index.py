from __future__ import annotations

import html
from pathlib import Path


def _escape(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _breakable(value: object) -> str:
    escaped = _escape(value)
    return escaped.replace("/", "/<wbr>").replace("_", "_<wbr>").replace("-", "-<wbr>")


def render_artifact_index(root: str | Path, *, title: str, description: str, dashboard: str) -> Path:
    root = Path(root)
    cards = [
        ("Executive Dashboard", dashboard, "HTML control-room view for model health, release state, and monitoring signals."),
        ("Governance Evidence", "governance_evidence_bundle.json", "Model card, data card, approval record, risk register, and reproducibility hashes."),
        ("SLO Error Budget", "slo_error_budget.json", "Availability, latency, and quality SLO burn-rate evidence for release decisions."),
        ("Supply Chain Evidence", "supply_chain_evidence.json", "Artifact hashes, GitHub attestations, SLSA provenance, and Sigstore policy controls."),
        ("Cloud Migration Plan", "cloud_migration_plan.json", "AWS, Snowflake, and Databricks migration notes with cost and operational trade-offs."),
        ("Disaster Recovery Plan", "disaster_recovery_plan.json", "Backup, restore, failover, and replay plan aligned with Kubernetes recovery patterns."),
        ("Policy Audit", "policy_audit.json", "Security and platform policy checks for manifests, supply chain, and runtime posture."),
        ("Accelerator Plan", "accelerator_capacity_plan.json", "GPU, DRA, Kueue, MIG, and time-slicing plan for accelerator-aware workloads."),
        ("Device Allocation", "device_allocation_plan.json", "DRA ResourceClaim templates, Kueue coupling, fallback paths, and device-health guardrails."),
        ("Resource Health Status", "resource_health_status_plan.json", "Kubernetes v1.36 DRA device health, Pod allocatedResourcesStatus, ResourceClaim status.devices, and DeviceTaintRule quarantine."),
        ("Advanced Device Sharing", "advanced_device_sharing_plan.json", "DRA prioritized alternatives, partitionable devices, consumable capacity, and binding-condition readiness."),
        ("AdminAccess Diagnostics", "admin_access_diagnostics_plan.json", "Kubernetes v1.36 DRA AdminAccess diagnostics with namespace isolation, RBAC, cleanup, and incident evidence."),
        ("In-Place Resize", "inplace_resize_plan.json", "Kubernetes in-place Pod resize, pod-level resource resizing, resizePolicy, VPA InPlaceOrRecreate, and resize-status alerts."),
        ("Topology Placement", "topology_placement_plan.json", "Kueue topology-aware placement, serving spread constraints, and topology fallback policy."),
        ("KubeRay Capacity", "kuberay_capacity_plan.json", "Kueue-admitted RayJobs, elastic worker bounds, release-analysis fanout, and fallback policy."),
        ("Inference Gateway", "inference_gateway_plan.json", "Gateway API Inference Extension pool, endpoint picker fallback, route priority, and canary routing signals."),
        ("Semantic Telemetry", "semantic_telemetry_plan.json", "Release, MLflow, KServe, Kubernetes, and SLO attributes with prediction payload redaction."),
        ("Deadline Alerts", "deadline_alert_plan.json", "Airflow 3 release queue, registration, canary readiness, and rollback deadline policies."),
        ("Cost Observability", "cost_observability_report.json", "OpenCost exporter, allocation labels, GPU spend, namespace budgets, and idle-cost alerts."),
        ("Elastic Workloads", "elastic_workload_plan.json", "Kueue Workload Slices, JobSet elastic release training, replacement scoring slices, and rollback quota recovery."),
        ("Indexed Job Resilience", "indexed_job_resilience_plan.json", "Kubernetes Indexed Jobs, per-index retries, success policy, pod failure policy, and bounded Airflow release backfills."),
        ("Provisioning Admission", "provisioning_admission_plan.json", "Kueue ProvisioningRequest capacity checks for release training, scoring, canary analysis, and rollback smoke."),
        ("MultiKueue Dispatch", "multikueue_dispatch_plan.json", "Kueue MultiKueue release dispatch, worker status sync, candidate freeze, and rollback-smoke protection."),
        ("Model Cache", "model_cache_plan.json", "KServe LocalModel cache, modelcar OCI artifacts, promotion cache gates, and rollback preloading."),
        ("DAG Bundle Versioning", "dag_bundle_versioning_plan.json", "Airflow 3 GitDagBundle versioning, rerun semantics, backfill policy, and incident replay guardrails."),
        ("Asset Partitioning", "asset_partitioning_plan.json", "Airflow 3.2 partitioned assets, partition-aware release DAGs, scheduler-managed partition backfills, and partition-key lineage."),
        ("Multi-Team Readiness", "multi_team_readiness_plan.json", "Airflow multi-team preview readiness for team-owned DAG Bundles, pools, triggerers, secrets, executors, and asset filtering."),
        ("Event-Driven Assets", "event_driven_assets_plan.json", "Airflow 3 AssetWatchers, BaseEventTrigger contracts, shared-stream polling, and conditional release asset expressions."),
        ("Pod Resource Envelopes", "pod_resource_envelope_plan.json", "Kubernetes pod-level resources, scheduling gates, DRA fit checks, and scheduler-churn observability."),
        ("Cohort Fair Sharing", "cohort_fair_sharing_plan.json", "Kueue Fair Sharing, Admission Fair Sharing, borrowing/lending limits, weights, and preemption guardrails."),
        ("Flavor Fungibility", "flavor_fungibility_plan.json", "Kueue ResourceFlavor fallback, TryNextFlavor policies, explicit borrowing/preemption preference, and spot/on-demand trade-offs."),
        ("Pending Workload Visibility", "pending_workload_visibility_plan.json", "Kueue VisibilityOnDemand, pending workload RBAC, queue triage endpoints, APF setup, and admission-wait alerts."),
        ("Performance Budget", "performance_budget.json", "Latency, training, queueing, artifact-size, and accuracy gates with remediation actions."),
        ("Queue Simulation", "queue_simulation.json", "Kueue quota, Airflow pool, priority, preemption, and pending workload simulation."),
        ("Workload-Aware Scheduling", "workload_aware_scheduling_plan.json", "Kubernetes v1.36 Workload/PodGroup readiness for atomic release jobs, topology constraints, DRA sharing, and workload-aware preemption."),
        ("Release Admission", "release_admission_decision.json", "Fail-closed decision record combining SLOs, provenance, queues, governance, and rollout state."),
        ("Tenant Fairness", "tenancy_fairness_report.json", "Namespace quotas, Kueue cohorts, Airflow pools, cost labels, and noisy-neighbor controls."),
        ("Workload Identity", "identity_access_report.json", "Projected tokens, External Secrets, SPIFFE IDs, and Airflow task service accounts."),
        ("Resource Optimization", "resource_optimization.json", "Rightsizing recommendations for requests, limits, HPA, VPA, and Kueue admission."),
        ("Network Security", "network_security.json", "mTLS, network policy, and service-to-service access topology for the platform."),
        ("Chaos Drill", "chaos_drill_report.json", "Failure injection scenarios with blast radius, controls, and recovery objectives."),
        ("GitOps Plan", "gitops_plan.json", "Promotion waves, rollback commands, and release gates for GitOps-controlled deployment."),
        ("Orchestration Scorecard", "orchestration_scorecard.json", "Automated scan of advanced Airflow, Kubernetes, lineage, and security controls."),
    ]
    card_html = "\n".join(
        f"""
        <a class="card" href="{_escape(href)}">
          <span class="label">{_escape(label)}</span>
          <strong>{_breakable(href)}</strong>
          <small>{_escape(summary)}</small>
        </a>"""
        for label, href, summary in cards
    )
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(title)} Evidence Index</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f9fc;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #5b6578;
      --line: #d9e0ec;
      --accent: #136f63;
      --accent-soft: #e4f4ef;
      --shadow: 0 18px 45px rgba(30, 44, 70, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.55;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 48px 24px 56px;
    }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 28px;
      align-items: end;
      padding-bottom: 28px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: clamp(2rem, 4vw, 4rem);
      line-height: 1;
      letter-spacing: 0;
    }}
    p {{ margin: 0; color: var(--muted); max-width: 760px; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 36px;
      padding: 0 14px;
      border: 1px solid #a7d8cc;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.82rem;
      font-weight: 800;
      text-transform: uppercase;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      margin-top: 28px;
    }}
    .card {{
      display: flex;
      min-height: 178px;
      flex-direction: column;
      justify-content: space-between;
      gap: 18px;
      padding: 22px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: var(--shadow);
      color: inherit;
      text-decoration: none;
    }}
    .card:hover {{ border-color: #7abeb2; transform: translateY(-1px); }}
    .label {{ color: var(--accent); font-size: 0.78rem; font-weight: 800; text-transform: uppercase; }}
    strong {{ font-size: 0.96rem; line-height: 1.3; overflow-wrap: break-word; }}
    small {{ color: var(--muted); font-size: 0.9rem; }}
    footer {{ margin-top: 28px; color: var(--muted); font-size: 0.9rem; }}
    @media (max-width: 880px) {{
      header {{ grid-template-columns: 1fr; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>{_escape(title)}</h1>
        <p>{_escape(description)}</p>
      </div>
      <span class="badge">Demo Evidence</span>
    </header>
    <section class="grid" aria-label="Generated artifacts">
      {card_html}
    </section>
    <footer>Generated by the local demo command. Open the dashboard first, then inspect the JSON evidence behind each operational claim.</footer>
  </main>
</body>
</html>
"""
    output = root / "reports" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    return output
