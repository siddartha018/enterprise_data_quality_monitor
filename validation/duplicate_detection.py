from __future__ import annotations

from typing import Dict, Iterable, Optional

import pandas as pd

from enterprise_data_quality_monitor.utils.data_utils import percentage


def detect_duplicates(
    df: pd.DataFrame,
    subset_cols: Optional[Iterable[str]] = None,
) -> Dict[str, object]:
    """Detect duplicate rows and return summary statistics.

    Returns a dictionary with:
    - duplicate_count: int
    - duplicate_percentage: float
    - subset_columns: list[str] | None
    - duplicates: pandas.DataFrame (may be empty)
    """
    duplicated_mask = df.duplicated(subset=subset_cols, keep=False)
    duplicates_df = df[duplicated_mask].copy()

    duplicate_count = int(duplicated_mask.sum())
    duplicate_pct = percentage(float(duplicate_count), float(len(df)))

    return {
        "duplicate_count": duplicate_count,
        "duplicate_percentage": duplicate_pct,
        "subset_columns": list(subset_cols) if subset_cols is not None else None,
        "duplicates": duplicates_df,
    }

