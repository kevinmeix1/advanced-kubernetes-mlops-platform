from __future__ import annotations

import argparse
import json
from pathlib import Path

from .accelerator_plan import build_accelerator_capacity_plan
from .admin_access_diagnostics import build_admin_access_diagnostic_plan
from .advanced_device_sharing import build_advanced_device_sharing_plan
from .airflow_stateful_orchestration import build_airflow_stateful_orchestration_plan
from .asset_partitioning import build_asset_partitioning_plan
from .artifact_index import render_artifact_index
from .chaos import run_chaos_drill
from .cloud_migration import build_cloud_migration_plan
from .control_plane import build_release_plan
from .cohort_fair_sharing import build_cohort_fair_sharing_plan
from .control_plane_diagnostics import build_control_plane_diagnostics_plan
from .constrained_impersonation import build_constrained_impersonation_plan
from .cost_observability import build_cost_observability_report
from .dashboard import render_dashboard
from .data import generate_churn_dataset, split_rows
from .dag_bundle_versioning import build_dag_bundle_versioning_plan
from .deadline_alerts import build_deadline_alert_plan
from .disaster_recovery import build_disaster_recovery_plan
from .device_allocation import build_device_allocation_plan
from .elastic_workload import build_elastic_workload_plan
from .event_driven_assets import build_event_driven_assets_plan
from .flavor_fungibility import build_flavor_fungibility_plan
from .gates import evaluate_gates
from .gitops_release import build_gitops_plan
from .governance import build_governance_bundle
from .hpa_scale_to_zero import build_hpa_scale_to_zero_plan
from .identity import build_identity_access_report
from .indexed_job_resilience import build_indexed_job_resilience_plan
from .inplace_resize import build_inplace_resize_plan
from .inference_gateway import build_inference_gateway_plan
from .io import read_csv, read_json, write_csv, write_json
from .kserve_canary_readiness import build_kserve_canary_readiness_plan
from .kuberay_capacity import build_kuberay_capacity_plan
from .memory_qos import build_memory_qos_plan
from .model_cache import build_model_cache_plan
from .model import evaluate_model, train_model
from .monitoring import build_monitoring_report
from .multi_team_readiness import build_multi_team_readiness_plan
from .multikueue_dispatch import build_multikueue_dispatch_plan
from .network_security import build_network_security_report
from .orchestration_scorecard import build_orchestration_scorecard
from .policy_audit import audit_platform_policy
from .performance_budget import build_performance_budget_report
from .pending_workload_visibility import build_pending_workload_visibility_plan
from .pod_resource_envelopes import build_pod_resource_envelope_plan
from .provisioning_admission import build_provisioning_admission_plan
from .queue_simulator import build_queue_simulation
from .release_admission import build_release_admission_decision
from .registry import champion_metadata, promote_candidate, register_candidate, rollback as rollback_model, log_mlflow_run
from .resource_health_status import build_resource_health_status_plan
from .resource_optimizer import build_resource_optimization_report
from .runtime_security import build_runtime_security_plan
from .scheduling_gate_controller import build_scheduling_gate_controller_plan
from .semantic_telemetry import build_semantic_telemetry_plan
from .serving import deploy_local_kserve, health, predict
from .slo import build_slo_report
from .supply_chain import build_supply_chain_evidence
from .suspended_job_resources import build_suspended_job_resource_plan
from .tenancy import build_tenancy_report
from .topology_placement import build_topology_placement_plan
from .traceability import build_trace_report
from .validation import validate_dataset
from .workload_aware_scheduling import build_workload_aware_scheduling_plan


def root_path(output: str | Path) -> Path:
    return Path(output)


def train(
    output: str | Path,
    *,
    version: str = "2026.07.0",
    dataset_seed: int = 42,
) -> dict:
    root = root_path(output)
    dataset_path = generate_churn_dataset(
        root / "data" / "training.csv",
        seed=dataset_seed,
    )
    rows = read_csv(dataset_path)
    validation = validate_dataset(rows)
    write_json(root / "reports" / "data_validation.json", validation)
    splits = split_rows(rows)
    for split, split_rows_ in splits.items():
        write_csv(root / "data" / "splits" / f"{split}.csv", split_rows_)
    model = train_model(splits["train"], validation_rows=splits["validation"], version=version)
    metrics = {
        "train": evaluate_model(model, splits["train"]),
        "validation": evaluate_model(model, splits["validation"]),
        "test": evaluate_model(model, splits["test"]),
    }
    model["metrics"] = metrics["validation"]
    write_json(root / "models" / "candidate" / "model.json", model)
    write_json(root / "reports" / "metrics.json", metrics)
    run = log_mlflow_run(
        root,
        model=model,
        metrics=metrics["validation"],
        params={
            "version": version,
            "features": model["feature_names"],
            "dataset_seed": dataset_seed,
        },
        artifacts={"candidate_model": str(root / "models" / "candidate" / "model.json")},
    )
    registered = register_candidate(root, model, metrics["validation"])
    return {
        "dataset": str(dataset_path),
        "validation": validation,
        "model": model,
        "metrics": metrics,
        "mlflow_run": run,
        "registered": registered,
    }


def evaluate(output: str | Path) -> dict:
    root = root_path(output)
    if not (root / "models" / "candidate" / "model.json").exists():
        train(root)
    model = read_json(root / "models" / "candidate" / "model.json")
    validation_report = read_json(root / "reports" / "data_validation.json")
    test_rows = read_csv(root / "data" / "splits" / "test.csv")
    metrics = evaluate_model(model, test_rows)
    gate_report = evaluate_gates(metrics, validation_report, latency_ms_p95=12.0)
    write_json(root / "reports" / "gate_report.json", gate_report)
    promotion = promote_candidate(root, model["version"], gate_report)
    return {"metrics": metrics, "gate_report": gate_report, "promotion": promotion}


def deploy(output: str | Path) -> dict:
    root = root_path(output)
    if not (root / "registry" / "churn-risk" / "champion" / "model.json").exists():
        evaluate(root)
    return deploy_local_kserve(root)


def sample_payload() -> dict:
    return {
        "customer_id": "cust_live_001",
        "segment": "self_serve",
        "tenure_months": 9,
        "monthly_spend": 88.0,
        "support_tickets": 7,
        "late_payments": 3,
        "usage_drop_pct": 0.48,
    }


def predict_once(output: str | Path) -> dict:
    root = root_path(output)
    if not health(root).get("healthy"):
        deploy(root)
    response = predict(root, sample_payload())
    return {"health": health(root), "response": response}


def monitor(output: str | Path) -> dict:
    root = root_path(output)
    if not (root / "logs" / "predictions.jsonl").exists():
        predict_once(root)
    generate_churn_dataset(root / "data" / "current_scoring.csv", rows=240, seed=99, drift=True)
    report = build_monitoring_report(root)
    release_plan = build_release_plan(root)
    kserve_canary_readiness = build_kserve_canary_readiness_plan(root)
    dashboard = render_dashboard(
        root / "reports" / "mlops_platform_dashboard.html",
        validation_report=read_json(root / "reports" / "data_validation.json"),
        gate_report=read_json(root / "reports" / "gate_report.json"),
        deployment_state=read_json(root / "deployments" / "kserve_state.json"),
        monitoring_report=report,
        registry_metadata=champion_metadata(root),
        release_plan=release_plan,
        scheduling_gate_controller=build_scheduling_gate_controller_plan(root),
        kserve_canary_readiness=kserve_canary_readiness,
    )
    return {
        "monitoring": report,
        "release_plan": release_plan,
        "kserve_canary_readiness": kserve_canary_readiness,
        "dashboard": str(dashboard),
    }


def governance(output: str | Path) -> dict:
    root = root_path(output)
    if not (root / "reports" / "gate_report.json").exists():
        monitor(root)
    return build_governance_bundle(root)


def slo_report(output: str | Path) -> dict:
    root = root_path(output)
    if not (root / "reports" / "monitoring_report.json").exists():
        monitor(root)
    return build_slo_report(root)


def rollback(output: str | Path) -> dict:
    return rollback_model(root_path(output))


def demo(output: str | Path) -> dict:
    root = root_path(output)
    train_result = train(root)
    eval_result = evaluate(root)
    deploy_result = deploy(root)
    predictions = [predict(root, {**sample_payload(), "customer_id": f"cust_live_{idx:03d}", "usage_drop_pct": 0.2 + idx * 0.035}) for idx in range(1, 16)]
    monitor_result = monitor(root)
    policy_audit = audit_platform_policy(Path.cwd(), output_root=root)
    trace_report = build_trace_report(root)
    chaos_drill = run_chaos_drill(root)
    resource_optimization = build_resource_optimization_report(root)
    network_security = build_network_security_report(root)
    gitops_plan = build_gitops_plan(root)
    disaster_recovery = build_disaster_recovery_plan(root)
    governance_bundle = build_governance_bundle(root)
    slo_error_budget = build_slo_report(root)
    cloud_migration = build_cloud_migration_plan(root)
    accelerator_capacity = build_accelerator_capacity_plan(
        root,
        project="Kubernetes MLOps Platform",
        primary_workload="training, release, and batch scoring control plane",
    )
    device_allocation = build_device_allocation_plan(root)
    resource_health_status = build_resource_health_status_plan(root)
    advanced_device_sharing = build_advanced_device_sharing_plan(root)
    admin_access_diagnostics = build_admin_access_diagnostic_plan(root)
    inplace_resize = build_inplace_resize_plan(root)
    topology_placement = build_topology_placement_plan(root)
    kuberay_capacity = build_kuberay_capacity_plan(root)
    inference_gateway = build_inference_gateway_plan(root)
    semantic_telemetry = build_semantic_telemetry_plan(root)
    deadline_alerts = build_deadline_alert_plan(root)
    cost_observability = build_cost_observability_report(root)
    elastic_workload = build_elastic_workload_plan(root)
    indexed_job_resilience = build_indexed_job_resilience_plan(root)
    provisioning_admission = build_provisioning_admission_plan(root)
    multikueue_dispatch = build_multikueue_dispatch_plan(root)
    model_cache = build_model_cache_plan(root)
    dag_bundle_versioning = build_dag_bundle_versioning_plan(root)
    asset_partitioning = build_asset_partitioning_plan(root)
    airflow_stateful_orchestration = build_airflow_stateful_orchestration_plan(root)
    multi_team_readiness = build_multi_team_readiness_plan(root)
    event_driven_assets = build_event_driven_assets_plan(root)
    pod_resource_envelopes = build_pod_resource_envelope_plan(root)
    scheduling_gate_controller = build_scheduling_gate_controller_plan(root)
    cohort_fair_sharing = build_cohort_fair_sharing_plan(root)
    flavor_fungibility = build_flavor_fungibility_plan(root)
    pending_workload_visibility = build_pending_workload_visibility_plan(root)
    tenancy = build_tenancy_report(root)
    identity_access = build_identity_access_report(root)
    performance_budget = build_performance_budget_report(root)
    queue_simulation = build_queue_simulation(root)
    workload_aware_scheduling = build_workload_aware_scheduling_plan(root)
    runtime_security = build_runtime_security_plan(root)
    control_plane_diagnostics = build_control_plane_diagnostics_plan(root)
    memory_qos = build_memory_qos_plan(root)
    hpa_scale_to_zero = build_hpa_scale_to_zero_plan(root)
    suspended_job_resources = build_suspended_job_resource_plan(root)
    constrained_impersonation = build_constrained_impersonation_plan(root)
    supply_chain = build_supply_chain_evidence(
        root,
        project="Kubernetes MLOps Platform",
        artifact_name="kubernetes-mlops-demo-artifacts",
        workflow="Kubernetes MLOps CI",
        namespace="mlops",
    )
    release_admission = build_release_admission_decision(root)
    kserve_canary_readiness = build_kserve_canary_readiness_plan(root)
    artifact_index = render_artifact_index(
        root,
        title="Kubernetes MLOps Platform",
        description="Reviewer landing page for generated dashboard, governance evidence, SLOs, migration, and reliability artifacts.",
        dashboard="mlops_platform_dashboard.html",
    )
    orchestration_scorecard = build_orchestration_scorecard(root, project="Kubernetes MLOps Platform")
    return {
        "train": {"model_version": train_result["model"]["version"], "validation_passed": train_result["validation"]["passed"]},
        "evaluate": eval_result,
        "deploy": deploy_result,
        "predictions": predictions,
        "monitor": monitor_result,
        "release_plan": monitor_result["release_plan"],
        "policy_audit": policy_audit,
        "trace_report": trace_report,
        "chaos_drill": chaos_drill,
        "resource_optimization": resource_optimization,
        "network_security": network_security,
        "gitops_plan": gitops_plan,
        "disaster_recovery": disaster_recovery,
        "governance_bundle": governance_bundle,
        "slo_error_budget": slo_error_budget,
        "cloud_migration": cloud_migration,
        "accelerator_capacity": accelerator_capacity,
        "device_allocation": device_allocation,
        "resource_health_status": resource_health_status,
        "advanced_device_sharing": advanced_device_sharing,
        "admin_access_diagnostics": admin_access_diagnostics,
        "inplace_resize": inplace_resize,
        "topology_placement": topology_placement,
        "kuberay_capacity": kuberay_capacity,
        "inference_gateway": inference_gateway,
        "semantic_telemetry": semantic_telemetry,
        "deadline_alerts": deadline_alerts,
        "cost_observability": cost_observability,
        "elastic_workload": elastic_workload,
        "indexed_job_resilience": indexed_job_resilience,
        "provisioning_admission": provisioning_admission,
        "multikueue_dispatch": multikueue_dispatch,
        "model_cache": model_cache,
        "dag_bundle_versioning": dag_bundle_versioning,
        "asset_partitioning": asset_partitioning,
        "airflow_stateful_orchestration": airflow_stateful_orchestration,
        "multi_team_readiness": multi_team_readiness,
        "event_driven_assets": event_driven_assets,
        "pod_resource_envelopes": pod_resource_envelopes,
        "scheduling_gate_controller": scheduling_gate_controller,
        "cohort_fair_sharing": cohort_fair_sharing,
        "flavor_fungibility": flavor_fungibility,
        "pending_workload_visibility": pending_workload_visibility,
        "tenancy": tenancy,
        "identity_access": identity_access,
        "performance_budget": performance_budget,
        "queue_simulation": queue_simulation,
        "workload_aware_scheduling": workload_aware_scheduling,
        "runtime_security": runtime_security,
        "control_plane_diagnostics": control_plane_diagnostics,
        "memory_qos": memory_qos,
        "hpa_scale_to_zero": hpa_scale_to_zero,
        "suspended_job_resources": suspended_job_resources,
        "constrained_impersonation": constrained_impersonation,
        "release_admission": release_admission,
        "kserve_canary_readiness": kserve_canary_readiness,
        "artifact_index": str(artifact_index),
        "orchestration_scorecard": orchestration_scorecard,
        "supply_chain": supply_chain,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kubernetes-native MLOps platform")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in [
        "demo",
        "train",
        "evaluate",
        "deploy",
        "predict",
        "monitor",
        "rollback",
        "health",
        "plan-release",
        "policy-audit",
        "trace-report",
        "chaos-drill",
        "optimize-resources",
        "network-security",
        "gitops-plan",
        "dr-plan",
        "governance-bundle",
        "slo-report",
        "cloud-plan",
        "supply-chain",
        "orchestration-scorecard",
        "accelerator-plan",
        "device-plan",
        "resource-health-status",
        "advanced-device-sharing",
        "admin-access-diagnostics",
        "inplace-resize-plan",
        "topology-plan",
        "kuberay-plan",
        "inference-gateway-plan",
        "kserve-canary-readiness",
        "semantic-telemetry-plan",
        "deadline-alerts-plan",
        "cost-observability",
        "elastic-workload-plan",
        "indexed-job-resilience",
        "provisioning-admission",
        "multikueue-dispatch",
        "model-cache",
        "dag-bundle-plan",
        "asset-partitioning-plan",
        "airflow-stateful-orchestration",
        "multi-team-readiness",
        "event-driven-assets",
        "pod-resource-envelopes",
        "scheduling-gate-controller",
        "cohort-fair-sharing",
        "flavor-fungibility",
        "pending-workload-visibility",
        "tenancy-report",
        "identity-report",
        "performance-budget",
        "queue-simulation",
        "workload-aware-scheduling",
        "runtime-security",
        "control-plane-diagnostics",
        "memory-qos",
        "hpa-scale-zero",
        "suspended-job-resources",
        "constrained-impersonation",
        "release-admission",
    ]:
        cmd = sub.add_parser(command)
        cmd.add_argument("--output", default=".local")
        if command == "train":
            cmd.add_argument("--version", default="2026.07.0")
    args = parser.parse_args(argv)
    if args.command == "demo":
        print(json.dumps(demo(args.output), indent=2, sort_keys=True))
    elif args.command == "train":
        print(json.dumps(train(args.output, version=args.version), indent=2, sort_keys=True))
    elif args.command == "evaluate":
        print(json.dumps(evaluate(args.output), indent=2, sort_keys=True))
    elif args.command == "deploy":
        print(json.dumps(deploy(args.output), indent=2, sort_keys=True))
    elif args.command == "predict":
        print(json.dumps(predict_once(args.output), indent=2, sort_keys=True))
    elif args.command == "monitor":
        print(json.dumps(monitor(args.output), indent=2, sort_keys=True))
    elif args.command == "rollback":
        print(json.dumps(rollback(args.output), indent=2, sort_keys=True))
    elif args.command == "health":
        print(json.dumps(health(args.output), indent=2, sort_keys=True))
    elif args.command == "plan-release":
        print(json.dumps(build_release_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "policy-audit":
        print(json.dumps(audit_platform_policy(Path.cwd(), output_root=args.output), indent=2, sort_keys=True))
    elif args.command == "trace-report":
        print(json.dumps(build_trace_report(args.output), indent=2, sort_keys=True))
    elif args.command == "chaos-drill":
        print(json.dumps(run_chaos_drill(args.output), indent=2, sort_keys=True))
    elif args.command == "optimize-resources":
        print(json.dumps(build_resource_optimization_report(args.output), indent=2, sort_keys=True))
    elif args.command == "network-security":
        print(json.dumps(build_network_security_report(args.output), indent=2, sort_keys=True))
    elif args.command == "gitops-plan":
        print(json.dumps(build_gitops_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "dr-plan":
        print(json.dumps(build_disaster_recovery_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "governance-bundle":
        print(json.dumps(governance(args.output), indent=2, sort_keys=True))
    elif args.command == "slo-report":
        print(json.dumps(slo_report(args.output), indent=2, sort_keys=True))
    elif args.command == "cloud-plan":
        print(json.dumps(build_cloud_migration_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "supply-chain":
        print(json.dumps(build_supply_chain_evidence(args.output, project="Kubernetes MLOps Platform", artifact_name="kubernetes-mlops-demo-artifacts", workflow="Kubernetes MLOps CI", namespace="mlops"), indent=2, sort_keys=True))
    elif args.command == "orchestration-scorecard":
        print(json.dumps(build_orchestration_scorecard(args.output, project="Kubernetes MLOps Platform"), indent=2, sort_keys=True))
    elif args.command == "accelerator-plan":
        print(json.dumps(build_accelerator_capacity_plan(args.output, project="Kubernetes MLOps Platform", primary_workload="training, release, and batch scoring control plane"), indent=2, sort_keys=True))
    elif args.command == "device-plan":
        print(json.dumps(build_device_allocation_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "resource-health-status":
        print(json.dumps(build_resource_health_status_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "advanced-device-sharing":
        print(json.dumps(build_advanced_device_sharing_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "admin-access-diagnostics":
        print(json.dumps(build_admin_access_diagnostic_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "inplace-resize-plan":
        print(json.dumps(build_inplace_resize_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "topology-plan":
        print(json.dumps(build_topology_placement_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "kuberay-plan":
        print(json.dumps(build_kuberay_capacity_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "inference-gateway-plan":
        print(json.dumps(build_inference_gateway_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "kserve-canary-readiness":
        print(json.dumps(build_kserve_canary_readiness_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "semantic-telemetry-plan":
        print(json.dumps(build_semantic_telemetry_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "deadline-alerts-plan":
        print(json.dumps(build_deadline_alert_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "cost-observability":
        print(json.dumps(build_cost_observability_report(args.output), indent=2, sort_keys=True))
    elif args.command == "elastic-workload-plan":
        print(json.dumps(build_elastic_workload_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "indexed-job-resilience":
        print(json.dumps(build_indexed_job_resilience_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "provisioning-admission":
        print(json.dumps(build_provisioning_admission_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "multikueue-dispatch":
        print(json.dumps(build_multikueue_dispatch_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "model-cache":
        print(json.dumps(build_model_cache_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "dag-bundle-plan":
        print(json.dumps(build_dag_bundle_versioning_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "asset-partitioning-plan":
        print(json.dumps(build_asset_partitioning_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "airflow-stateful-orchestration":
        print(json.dumps(build_airflow_stateful_orchestration_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "multi-team-readiness":
        print(json.dumps(build_multi_team_readiness_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "event-driven-assets":
        print(json.dumps(build_event_driven_assets_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "pod-resource-envelopes":
        print(json.dumps(build_pod_resource_envelope_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "scheduling-gate-controller":
        print(json.dumps(build_scheduling_gate_controller_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "cohort-fair-sharing":
        print(json.dumps(build_cohort_fair_sharing_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "flavor-fungibility":
        print(json.dumps(build_flavor_fungibility_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "pending-workload-visibility":
        print(json.dumps(build_pending_workload_visibility_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "tenancy-report":
        print(json.dumps(build_tenancy_report(args.output), indent=2, sort_keys=True))
    elif args.command == "identity-report":
        print(json.dumps(build_identity_access_report(args.output), indent=2, sort_keys=True))
    elif args.command == "performance-budget":
        print(json.dumps(build_performance_budget_report(args.output), indent=2, sort_keys=True))
    elif args.command == "queue-simulation":
        print(json.dumps(build_queue_simulation(args.output), indent=2, sort_keys=True))
    elif args.command == "workload-aware-scheduling":
        print(json.dumps(build_workload_aware_scheduling_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "runtime-security":
        print(json.dumps(build_runtime_security_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "control-plane-diagnostics":
        print(json.dumps(build_control_plane_diagnostics_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "memory-qos":
        print(json.dumps(build_memory_qos_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "hpa-scale-zero":
        print(json.dumps(build_hpa_scale_to_zero_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "suspended-job-resources":
        print(json.dumps(build_suspended_job_resource_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "constrained-impersonation":
        print(json.dumps(build_constrained_impersonation_plan(args.output), indent=2, sort_keys=True))
    elif args.command == "release-admission":
        print(json.dumps(build_release_admission_decision(args.output), indent=2, sort_keys=True))
    return 0
