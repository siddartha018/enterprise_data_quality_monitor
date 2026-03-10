from __future__ import annotations

from typing import Dict, Literal, Optional, Tuple

import pandas as pd

from enterprise_data_quality_monitor.config.snowflake_config import SnowflakeConfig
from enterprise_data_quality_monitor.metrics.data_quality_score import (
    compute_data_quality_score,
)
from enterprise_data_quality_monitor.forecasting.simple_forecast import (
    forecast_daily_series,
)
from enterprise_data_quality_monitor.pipeline.extract_from_snowflake import (
    extract_reported_revenue_from_snowflake,
    extract_transactions_from_snowflake,
)
from enterprise_data_quality_monitor.reconciliation.revenue_reconciliation import (
    reconcile_revenue,
)
from enterprise_data_quality_monitor.utils.alerts_utils import (
    maybe_alert_on_low_score,
)
from enterprise_data_quality_monitor.utils.data_utils import (
    aggregate_daily_revenue,
    aggregate_revenue_by_region,
    aggregate_top_customers,
    aggregate_total_revenue,
    customer_daily_spend_proxy,
    customer_spend_by_country,
    customer_top_customers_by_spend,
    customer_total_spend_proxy,
    load_customer_transactions_from_csv,
    load_transactions_from_csv,
    normalize_columns,
)
from enterprise_data_quality_monitor.utils.logging_utils import get_logger
from enterprise_data_quality_monitor.validation.anomaly_detection import (
    detect_numeric_anomalies,
    detect_revenue_anomalies,
)
from enterprise_data_quality_monitor.validation.duplicate_detection import (
    detect_duplicates,
)
from enterprise_data_quality_monitor.validation.missing_values_check import (
    check_missing_values,
)
from enterprise_data_quality_monitor.validation.schema_validation import validate_schema


logger = get_logger(__name__)

KAGGLE_CUSTOMER_EXPECTED_COLUMNS: Tuple[str, ...] = (
    "customer_id",
    "age",
    "gender",
    "country",
    "annual_income",
    "spending_score",
    "num_purchases",
    "avg_purchase_value",
    "membership_years",
    "website_visits_per_month",
    "cart_abandon_rate",
    "churned",
    "feedback_text",
    "last_purchase_date",
)


def _load_transactions(
    source: Literal["csv", "snowflake"],
    csv_path: Optional[str] = None,
    snowflake_config: Optional[SnowflakeConfig] = None,
    snowflake_table: Optional[str] = None,
) -> pd.DataFrame:
    if source == "csv":
        if not csv_path:
            raise ValueError("csv_path is required when source='csv'")
        return load_transactions_from_csv(csv_path)

    if source == "snowflake":
        if not snowflake_config or not snowflake_table:
            raise ValueError(
                "snowflake_config and snowflake_table are required when source='snowflake'"
            )
        return extract_transactions_from_snowflake(snowflake_config, snowflake_table)

    raise ValueError(f"Unsupported source: {source}")


def _detect_dataset_kind(df: pd.DataFrame) -> Literal["financial_transactions", "kaggle_customer_transactions"]:
    cols = {c.strip().lower() for c in df.columns}
    if {"customer_id", "country", "num_purchases", "avg_purchase_value", "last_purchase_date"}.issubset(
        cols
    ):
        return "kaggle_customer_transactions"
    return "financial_transactions"


def _load_reported_revenue(
    source: Literal["csv", "snowflake"],
    reported_csv_path: Optional[str] = None,
    snowflake_config: Optional[SnowflakeConfig] = None,
    snowflake_summary_table: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    if source == "csv":
        if not reported_csv_path:
            return None
        df = pd.read_csv(reported_csv_path)
        return df

    if source == "snowflake":
        if not snowflake_config or not snowflake_summary_table:
            return None
        return extract_reported_revenue_from_snowflake(
            snowflake_config, snowflake_summary_table
        )

    return None


def run_pipeline(
    source: Literal["csv", "snowflake"],
    csv_path: Optional[str] = "data/financial_transactions.csv",
    reported_csv_path: Optional[str] = None,
    snowflake_config: Optional[SnowflakeConfig] = None,
    snowflake_table: Optional[str] = None,
    snowflake_summary_table: Optional[str] = None,
) -> Dict[str, object]:
    """Run the end-to-end data quality pipeline.

    Returns a dictionary containing:
    - raw_data: pandas.DataFrame
    - validation: dict
    - anomalies: dict
    - reconciliation: dict
    - data_quality_score: dict
    - analytics: dict of pandas.DataFrame
    """
    logger.info("Starting data quality pipeline", extra={"source": source})

    transactions_df = _load_transactions(
        source=source,
        csv_path=csv_path,
        snowflake_config=snowflake_config,
        snowflake_table=snowflake_table,
    )
    transactions_df = normalize_columns(transactions_df)
    total_records = int(len(transactions_df))

    dataset_kind = _detect_dataset_kind(transactions_df)

    if dataset_kind == "kaggle_customer_transactions" and source == "csv" and csv_path:
        # Re-load with strong coercions and validation for the Kaggle dataset.
        transactions_df = load_customer_transactions_from_csv(csv_path)
        total_records = int(len(transactions_df))

    if dataset_kind == "kaggle_customer_transactions":
        schema_result = validate_schema(
            transactions_df, expected_columns=KAGGLE_CUSTOMER_EXPECTED_COLUMNS
        )
        duplicates_result = detect_duplicates(transactions_df, subset_cols=["customer_id"])
        anomaly_results = detect_numeric_anomalies(
            transactions_df,
            value_column="avg_purchase_value",
            date_column="last_purchase_date",
        )
        reconciliation_result = {
            "calculated_revenue": float("nan"),
            "reported_revenue": float("nan"),
            "absolute_difference": float("nan"),
            "percentage_difference": float("nan"),
            "within_tolerance": False,
            "has_reported_data": False,
        }
        daily_spend = customer_daily_spend_proxy(transactions_df)
        daily_forecast = forecast_daily_series(
            daily_spend, date_column="date", value_column="total_revenue"
        )
        analytics = {
            "total_revenue": customer_total_spend_proxy(transactions_df),
            "daily_revenue": daily_spend,
            "revenue_by_region": customer_spend_by_country(transactions_df),
            "top_customers": customer_top_customers_by_spend(transactions_df),
            "daily_forecast": daily_forecast,
        }
    else:
        schema_result = validate_schema(
            transactions_df,
            expected_columns=("transaction_id", "date", "customer_id", "product", "revenue", "region"),
        )
        duplicates_result = detect_duplicates(transactions_df, subset_cols=["transaction_id"])
        anomaly_results = detect_revenue_anomalies(transactions_df)
        reported_df = _load_reported_revenue(
            source=source,
            reported_csv_path=reported_csv_path,
            snowflake_config=snowflake_config,
            snowflake_summary_table=snowflake_summary_table,
        )
        reconciliation_result = reconcile_revenue(transactions_df, reported_df)
        daily_revenue = aggregate_daily_revenue(transactions_df)
        daily_forecast = forecast_daily_series(
            daily_revenue, date_column="date", value_column="total_revenue"
        )
        analytics = {
            "total_revenue": aggregate_total_revenue(transactions_df),
            "daily_revenue": daily_revenue,
            "revenue_by_region": aggregate_revenue_by_region(transactions_df),
            "top_customers": aggregate_top_customers(transactions_df),
            "daily_forecast": daily_forecast,
        }

    missing_result = check_missing_values(transactions_df)

    validation_results: Dict[str, object] = {
        "schema": schema_result,
        "missing": missing_result,
        "duplicates": duplicates_result,
        "total_records": total_records,
        "dataset_kind": dataset_kind,
    }

    dq_score = compute_data_quality_score(validation_results, anomaly_results)

    # Fire alert hook if score is low. This currently logs a warning and,
    # when configured, can also send an email via SMTP.
    maybe_alert_on_low_score(float(dq_score["score"]))

    logger.info("Data quality pipeline completed successfully")

    return {
        "raw_data": transactions_df,
        "validation": validation_results,
        "anomalies": anomaly_results,
        "reconciliation": reconciliation_result,
        "data_quality_score": dq_score,
        "analytics": analytics,
    }


if __name__ == "__main__":
    results = run_pipeline(source="csv")
    print("Dataset Health Score:", results["data_quality_score"]["score"])
    print("Total Revenue:", results["analytics"]["total_revenue"])

