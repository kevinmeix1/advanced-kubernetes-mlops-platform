from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .io import read_json, write_json


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_mlflow_run(root: str | Path, *, model: dict, metrics: dict, params: dict, artifacts: dict) -> dict:
    root = Path(root)
    run_id = str(uuid.uuid4())
    run_dir = root / "mlruns" / "churn-risk" / run_id
    payload = {
        "run_id": run_id,
        "experiment_name": "churn-risk",
        "started_at": utc_iso(),
        "ended_at": utc_iso(),
        "params": params,
        "metrics": metrics,
        "artifacts": artifacts,
        "model_version": model["version"],
    }
    write_json(run_dir / "run.json", payload)
    write_json(run_dir / "model.json", model)
    write_json(run_dir / "metrics.json", metrics)
    return payload


def register_candidate(root: str | Path, model: dict, metrics: dict, gate_report: dict | None = None) -> dict:
    root = Path(root)
    target = root / "registry" / "churn-risk" / model["version"]
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / "model.json", model)
    metadata = {
        "model_name": model["name"],
        "version": model["version"],
        "stage": "candidate",
        "metrics": metrics,
        "gate_report": gate_report or {},
        "registered_at": utc_iso(),
        "model_path": str(target / "model.json"),
    }
    write_json(target / "metadata.json", metadata)
    return metadata


def promote_candidate(root: str | Path, version: str, gate_report: dict) -> dict:
    root = Path(root)
    version_dir = root / "registry" / "churn-risk" / version
    champion_dir = root / "registry" / "churn-risk" / "champion"
    previous_dir = root / "registry" / "churn-risk" / "previous_champion"
    metadata = read_json(version_dir / "metadata.json")
    metadata["gate_report"] = gate_report
    write_json(version_dir / "metadata.json", metadata)
    if not gate_report.get("passed"):
        return {"promoted": False, "reason": "evaluation_gates_failed", "version": version}
    if champion_dir.exists():
        if previous_dir.exists():
            shutil.rmtree(previous_dir)
        shutil.copytree(champion_dir, previous_dir)
    if champion_dir.exists():
        shutil.rmtree(champion_dir)
    shutil.copytree(version_dir, champion_dir)
    metadata["stage"] = "champion"
    metadata["promoted_at"] = utc_iso()
    write_json(champion_dir / "metadata.json", metadata)
    return {"promoted": True, "version": version, "champion_path": str(champion_dir / "model.json")}


def champion_model(root: str | Path) -> dict:
    return read_json(Path(root) / "registry" / "churn-risk" / "champion" / "model.json")


def champion_metadata(root: str | Path) -> dict:
    return read_json(Path(root) / "registry" / "churn-risk" / "champion" / "metadata.json")


def rollback(root: str | Path) -> dict:
    root = Path(root)
    champion_dir = root / "registry" / "churn-risk" / "champion"
    previous_dir = root / "registry" / "churn-risk" / "previous_champion"
    if not previous_dir.exists():
        return {"rolled_back": False, "reason": "no_previous_champion"}
    temp_dir = root / "registry" / "churn-risk" / "_rollback_tmp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    shutil.move(str(champion_dir), str(temp_dir))
    shutil.move(str(previous_dir), str(champion_dir))
    shutil.move(str(temp_dir), str(previous_dir))
    metadata = champion_metadata(root)
    metadata["rolled_back_at"] = utc_iso()
    write_json(champion_dir / "metadata.json", metadata)
    return {"rolled_back": True, "champion_version": metadata["version"], "model_path": str(champion_dir / "model.json")}
