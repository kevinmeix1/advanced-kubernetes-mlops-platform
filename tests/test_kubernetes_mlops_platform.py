from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kube_mlops_platform.cli import demo, train
from kube_mlops_platform.data import generate_churn_dataset, split_rows
from kube_mlops_platform.gates import evaluate_gates
from kube_mlops_platform.io import read_csv, read_json, read_jsonl
from kube_mlops_platform.model import predict_score, train_model
from kube_mlops_platform.registry import rollback
from kube_mlops_platform.serving import health
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
        for expected in ["CronJob", "RoleBinding", "ConfigMap", "securityContext", "ttlSecondsAfterFinished"]:
            self.assertIn(expected, workload_text)

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
