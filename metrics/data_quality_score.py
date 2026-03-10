from __future__ import annotations

from typing import Dict


def compute_data_quality_score(
    validation_results: Dict[str, object],
    anomaly_results: Dict[str, object],
) -> Dict[str, object]:
    """Compute an overall data quality score (0-100).

    The score is derived from:
    - missing values percentage
    - duplicate rows percentage
    - schema validity
    - anomaly count (relative to dataset size)

    The scoring strategy is intentionally simple and transparent:
    - Start from 100 points.
    - Subtract:
      - up to 20 points for missing values (linear with missing %).
      - up to 15 points for duplicates (linear with duplicate %).
      - 20 points if schema is invalid.
      - up to 25 points for anomalies (capped).
    """
    missing_pct = float(
        validation_results.get("missing", {}).get("missing_percentage", 0.0)
    )
    duplicate_pct = float(
        validation_results.get("duplicates", {}).get("duplicate_percentage", 0.0)
    )
    schema_valid = bool(
        validation_results.get("schema", {}).get("is_valid", False)
    )
    anomaly_count = int(anomaly_results.get("anomaly_count", 0))
    total_records = int(validation_results.get("total_records", 0))

    # Missing values penalty: up to 20 points.
    missing_penalty = min(missing_pct, 100.0) * 0.2

    # Duplicates penalty: up to 15 points.
    duplicate_penalty = min(duplicate_pct, 100.0) * 0.15

    # Schema penalty: 0 or 20.
    schema_penalty = 0.0 if schema_valid else 20.0

    # Anomaly penalty: relative to dataset size, up to 25.
    if total_records > 0:
        anomaly_ratio = anomaly_count / total_records
    else:
        anomaly_ratio = 0.0
    anomaly_penalty = min(anomaly_ratio * 100.0 * 0.25, 25.0)

    score = 100.0 - (
        missing_penalty + duplicate_penalty + schema_penalty + anomaly_penalty
    )
    score = max(0.0, min(100.0, score))

    return {
        "score": round(score, 2),
        "components": {
            "missing_percentage": round(missing_pct, 2),
            "duplicate_percentage": round(duplicate_pct, 2),
            "schema_valid": schema_valid,
            "anomaly_count": anomaly_count,
            "total_records": total_records,
        },
        "penalties": {
            "missing_penalty": round(missing_penalty, 2),
            "duplicate_penalty": round(duplicate_penalty, 2),
            "schema_penalty": round(schema_penalty, 2),
            "anomaly_penalty": round(anomaly_penalty, 2),
        },
    }

