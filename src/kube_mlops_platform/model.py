from __future__ import annotations

import math

from .data import FEATURES


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(min(value, 35), -35)))


def features(row: dict) -> dict[str, float]:
    return {feature: float(row[feature]) for feature in FEATURES}


def predict_score(model: dict, row: dict) -> float:
    values = features(row)
    logit = float(model["bias"])
    stats = model.get("feature_stats", {})
    means = stats.get("mean", {})
    stds = stats.get("std", {})
    for feature, weight in model["weights"].items():
        value = values[feature]
        if feature in means and feature in stds:
            value = (value - float(means[feature])) / max(float(stds[feature]), 1e-9)
        logit += float(weight) * value
    if row.get("segment") == "enterprise":
        logit += float(model.get("segment_adjustments", {}).get("enterprise", -0.25))
    return round(sigmoid(logit), 6)


def predict_label(model: dict, row: dict) -> int:
    return int(predict_score(model, row) >= float(model.get("threshold", 0.5)))


def _feature_stats(train_rows: list[dict]) -> dict:
    means = {
        feature: sum(float(row[feature]) for row in train_rows) / max(len(train_rows), 1)
        for feature in FEATURES
    }
    stds = {}
    for feature in FEATURES:
        variance = sum((float(row[feature]) - means[feature]) ** 2 for row in train_rows) / max(len(train_rows), 1)
        stds[feature] = math.sqrt(variance) or 1.0
    return {
        "mean": {feature: round(value, 6) for feature, value in means.items()},
        "std": {feature: round(value, 6) for feature, value in stds.items()},
    }


def _normalized_features(row: dict, stats: dict) -> dict[str, float]:
    return {
        feature: (float(row[feature]) - float(stats["mean"][feature])) / max(float(stats["std"][feature]), 1e-9)
        for feature in FEATURES
    }


def _select_threshold(model: dict, validation_rows: list[dict]) -> float:
    best = {"threshold": 0.5, "score": -1.0, "f1": -1.0, "accuracy": -1.0}
    for step in range(20, 61):
        threshold = step / 100
        model["threshold"] = threshold
        metrics = evaluate_model(model, validation_rows)
        score = metrics["f1"] + 0.15 * metrics["accuracy"] - 0.05 * metrics["segment_accuracy_gap"]
        if score > best["score"]:
            best = {
                "threshold": threshold,
                "score": score,
                "f1": metrics["f1"],
                "accuracy": metrics["accuracy"],
            }
    return round(best["threshold"], 2)


def train_model(train_rows: list[dict], validation_rows: list[dict] | None = None, version: str = "2026.07.0") -> dict:
    positive_rate = sum(int(row["churned"]) for row in train_rows) / max(len(train_rows), 1)
    bias = math.log(max(positive_rate, 0.001) / max(1 - positive_rate, 0.001))
    stats = _feature_stats(train_rows)
    weights = {feature: 0.0 for feature in FEATURES}
    segment_adjustments = {"enterprise": 0.0, "self_serve": 0.0}

    for epoch in range(1400):
        bias_gradient = 0.0
        weight_gradients = {feature: 0.0 for feature in FEATURES}
        segment_gradient = 0.0
        for row in train_rows:
            normalized = _normalized_features(row, stats)
            logit = bias
            logit += sum(weights[feature] * normalized[feature] for feature in FEATURES)
            logit += segment_adjustments["enterprise"] * int(row.get("segment") == "enterprise")
            error = sigmoid(logit) - int(row["churned"])
            bias_gradient += error
            segment_gradient += error * int(row.get("segment") == "enterprise")
            for feature in FEATURES:
                weight_gradients[feature] += error * normalized[feature]

        learning_rate = 0.15 / (1 + epoch / 900)
        regularization = 0.0005
        row_count = max(len(train_rows), 1)
        bias -= learning_rate * bias_gradient / row_count
        segment_adjustments["enterprise"] -= learning_rate * (
            segment_gradient / row_count + regularization * segment_adjustments["enterprise"]
        )
        for feature in FEATURES:
            weights[feature] -= learning_rate * (
                weight_gradients[feature] / row_count + regularization * weights[feature]
            )

    model = {
        "name": "kserve-churn-risk-baseline",
        "version": version,
        "bias": round(bias, 6),
        "weights": {feature: round(weight, 6) for feature, weight in weights.items()},
        "segment_adjustments": {key: round(value, 6) for key, value in segment_adjustments.items()},
        "feature_names": FEATURES,
        "feature_stats": stats,
        "threshold": 0.5,
        "training_rows": len(train_rows),
    }
    if validation_rows:
        model["threshold"] = _select_threshold(model, validation_rows)
    return model


def evaluate_model(model: dict, rows: list[dict]) -> dict:
    tp = fp = tn = fn = 0
    scores = []
    segment_correct: dict[str, int] = {}
    segment_total: dict[str, int] = {}
    for row in rows:
        label = int(row["churned"])
        score = predict_score(model, row)
        prediction = int(score >= model.get("threshold", 0.5))
        scores.append(score)
        segment = row.get("segment", "unknown")
        segment_total[segment] = segment_total.get(segment, 0) + 1
        segment_correct[segment] = segment_correct.get(segment, 0) + int(prediction == label)
        if prediction == 1 and label == 1:
            tp += 1
        elif prediction == 1 and label == 0:
            fp += 1
        elif prediction == 0 and label == 0:
            tn += 1
        else:
            fn += 1
    total = max(tp + fp + tn + fn, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    accuracy = (tp + tn) / total
    brier = sum((score - int(row["churned"])) ** 2 for score, row in zip(scores, rows)) / max(len(rows), 1)
    segment_accuracy = {
        segment: round(segment_correct[segment] / max(count, 1), 4)
        for segment, count in sorted(segment_total.items())
    }
    gap = max(segment_accuracy.values(), default=0) - min(segment_accuracy.values(), default=0)
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "brier_score": round(brier, 4),
        "mean_score": round(sum(scores) / max(len(scores), 1), 6),
        "segment_accuracy": segment_accuracy,
        "segment_accuracy_gap": round(gap, 4),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }
