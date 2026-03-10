from __future__ import annotations

from typing import Dict

import pandas as pd

from enterprise_data_quality_monitor.utils.data_utils import percentage


def check_missing_values(df: pd.DataFrame) -> Dict[str, object]:
    """Compute missing value statistics for the dataset.

    Returns a dictionary with:
    - total_missing: int
    - total_cells: int
    - missing_percentage: float
    - per_column_missing: dict[column, float]
    """
    total_cells = df.size
    total_missing = int(df.isna().sum().sum())
    missing_pct = percentage(float(total_missing), float(total_cells))
    per_column_missing = {
        col: percentage(float(df[col].isna().sum()), float(len(df)))
        for col in df.columns
    }
    return {
        "total_missing": total_missing,
        "total_cells": int(total_cells),
        "missing_percentage": missing_pct,
        "per_column_missing": per_column_missing,
    }

