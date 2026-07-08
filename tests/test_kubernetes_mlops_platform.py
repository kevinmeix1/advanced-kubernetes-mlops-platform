from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kube_mlops_platform.accelerator_plan import build_accelerator_capacity_plan
from kube_mlops_platform.chaos import run_chaos_drill
from kube_mlops_platform.cloud_migration import build_cloud_migration_plan
from kube_mlops_platform.cli import demo, train
from kube_mlops_platform.control_plane import build_release_plan, evaluate_release_policy
from kube_mlops_platform.cost_observability import build_cost_observability_report
from kube_mlops_platform.data import generate_churn_dataset, split_rows
from kube_mlops_platform.deadline_alerts import build_deadline_alert_plan
from kube_mlops_platform.disaster_recovery import build_disaster_recovery_plan
from kube_mlops_platform.device_allocation import build_device_allocation_plan
from kube_mlops_platform.elastic_workload import build_elastic_workload_plan
from kube_mlops_platform.gates import evaluate_gates
from kube_mlops_platform.gitops_release import build_gitops_plan
from kube_mlops_platform.governance import build_governance_bundle
from kube_mlops_platform.identity import build_identity_access_report
from kube_mlops_platform.indexed_job_resilience import build_indexed_job_resilience_plan
from kube_mlops_platform.inference_gateway import build_inference_gateway_plan
from kube_mlops_platform.io import read_csv, read_json, read_jsonl, write_json
from kube_mlops_platform.kuberay_capacity import build_kuberay_capacity_plan
from kube_mlops_platform.model import predict_score, train_model
from kube_mlops_platform.multikueue_dispatch import build_multikueue_dispatch_plan
from kube_mlops_platform.network_security import build_network_security_report
from kube_mlops_platform.orchestration_scorecard import build_orchestration_scorecard
from kube_mlops_platform.policy_audit import audit_platform_policy
from kube_mlops_platform.performance_budget import build_performance_budget_report
from kube_mlops_platform.provisioning_admission import build_provisioning_admission_plan
from kube_mlops_platform.queue_simulator import build_queue_simulation
from kube_mlops_platform.release_admission import build_release_admission_decision, evaluate_release_admission
from kube_mlops_platform.registry import rollback
from kube_mlops_platform.resource_optimizer import build_resource_optimization_report
from kube_mlops_platform.semantic_telemetry import build_semantic_telemetry_plan
from kube_mlops_platform.serving import health
from kube_mlops_platform.slo import build_slo_report
from kube_mlops_platform.supply_chain import build_supply_chain_evidence
from kube_mlops_platform.tenancy import build_tenancy_report
from kube_mlops_platform.topology_placement import build_topology_placement_plan
from kube_mlops_platform.traceability import build_trace_report
from kube_mlops_platform.validation import validate_dataset


class KubernetesMLOpsPlatformTest(unittest.TestCase):
    def test_advanced_airflow_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        dag = repo / "airflow" / "dags" / "enterprise_kubernetes_mlops_release_dag.py"
        workloads = repo / "kubernetes" / "training-and-monitoring-workloads.yaml"

        dag_text = dag.read_text(encoding="utf-8")
        workload_text = workloads.read_text(encoding="utf-8")

        for expected in ["KubernetesPodOperator", "task_group", "BranchPythonOperator", "ShortCircuitOperator", "Asset", "expand("]:
            self.assertIn(expected, dag_text)
        for expected in ["deferrable=True", "pod_template_file", "capacity_and_slo_governance", "reserve_kueue_release_quota"]:
            self.assertIn(expected, dag_text)
        for expected in ["CronJob", "RoleBinding", "ConfigMap", "securityContext", "ttlSecondsAfterFinished", "kueue.x-k8s.io/queue-name"]:
            self.assertIn(expected, workload_text)

    def test_kubernetes_governance_and_airflow_pod_template_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        governance = (repo / "kubernetes" / "platform-governance.yaml").read_text(encoding="utf-8")
        pod_template = (repo / "kubernetes" / "airflow-kubernetes-executor-pod-template.yaml").read_text(encoding="utf-8")

        for expected in ["ResourceQuota", "LimitRange", "PriorityClass", "HTTPRoute"]:
            self.assertIn(expected, governance)
        for expected in ["initContainers", "startupProbe", "livenessProbe", "readinessProbe", "topologySpreadConstraints"]:
            self.assertIn(expected, pod_template)

    def test_kueue_admission_control_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        admission = (repo / "kubernetes" / "kueue-admission-control.yaml").read_text(encoding="utf-8")

        for expected in [
            "ResourceFlavor",
            "ClusterQueue",
            "LocalQueue",
            "WorkloadPriorityClass",
            "churn-release-queue",
            "borrowingLimit",
            "preemption",
            "kueue.x-k8s.io/queue-name",
        ]:
            self.assertIn(expected, admission)

    def test_event_driven_autoscaling_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        autoscaling = (repo / "kubernetes" / "event-driven-autoscaling.yaml").read_text(encoding="utf-8")

        for expected in ["ScaledObject", "prometheus", "fallback", "horizontalPodAutoscalerConfig", "activationThreshold"]:
            self.assertIn(expected, autoscaling)

    def test_queue_simulation_models_priority_and_preemption(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "queue-simulation-policy.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_queue_simulation(root)

            self.assertTrue(report["passed"])
            self.assertGreaterEqual(report["preempted_count"], 1)
            self.assertTrue(any(item["name"] == "emergency-rollback-validation" for item in report["simulation"]["admitted"]))
            self.assertTrue((root / "reports" / "queue_simulation.json").exists())
            self.assertIn("PriorityClass", manifest)
            self.assertIn("ChurnReleaseQueuePressureHigh", manifest)

    def test_release_admission_fails_closed_with_policy_assets(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "release-admission-policy.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root / "reports" / "slo_error_budget.json", {"max_burn_rate": 0.2, "release_freeze": False, "recommended_action": "allow_release"})
            write_json(root / "reports" / "performance_budget.json", {"passed": True, "checks": []})
            write_json(root / "reports" / "queue_simulation.json", {"passed": True, "pending_count": 0, "simulation": {"pending": []}})
            write_json(root / "reports" / "governance_evidence_bundle.json", {"release": {"decision": "approved_for_champion"}})
            write_json(root / "reports" / "supply_chain_evidence.json", {"artifact_count": 8, "subject": {"attestation_action": "actions/attest@v4"}})
            write_json(root / "reports" / "release_control_plan.json", {"recommended_action": "advance_canary"})

            decision = build_release_admission_decision(root)
            frozen = evaluate_release_admission(
                slo={"max_burn_rate": 20.0, "release_freeze": True, "recommended_action": "freeze_promotion_and_page"},
                performance={"passed": True, "checks": []},
                queue={"passed": True, "pending_count": 0, "simulation": {"pending": []}},
                governance={"release": {"decision": "approved_for_champion"}},
                supply_chain={"artifact_count": 8, "subject": {"attestation_action": "actions/attest@v4"}},
                release_plan={"recommended_action": "advance_canary"},
            )

            self.assertEqual(decision["decision"]["recommended_action"], "admit_canary")
            self.assertFalse(decision["decision"]["unsafe_allow"])
            self.assertEqual(frozen["recommended_action"], "freeze_promotion")
            self.assertTrue((root / "reports" / "release_admission_decision.json").exists())
            self.assertIn("ValidatingAdmissionPolicy", manifest)
            self.assertIn("AnalysisTemplate", manifest)
            self.assertIn("ChurnReleaseAdmissionUnsafeAllow", manifest)

    def test_performance_budget_report_and_prometheus_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "performance-budget-policy.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)
            report = build_performance_budget_report(root)
            names = {check["name"] for check in report["checks"]}

            self.assertTrue(result["performance_budget"]["passed"])
            self.assertTrue(report["passed"])
            self.assertIn("online_inference_p95_ms", names)
            self.assertIn("airflow_queue_wait_p95_seconds", names)
            self.assertTrue((root / "reports" / "performance_budget.json").exists())
            self.assertIn("PrometheusRule", manifest)
            self.assertIn("histogram_quantile", manifest)
            self.assertIn("ChurnRiskP95LatencyBudgetExceeded", manifest)

    def test_admission_policies_and_policy_audit_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        admission = (repo / "kubernetes" / "admission-policies.yaml").read_text(encoding="utf-8")

        for expected in ["ValidatingAdmissionPolicy", "ValidatingAdmissionPolicyBinding", "ImageValidatingPolicy", "slsa-provenance"]:
            self.assertIn(expected, admission)
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_platform_policy(repo, output_root=tmp)
            passed = {check["name"] for check in report["checks"] if check["passed"]}
            self.assertIn("pod_security_restricted", passed)
            self.assertIn("event_driven_scaling", passed)
            self.assertIn("immutable_image_digest", passed)
            self.assertIn("no_latest_image_tags", report["failed_checks"])
            self.assertTrue((Path(tmp) / "reports" / "policy_audit.json").exists())

    def test_trace_report_and_otel_collector_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        collector = (repo / "kubernetes" / "opentelemetry-collector.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            trace = build_trace_report(tmp)

            self.assertEqual(trace["span_count"], 5)
            self.assertEqual(trace["root_service"], "airflow")
            self.assertTrue(any(span["service"] == "kserve" for span in trace["spans"]))
            release_attrs = trace["spans"][0]["attributes"]
            self.assertEqual(release_attrs["airflow.dag_id"], "enterprise_kubernetes_mlops_release")
            self.assertTrue(any(span["attributes"].get("kserve.inferenceservice.name") == "churn-risk" for span in trace["spans"]))
            self.assertTrue(any(span["attributes"].get("ml.model.version") == "2026.07.0" for span in trace["spans"]))
            self.assertTrue((Path(tmp) / "reports" / "trace_report.json").exists())
        for expected in ["kind: ConfigMap", "otlp", "k8sattributes", "memory_limiter", "attributes/semantic_redaction", "prediction.request.features", "customer.id", "prometheus", "batch"]:
            self.assertIn(expected, collector)

    def test_chaos_drill_and_chaos_mesh_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        chaos_manifest = (repo / "kubernetes" / "chaos-experiments.yaml").read_text(encoding="utf-8")

        for expected in ["PodChaos", "NetworkChaos", "StressChaos", "Schedule", "concurrencyPolicy: Forbid", "churn-risk-pod-kill"]:
            self.assertIn(expected, chaos_manifest)
        with tempfile.TemporaryDirectory() as tmp:
            report = run_chaos_drill(tmp)

            self.assertTrue(report["passed"])
            self.assertEqual(report["scenario_count"], 3)
            self.assertTrue(any(scenario["fault"] == "NetworkChaos" for scenario in report["scenarios"]))
            self.assertTrue((Path(tmp) / "reports" / "chaos_drill_report.json").exists())

    def test_resource_optimization_and_autoscaling_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        optimization = (repo / "kubernetes" / "resource-optimization.yaml").read_text(encoding="utf-8")

        for expected in ["VerticalPodAutoscaler", "HorizontalPodAutoscaler", "PrometheusRule", "airflow-capacity-pools", "stabilizationWindowSeconds: 300"]:
            self.assertIn(expected, optimization)
        with tempfile.TemporaryDirectory() as tmp:
            report = build_resource_optimization_report(tmp)

            self.assertEqual(report["summary"]["workload_count"], 3)
            self.assertIn("VPA in Off mode", report["guardrails"][0])
            self.assertTrue(any("prewarm_replicas" in item["actions"] for item in report["recommendations"]))
            self.assertTrue((Path(tmp) / "reports" / "resource_optimization.json").exists())

    def test_network_security_topology_and_manifests_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        network_security = (repo / "kubernetes" / "network-security.yaml").read_text(encoding="utf-8")

        for expected in ["kind: NetworkPolicy", "default-deny-all", "PeerAuthentication", "mode: STRICT", "AuthorizationPolicy"]:
            self.assertIn(expected, network_security)
        with tempfile.TemporaryDirectory() as tmp:
            report = build_network_security_report(tmp)

            self.assertEqual(report["mtls_mode"], "STRICT")
            self.assertEqual(report["allowed_flow_count"], 3)
            self.assertTrue(any(flow["destination"] == "mlflow-registry" for flow in report["allowed_flows"]))
            self.assertTrue((Path(tmp) / "reports" / "network_security.json").exists())

    def test_gitops_plan_and_progressive_delivery_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        gitops = (repo / "gitops" / "gitops-promotion.yaml").read_text(encoding="utf-8")

        for expected in ["kind: Application", "kind: AppProject", "AnalysisTemplate", "Rollout", "argocd.argoproj.io/sync-wave"]:
            self.assertIn(expected, gitops)
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_gitops_plan(tmp)

            self.assertEqual(plan["deployment_controller"], "Argo CD")
            self.assertEqual(plan["sync_waves"][0]["wave"], -3)
            self.assertTrue(any(stage["environment"] == "prod" and stage["sync"] == "manual" for stage in plan["promotion_stages"]))
            self.assertTrue((Path(tmp) / "reports" / "gitops_plan.json").exists())

    def test_disaster_recovery_plan_and_backup_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        dr = (repo / "kubernetes" / "disaster-recovery.yaml").read_text(encoding="utf-8")

        for expected in ["kind: Schedule", "BackupStorageLocation", "VolumeSnapshotClass", "restore-order"]:
            self.assertIn(expected, dr)
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_disaster_recovery_plan(tmp)

            self.assertLessEqual(plan["rpo_minutes"], 30)
            self.assertEqual(plan["restore_sequence"][0]["asset"], "namespace and CRDs")
            self.assertTrue(any(item["asset"] == "MLflow registry and artifacts" for item in plan["restore_sequence"]))
            self.assertTrue((Path(tmp) / "reports" / "disaster_recovery_plan.json").exists())

    def test_governance_evidence_bundle_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        governance = (repo / "kubernetes" / "governance-evidence.yaml").read_text(encoding="utf-8")

        for expected in ["kind: ConfigMap", "kind: Job", "model-card", "risk-register", "reproducibility-manifest"]:
            self.assertIn(expected, governance)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)
            bundle = build_governance_bundle(root)
            model_card = read_json(root / "governance" / "model_card.json")
            manifest = read_json(root / "governance" / "reproducibility_manifest.json")

            self.assertEqual(result["governance_bundle"]["release"]["decision"], "approved_for_champion")
            self.assertEqual(bundle["framework_alignment"]["nist_ai_rmf"], ["Govern", "Map", "Measure", "Manage"])
            self.assertEqual(model_card["name"], "kserve-churn-risk-baseline")
            self.assertTrue(any(item["exists"] and len(item["sha256"]) == 64 for item in manifest["artifact_hashes"]))
            self.assertTrue((root / "reports" / "governance_evidence_bundle.json").exists())

    def test_slo_error_budget_report_and_alert_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        alerts = (repo / "kubernetes" / "slo-alerts.yaml").read_text(encoding="utf-8")

        for expected in ["PrometheusRule", "SLOBurnRateHigh", "multiwindow", "error-budget-freeze"]:
            self.assertIn(expected, alerts)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)
            report = build_slo_report(root)

            self.assertIn(result["slo_error_budget"]["recommended_action"], {"freeze_promotion_and_page", "hold_canary_and_open_incident"})
            self.assertEqual(report["slos"][0]["name"], "online_inference_availability")
            self.assertTrue(any(item["name"] == "feature_drift_clean_window" for item in report["slos"]))
            self.assertTrue((root / "reports" / "slo_error_budget.json").exists())

    def test_cloud_migration_plan_and_infra_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        nodepools = (repo / "kubernetes" / "cloud-nodepools.yaml").read_text(encoding="utf-8")
        terraform = (repo / "infra" / "terraform" / "aws" / "main.tf").read_text(encoding="utf-8")

        for expected in ["NodePool", "EC2NodeClass", "WhenEmptyOrUnderutilized"]:
            self.assertIn(expected, nodepools)
        for expected in ["cluster_compute_config", "node_pools", "aws_s3_bucket"]:
            self.assertIn(expected, terraform)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)
            plan = build_cloud_migration_plan(root)

            self.assertEqual(result["cloud_migration"]["primary_target"], "AWS EKS Auto Mode")
            self.assertEqual(plan["managed_service_mapping"]["serving"], "KServe Standard mode on EKS with Gateway API")
            self.assertTrue((root / "reports" / "cloud_migration_plan.json").exists())

    def test_ci_workflow_uploads_artifacts_and_validates_outputs(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        workflow = (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        makefile = (repo / "Makefile").read_text(encoding="utf-8")

        for expected in ["actions/upload-artifact@v6", "actions/attest@v4", "attestations: write", "GITHUB_STEP_SUMMARY", "make ci-verify", "concurrency"]:
            self.assertIn(expected, workflow)
        for expected in ["ci-verify:", "index.html", "tenancy_fairness_report.json", "identity_access_report.json", "multikueue_dispatch_plan.json", "provisioning_admission_plan.json", "indexed_job_resilience_plan.json", "elastic_workload_plan.json", "cost_observability_report.json", "deadline_alert_plan.json", "semantic_telemetry_plan.json", "inference_gateway_plan.json", "kuberay_capacity_plan.json", "topology_placement_plan.json", "device_allocation_plan.json", "release_admission_decision.json", "queue_simulation.json", "performance_budget.json", "accelerator_capacity_plan.json", "orchestration_scorecard.json", "supply_chain_evidence.json", "governance_evidence_bundle.json", "cloud_migration_plan.json"]:
            self.assertIn(expected, makefile)

    def test_accelerator_capacity_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "accelerator-scheduling.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = build_accelerator_capacity_plan(root, project="Kubernetes MLOps Platform", primary_workload="training")

            self.assertEqual(len(plan["profiles"]), 3)
            self.assertIn("gpu-a100-mig", {profile["kueue_flavor"] for profile in plan["profiles"]})
            self.assertTrue((root / "reports" / "accelerator_capacity_plan.json").exists())
            self.assertIn("ResourceFlavor", manifest)
            self.assertIn("ResourceClaimTemplate", manifest)
            self.assertIn("nvidia.com/mig-1g.10gb", manifest)

    def test_device_allocation_plan_and_dra_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "dynamic-resource-allocation.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "dynamic-resource-allocation.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_device_allocation_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "admit_dra_backed_canary")
            self.assertTrue((root / "reports" / "device_allocation_plan.json").exists())
            self.assertTrue(any(workload["resource_claim_template"] == "l4-shared-canary" for workload in report["workloads"]))
        for expected in ["DeviceClass", "ResourceClaimTemplate", "kueue.x-k8s.io/queue-name", "kube_resourceclaim_status_phase"]:
            self.assertIn(expected, manifest)
        for expected in ["Dynamic Resource Allocation", "time-slicing", "MIG", "ResourceClaim"]:
            self.assertIn(expected, docs)

    def test_topology_placement_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "topology-aware-scheduling.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "topology-aware-scheduling.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_topology_placement_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_topology_aware_release_training")
            self.assertTrue((root / "reports" / "topology_placement_plan.json").exists())
            self.assertTrue(any(workload["placement"] == "compact" for workload in report["workloads"]))
        for expected in ["kind: Topology", "topologyName", "AdmissionCheck", "kueue.x-k8s.io/podset-required-topology", "topologySpreadConstraints", "KueueTopologyAssignmentDelayed"]:
            self.assertIn(expected, manifest)
        for expected in ["Topology-Aware Scheduling", "topology spread constraints", "ResourceFlavor", "AdmissionChecks"]:
            self.assertIn(expected, docs)

    def test_kuberay_capacity_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "kuberay-kueue-workloads.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "kuberay-kueue.md").read_text(encoding="utf-8")
        dag = (repo / "airflow" / "dags" / "enterprise_kubernetes_mlops_release_dag.py").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_kuberay_capacity_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_kuberay_release_analysis")
            self.assertTrue((root / "reports" / "kuberay_capacity_plan.json").exists())
            self.assertGreaterEqual(report["capacity"]["max_workers"], 24)
        for expected in ["RayJob", "enableInTreeAutoscaling", "kueue.x-k8s.io/elastic-job", "churn-canary-analysis", "ChurnRayWorkersPending"]:
            self.assertIn(expected, manifest)
        for expected in ["KubeRay", "Kueue", "elastic worker", "Airflow"]:
            self.assertIn(expected, docs)
        for expected in ["submit_kuberay_canary_analysis", "wait_for_kuberay_canary_analysis_deferrable", "rayjob/churn-canary-analysis"]:
            self.assertIn(expected, dag)

    def test_elastic_workload_plan_and_jobset_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "kueue-elastic-workloads.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "kueue-elastic-workloads.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_elastic_workload_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_kueue_elastic_release_slices")
            self.assertEqual(report["feature_gate"], "ElasticJobsViaWorkloadSlices")
            self.assertTrue(any(item["replacement_for"] for item in report["workload_slices"]))
            self.assertTrue((root / "reports" / "elastic_workload_plan.json").exists())
        for expected in ["JobSet", "workload-slice-name", "workload-slice-replacement-for", "ChurnElasticWorkloadSlicePending"]:
            self.assertIn(expected, manifest)
        for expected in ["Elastic Workloads", "Workload Slices", "JobSet", "rollback"]:
            self.assertIn(expected, docs)

    def test_indexed_job_resilience_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "indexed-job-resilience.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "indexed-job-resilience.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_indexed_job_resilience_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_indexed_release_job_resilience")
            self.assertEqual(report["kubernetes_job"]["completion_mode"], "Indexed")
            self.assertEqual(report["retry_policy"]["backoff_limit_per_index"], 1)
            self.assertTrue(any(item["stage"] == "rollback_smoke" for item in report["release_shards"]))
            self.assertTrue((root / "reports" / "indexed_job_resilience_plan.json").exists())
        for expected in ["completionMode: Indexed", "backoffLimitPerIndex", "maxFailedIndexes", "successPolicy", "podFailurePolicy", "JOB_COMPLETION_INDEX", "ChurnIndexedJobFailedIndexesHigh"]:
            self.assertIn(expected, manifest)
        for expected in ["Indexed Job Resilience", "Airflow Backfill Create", "successPolicy", "podFailurePolicy", "backoffLimitPerIndex"]:
            self.assertIn(expected, docs)

    def test_provisioning_admission_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "provisioning-admission-checks.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "provisioning-admission.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_provisioning_admission_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_kueue_provisioning_admission_for_release")
            self.assertTrue(report["release_policy"]["promotion_requires_capacity_evidence"])
            self.assertTrue(any(check["name"] == "release_gates_wait_for_capacity" for check in report["checks"]))
            self.assertTrue((root / "reports" / "provisioning_admission_plan.json").exists())
        for expected in ["AdmissionCheck", "ProvisioningRequestConfig", "kueue.x-k8s.io/provisioning-request", "admissionChecksStrategy", "check-capacity.autoscaling.x-k8s.io", "podSetUpdates", "MLOpsProvisioningAdmissionPendingTooLong"]:
            self.assertIn(expected, manifest)
        for expected in ["Kueue Provisioning Admission", "ProvisioningRequest", "Cluster Autoscaler", "release"]:
            self.assertIn(expected, docs)

    def test_multikueue_dispatch_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "multikueue-dispatch.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "multikueue-dispatch.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_multikueue_dispatch_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_multikueue_release_dispatch")
            self.assertTrue(report["release_policy"]["promotion_requires_dispatch_evidence"])
            self.assertEqual(report["dispatch_policy"]["controller_name"], "kueue.x-k8s.io/multikueue")
            self.assertIn("status.clusterName", report["dispatch_policy"]["status_fields"])
            self.assertEqual(report["manager_quota"]["nvidia_com_gpu"], 6)
            self.assertTrue(any(check["name"] == "release_gates_wait_for_dispatch" for check in report["checks"]))
            self.assertTrue((root / "reports" / "multikueue_dispatch_plan.json").exists())
        for expected in ["MultiKueueConfig", "MultiKueueCluster", "kueue.x-k8s.io/multikueue", "admissionChecksStrategy", "promotionPolicy", "kueue.x-k8s.io/prebuilt-workload-name", "MLOpsMultiKueueDispatchStalled"]:
            self.assertIn(expected, manifest)
        for expected in ["MultiKueue Dispatch", "candidate", "status.clusterName", "champion"]:
            self.assertIn(expected, docs)

    def test_inference_gateway_plan_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "inference-gateway-routing.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "inference-gateway.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_inference_gateway_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_inference_gateway_for_release_routes")
            self.assertEqual(report["pool"]["api_version"], "inference.networking.k8s.io/v1")
            self.assertTrue((root / "reports" / "inference_gateway_plan.json").exists())
        for expected in ["InferencePool", "InferenceObjective", "endpointPickerRef", "FailOpen", "HTTPRoute", "ChurnEndpointPickerUnavailable"]:
            self.assertIn(expected, manifest)
        for expected in ["Gateway API Inference Extension", "InferencePool", "Endpoint Picker", "InferenceObjective"]:
            self.assertIn(expected, docs)

    def test_semantic_telemetry_plan_and_collector_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        collector = (repo / "kubernetes" / "opentelemetry-collector.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "semantic-telemetry.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_semantic_telemetry_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enforce_release_telemetry_contract")
            self.assertIn("kserve.inferenceservice.name", report["schema"]["required_attributes"])
            self.assertIn("prediction.request.features", report["schema"]["redacted_attributes"])
            self.assertTrue((root / "reports" / "semantic_telemetry_plan.json").exists())
        for expected in ["attributes/semantic_redaction", "telemetry.contract.name", "prediction.response.score", "customer.id"]:
            self.assertIn(expected, collector)
        for expected in ["Semantic Telemetry", "MLflow", "KServe", "payload"]:
            self.assertIn(expected, docs)

    def test_airflow_deadline_alert_plan_and_docs_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        docs = (repo / "docs" / "airflow-deadline-alerts.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_deadline_alert_plan(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_airflow3_release_deadline_alerts")
            self.assertEqual(report["runtime_config"]["AIRFLOW__CALLBACKS__CALLBACK_EXECUTION_TIMEOUT"], "300")
            self.assertTrue(any(policy["name"] == "canary_readiness" for policy in report["deadline_policies"]))
            self.assertTrue((root / "reports" / "deadline_alert_plan.json").exists())
        for expected in ["Deadline Alerts", "legacy Airflow 2 SLA", "MLflow", "rollback"]:
            self.assertIn(expected, docs)

    def test_cost_observability_report_and_opencost_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "opencost-finops.yaml").read_text(encoding="utf-8")
        docs = (repo / "docs" / "cost-observability.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_cost_observability_report(root)

            self.assertTrue(report["passed"])
            self.assertEqual(report["recommended_action"], "enable_opencost_finops_guardrails")
            self.assertIn("node_gpu_hourly_cost", report["required_metrics"])
            self.assertTrue(any(item["workload"] == "kuberay-canary-analysis" for item in report["workload_budgets"]))
            self.assertTrue((root / "reports" / "cost_observability_report.json").exists())
        for expected in ["PrometheusRule", "opencost", "MLOpsMonthlyCostBudgetExceeded", "MLOpsIdleGpuCostWaste", "label_cost_center"]:
            self.assertIn(expected, manifest)
        for expected in ["OpenCost", "ResourceQuota", "LimitRange", "GPU"]:
            self.assertIn(expected, docs)

    def test_tenancy_fairness_report_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "multitenancy-fairness.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_tenancy_report(root)
            tenant_names = {tenant["name"] for tenant in report["tenants"]}

            self.assertTrue(report["passed"])
            self.assertIn("release-critical", tenant_names)
            self.assertIn("mlops-shared-cohort", report["fairness"]["cohort"])
            self.assertTrue((root / "reports" / "tenancy_fairness_report.json").exists())
            for expected in ["ResourceQuota", "LimitRange", "RoleBinding", "NetworkPolicy", "Cohort", "ClusterQueue", "airflow-tenant-pools"]:
                self.assertIn(expected, manifest)

    def test_identity_access_report_and_kubernetes_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        manifest = (repo / "kubernetes" / "workload-identity.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = build_identity_access_report(root)
            service_accounts = {identity["service_account"] for identity in report["identities"]}

            self.assertTrue(report["passed"])
            self.assertIn("airflow-release-runner", service_accounts)
            self.assertTrue((root / "reports" / "identity_access_report.json").exists())
            for expected in ["ServiceAccount", "automountServiceAccountToken: false", "SecretStore", "ExternalSecret", "refreshInterval: 30m", "eks.amazonaws.com/role-arn", "spiffe.io/spiffe-id", "airflow-workload-identity-policy"]:
                self.assertIn(expected, manifest)

    def test_orchestration_scorecard_covers_advanced_controls(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scorecard = build_orchestration_scorecard(root, repo_root=repo, project="Kubernetes MLOps Platform")
            names = {check["name"] for check in scorecard["checks"] if check["passed"]}

            self.assertTrue(scorecard["passed"])
            self.assertGreaterEqual(scorecard["score"], 90.0)
            self.assertIn("dynamic_task_mapping", names)
            self.assertIn("kueue_admission", names)
            self.assertIn("semantic_telemetry_contract", names)
            self.assertIn("airflow_deadline_alerts", names)
            self.assertIn("opencost_finops", names)
            self.assertIn("kueue_elastic_workloads", names)
            self.assertIn("indexed_job_resilience", names)
            self.assertIn("provisioning_admission_checks", names)
            self.assertIn("multikueue_dispatch", names)
            self.assertIn("supply_chain_provenance", names)
            self.assertTrue((root / "reports" / "orchestration_scorecard.json").exists())

    def test_supply_chain_evidence_and_policy_assets_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        policy = (repo / "kubernetes" / "supply-chain-policy.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root / "reports" / "demo.json", {"status": "ok"})
            evidence = build_supply_chain_evidence(
                root,
                project="Kubernetes MLOps Platform",
                artifact_name="kubernetes-mlops-demo-artifacts",
                workflow="Kubernetes MLOps CI",
                namespace="mlops",
            )

            self.assertEqual(evidence["artifact_count"], 1)
            self.assertEqual(len(evidence["artifacts"][0]["sha256"]), 64)
            self.assertEqual(evidence["subject"]["attestation_action"], "actions/attest@v4")
            self.assertTrue((root / "supply-chain" / "subject.checksums.txt").exists())
            self.assertIn("ClusterImagePolicy", policy)
            self.assertIn("predicateType: https://slsa.dev/provenance/v1", policy)
            self.assertIn("policy.sigstore.dev/include", policy)

    def test_artifact_index_links_key_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)
            index = (root / "reports" / "index.html").read_text(encoding="utf-8")

            self.assertTrue(result["artifact_index"].endswith("index.html"))
            for expected in [
                "mlops_platform_dashboard.html",
                "governance_evidence_bundle.json",
                "slo_error_budget.json",
                "accelerator_capacity_plan.json",
                "device_allocation_plan.json",
                "topology_placement_plan.json",
                "kuberay_capacity_plan.json",
                "inference_gateway_plan.json",
                "semantic_telemetry_plan.json",
                "deadline_alert_plan.json",
                "cost_observability_report.json",
                "elastic_workload_plan.json",
                "indexed_job_resilience_plan.json",
                "provisioning_admission_plan.json",
                "multikueue_dispatch_plan.json",
                "tenancy_fairness_report.json",
                "identity_access_report.json",
                "performance_budget.json",
                "queue_simulation.json",
                "release_admission_decision.json",
                "resource_optimization.json",
                "network_security.json",
                "chaos_drill_report.json",
                "gitops_plan.json",
                "orchestration_scorecard.json",
                "supply_chain_evidence.json",
                "cloud_migration_plan.json",
            ]:
                self.assertIn(expected, index)

    def test_release_control_plane_advances_and_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root / "reports" / "gate_report.json", {"passed": True})
            write_json(
                root / "reports" / "monitoring_report.json",
                {"latency_ms": {"p95": 18.0}, "error_rate": 0.0, "feature_drift": {"passed": True}},
            )

            plan = build_release_plan(root, queued_jobs=1, available_slots=8)
            rollback_policy = evaluate_release_policy(
                {"passed": True},
                {"latency_ms": {"p95": 18.0}, "error_rate": 0.06, "feature_drift": {"passed": True}},
                {"queued_jobs": 1, "available_slots": 8},
            )

            self.assertEqual(plan["recommended_action"], "advance_canary")
            self.assertEqual(plan["stages"][1]["system"], "kueue")
            self.assertTrue((root / "reports" / "release_control_plan.json").exists())
            self.assertEqual(rollback_policy["action"], "rollback")

    def test_demo_promotes_champion_and_writes_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = demo(root)

            self.assertTrue(result["evaluate"]["gate_report"]["passed"])
            self.assertTrue(result["evaluate"]["promotion"]["promoted"])
            self.assertEqual(health(root)["status"], "Ready")
            self.assertTrue((root / "reports" / "mlops_platform_dashboard.html").exists())
            self.assertTrue((root / "reports" / "index.html").exists())
            self.assertTrue((root / "reports" / "accelerator_capacity_plan.json").exists())
            self.assertTrue((root / "reports" / "device_allocation_plan.json").exists())
            self.assertTrue((root / "reports" / "topology_placement_plan.json").exists())
            self.assertTrue((root / "reports" / "kuberay_capacity_plan.json").exists())
            self.assertTrue((root / "reports" / "inference_gateway_plan.json").exists())
            self.assertTrue((root / "reports" / "semantic_telemetry_plan.json").exists())
            self.assertTrue((root / "reports" / "deadline_alert_plan.json").exists())
            self.assertTrue((root / "reports" / "cost_observability_report.json").exists())
            self.assertTrue((root / "reports" / "elastic_workload_plan.json").exists())
            self.assertTrue((root / "reports" / "indexed_job_resilience_plan.json").exists())
            self.assertTrue((root / "reports" / "multikueue_dispatch_plan.json").exists())
            self.assertTrue((root / "reports" / "tenancy_fairness_report.json").exists())
            self.assertTrue((root / "reports" / "identity_access_report.json").exists())
            self.assertTrue((root / "reports" / "performance_budget.json").exists())
            self.assertTrue((root / "reports" / "queue_simulation.json").exists())
            self.assertTrue((root / "reports" / "release_admission_decision.json").exists())
            self.assertTrue((root / "reports" / "orchestration_scorecard.json").exists())
            self.assertTrue((root / "reports" / "supply_chain_evidence.json").exists())
            self.assertGreaterEqual(len(read_jsonl(root / "logs" / "predictions.jsonl")), 15)

            monitoring = read_json(root / "reports" / "monitoring_report.json")
            self.assertIn("latency_ms", monitoring)
            self.assertIn("feature_drift", monitoring)
            self.assertEqual(monitoring["model_version"], "2026.07.0")

    def test_evaluation_gates_reject_low_quality_model(self) -> None:
        validation_report = {"passed": True, "row_count": 900}
        metrics = {
            "accuracy": 0.52,
            "f1": 0.18,
            "brier_score": 0.42,
            "segment_accuracy_gap": 0.3,
        }

        gate_report = evaluate_gates(metrics, validation_report, latency_ms_p95=120.0)

        self.assertFalse(gate_report["passed"])
        failing = {check["name"] for check in gate_report["checks"] if not check["passed"]}
        self.assertEqual(
            failing,
            {"min_accuracy", "min_f1", "max_brier_score", "segment_accuracy_gap", "latency_gate_p95_ms"},
        )

    def test_training_validation_and_risk_ordering_are_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dataset = generate_churn_dataset(Path(tmp) / "training.csv")
            rows = read_csv(dataset)
            splits = split_rows(rows)
            validation = validate_dataset(rows)
            model = train_model(splits["train"], validation_rows=splits["validation"], version="test.1")

            low_risk = {
                "customer_id": "low",
                "segment": "enterprise",
                "tenure_months": 42,
                "monthly_spend": 520.0,
                "support_tickets": 1,
                "late_payments": 0,
                "usage_drop_pct": 0.03,
            }
            high_risk = {
                "customer_id": "high",
                "segment": "self_serve",
                "tenure_months": 6,
                "monthly_spend": 70.0,
                "support_tickets": 8,
                "late_payments": 4,
                "usage_drop_pct": 0.62,
            }

            self.assertTrue(validation["passed"])
            self.assertEqual(model["version"], "test.1")
            self.assertLess(predict_score(model, low_risk), predict_score(model, high_risk))

    def test_rollback_is_safe_without_previous_champion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            train(root, version="only-model")

            result = rollback(root)

            self.assertFalse(result["rolled_back"])
            self.assertEqual(result["reason"], "no_previous_champion")


if __name__ == "__main__":
    unittest.main()
