from __future__ import annotations

from .data import FEATURES


REQUIRED_COLUMNS = ["customer_id", "segment", *FEATURES, "churned"]


def validate_dataset(rows: list[dict]) -> dict:
    checks = []
    row_count = len(rows)
    checks.append({"name": "row_count_min_500", "passed": row_count >= 500, "observed": row_count})
    observed = set(rows[0]) if rows else set()
    missing = sorted(set(REQUIRED_COLUMNS) - observed)
    checks.append({"name": "required_columns_present", "passed": not missing, "observed": missing})
    null_count = sum(1 for row in rows for column in REQUIRED_COLUMNS if row.get(column, "") in {"", None})
    checks.append({"name": "no_nulls_in_required_columns", "passed": null_count == 0, "observed": null_count})
    numeric_errors = 0
    for row in rows:
        for feature in FEATURES:
            try:
                float(row[feature])
            except Exception:
                numeric_errors += 1
    checks.append({"name": "numeric_features_parse", "passed": numeric_errors == 0, "observed": numeric_errors})
    target_values = {str(row.get("churned")) for row in rows}
    checks.append({"name": "binary_target", "passed": target_values <= {"0", "1"}, "observed": sorted(target_values)})
    positive_rate = sum(int(row["churned"]) for row in rows) / max(row_count, 1)
    checks.append({"name": "target_has_signal", "passed": 0.05 <= positive_rate <= 0.8, "observed": round(positive_rate, 4)})
    return {
        "suite": "great_expectations_style_training_data",
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "row_count": row_count,
    }
