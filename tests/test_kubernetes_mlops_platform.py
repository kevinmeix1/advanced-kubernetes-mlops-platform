from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kube_mlops_platform.chaos import run_chaos_drill
from kube_mlops_platform.cli import demo, train
from kube_mlops_platform.control_plane import build_release_plan, evaluate_release_policy
from kube_mlops_platform.data import generate_churn_dataset, split_rows
from kube_mlops_platform.gates import evaluate_gates
from kube_mlops_platform.io import read_csv, read_json, read_jsonl, write_json
from kube_mlops_platform.model import predict_score, train_model
from kube_mlops_platform.network_security import build_network_security_report
from kube_mlops_platform.policy_audit import audit_platform_policy
from kube_mlops_platform.registry import rollback
from kube_mlops_platform.resource_optimizer import build_resource_optimization_report
from kube_mlops_platform.serving import health
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
            self.assertIn("no_latest_image_tags", report["failed_checks"])
            self.assertIn("immutable_image_digest", report["failed_checks"])
            self.assertTrue((Path(tmp) / "reports" / "policy_audit.json").exists())

    def test_trace_report_and_otel_collector_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        collector = (repo / "kubernetes" / "opentelemetry-collector.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            trace = build_trace_report(tmp)

            self.assertEqual(trace["span_count"], 5)
            self.assertEqual(trace["root_service"], "airflow")
            self.assertTrue(any(span["service"] == "kserve" for span in trace["spans"]))
            self.assertTrue((Path(tmp) / "reports" / "trace_report.json").exists())
        for expected in ["kind: ConfigMap", "otlp", "k8sattributes", "memory_limiter", "prometheus", "batch"]:
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
