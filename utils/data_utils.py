from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

from enterprise_data_quality_monitor.utils.logging_utils import get_logger


logger = get_logger(__name__)


REQUIRED_COLUMNS: Tuple[str, ...] = (
    "transaction_id",
    "date",
    "customer_id",
    "product",
    "revenue",
    "region",
)


def _looks_like_kaggle_customer_transactions(df: pd.DataFrame) -> bool:
    expected = {
        "customer_id",
        "country",
        "num_purchases",
        "avg_purchase_value",
        "last_purchase_date",
    }
    cols = {c.strip().lower() for c in df.columns}
    return expected.issubset(cols)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names (strip + lowercase) for consistent access."""
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    return out


def ensure_required_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    """Ensure all required columns are present in the DataFrame."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    extra = [col for col in df.columns if col not in REQUIRED_COLUMNS]
    if missing:
        logger.warning("Missing required columns: %s", missing)
    if extra:
        logger.info("Extra columns present: %s", extra)
    return {"missing_columns": missing, "extra_columns": extra}


def coerce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce common dtypes for the transactions dataset."""
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "revenue" in df.columns:
        df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    return df


def load_transactions_from_csv(path: str) -> pd.DataFrame:
    """Load transactions from CSV with basic schema enforcement."""
    logger.info("Loading transactions from CSV: %s", path)
    df = pd.read_csv(path)
    df = normalize_columns(df)
    schema_info = ensure_required_columns(df)
    if schema_info["missing_columns"]:
        logger.error("CSV is missing required columns: %s", schema_info["missing_columns"])
        # Still return the DataFrame; validation layer will treat as failure.
    df = coerce_dtypes(df)
    return df


def load_customer_transactions_from_csv(path: str) -> pd.DataFrame:
    """Load Kaggle 'Customer_Transactions.csv' style dataset."""
    logger.info("Loading customer transactions from CSV: %s", path)
    df = pd.read_csv(path)
    df = normalize_columns(df)
    if not _looks_like_kaggle_customer_transactions(df):
        raise ValueError(
            "CSV does not look like the Kaggle Customer Transactions dataset. "
            "Expected columns include: customer_id, country, num_purchases, "
            "avg_purchase_value, last_purchase_date."
        )
    # Coerce key types used by pipeline
    df["last_purchase_date"] = pd.to_datetime(df["last_purchase_date"], errors="coerce")
    df["num_purchases"] = pd.to_numeric(df["num_purchases"], errors="coerce")
    df["avg_purchase_value"] = pd.to_numeric(df["avg_purchase_value"], errors="coerce")
    return df


def customer_total_spend_proxy(df: pd.DataFrame) -> float:
    """Compute a spend proxy using only Kaggle columns."""
    if "num_purchases" not in df.columns or "avg_purchase_value" not in df.columns:
        return float("nan")
    spend = df["num_purchases"] * df["avg_purchase_value"]
    return float(spend.sum())


def customer_daily_spend_proxy(df: pd.DataFrame) -> pd.DataFrame:
    """Compute daily spend proxy (date + total_revenue) using only Kaggle columns."""
    if (
        "last_purchase_date" not in df.columns
        or "num_purchases" not in df.columns
        or "avg_purchase_value" not in df.columns
    ):
        return pd.DataFrame(columns=["date", "total_revenue"])
    spend = df["num_purchases"] * df["avg_purchase_value"]
    grouped = (
        pd.DataFrame({"date": df["last_purchase_date"], "spend": spend})
        .groupby("date", dropna=False)["spend"]
        .sum()
        .reset_index(name="total_revenue")
        .sort_values("date")
    )
    return grouped


def customer_spend_by_country(df: pd.DataFrame) -> pd.DataFrame:
    """Compute spend proxy by country (region + total_revenue)."""
    if (
        "country" not in df.columns
        or "num_purchases" not in df.columns
        or "avg_purchase_value" not in df.columns
    ):
        return pd.DataFrame(columns=["region", "total_revenue"])
    spend = df["num_purchases"] * df["avg_purchase_value"]
    grouped = (
        pd.DataFrame({"region": df["country"], "spend": spend})
        .groupby("region", dropna=False)["spend"]
        .sum()
        .reset_index(name="total_revenue")
        .sort_values("total_revenue", ascending=False)
    )
    return grouped


def customer_top_customers_by_spend(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Compute top customers by spend proxy."""
    if (
        "customer_id" not in df.columns
        or "num_purchases" not in df.columns
        or "avg_purchase_value" not in df.columns
    ):
        return pd.DataFrame(columns=["customer_id", "total_revenue"])
    spend = df["num_purchases"] * df["avg_purchase_value"]
    grouped = (
        pd.DataFrame({"customer_id": df["customer_id"].astype(str), "spend": spend})
        .groupby("customer_id", dropna=False)["spend"]
        .sum()
        .reset_index(name="total_revenue")
        .sort_values("total_revenue", ascending=False)
        .head(top_n)
    )
    return grouped


def aggregate_total_revenue(df: pd.DataFrame) -> float:
    """Return total revenue from the dataset."""
    if "revenue" not in df.columns:
        return float("nan")
    return float(df["revenue"].sum())


def aggregate_daily_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Return daily revenue as a DataFrame."""
    if "date" not in df.columns or "revenue" not in df.columns:
        return pd.DataFrame(columns=["date", "total_revenue"])
    grouped = (
        df.groupby("date", dropna=False)["revenue"]
        .sum()
        .reset_index(name="total_revenue")
        .sort_values("date")
    )
    return grouped


def aggregate_revenue_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Return revenue by region as a DataFrame."""
    if "region" not in df.columns or "revenue" not in df.columns:
        return pd.DataFrame(columns=["region", "total_revenue"])
    grouped = (
        df.groupby("region", dropna=False)["revenue"]
        .sum()
        .reset_index(name="total_revenue")
        .sort_values("total_revenue", ascending=False)
    )
    return grouped


def aggregate_top_customers(
    df: pd.DataFrame,
    top_n: int = 10,
) -> pd.DataFrame:
    """Return top N customers by revenue."""
    if "customer_id" not in df.columns or "revenue" not in df.columns:
        return pd.DataFrame(columns=["customer_id", "total_revenue"])
    grouped = (
        df.groupby("customer_id", dropna=False)["revenue"]
        .sum()
        .reset_index(name="total_revenue")
        .sort_values("total_revenue", ascending=False)
        .head(top_n)
    )
    return grouped


def percentage(numerator: float, denominator: float) -> float:
    """Safely compute a percentage (0-100)."""
    if denominator <= 0 or np.isnan(denominator):
        return 0.0
    return float((numerator / denominator) * 100.0)

