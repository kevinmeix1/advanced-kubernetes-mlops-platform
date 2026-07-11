from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from tools.smoke_mlflow_registry import run_contract

    MLFLOW_RUNTIME_AVAILABLE = True
except ImportError:
    run_contract = None
    MLFLOW_RUNTIME_AVAILABLE = False


@unittest.skipUnless(
    MLFLOW_RUNTIME_AVAILABLE,
    "MLflow runtime dependencies are not installed",
)
class MLflowRegistryIntegrationTest(unittest.TestCase):
    def test_prometheus_exporter_runtime_is_installed(self) -> None:
        from prometheus_flask_exporter.multiprocess import (
            GunicornInternalPrometheusMetrics,
        )

        self.assertIsNotNone(GunicornInternalPrometheusMetrics)

    def test_database_registry_aliases_idempotency_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = run_contract(root, None)

            self.assertTrue(report["passed"], report["checks"])
            self.assertEqual(report["mlflow_version"], "3.14.0")
            self.assertEqual(report["tracking_backend"], "local-sqlite")
            self.assertEqual(len(report["inventory"]["versions"]), 3)
            self.assertEqual(
                report["aliases"]["champion"],
                report["second_candidate"]["registry_version"],
            )
            self.assertEqual(
                report["aliases"]["previous_champion"],
                report["first_candidate"]["registry_version"],
            )
            self.assertNotEqual(
                report["champion_verification"]["observed_score"],
                report["rollback_verification"]["observed_score"],
            )
            self.assertTrue(report["champion_verification"]["model_from_code"])
            self.assertIsNotNone(report["second_candidate"]["logged_model_id"])

            replay = run_contract(root, None)
            self.assertTrue(replay["passed"], replay["checks"])
            self.assertTrue(replay["first_candidate"]["replayed"])
            self.assertTrue(replay["second_candidate"]["replayed"])
            self.assertTrue(replay["rejected_candidate"]["replayed"])
            self.assertEqual(len(replay["inventory"]["versions"]), 3)


if __name__ == "__main__":
    unittest.main()
