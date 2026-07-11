from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import mlflow

from kube_mlops_platform.cli import deploy, evaluate, monitor, predict_once, sample_payload, train
from kube_mlops_platform.dashboard import render_dashboard
from kube_mlops_platform.io import read_json, write_json
from kube_mlops_platform.mlflow_runtime import (
    MLflowRegistryConfig,
    PromotionRejected,
    RegistryConflict,
    alias_state,
    local_registry_config,
    promote_candidate,
    publish_candidate,
    registry_inventory,
    rollback_champion,
    verify_champion,
)


def run_contract(root: Path, tracking_uri: str | None) -> dict:
    config = (
        MLflowRegistryConfig(tracking_uri=tracking_uri)
        if tracking_uri
        else local_registry_config(root)
    )

    first_training = train(root, version="2026.07.0")
    first_evaluation = evaluate(root)
    first = publish_candidate(
        root,
        model=first_training["model"],
        metrics=first_evaluation["metrics"],
        gate_report=first_evaluation["gate_report"],
        config=config,
    )
    first_promotion = promote_candidate(
        config=config,
        registry_version=first["registry_version"],
    )

    second_training = train(root, version="2026.07.1", dataset_seed=46)
    second_evaluation = evaluate(root)
    second = publish_candidate(
        root,
        model=second_training["model"],
        metrics=second_evaluation["metrics"],
        gate_report=second_evaluation["gate_report"],
        config=config,
    )
    replay = publish_candidate(
        root,
        model=second_training["model"],
        metrics=second_evaluation["metrics"],
        gate_report=second_evaluation["gate_report"],
        config=config,
    )

    conflicting_model = copy.deepcopy(second_training["model"])
    conflicting_model["bias"] = float(conflicting_model["bias"]) + 0.01
    conflict_detected = False
    try:
        publish_candidate(
            root,
            model=conflicting_model,
            metrics=second_evaluation["metrics"],
            gate_report=second_evaluation["gate_report"],
            config=config,
        )
    except RegistryConflict:
        conflict_detected = True

    second_promotion = promote_candidate(
        config=config,
        registry_version=second["registry_version"],
    )
    champion_verified = verify_champion(
        config=config,
        expected_model=second_training["model"],
        payload=sample_payload(),
    )
    rollback = rollback_champion(config=config)
    rollback_verified = verify_champion(
        config=config,
        expected_model=first_training["model"],
        payload=sample_payload(),
    )
    restored = promote_candidate(
        config=config,
        registry_version=second["registry_version"],
    )
    restored_verified = verify_champion(
        config=config,
        expected_model=second_training["model"],
        payload=sample_payload(),
    )

    rejected_model = copy.deepcopy(second_training["model"])
    rejected_model["version"] = "2026.07.rejected"
    rejected_gates = copy.deepcopy(second_evaluation["gate_report"])
    rejected_gates["passed"] = False
    rejected_gates["checks"][0]["passed"] = False
    rejected = publish_candidate(
        root,
        model=rejected_model,
        metrics=second_evaluation["metrics"],
        gate_report=rejected_gates,
        config=config,
    )
    rejected_promotion_blocked = False
    try:
        promote_candidate(
            config=config,
            registry_version=rejected["registry_version"],
        )
    except PromotionRejected:
        rejected_promotion_blocked = True

    final_aliases = alias_state(config)
    inventory = registry_inventory(config)
    checks = {
        "database_backed_registry": config.tracking_uri.startswith(("sqlite:", "http")),
        "model_signature": bool(second.get("signature")),
        "dataset_lineage": bool(second.get("dataset_digest")),
        "model_from_code": bool(champion_verified["model_from_code"]),
        "registration_idempotency": bool(replay["replayed"]),
        "registration_conflict_detection": conflict_detected,
        "gate_enforced_promotion": rejected_promotion_blocked,
        "champion_prediction_parity": bool(champion_verified["passed"]),
        "rollback_prediction_parity": bool(rollback_verified["passed"]),
        "rollback_changes_serving_behavior": (
            abs(
                champion_verified["observed_score"]
                - rollback_verified["observed_score"]
            )
            > 1e-6
        ),
        "champion_restored": (
            final_aliases["champion"] == second["registry_version"]
        ),
        "restored_prediction_parity": bool(restored_verified["passed"]),
        "previous_champion_retained": (
            final_aliases["previous_champion"] == first["registry_version"]
        ),
    }
    report = {
        "passed": all(checks.values()),
        "mlflow_version": mlflow.__version__,
        "tracking_backend": (
            "remote-http" if config.tracking_uri.startswith("http") else "local-sqlite"
        ),
        "experiment": config.experiment_name,
        "registered_model": config.registered_model_name,
        "checks": checks,
        "first_candidate": first,
        "first_promotion": first_promotion,
        "second_candidate": second,
        "second_promotion": second_promotion,
        "registration_replay": replay,
        "champion_verification": champion_verified,
        "rollback": rollback,
        "rollback_verification": rollback_verified,
        "restored_promotion": restored,
        "restored_verification": restored_verified,
        "rejected_candidate": rejected,
        "aliases": final_aliases,
        "inventory": inventory,
    }
    deploy(root)
    predict_once(root)
    monitor_result = monitor(root)
    dashboard = render_dashboard(
        root / "reports" / "mlops_platform_dashboard.html",
        validation_report=read_json(root / "reports" / "data_validation.json"),
        gate_report=read_json(root / "reports" / "gate_report.json"),
        deployment_state=read_json(root / "deployments" / "kserve_state.json"),
        monitoring_report=monitor_result["monitoring"],
        registry_metadata=read_json(
            root / "registry" / "churn-risk" / "champion" / "metadata.json"
        ),
        release_plan=monitor_result["release_plan"],
        mlflow_contract=report,
    )
    report["dashboard"] = str(dashboard)
    path = write_json(root / "reports" / "mlflow_registry_contract.json", report)
    return {**report, "report_path": str(path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exercise the real MLflow registry contract")
    parser.add_argument("--output", default=".local")
    parser.add_argument("--tracking-uri")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_contract(Path(args.output), args.tracking_uri)
    print(
        json.dumps(
            {
                "contract_passed": report["passed"],
                "mlflow_version": report["mlflow_version"],
                "tracking_backend": report["tracking_backend"],
                "registered_model": report["registered_model"],
                "aliases": report["aliases"],
                "version_count": len(report["inventory"]["versions"]),
                "dashboard": report["dashboard"],
                "report": report["report_path"],
            },
            indent=2,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
