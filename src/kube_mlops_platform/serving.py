from __future__ import annotations

import time
from pathlib import Path

from .io import append_jsonl, read_json, write_json
from .model import predict_label, predict_score
from .registry import champion_metadata, champion_model


def deploy_local_kserve(root: str | Path) -> dict:
    root = Path(root)
    metadata = champion_metadata(root)
    state = {
        "service_name": "churn-risk-predictor",
        "namespace": "mlops",
        "runtime": "kserve-sklearnserver",
        "status": "Ready",
        "traffic": {"champion": 100, "challenger": 0},
        "model_version": metadata["version"],
        "model_uri": metadata["model_path"],
        "inference_service_manifest": "kserve/inferenceservice.yaml",
    }
    write_json(root / "deployments" / "kserve_state.json", state)
    return state


def health(root: str | Path) -> dict:
    root = Path(root)
    state_path = root / "deployments" / "kserve_state.json"
    if not state_path.exists():
        return {"healthy": False, "reason": "not_deployed"}
    state = read_json(state_path)
    return {"healthy": state.get("status") == "Ready", **state}


def predict(root: str | Path, payload: dict) -> dict:
    root = Path(root)
    started = time.perf_counter()
    model = champion_model(root)
    score = predict_score(model, payload)
    label = predict_label(model, payload)
    latency_ms = round((time.perf_counter() - started) * 1000, 4)
    response = {
        "customer_id": payload.get("customer_id", "adhoc"),
        "model_version": model["version"],
        "churn_score": score,
        "prediction": label,
        "latency_ms": latency_ms,
        "status": "success",
    }
    append_jsonl(root / "logs" / "predictions.jsonl", {**response, "features": payload})
    return response
