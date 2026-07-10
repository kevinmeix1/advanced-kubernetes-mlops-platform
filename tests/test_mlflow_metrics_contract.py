from __future__ import annotations

import unittest

from tools.smoke_mlflow_metrics import evaluate_metrics


class MLflowMetricsContractTest(unittest.TestCase):
    def test_accepts_mlflow_exporter_identity(self) -> None:
        body = """\
# HELP mlflow_exporter_info Information about the Prometheus Flask exporter
# TYPE mlflow_exporter_info gauge
mlflow_exporter_info{version="0.23.2"} 1.0
"""

        checks, sample = evaluate_metrics(
            body,
            "text/plain; version=0.0.4; charset=utf-8",
            "0.23.2",
        )

        self.assertTrue(all(checks.values()), checks)
        self.assertEqual(
            sample,
            'mlflow_exporter_info{version="0.23.2"} 1.0',
        )

    def test_rejects_incidental_process_metrics(self) -> None:
        body = """\
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 1.2
"""

        checks, sample = evaluate_metrics(body, "text/plain", "0.23.2")

        self.assertIsNone(sample)
        self.assertFalse(checks["exporter_help_declared"])
        self.assertFalse(checks["exporter_type_declared"])
        self.assertFalse(checks["pinned_exporter_reported"])


if __name__ == "__main__":
    unittest.main()
