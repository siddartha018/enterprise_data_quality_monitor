from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import pandas as pd

def validate_schema(
    df: pd.DataFrame,
    expected_columns: Optional[Iterable[str]] = None,
) -> Dict[str, object]:
    """Validate that the DataFrame contains the expected columns.

    Returns a dictionary with:
    - is_valid: bool
    - missing_columns: list[str]
    - extra_columns: list[str]
    """
    expected = list(expected_columns) if expected_columns is not None else []
    columns = list(df.columns)
    missing: List[str] = [col for col in expected if col not in columns]
    extra: List[str] = [col for col in columns if col not in expected] if expected else []
    is_valid = not missing
    return {
        "is_valid": is_valid,
        "missing_columns": missing,
        "extra_columns": extra,
    }

