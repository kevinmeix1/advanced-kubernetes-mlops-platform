from __future__ import annotations

import argparse
import json
from pathlib import Path

from .chaos import run_chaos_drill
from .control_plane import build_release_plan
from .dashboard import render_dashboard
from .data import generate_churn_dataset, split_rows
from .gates import evaluate_gates
from .io import read_csv, read_json, write_csv, write_json
from .model import evaluate_model, train_model
from .monitoring import build_monitoring_report
from .network_security import build_network_security_report
from .policy_audit import audit_platform_policy
from .registry import champion_metadata, promote_candidate, register_candidate, rollback as rollback_model, log_mlflow_run
from .resource_optimizer import build_resource_optimization_report
from .serving import deploy_local_kserve, health, predict
from .traceability import build_trace_report
from .validation import validate_dataset


def root_path(output: str | Path) -> Path:
    return Path(output)


def train(output: str | Path, *, version: str = "2026.07.0") -> dict:
    root = root_path(output)
    dataset_path = generate_churn_dataset(root / "data" / "training.csv")
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
        params={"version": version, "features": model["feature_names"]},
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
    dashboard = render_dashboard(
        root / "reports" / "mlops_platform_dashboard.html",
        validation_report=read_json(root / "reports" / "data_validation.json"),
        gate_report=read_json(root / "reports" / "gate_report.json"),
        deployment_state=read_json(root / "deployments" / "kserve_state.json"),
        monitoring_report=report,
        registry_metadata=champion_metadata(root),
        release_plan=release_plan,
    )
    return {"monitoring": report, "release_plan": release_plan, "dashboard": str(dashboard)}


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
    return 0
