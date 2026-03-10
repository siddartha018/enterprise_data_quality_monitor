from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def detect_numeric_anomalies(
    df: pd.DataFrame,
    value_column: str,
    date_column: Optional[str] = None,
    contamination: float = 0.05,
    random_state: int = 42,
) -> Dict[str, object]:
    """Detect anomalous numeric records using IsolationForest.

    The model is fit on records with non-null revenue values. It uses
    the chosen numeric column as the primary feature and optionally additional numeric
    encodings (e.g., day of month) for basic temporal awareness.

    Returns a dictionary with:
    - anomalies: pandas.DataFrame (subset of df)
    - anomaly_count: int
    - scores: pandas.Series of anomaly scores aligned with df index
    """
    if value_column not in df.columns:
        return {
            "anomalies": pd.DataFrame(columns=df.columns),
            "anomaly_count": 0,
            "scores": pd.Series([], dtype=float),
        }

    working_df = df.copy()
    mask_valid = working_df[value_column].notna()
    valid_df = working_df[mask_valid]

    if valid_df.empty:
        return {
            "anomalies": pd.DataFrame(columns=df.columns),
            "anomaly_count": 0,
            "scores": pd.Series([], dtype=float),
        }

    features = valid_df[[value_column]].astype(float)

    if date_column and date_column in valid_df.columns:
        dates = pd.to_datetime(valid_df[date_column], errors="coerce")
        features = features.assign(day_of_month=dates.dt.day.fillna(0).astype(float))

    model = IsolationForest(
        contamination=min(max(contamination, 0.001), 0.5),
        random_state=random_state,
    )
    model.fit(features)

    anomaly_scores = model.decision_function(features)
    anomaly_flags = model.predict(features) == -1

    scores_series = pd.Series(index=valid_df.index, data=anomaly_scores)
    full_scores = pd.Series(index=df.index, data=np.nan, dtype=float)
    full_scores.loc[scores_series.index] = scores_series

    anomalies_df = valid_df[anomaly_flags]

    return {
        "anomalies": anomalies_df,
        "anomaly_count": int(len(anomalies_df)),
        "scores": full_scores,
    }


def detect_revenue_anomalies(
    df: pd.DataFrame,
    contamination: float = 0.05,
    random_state: int = 42,
) -> Dict[str, object]:
    """Backwards-compatible wrapper for revenue anomaly detection."""
    return detect_numeric_anomalies(
        df=df,
        value_column="revenue",
        date_column="date",
        contamination=contamination,
        random_state=random_state,
    )

