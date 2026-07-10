from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
import pandas as pd
from mlflow import MlflowClient
from mlflow.data.sources import LocalArtifactDatasetSource
from mlflow.exceptions import MlflowException
from mlflow.models import ModelSignature
from mlflow.types import ColSpec, Schema

from .data import FEATURES
from .io import read_csv
from .model import predict_score

REGISTERED_MODEL_NAME = "prod.churn-risk"
EXPERIMENT_NAME = "kubernetes-mlops-release-contract"
MODEL_CODE = Path(__file__).with_name("mlflow_churn_model.py")
MODEL_INPUTS = (*FEATURES, "segment")
MODEL_SIGNATURE = ModelSignature(
    inputs=Schema(
        [
            *[ColSpec("double", feature) for feature in FEATURES],
            ColSpec("string", "segment"),
        ]
    ),
    outputs=Schema(
        [
            ColSpec("double", "churn_score"),
            ColSpec("long", "prediction"),
        ]
    ),
)


class RegistryConflict(RuntimeError):
    pass


class PromotionRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class MLflowRegistryConfig:
    tracking_uri: str
    registry_uri: str | None = None
    experiment_name: str = EXPERIMENT_NAME
    registered_model_name: str = REGISTERED_MODEL_NAME


def local_registry_config(root: str | Path) -> MLflowRegistryConfig:
    root = Path(root).resolve()
    database = root / "mlflow" / "mlflow.db"
    database.parent.mkdir(parents=True, exist_ok=True)
    return MLflowRegistryConfig(tracking_uri=f"sqlite:///{database}")


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _configure(config: MLflowRegistryConfig) -> MlflowClient:
    mlflow.set_tracking_uri(config.tracking_uri)
    mlflow.set_registry_uri(config.registry_uri or config.tracking_uri)
    return MlflowClient(
        tracking_uri=config.tracking_uri,
        registry_uri=config.registry_uri or config.tracking_uri,
    )


def _experiment_id(
    client: MlflowClient,
    config: MLflowRegistryConfig,
    root: Path,
) -> str:
    existing = client.get_experiment_by_name(config.experiment_name)
    if existing is not None:
        return existing.experiment_id
    artifact_location = None
    if config.tracking_uri.startswith("sqlite:"):
        artifacts = (root / "mlflow" / "artifacts").resolve()
        artifacts.mkdir(parents=True, exist_ok=True)
        artifact_location = artifacts.as_uri()
    return client.create_experiment(
        config.experiment_name,
        artifact_location=artifact_location,
        tags={
            "owner": "ml-platform",
            "purpose": "release-contract",
        },
    )


def _training_frame(path: Path) -> pd.DataFrame:
    frame = pd.DataFrame(read_csv(path))
    for column in FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("float64")
    frame["churned"] = pd.to_numeric(frame["churned"], errors="raise").astype("float64")
    frame["segment"] = frame["segment"].astype("string")
    return frame


def _application_version(
    client: MlflowClient,
    *,
    registered_model_name: str,
    application_version: str,
) -> Any | None:
    versions = client.search_model_versions(f"name = '{registered_model_name}'")
    matches = [
        version
        for version in versions
        if version.tags.get("application.version") == application_version
    ]
    if len(matches) > 1:
        raise RegistryConflict(
            f"multiple registry versions claim application version {application_version}"
        )
    return matches[0] if matches else None


def _alias(client: MlflowClient, model_name: str, alias: str) -> Any | None:
    try:
        return client.get_model_version_by_alias(model_name, alias)
    except MlflowException:
        return None


def alias_state(config: MLflowRegistryConfig) -> dict[str, str | None]:
    client = _configure(config)
    return {
        alias: (
            str(version.version)
            if (version := _alias(client, config.registered_model_name, alias))
            else None
        )
        for alias in ("candidate", "champion", "previous_champion")
    }


def registry_inventory(config: MLflowRegistryConfig) -> dict[str, Any]:
    client = _configure(config)
    versions = client.search_model_versions(
        f"name = '{config.registered_model_name}'",
        order_by=["version_number ASC"],
    )
    return {
        "registered_model": config.registered_model_name,
        "aliases": alias_state(config),
        "versions": [
            {
                "registry_version": str(version.version),
                "application_version": version.tags.get("application.version"),
                "validation_status": version.tags.get("validation.status"),
                "deployment_status": version.tags.get("deployment.status"),
                "run_id": version.run_id,
                "source": version.source,
            }
            for version in versions
        ],
    }


def publish_candidate(
    root: str | Path,
    *,
    model: dict[str, Any],
    metrics: dict[str, Any],
    gate_report: dict[str, Any],
    config: MLflowRegistryConfig,
) -> dict[str, Any]:
    root = Path(root).resolve()
    client = _configure(config)
    model_digest = canonical_hash(model)
    gate_digest = canonical_hash(gate_report)
    existing = _application_version(
        client,
        registered_model_name=config.registered_model_name,
        application_version=str(model["version"]),
    )
    if existing is not None:
        if (
            existing.tags.get("artifact.sha256") != model_digest
            or existing.tags.get("gate.sha256") != gate_digest
        ):
            raise RegistryConflict(
                f"application version {model['version']} already has different evidence"
            )
        loaded = mlflow.pyfunc.load_model(existing.source)
        signature = loaded.metadata.signature
        run = client.get_run(existing.run_id)
        dataset_inputs = run.inputs.dataset_inputs
        return {
            "replayed": True,
            "application_version": str(model["version"]),
            "registry_version": str(existing.version),
            "run_id": existing.run_id,
            "model_uri": existing.source,
            "logged_model_id": existing.source.removeprefix("models:/"),
            "artifact_sha256": model_digest,
            "gate_sha256": gate_digest,
            "validation_status": existing.tags.get("validation.status"),
            "dataset_digest": (
                dataset_inputs[0].dataset.digest if dataset_inputs else None
            ),
            "signature": signature.to_dict() if signature is not None else None,
        }

    training_path = root / "data" / "splits" / "train.csv"
    model_path = root / "models" / "candidate" / "model.json"
    frame = _training_frame(training_path)
    inputs = frame[list(MODEL_INPUTS)].head(5).copy()
    dataset = mlflow.data.from_pandas(
        frame,
        source=LocalArtifactDatasetSource(training_path.as_uri()),
        name="churn-training-split",
        targets="churned",
    )
    experiment_id = _experiment_id(client, config, root)
    with mlflow.start_run(
        experiment_id=experiment_id,
        run_name=f"candidate-{model['version']}",
        tags={
            "release.workflow": "kubernetes-mlops",
            "application.version": str(model["version"]),
            "validation.status": "passed" if gate_report.get("passed") else "failed",
        },
    ) as run:
        mlflow.log_input(dataset, context="training")
        mlflow.log_params(
            {
                "application.version": str(model["version"]),
                "feature.count": len(model["feature_names"]),
                "decision.threshold": float(model.get("threshold", 0.5)),
                "training.rows": int(model["training_rows"]),
            }
        )
        mlflow.log_dict(model, "evidence/model_config.json")
        mlflow.log_dict(gate_report, "evidence/gate_report.json")
        model_info = mlflow.pyfunc.log_model(
            name="churn-risk-model",
            python_model=str(MODEL_CODE),
            artifacts={"model_config": str(model_path)},
            input_example=inputs,
            signature=MODEL_SIGNATURE,
            registered_model_name=config.registered_model_name,
            pip_requirements=["mlflow==3.14.0", "pandas==2.3.3"],
            metadata={
                "application_version": str(model["version"]),
                "artifact_sha256": model_digest,
                "feature_contract": "contracts/training_data_contract.json",
            },
        )
        numeric_metrics = {
            key: float(value)
            for key, value in metrics.items()
            if isinstance(value, (int, float))
        }
        for key, value in sorted(numeric_metrics.items()):
            mlflow.log_metric(
                f"validation.{key}",
                value,
                model_id=model_info.model_id,
                dataset=dataset,
            )

    versions = client.search_model_versions(
        f"name = '{config.registered_model_name}' AND run_id = '{run.info.run_id}'"
    )
    if len(versions) != 1:
        raise RegistryConflict(
            f"expected one registry version for run {run.info.run_id}, found {len(versions)}"
        )
    registered = versions[0]
    tags = {
        "application.version": str(model["version"]),
        "artifact.sha256": model_digest,
        "gate.sha256": gate_digest,
        "validation.status": "passed" if gate_report.get("passed") else "failed",
        "feature.contract": "training-data-v1",
        "source.run_id": run.info.run_id,
    }
    for key, value in tags.items():
        client.set_model_version_tag(
            config.registered_model_name,
            str(registered.version),
            key,
            value,
        )
    if gate_report.get("passed"):
        client.set_registered_model_alias(
            config.registered_model_name,
            "candidate",
            str(registered.version),
        )
    return {
        "replayed": False,
        "application_version": str(model["version"]),
        "registry_version": str(registered.version),
        "run_id": run.info.run_id,
        "logged_model_id": model_info.model_id,
        "model_uri": registered.source,
        "artifact_sha256": model_digest,
        "gate_sha256": gate_digest,
        "validation_status": tags["validation.status"],
        "dataset_digest": dataset.digest,
        "signature": MODEL_SIGNATURE.to_dict(),
    }


def promote_candidate(
    *,
    config: MLflowRegistryConfig,
    registry_version: str,
) -> dict[str, Any]:
    client = _configure(config)
    version = client.get_model_version(config.registered_model_name, registry_version)
    if version.tags.get("validation.status") != "passed":
        raise PromotionRejected("candidate did not pass validation gates")
    champion = _alias(client, config.registered_model_name, "champion")
    if champion is not None and str(champion.version) == str(registry_version):
        return {
            "promoted": True,
            "replayed": True,
            "champion_version": str(registry_version),
            "previous_champion_version": alias_state(config)["previous_champion"],
        }
    if champion is not None:
        client.set_registered_model_alias(
            config.registered_model_name,
            "previous_champion",
            str(champion.version),
        )
        client.set_model_version_tag(
            config.registered_model_name,
            str(champion.version),
            "deployment.status",
            "previous_champion",
        )
    client.set_registered_model_alias(
        config.registered_model_name,
        "champion",
        str(registry_version),
    )
    client.set_model_version_tag(
        config.registered_model_name,
        str(registry_version),
        "deployment.status",
        "champion",
    )
    candidate = _alias(client, config.registered_model_name, "candidate")
    if candidate is not None and str(candidate.version) == str(registry_version):
        client.delete_registered_model_alias(config.registered_model_name, "candidate")
    return {
        "promoted": True,
        "replayed": False,
        "champion_version": str(registry_version),
        "previous_champion_version": (
            str(champion.version) if champion is not None else None
        ),
    }


def rollback_champion(*, config: MLflowRegistryConfig) -> dict[str, Any]:
    client = _configure(config)
    champion = _alias(client, config.registered_model_name, "champion")
    previous = _alias(client, config.registered_model_name, "previous_champion")
    if champion is None or previous is None:
        return {"rolled_back": False, "reason": "previous_champion_unavailable"}
    client.set_registered_model_alias(
        config.registered_model_name,
        "champion",
        str(previous.version),
    )
    client.set_registered_model_alias(
        config.registered_model_name,
        "previous_champion",
        str(champion.version),
    )
    client.set_model_version_tag(
        config.registered_model_name,
        str(previous.version),
        "deployment.status",
        "champion",
    )
    client.set_model_version_tag(
        config.registered_model_name,
        str(champion.version),
        "deployment.status",
        "previous_champion",
    )
    return {
        "rolled_back": True,
        "champion_version": str(previous.version),
        "previous_champion_version": str(champion.version),
    }


def verify_champion(
    *,
    config: MLflowRegistryConfig,
    expected_model: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    _configure(config)
    model_uri = f"models:/{config.registered_model_name}@champion"
    loaded = mlflow.pyfunc.load_model(model_uri)
    frame = pd.DataFrame(
        [
            {
                **{feature: float(payload[feature]) for feature in FEATURES},
                "segment": payload["segment"],
            }
        ]
    )
    prediction = loaded.predict(frame)
    observed_score = float(prediction.iloc[0]["churn_score"])
    expected_score = float(predict_score(expected_model, payload))
    signature = loaded.metadata.signature
    pyfunc_flavor = loaded.metadata.flavors.get("python_function", {})
    return {
        "passed": abs(observed_score - expected_score) <= 1e-6,
        "model_from_code": (
            pyfunc_flavor.get("loader_module") == "mlflow.pyfunc.loaders.code_model"
        ),
        "model_uri": model_uri,
        "observed_score": observed_score,
        "expected_score": expected_score,
        "prediction": int(prediction.iloc[0]["prediction"]),
        "signature": signature.to_dict() if signature is not None else None,
    }
