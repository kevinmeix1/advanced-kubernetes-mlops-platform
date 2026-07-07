from __future__ import annotations

import random
from pathlib import Path

from .io import write_csv


FEATURES = ["tenure_months", "monthly_spend", "support_tickets", "late_payments", "usage_drop_pct"]


def sigmoid(value: float) -> float:
    import math

    return 1 / (1 + math.exp(-value))


def generate_churn_dataset(path: str | Path, rows: int = 900, seed: int = 42, drift: bool = False) -> Path:
    rng = random.Random(seed)
    records = []
    for idx in range(rows):
        segment = "enterprise" if rng.random() < 0.32 else "self_serve"
        tenure = max(1, int(rng.gauss(30 if segment == "enterprise" else 18, 10)))
        spend = max(20, rng.gauss(420 if segment == "enterprise" else 95, 55))
        if drift:
            spend *= 1.12
        tickets = max(0, int(rng.gauss(2.2 if segment == "enterprise" else 4.2, 1.6)))
        late_payments = max(0, int(rng.gauss(0.7 if segment == "enterprise" else 1.8, 1.1)))
        usage_drop = min(max(rng.gauss(0.18, 0.18), 0), 0.9)
        logit = (
            -1.8
            - 0.025 * tenure
            + 0.24 * tickets
            + 0.70 * late_payments
            + 4.8 * usage_drop
            - (0.35 if segment == "enterprise" else 0)
            + rng.gauss(0, 0.25)
        )
        churn_probability = sigmoid(logit)
        churned = 1 if rng.random() < churn_probability else 0
        records.append(
            {
                "customer_id": f"cust_{idx:05d}",
                "segment": segment,
                "tenure_months": tenure,
                "monthly_spend": round(spend, 2),
                "support_tickets": tickets,
                "late_payments": late_payments,
                "usage_drop_pct": round(usage_drop, 4),
                "churned": churned,
            }
        )
    return write_csv(path, records)


def split_rows(rows: list[dict], seed: int = 7) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    n = len(shuffled)
    train_end = int(n * 0.68)
    validation_end = int(n * 0.84)
    return {
        "train": shuffled[:train_end],
        "validation": shuffled[train_end:validation_end],
        "test": shuffled[validation_end:],
    }
