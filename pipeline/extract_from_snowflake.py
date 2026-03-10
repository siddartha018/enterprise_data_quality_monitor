from __future__ import annotations

from typing import Optional

import pandas as pd

from enterprise_data_quality_monitor.config.snowflake_config import SnowflakeConfig
from enterprise_data_quality_monitor.utils.logging_utils import get_logger
from enterprise_data_quality_monitor.warehouse.snowflake_client import (
    fetch_reported_revenue,
    fetch_transactions,
)


logger = get_logger(__name__)


def extract_transactions_from_snowflake(
    config: SnowflakeConfig,
    table_name: str,
) -> pd.DataFrame:
    """Extract financial transactions from Snowflake."""
    logger.info("Extracting transactions from Snowflake table '%s'", table_name)
    return fetch_transactions(config, table_name)


def extract_reported_revenue_from_snowflake(
    config: SnowflakeConfig,
    summary_table: str,
) -> pd.DataFrame:
    """Extract reported revenue totals from a Snowflake summary table."""
    logger.info(
        "Extracting reported revenue from Snowflake summary table '%s'", summary_table
    )
    return fetch_reported_revenue(config, summary_table)

