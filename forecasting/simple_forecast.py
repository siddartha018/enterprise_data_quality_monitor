from __future__ import annotations

from datetime import timedelta
from typing import Optional

import pandas as pd

from enterprise_data_quality_monitor.utils.logging_utils import get_logger


logger = get_logger(__name__)


def forecast_daily_series(
    history_df: pd.DataFrame,
    *,
    date_column: str = "date",
    value_column: str = "total_revenue",
    horizon_days: int = 7,
    window_days: int = 14,
) -> Optional[pd.DataFrame]:
    """Create a simple moving-average forecast for a daily time series.

    This intentionally uses a very simple model to demonstrate forecasting
    without adding heavy dependencies. It:
    - Aggregates to daily totals (in case there are duplicates).
    - Computes a rolling mean over the last `window_days`.
    - Uses the last available rolling mean as the forecast for the next
      `horizon_days`.

    Returns a DataFrame with:
    - date
    - forecast_total_revenue
    or None if there is insufficient data.
    """
    if history_df.empty or date_column not in history_df.columns or value_column not in history_df.columns:
        logger.info("Not enough data for forecasting; history is empty or missing columns.")
        return None

    df = history_df.copy()
    df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
    df = df.dropna(subset=[date_column])

    daily = (
        df.groupby(date_column, dropna=False)[value_column]
        .sum()
        .reset_index(name=value_column)
        .sort_values(date_column)
    )

    if len(daily) < max(window_days, 3):
        logger.info("Not enough history (%s days) for rolling-window forecast.", len(daily))
        return None

    daily["rolling_mean"] = (
        daily[value_column].rolling(window=window_days, min_periods=3).mean()
    )
    last_row = daily.dropna(subset=["rolling_mean"]).tail(1)
    if last_row.empty:
        logger.info("Rolling mean could not be computed; skipping forecast.")
        return None

    last_date = last_row[date_column].iloc[0]
    last_mean = float(last_row["rolling_mean"].iloc[0])

    future_dates = [
        last_date + timedelta(days=i) for i in range(1, horizon_days + 1)
    ]
    forecast_df = pd.DataFrame(
        {
            "date": future_dates,
            "forecast_total_revenue": [last_mean] * len(future_dates),
        }
    )
    return forecast_df

