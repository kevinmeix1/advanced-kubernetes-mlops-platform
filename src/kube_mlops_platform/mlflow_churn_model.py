from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import mlflow
import pandas as pd


class ChurnRiskModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context: Any) -> None:
        config_path = Path(context.artifacts["model_config"])
        self.config = json.loads(config_path.read_text(encoding="utf-8"))

    def predict(
        self,
        context: Any,
        model_input: pd.DataFrame,
        params: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        del context, params
        scores: list[float] = []
        predictions: list[int] = []
        threshold = float(self.config.get("threshold", 0.5))
        for _, row in model_input.iterrows():
            logit = float(self.config["bias"])
            for feature, weight in self.config["weights"].items():
                value = float(row[feature])
                mean = float(self.config["feature_stats"]["mean"][feature])
                std = max(float(self.config["feature_stats"]["std"][feature]), 1e-9)
                logit += float(weight) * ((value - mean) / std)
            if row.get("segment") == "enterprise":
                logit += float(
                    self.config.get("segment_adjustments", {}).get("enterprise", 0)
                )
            score = 1 / (1 + math.exp(-max(min(logit, 35), -35)))
            scores.append(score)
            predictions.append(int(score >= threshold))
        return pd.DataFrame(
            {
                "churn_score": scores,
                "prediction": predictions,
            }
        )


mlflow.models.set_model(ChurnRiskModel())
