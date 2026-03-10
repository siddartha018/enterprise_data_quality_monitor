from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from enterprise_data_quality_monitor.utils.data_utils import (
    aggregate_total_revenue,
    percentage,
)


def reconcile_revenue(
    transactions_df: pd.DataFrame,
    reported_df: Optional[pd.DataFrame],
    tolerance_pct: float = 1.0,
) -> Dict[str, object]:
    """Compare calculated vs reported revenue and return reconciliation results.

    `reported_df` is expected to contain at least a `reported_revenue` column.
    If multiple rows are present, the function will sum them to derive a total.
    """
    calculated_revenue = aggregate_total_revenue(transactions_df)

    if reported_df is None or reported_df.empty:
        return {
            "calculated_revenue": calculated_revenue,
            "reported_revenue": np.nan,
            "absolute_difference": np.nan,
            "percentage_difference": np.nan,
            "within_tolerance": False,
            "has_reported_data": False,
        }

    if "reported_revenue" not in reported_df.columns:
        raise ValueError("reported_df must contain a 'reported_revenue' column")

    reported_revenue = float(reported_df["reported_revenue"].sum())
    abs_diff = float(calculated_revenue - reported_revenue)
    pct_diff = percentage(abs(abs_diff), reported_revenue)
    within_tolerance = pct_diff <= tolerance_pct

    return {
        "calculated_revenue": calculated_revenue,
        "reported_revenue": reported_revenue,
        "absolute_difference": abs_diff,
        "percentage_difference": pct_diff,
        "within_tolerance": within_tolerance,
        "has_reported_data": True,
    }

