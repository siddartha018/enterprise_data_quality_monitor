from enterprise_data_quality_monitor.metrics.data_quality_score import (
    compute_data_quality_score,
)


def test_data_quality_score_perfect():
    validation_results = {
        "missing": {"missing_percentage": 0.0},
        "duplicates": {"duplicate_percentage": 0.0},
        "schema": {"is_valid": True},
        "total_records": 100,
    }
    anomaly_results = {"anomaly_count": 0}

    result = compute_data_quality_score(validation_results, anomaly_results)
    assert result["score"] == 100.0


def test_data_quality_score_penalizes_missing_and_anomalies():
    validation_results = {
        "missing": {"missing_percentage": 10.0},
        "duplicates": {"duplicate_percentage": 5.0},
        "schema": {"is_valid": False},
        "total_records": 100,
    }
    anomaly_results = {"anomaly_count": 10}

    result = compute_data_quality_score(validation_results, anomaly_results)
    assert result["score"] < 100.0
