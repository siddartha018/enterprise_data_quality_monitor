from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

import pandas as pd

try:
    import snowflake.connector  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    snowflake = None  # type: ignore

from enterprise_data_quality_monitor.config.snowflake_config import SnowflakeConfig
from enterprise_data_quality_monitor.utils.logging_utils import get_logger


logger = get_logger(__name__)


@contextmanager
def snowflake_connection(config: SnowflakeConfig):
    """Context manager yielding a Snowflake connection.

    This isolates connector usage so local development can run
    without Snowflake installed, as long as Snowflake-specific
    paths are not exercised.
    """

    if "snowflake" not in globals() or snowflake is None:  # type: ignore[name-defined]
        raise RuntimeError(
            "snowflake-connector-python is not installed. "
            "Install it or avoid using Snowflake as a data source."
        )

    conn = snowflake.connector.connect(  # type: ignore[attr-defined]
        account=config.account,
        user=config.user,
        password=config.password,
        role=config.role,
        warehouse=config.warehouse,
        database=config.database,
        schema=config.schema,
    )
    try:
        yield conn
    finally:
        conn.close()


def fetch_dataframe(
    config: SnowflakeConfig,
    query: str,
    params: Optional[dict] = None,
) -> pd.DataFrame:
    """Run a query and return results as a pandas DataFrame."""
    logger.info("Executing Snowflake query", extra={"query": query})
    with snowflake_connection(config) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params or {})
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        finally:
            cursor.close()

    df = pd.DataFrame(rows, columns=columns)
    # Normalize column names to lowercase so downstream logic can rely
    # on canonical names like "transaction_id" regardless of Snowflake
    # identifier casing rules.
    df.columns = [str(c).lower() for c in df.columns]
    return df


def fetch_transactions(
    config: SnowflakeConfig,
    table_name: str,
) -> pd.DataFrame:
    """Fetch rows from a Snowflake table for use as transactions.

    We select all columns so that this function works both for:
    - Traditional transaction tables with columns like transaction_id, date, revenue, etc.
    - Kaggle-style customer transactions tables (Customer_Transactions.csv schema).
    Column names are normalized to lowercase by fetch_dataframe.
    """
    query = f"SELECT * FROM {table_name}"
    return fetch_dataframe(config, query)


def fetch_reported_revenue(
    config: SnowflakeConfig,
    summary_table: str,
) -> pd.DataFrame:
    """Fetch reported revenue totals from a Snowflake summary table.

    The summary table is expected to contain at least:
    - reporting_date (DATE)
    - reported_revenue (NUMERIC)
    """
    query = f"""
        SELECT
            reporting_date,
            reported_revenue
        FROM {summary_table}
    """
    return fetch_dataframe(config, query)

